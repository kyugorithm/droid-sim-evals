"""Run DreamZero on one or more reconstructed DreamZero Appendix G tasks.

The evaluator deliberately keeps the inference loop identical to the existing
DROID simulator smoke test: three DROID views, 8D joint-position actions, and
the DreamZero WebSocket client.  The scene/layout and instruction are the only
task-level inputs changed here.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import subprocess
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import gymnasium as gym
import mediapy
import numpy as np
import torch
import tyro
import yaml
from openpi_client import image_tools
from tqdm import tqdm

from eval_utils.policy_client import WebsocketClientPolicy


REPO_ROOT = Path(__file__).resolve().parents[1]
TASKS_PATH = REPO_ROOT / "configs/appendix_g_tasks.yaml"
PRIVATE_DATA_ROOT = Path(
    os.environ.get("PRIVATE_DATA_ROOT", Path.home() / ".local/share/.private")
)
SIM_ROOT = Path(os.environ.get("SIM_EVALS_ROOT", PRIVATE_DATA_ROOT / "sim-evals"))
DEFAULT_OUTPUT = Path(
    os.environ.get("APPENDIX_G_RUN_DIR", PRIVATE_DATA_ROOT / "runs")
)
DEFAULT_SCENE_DIR = Path(
    os.environ.get("APPENDIX_G_SCENE_DIR", PRIVATE_DATA_ROOT / "appendix_g_scenes")
)


def _load_task(task_id: str, path: Path = TASKS_PATH) -> dict[str, Any]:
    with path.open() as handle:
        manifest = yaml.safe_load(handle)
    for task in manifest["tasks"]:
        if str(task["id"]).upper() == task_id.upper():
            return task
    raise ValueError(f"Unknown Appendix G task: {task_id}")


def _load_tasks(selector: str, path: Path = TASKS_PATH) -> list[dict[str, Any]]:
    with path.open() as handle:
        tasks = yaml.safe_load(handle)["tasks"]
    selector = selector.lower()
    if selector == "all":
        return tasks
    if selector in {"seen", "unseen"}:
        return [task for task in tasks if task["split"] == selector]
    return [_load_task(selector, path)]


class ProxyTaskEvaluator:
    """Progress metrics for the generated proxy scenes.

    This is the first evaluator layer.  For rigid pick/place and directional
    tasks it reports a reproducible geometric score.  Articulation, cloth,
    deformable and multi-stage interactions are explicitly marked approximate
    until their real asset/controller is installed, so they are not confused
    with a faithful physical reproduction.
    """

    def __init__(self, env: Any, task: dict[str, Any], layout_id: int):
        self.env = env
        self.task = task
        self.layout_id = layout_id
        self.evaluator = str(task.get("evaluator", "unknown"))
        self.objects = [str(x) for x in task.get("objects", [])]
        self.initial: dict[str, np.ndarray] = {}
        self.initial_quat: dict[str, np.ndarray] = {}
        self._move_stage_completed = False
        self._capture_initial()

    @property
    def approximate(self) -> bool:
        return self.evaluator not in {
            "contain",
            "place_on_surface",
            "place_on_object",
            "pick_and_place",
            "remove_and_place",
            "remove_from_container",
            "move_to_region",
            "place_next_to",
            "attach_to_surface",
            "bring_objects_together",
        }

    def _scene(self) -> Any:
        return self.env.unwrapped.scene

    def _get_vec(self, name: str, field: str = "root_pos_w") -> np.ndarray | None:
        try:
            asset = self._scene()[name]
        except (KeyError, TypeError, AttributeError):
            return None
        value = getattr(asset.data, field, None)
        if value is None:
            return None
        return value[0].detach().cpu().numpy().astype(np.float64)

    def _capture_initial(self) -> None:
        for name in self.objects:
            pos = self._get_vec(name)
            if pos is not None:
                self.initial[name] = pos.copy()
            quat = self._get_vec(name, "root_quat_w")
            if quat is not None:
                self.initial_quat[name] = quat.copy()

    def _position(self, name: str) -> np.ndarray | None:
        return self._get_vec(name)

    @staticmethod
    def _distance(a: np.ndarray | None, b: np.ndarray | None) -> float | None:
        if a is None or b is None:
            return None
        return float(np.linalg.norm(a - b))

    def score(self) -> dict[str, Any]:
        source = self.objects[0] if self.objects else ""
        target = self.objects[1] if len(self.objects) > 1 else ""
        src = self._position(source)
        dst = self._position(target)
        start = self.initial.get(source)
        start_dist = self._distance(start, self.initial.get(target))
        current_dist = self._distance(src, dst)
        moved = 0.0 if src is None or start is None else float(np.linalg.norm(src - start))

        metric: float | None = None
        success = False
        reason = ""
        if self.evaluator == "move_then_contain":
            # The paper gives the instruction and says the two rollouts vary
            # object locations, but does not publish a DROID-frame success
            # function.  These thresholds/directions are explicitly local
            # geometric proxies, not the paper's hidden evaluator.
            cfg = self.task.get("proxy_evaluation", {})
            container_name = str(cfg.get("container", source))
            item_name = str(cfg.get("item", target))
            container = self._position(container_name)
            item = self._position(item_name)
            container_start = self.initial.get(container_name)
            move_axis = np.asarray(cfg.get("forward_axis_xy", [1.0, 0.0]), dtype=np.float64)
            axis_norm = float(np.linalg.norm(move_axis))
            if axis_norm <= 1e-8:
                raise ValueError("proxy_evaluation.forward_axis_xy must be non-zero")
            move_axis /= axis_norm
            move_threshold = float(cfg.get("move_distance_m", 0.15))
            moved_forward = (
                float(np.dot((container - container_start)[:2], move_axis))
                if container is not None and container_start is not None
                else None
            )
            move_progress = (
                float(np.clip(moved_forward / move_threshold, 0.0, 1.0))
                if moved_forward is not None and move_threshold > 0
                else None
            )
            move_stage_was_completed = self._move_stage_completed
            cup_moved = bool(moved_forward is not None and moved_forward >= move_threshold)
            self._move_stage_completed = self._move_stage_completed or cup_moved

            container_size = cfg.get("container_size_m", [0.22, 0.22, 0.12])
            inner_radius = float(cfg.get("inner_radius_m", 0.085))
            item_to_container_xy = (
                float(np.linalg.norm((item - container)[:2]))
                if item is not None and container is not None
                else None
            )
            container_bottom = (
                float(container[2] - float(container_size[2]) / 2.0)
                if container is not None
                else None
            )
            container_top = (
                float(container[2] + float(container_size[2]) / 2.0)
                if container is not None
                else None
            )
            item_z = float(item[2]) if item is not None else None
            # Marker may protrude above the cup; require its center to be
            # above the cup floor and near the interior footprint.
            geometrically_inside = bool(
                item_to_container_xy is not None
                and container_bottom is not None
                and container_top is not None
                and item_z is not None
                and item_to_container_xy <= inner_radius
                and container_bottom + 0.005 <= item_z <= container_top + 0.08
            )
            containment_progress = (
                float(np.clip(1.0 - item_to_container_xy / max(inner_radius, 1e-6), 0.0, 1.0))
                if item_to_container_xy is not None
                else None
            )
            inside = geometrically_inside and move_stage_was_completed
            if not move_stage_was_completed:
                containment_progress = 0.0
            if move_progress is not None and containment_progress is not None:
                metric = 0.5 * move_progress + 0.5 * containment_progress
            success = cup_moved and inside
            return {
                "progress": metric,
                "success": success,
                "scoring": "proxy_geometric_staged",
                "approximate": True,
                "reason": "cup_forward_then_marker_center_inside_cup_proxy",
                "stages": {
                    "cup_moved_forward": {
                        "progress": move_progress,
                        "complete": cup_moved,
                        "forward_displacement_m": moved_forward,
                    },
                    "marker_inside_cup": {
                        "progress": containment_progress,
                        "complete": inside,
                        "xy_distance_m": item_to_container_xy,
                    },
                },
            }
        elif self.evaluator in {"contain", "place_on_object", "pick_and_place", "remove_and_place"}:
            if current_dist is not None and start_dist is not None:
                metric = np.clip((start_dist - current_dist) / max(start_dist - 0.10, 1e-6), 0.0, 1.0)
                success = bool(current_dist < 0.12 and moved > 0.08)
                reason = "source_target_distance"
        elif self.evaluator == "remove_from_container":
            metric = float(np.clip(moved / 0.25, 0.0, 1.0))
            success = bool(moved > 0.20)
            reason = "source_displacement"
        elif self.evaluator == "orient_object":
            cfg = self.task.get("proxy_evaluation", {})
            local_axis = np.asarray(
                cfg.get("handle_local_axis_xyz", [1.0, 0.0, 0.0]), dtype=np.float64
            )
            target_axis = np.asarray(
                cfg.get("target_axis_xy", [1.0, 0.0]), dtype=np.float64
            )
            local_norm = float(np.linalg.norm(local_axis))
            target_norm = float(np.linalg.norm(target_axis))
            if local_norm <= 1e-8 or target_norm <= 1e-8:
                raise ValueError("orient_object proxy axes must be non-zero")
            local_axis /= local_norm
            target_axis /= target_norm
            quat = self._get_vec(source, "root_quat_w")
            if quat is not None and np.isfinite(quat).all():
                quat_norm = float(np.linalg.norm(quat))
                if quat_norm <= 1e-8:
                    raise ValueError("mug root quaternion must be non-zero")
                w, x, y, z = quat / quat_norm
                rotation = np.asarray(
                    [
                        [1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
                        [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
                        [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)],
                    ],
                    dtype=np.float64,
                )
                handle_axis = rotation @ local_axis
                handle_xy = handle_axis[:2]
                handle_xy /= max(float(np.linalg.norm(handle_xy)), 1e-8)
                alignment = float(np.clip(np.dot(handle_xy, target_axis), -1.0, 1.0))
                tolerance_deg = float(cfg.get("tolerance_deg", 30.0))
                metric = float(np.clip((alignment + 1.0) / 2.0, 0.0, 1.0))
                success = bool(alignment >= math.cos(math.radians(tolerance_deg)))
                reason = "mug_handle_axis_aligned_with_local_right_proxy"
        elif self.evaluator == "place_on_surface":
            if src is not None and start is not None:
                metric = float(np.clip(moved / 0.25, 0.0, 1.0))
                success = bool(moved > 0.20 and TABLE_XY(src))
                reason = "tabletop_region_and_displacement"
        elif self.evaluator in {"place_next_to", "attach_to_surface", "bring_objects_together"}:
            if current_dist is not None and start_dist is not None:
                metric = np.clip((start_dist - current_dist) / max(start_dist - 0.15, 1e-6), 0.0, 1.0)
                success = bool(current_dist < 0.18 and moved > 0.08)
                reason = "pair_distance"
        elif self.evaluator == "move_to_region":
            if src is not None:
                cfg = self.task.get("proxy_evaluation", {})
                direction = np.asarray(cfg.get("direction_xy", [1.0, 0.0]), dtype=np.float64)
                direction_norm = float(np.linalg.norm(direction))
                if direction_norm <= 1e-8:
                    raise ValueError("proxy_evaluation.direction_xy must be non-zero")
                direction /= direction_norm
                target_distance = float(cfg.get("target_distance_m", 0.25))
                start_pos = self.initial.get(source)
                directional_displacement = (
                    float(np.dot((src - start_pos)[:2], direction))
                    if start_pos is not None
                    else 0.0
                )
                metric = float(
                    np.clip(directional_displacement / max(target_distance, 1e-6), 0.0, 1.0)
                )
                success = bool(
                    directional_displacement >= target_distance
                    and moved > 0.12
                    and TABLE_XY(src)
                )
                reason = "proxy_directional_displacement_on_table"

        if metric is None:
            # We still emit a row for every episode.  A null score prevents a
            # proxy from being silently presented as a real success metric.
            return {
                "progress": None,
                "success": None,
                "scoring": "not_implemented",
                "approximate": True,
                "reason": "requires articulated/deformable/multi-stage evaluator",
            }
        return {
            "progress": float(metric),
            "success": success,
            "scoring": "proxy_geometric",
            "approximate": self.approximate,
            "reason": reason,
        }


def TABLE_XY(pos: np.ndarray) -> bool:
    # Bounds of the generated tabletop aligned to sim-evals/assets/scene1.usd.
    return 0.20 < float(pos[0]) < 0.90 and -0.478 < float(pos[1]) < 0.522


class AppendixGJointPosClient:
    """DreamZero-compatible client for the three-view AR-DROID server."""

    def __init__(self, remote_host: str, remote_port: int, open_loop_horizon: int = 8):
        if open_loop_horizon < 1:
            raise ValueError("open_loop_horizon must be at least 1")
        self.client = WebsocketClientPolicy(remote_host, remote_port)
        self.open_loop_horizon = open_loop_horizon
        self.actions_from_chunk_completed = 0
        self.pred_action_chunk: np.ndarray | None = None
        self.session_id = str(uuid.uuid4())

    def reset(self) -> None:
        self.actions_from_chunk_completed = 0
        self.pred_action_chunk = None
        self.session_id = str(uuid.uuid4())
        self.client.reset({"session_id": self.session_id})

    @staticmethod
    def _extract_observation(obs_dict: dict[str, Any]) -> dict[str, np.ndarray]:
        policy = obs_dict["policy"]
        return {
            "right_image": policy["external_cam"][0].detach().cpu().numpy(),
            "left_image": policy["external_cam_2"][0].detach().cpu().numpy(),
            "wrist_image": policy["wrist_cam"][0].detach().cpu().numpy(),
            "joint_position": policy["arm_joint_pos"].detach().cpu().numpy(),
            "gripper_position": policy["gripper_pos"].detach().cpu().numpy(),
        }

    def infer(self, obs: dict[str, Any], instruction: str) -> dict[str, Any]:
        current = self._extract_observation(obs)
        if (
            self.actions_from_chunk_completed == 0
            or self.actions_from_chunk_completed >= self.open_loop_horizon
            or self.pred_action_chunk is None
            or self.actions_from_chunk_completed >= len(self.pred_action_chunk)
        ):
            self.actions_from_chunk_completed = 0
            request = {
                "observation/exterior_image_0_left": image_tools.resize_with_pad(
                    current["right_image"], 180, 320
                ),
                "observation/exterior_image_1_left": image_tools.resize_with_pad(
                    current["left_image"], 180, 320
                ),
                "observation/wrist_image_left": image_tools.resize_with_pad(
                    current["wrist_image"], 180, 320
                ),
                "observation/joint_position": current["joint_position"].astype(np.float64),
                "observation/cartesian_position": np.zeros((1, 6), dtype=np.float64),
                "observation/gripper_position": current["gripper_position"].astype(np.float64),
                "prompt": instruction,
                "session_id": self.session_id,
            }
            response = self.client.infer(request)
            actions = response["actions"] if isinstance(response, dict) else response
            self.pred_action_chunk = np.asarray(actions)
            if (
                self.pred_action_chunk.ndim != 2
                or self.pred_action_chunk.shape[0] == 0
                or self.pred_action_chunk.shape[-1] != 8
                or not np.isfinite(self.pred_action_chunk).all()
            ):
                raise RuntimeError(
                    "DreamZero returned invalid actions: "
                    f"shape={self.pred_action_chunk.shape}, "
                    f"finite={np.isfinite(self.pred_action_chunk).all()}"
                )

        action = self.pred_action_chunk[self.actions_from_chunk_completed]
        self.actions_from_chunk_completed += 1
        action = action.copy()
        action[-1] = 1.0 if action[-1] > 0.5 else 0.0
        viz = np.concatenate(
            [
                image_tools.resize_with_pad(current["right_image"], 224, 224),
                image_tools.resize_with_pad(current["wrist_image"], 224, 224),
                image_tools.resize_with_pad(current["left_image"], 224, 224),
            ],
            axis=1,
        )
        return {"action": action, "viz": viz}


def _build_app(requested_device: str):
    from isaaclab.app import AppLauncher

    parser = argparse.ArgumentParser(description="DreamZero Appendix G evaluator")
    AppLauncher.add_app_launcher_args(parser)
    args_cli, _ = parser.parse_known_args()
    args_cli.device = requested_device
    args_cli.enable_cameras = True
    args_cli.headless = True
    return AppLauncher(args_cli), args_cli


def _check_isaac_graphics() -> None:
    """Check the host capability before Isaac Sim initializes GPU Foundation."""
    local_icd = REPO_ROOT / "configs/nvidia_icd.local.json"
    example_icd = REPO_ROOT / "configs/nvidia_icd.example.json"
    os.environ.setdefault(
        "VK_ICD_FILENAMES", str(local_icd if local_icd.is_file() else example_icd)
    )
    checker = REPO_ROOT / "scripts/check_nvidia_vulkan.py"
    subprocess.run([sys.executable, str(checker)], check=True)


def main(
    task: str = "S01",
    layout: int = 0,
    episodes: int = 1,
    host: str = "127.0.0.1",
    port: int = 8000,
    output: Path = DEFAULT_OUTPUT,
    scene_dir: Path = DEFAULT_SCENE_DIR,
    headless: bool = True,
    device: str = "cuda:0",
    open_loop_horizon: int = 8,
    max_steps: int | None = None,
) -> None:
    del headless  # Isaac Lab is always launched headless for reproducibility.
    task_specs = _load_tasks(task)
    if layout not in (0, 1, 2):
        raise ValueError("layout must be 0, 1, or 2 (both paired layouts)")
    layout_ids = [0, 1] if layout == 2 or task.lower() in {"all", "seen", "unseen"} else [layout]

    # Fail before Isaac starts if the pod has CUDA but not the Vulkan/RTX
    # capability required for camera observations.
    _check_isaac_graphics()

    # Launch Isaac before importing IsaacLab-dependent packages.
    app_launcher, args_cli = _build_app(device)
    simulation_app = app_launcher.app
    try:
        import sim_evals.environments  # noqa: F401
        from isaaclab_tasks.utils import parse_env_cfg
        client = AppendixGJointPosClient(
            remote_host=host, remote_port=port, open_loop_horizon=open_loop_horizon
        )

        run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        run_dir = output / ("matrix" if task.lower() in {"all", "seen", "unseen"} else task.upper()) / run_id
        run_dir.mkdir(parents=True, exist_ok=True)
        results: list[dict[str, Any]] = []

        with torch.no_grad():
            for task_spec in task_specs:
                for current_layout in layout_ids:
                    env_cfg = parse_env_cfg("APPENDIX_G", device=args_cli.device, num_envs=1, use_fabric=True)
                    env_cfg.sim.device = args_cli.device
                    task_id = str(task_spec["id"]).upper()
                    env_cfg.set_task(task_id, current_layout, scene_dir=scene_dir)
                    env = gym.make("APPENDIX_G", cfg=env_cfg)
                    task_run_dir = run_dir / task_id / f"layout{current_layout}"
                    task_run_dir.mkdir(parents=True, exist_ok=True)
                    episode_limit = max_steps or int(
                        getattr(env.unwrapped, "max_episode_length", env.env.max_episode_length)
                    )
                    try:
                        for episode in range(episodes):
                            obs, _ = env.reset()
                            # Isaac Lab needs the second render cycle for loaded
                            # materials, matching the original sim-evals runner.
                            obs, _ = env.reset()
                            evaluator = ProxyTaskEvaluator(env, task_spec, current_layout)
                            frames: list[np.ndarray] = []
                            steps = 0
                            last_score: dict[str, Any] = {}
                            for _ in tqdm(
                                range(episode_limit),
                                desc=f"{task_id} layout={current_layout} episode={episode + 1}/{episodes}",
                            ):
                                result = client.infer(obs, str(task_spec["instruction"]))
                                frames.append(result["viz"])
                                action = torch.as_tensor(result["action"], dtype=torch.float32).reshape(1, -1)
                                obs, _, terminated, truncated, _ = env.step(action)
                                last_score = evaluator.score()
                                steps += 1
                                if terminated or truncated:
                                    break
                            client.reset()

                            video_path = task_run_dir / f"episode_{episode:02d}.mp4"
                            if frames:
                                mediapy.write_video(video_path, frames, fps=15)
                            result_row = {
                                "task_id": task_id,
                                "split": task_spec["split"],
                                "instruction": task_spec["instruction"],
                                "layout_id": current_layout,
                                "episode": episode,
                                "steps": steps,
                                "video": str(video_path),
                                **last_score,
                            }
                            results.append(result_row)
                            (run_dir / "results.json").write_text(json.dumps(results, indent=2))
                            print(json.dumps(result_row, indent=2), flush=True)
                    finally:
                        env.close()

        print(f"[appendix-g-eval] results: {run_dir / 'results.json'}", flush=True)
    finally:
        simulation_app.close()


if __name__ == "__main__":
    tyro.cli(main)
