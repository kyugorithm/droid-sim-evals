#!/usr/bin/env python3
"""Render an Appendix G proxy scene without connecting to DreamZero inference."""

from __future__ import annotations

import argparse
import gc
import hashlib
import html
import json
import os
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def _write_review_index(
    output_dir: Path,
    task_ids: list[str],
    task_specs: dict[str, dict],
    references_root: Path,
) -> Path:
    """Create a private side-by-side paper-reference and camera-preview gallery."""
    output_dir = output_dir.resolve()
    references_root = references_root.resolve()

    def image_cell(path: Path, alt: str, css_class: str = "") -> str:
        if not path.is_file():
            return '<div class="missing">not rendered</div>'
        rel = os.path.relpath(path.resolve(), output_dir).replace(os.sep, "/")
        return (
            f'<a href="{html.escape(rel, quote=True)}">'
            f'<img class="{html.escape(css_class, quote=True)}" '
            f'src="{html.escape(rel, quote=True)}" alt="{html.escape(alt, quote=True)}">'
            "</a>"
        )

    rows = []
    for task_id in task_ids:
        spec = task_specs.get(task_id, {})
        instruction = html.escape(str(spec.get("instruction", "")))
        ref_group = "paper_refs" if task_id.startswith("S") else "paper_refs_task_mapped"
        reference = references_root / ref_group / f"{task_id}.png"
        rows.append(
            "<section class=\"task\">"
            f"<header><h2>{html.escape(task_id)}</h2><p>{instruction}</p></header>"
            f"<div><h3>Paper image</h3>{image_cell(reference, task_id + ' paper reference', 'reference')}</div>"
            f"<div><h3>Layout 0 · inferred comparison view</h3>{image_cell(output_dir / task_id / 'layout0' / 'reference_cam.png', task_id + ' comparison camera', 'preview')}</div>"
            f"<div><h3>Layout 0 · unchanged fixed view</h3>{image_cell(output_dir / task_id / 'layout0' / 'review_cam.png', task_id + ' fixed camera', 'preview')}</div>"
            f"<details><summary>Original policy cameras / optional layout 1</summary>{image_cell(output_dir / task_id / 'layout0' / 'contact_sheet.png', task_id + ' policy cameras')}{image_cell(output_dir / task_id / 'layout1' / 'review_cam.png', task_id + ' layout 1')}</details>"
            "</section>"
        )
    document = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Appendix G scene pose review</title>
