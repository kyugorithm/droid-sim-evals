#!/usr/bin/env python3
"""Render an Appendix G proxy scene without connecting to DreamZero inference."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


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
    parser.add_argument("--task", default="S01")
    parser.add_argument("--layout", type=int, default=0, choices=[0, 1])
    parser.add_argument("--scene-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
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

        env_cfg = parse_env_cfg(
            "APPENDIX_G", device=args.device, num_envs=1, use_fabric=True
        )
        env_cfg.sim.device = args.device
        env_cfg.set_task(args.task.upper(), args.layout, scene_dir=args.scene_dir)
        env = gym.make("APPENDIX_G", cfg=env_cfg)
        # Match the evaluator's two reset/render cycles so materials and camera
        # buffers are populated, but deliberately do not create a policy client.
        obs, _ = env.reset()
        obs, _ = env.reset()

        output_dir = args.output / args.task.upper() / f"layout{args.layout}"
        output_dir.mkdir(parents=True, exist_ok=True)
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

        thumb_w, thumb_h = 480, 360
        sheet = Image.new("RGB", (thumb_w * len(images), thumb_h + 28), (25, 25, 25))
        draw = ImageDraw.Draw(sheet)
        for index, (label, image) in enumerate(images):
            image.thumbnail((thumb_w, thumb_h))
            x = index * thumb_w + (thumb_w - image.width) // 2
            y = 28 + (thumb_h - image.height) // 2
            sheet.paste(image, (x, y))
            draw.text((index * thumb_w + 8, 7), label, fill=(245, 245, 245))
        contact_path = output_dir / "contact_sheet.png"
        sheet.save(contact_path)
        print(f"[scene-preview] saved: {contact_path}", flush=True)
        print("[scene-preview] DreamZero inference calls: 0", flush=True)
    finally:
        if env is not None:
            env.close()
        simulation_app.close()


if __name__ == "__main__":
    main()
