"""Run DreamZero on one or more reconstructed DreamZero Appendix G tasks.

The evaluator deliberately keeps the inference loop identical to the existing
DROID simulator smoke test: three DROID views, 8D joint-position actions, and
the DreamZero WebSocket client.  The scene/layout and instruction are the only
task-level inputs changed here.
"""

from __future__ import annotations

import argparse
import html
import json
import math
import os
import subprocess
import sys
import traceback
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

if ffmpeg_path := os.environ.get("APPENDIX_G_FFMPEG"):
    mediapy.set_ffmpeg(ffmpeg_path)


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


def _s13_rotation_from_wxyz(quat: np.ndarray) -> np.ndarray:
    """Return a validated rotation matrix for an S13 pose quaternion."""
    quat = np.asarray(quat, dtype=np.float64)
    if quat.shape != (4,) or not np.isfinite(quat).all():
        raise ValueError("S13 pose quaternion must contain four finite values")
    norm = float(np.linalg.norm(quat))
    if norm <= 1e-8:
        raise ValueError("S13 pose quaternion must have non-zero magnitude")
    w, x, y, z = quat / norm
    return np.asarray(
        [
            [1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
            [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
            [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)],
        ],
        dtype=np.float64,
    )


def _s13_circular_bowl_geometry(
    *,
    item_position: np.ndarray,
    item_quaternion_wxyz: np.ndarray,
    bowl_position: np.ndarray,
    bowl_quaternion_wxyz: np.ndarray,
    item_size_xyz_m: np.ndarray,
    opening_radius_m: float,
    maximum_center_offset_m: float,
    floor_z_relative_m: float,
    rim_z_relative_m: float,
    floor_tolerance_m: float,
    minimum_fraction_inside: float,
) -> dict[str, Any]:
    """Conservative box-proxy containment check for a circular bowl.

    All eight marker-box corners are transformed into the bowl frame. Since a
    circle is convex, requiring every projected corner to lie inside the circle
    also contains the marker's full projected box footprint. The vertical
    fraction is an AABB-span approximation, not a mesh-volume intersection.
    """
    def finite_vector(name: str, value: np.ndarray, size: int = 3) -> np.ndarray:
        result = np.asarray(value, dtype=np.float64)
        if result.shape != (size,) or not np.isfinite(result).all():
            raise ValueError(f"{name} must contain {size} finite values")
        return result

    item_position = finite_vector("item_position", item_position)
    bowl_position = finite_vector("bowl_position", bowl_position)
    item_size = finite_vector("item_size_xyz_m", item_size_xyz_m)
    if np.any(item_size <= 0):
        raise ValueError("item_size_xyz_m dimensions must be positive")
    scalars = np.asarray(
        [
            opening_radius_m,
            maximum_center_offset_m,
            floor_z_relative_m,
            rim_z_relative_m,
            floor_tolerance_m,
            minimum_fraction_inside,
        ],
        dtype=np.float64,
    )
    if not np.isfinite(scalars).all():
        raise ValueError("S13 bowl geometry thresholds must be finite")
    if opening_radius_m <= 0 or maximum_center_offset_m < 0 or floor_tolerance_m < 0:
        raise ValueError(
            "S13 opening radius must be positive; center offset and floor tolerance must be non-negative"
        )
    if rim_z_relative_m <= floor_z_relative_m:
        raise ValueError("S13 bowl rim must be above its floor")
    if not 0.0 < minimum_fraction_inside <= 1.0:
        raise ValueError("minimum_fraction_inside must be in (0, 1]")

    item_rotation = _s13_rotation_from_wxyz(item_quaternion_wxyz)
    bowl_rotation = _s13_rotation_from_wxyz(bowl_quaternion_wxyz)
    signs = np.asarray(
        [
            [-1, -1, -1], [-1, -1, 1], [-1, 1, -1], [-1, 1, 1],
            [1, -1, -1], [1, -1, 1], [1, 1, -1], [1, 1, 1],
        ],
        dtype=np.float64,
    )
    item_local_corners = signs * (item_size / 2.0)
    item_world_corners = item_local_corners @ item_rotation.T + item_position
    bowl_local_corners = (item_world_corners - bowl_position) @ bowl_rotation
    item_center_bowl = (item_position - bowl_position) @ bowl_rotation
    corner_radii = np.linalg.norm(bowl_local_corners[:, :2], axis=1)
    maximum_corner_radius = float(np.max(corner_radii))
    center_offset = float(np.linalg.norm(item_center_bowl[:2]))
    bottom_z = float(np.min(bowl_local_corners[:, 2]))
    top_z = float(np.max(bowl_local_corners[:, 2]))
    bottom_world_z = float(np.min(item_world_corners[:, 2]))
    top_world_z = float(np.max(item_world_corners[:, 2]))
    vertical_span = top_z - bottom_z
    vertical_overlap = max(
        0.0,
        min(top_z, rim_z_relative_m) - max(bottom_z, floor_z_relative_m),
    )
    fraction_inside = float(np.clip(vertical_overlap / vertical_span, 0.0, 1.0))
    footprint_fits = maximum_corner_radius <= opening_radius_m
    center_within_tolerance = center_offset <= maximum_center_offset_m
    above_floor = bottom_z >= floor_z_relative_m - floor_tolerance_m
    fraction_ok = fraction_inside >= minimum_fraction_inside
    return {
        "inside_bowl": bool(
            footprint_fits and center_within_tolerance and above_floor and fraction_ok
        ),
        "projected_footprint_fits": bool(footprint_fits),
        "maximum_projected_corner_radius_m": maximum_corner_radius,
        "projected_corner_radii_m": corner_radii.tolist(),
        "opening_radius_m": float(opening_radius_m),
        "radial_clearance_m": float(opening_radius_m - maximum_corner_radius),
        "center_offset_xy_m": center_offset,
        "maximum_center_offset_m": float(maximum_center_offset_m),
        "center_within_spec_tolerance": bool(center_within_tolerance),
        "vertical_bounds_relative_to_bowl_m": [bottom_z, top_z],
        "vertical_bounds_world_z_m": [bottom_world_z, top_world_z],
        "floor_z_relative_m": float(floor_z_relative_m),
        "rim_z_relative_m": float(rim_z_relative_m),
        "above_floor": bool(above_floor),
        "fraction_of_vertical_extent_inside_proxy": fraction_inside,
        "minimum_fraction_inside": float(minimum_fraction_inside),
        "fraction_inside_ok": bool(fraction_ok),
    }


def _write_run_gallery(run_dir: Path, results: list[dict[str, Any]]) -> Path:
    """Write a browsable, incrementally updated gallery for every rollout MP4."""
    cards = []
    for row in results:
        video_path = Path(row["video"])
        try:
            relative_video = video_path.relative_to(run_dir)
        except ValueError as exc:
            raise ValueError(f"Rollout video must be inside its run directory: {video_path}") from exc
        score_fields = []
        for key in ("success", "progress", "approximate", "steps"):
            if key in row:
                score_fields.append(
                    f"<dt>{html.escape(key)}</dt><dd>{html.escape(str(row[key]))}</dd>"
                )
        title = (
            f"{row['task_id']} · layout {row['layout_id']} · "
            f"episode {int(row['episode']) + 1}"
        )
        instruction = html.escape(str(row["instruction"]))
        video_url = html.escape(relative_video.as_posix(), quote=True)
        cards.append(
            "<article><h2>" + html.escape(title) + "</h2>"
            + f"<p>{instruction}</p>"
            + f'<video controls preload="metadata" src="{video_url}"></video>'
            + f"<dl>{''.join(score_fields)}</dl>"
            + f'<p><a href="{video_url}">Open MP4</a></p></article>'
        )
    page = """<!doctype html>
<html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>Appendix G rollout videos</title>
<style>
body{font:16px system-ui,sans-serif;margin:2rem;background:#f5f6f8;color:#17202a}
main{max-width:1100px;margin:auto}article{background:white;padding:1rem 1.25rem;margin:1rem 0;border-radius:10px}
video{display:block;width:min(100%,960px);background:#111}dl{display:flex;gap:.6rem;flex-wrap:wrap}
dt{font-weight:700}dd{margin:0 1rem 0 0}
</style><main><h1>Appendix G rollout videos</h1>
<p>Generated by the evaluator. Each card is one policy rollout; the JSON beside this file is the machine-readable record.</p>
""" + "\n".join(cards) + "\n</main></html>\n"
    gallery_path = run_dir / "index.html"
    gallery_path.write_text(page)
    return gallery_path


def _write_output_catalog(output_dir: Path) -> Path:
    """Index every rollout run and embed every recorded MP4 below the output root."""
    entries = []
    video_cards = []
    for result_path in sorted(output_dir.rglob("results.json")):
        try:
            rows = json.loads(result_path.read_text())
        except (OSError, json.JSONDecodeError):
            continue
        if not rows:
            continue
        run_dir = result_path.parent
        gallery_path = _write_run_gallery(run_dir, rows)
        relative_gallery = html.escape(gallery_path.relative_to(output_dir).as_posix(), quote=True)
        task_ids = ", ".join(sorted({str(row.get("task_id", "?")) for row in rows}))
        successes = sum(bool(row.get("success")) for row in rows)
        unscored = sum(row.get("success") is None for row in rows)
        label = html.escape(run_dir.relative_to(output_dir).as_posix())
        entries.append(
            f'<li><a href="{relative_gallery}">{label}</a> — '
            f'{html.escape(task_ids)}; {len(rows)} rollout(s), {successes} proxy success(es), {unscored} unscored</li>'
        )
        for row in rows:
            video_path = Path(row["video"])
            try:
                relative_video = html.escape(
                    video_path.relative_to(output_dir).as_posix(), quote=True
                )
            except ValueError as exc:
                raise ValueError(
                    f"Rollout video must be inside catalog output root: {video_path}"
                ) from exc
            title = (
                f"{row['task_id']} · layout {row['layout_id']} · "
                f"episode {int(row['episode']) + 1}"
            )
            outcome = (
                "unscored" if row.get("success") is None
                else "proxy success" if row["success"] else "proxy failure"
            )
            approximation = " · approximate evaluator" if row.get("approximate") else ""
            instruction = html.escape(str(row.get("instruction", "")))
            reason = html.escape(str(row.get("reason", "")))
            video_cards.append(
                "<article><h3>" + html.escape(title) + "</h3>"
                + f"<p>{instruction}</p>"
                + f"<p>{outcome}{approximation}; {int(row.get('steps', 0))} steps"
                + (f"; {reason}" if reason else "") + "</p>"
                + f'<video controls preload="metadata" src="{relative_video}"></video>'
                + f'<p><a href="{relative_video}">Open MP4</a> · '
                + f'<a href="{relative_gallery}">Run details</a></p></article>'
            )
    page = """<!doctype html>
<html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>Simulation rollout catalog</title>
<style>body{font:16px system-ui,sans-serif;max-width:1100px;margin:2rem auto;padding:0 1rem;background:#f5f6f8;color:#17202a}li{margin:.8rem 0}article{background:white;padding:1rem 1.25rem;margin:1rem 0;border-radius:10px}video{display:block;width:min(100%,960px);background:#111}</style>
<h1>Simulation rollout catalog</h1>
<p>Every recorded policy rollout is shown below. Success counts are local proxy outcomes, not paper metrics.</p>
<ul>
""" + "\n".join(entries) + "\n</ul><h2>All rollout videos</h2>\n" + "\n".join(video_cards) + "\n</html>\n"
    catalog_path = output_dir / "index.html"
    catalog_path.write_text(page)
    return catalog_path


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
    if "," in selector:
        tasks_by_id = {str(task["id"]).lower(): task for task in tasks}
        requested_ids = [item.strip() for item in selector.split(",") if item.strip()]
        if not requested_ids:
            raise ValueError("Task list must contain at least one task id")
        unknown_ids = [task_id for task_id in requested_ids if task_id not in tasks_by_id]
        if unknown_ids:
            raise ValueError(f"Unknown Appendix G task(s): {', '.join(unknown_ids)}")
        if len(requested_ids) != len(set(requested_ids)):
            raise ValueError("Task list must not contain duplicate task ids")
        return [tasks_by_id[task_id] for task_id in requested_ids]
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
        self._u13_stable_steps = 0
        self._u19_stable_steps = 0
        self._s13_stable_samples = 0
        self._s13_lifted_over_rim = False
        self._s13_max_item_bottom_world_z = -math.inf
        self._capture_initial()

    @property
    def approximate(self) -> bool:
        # Appendix G does not disclose its per-task simulator metrics. Every
        # local score below is therefore a project-defined approximation,
        # including the otherwise simple rigid-body geometry checks.
        return True

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

    @staticmethod
    def _rotation_from_wxyz(quat: np.ndarray | None) -> np.ndarray:
        if quat is None or not np.isfinite(quat).all():
            return np.eye(3, dtype=np.float64)
        quat_norm = float(np.linalg.norm(quat))
        if quat_norm <= 1e-8:
            return np.eye(3, dtype=np.float64)
        w, x, y, z = quat / quat_norm
        return np.asarray(
            [
                [1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
                [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
                [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)],
            ],
            dtype=np.float64,
        )

    def score(self) -> dict[str, Any]:
        eligibility = str(self.task.get("physical_evaluation", "eligible")).lower()
        if eligibility != "eligible":
            return {
                "progress": None,
                "success": None,
                "scoring": f"physical_evaluation_{eligibility}",
                "approximate": True,
                "reason": str(
                    self.task.get(
                        "physical_evaluation_note",
                        "Physical success has not been validated for this task.",
                    )
                ),
            }

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
        score_details: dict[str, Any] = {}
        if self.task.get("id") == "U02" and self.evaluator == "repeated_contact_motion":
            state = getattr(self.env.unwrapped, "_fan_cooling", {})
            initial_temp = float(state.get("initial_temp_c", 55.0))
            current_temp = float(state.get("burger_temp_c", initial_temp))
            required_drop = float(
                self.task.get("proxy_evaluation", {}).get("minimum_temperature_drop_c", 8.0)
            )
            drop = max(0.0, initial_temp - current_temp)
            success = drop >= required_drop
            metric = float(np.clip(drop / max(required_drop, 1e-8), 0.0, 1.0))
            reason = "burger_cooled_by_oriented_fan_proxy" if success else "insufficient_fan_cooling_proxy"
            score_details["cooling"] = {
                "initial_temperature_c": initial_temp,
                "estimated_temperature_c": current_temp,
                "temperature_drop_c": drop,
                "required_drop_c": required_drop,
                "model": "orientation_and_distance_gated_lumped_cooling_not_airflow_simulation",
            }
        elif self.evaluator == "marker_in_circular_bowl":
            cfg = self.task.get("proxy_evaluation", {})
            item_name = str(cfg.get("item", source))
            bowl_name = str(cfg.get("container", target))
            item = self._position(item_name)
            bowl = self._position(bowl_name)
            item_quat = self._get_vec(item_name, "root_quat_w")
            bowl_quat = self._get_vec(bowl_name, "root_quat_w")
            initial_item = self.initial.get(item_name)
            velocity = self._get_vec(item_name, "root_lin_vel_w")
            if (
                item is None
                or bowl is None
                or item_quat is None
                or bowl_quat is None
                or initial_item is None
            ):
                self._s13_stable_samples = 0
                return {
                    "progress": 0.0,
                    "success": False,
                    "scoring": "proxy_geometric_staged",
                    "approximate": True,
                    "reason": "marker_or_bowl_pose_unavailable",
                    "stages": {
                        "marker_inside_bowl": {"complete": False},
                        "marker_moved_from_reset_pose": {"complete": False},
                        "stable_rest": {"complete": False},
                    },
                }

            geometry = _s13_circular_bowl_geometry(
                item_position=item,
                item_quaternion_wxyz=item_quat,
                bowl_position=bowl,
                bowl_quaternion_wxyz=bowl_quat,
                item_size_xyz_m=np.asarray(
                    cfg.get("item_size_m", [0.125, 0.016, 0.016]), dtype=np.float64
                ),
                opening_radius_m=float(cfg.get("bowl_opening_diameter_m", 0.145)) / 2.0,
                maximum_center_offset_m=float(cfg.get("maximum_center_offset_m", 0.008)),
                floor_z_relative_m=float(cfg.get("bowl_floor_relative_z_m", -0.04)),
                rim_z_relative_m=float(cfg.get("bowl_rim_relative_z_m", 0.04)),
                floor_tolerance_m=float(cfg.get("floor_tolerance_m", 0.005)),
                minimum_fraction_inside=float(cfg.get("minimum_fraction_inside", 0.60)),
            )
            displacement = float(np.linalg.norm(item - initial_item))
            minimum_displacement = float(cfg.get("minimum_item_displacement_m", 0.01))
            if not math.isfinite(minimum_displacement) or minimum_displacement <= 0:
                raise ValueError("S13 minimum_item_displacement_m must be positive and finite")
            moved_from_reset = displacement >= minimum_displacement

            table_surface_z = float(cfg.get("table_surface_z_m", 0.045))
            minimum_lift_clearance = float(cfg.get("minimum_lift_clearance_m", 0.005))
            if not math.isfinite(table_surface_z):
                raise ValueError("S13 table_surface_z_m must be finite")
            if not math.isfinite(minimum_lift_clearance) or minimum_lift_clearance < 0:
                raise ValueError("S13 minimum_lift_clearance_m must be finite and non-negative")
            item_bottom_world_z = float(geometry["vertical_bounds_world_z_m"][0])
            bowl_rim_world_z = float(bowl[2]) + float(geometry["rim_z_relative_m"])
            required_item_bottom_world_z = bowl_rim_world_z + minimum_lift_clearance
            self._s13_max_item_bottom_world_z = max(
                self._s13_max_item_bottom_world_z, item_bottom_world_z
            )
            lifted_over_rim_now = item_bottom_world_z >= required_item_bottom_world_z
            self._s13_lifted_over_rim = self._s13_lifted_over_rim or lifted_over_rim_now
            lift_progress = float(
                np.clip(
                    (self._s13_max_item_bottom_world_z - table_surface_z)
                    / max(required_item_bottom_world_z - table_surface_z, 1e-8),
                    0.0,
                    1.0,
                )
            )

            velocity_array = (
                np.asarray(velocity, dtype=np.float64) if velocity is not None else None
            )
            speed = (
                float(np.linalg.norm(velocity_array))
                if velocity_array is not None
                and velocity_array.shape == (3,)
                and np.isfinite(velocity_array).all()
                else None
            )
            maximum_speed = float(cfg.get("maximum_linear_speed_mps", 0.02))
            if not math.isfinite(maximum_speed) or maximum_speed < 0:
                raise ValueError("S13 maximum_linear_speed_mps must be finite and non-negative")
            low_speed = speed is not None and speed <= maximum_speed

            raw_step_dt = getattr(self.env.unwrapped, "step_dt", None)
            if raw_step_dt is None:
                env_cfg = getattr(self.env.unwrapped, "cfg", None)
                sim_cfg = getattr(env_cfg, "sim", None)
                raw_step_dt = (
                    float(sim_cfg.dt) * int(env_cfg.decimation)
                    if sim_cfg is not None and hasattr(env_cfg, "decimation")
                    else None
                )
            if raw_step_dt is None:
                raise ValueError(
                    "S13 stability scoring requires measured step_dt or sim.dt * decimation"
                )
            step_dt = float(raw_step_dt)
            if not math.isfinite(step_dt) or step_dt <= 0:
                raise ValueError("S13 evaluator requires a positive finite simulation step_dt")
            stable_duration = float(cfg.get("stable_duration_s", 1.0))
            if not math.isfinite(stable_duration) or stable_duration <= 0:
                raise ValueError("S13 stable_duration_s must be positive and finite")
            stable_sample = (
                geometry["inside_bowl"]
                and moved_from_reset
                and self._s13_lifted_over_rim
                and low_speed
            )
            self._s13_stable_samples = (
                self._s13_stable_samples + 1 if stable_sample else 0
            )
            # N observations span (N-1) physics intervals; require the measured
            # interval itself, not N*dt, to cover the full one-second hold.
            required_samples = max(2, math.ceil(stable_duration / step_dt) + 1)
            stable_elapsed = max(0, self._s13_stable_samples - 1) * step_dt
            stable_complete = self._s13_stable_samples >= required_samples
            success = bool(
                geometry["inside_bowl"]
                and moved_from_reset
                and self._s13_lifted_over_rim
                and stable_complete
            )

            opening_radius = float(geometry["opening_radius_m"])
            footprint_progress = float(
                np.clip(
                    1.0
                    - max(
                        0.0,
                        float(geometry["maximum_projected_corner_radius_m"])
                        - opening_radius,
                    )
                    / max(opening_radius, 1e-8),
                    0.0,
                    1.0,
                )
            )
            vertical_progress = float(
                np.clip(
                    float(geometry["fraction_of_vertical_extent_inside_proxy"])
                    / float(geometry["minimum_fraction_inside"]),
                    0.0,
                    1.0,
                )
                if geometry["above_floor"]
                else 0.0
            )
            center_progress = float(
                np.clip(
                    1.0
                    - max(
                        0.0,
                        float(geometry["center_offset_xy_m"])
                        - float(geometry["maximum_center_offset_m"]),
                    )
                    / max(float(geometry["maximum_center_offset_m"]), 1e-8),
                    0.0,
                    1.0,
                )
            )
            movement_progress = float(
                np.clip(displacement / max(minimum_displacement, 1e-8), 0.0, 1.0)
            )
            stability_progress = float(
                np.clip(stable_elapsed / stable_duration, 0.0, 1.0)
            )
            progress = min(
                footprint_progress,
                center_progress,
                vertical_progress,
                movement_progress,
                lift_progress,
                stability_progress,
            )

            if not geometry["projected_footprint_fits"]:
                reason = "marker_projected_footprint_exceeds_bowl_opening"
            elif not geometry["center_within_spec_tolerance"]:
                reason = "marker_center_outside_s13_target_tolerance"
            elif not geometry["above_floor"]:
                reason = "marker_extends_below_bowl_floor"
            elif not geometry["fraction_inside_ok"]:
                reason = "insufficient_marker_extent_inside_bowl_below_rim"
            elif not moved_from_reset:
                reason = "marker_displacement_below_minimum"
            elif not self._s13_lifted_over_rim:
                reason = "marker_never_lifted_clear_of_bowl_rim"
            elif speed is None:
                reason = "measured_marker_linear_velocity_unavailable"
            elif not low_speed:
                reason = "marker_not_stable_by_measured_linear_velocity"
            elif not stable_complete:
                reason = "marker_not_stable_for_required_hold_duration"
            else:
                reason = "marker_inside_bowl_and_stable_for_required_hold"

            return {
                "progress": float(progress),
                "success": success,
                "scoring": "proxy_geometric_staged",
                "approximate": True,
                "reason": reason,
                "stages": {
                    "marker_inside_bowl": {
                        "complete": bool(geometry["inside_bowl"]),
                        **geometry,
                    },
                    "marker_moved_from_reset_pose": {
                        "complete": bool(moved_from_reset),
                        "displacement_m": displacement,
                        "minimum_displacement_m": minimum_displacement,
                    },
                    "marker_lifted_above_bowl_rim": {
                        "complete": bool(self._s13_lifted_over_rim),
                        "current_bottom_world_z_m": item_bottom_world_z,
                        "maximum_bottom_world_z_m": self._s13_max_item_bottom_world_z,
                        "required_bottom_world_z_m": required_item_bottom_world_z,
                        "lift_clearance_m": minimum_lift_clearance,
                        "progress": lift_progress,
                    },
                    "stable_rest": {
                        "complete": bool(stable_complete),
                        "measured_linear_speed_mps": speed,
                        "maximum_linear_speed_mps": maximum_speed,
                        "consecutive_stable_samples": self._s13_stable_samples,
                        "elapsed_seconds": stable_elapsed,
                        "required_seconds": stable_duration,
                        "required_samples": required_samples,
                        "step_dt_seconds": step_dt,
                    },
                },
            }
        elif self.evaluator == "move_then_contain":
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
        elif self.evaluator == "withdraw_and_place_on_plate":
            cfg = self.task.get("proxy_evaluation", {})
            bread_name = str(cfg.get("bread", "bread"))
            toaster_name = str(cfg.get("toaster", "toaster"))
            plate_name = str(cfg.get("plate", "plate"))
            bread = self._position(bread_name)
            toaster = self._position(toaster_name)
            plate = self._position(plate_name)
            if bread is not None and toaster is not None and plate is not None:
                bread_rotation = self._rotation_from_wxyz(
                    self._get_vec(bread_name, "root_quat_w")
                )
                toaster_rotation = self._rotation_from_wxyz(
                    self._get_vec(toaster_name, "root_quat_w")
                )
                bread_half = np.abs(bread_rotation) @ (
                    np.asarray(cfg.get("bread_size_m", [0.10, 0.014, 0.12]), dtype=np.float64) / 2.0
                )
                toaster_half = np.abs(toaster_rotation) @ (
                    np.asarray(cfg.get("toaster_size_m", [0.323, 0.167, 0.191]), dtype=np.float64) / 2.0
                )
                axis_gap = np.maximum(
                    np.abs(bread - toaster) - bread_half - toaster_half, 0.0
                )
                toaster_clearance = float(np.linalg.norm(axis_gap))
                clearance_threshold = float(cfg.get("toaster_clearance_m_min", 0.02))
                clear = toaster_clearance >= clearance_threshold
                clearance_progress = float(
                    np.clip(toaster_clearance / max(clearance_threshold, 1e-8), 0.0, 1.0)
                )

                plate_xy_distance = float(np.linalg.norm((bread - plate)[:2]))
                plate_radius = float(cfg.get("plate_center_xy_radius_m_max", 0.085))
                plate_surface_z = float(plate[2]) + float(
                    cfg.get("plate_surface_z_offset_m", 0.0005)
                )
                bottom_to_surface = float(bread[2] - bread_half[2] - plate_surface_z)
                vertical_tolerance = float(
                    cfg.get("bread_bottom_to_plate_surface_m_abs_max", 0.015)
                )
                xy_on_plate = plate_xy_distance <= plate_radius
                vertically_supported = abs(bottom_to_surface) <= vertical_tolerance
                placed = xy_on_plate and vertically_supported
                xy_progress = float(
                    np.clip(1.0 - plate_xy_distance / max(plate_radius, 1e-8), 0.0, 1.0)
                )
                vertical_progress = float(
                    np.clip(1.0 - abs(bottom_to_surface) / max(vertical_tolerance, 1e-8), 0.0, 1.0)
                )
                placement_progress = xy_progress * vertical_progress
                metric = 0.5 * clearance_progress + 0.5 * placement_progress

                raw_step_dt = getattr(self.env.unwrapped, "step_dt", None)
                if raw_step_dt is None:
                    env_cfg = getattr(self.env.unwrapped, "cfg", None)
                    sim_cfg = getattr(env_cfg, "sim", None)
                    raw_step_dt = (
                        float(sim_cfg.dt) * int(env_cfg.decimation)
                        if sim_cfg is not None and hasattr(env_cfg, "decimation")
                        else 1.0 / 30.0
                    )
                step_dt = max(float(raw_step_dt), 1e-8)
                stable_seconds_required = float(cfg.get("stable_hold_seconds", 1.0))
                stable_steps_required = max(1, math.ceil(stable_seconds_required / step_dt))
                self._u13_stable_steps = (
                    self._u13_stable_steps + 1 if clear and placed else 0
                )
                stable_seconds = self._u13_stable_steps * step_dt
                success = self._u13_stable_steps >= stable_steps_required
                if not clear:
                    reason = "bread_not_clear_of_toaster_proxy"
                elif not placed:
                    reason = "bread_not_supported_by_plate_proxy"
                elif not success:
                    reason = "placement_not_stable_for_required_hold_proxy"
                else:
                    reason = "bread_clear_and_supported_on_plate_for_hold_proxy"
                return {
                    "progress": float(metric),
                    "success": success,
                    "scoring": "proxy_geometric_staged",
                    "approximate": True,
                    "reason": reason,
                    "stages": {
                        "bread_clear_of_toaster": {
                            "complete": clear,
                            "clearance_m": toaster_clearance,
                            "minimum_clearance_m": clearance_threshold,
                            "progress": clearance_progress,
                        },
                        "bread_supported_by_plate": {
                            "complete": placed,
                            "center_xy_distance_m": plate_xy_distance,
                            "maximum_center_xy_distance_m": plate_radius,
                            "bottom_to_surface_m": bottom_to_surface,
                            "maximum_abs_bottom_gap_m": vertical_tolerance,
                            "progress": placement_progress,
                        },
                        "stable_hold": {
                            "elapsed_seconds": stable_seconds,
                            "required_seconds": stable_seconds_required,
                            "complete": self._u13_stable_steps >= stable_steps_required,
                        },
                    },
                    "measured_geometry": {
                        "bread_center_xyz_m": bread.tolist(),
                        "bread_aabb_half_extents_world_m": bread_half.tolist(),
                        "toaster_center_xyz_m": toaster.tolist(),
                        "plate_center_xyz_m": plate.tolist(),
                        "plate_surface_z_m": plate_surface_z,
                    },
                }
        elif (
            self.evaluator in {"contain", "pick_and_place"}
            and self.task.get("proxy_evaluation", {}).get("container")
        ):
            cfg = self.task["proxy_evaluation"]
            container_name = str(cfg["container"])
            item_name = str(cfg.get("item", source))
            container = self._position(container_name)
            item = self._position(item_name)
            container_quat = self._get_vec(container_name, "root_quat_w")
            item_quat = self._get_vec(item_name, "root_quat_w")
            if container is not None and item is not None:
                box_rotation = self._rotation_from_wxyz(container_quat)
                item_rotation = self._rotation_from_wxyz(item_quat)
                relative = box_rotation.T @ (item - container)
                item_size = np.asarray(
                    cfg.get("item_size_m", [0.0, 0.0, 0.0]), dtype=np.float64
                )
                item_half_extents = item_size / 2.0
                item_half_extents_box = np.abs(box_rotation.T @ item_rotation) @ item_half_extents
                inner_size = np.asarray(cfg["container_inner_size_xy_m"], dtype=np.float64)
                inner_half = inner_size / 2.0
                remaining_xy = inner_half - np.abs(relative[:2]) - item_half_extents_box[:2]
                container_size = np.asarray(cfg["container_size_m"], dtype=np.float64)
                floor_top = float(
                    cfg.get("floor_top_relative_z_m", -float(container_size[2]) / 2.0)
                )
                max_above_rim = float(cfg.get("max_item_above_rim_m", 0.0))
                box_half_height = float(container_size[2]) / 2.0
                vertical_ok = bool(
                    relative[2] - item_half_extents_box[2] >= floor_top - 0.005
                    and relative[2] + item_half_extents_box[2] <= box_half_height + max_above_rim
                )
                inside = bool(np.all(remaining_xy >= 0.0) and vertical_ok)
                displacement = float(np.linalg.norm(item - self.initial.get(item_name, item)))
                minimum_displacement = float(cfg.get("minimum_item_displacement_m", 0.0))
                success = inside and displacement >= minimum_displacement
                outside_distance = float(np.linalg.norm(np.minimum(remaining_xy, 0.0)))
                metric = (
                    1.0
                    if inside
                    else float(
                        np.clip(
                            1.0 - outside_distance / max(float(np.linalg.norm(inner_half)), 1e-6),
                            0.0,
                            1.0,
                        )
                    )
                )
                if not inside:
                    reason = "item_not_fully_inside_container_proxy"
                elif not success:
                    reason = "item_inside_but_displacement_below_minimum_proxy"
                else:
                    reason = "item_footprint_inside_container_and_above_floor_proxy"
                score_details["containment_proxy"] = {
                    "inside": inside,
                    "item_center_in_container_xyz_m": relative.tolist(),
                    "item_footprint_margin_xy_m": remaining_xy.tolist(),
                    "item_displacement_m": displacement,
                    "minimum_displacement_m": minimum_displacement,
                    "vertical_ok": vertical_ok,
                }
            else:
                reason = "container_or_item_pose_unavailable"
        elif self.evaluator in {"contain", "place_on_object", "pick_and_place", "remove_and_place"}:
            if current_dist is not None and start_dist is not None:
                metric = np.clip((start_dist - current_dist) / max(start_dist - 0.10, 1e-6), 0.0, 1.0)
                success = bool(current_dist < 0.12 and moved > 0.08)
                reason = "source_target_distance"
        elif self.evaluator == "remove_from_container":
            cfg = self.task.get("proxy_evaluation", {})
            if self.task.get("id") == "U05" and cfg:
                straw_name = str(cfg.get("straw", "straw"))
                cup_name = str(cfg.get("cup", "cup"))
                straw = self._position(straw_name)
                cup = self._position(cup_name)
                straw_q = self._get_vec(straw_name, "root_quat_w")
                initial_cup = self.initial.get(cup_name)
                cup_current = self._position(cup_name)
                if straw is not None and cup is not None and straw_q is not None and initial_cup is not None:
                    rot = self._rotation_from_wxyz(straw_q)
                    long_axis = np.asarray(
                        cfg.get("straw_long_axis_local_xyz", [0.0, 1.0, 0.0]),
                        dtype=np.float64,
                    )
                    long_axis /= max(float(np.linalg.norm(long_axis)), 1e-8)
                    axis = rot @ long_axis
                    half = float(cfg.get("straw_length_m", 0.115)) / 2.0
                    z_extent = half * abs(float(axis[2]))
                    rim_z = float(cup[2]) + float(cfg.get("cup_height_m", 0.105)) / 2.0
                    bottom_z = float(straw[2]) - z_extent
                    top_z = float(straw[2]) + z_extent
                    vertical_clear = bottom_z > rim_z + 0.005
                    a = straw[:2] - half * axis[:2]
                    b = straw[:2] + half * axis[:2]
                    segment = b - a
                    denom = float(np.dot(segment, segment))
                    t = 0.0 if denom < 1e-12 else float(np.clip(np.dot(cup[:2] - a, segment) / denom, 0.0, 1.0))
                    closest = a + t * segment
                    lateral_clear = float(np.linalg.norm(closest - cup[:2])) > float(cfg.get("cup_outer_radius_m", 0.0325)) + float(cfg.get("straw_radius_m", 0.003))
                    above_table = bottom_z >= float(cfg.get("table_surface_z_m", 0.0451)) - 0.004
                    clear = bool(vertical_clear or (lateral_clear and above_table))
                    cup_shift = float(np.linalg.norm(cup_current - initial_cup))
                    cup_stable = cup_shift <= float(cfg.get("cup_displacement_m_max", 0.01))
                    success = clear and cup_stable
                    metric = float(clear and cup_stable)
                    reason = "whole_straw_cleared_rim_and_cup_stable" if success else "straw_still_overlaps_cup_or_cup_moved"
                    score_details["extraction"] = {
                        "whole_straw_clear": clear,
                        "vertical_clearance_m": bottom_z-rim_z,
                        "lateral_clearance": lateral_clear,
                        "cup_displacement_m": cup_shift,
                        "cup_stable": cup_stable,
                    }
                else:
                    metric, success, reason = 0.0, False, "straw_or_cup_pose_unavailable"
            else:
                metric = float(np.clip(moved / 0.25, 0.0, 1.0))
                success = bool(moved > 0.20)
                reason = "source_displacement"
        elif self.task.get("id") == "U18" and self.evaluator == "articulation_target":
            toaster_name, lever_name = "toaster", "toaster_lever"
            toaster, lever = self._position(toaster_name), self._position(lever_name)
            initial_t = self.initial.get(toaster_name)
            initial_l = self.initial.get(lever_name)
            if toaster is not None and lever is not None and initial_t is not None and initial_l is not None:
                press = float(initial_l[2] - lever[2])
                body_shift = float(np.linalg.norm(toaster-initial_t))
                threshold = float(self.task.get("proxy_evaluation", {}).get("lever_travel_m_min", 0.025))
                success = press >= threshold and body_shift <= 0.01
                metric = float(np.clip(press/max(threshold,1e-8),0.0,1.0))
                reason = "prismatic_lever_travel_and_fixed_toaster_proxy"
                score_details["lever"] = {"downward_travel_m":press,"required_m":threshold,"toaster_displacement_m":body_shift}
            else:
                metric, success, reason = 0.0, False, "lever_or_toaster_pose_unavailable"
        elif self.task.get("id") == "U19" and self.evaluator == "place_at_height":
            block, shelf = self._position("yellow_block"), self._position("multi_level_platform")
            initial_block = self.initial.get("yellow_block")
            if block is not None and shelf is not None and initial_block is not None:
                shelf_q = self._get_vec("multi_level_platform", "root_quat_w")
                shelf_r = self._rotation_from_wxyz(shelf_q)
                local = shelf_r.T @ (block-shelf)
                block_size = np.asarray(self.task.get("proxy_evaluation", {}).get("block_size_m", [0.06,0.045,0.03]))
                shelf_size = np.asarray(self.task.get("proxy_evaluation", {}).get("shelf_size_m", [0.18,0.30,0.20]))
                top = shelf_size[2]/2
                on_top = (abs(local[0]) <= (shelf_size[0]+block_size[0])/2 and
                          abs(local[1]) <= (shelf_size[1]+block_size[1])/2 and
                          abs(local[2] - (top+block_size[2]/2)) <= 0.018)
                moved = float(np.linalg.norm(block-initial_block))
                vel = self._get_vec("yellow_block", "root_lin_vel_w")
                max_speed = float(self.task.get("proxy_evaluation", {}).get("maximum_linear_speed_mps", 0.03))
                stable = vel is not None and float(np.linalg.norm(vel)) <= max_speed
                min_moved=float(self.task.get("proxy_evaluation",{}).get("minimum_displacement_m",.08))
                placement_sample = bool(on_top and moved > min_moved and stable)
                raw_step_dt = getattr(self.env.unwrapped, "step_dt", None)
                if raw_step_dt is None:
                    env_cfg = getattr(self.env.unwrapped, "cfg", None)
                    sim_cfg = getattr(env_cfg, "sim", None)
                    raw_step_dt = (
                        float(sim_cfg.dt) * int(env_cfg.decimation)
                        if sim_cfg is not None and hasattr(env_cfg, "decimation")
                        else 1.0 / 30.0
                    )
                step_dt = max(float(raw_step_dt), 1e-8)
                stable_duration = float(self.task.get("proxy_evaluation", {}).get("stable_hold_seconds", 0.5))
                required_steps = max(2, math.ceil(stable_duration / step_dt) + 1)
                self._u19_stable_steps = self._u19_stable_steps + 1 if placement_sample else 0
                stable_complete = self._u19_stable_steps >= required_steps
                success = bool(stable_complete)
                metric = float(on_top) * min(self._u19_stable_steps / required_steps, 1.0)
                reason = "block_on_highest_shelf_surface_proxy" if success else "block_not_stably_on_highest_surface"
                score_details["placement"] = {"block_in_shelf_frame_m":local.tolist(),"on_top":on_top,"displacement_m":moved,"stable":stable,"stable_samples":self._u19_stable_steps,"required_samples":required_steps,"stable_hold_seconds":stable_duration}
            else:
                metric, success, reason = 0.0, False, "block_or_shelf_pose_unavailable"
        elif self.task.get("id") == "U09" and self.evaluator == "attach_to_surface":
            cfg=self.task.get("proxy_evaluation",{})
            magnet_name=str(cfg.get("magnet","gray_magnet_candidate"))
            tray_name=str(cfg.get("tray","tray"))
            magnet=self._position(magnet_name);tray=self._position(tray_name)
            initial=self.initial.get(magnet_name)
            velocity=self._get_vec(magnet_name,"root_lin_vel_w")
            if magnet is not None and tray is not None and initial is not None:
                rot=self._rotation_from_wxyz(self._get_vec(tray_name,"root_quat_w"))
                local=rot.T@(magnet-tray)
                half=np.asarray([.135,.100,.025])
                closest=np.maximum(np.minimum(local,half),-half)
                gap=float(np.linalg.norm(local-closest))
                speed=math.inf if velocity is None else float(np.linalg.norm(velocity))
                contact=gap<=float(cfg.get("maximum_contact_gap_m",.018))
                stable=speed<=float(cfg.get("maximum_linear_speed_mps",.025))
                moved=float(np.linalg.norm(magnet-initial))
                success=bool(contact and stable and moved>.03)
                metric=float(np.clip(1.0-gap/.15,0,1))
                reason="magnet_in_contact_with_tray_and_stable_proxy" if success else "magnet_not_retained_on_tray"
                score_details["magnetic_contact"]={"surface_gap_m":gap,"contact":contact,"speed_mps":speed,"stable":stable,"displacement_m":moved}
            else:
                metric,success,reason=0.0,False,"magnet_or_tray_pose_unavailable"
        elif self.task.get("id") == "U12" and self.evaluator == "articulated_tool_interaction":
            paper=self._position("papers");initial=self.initial.get("papers")
            released=bool(getattr(self.env.unwrapped,"_clip_released",False))
            moved=0.0 if paper is None or initial is None else float(np.linalg.norm(paper-initial))
            angles=getattr(self.env.unwrapped,"_clip_handle_angles_rad",[])
            squeezed=len(angles)==2 and all(abs(float(a))<math.radians(38) for a in angles)
            success=bool(squeezed and released and moved>=.06)
            metric=float(np.clip(moved/.06,0,1))
            reason="handles_pinched_and_clamped_papers_released" if success else "clip_not_pinched_or_papers_not_released"
            score_details["clip"]={"handle_angles_rad":angles,"squeezed":squeezed,"paper_displacement_m":moved,"joint_released":released}
        elif self.task.get("id") == "U15" and self.evaluator == "pour_or_dispense":
            bread=self._position("bread")
            count=0;on_bread=[]
            if bread is not None:
                for i in range(16):
                    name=f"mustard_bead_{i:02d}"
                    pos=self._position(name)
                    if pos is None: continue
                    vel=self._get_vec(name,"root_lin_vel_w")
                    bead_radius = float(self.task.get("proxy_evaluation", {}).get("bead_radius_m", .003))
                    bread_half_height = float(self.task.get("proxy_evaluation", {}).get("bread_size_m", [.24,.16,.05])[2]) / 2.0
                    expected_center_z = float(bread[2]) + bread_half_height + bead_radius
                    bread_half_x = float(self.task.get("proxy_evaluation", {}).get("bread_size_m", [.24,.16,.05])[0]) / 2.0
                    bread_half_y = float(self.task.get("proxy_evaluation", {}).get("bread_size_m", [.24,.16,.05])[1]) / 2.0
                    landed = (
                        abs(float(pos[2]) - expected_center_z) <= .009
                        and abs(float(pos[0] - bread[0])) <= bread_half_x - bead_radius
                        and abs(float(pos[1] - bread[1])) <= bread_half_y - bead_radius
                        and vel is not None
                        and float(np.linalg.norm(vel)) < .035
                    )
                    on_bread.append(landed)
                    count+=int(landed)
            required=int(self.task.get("proxy_evaluation", {}).get("stable_bead_count_min",8))
            success=count>=required
            metric=float(np.clip(count/required,0,1))
            reason="discrete_droplet_count_on_bread_proxy" if success else "insufficient_stable_droplets_on_bread"
            score_details["dispensing"]={"stable_droplets_on_bread":count,"required":required,"emitted":int(getattr(self.env.unwrapped,"_mustard",{}).get("emitted",0)),"model":"discrete_rigid_droplets_not_fluid"}
        elif self.task.get("id") == "U07" and self.evaluator == "multi_object_sort":
            cfg=self.task.get("proxy_evaluation",{})
            pairs=cfg.get("item_to_vessels",{})
            half=np.asarray(cfg.get("item_half_extents_m",[.016,.013,.011]),dtype=float)
            completed=[]; margins=[]
            for item_name,vessel_names in pairs.items():
                item=self._position(item_name)
                item_vel=self._get_vec(item_name,"root_lin_vel_w")
                item_done=False; best_margin=-math.inf
                if item is not None:
                    for vessel_name in vessel_names:
                        vessel=self._position(vessel_name)
                        if vessel is None: continue
                        dims=np.asarray(cfg.get("vessel_size_by_name_m",{}).get(vessel_name,[.12,.105,.04]),dtype=float)
                        radius=min(dims[:2])*float(cfg.get("bowl_inner_radius_scale",.38))
                        radial=float(np.linalg.norm(item[:2]-vessel[:2]))
                        floor=float(vessel[2])+float(cfg.get("floor_relative_z_m",-.012))
                        rim=float(vessel[2])+float(cfg.get("rim_relative_z_m",.020))
                        inside=radial+float(np.linalg.norm(half[:2])) < radius and item[2]-half[2]>=floor-.004 and item[2]+half[2]<=rim+.003
                        best_margin=max(best_margin,radius-radial-float(np.linalg.norm(half[:2])))
                        speed=math.inf if item_vel is None else float(np.linalg.norm(item_vel))
                        item_done=item_done or (inside and speed<=float(cfg.get("maximum_linear_speed_mps",.025)))
                completed.append(item_done);margins.append(best_margin)
            success=bool(completed and all(completed))
            metric=float(sum(completed)/max(len(completed),1))
            reason="all_pieces_stably_inside_color_matched_vessel_proxy" if success else "one_or_more_pieces_outside_matching_vessel"
            score_details["sorting"]={"piece_inside_and_stable":completed,"footprint_margin_m":margins,"yellow_vessel_choice":"either"}
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
            **score_details,
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


def _close_task_env(env: Any) -> None:
    """Close a task without entering Isaac Lab's STOP-event render loop.

    STOP handling is useful during an interactive run, but a deliberate task
    teardown must return so that the next environment can be created.
    """
    sim = env.unwrapped.sim
    sim._disable_app_control_on_stop_handle = True
    stop_handle = getattr(sim, "_app_control_on_stop_handle", None)
    if stop_handle is not None:
        stop_handle.unsubscribe()
        sim._app_control_on_stop_handle = None
    # Stop before the next SimulationContext installs its own STOP handler;
    # otherwise replacing the old playing stage can invoke the new handler.
    sim.stop()
    env.close()
    # Clearing SimulationContext does not remove prims from the USD stage.
    # The next task otherwise tries to spawn lights/robot at occupied paths.
    from isaacsim.core.utils.stage import create_new_stage

    create_new_stage()


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
    layout_ids_csv: str | None = None,
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
    is_multi_task = task.lower() in {"all", "seen", "unseen"} or "," in task
    if layout_ids_csv is not None:
        layout_ids = [int(item.strip()) for item in layout_ids_csv.split(",") if item.strip()]
        if not layout_ids or any(item < 0 for item in layout_ids):
            raise ValueError("layout_ids_csv must be a comma-separated list of non-negative layout ids")
        if len(layout_ids) != len(set(layout_ids)):
            raise ValueError("layout_ids_csv must not contain duplicate layout ids")
    else:
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
        run_dir = output / ("matrix" if is_multi_task else task.upper()) / run_id
        run_dir.mkdir(parents=True, exist_ok=True)
        results: list[dict[str, Any]] = []

        with torch.no_grad():
            for task_spec in task_specs:
                for current_layout in layout_ids:
                    env_cfg = parse_env_cfg("APPENDIX_G", device=args_cli.device, num_envs=1, use_fabric=True)
                    env_cfg.sim.device = args_cli.device
                    task_id = str(task_spec["id"]).upper()
                    env_cfg.set_task(task_id, current_layout, scene_dir=scene_dir)
                    step_dt = float(env_cfg.sim.dt) * int(env_cfg.decimation)
                    native_episode_limit = int(
                        round(float(env_cfg.episode_length_s) / step_dt)
                    )
                    episode_limit = (
                        int(max_steps) if max_steps is not None else native_episode_limit
                    )
                    if episode_limit < 1:
                        raise ValueError("max_steps must be a positive integer")
                    # ManagerBasedRLEnv resets timed-out environments inside
                    # env.step() before returning its observation. Keep that
                    # reset just beyond our rollout cap so the final score and
                    # joint-state diagnostics describe the terminal scene,
                    # not a silently reset initial state.
                    env_cfg.episode_length_s = (episode_limit + 1) * step_dt
                    env = gym.make("APPENDIX_G", cfg=env_cfg)
                    task_run_dir = run_dir / task_id / f"layout{current_layout}"
                    task_run_dir.mkdir(parents=True, exist_ok=True)
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
                            joint_position_start = (
                                obs["policy"]["arm_joint_pos"][0].detach().cpu().numpy().copy()
                            )
                            joint_position_end = joint_position_start.copy()
                            first_action_targets: list[dict[str, Any]] = []
                            for _ in tqdm(
                                range(episode_limit),
                                desc=f"{task_id} layout={current_layout} episode={episode + 1}/{episodes}",
                            ):
                                result = client.infer(obs, str(task_spec["instruction"]))
                                frames.append(result["viz"])
                                action = torch.as_tensor(result["action"], dtype=torch.float32).reshape(1, -1)
                                if len(first_action_targets) < 8:
                                    first_action_targets.append(
                                        {
                                            "step": steps,
                                            "joint_position_target": action[0, :7].cpu().tolist(),
                                            "gripper_target": float(action[0, 7].item()),
                                        }
                                    )
                                obs, _, terminated, truncated, _ = env.step(action)
                                joint_position_end = (
                                    obs["policy"]["arm_joint_pos"][0].detach().cpu().numpy().copy()
                                )
                                last_score = evaluator.score()
                                steps += 1
                                if terminated or truncated:
                                    break
                            client.reset()

                            video_path = task_run_dir / f"episode_{episode:02d}.mp4"
                            if not frames:
                                raise RuntimeError(
                                    f"No rendered frames were captured for {task_id} "
                                    f"layout {current_layout} episode {episode}"
                                )
                            mediapy.write_video(video_path, frames, fps=15)
                            if not video_path.is_file() or video_path.stat().st_size == 0:
                                raise RuntimeError(f"Rollout video was not written: {video_path}")
                            result_row = {
                                "task_id": task_id,
                                "split": task_spec["split"],
                                "instruction": task_spec["instruction"],
                                "layout_id": current_layout,
                                "episode": episode,
                                "steps": steps,
                                "video": str(video_path),
                                "action_diagnostics": {
                                    "joint_position_start_rad": joint_position_start.tolist(),
                                    "joint_position_end_rad": joint_position_end.tolist(),
                                    "joint_position_max_abs_change_rad": float(
                                        np.max(np.abs(joint_position_end - joint_position_start))
                                    ),
                                    "first_action_targets": first_action_targets,
                                },
                                **last_score,
                            }
                            results.append(result_row)
                            (run_dir / "results.json").write_text(json.dumps(results, indent=2))
                            gallery_path = _write_run_gallery(run_dir, results)
                            catalog_path = _write_output_catalog(output)
                            archive_root = PRIVATE_DATA_ROOT / "runs"
                            archive_catalog = (
                                catalog_path
                                if output.resolve() == archive_root.resolve()
                                else _write_output_catalog(archive_root)
                            )
                            print(f"[appendix-g-eval] video: {video_path}", flush=True)
                            print(f"[appendix-g-eval] gallery: {gallery_path}", flush=True)
                            print(f"[appendix-g-eval] output catalog: {catalog_path}", flush=True)
                            print(f"[appendix-g-eval] archive catalog: {archive_catalog}", flush=True)
                            print(json.dumps(result_row, indent=2), flush=True)
                    finally:
                        _close_task_env(env)

        print(f"[appendix-g-eval] results: {run_dir / 'results.json'}", flush=True)
    except BaseException:
        # Kit fast shutdown can terminate before Python prints an exception
        # propagated through finally. Preserve the actual failure in the log.
        traceback.print_exc()
        sys.stderr.flush()
        raise
    finally:
        simulation_app.close()


if __name__ == "__main__":
    tyro.cli(main)