<style>
body{font:15px system-ui,sans-serif;margin:20px;background:#f3f4f6;color:#16181d}
h1{margin:0 0 6px}.note{max-width:1100px;margin:0 0 18px;color:#454b55}
.task{display:grid;grid-template-columns:1fr 1fr 1fr;gap:12px;align-items:start;background:white;padding:12px;margin:12px 0;border:1px solid #d9dde3;border-radius:8px}.task header,.task details{grid-column:1/-1}
.task h2{margin:2px 0 6px}.task h3{font-size:13px;margin:0 0 6px;color:#555}
.task p{margin:0;font-size:13px}.task img{display:block;max-width:100%;height:auto;border:1px solid #ddd;background:#eee}
.reference,.preview{width:100%;height:320px!important;object-fit:contain}.missing{padding:28px 8px;background:#eee;color:#666;text-align:center}
@media(max-width:700px){.task{grid-template-columns:1fr}}
</style></head><body>
<h1>Appendix G scene pose review</h1>
<p class="note">Three columns: paper / inferred close comparison / unchanged fixed camera. Framing is NOT calibrated to the paper. Rendered does not mean visually approved, physically validated, or policy success. <a href="batch_status.json">Batch status and hashes</a></p>
<p class="note">Paper thumbnails are from <a href="https://arxiv.org/html/2602.15922v1#appendix.G">DreamZero Appendix G</a>. The simulator scenes are approximate local reconstructions: exact paper poses/assets are not published. The fixed tabletop review camera is for visual comparison only and is not a policy input; adjacent panels show the original three DROID camera views. No policy inference was run for this gallery.</p>
""" + "\n".join(rows) + "\n</body></html>\n"
    index_path = output_dir / "index.html"
    index_path.write_text(document, encoding="utf-8")
    return index_path


def _check_graphics() -> None:
    local_icd = REPO_ROOT / "configs/nvidia_icd.local.json"
    example_icd = REPO_ROOT / "configs/nvidia_icd.example.json"
    os.environ.setdefault("VK_ICD_FILENAMES", str(local_icd if local_icd.is_file() else example_icd))
    subprocess.run(
        [sys.executable, str(REPO_ROOT / "scripts/check_nvidia_vulkan.py")],
        check=True,
    )


def _to_rgb(image):
    import numpy as np

    if hasattr(image, "detach"):
        image = image.detach().cpu().numpy()
    image = np.asarray(image)
    if image.ndim == 4 and image.shape[0] == 1:
        image = image[0]
    if image.ndim != 3:
        raise ValueError(f"Expected HxWxC camera image, got {image.shape}")
    if image.shape[-1] == 4:
        image = image[..., :3]
    if image.dtype != np.uint8:
        if image.size and float(np.nanmax(image)) <= 1.0:
            image = image * 255.0
        image = np.nan_to_num(image, nan=0.0, posinf=255.0, neginf=0.0)
        image = np.clip(image, 0, 255).astype(np.uint8)
    return image


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--task", action="append", dest="tasks",
        help="Task id; may be repeated to preview several tasks in one Isaac session.",
    )
    parser.add_argument(
        "--all-tasks", action="store_true",
        help="Preview every task in configs/appendix_g_tasks.yaml.",
    )
    parser.add_argument(
        "--index-only", action="store_true",
        help="Regenerate the gallery from already rendered task images without starting Isaac Sim.",
    )
    parser.add_argument(
        "--layout", action="append", type=int, choices=[0, 1], dest="layouts",
        help="Layout id; may be repeated to preview both paired initial states.",
    )
    parser.add_argument("--scene-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--quality-review", action="store_true",
                        help="Inspection-only high quality preset; not an evaluation default.")
    parser.add_argument(
        "--paper-refs-root",
        type=Path,
        default=Path(os.environ.get("PRIVATE_DATA_ROOT", Path.home() / ".local/share/.private"))
        / "runs/scene_previews",
        help="Private directory containing paper_refs/ and paper_refs_task_mapped/.",
    )
    parser.add_argument(
        "--settle-steps", type=int, default=0,
        help="Optional policy-free physics settling steps while holding the initial robot joints.",
    )
    parser.add_argument('--cutting-probe', choices=['valid','miss'], default=None,
                        help='Scripted U03 prototype joint-release test, NOT policy inference.')
    args, _ = parser.parse_known_args()
    if args.index_only:
        import yaml

        with (REPO_ROOT / "configs/appendix_g_tasks.yaml").open() as handle:
            manifest_tasks = yaml.safe_load(handle)["tasks"]
        task_specs = {str(row["id"]).upper(): row for row in manifest_tasks}
        rendered_task_ids = [
            task_id for task_id in task_specs
            if any(
                (args.output / task_id / f"layout{layout_id}" / "review_cam.png").is_file()
                for layout_id in (0, 1)
            )
        ]
        index_path = _write_review_index(
            args.output, rendered_task_ids, task_specs, args.paper_refs_root
        )
        print(f"[scene-preview] wrote review gallery for {len(rendered_task_ids)} rendered tasks: {index_path}")
        return

    from isaaclab.app import AppLauncher

    AppLauncher.add_app_launcher_args(parser)
    args, _ = parser.parse_known_args()
    args.enable_cameras = True
    args.headless = True

    _check_graphics()
    launcher = AppLauncher(args)
    simulation_app = launcher.app
    env = None
    try:
        import gymnasium as gym
        import torch
        from PIL import Image, ImageDraw

        import sim_evals.environments  # noqa: F401
        from isaaclab_tasks.utils import parse_env_cfg

        if args.settle_steps < 0:
            raise ValueError("--settle-steps must be non-negative")
        if args.all_tasks and args.tasks:
            raise ValueError("Use either --all-tasks or repeated --task, not both")
        layout_ids = args.layouts or [0]
        task_specs = {}
        task_ids = [task.upper() for task in (args.tasks or ["S01"])]
        import yaml

        with (REPO_ROOT / "configs/appendix_g_tasks.yaml").open() as handle:
            task_manifest = yaml.safe_load(handle)
        manifest_tasks = task_manifest["tasks"]
        task_specs = {str(row["id"]).upper(): row for row in manifest_tasks}
        if args.all_tasks:
            task_ids = [str(row["id"]).upper() for row in manifest_tasks]

        for task_id in task_ids:
            for layout_id in layout_ids:
                env_cfg = parse_env_cfg(
                    "APPENDIX_G", device=args.device, num_envs=1, use_fabric=True
                )
                env_cfg.sim.device = args.device
                env_cfg.set_task(task_id, layout_id, scene_dir=args.scene_dir)
                reference_camera = env_cfg.add_reference_camera(
                    task_specs[task_id].get("objects", []),
                    elevation_degrees=75.0 if task_id == "S15" else 28.0,
                )
                if args.quality_review:
                    # This affects this inspection process globally, including
                    # its policy-view screenshots, but never evaluation defaults.
                    env_cfg.sim.render.rendering_mode = "quality"
                    env_cfg.sim.render.antialiasing_mode = "TAA"
                    env_cfg.sim.render.enable_shadows = True
                    env_cfg.sim.render.enable_ambient_occlusion = True
                    env_cfg.sim.render.enable_reflections = True
                    env_cfg.sim.render.enable_global_illumination = True
                    env_cfg.sim.render.enable_translucency = True
                    env_cfg.sim.render.samples_per_pixel = 8
                    env_cfg.scene.reference_cam.width = 2560
                    env_cfg.scene.reference_cam.height = 1920
                env = gym.make("APPENDIX_G", cfg=env_cfg)
                try:
                    # Match the evaluator's two reset/render cycles so materials
                    # and camera buffers populate, without creating a policy client.
                    obs, _ = env.reset()
                    obs, _ = env.reset()
                    if args.quality_review:
                        # Warm up temporal rendering without moving physics.
                        for _ in range(32):
                            env.unwrapped.sim.render()
                        for sensor in env.unwrapped.scene.sensors.values():
                            sensor.update(env.unwrapped.physics_dt, force_recompute=True)

                    output_dir = args.output / task_id / f"layout{layout_id}"
                    output_dir.mkdir(parents=True, exist_ok=True)
                    if args.cutting_probe:
                        from sim_evals.environments.cutting_physics import cutting_step
                        if not hasattr(env.unwrapped, '_cut_gate'):
                            raise RuntimeError('Cutting probe requires opt-in cutting USD')
                        import numpy as np
                        import imageio.v2 as imageio
                        core = env.unwrapped
                        hold = torch.cat((obs['policy']['arm_joint_pos'].clone(),
                                          obs['policy']['gripper_pos'].clone()),dim=-1)
                        knife = core.scene['knife']
                        from pxr import UsdPhysics
                        import omni.usd
                        # Test fixture only: kinematic prescribed blade, not a
                        # learned grasp. Prevent free-fall between commands.
                        knife_prim=omni.usd.get_context().get_stage().GetPrimAtPath('/World/envs/env_0/scene/knife')
                        UsdPhysics.RigidBodyAPI(knife_prim).CreateKinematicEnabledAttr(True)
                        frames = []
                        trajectory = []
                        for z in np.linspace(.035,-.023,30):
                            state = knife.data.root_state_w.clone()
                            base = core.scene['bread_half_a'].data.root_pos_w[0].clone()
                            state[0,:3] = base + torch.tensor(
                                [0.0 if args.cutting_probe=='valid' else .06,0.,float(z)+.012],
                                device=state.device)
                            state[0,3:7] = torch.tensor([1.,0.,0.,0.],device=state.device)
                            state[0,7:13] = 0
                            knife.write_root_pose_to_sim(state[:,:7])
                            core.scene.update(core.physics_dt)
                            cutting_step(core)
                            obs, _, _, _, _ = env.step(hold)
                            frames.append(_to_rgb(core.scene.sensors['review_cam'].data.output['rgb'][0]))
                            trajectory.append({'edge_z_command':float(z),'released':core._cut_gate.cut,
                                               'armed':core._cut_gate.armed,'sample':core._cut_last_sample})
                        # Remove the tool, then apply equal/opposite velocities:
                        # joined halves should resist separation, cut halves should not.
                        state=knife.data.root_state_w.clone();state[0,2]=.5;state[0,7:13]=0
                        knife.write_root_pose_to_sim(state[:,:7])
                        for name,sign in [('bread_half_a',-1),('bread_half_b',1)]:
                            body=core.scene[name]
                            vel=torch.zeros_like(body.data.root_vel_w);vel[0,0]=sign*.30
                            body.write_root_velocity_to_sim(vel)
                        for _ in range(20):
                            obs, _, _, _, _ = env.step(hold)
                            frames.append(_to_rgb(core.scene.sensors['review_cam'].data.output['rgb'][0]))
                        a=core.scene['bread_half_a'].data.root_pos_w[0].detach().cpu().numpy()
                        b=core.scene['bread_half_b'].data.root_pos_w[0].detach().cpu().numpy()
                        separation=float(np.linalg.norm(a-b))
                        expected=args.cutting_probe=='valid'
                        passed=(core._cut_gate.cut==expected and
                                (separation>.02 if expected else separation<.01))
                        result={'probe':args.cutting_probe,'passed':passed,'released':core._cut_gate.cut,
                                'root_separation_m':separation,'events':core._cut_events,
                                'trajectory':trajectory,'policy_inference_calls':0,
                                'limitations':'scripted knife poses; filtered blade/bread contact; no fracture forces'}
                        (output_dir/'cutting_probe.json').write_text(json.dumps(result,indent=2))
                        imageio.mimsave(output_dir/'cutting_probe.mp4',frames,fps=10,
                                         codec='libx264',macro_block_size=2)
                        print('[cutting-probe] '+json.dumps(result),flush=True)
                        if not passed:
                            raise RuntimeError('Cutting physical separation probe failed')
                    if args.settle_steps:
                        initial_joints = obs["policy"]["arm_joint_pos"].clone()
                        initial_gripper = obs["policy"]["gripper_pos"].clone()
                        hold_action = torch.cat((initial_joints, initial_gripper), dim=-1)
                        task_spec = task_specs.get(task_id)
                        if task_spec is None:
                            raise ValueError(f"Unknown Appendix G task: {task_id}")
                        # Scene overrides may rename manifest objects (e.g.
                        # hat -> fedora_hat). Read actually registered bodies,
                        # otherwise an empty dict falsely resembles a test.
                        object_names = list(env.unwrapped.scene.rigid_objects)
                        if not object_names:
                            raise RuntimeError("Settling test has no registered rigid bodies")

                        def object_positions():
                            positions = {}
                            for name in object_names:
                                try:
                                    positions[name] = (
                                        env.unwrapped.scene[name].data.root_pos_w[0]
                                        .detach().cpu().tolist()
                                    )
                                except (KeyError, TypeError, AttributeError):
                                    pass
                            return positions

                        before = object_positions()
                        steps_completed = 0
                        for _ in range(args.settle_steps):
                            obs, _, terminated, truncated, _ = env.step(hold_action)
                            steps_completed += 1
                            if terminated or truncated:
                                break
                        after = object_positions()
                        with (output_dir / "physics_settle.json").open("w") as handle:
                            json.dump(
                                {
                                    "task_id": task_id,
                                    "layout_id": layout_id,
                                    "steps_requested": args.settle_steps,
                                    "steps_completed": steps_completed,
                                    "objects_before_xyz_m": before,
                                    "objects_after_xyz_m": after,
                                },
                                handle,
                                indent=2,
                            )
                        print(
                            f"[scene-preview] {task_id}/layout{layout_id} policy-free settle: "
                            f"{before} -> {after}",
                            flush=True,
                        )

                    keys = {
                        "external_cam": "external_cam",
                        "external_cam_2": "external_cam_2",
                        "wrist_cam": "wrist_cam",
                    }
                    images = []
                    for filename, observation_key in keys.items():
                        rgb = _to_rgb(obs["policy"][observation_key])
                        image = Image.fromarray(rgb, mode="RGB")
                        image.save(output_dir / f"{filename}.png")
                        images.append((filename, image.copy()))

                    review_cam = env.unwrapped.scene.sensors["review_cam"]
                    review_rgb = _to_rgb(review_cam.data.output["rgb"])
                    Image.fromarray(review_rgb, mode="RGB").save(
                        output_dir / "review_cam.png"
                    )
                    reference_rgb = _to_rgb(env.unwrapped.scene.sensors["reference_cam"].data.output["rgb"])
                    Image.fromarray(reference_rgb, mode="RGB").save(output_dir / "reference_cam.png")
                    evidence = {
                        "task_id": task_id, "layout_id": layout_id,
                        "scene_sha256": hashlib.sha256(Path(env_cfg.scene_path).read_bytes()).hexdigest(),
                        "reference_camera": reference_camera,
                        "inference_calls": 0, "visual_review": "pending",
                        "render_preset": "quality_review" if args.quality_review else "default",
                        "inspection_only": True,
                        "physics_validation": "pending" if not args.settle_steps else "settling_only",
                    }
                    (output_dir / "render_evidence.json").write_text(json.dumps(evidence, indent=2) + "\n")

                    thumb_w, thumb_h = 480, 360
                    sheet = Image.new(
                        "RGB", (thumb_w * len(images), thumb_h + 28), (25, 25, 25)
                    )
                    draw = ImageDraw.Draw(sheet)
                    for index, (label, image) in enumerate(images):
                        image.thumbnail((thumb_w, thumb_h))
                        x = index * thumb_w + (thumb_w - image.width) // 2
                        y = 28 + (thumb_h - image.height) // 2
                        sheet.paste(image, (x, y))
                        draw.text(
                            (index * thumb_w + 8, 7), label, fill=(245, 245, 245)
                        )
                    contact_path = output_dir / "contact_sheet.png"
                    sheet.save(contact_path)
                    print(f"[scene-preview] saved: {contact_path}", flush=True)
                finally:
                    # Drop camera observations before closing the environment.
                    # They retain render buffers that can otherwise keep the
                    # previous stage alive when the next task/layout is opened.
                    if "obs" in locals():
                        del obs
                    if "rgb" in locals():
                        del rgb
                    if "image" in locals():
                        del image
                    if "images" in locals():
                        del images
                    if "sheet" in locals():
                        del sheet
                    if "draw" in locals():
                        del draw
                    env.close()
                    env = None
                    gc.collect()
                    simulation_app.update()
        index_path = _write_review_index(
            args.output, task_ids, task_specs, args.paper_refs_root
        )
        print(f"[scene-preview] wrote review gallery: {index_path}", flush=True)
        print("[scene-preview] DreamZero inference calls: 0", flush=True)
    finally:
        if env is not None:
            env.close()
        simulation_app.close()


if __name__ == "__main__":
    main()
