#!/usr/bin/env python3
"""Build deterministic USD scenes for the DreamZero Appendix G task proxies.

This is intentionally a small, reproducible scene generator. It creates the
tabletop, task objects, and the two paired layouts. Reviewed task overrides
provide explicit poses and procedural templates; selected props use textured
YCB scans with simpler collision proxies. S02 uses a project-authored,
perforated turquoise basket visual with separate container collision proxies.

Run ``scripts/prepare_ycb_assets.sh`` once to verify and extract the small YCB
visuals. Use ``scripts/build_appendix_g_scenes_b300.sh`` for Isaac Sim's
bundled ``pxr`` bindings and shared libraries. USD authoring does not require
DreamZero inference; it starts Kit only to author the stages.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import shutil
from pathlib import Path
from typing import Any

import yaml

try:
    from appendix_g_basket_v7 import draw_blue_basket
except ModuleNotFoundError:
    from scripts.appendix_g_basket_v7 import draw_blue_basket


# Approximate local proxy dimensions aligned to the public sim-evals
# scene1.usd table bounds: x=[0.1986, 0.8986], y=[-0.4779, 0.5221],
# tabletop z_max=0.0451 m. This is the smoke-scene frame, not Appendix G data.
TABLE_TOP_CENTER_Z = 0.025
TABLE_TOP_SIZE = (0.70, 1.00, 0.04)
TABLE_SURFACE_Z = TABLE_TOP_CENTER_Z + TABLE_TOP_SIZE[2] / 2.0
TABLE_LEG_HEIGHT = 0.66
TABLE_LEG_BOTTOM_Z = TABLE_SURFACE_Z - TABLE_TOP_SIZE[2] - TABLE_LEG_HEIGHT
# The DROID camera/robot rig is rooted at the robot base. The work surface
# therefore belongs in front of the robot, not centered on its base (which
# caused the robot and table to occlude the objects in the first proxy render).
TABLE_CENTER_X = 0.55
TABLE_CENTER_Y = 0.022
PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCENE_OVERRIDE_PATHS = (
    PROJECT_ROOT / "assets/appendix_g/task_specs/group_a/scene_overrides.yaml",
    PROJECT_ROOT / "assets/appendix_g/task_specs/group_b_s11_s20/scene_overrides.yaml",
    PROJECT_ROOT / "assets/appendix_g/task_specs/group_c/scene_overrides.yaml",
    PROJECT_ROOT / "assets/appendix_g/task_specs/group_d/scene_overrides.yaml",
)
PRIVATE_DATA_ROOT = Path(
    os.environ.get("PRIVATE_DATA_ROOT", Path.home() / ".local/share/.private")
)
SIM_EVALS_ROOT = Path(
    os.environ.get("SIM_EVALS_ROOT", PROJECT_ROOT)
).resolve()
OUTPUT_DEFAULT = Path(
    os.environ.get("APPENDIX_G_SCENE_DIR", PRIVATE_DATA_ROOT / "appendix_g_scenes")
)
MANIFEST_DEFAULT = PROJECT_ROOT / "configs/appendix_g_tasks.yaml"
BACKGROUND_HDRI = SIM_EVALS_ROOT / "assets/backgrounds/billiard_hall_4k.hdr"
SCISSOR_OBJ = (
    PROJECT_ROOT / "assets/third_party/ycb/037_scissors/google_16k/textured.obj"
).resolve()
SCISSOR_TEXTURE = SCISSOR_OBJ.with_name("texture_map.png")
YCB_UNPACKED = PROJECT_ROOT / "assets/third_party/ycb/unpacked"
YCB_MODEL_FILES = {
    "apple": ("013_apple", "YCB 013 Apple"),
    "lemon": ("014_lemon", "YCB 014 Lemon"),
    "bowl": ("024_bowl", "YCB 024 Bowl"),
    "mug": ("025_mug", "YCB 025 Mug"),
    "pan": ("027_skillet", "YCB 027 Skillet"),
    "knife": ("032_knife", "YCB 032 Knife"),
    "spatula": ("033_spatula", "YCB 033 Spatula"),
    "marker": ("040_large_marker", "YCB 040 Large Marker"),
}
S02_BLUE_BOX_GLB = (
    PROJECT_ROOT / "assets/third_party/innerscene/stackable-storage-bin.glb"
).resolve()


COLORS = {
    "apple": (0.75, 0.05, 0.03),
    "lemon": (0.95, 0.80, 0.05),
    "marker": (0.05, 0.20, 0.80),
    "small_marker": (0.10, 0.55, 0.90),
    "blue_box": (0.025, 0.48, 0.66),
    "bowl": (0.82, 0.82, 0.84),
    "mug": (0.90, 0.90, 0.92),
    "white_cup": (0.95, 0.95, 0.95),
    "cup": (0.80, 0.90, 0.95),
    "mug": (0.88, 0.88, 0.84),
    "pan": (0.12, 0.12, 0.14),
    "plate": (0.96, 0.96, 0.96),
    "bread": (0.75, 0.42, 0.16),
    "hat": (0.12, 0.08, 0.05),
    "grapes": (0.35, 0.08, 0.50),
    "green_grapes": (0.08, 0.45, 0.12),
    "yellow_block": (0.95, 0.75, 0.05),
    "magnet": (0.80, 0.04, 0.04),
    "batteries": (0.25, 0.25, 0.28),
    "vegetables": (0.10, 0.55, 0.12),
    "towel": (0.15, 0.55, 0.75),
    "burger": (0.70, 0.35, 0.10),
    "orange": (0.96, 0.38, 0.035),
}


def _safe_id(value: str) -> str:
    return "".join(ch if ch.isalnum() or ch == "_" else "_" for ch in value)


def _stable_number(task_id: str, layout_id: int) -> float:
    digest = hashlib.sha256(f"{task_id}:{layout_id}".encode()).digest()
    return (int.from_bytes(digest[:2], "big") / 65535.0) - 0.5


def _load_scene_override(task_id: str) -> dict[str, Any] | None:
    """Read a task's reviewed local scene specification, if one exists."""
    for path in SCENE_OVERRIDE_PATHS:
        if not path.is_file():
            continue
        with path.open(encoding="utf-8") as handle:
            manifest = yaml.safe_load(handle) or {}
        tasks = manifest.get("scene_tasks", manifest.get("tasks", {}))
        if isinstance(tasks, list):
            task_map = {
                str(item.get("id", "")).upper(): item
                for item in tasks
                if isinstance(item, dict)
            }
        else:
            task_map = {str(key).upper(): value for key, value in tasks.items()}
        if task_id.upper() in task_map:
            return task_map[task_id.upper()]
    return None


def _scene_object_specs(
    task_id: str, layout_id: int
) -> tuple[list[str], dict[str, dict[str, Any]], dict[str, tuple[float, float, float]]]:
    """Normalize the independent task-spec formats for the scene builder."""
    task_spec = _load_scene_override(task_id)
    if task_spec is None:
        return [], {}, {}
    objects_value = task_spec.get("objects", {})
    if isinstance(objects_value, list):
        object_specs = {
            str(item["id"]): dict(item)
            for item in objects_value
            if isinstance(item, dict) and item.get("id")
        }
    else:
        object_specs = {
            str(name): dict(item)
            for name, item in objects_value.items()
            if isinstance(item, dict)
        }

    layout_value = task_spec.get("layouts", {})
    selected_layout = layout_value.get(layout_id, layout_value.get(str(layout_id)))
    if selected_layout is None:
        selected_layout = layout_value.get(f"layout_{layout_id}", {})
    if isinstance(selected_layout, dict) and "initial_poses" in selected_layout:
        selected_layout = selected_layout["initial_poses"]
    poses: dict[str, tuple[float, float, float]] = {}
    for name, object_spec in object_specs.items():
        pose_value = None
        if isinstance(selected_layout, dict):
            pose_value = selected_layout.get(name)
        if pose_value is None:
            by_layout = object_spec.get(
                "layout_positions_robot_frame_m",
                object_spec.get("initial_pose_by_layout", {}),
            )
            if isinstance(by_layout, dict):
                pose_value = by_layout.get(layout_id, by_layout.get(str(layout_id)))
        if pose_value is None:
            pose_value = object_spec.get("initial_position_robot_frame_m")

        if isinstance(pose_value, dict):
            position = pose_value.get("position_m")
            euler = pose_value.get(
                "rpy_deg", pose_value.get("euler_xyz_deg", [0.0, 0.0, 0.0])
            )
            pose_value = [*(position or []), *euler]
        if pose_value is None:
            continue
        pose = [float(value) for value in pose_value]
        if len(pose) < 3:
            raise ValueError(f"Scene override {task_id}/{name} needs x/y/z position")
        poses[name] = (pose[0], pose[1], pose[2])
        if len(pose) >= 6:
            object_spec["_pose_rpy_deg"] = pose[3:6]
        elif "yaw_deg" in object_spec:
            object_spec["_pose_rpy_deg"] = [0.0, 0.0, float(object_spec["yaw_deg"])]
        else:
            object_spec["_pose_rpy_deg"] = [0.0, 0.0, 0.0]
    missing = set(object_specs) - set(poses)
    if missing:
        raise ValueError(
            f"Scene override {task_id} layout {layout_id} lacks poses for {sorted(missing)}"
        )
    return list(object_specs), object_specs, poses


def _object_size(name: str, task_id: str | None = None) -> tuple[float, float, float]:
    # S01 uses the approximate physical scale visible in the Appendix G photo,
    # rather than the large generic boxes used by the initial smoke proxy.
    if task_id == "S01":
        if name == "cup":
            return (0.095, 0.095, 0.10)
        if name == "marker":
            return (0.016, 0.125, 0.016)
        if name == "scissors":
            # Bounds of YCB 037_scissors Google 16k scan, in metres.
            return (0.096, 0.202, 0.016)
    if task_id == "S02":
        if name == "blue_box":
            # Scaled from the public CC0 Innerscene stack-bin model. Its
            # original 35.4 x 43 x 22.4 cm proportions are kept in the
            # tabletop plane and compressed slightly in height to match the
            # paper image's small open container.
            return (0.18, 0.148, 0.08)
        if name == "marker":
            return (0.016, 0.125, 0.016)
        if name == "scissors":
            return (0.096, 0.202, 0.016)
    if name in {"marker", "small_marker", "pencil", "straw", "wire", "toaster_lever"}:
        return (0.025, 0.18, 0.025)
    if name == "orange":
        return (0.075, 0.075, 0.075)
    if name in {"apple", "lemon", "burger", "croissant", "magnet", "hidden_object"}:
        return (0.10, 0.10, 0.10)
    if name in {"bowl", "pan", "plate", "matching_bowls", "mug", "white_cup", "cup_set"}:
        return (0.20, 0.20, 0.10)
    if name == "cup":
        # Deliberately generous proxy dimensions so the proxy marker can fit
        # inside; these are not measurements of the paper's real props.
        return (0.22, 0.22, 0.12)
    if name in {"bread", "towel", "papers", "drawstring_bag", "gloves"}:
        return (0.24, 0.16, 0.05)
    if name in {"knife", "spatula", "scissors"}:
        return (0.28, 0.06, 0.04)
    if name in {"blocks", "colored_objects", "yellow_block", "batteries", "nuts"}:
        return (0.10, 0.10, 0.10)
    if name in {"drawer", "tray", "blue_box", "matching_hole_board", "hole_box", "multi_level_platform"}:
        return (0.30, 0.22, 0.10)
    if name in {"toaster", "oven", "keyboard", "tripod", "basket"}:
        return (0.38, 0.24, 0.16)
    if name in {"mustard_bottle", "bottle"}:
        return (0.08, 0.08, 0.22)
    return (0.16, 0.16, 0.12)


def _shape_for(name: str) -> str:
    if name in {"apple", "lemon", "orange", "burger", "croissant", "magnet", "hidden_object"}:
        return "sphere"
    if any(token in name for token in ("bowl", "cup", "mug", "plate", "pan", "mustard_bottle", "battery")):
        return "cylinder"
    if any(token in name for token in ("tomato", "broccoli", "grape", "orange", "fruit", "object")):
        return "sphere"
    return "cube"


def _default_template_for_object(name: str, task_id: str) -> str | None:
    """Use recognizable silhouettes for common object names if a spec omits one."""
    if name in {"toaster", "oven"}:
        return "toaster_v1"
    if name in {"pencil", "pen_distractor", "small_pen"}:
        return "pencil_v1"
    if name in {"marker", "marker_distractor", "small_marker"}:
        return "marker_white_red_v1"
    if name in {"white_cup", "receiver_cup_a", "receiver_cup_b", "cup_set"}:
        return "paper_cup_v1"
    if name in {"red_bowl", "blue_bowl", "yellow_bowl", "green_bowl"}:
        return "shallow_bowl_v1"
    if name in {"tripod", "papers", "binder_clip", "drawstring_bag", "wire"}:
        return {
            "tripod": "tripod_v1",
            "papers": "paper_stack_v1",
            "binder_clip": "binder_clip_v1",
            "drawstring_bag": "drawstring_pouch_v1",
            "wire": "cable_coil_v1",
        }[name]
    if name in {"mustard_bottle", "croissant", "orange"}:
        return {
            "mustard_bottle": "mustard_bottle_v1",
            "croissant": "croissant_v1",
            "orange": "orange_v1",
        }[name]
    if name in {"grapes", "green_grapes", "red_grapes_distractor", "purple_grapes_distractor"}:
        return "grape_cluster_v1"
    if name in {"bread", "toast_bread"}:
        return "toast_slice_v1"
    if name.startswith("bread_half"):
        return "bread_loaf_v1"
    if name in {"keyboard", "keyboard_base"}:
        return "keyboard_v1"
    if name in {"sorter_frame_and_board", "matching_hole_board", "hole_box"}:
        return "shape_sorter_box_v1"
    if name in {"nut", "bar_magnet", "magnet"}:
        return "magnet_bar_v1"
    if name == "bowl" and task_id == "S20":
        return "shallow_bowl_v1"
    return None


def _object_xy(
    task_id: str,
    index: int,
    object_count: int,
    layout_id: int,
    jitter: float,
    object_name: str | None = None,
) -> tuple[float, float]:
    """Return a deterministic, non-overlapping XY slot inside the smoke table.

    S01 and S02 use image-guided object arrangements. Other tasks use size-safe
    slots because their objects can be as large as a toaster or basket. These
    placements are local assumptions, not paper poses.
    """
    if task_id == "S01" and object_count >= 3:
        # Approximate the photo's composition: cup in the middle, scissors on
        # its image-left, and marker on image-right. A policy-free camera check
        # established that increasing world Y appears on image-left in the
        # primary DROID exterior view.
        slots_by_name = {
            "cup": (0.44, TABLE_CENTER_Y),
            "scissors": (0.53, TABLE_CENTER_Y + 0.22),
            "marker": (0.53, TABLE_CENTER_Y - 0.22),
        }
        if object_name not in slots_by_name:
            raise ValueError(f"No image-reference S01 placement for {object_name!r}")
        x, y = slots_by_name[object_name]
        if layout_id == 1:
            x += 0.035
            y -= 0.075
        return x + 0.01 * jitter, y + 0.01 * jitter
    elif task_id == "S02" and object_count >= 3:
        # Appendix G(a), task 2 reference: blue box near the middle/back;
        # blue-handled scissors and red-capped marker sit nearer the front,
        # to image-left and image-right respectively. Positive X points away
        # from the robot, so the earlier ordering (box at X=.44, tools at
        # X=.53) accidentally put the box in front of both tools. These remain
        # visual estimates, not recovered paper poses.
        slots_by_name = {
            "blue_box": (0.60, TABLE_CENTER_Y),
            "scissors": (0.46, TABLE_CENTER_Y + 0.18),
            "marker": (0.46, TABLE_CENTER_Y - 0.18),
        }
        if object_name not in slots_by_name:
            raise ValueError(f"No image-reference S02 placement for {object_name!r}")
        x, y = slots_by_name[object_name]
        if layout_id == 1:
            x += 0.035
            y -= 0.075
        return x + 0.01 * jitter, y + 0.01 * jitter
    elif task_id == "S01" and object_count >= 2:
        # Backwards-compatible placement if a local task manifest omits the
        # visible distractor object.
        slots = ((0.44, TABLE_CENTER_Y), (0.53, TABLE_CENTER_Y - 0.22))
        layout_shift_y = 0.0
    elif task_id == "S11":
        slots = ((TABLE_CENTER_X - 0.18, TABLE_CENTER_Y),)
        layout_shift_y = 0.08
    elif task_id == "S16":
        slots = ((TABLE_CENTER_X + 0.18, TABLE_CENTER_Y),)
        layout_shift_y = 0.08
    elif task_id == "S17":
        slots = ((TABLE_CENTER_X, TABLE_CENTER_Y + 0.18),)
        layout_shift_y = 0.08
    elif object_count <= 1:
        slots = ((TABLE_CENTER_X, TABLE_CENTER_Y),)
        layout_shift_y = 0.08
    elif object_count == 2:
        slots = ((0.41, -0.18), (0.69, 0.18))
        layout_shift_y = 0.08
    else:
        slots = ((0.41, -0.30), (0.69, 0.30), (0.55, 0.0))
        layout_shift_y = 0.08

    if index >= len(slots):
        raise ValueError(f"No placement slot for {object_count} objects in {task_id}")
    x, y = slots[index]
    # Small per-task offsets decorrelate otherwise identical scenes without
    # pushing the largest proxy boxes outside the tabletop.
    x += 0.02 * jitter
    y += 0.02 * jitter
    if layout_id == 1:
        y += layout_shift_y
    return x, y


def _define_open_container(
    stage: Any,
    root_path: str,
    size: tuple[float, float, float],
    color: tuple[float, float, float],
    *,
    hide_collision_geometry: bool = False,
) -> None:
    """Create a stable open-top container proxy with convex box colliders."""
    from pxr import UsdGeom

    height = size[2]
    wall = min(0.012, min(size[0], size[1]) * 0.075)
    floor = min(0.012, height * 0.15)
    wall_height = height - floor
    half_x, half_y = size[0] / 2.0, size[1] / 2.0

    # A flat floor and four unrotated convex walls keep the container open
    # while avoiding a dense compound collider that was unstable in PhysX.
    proxy_paths = [
        (f"{root_path}/geometry/floor", (size[0], size[1], floor), (0.0, 0.0, -height / 2.0 + floor / 2.0)),
        (f"{root_path}/geometry/wall_x_neg", (wall, size[1], wall_height), (-half_x + wall / 2.0, 0.0, floor / 2.0)),
        (f"{root_path}/geometry/wall_x_pos", (wall, size[1], wall_height), (half_x - wall / 2.0, 0.0, floor / 2.0)),
        (f"{root_path}/geometry/wall_y_neg", (size[0] - 2.0 * wall, wall, wall_height), (0.0, -half_y + wall / 2.0, floor / 2.0)),
        (f"{root_path}/geometry/wall_y_pos", (size[0] - 2.0 * wall, wall, wall_height), (0.0, half_y - wall / 2.0, floor / 2.0)),
    ]
    for path, box_size, pos in proxy_paths:
        prim = _define_box(stage, path, box_size, pos, color)
        if hide_collision_geometry:
            UsdGeom.Imageable(prim).CreateVisibilityAttr().Set(UsdGeom.Tokens.invisible)


def _define_lattice_basket_visual(
    stage: Any, root_path: str, size: tuple[float, float, float]
) -> None:
    """Draw a recognizable open pink lattice basket around hidden box colliders."""
    sx, sy, sz = size
    wall = 0.008
    half_x, half_y, half_z = sx / 2.0, sy / 2.0, sz / 2.0
    pink = (0.78, 0.12, 0.31)
    dark_pink = (0.40, 0.045, 0.13)
    _define_box(
        stage,
        f"{root_path}/visual/basket_floor",
        (sx - 2.0 * wall, sy - 2.0 * wall, 0.006),
        (0.0, 0.0, -half_z + 0.003),
        dark_pink,
        collision=False,
    )
    rail_zs = (-half_z + 0.018, 0.0, half_z - 0.012)
    for level, z in enumerate(rail_zs):
        for side_y in (-1.0, 1.0):
            _define_box(
                stage,
                f"{root_path}/visual/rail_y_{level}_{'n' if side_y < 0 else 'p'}",
                (sx, wall, wall),
                (0.0, side_y * (half_y - wall / 2.0), z),
                pink,
                collision=False,
            )
        for side_x in (-1.0, 1.0):
            _define_box(
                stage,
                f"{root_path}/visual/rail_x_{level}_{'n' if side_x < 0 else 'p'}",
                (wall, sy - 2.0 * wall, wall),
                (side_x * (half_x - wall / 2.0), 0.0, z),
                pink,
                collision=False,
            )

    slat_height = sz - 0.035
    slat_z = -half_z + 0.018 + slat_height / 2.0
    for index in range(1, 6):
        x = -half_x + sx * index / 6.0
        for side_y in (-1.0, 1.0):
            _define_box(
                stage,
                f"{root_path}/visual/slat_y_{index}_{'n' if side_y < 0 else 'p'}",
                (wall, wall, slat_height),
                (x, side_y * (half_y - wall / 2.0), slat_z),
                pink,
                collision=False,
            )
    for index in range(1, 5):
        y = -half_y + sy * index / 5.0
        for side_x in (-1.0, 1.0):
            _define_box(
                stage,
                f"{root_path}/visual/slat_x_{index}_{'n' if side_x < 0 else 'p'}",
                (wall, wall, slat_height),
                (side_x * (half_x - wall / 2.0), y, slat_z),
                pink,
                collision=False,
            )


def _define_curved_banana_visual(
    stage: Any, root_path: str, size: tuple[float, float, float]
) -> None:
    """Create a small curved yellow fruit from overlapping smooth segments."""
    from pxr import Gf, UsdGeom

    length = size[0]
    radius = min(size[1], size[2]) * 0.34
    segments = 9
    for index in range(segments):
        t = index / (segments - 1)
        x = -length / 2.0 + length * t
        y = 0.012 * math.sin(math.pi * t)
        z = 0.008 * math.sin(math.pi * t)
        taper = 0.78 + 0.22 * math.sin(math.pi * t)
        sphere = UsdGeom.Sphere.Define(stage, f"{root_path}/visual/segment_{index}")
        sphere.CreateRadiusAttr(1.0)
        sphere.AddTranslateOp().Set(Gf.Vec3d(x, y, z))
        sphere.AddScaleOp().Set(Gf.Vec3f(radius * 1.35, radius * taper, radius * taper))
        sphere.CreateDisplayColorAttr([Gf.Vec3f(0.96, 0.72, 0.08)])


def _define_tape_outline(
    stage: Any, root_path: str, size: tuple[float, float, float]
) -> None:
    """Add four non-colliding dark tape strips to mark a tabletop rectangle."""
    sx, sy, sz = size
    tape = 0.006
    color = (0.035, 0.035, 0.04)
    for side_y in (-1.0, 1.0):
        _define_box(
            stage,
            f"{root_path}/visual/tape_y_{'n' if side_y < 0 else 'p'}",
            (sx, tape, sz),
            (0.0, side_y * (sy / 2.0 - tape / 2.0), 0.0),
            color,
            collision=False,
        )
    for side_x in (-1.0, 1.0):
        _define_box(
            stage,
            f"{root_path}/visual/tape_x_{'n' if side_x < 0 else 'p'}",
            (tape, sy - 2.0 * tape, sz),
            (side_x * (sx / 2.0 - tape / 2.0), 0.0, 0.0),
            color,
            collision=False,
        )


def _rounded_rectangle_loop(
    width: float,
    depth: float,
    radius: float,
    z: float,
    *,
    segments_per_corner: int = 6,
) -> list[tuple[float, float, float]]:
    """Return a counter-clockwise rounded-rectangle contour in the XY plane."""
    half_x, half_y = width / 2.0, depth / 2.0
    radius = min(radius, half_x, half_y)
    corners = (
        (half_x - radius, -half_y + radius, -90.0),
        (half_x - radius, half_y - radius, 0.0),
        (-half_x + radius, half_y - radius, 90.0),
        (-half_x + radius, -half_y + radius, 180.0),
    )
    points = []
    for center_x, center_y, start_deg in corners:
        for step in range(segments_per_corner):
            angle = math.radians(start_deg + 90.0 * step / segments_per_corner)
            points.append((
                center_x + radius * math.cos(angle),
                center_y + radius * math.sin(angle),
                z,
            ))
    return points


def _define_s02_blue_box_visual(
    stage: Any,
    root_path: str,
    size: tuple[float, float, float],
) -> None:
    """Build the small turquoise perforated basket seen in the S02 photo."""
    sx, sy, sz = size
    half_x, half_y, half_z = sx / 2.0, sy / 2.0, sz / 2.0
    wall = min(sx, sy) * 0.035
    rail = min(sx, sy) * 0.025
    blue = (0.025, 0.47, 0.57)
    blue_light = (0.035, 0.55, 0.65)
    blue_dark = (0.018, 0.34, 0.43)

    def bar(label: str, dimensions: tuple[float, float, float], position: tuple[float, float, float], color: tuple[float, float, float] = blue) -> None:
        _define_box(
            stage, f"{root_path}/visual/lattice/{label}", dimensions,
            position, color, collision=False,
        )

    # Perforated floor: the hidden collision floor remains continuous, while
    # the render makes the open plastic grid visible through the basket.
    bottom_z = -half_z + rail / 2.0
    floor_count = 7
    for index in range(floor_count):
        t = index / (floor_count - 1)
        y = -half_y + wall + t * (2.0 * (half_y - wall))
        bar(f"floor_x_{index}", (sx - 2.0 * wall, rail, rail), (0.0, y, bottom_z), blue_dark)
        x = -half_x + wall + t * (2.0 * (half_x - wall))
        bar(f"floor_y_{index}", (rail, sy - 2.0 * wall, rail), (x, 0.0, bottom_z), blue)

    wall_bottom = -half_z + rail
    wall_top = half_z - rail
    wall_height = wall_top - wall_bottom
    wall_center = (wall_bottom + wall_top) / 2.0
    horizontal_rows = 4
    for row in range(horizontal_rows):
        z = wall_bottom + (row + 0.5) * wall_height / horizontal_rows
        row_color = blue_light if row % 2 == 0 else blue
        bar(f"long_wall_y_neg_rail_{row}", (sx - 2.0 * wall, wall, rail), (0.0, -half_y + wall / 2.0, z), row_color)
        bar(f"long_wall_y_pos_rail_{row}", (sx - 2.0 * wall, wall, rail), (0.0, half_y - wall / 2.0, z), row_color)
        bar(f"end_wall_x_neg_rail_{row}", (wall, sy - 2.0 * wall, rail), (-half_x + wall / 2.0, 0.0, z), row_color)
        bar(f"end_wall_x_pos_rail_{row}", (wall, sy - 2.0 * wall, rail), (half_x - wall / 2.0, 0.0, z), row_color)

    for index in range(7):
        x = -half_x + wall + index * (sx - 2.0 * wall) / 6.0
        bar(f"long_wall_y_neg_upright_{index}", (rail, wall, wall_height), (x, -half_y + wall / 2.0, wall_center), blue)
        bar(f"long_wall_y_pos_upright_{index}", (rail, wall, wall_height), (x, half_y - wall / 2.0, wall_center), blue_light)
    for index in range(6):
        y = -half_y + wall + index * (sy - 2.0 * wall) / 5.0
        bar(f"end_wall_x_neg_upright_{index}", (wall, rail, wall_height), (-half_x + wall / 2.0, y, wall_center), blue_light)
        bar(f"end_wall_x_pos_upright_{index}", (wall, rail, wall_height), (half_x - wall / 2.0, y, wall_center), blue)

    # Thick rolled lip, slightly brighter than the lattice below it.
    rim_z = half_z - rail / 2.0
    bar("rim_y_neg", (sx, wall * 1.35, rail), (0.0, -half_y + wall / 2.0, rim_z), blue_light)
    bar("rim_y_pos", (sx, wall * 1.35, rail), (0.0, half_y - wall / 2.0, rim_z), blue_light)
    bar("rim_x_neg", (wall * 1.35, sy - 2.0 * wall, rail), (-half_x + wall / 2.0, 0.0, rim_z), blue_light)
    bar("rim_x_pos", (wall * 1.35, sy - 2.0 * wall, rail), (half_x - wall / 2.0, 0.0, rim_z), blue_light)


def _define_s07_wire_strainer_visual(
    stage: Any, root_path: str, size: tuple[float, float, float]
) -> None:
    """Build a small open wire-mesh strainer instead of a skillet scan."""
    sx, sy, sz = size
    radius = min(sx, sy) * 0.46
    wire_radius = min(sx, sy) * 0.009
    steel = (0.48, 0.53, 0.55)
    steel_dark = (0.31, 0.35, 0.37)
    profile = (
        (radius * 0.27, -sz * 0.48),
        (radius * 0.43, -sz * 0.34),
        (radius * 0.60, -sz * 0.18),
        (radius * 0.78, sz * 0.04),
        (radius * 0.92, sz * 0.45),
    )

    # Concentric horizontal wires and bowed uprights form a shallow basket.
    for index, (ring_radius, z) in enumerate(profile):
        _define_torus(
            stage, f"{root_path}/visual/mesh/ring_{index}",
            (0.0, 0.0, z), ring_radius, wire_radius,
            steel if index % 2 == 0 else steel_dark,
            ring_segments=48, tube_segments=6,
        )
    uprights = 24
    for index in range(uprights):
        angle = 2.0 * math.pi * index / uprights
        points = [
            (ring_radius * math.cos(angle), ring_radius * math.sin(angle), z)
            for ring_radius, z in profile
        ]
        for segment, (start, end) in enumerate(zip(points, points[1:])):
            _define_cylinder_segment(
                stage, f"{root_path}/visual/mesh/upright_{index}_{segment}",
                start, end, wire_radius * 0.72,
                steel if index % 3 else steel_dark,
            )

    # A sparse crossed-wire floor and two small loop handles match the compact
    # perforated metal object in the paper thumbnail without adding a skillet.
    bottom_radius = profile[0][0]
    floor_offsets = (("negative", -0.55), ("center", 0.0), ("positive", 0.55))
    for label, offset in floor_offsets:
        y = bottom_radius * offset
        half_chord = math.sqrt(max(0.0, bottom_radius**2 - y**2))
        _define_cylinder_segment(
            stage, f"{root_path}/visual/mesh/floor_wire_x_{label}",
            (-half_chord, y, profile[0][1]),
            (half_chord, y, profile[0][1]),
            wire_radius * 0.65, steel_dark,
        )
        x = bottom_radius * offset
        half_chord = math.sqrt(max(0.0, bottom_radius**2 - x**2))
        _define_cylinder_segment(
            stage, f"{root_path}/visual/mesh/floor_wire_y_{label}",
            (x, -half_chord, profile[0][1]),
            (x, half_chord, profile[0][1]),
            wire_radius * 0.65, steel_dark,
        )
    handle_z = sz * 0.22
    handle_y = radius * 0.22
    for side in (-1.0, 1.0):
        side_label = "negative" if side < 0 else "positive"
        inner_x = side * radius * 0.90
        outer_x = side * (radius + sz * 0.18)
        loop = (
            (inner_x, -handle_y, handle_z),
            (outer_x, -handle_y, handle_z),
            (outer_x, handle_y, handle_z),
            (inner_x, handle_y, handle_z),
        )
        for index, (start, end) in enumerate(zip(loop, loop[1:])):
            _define_cylinder_segment(
                stage, f"{root_path}/visual/handle_{side_label}_{index}",
                start, end, wire_radius * 0.8, steel,
            )


def _define_mesh(
    stage: Any,
    path: str,
    points: list[tuple[float, float, float]],
    face_counts: list[int],
    face_indices: list[int],
    color: tuple[float, float, float],
) -> Any:
    from pxr import Gf, UsdGeom

    mesh = UsdGeom.Mesh.Define(stage, path)
    mesh.CreatePointsAttr([Gf.Vec3f(*point) for point in points])
    mesh.CreateFaceVertexCountsAttr(face_counts)
    mesh.CreateFaceVertexIndicesAttr(face_indices)
    mesh.CreateSubdivisionSchemeAttr(UsdGeom.Tokens.none)
    mesh.CreateDisplayColorAttr([Gf.Vec3f(*color)])
    return mesh.GetPrim()


def _define_frustum_side(
    stage: Any,
    path: str,
    bottom_radius: float,
    top_radius: float,
    height: float,
    color: tuple[float, float, float],
    *,
    segments: int = 32,
) -> Any:
    """Create an open-ended tapered cylindrical surface for the paper cup."""
    import math

    points: list[tuple[float, float, float]] = []
    for radius, z in ((bottom_radius, -height / 2.0), (top_radius, height / 2.0)):
        points.extend(
            (radius * math.cos(2.0 * math.pi * i / segments),
             radius * math.sin(2.0 * math.pi * i / segments), z)
            for i in range(segments)
        )
    indices: list[int] = []
    for i in range(segments):
        nxt = (i + 1) % segments
        indices.extend((i, nxt, segments + nxt, segments + i))
    return _define_mesh(stage, path, points, [4] * segments, indices, color)


def _define_disk(
    stage: Any,
    path: str,
    radius: float,
    z: float,
    color: tuple[float, float, float],
    *,
    segments: int = 32,
) -> Any:
    import math

    points = [(0.0, 0.0, z)] + [
        (radius * math.cos(2.0 * math.pi * i / segments),
         radius * math.sin(2.0 * math.pi * i / segments), z)
        for i in range(segments)
    ]
    indices: list[int] = []
    for i in range(segments):
        indices.extend((0, i + 1, ((i + 1) % segments) + 1))
    return _define_mesh(stage, path, points, [3] * segments, indices, color)


def _define_torus(
    stage: Any,
    path: str,
    center: tuple[float, float, float],
    major_radius: float,
    tube_radius: float,
    color: tuple[float, float, float],
    *,
    ring_segments: int = 24,
    tube_segments: int = 8,
) -> Any:
    """Build a lightweight horizontal torus mesh for cup rims/scissor loops."""
    import math

    points: list[tuple[float, float, float]] = []
    for i in range(ring_segments):
        u = 2.0 * math.pi * i / ring_segments
        for j in range(tube_segments):
            v = 2.0 * math.pi * j / tube_segments
            radius = major_radius + tube_radius * math.cos(v)
            points.append((
                center[0] + radius * math.cos(u),
                center[1] + radius * math.sin(u),
                center[2] + tube_radius * math.sin(v),
            ))

    indices: list[int] = []
    for i in range(ring_segments):
        for j in range(tube_segments):
            a = i * tube_segments + j
            b = ((i + 1) % ring_segments) * tube_segments + j
            c = ((i + 1) % ring_segments) * tube_segments + ((j + 1) % tube_segments)
            d = i * tube_segments + ((j + 1) % tube_segments)
            indices.extend((a, b, c, d))
    return _define_mesh(
        stage, path, points, [4] * (ring_segments * tube_segments), indices, color
    )


def _define_cylinder(
    stage: Any,
    path: str,
    radius: float,
    height: float,
    pos: tuple[float, float, float],
    color: tuple[float, float, float],
    *,
    axis: str = "Z",
    collision: bool = False,
) -> Any:
    from pxr import Gf, UsdGeom, UsdPhysics

    cylinder = UsdGeom.Cylinder.Define(stage, path)
    cylinder.CreateRadiusAttr(radius)
    cylinder.CreateHeightAttr(height)
    cylinder.CreateAxisAttr(axis)
    cylinder.AddTranslateOp().Set(Gf.Vec3d(*pos))
    cylinder.CreateDisplayColorAttr([Gf.Vec3f(*color)])
    if collision:
        UsdPhysics.CollisionAPI.Apply(cylinder.GetPrim())
    return cylinder.GetPrim()


def _define_cylinder_segment(
    stage: Any,
    path: str,
    start: tuple[float, float, float],
    end: tuple[float, float, float],
    radius: float,
    color: tuple[float, float, float],
) -> None:
    """Create a short visual-only cylinder between two local points."""
    from pxr import Gf, UsdGeom

    vector = Gf.Vec3d(*(end[i] - start[i] for i in range(3)))
    length = vector.GetLength()
    if length <= 1.0e-6:
        return
    midpoint = tuple((start[i] + end[i]) * 0.5 for i in range(3))
    cylinder = UsdGeom.Cylinder.Define(stage, path)
    cylinder.CreateRadiusAttr(radius)
    cylinder.CreateHeightAttr(length)
    cylinder.CreateAxisAttr("Z")
    cylinder.AddTranslateOp().Set(Gf.Vec3d(*midpoint))
    orientation = Gf.Rotation(Gf.Vec3d(0.0, 0.0, 1.0), vector).GetQuat()
    cylinder.AddOrientOp().Set(
        Gf.Quatf(orientation.GetReal(), Gf.Vec3f(orientation.GetImaginary()))
    )
    cylinder.CreateDisplayColorAttr([Gf.Vec3f(*color)])


def _define_oriented_box(
    stage: Any,
    path: str,
    size: tuple[float, float, float],
    pos: tuple[float, float, float],
    color: tuple[float, float, float],
    *,
    rotation_axis: tuple[float, float, float],
    angle_deg: float,
) -> None:
    import math

    from pxr import Gf, UsdGeom

    axis = Gf.Vec3f(*rotation_axis)
    axis.Normalize()
    half_angle = math.radians(angle_deg) / 2.0
    xform = UsdGeom.Xform.Define(stage, path)
    xform.AddTranslateOp().Set(Gf.Vec3d(*pos))
    xform.AddOrientOp().Set(
        Gf.Quatf(math.cos(half_angle), axis * math.sin(half_angle))
    )
    _define_box(stage, f"{path}/geometry", size, (0.0, 0.0, 0.0), color, collision=False)


def _define_wood_table_grain(stage: Any) -> None:
    """Add subtle image-only grain strips to the common warm wooden tabletop."""
    grain_colors = (
        (0.20, 0.085, 0.040), (0.29, 0.125, 0.060), (0.23, 0.100, 0.048),
        (0.31, 0.135, 0.065), (0.21, 0.090, 0.044), (0.28, 0.120, 0.058),
    )
    for index, color in enumerate(grain_colors):
        x = TABLE_CENTER_X - 0.27 + index * 0.105
        _define_box(
            stage, f"/World/s01_wood_grain_{index}", (0.002, 0.94, 0.0008),
            (x, TABLE_CENTER_Y, TABLE_SURFACE_Z + 0.0005), color, collision=False,
        )


def _copy_texture_for_scene(texture_path: Path, stage_output: Path) -> Path:
    """Copy a small licensed texture beside generated USDs for portability."""
    texture_dir = stage_output.parent / "textures"
    texture_dir.mkdir(parents=True, exist_ok=True)
    destination = texture_dir / texture_path.name
    if not destination.exists():
        shutil.copy2(texture_path, destination)
    return destination


def _define_textured_table_top(stage: Any, stage_output: Path) -> None:
    """Add a UV-mapped CC0 wood surface over the shared tabletop collider."""
    from pxr import Sdf, UsdGeom

    # Warm finished wood; preserve fine grain rather than making it near-white.
    # This is an inferred material, not an exact recovered paper texture.
    texture_path = PROJECT_ROOT / (
        "assets/third_party/polyhaven/white_maple_veneer/"
        "white_maple_veneer_diff_1k.jpg"
    )
    if not texture_path.is_file():
        raise FileNotFoundError(f"Missing CC0 tabletop texture: {texture_path}")
    width, depth, _ = TABLE_TOP_SIZE
    mesh = UsdGeom.Mesh.Define(stage, "/World/table_surface_texture")
    mesh.CreatePointsAttr([
        (-width / 2.0, -depth / 2.0, 0.0),
        (width / 2.0, -depth / 2.0, 0.0),
        (width / 2.0, depth / 2.0, 0.0),
        (-width / 2.0, depth / 2.0, 0.0),
    ])
    mesh.CreateFaceVertexCountsAttr([3, 3])
    mesh.CreateFaceVertexIndicesAttr([0, 1, 2, 0, 2, 3])
    mesh.CreateSubdivisionSchemeAttr(UsdGeom.Tokens.none)
    mesh.AddTranslateOp().Set((TABLE_CENTER_X, TABLE_CENTER_Y, TABLE_SURFACE_Z + 0.0008))
    st = UsdGeom.PrimvarsAPI(mesh).CreatePrimvar(
        "st", Sdf.ValueTypeNames.TexCoord2fArray, UsdGeom.Tokens.faceVarying
    )
    st.Set([(0.0, 0.0), (width, 0.0), (width, depth),
            (0.0, 0.0), (width, depth), (0.0, depth)])
    texture_for_scene = _copy_texture_for_scene(texture_path, stage_output)
    _bind_obj_texture(
        stage, mesh.GetPrim(), "/World/table_surface_texture", stage_output,
        texture_for_scene, color_scale=(0.70, 0.48, 0.32), roughness=0.68,
    )


def _define_s01_table_context(stage: Any) -> None:
    """Add the gray equipment panel visible behind the S01/S02 photos."""
    # The reference image has a gray vertical machine/backboard behind the
    # tabletop. This simplified panel and two rails provide similar context.
    far_edge_y = TABLE_CENTER_Y + TABLE_TOP_SIZE[1] / 2.0
    _define_box(
        stage, "/World/s01_gray_back_panel", (1.50, 0.025, 0.60),
        (TABLE_CENTER_X, far_edge_y + 0.035, TABLE_SURFACE_Z + 0.32),
        (0.44, 0.46, 0.48), collision=False,
    )
    for index, (x, angle) in enumerate(((-0.30, -17.0), (0.30, 17.0))):
        _define_oriented_box(
            stage, f"/World/s01_back_rail_{index}", (0.022, 0.018, 0.44),
            (TABLE_CENTER_X + x, far_edge_y - 0.005, TABLE_SURFACE_Z + 0.32),
            (0.42, 0.44, 0.46), rotation_axis=(0.0, 1.0, 0.0), angle_deg=angle,
        )


def _define_s01_cup_visual(stage: Any, root_path: str, size: tuple[float, float, float]) -> None:
    height = size[2]
    bottom_r, top_r = size[0] * 0.37, size[0] * 0.49
    white = (0.88, 0.87, 0.82)
    inside = (0.24, 0.25, 0.24)
    _define_frustum_side(stage, f"{root_path}/visual/cup_outer", bottom_r, top_r, height, white)
    inner_height = height - 0.014
    _define_frustum_side(
        stage, f"{root_path}/visual/cup_inner", bottom_r - 0.004, top_r - 0.004,
        inner_height, inside
    )
    _define_disk(stage, f"{root_path}/visual/cup_inside_bottom", bottom_r - 0.005,
                 -height / 2.0 + 0.012, inside)
    _define_torus(stage, f"{root_path}/visual/cup_rim",
                  (0.0, 0.0, height / 2.0 - 0.0015), top_r - 0.002, 0.002,
                  (0.96, 0.95, 0.91))


def _define_white_red_marker(stage: Any, root_path: str) -> None:
    # The reference photos show a white-bodied marker with a red cap; the red
    # cap is placed at its +Y end to preserve a recognizable visual cue.
    _define_cylinder(stage, f"{root_path}/geometry/barrel", 0.0075, 0.10,
                     (0.0, -0.004, 0.0), (0.91, 0.90, 0.85), axis="Y", collision=True)
    _define_cylinder(stage, f"{root_path}/geometry/red_cap", 0.0085, 0.016,
                     (0.0, 0.054, 0.0), (0.78, 0.055, 0.035), axis="Y", collision=True)
    _define_cylinder(stage, f"{root_path}/geometry/writing_tip", 0.005,
                     0.008, (0.0, -0.058, 0.0), (0.30, 0.29, 0.26), axis="Y", collision=True)


def _read_obj_mesh(path: Path) -> tuple[list[tuple[float, float, float]], list[int], list[int], list[list[tuple[float, float]]]]:
    """Read the small, triangulated YCB OBJ and center its measured bounds."""
    vertices: list[tuple[float, float, float]] = []
    texcoords: list[tuple[float, float]] = []
    faces: list[list[tuple[int, int]]] = []

    def resolve_index(value: str, length: int) -> int:
        index = int(value)
        return index - 1 if index > 0 else length + index

    with path.open(encoding="utf-8") as source:
        for line in source:
            fields = line.split()
            if not fields:
                continue
            if fields[0] == "v":
                vertices.append(tuple(float(value) for value in fields[1:4]))
            elif fields[0] == "vt":
                texcoords.append(tuple(float(value) for value in fields[1:3]))
            elif fields[0] == "f":
                face: list[tuple[int, int]] = []
                for item in fields[1:]:
                    components = item.split("/")
                    if len(components) < 2 or not components[1]:
                        raise ValueError(f"YCB mesh face has no UV coordinate: {item}")
                    face.append((
                        resolve_index(components[0], len(vertices)),
                        resolve_index(components[1], len(texcoords)),
                    ))
                faces.append(face)

    if not vertices or not texcoords or not faces:
        raise ValueError(f"Incomplete textured OBJ: {path}")
    mins = tuple(min(point[axis] for point in vertices) for axis in range(3))
    maxs = tuple(max(point[axis] for point in vertices) for axis in range(3))
    center = tuple((mins[axis] + maxs[axis]) / 2.0 for axis in range(3))
    points = [tuple(point[axis] - center[axis] for axis in range(3)) for point in vertices]
    face_counts = [len(face) for face in faces]
    face_indices = [vertex for face in faces for vertex, _ in face]
    face_uvs = [[texcoords[uv] for _, uv in face] for face in faces]
    return points, face_counts, face_indices, face_uvs


def _bind_obj_texture(
    stage: Any,
    mesh: Any,
    root_path: str,
    stage_output: Path,
    texture_path: Path | None,
    *,
    color_scale: tuple[float, float, float] = (1.0, 1.0, 1.0),
    roughness: float = 0.78,
    metallic: float = 0.0,
    normal_path: Path | None = None,
    metallic_roughness_path: Path | None = None,
    base_color: tuple[float, float, float] | None = None,
) -> None:
    from pxr import Sdf, UsdShade

    material_path = f"{root_path}/material"
    material = UsdShade.Material.Define(stage, material_path)
    surface = UsdShade.Shader.Define(stage, f"{material_path}/PreviewSurface")
    surface.CreateIdAttr("UsdPreviewSurface")
    surface.CreateInput("roughness", Sdf.ValueTypeNames.Float).Set(float(roughness))
    surface.CreateInput("metallic", Sdf.ValueTypeNames.Float).Set(float(metallic))

    primvar = UsdShade.Shader.Define(stage, f"{material_path}/PrimvarReader")
    primvar.CreateIdAttr("UsdPrimvarReader_float2")
    primvar.CreateInput("varname", Sdf.ValueTypeNames.Token).Set("st")
    primvar_result = primvar.CreateOutput("result", Sdf.ValueTypeNames.Float2)

    if texture_path is not None:
        texture = UsdShade.Shader.Define(stage, f"{material_path}/Texture")
        texture.CreateIdAttr("UsdUVTexture")
        texture_file = os.path.relpath(texture_path, stage_output.parent).replace(os.sep, "/")
        texture.CreateInput("file", Sdf.ValueTypeNames.Asset).Set(Sdf.AssetPath(texture_file))
        texture.CreateInput("sourceColorSpace", Sdf.ValueTypeNames.Token).Set("sRGB")
        texture.CreateInput("st", Sdf.ValueTypeNames.Float2).ConnectToSource(primvar_result)
        texture.CreateInput("wrapS", Sdf.ValueTypeNames.Token).Set("repeat")
        texture.CreateInput("wrapT", Sdf.ValueTypeNames.Token).Set("repeat")
        texture.CreateInput("scale", Sdf.ValueTypeNames.Float4).Set(
            (*color_scale, 1.0)
        )
        texture_rgb = texture.CreateOutput("rgb", Sdf.ValueTypeNames.Float3)
        if base_color is None:
            surface.CreateInput("diffuseColor", Sdf.ValueTypeNames.Color3f).ConnectToSource(texture_rgb)
        else:
            surface.CreateInput("diffuseColor", Sdf.ValueTypeNames.Color3f).Set(base_color)
    elif base_color is not None:
        surface.CreateInput("diffuseColor", Sdf.ValueTypeNames.Color3f).Set(base_color)

    if normal_path is not None:
        normal_texture = UsdShade.Shader.Define(stage, f"{material_path}/NormalTexture")
        normal_texture.CreateIdAttr("UsdUVTexture")
        normal_file = os.path.relpath(normal_path, stage_output.parent).replace(os.sep, "/")
        normal_texture.CreateInput("file", Sdf.ValueTypeNames.Asset).Set(Sdf.AssetPath(normal_file))
        normal_texture.CreateInput("sourceColorSpace", Sdf.ValueTypeNames.Token).Set("raw")
        normal_texture.CreateInput("st", Sdf.ValueTypeNames.Float2).ConnectToSource(primvar_result)
        normal_texture.CreateInput("wrapS", Sdf.ValueTypeNames.Token).Set("repeat")
        normal_texture.CreateInput("wrapT", Sdf.ValueTypeNames.Token).Set("repeat")
        normal_texture.CreateInput("scale", Sdf.ValueTypeNames.Float4).Set((2.0, 2.0, 2.0, 1.0))
        normal_texture.CreateInput("bias", Sdf.ValueTypeNames.Float4).Set((-1.0, -1.0, -1.0, 0.0))
        surface.CreateInput("normal", Sdf.ValueTypeNames.Normal3f).ConnectToSource(
            normal_texture.CreateOutput("rgb", Sdf.ValueTypeNames.Float3)
        )
    if metallic_roughness_path is not None:
        packed = UsdShade.Shader.Define(stage, f"{material_path}/MetallicRoughnessTexture")
        packed.CreateIdAttr("UsdUVTexture")
        packed.CreateInput("file", Sdf.ValueTypeNames.Asset).Set(
            Sdf.AssetPath(os.path.relpath(metallic_roughness_path, stage_output.parent)))
        packed.CreateInput("sourceColorSpace", Sdf.ValueTypeNames.Token).Set("raw")
        packed.CreateInput("st", Sdf.ValueTypeNames.Float2).ConnectToSource(primvar_result)
        packed.CreateInput("scale", Sdf.ValueTypeNames.Float4).Set((1., roughness, metallic, 1.))
        surface.CreateInput("roughness", Sdf.ValueTypeNames.Float).ConnectToSource(
            packed.CreateOutput("g", Sdf.ValueTypeNames.Float))
        surface.CreateInput("metallic", Sdf.ValueTypeNames.Float).ConnectToSource(
            packed.CreateOutput("b", Sdf.ValueTypeNames.Float))
    material.CreateSurfaceOutput().ConnectToSource(
        surface.CreateOutput("surface", Sdf.ValueTypeNames.Token)
    )
    UsdShade.MaterialBindingAPI.Apply(mesh).Bind(material)


def _define_s01_scissors(stage: Any, root_path: str, stage_output: Path) -> None:
    """Use the YCB scan geometry, blue image-matched handles, and stable collider."""
    from pxr import Sdf, UsdGeom, UsdShade

    from PIL import Image

    if not SCISSOR_OBJ.is_file() or not SCISSOR_TEXTURE.is_file():
        raise FileNotFoundError(
            "The YCB 037 scissors visual requires its OBJ and texture under "
            f"{SCISSOR_OBJ.parent}"
        )

    points, face_counts, face_indices, face_uvs = _read_obj_mesh(SCISSOR_OBJ)
    mesh_path = f"{root_path}/visual/ycb_scissors_mesh"
    mesh = UsdGeom.Mesh.Define(stage, mesh_path)
    mesh.CreatePointsAttr(points)
    mesh.CreateFaceVertexCountsAttr(face_counts)
    mesh.CreateFaceVertexIndicesAttr(face_indices)
    mesh.CreateSubdivisionSchemeAttr(UsdGeom.Tokens.none)
    st = UsdGeom.PrimvarsAPI(mesh).CreatePrimvar(
        "st", Sdf.ValueTypeNames.TexCoord2fArray, UsdGeom.Tokens.faceVarying
    )
    st.Set([uv for face in face_uvs for uv in face])
    _bind_obj_texture(stage, mesh.GetPrim(), root_path, stage_output, SCISSOR_TEXTURE)

    # Appendix G's photo shows blue plastic handles, while the YCB scan uses
    # yellow/orange plastic. Recolor only those UV faces; preserve the scanned
    # steel, texture detail, and mesh geometry.
    texture_image = Image.open(SCISSOR_TEXTURE).convert("RGB")
    blue_handle_faces: list[int] = []
    for face_index, uv_face in enumerate(face_uvs):
        u = sum(uv[0] for uv in uv_face) / len(uv_face)
        v = sum(uv[1] for uv in uv_face) / len(uv_face)
        pixel = texture_image.getpixel((
            min(texture_image.width - 1, max(0, int(u * (texture_image.width - 1)))),
            min(texture_image.height - 1, max(0, int((1.0 - v) * (texture_image.height - 1)))),
        ))
        red, green, blue = pixel
        if red - blue > 35 and green - blue > 18 and red > 70:
            blue_handle_faces.append(face_index)
    if not blue_handle_faces:
        raise ValueError("Could not identify YCB scissors handle faces for blue recoloring")

    handle_subset = UsdGeom.Subset.Define(stage, f"{mesh_path}/blue_handles")
    handle_subset.CreateElementTypeAttr(UsdGeom.Tokens.face)
    handle_subset.CreateFamilyNameAttr("materialBind")
    handle_subset.CreateIndicesAttr(blue_handle_faces)
    UsdGeom.Subset.SetFamilyType(mesh, "materialBind", UsdGeom.Tokens.nonOverlapping)
    handle_material = UsdShade.Material.Define(stage, f"{root_path}/material/BlueHandles")
    handle_surface = UsdShade.Shader.Define(
        stage, f"{root_path}/material/BlueHandles/PreviewSurface"
    )
    handle_surface.CreateIdAttr("UsdPreviewSurface")
    handle_surface.CreateInput("diffuseColor", Sdf.ValueTypeNames.Color3f).Set(
        (0.025, 0.19, 0.72)
    )
    handle_surface.CreateInput("roughness", Sdf.ValueTypeNames.Float).Set(0.48)
    handle_material.CreateSurfaceOutput().ConnectToSource(
        handle_surface.CreateOutput("surface", Sdf.ValueTypeNames.Token)
    )
    UsdShade.MaterialBindingAPI.Apply(handle_subset.GetPrim()).Bind(handle_material)

    # A convex/triangle mesh is unsuitable as a dynamic PhysX collider here.
    # This hidden box is only for contact; the scanned mesh is the rendered prop.
    collider = _define_box(
        stage, f"{root_path}/geometry/collision_proxy", (0.096, 0.202, 0.018),
        (0.0, 0.0, 0.0), (0.5, 0.5, 0.5), collision=True,
    )
    UsdGeom.Imageable(collider).CreateVisibilityAttr().Set(UsdGeom.Tokens.invisible)


def _define_ycb_visual(
    stage: Any,
    root_path: str,
    name: str,
    size: tuple[float, float, float],
    stage_output: Path,
) -> None:
    """Render a licensed textured YCB scan with separate proxy colliders."""
    from pxr import Gf, Sdf, UsdGeom

    if name not in YCB_MODEL_FILES and name != "scissors":
        raise ValueError(f"No YCB model registered for {name!r}")
    if name == "scissors":
        model_dir = SCISSOR_OBJ.parent
    else:
        model_dir_name, _ = YCB_MODEL_FILES[name]
        model_dir = YCB_UNPACKED / model_dir_name / "google_16k"
    obj_path = model_dir / "textured.obj"
    texture_path = model_dir / "texture_map.png"
    if not obj_path.is_file() or not texture_path.is_file():
        raise FileNotFoundError(
            f"YCB {name} model not extracted; run scripts/prepare_ycb_assets.sh"
        )

    points, face_counts, face_indices, face_uvs = _read_obj_mesh(obj_path)
    source_span = tuple(
        max(point[axis] for point in points) - min(point[axis] for point in points)
        for axis in range(3)
    )
    scale = tuple(
        size[axis] / source_span[axis] if source_span[axis] > 1e-8 else 1.0
        for axis in range(3)
    )
    scaled_points = [
        Gf.Vec3f(*(point[axis] * scale[axis] for axis in range(3)))
        for point in points
    ]
    mesh_path = f"{root_path}/visual/ycb_{name}_mesh"
    mesh = UsdGeom.Mesh.Define(stage, mesh_path)
    mesh.CreatePointsAttr(scaled_points)
    mesh.CreateFaceVertexCountsAttr(face_counts)
    mesh.CreateFaceVertexIndicesAttr(face_indices)
    mesh.CreateSubdivisionSchemeAttr(UsdGeom.Tokens.none)
    st = UsdGeom.PrimvarsAPI(mesh).CreatePrimvar(
        "st", Sdf.ValueTypeNames.TexCoord2fArray, UsdGeom.Tokens.faceVarying
    )
    st.Set([uv for face in face_uvs for uv in face])
    _bind_obj_texture(stage, mesh.GetPrim(), root_path, stage_output, texture_path)


def _define_external_glb_visual(
    stage: Any,
    root_path: str,
    asset_path: Path,
    size: tuple[float, float, float],
    stage_output: Path,
    orientation: str,
    fallback_color: tuple[float, float, float],
    texture_tint_rgb: tuple[float, float, float] = (1.0, 1.0, 1.0),
) -> None:
    """Import a textured GLB as render geometry, not as a PhysX collider."""
    import numpy as np
    import trimesh
    from pxr import Gf, Sdf, UsdGeom

    if not asset_path.is_file():
        raise FileNotFoundError(f"Missing configured GLB visual asset: {asset_path}")
    if orientation == "z_up":
        axis_map = np.eye(3)
    elif orientation == "y_up_to_z_up":
        # Source X/Y/Z -> stage X/Z/-Y.
        axis_map = np.asarray([[1.0, 0.0, 0.0], [0.0, 0.0, -1.0], [0.0, 1.0, 0.0]])
    elif orientation == "bread_upright":
        # Kenney bread is broad in source X/Z and thin in source Y. Rotate it
        # upright while preserving a right-handed frame: source X -> stage Z,
        # source Y -> stage Y, source Z -> -stage X.
        axis_map = np.asarray([[0.0, 0.0, -1.0], [0.0, 1.0, 0.0], [1.0, 0.0, 0.0]])
    elif orientation == "y_up_to_x":
        # Lay a Y-up bunch along tabletop X without flattening its berries.
        axis_map = np.asarray([[0., 1., 0.], [-1., 0., 0.], [0., 0., 1.]])
    else:
        raise ValueError(f"Unsupported GLB orientation {orientation!r}")

    source_scene = trimesh.load(str(asset_path), force="scene")
    meshes = source_scene.dump(concatenate=False)
    if not meshes:
        raise ValueError(f"GLB contains no renderable mesh: {asset_path}")
    mapped_vertices = [np.asarray(mesh.vertices, dtype=np.float64) @ axis_map.T for mesh in meshes]
    all_vertices = np.concatenate(mapped_vertices, axis=0)
    source_min = all_vertices.min(axis=0)
    source_max = all_vertices.max(axis=0)
    source_span = source_max - source_min
    if np.any(source_span <= 1e-8):
        raise ValueError(f"GLB has degenerate bounds: {asset_path} ({source_span})")
    source_center = (source_min + source_max) / 2.0
    scale = np.asarray(size, dtype=np.float64) / source_span
    root_prim = stage.GetPrimAtPath(root_path)
    root_prim.CreateAttribute("appendix_g:source_dimensions_m", Sdf.ValueTypeNames.Double3).Set(tuple(source_span))
    root_prim.CreateAttribute("appendix_g:visual_axis_scale", Sdf.ValueTypeNames.Double3).Set(tuple(scale))
    root_prim.CreateAttribute("appendix_g:aspect_distortion_ratio", Sdf.ValueTypeNames.Double).Set(float(scale.max() / scale.min()))

    texture_dir = stage_output.parent / "textures"
    texture_dir.mkdir(parents=True, exist_ok=True)
    def export_texture(image):
        if image is None:
            return None
        image = image.convert("RGBA")
        digest = hashlib.sha256(str(image.size).encode() + image.tobytes()).hexdigest()[:20]
        path = texture_dir / f"glb_{digest}.png"
        if not path.exists():
            image.save(path)
        return path

    for index, (mesh, vertices) in enumerate(zip(meshes, mapped_vertices, strict=True)):
        faces = np.asarray(mesh.faces, dtype=np.int64)
        points = (vertices - source_center) * scale
        mesh_prim = _define_mesh(
            stage,
            f"{root_path}/visual/imported_glb/part_{index:02d}",
            [tuple(float(value) for value in point) for point in points],
            [len(face) for face in faces],
            faces.reshape(-1).tolist(),
            fallback_color,
        )
        mesh_api = UsdGeom.Mesh(mesh_prim)
        # Preserve authored/smoothed source normals. The asset is first rotated
        # into stage axes and then scaled, so normals use the inverse-transpose
        # of that transform rather than the point transform itself.
        normals = np.asarray(mesh.vertex_normals, dtype=np.float64)
        normals = (normals @ axis_map.T) / scale
        normal_lengths = np.linalg.norm(normals, axis=1, keepdims=True)
        normals = np.divide(
            normals,
            normal_lengths,
            out=np.zeros_like(normals),
            where=normal_lengths > 1e-12,
        )
        mesh_api.CreateNormalsAttr(
            [Gf.Vec3f(*normal) for normal in normals.tolist()]
        )
        mesh_api.SetNormalsInterpolation(UsdGeom.Tokens.vertex)

        visual = getattr(mesh, "visual", None)
        material = getattr(visual, "material", None)
        texture_image = getattr(material, "baseColorTexture", None)
        uv = getattr(visual, "uv", None)
        roughness = getattr(material, "roughnessFactor", None)
        metallic = getattr(material, "metallicFactor", None)
        material_base = getattr(material, "baseColorFactor", None)
        if material_base is not None:
            material_base = np.asarray(material_base, dtype=np.float64)[:3]
            if material_base.size and float(np.max(material_base)) > 1.0:
                material_base /= 255.0
            material_base = np.clip(material_base, 0.0, 1.0)
        roughness = 0.78 if roughness is None else float(roughness)
        metallic = 0.0 if metallic is None else float(metallic)
        normal_path = export_texture(getattr(material, "normalTexture", None)) if uv is not None else None
        metallic_roughness_path = export_texture(getattr(material, "metallicRoughnessTexture", None)) if uv is not None else None
        if texture_image is not None and uv is not None:
            # Convert palette/grayscale sources to a standard RGBA PNG before
            # binding; several lightweight GLBs ship indexed-color atlases.
            texture_path = export_texture(texture_image)

            st = UsdGeom.PrimvarsAPI(mesh_prim).CreatePrimvar(
                "st", Sdf.ValueTypeNames.TexCoord2fArray, UsdGeom.Tokens.faceVarying
            )
            st.Set(np.asarray(uv, dtype=np.float64)[faces].reshape(-1, 2).tolist())
            _bind_obj_texture(
                stage, mesh_prim, f"{root_path}/visual/imported_glb/part_{index:02d}",
                stage_output, texture_path,
                color_scale=tuple(
                    texture_tint_rgb[channel]
                    * (float(material_base[channel]) if material_base is not None else 1.0)
                    for channel in range(3)
                ),
                roughness=roughness,
                metallic=metallic,
                normal_path=normal_path,
                metallic_roughness_path=metallic_roughness_path,
            )
        elif material_base is not None:
            _bind_obj_texture(
                stage, mesh_prim,
                f"{root_path}/visual/imported_glb/part_{index:02d}",
                stage_output, None,
                roughness=roughness,
                metallic=metallic,
                base_color=tuple(
                    texture_tint_rgb[channel] * float(material_base[channel])
                    for channel in range(3)
                ),
            )


def _hide_collider(collider: Any) -> None:
    from pxr import UsdGeom

    UsdGeom.Imageable(collider).CreateVisibilityAttr().Set(UsdGeom.Tokens.invisible)


def _define_toaster_slot_collision(
    stage: Any,
    root_path: str,
    size: tuple[float, float, float],
    slot_floor_relative_z_m: float,
) -> None:
    """Author a hidden toaster shell with one bread-width open slot."""
    width, depth, height = size
    wall = min(0.022, depth * 0.14)
    bottom = min(0.025, height * 0.15)
    roof = min(0.024, height * 0.14)
    slot_gap = min(0.034, depth * 0.25)
    wall_bottom = -height / 2.0 + bottom
    wall_top = height / 2.0 - roof
    wall_height = wall_top - wall_bottom
    wall_center = (wall_top + wall_bottom) / 2.0
    roof_center_z = height / 2.0 - roof / 2.0
    rail_depth = (depth - slot_gap) / 2.0
    rail_y = (slot_gap + rail_depth) / 2.0
    pieces = [
        ("bottom", (width, depth, bottom), (0.0, 0.0, -height / 2.0 + bottom / 2.0)),
        ("left_wall", (wall, depth, wall_height), (-width / 2.0 + wall / 2.0, 0.0, wall_center)),
        ("right_wall", (wall, depth, wall_height), (width / 2.0 - wall / 2.0, 0.0, wall_center)),
        ("front_wall", (width - 2.0 * wall, wall, wall_height), (0.0, -depth / 2.0 + wall / 2.0, wall_center)),
        ("back_wall", (width - 2.0 * wall, wall, wall_height), (0.0, depth / 2.0 - wall / 2.0, wall_center)),
        ("front_top_rail", (width - 2.0 * wall, rail_depth, roof), (0.0, -rail_y, roof_center_z)),
        ("back_top_rail", (width - 2.0 * wall, rail_depth, roof), (0.0, rail_y, roof_center_z)),
        # A hidden support ledge keeps the initially inserted bread from
        # falling through the intentionally open slot before the policy acts.
        ("slot_floor", (width * 0.62, slot_gap, 0.012),
         (0.0, 0.0, slot_floor_relative_z_m - 0.006)),
    ]
    for label, piece_size, position in pieces:
        collider = _define_box(
            stage, f"{root_path}/geometry/toaster_shell_{label}",
            piece_size, position, (0.4, 0.4, 0.4), collision=True,
        )
        _hide_collider(collider)


def _define_profile_collision(
    stage: Any,
    root_path: str,
    profile: str,
    size: tuple[float, float, float],
    visual_geometry: dict[str, Any],
) -> None:
    if profile == "toaster_open_slot_shell_v1":
        _define_toaster_slot_collision(
            stage,
            root_path,
            size,
            float(visual_geometry.get("slot_floor_relative_z_m", 0.0345)),
        )
    elif profile == "open_container_box_walls_floor_v1":
        _define_open_container(
            stage, root_path, size, (0.25, 0.12, 0.06),
            hide_collision_geometry=True,
        )
    elif profile == "bread_slice_box_v1":
        collider = _define_box(
            stage, f"{root_path}/geometry/bread_collision_proxy", size,
            (0.0, 0.0, 0.0), (0.45, 0.30, 0.16), collision=True,
        )
        _hide_collider(collider)
    elif profile == "plate_support_surface_v1":
        # The mesh supplies the rim and appearance. This hidden shallow support
        # avoids using the entire raised plate silhouette as a solid collider.
        surface = _define_box(
            stage, f"{root_path}/geometry/plate_support_proxy",
            (size[0] * 0.82, size[1] * 0.82, 0.008),
            (0.0, 0.0, -size[2] / 2.0 + 0.008),
            (0.5, 0.5, 0.5), collision=True,
        )
        _hide_collider(surface)
    else:
        raise ValueError(f"Unsupported external visual collision profile {profile!r}")
def _define_mug_handle(
    stage: Any,
    root_path: str,
    size: tuple[float, float, float],
    color: tuple[float, float, float],
) -> None:
    """Add a simple rigid U-shaped handle on the mug's local +X side."""
    half_x = size[0] / 2.0
    handle_depth = 0.025
    handle_height = size[2] * 0.58
    segment = 0.015
    inner_x = half_x - 0.005
    outer_x = half_x + 0.065
    span_x = outer_x - inner_x
    center_x = (inner_x + outer_x) / 2.0
    z_offset = handle_height / 2.0 - segment / 2.0

    for label, z in (("top", z_offset), ("bottom", -z_offset)):
        _define_box(
            stage,
            f"{root_path}/geometry/handle_{label}",
            (span_x, handle_depth, segment),
            (center_x, 0.0, z),
            color,
        )
    _define_box(
        stage,
        f"{root_path}/geometry/handle_outer",
        (segment, handle_depth, handle_height),
        (outer_x - segment / 2.0, 0.0, 0.0),
        color,
    )


def _define_box(stage: Any, path: str, size: tuple[float, float, float], pos: tuple[float, float, float], color: tuple[float, float, float], *, collision: bool = True) -> Any:
    from pxr import Gf, UsdGeom, UsdPhysics

    cube = UsdGeom.Cube.Define(stage, path)
    cube.CreateSizeAttr(1.0)
    # USD composes xform ops in stack order. Translation must precede scale;
    # otherwise the scale also scales the position (e.g. table z=.72 becomes
    # .72 * .08 = .0576m), leaving the tabletop below the objects.
    cube.AddTranslateOp().Set(Gf.Vec3d(*pos))
    cube.AddScaleOp().Set(Gf.Vec3f(*size))
    cube.CreateDisplayColorAttr([Gf.Vec3f(*color)])
    if collision:
        UsdPhysics.CollisionAPI.Apply(cube.GetPrim())
    return cube.GetPrim()


def _define_hidden_box_proxy(
    stage: Any, root_path: str, size: tuple[float, float, float]
) -> None:
    """Give a detailed visual a stable, non-rendering rigid-body proxy."""
    from pxr import UsdGeom

    proxy = _define_box(
        stage, f"{root_path}/geometry/collision_proxy", size, (0.0, 0.0, 0.0),
        (0.5, 0.5, 0.5), collision=True,
    )
    UsdGeom.Imageable(proxy).CreateVisibilityAttr().Set(UsdGeom.Tokens.invisible)


def _apply_mesh_collisions(stage: Any, visual_root: str) -> None:
    """Use authored static mesh surfaces as colliders instead of a solid box."""
    from pxr import Usd, UsdGeom, UsdPhysics

    root = stage.GetPrimAtPath(visual_root)
    if not root or not root.IsValid():
        raise ValueError(f"Missing visual root for mesh collision: {visual_root}")
    mesh_count = 0
    for prim in Usd.PrimRange(root):
        if prim.IsA(UsdGeom.Mesh):
            UsdPhysics.CollisionAPI.Apply(prim)
            mesh_count += 1
    if mesh_count == 0:
        raise ValueError(f"No mesh surfaces found for collision under {visual_root}")


def _bind_translucent_preview_material(
    stage: Any, prim_path: str, material_path: str,
    color: tuple[float, float, float], opacity: float,
) -> None:
    """Bind a simple USD Preview Surface for a clear/translucent prop."""
    from pxr import Sdf, UsdShade

    material = UsdShade.Material.Define(stage, material_path)
    shader = UsdShade.Shader.Define(stage, f"{material_path}/PreviewSurface")
    shader.CreateIdAttr("UsdPreviewSurface")
    shader.CreateInput("diffuseColor", Sdf.ValueTypeNames.Color3f).Set(color)
    shader.CreateInput("opacity", Sdf.ValueTypeNames.Float).Set(float(opacity))
    shader.CreateInput("roughness", Sdf.ValueTypeNames.Float).Set(0.12)
    material.CreateSurfaceOutput().ConnectToSource(
        shader.CreateOutput("surface", Sdf.ValueTypeNames.Token)
    )
    prim = stage.GetPrimAtPath(prim_path)
    if prim and prim.IsValid():
        UsdShade.MaterialBindingAPI.Apply(prim).Bind(material)


def _define_paper_cup_visual(
    stage: Any, root_path: str, size: tuple[float, float, float],
    color: tuple[float, float, float],
) -> None:
    """Create a tapered, open paper cup with a visible rim and interior."""
    sx, sy, height = size
    top_radius = min(sx, sy) * 0.48
    bottom_radius = top_radius * 0.72
    floor_z = -height / 2.0 + max(0.004, height * 0.09)
    _define_frustum_side(
        stage, f"{root_path}/visual/cup_outer", bottom_radius, top_radius,
        height, color,
    )
    _define_frustum_side(
        stage, f"{root_path}/visual/cup_inner",
        max(0.004, bottom_radius - 0.0025),
        max(0.004, top_radius - 0.0025), height - 0.006,
        tuple(component * 0.78 for component in color),
    )
    _define_disk(
        stage, f"{root_path}/visual/cup_bottom", bottom_radius - 0.002,
        floor_z, tuple(component * 0.82 for component in color),
    )
    _define_torus(
        stage, f"{root_path}/visual/cup_rim", (0.0, 0.0, height / 2.0),
        top_radius - 0.0015, 0.0015, color,
    )


def _define_straight_cup_visual(
    stage: Any, root_path: str, size: tuple[float, float, float],
    color: tuple[float, float, float],
) -> None:
    """Straight-sided open tumbler, used for the purple S20 destination cup."""
    radius, height = min(size[0], size[1]) * 0.48, size[2]
    _define_frustum_side(
        stage, f"{root_path}/visual/cup_outer", radius * 0.985, radius, height, color
    )
    _define_frustum_side(
        stage, f"{root_path}/visual/cup_inner", radius * 0.94, radius * 0.955,
        height - 0.005, tuple(component * 0.72 for component in color)
    )
    _define_disk(
        stage, f"{root_path}/visual/cup_floor", radius * 0.93,
        -height / 2.0 + 0.005, tuple(component * 0.76 for component in color)
    )
    _define_torus(
        stage, f"{root_path}/visual/cup_rim", (0, 0, height / 2.0),
        radius * 0.98, 0.0015, color
    )


def _define_shallow_bowl_visual(
    stage: Any, root_path: str, size: tuple[float, float, float],
    color: tuple[float, float, float],
) -> None:
    """Lathe a shallow open bowl with a curved sidewall."""
    from pxr import Gf, UsdGeom

    sx, sy, height = size
    radius, half_h = min(sx, sy) * 0.5, size[2] * 0.5
    profiles = [
        (radius * 0.34, -half_h), (radius * 0.58, -half_h * 0.82),
        (radius * 0.79, -half_h * 0.42), (radius * 0.94, half_h * 0.12),
        (radius, half_h * 0.40), (radius * 0.91, half_h * 0.40),
        (radius * 0.84, half_h * 0.05), (radius * 0.68, -half_h * 0.36),
        (radius * 0.49, -half_h * 0.72), (radius * 0.30, -half_h * 0.78),
    ]
    segments = 40
    points = [
        Gf.Vec3f(r * math.cos(2.0 * math.pi * index / segments),
                 r * math.sin(2.0 * math.pi * index / segments), z)
        for r, z in profiles for index in range(segments)
    ]
    counts: list[int] = []
    indices: list[int] = []
    for ring in range(len(profiles)):
        next_ring = (ring + 1) % len(profiles)
        for index in range(segments):
            nxt = (index + 1) % segments
            counts.append(4)
            indices.extend((ring * segments + index, ring * segments + nxt,
                            next_ring * segments + nxt, next_ring * segments + index))
    mesh = UsdGeom.Mesh.Define(stage, f"{root_path}/visual/bowl_shell")
    mesh.CreatePointsAttr(points)
    mesh.CreateFaceVertexCountsAttr(counts)
    mesh.CreateFaceVertexIndicesAttr(indices)
    mesh.CreateSubdivisionSchemeAttr(UsdGeom.Tokens.none)
    mesh.CreateDoubleSidedAttr(True)
    mesh.CreateDisplayColorAttr([Gf.Vec3f(*color)])
    _define_disk(
        stage, f"{root_path}/visual/bowl_inner_floor", radius * 0.30,
        -half_h * 0.76, tuple(component * 0.82 for component in color),
        segments=40,
    )


def _define_pencil_visual(
    stage: Any, root_path: str, size: tuple[float, float, float],
    color: tuple[float, float, float],
) -> None:
    """Create a slender pencil/pen instead of the generic cube fallback."""
    from pxr import Gf, UsdGeom

    length = max(size)
    radius = max(0.0018, min(value for value in size if value < length) / 2.0)
    shaft_length = length * 0.88
    shaft_color = color if color != (0.55, 0.55, 0.58) else (0.76, 0.70, 0.48)
    shaft = UsdGeom.Cylinder.Define(stage, f"{root_path}/visual/pencil_shaft")
    shaft.CreateRadiusAttr(radius)
    shaft.CreateHeightAttr(shaft_length)
    shaft.CreateAxisAttr("X")
    shaft.AddTranslateOp().Set((-length * 0.015, 0.0, 0.0))
    shaft.CreateDisplayColorAttr([Gf.Vec3f(*shaft_color)])
    cap = UsdGeom.Cylinder.Define(stage, f"{root_path}/visual/pencil_cap")
    cap.CreateRadiusAttr(radius * 1.04)
    cap.CreateHeightAttr(length * 0.11)
    cap.CreateAxisAttr("X")
    cap.AddTranslateOp().Set((length * 0.44, 0.0, 0.0))
    cap.CreateDisplayColorAttr([Gf.Vec3f(0.22, 0.22, 0.23)])
    tip = UsdGeom.Cone.Define(stage, f"{root_path}/visual/pencil_tip")
    tip.CreateRadiusAttr(radius)
    tip.CreateHeightAttr(length * 0.10)
    tip.CreateAxisAttr("X")
    tip.AddTranslateOp().Set((-length * 0.49, 0.0, 0.0))
    tip.CreateDisplayColorAttr([Gf.Vec3f(0.84, 0.73, 0.51)])


def _define_towel_visual(
    stage: Any, root_path: str, size: tuple[float, float, float],
    color: tuple[float, float, float],
    stage_output: Path,
) -> None:
    """Layer a folded towel with a soft profile and CC0 terrycloth normal map."""
    from pxr import Sdf, UsdGeom

    sx, sy, sz = size
    cloth = color if max(color) - min(color) > 0.12 else (0.92, 0.92, 0.89)
    source_normal = PROJECT_ROOT / "assets/third_party/polyhaven/terry_cloth/terry_cloth_nor_gl_1k.jpg"
    if not source_normal.is_file():
        raise FileNotFoundError(f"Missing CC0 terrycloth normal map: {source_normal}")
    normal_path = _copy_texture_for_scene(source_normal, stage_output)
    layers = (
        ((sx * 0.94, sy * 0.92, sz * 0.36), (0.0, -sy * 0.01, -sz * 0.30)),
        ((sx * 0.84, sy * 0.93, sz * 0.34), (sx * 0.025, sy * 0.005, 0.0)),
        ((sx * 0.92, sy * 0.78, sz * 0.32), (-sx * 0.015, sy * 0.02, sz * 0.30)),
    )
    for index, (layer_size, position) in enumerate(layers):
        shade = 1.0 - index * 0.045
        layer_color = tuple(min(1.0, channel * shade) for channel in cloth)
        _define_box(
            stage, f"{root_path}/visual/fold_{index}", layer_size, position,
            layer_color, collision=False,
        )
        nx, ny = 14, 10
        top_z = position[2] + layer_size[2] / 2.0 + 0.0007
        points = []
        for row in range(ny + 1):
            v = row / ny
            for column in range(nx + 1):
                u = column / nx
                x = (u - 0.5) * layer_size[0]
                y = (v - 0.5) * layer_size[1]
                edge = min(u, 1.0 - u, v, 1.0 - v)
                ripple = (math.sin(u * 17.0 + index * 1.7)
                          + 0.6 * math.sin(v * 21.0 + index * 0.9))
                z = top_z + ripple * min(sz * 0.018, 0.0018) * min(1.0, edge * 10.0)
                points.append((x, y, z))
        face_counts: list[int] = []
        face_indices: list[int] = []
        face_uvs: list[tuple[float, float]] = []
        for row in range(ny):
            for column in range(nx):
                a = row * (nx + 1) + column
                b, c, d = a + 1, a + nx + 2, a + nx + 1
                face_counts.append(4)
                face_indices.extend((a, b, c, d))
                face_uvs.extend(((column / nx, row / ny),
                                 ((column + 1) / nx, row / ny),
                                 ((column + 1) / nx, (row + 1) / ny),
                                 (column / nx, (row + 1) / ny)))
        mesh = _define_mesh(
            stage, f"{root_path}/visual/terry_surface_{index}", points,
            face_counts, face_indices, layer_color,
        )
        st = UsdGeom.PrimvarsAPI(mesh).CreatePrimvar(
            "st", Sdf.ValueTypeNames.TexCoord2fArray, UsdGeom.Tokens.faceVarying
        )
        st.Set(face_uvs)
        _bind_obj_texture(
            stage, mesh, f"{root_path}/material/Terrycloth", stage_output,
            None, roughness=0.96, normal_path=normal_path, base_color=layer_color,
        )


def _define_drawstring_pouch_visual(
    stage: Any, root_path: str, size: tuple[float, float, float],
    color: tuple[float, float, float], stage_output: Path,
) -> None:
    """Make a low, soft fabric pouch with a puckered mouth and loose cords."""
    from pxr import Gf, Sdf, UsdGeom

    sx, sy, sz = size
    cloth = color if color != (0.55, 0.55, 0.58) else (0.035, 0.038, 0.043)
    normal_source = PROJECT_ROOT / "assets/third_party/polyhaven/terry_cloth/terry_cloth_nor_gl_1k.jpg"
    if not normal_source.is_file():
        raise FileNotFoundError(f"Missing CC0 cloth normal map: {normal_source}")
    normal_path = _copy_texture_for_scene(normal_source, stage_output)

    # A soft, flattened body supports the cloth surface and gives the side edge
    # a visible thickness instead of the previous ball-like silhouette.
    body = UsdGeom.Sphere.Define(stage, f"{root_path}/visual/cloth_body")
    body.CreateRadiusAttr(1.0)
    body.AddTranslateOp().Set((0.0, 0.0, -sz * 0.13))
    body.AddScaleOp().Set(Gf.Vec3f(sx * 0.47, sy * 0.45, sz * 0.35))
    body.CreateDisplayColorAttr([Gf.Vec3f(*(channel * 0.76 for channel in cloth))])

    # The top is a shallow, asymmetric grid with broad fabric folds and tighter
    # radial puckers where the drawstring channel gathers the mouth.
    nx, ny = 28, 20
    mouth_x = 0.31
    points: list[tuple[float, float, float]] = []
    for row in range(ny + 1):
        v = row / ny
        yn = v - 0.5
        for column in range(nx + 1):
            u = column / nx
            xn = u - 0.5
            edge = min(u, 1.0 - u, v, 1.0 - v)
            # Round the corners of the flat pouch footprint while keeping its
            # broad rectangular fabric silhouette.
            corner = max(0.0, (abs(xn) + abs(yn) - 0.72) / 0.28)
            corner_scale = 1.0 - 0.20 * min(1.0, corner)
            mound = 0.30 * math.exp(-(((xn + 0.08) / 0.43) ** 2 + (yn / 0.39) ** 2))
            broad_folds = 0.13 * math.sin(23.0 * xn + 2.8 * math.sin(7.0 * yn))
            broad_folds *= math.exp(-(((xn - 0.04) / 0.55) ** 2 + (yn / 0.55) ** 2))
            angle = math.atan2(yn, xn - mouth_x)
            radius = math.sqrt(((xn - mouth_x) / 0.19) ** 2 + (yn / 0.34) ** 2)
            gathers = 0.10 * math.cos(angle * 9.0 + radius * 2.0)
            gathers *= math.exp(-(((radius - 0.92) / 0.62) ** 2))
            z = -0.18 + mound + broad_folds + gathers + 0.035 * math.sin(yn * 19.0)
            z += 0.025 * math.sin(yn * 15.0 + xn * 5.0) * (1.0 - min(1.0, edge * 8.0))
            # Gently taper the right end into the gathered opening.
            x_scale = 1.0 - 0.18 * max(0.0, xn - 0.18)
            points.append((xn * sx * 0.95 * x_scale * corner_scale,
                           yn * sy * 0.92 * corner_scale, z * sz))

    counts: list[int] = []
    indices: list[int] = []
    face_uvs: list[tuple[float, float]] = []
    for row in range(ny):
        for column in range(nx):
            a = row * (nx + 1) + column
            b, c, d = a + 1, a + nx + 2, a + nx + 1
            counts.append(4)
            indices.extend((a, b, c, d))
            face_uvs.extend(((column / nx, row / ny),
                             ((column + 1) / nx, row / ny),
                             ((column + 1) / nx, (row + 1) / ny),
                             (column / nx, (row + 1) / ny)))
    mesh = _define_mesh(stage, f"{root_path}/visual/wrinkled_cloth", points,
                        counts, indices, cloth)
    UsdGeom.Mesh(mesh).CreateDoubleSidedAttr(True)
    st = UsdGeom.PrimvarsAPI(mesh).CreatePrimvar(
        "st", Sdf.ValueTypeNames.TexCoord2fArray, UsdGeom.Tokens.faceVarying
    )
    st.Set(face_uvs)
    _bind_obj_texture(
        stage, mesh, f"{root_path}/material/PouchFabric", stage_output,
        None, roughness=0.97, normal_path=normal_path, base_color=cloth,
    )

    # A dark opening and folded annular lip make the mouth legible from above.
    segments = 40
    cx = sx * 0.30
    profiles = ((0.125, 0.185, 0.08), (0.100, 0.148, 0.25),
                (0.070, 0.105, 0.23), (0.048, 0.073, 0.13))
    ring_points: list[tuple[float, float, float]] = []
    for ring, (rx, ry, z0) in enumerate(profiles):
        for index in range(segments):
            angle = 2.0 * math.pi * index / segments
            ripple = 0.035 * math.sin(9.0 * angle + ring * 0.8)
            ring_points.append((cx + sx * rx * math.cos(angle),
                                sy * ry * math.sin(angle),
                                sz * (z0 + ripple)))
    ring_indices: list[int] = []
    for ring in range(len(profiles) - 1):
        for index in range(segments):
            nxt = (index + 1) % segments
            ring_indices.extend((ring * segments + index, ring * segments + nxt,
                                 (ring + 1) * segments + nxt,
                                 (ring + 1) * segments + index))
    collar = _define_mesh(stage, f"{root_path}/visual/gathered_collar", ring_points,
                          [4] * (len(ring_indices) // 4), ring_indices,
                          tuple(min(1.0, channel * 1.14) for channel in cloth))
    UsdGeom.Mesh(collar).CreateDoubleSidedAttr(True)
    opening = _define_disk(stage, f"{root_path}/visual/dark_opening",
                           sx * 0.048, sz * 0.135, (0.009, 0.010, 0.012),
                           segments=40)
    UsdGeom.Mesh(opening).AddTranslateOp().Set((cx, 0.0, sz * 0.002))

    cord_color = tuple(min(1.0, channel * 1.55 + 0.012) for channel in cloth)
    cords = (
        ((cx - sx * 0.035, 0.0, sz * 0.24),
         (cx + sx * 0.09, sy * 0.12, sz * 0.20),
         (cx + sx * 0.34, sy * 0.28, sz * 0.12),
         (cx + sx * 0.88, sy * 0.44, sz * 0.06)),
        ((cx + sx * 0.025, 0.0, sz * 0.23),
         (cx + sx * 0.12, -sy * 0.12, sz * 0.18),
         (cx + sx * 0.34, -sy * 0.28, sz * 0.11),
         (cx + sx * 0.72, -sy * 0.44, sz * 0.04)),
    )
    for cord_index, route in enumerate(cords):
        for segment_index, (start, end) in enumerate(zip(route, route[1:])):
            _define_cylinder_segment(
                stage,
                f"{root_path}/visual/drawcord_{cord_index}_{segment_index}",
                start, end, 0.0015, cord_color,
            )


def _define_open_drawer_visual(
    stage: Any, root_path: str, size: tuple[float, float, float]
) -> None:
    """Build a recognizable shallow drawer/box with a dark cavity and pull."""
    sx, sy, sz = size
    wall, floor = min(0.014, sx * 0.055, sy * 0.08), min(0.012, sz * 0.16)
    wood = (0.62, 0.40, 0.22)
    trim = (0.47, 0.27, 0.14)
    panels = (
        ("floor", (sx, sy, floor), (0.0, 0.0, -sz / 2.0 + floor / 2.0), (0.18, 0.095, 0.05)),
        ("back", (wall, sy, sz - floor), (sx / 2.0 - wall / 2.0, 0.0, floor / 2.0), wood),
        ("left", (sx - 2 * wall, wall, sz - floor), (0.0, sy / 2.0 - wall / 2.0, floor / 2.0), wood),
        ("right", (sx - 2 * wall, wall, sz - floor), (0.0, -sy / 2.0 + wall / 2.0, floor / 2.0), wood),
        # Open face toward the robot (-X); a raised outer rim surrounds the low lip.
        ("front_lip", (wall, sy, sz * 0.32), (-sx / 2.0 + wall / 2.0, 0.0, -sz * 0.31), trim),
        ("front_left_post", (wall, wall, sz * 0.78), (-sx / 2.0 + wall / 2.0, sy / 2.0 - wall / 2.0, sz * 0.10), wood),
        ("front_right_post", (wall, wall, sz * 0.78), (-sx / 2.0 + wall / 2.0, -sy / 2.0 + wall / 2.0, sz * 0.10), wood),
    )
    for name, panel_size, pos, color in panels:
        _define_box(stage, f"{root_path}/visual/{name}", panel_size, pos, color, collision=False)
    _define_cylinder(
        stage, f"{root_path}/visual/front_pull", 0.0045, sy * 0.24,
        (-sx / 2.0 - 0.001, 0.0, -sz * 0.27), (0.06, 0.055, 0.05),
        axis="Y", collision=False,
    )
    for index in range(3):
        y = -sy * 0.28 + index * sy * 0.28
        _define_box(
            stage, f"{root_path}/visual/floor_grain_{index}",
            (sx * 0.78, 0.0015, 0.0008), (0.06 * sx, y, -sz / 2.0 + floor + 0.001),
            (0.30, 0.16, 0.075), collision=False,
        )


def _define_two_tier_cabinet_visual(
    stage: Any,
    root_path: str,
    size: tuple[float, float, float],
    color: tuple[float, float, float],
    *,
    drawer_state: str,
) -> None:
    """Low two-drawer wooden cabinet; the upper drawer can be shown open."""
    sx, sy, sz = size
    wood = color if color != (0.55, 0.55, 0.58) else (0.65, 0.43, 0.25)
    dark_wood = tuple(channel * 0.76 for channel in wood)
    wall = min(0.012, sx * 0.05, sy * 0.055, sz * 0.10)
    parts = (
        ("case_top", (sx, sy, wall), (0.0, 0.0, sz / 2.0 - wall / 2.0), wood),
        ("case_bottom", (sx, sy, wall), (0.0, 0.0, -sz / 2.0 + wall / 2.0), dark_wood),
        ("case_left", (sx, wall, sz), (0.0, sy / 2.0 - wall / 2.0, 0.0), dark_wood),
        ("case_right", (sx, wall, sz), (0.0, -sy / 2.0 + wall / 2.0, 0.0), dark_wood),
        ("case_back", (wall, sy - 2.0 * wall, sz - 2.0 * wall), (sx / 2.0 - wall / 2.0, 0.0, 0.0), dark_wood),
        ("middle_shelf", (sx - wall, sy - 2.0 * wall, wall), (0.0, 0.0, 0.0), wood),
    )
    for name, part_size, pos, part_color in parts:
        _define_box(stage, f"{root_path}/visual/{name}", part_size, pos, part_color, collision=False)

    open_upper = drawer_state.lower() in {"open", "upper_open", "top_open"}
    drawer_height = (sz - 3.0 * wall) / 2.0
    drawer_depth = sx - 2.0 * wall
    drawer_width = sy - 2.0 * wall
    for tier, center_z in (("lower", -sz * 0.25), ("upper", sz * 0.25)):
        is_open = tier == "upper" and open_upper
        pull_out = sx * 0.40 if is_open else 0.0
        drawer_center_x = -pull_out
        floor_z = center_z - drawer_height / 2.0 + wall * 0.55
        floor_thickness = max(0.004, wall * 0.58)
        drawer_color = tuple(channel * 0.78 for channel in wood)
        drawer_parts = (
            ("floor", (drawer_depth, drawer_width, floor_thickness),
             (drawer_center_x + wall * 0.25, 0.0, floor_z), drawer_color),
            ("side_pos", (drawer_depth, wall * 0.55, drawer_height * 0.82),
             (drawer_center_x + wall * 0.25, drawer_width / 2.0 - wall * 0.28, center_z), wood),
            ("side_neg", (drawer_depth, wall * 0.55, drawer_height * 0.82),
             (drawer_center_x + wall * 0.25, -drawer_width / 2.0 + wall * 0.28, center_z), wood),
            ("back", (wall * 0.55, drawer_width, drawer_height * 0.82),
             (drawer_center_x + drawer_depth / 2.0, 0.0, center_z), wood),
        )
        for label, part_size, pos, part_color in drawer_parts:
            _define_box(
                stage, f"{root_path}/visual/{tier}_drawer_{label}",
                part_size, pos, part_color, collision=False,
            )
        front_x = -sx / 2.0 - pull_out + wall * 0.35
        front_height = drawer_height * (0.46 if is_open else 0.88)
        _define_box(
            stage, f"{root_path}/visual/{tier}_drawer_front",
            (wall * 0.78, drawer_width, front_height),
            (front_x, 0.0, center_z), wood, collision=False,
        )
        # Inset panel and two narrow grain lines make the drawer face read as wood.
        _define_box(
            stage, f"{root_path}/visual/{tier}_drawer_inset",
            (wall * 0.12, drawer_width * 0.74, front_height * 0.56),
            (front_x - wall * 0.42, 0.0, center_z),
            tuple(min(1.0, channel * 1.08) for channel in wood), collision=False,
        )
        for stripe in range(2):
            stripe_y = -drawer_width * 0.30 + stripe * drawer_width * 0.60
            _define_box(
                stage, f"{root_path}/visual/{tier}_grain_{stripe}",
                (wall * 0.10, drawer_width * 0.20, 0.0012),
                (front_x - wall * 0.50, stripe_y, center_z + front_height * 0.22),
                dark_wood, collision=False,
            )
        _define_cylinder(
            stage, f"{root_path}/visual/{tier}_handle", 0.0038,
            drawer_width * 0.20, (front_x - wall * 0.62, 0.0, center_z),
            (0.045, 0.045, 0.042), axis="Y", collision=False,
        )


def _define_grape_cluster_visual(
    stage: Any, root_path: str, size: tuple[float, float, float],
    color: tuple[float, float, float],
) -> None:
    """Create a low clustered bunch of grapes with a visible short stem."""
    from pxr import Gf, UsdGeom

    sx, sy, sz = size
    radius = min(sx, sy, sz) * 0.15
    points = [
        (-0.27, -0.22, -0.18), (0.0, -0.25, -0.24), (0.27, -0.18, -0.20),
        (-0.34, 0.05, 0.02), (-0.10, 0.02, 0.0), (0.16, 0.07, 0.04),
        (0.34, 0.02, -0.04), (-0.22, 0.28, -0.15), (0.06, 0.29, -0.11),
        (0.28, 0.25, -0.17), (-0.04, -0.02, 0.29),
    ]
    for index, (x, y, z) in enumerate(points):
        grape = UsdGeom.Sphere.Define(stage, f"{root_path}/visual/grape_{index:02d}")
        grape.CreateRadiusAttr(radius)
        grape.AddTranslateOp().Set((x * sx * 1.55, y * sy * 1.55, z * sz * 1.30))
        grape.CreateDisplayColorAttr([Gf.Vec3f(*color)])
    _define_cylinder(
        stage, f"{root_path}/visual/stem", 0.0025, min(0.035, sz * 0.22),
        (0.0, 0.0, sz * 0.36), (0.27, 0.19, 0.06), collision=False,
    )


def _define_toaster_visual(
    stage: Any, root_path: str, size: tuple[float, float, float],
    color: tuple[float, float, float],
    *, power_cord: bool = False,
) -> None:
    """Build a dark toaster with a top slot and front panel/controls."""
    sx, sy, sz = size
    body_color = color if color != (0.55, 0.55, 0.58) else (0.075, 0.082, 0.085)
    _define_box(stage, f"{root_path}/visual/body", size, (0.0, 0.0, 0.0), body_color, collision=False)
    _define_box(
        stage, f"{root_path}/visual/front_panel", (sx * 0.018, sy * 0.78, sz * 0.68),
        (-sx * 0.505, 0.0, -sz * 0.02), (0.10, 0.11, 0.12), collision=False,
    )
    _define_box(
        stage, f"{root_path}/visual/top_slot",
        (sx * 0.58, max(0.007, sy * 0.09), 0.0025),
        (sx * 0.02, 0.0, sz * 0.501), (0.025, 0.028, 0.03), collision=False,
    )
    _define_box(
        stage, f"{root_path}/visual/lever", (sx * 0.035, 0.008, sz * 0.48),
        (-sx * 0.36, sy * 0.49, sz * 0.08), (0.48, 0.50, 0.51), collision=False,
    )
    _define_box(
        stage, f"{root_path}/visual/control", (sx * 0.012, 0.025, 0.028),
        (-sx * 0.51, -sy * 0.27, sz * 0.10), (0.025, 0.028, 0.03), collision=False,
    )
    # The Appendix photo shows the black power lead curling out to image-left.
    # Add it only to scenes whose source image clearly includes the cord.
    # The toaster root is static, and these visuals intentionally have no
    # collision shapes.
    cord = (0.025, 0.025, 0.028)
    if power_cord:
        points = (
            (0.0, sy * 0.49, -sz * 0.20),
            (sx * 0.10, sy * 0.64, -sz * 0.34),
            (sx * 0.24, sy * 0.77, -sz * 0.35),
            (sx * 0.32, sy * 0.75, -sz * 0.35),
            (sx * 0.39, sy * 0.63, -sz * 0.35),
        )
        for index, (start, end) in enumerate(zip(points, points[1:])):
            _define_cylinder_segment(
                stage, f"{root_path}/visual/power_cord_{index}", start, end,
                0.0035, cord,
            )


def _define_toast_visual(
    stage: Any, root_path: str, size: tuple[float, float, float],
    color: tuple[float, float, float],
) -> None:
    """Make a recognizable upright slice, with crust and lighter crumb."""
    sx, sy, sz = size
    width, height = max(sx, sy), max(sz, sx)
    thickness = min(sy, sx * 0.16, sz * 0.18)
    crust = color if color != (0.75, 0.42, 0.16) else (0.53, 0.27, 0.10)
    _define_box(stage, f"{root_path}/visual/crust", (width, thickness, height), (0.0, 0.0, 0.0), crust, collision=False)
    _define_box(
        stage, f"{root_path}/visual/crumb", (width * 0.78, thickness * 0.48, height * 0.75),
        (0.0, -thickness * 0.06, -height * 0.035), (0.91, 0.73, 0.48), collision=False,
    )


def _define_wide_hat_visual(
    stage: Any, root_path: str, size: tuple[float, float, float],
    color: tuple[float, float, float],
) -> None:
    from pxr import Gf, UsdGeom

    sx, sy, sz = size
    segments = 64
    rx, ry = sx * 0.5, sy * 0.5
    brim_z = -sz * 0.39
    brim_profiles = ((0.29, -0.045), (1.0, -0.035), (1.0, 0.015), (0.30, 0.008))
    brim_points = []
    for radius_scale, z_offset in brim_profiles:
        for index in range(segments):
            angle = 2.0 * math.pi * index / segments
            wave = 0.012 * sz * math.cos(2.0 * angle)
            brim_points.append((rx * radius_scale * math.cos(angle),
                                ry * radius_scale * math.sin(angle),
                                brim_z + z_offset * sz + wave))
    brim_counts, brim_indices = [], []
    for ring in range(len(brim_profiles)):
        next_ring = (ring + 1) % len(brim_profiles)
        for index in range(segments):
            nxt = (index + 1) % segments
            brim_counts.append(4)
            brim_indices.extend((ring * segments + index, ring * segments + nxt,
                                 next_ring * segments + nxt, next_ring * segments + index))
    brim = _define_mesh(stage, f"{root_path}/visual/fedora_brim",
                        brim_points, brim_counts, brim_indices, color)
    UsdGeom.Mesh(brim).CreateDoubleSidedAttr(True)

    # A fedora crown is low and rounded, with gently pinched sides and a dented top.
    crown_profiles = ((0.31, -0.345), (0.34, -0.26), (0.325, -0.08),
                      (0.30, 0.20), (0.255, 0.38), (0.17, 0.47), (0.045, 0.485))
    crown_points = []
    for radius_scale, z_fraction in crown_profiles:
        for index in range(segments):
            angle = 2.0 * math.pi * index / segments
            pinch = 1.0 - 0.055 * max(0.0, z_fraction) * math.cos(2.0 * angle)
            crown_points.append((rx * radius_scale * pinch * math.cos(angle),
                                 ry * radius_scale * pinch * math.sin(angle),
                                 z_fraction * sz))
    crown_counts, crown_indices = [], []
    for ring in range(len(crown_profiles) - 1):
        for index in range(segments):
            nxt = (index + 1) % segments
            crown_counts.append(4)
            crown_indices.extend((ring * segments + index, ring * segments + nxt,
                                  (ring + 1) * segments + nxt,
                                  (ring + 1) * segments + index))
    crown = _define_mesh(stage, f"{root_path}/visual/fedora_crown",
                         crown_points, crown_counts, crown_indices, color)
    UsdGeom.Mesh(crown).CreateDoubleSidedAttr(True)
    band_color = tuple(min(1.0, component * 1.28) for component in color)
    _define_torus(
        stage, f"{root_path}/visual/fedora_band", (0.0, 0.0, -sz * 0.29),
        min(rx, ry) * 0.285, max(0.001, sz * 0.018), band_color,
        ring_segments=48, tube_segments=8,
    )


def _define_keyboard_visual(
    stage: Any, root_path: str, size: tuple[float, float, float],
    color: tuple[float, float, float],
    stage_output: Path,
) -> None:
    from PIL import Image, ImageDraw, ImageFont
    from pxr import Sdf, UsdGeom
    sx, sy, sz = size
    base = color if max(color) - min(color) < 0.20 else (0.10, 0.11, 0.12)
    _define_box(stage, f"{root_path}/visual/base", size, (0.0, 0.0, 0.0), base, collision=False)
    labels = [list("1234567890-=  "), list("QWERTYUIOP[]  "),
              list("ASDFGHJKL;'   "), list("ZXCVBNM,./    "), ["Ctrl", "", "Alt", "", "", "", "", "", "", "", "", "", "", ""]]
    atlas = Image.new("RGB", (14*64,5*64), (16,17,19))
    draw = ImageDraw.Draw(atlas)
    try:
        font = ImageFont.truetype("DejaVuSans.ttf", 30)
    except OSError:
        font = ImageFont.load_default()
    for row in range(5):
        for column in range(14):
            label = labels[row][column] if column < len(labels[row]) else ""
            draw.text((column*64+32,row*64+32),label,font=font,fill=(218,218,210),anchor="mm")
    texture = stage_output.parent / "textures/keyboard_qwerty_v7.png"
    texture.parent.mkdir(parents=True,exist_ok=True)
    if not texture.exists():
        atlas.save(texture)
    for row in range(5):
        for column in range(14):
            x, y = -sx * 0.43 + column * sx * 0.066, -sy * 0.38 + row * sy * 0.18
            key_color = (0.025, 0.028, 0.032)
            _define_box(
                stage, f"{root_path}/visual/key_{row}_{column}",
                (sx * 0.052, sy * 0.13, max(0.002, sz * 0.19)),
                (x, y, sz * 0.58), key_color, collision=False,
            )
            hx,hy,z=sx*.026,sy*.065,sz*.58+max(.002,sz*.19)*.5+.0001
            cap = _define_mesh(stage,f"{root_path}/visual/legend_{row}_{column}",
                [(x-hx,y-hy,z),(x+hx,y-hy,z),(x+hx,y+hy,z),(x-hx,y+hy,z)], [4],[0,1,2,3],key_color)
            uv = UsdGeom.PrimvarsAPI(cap).CreatePrimvar("st",Sdf.ValueTypeNames.TexCoord2fArray,UsdGeom.Tokens.faceVarying)
            u0,u1=column/14,(column+1)/14
            v0,v1=1-(row+1)/5,1-row/5
            uv.Set([(u0,v0),(u1,v0),(u1,v1),(u0,v1)])
            _bind_obj_texture(stage,cap,f"{root_path}/visual/legend_{row}_{column}",stage_output,texture,roughness=.86)


def _define_shape_sorter_visual(
    stage: Any, root_path: str, size: tuple[float, float, float],
    color: tuple[float, float, float],
) -> None:
    sx, sy, sz = size
    wood = color if color != (0.55, 0.55, 0.58) else (0.59, 0.36, 0.17)
    _define_box(stage, f"{root_path}/visual/box_body", (sx, sy, sz * 0.70), (0.0, 0.0, -sz * 0.15), wood, collision=False)
    board_z = sz * 0.36
    _define_box(stage, f"{root_path}/visual/top_board", (sx * 0.98, sy * 0.96, sz * 0.18), (0.0, 0.0, board_z), (0.66, 0.45, 0.25), collision=False)
    for index, (x, y, radius) in enumerate(((-sx * 0.27, 0.0, 0.045), (0.0, 0.0, 0.038), (sx * 0.27, 0.0, 0.035))):
        _define_cylinder(stage, f"{root_path}/visual/hole_{index}", radius, 0.0015, (x, y, board_z + sz * 0.10), (0.10, 0.08, 0.06), collision=False)


def _define_basket_visual(
    stage: Any, root_path: str, size: tuple[float, float, float],
    color: tuple[float, float, float],
) -> None:
    sx, sy, sz = size
    bar = max(0.003, min(sx, sy) * 0.025)
    for layer in range(4):
        z = -sz * 0.34 + layer * sz * 0.22
        for sign in (-1.0, 1.0):
            side = "neg" if sign < 0 else "pos"
            _define_box(stage, f"{root_path}/visual/weave_x_{layer}_{side}", (sx, bar, bar), (0, sign * (sy / 2 - bar / 2), z), color, collision=False)
            _define_box(stage, f"{root_path}/visual/weave_y_{layer}_{side}", (bar, sy, bar), (sign * (sx / 2 - bar / 2), 0, z), color, collision=False)
    for ix, x in enumerate((-sx * 0.35, 0.0, sx * 0.35)):
        for iy, y in enumerate((-sy * 0.35, sy * 0.35)):
            _define_box(stage, f"{root_path}/visual/reed_{ix}_{iy}", (bar, bar, sz * 0.75), (x, y, 0), color, collision=False)


def _define_pink_fabric_bundle_visual(
    stage: Any, root_path: str, size: tuple[float, float, float],
    color: tuple[float, float, float],
) -> None:
    """Create a soft, irregular cloth/net mound instead of a flat grid."""
    from pxr import Gf, UsdGeom

    sx, sy, sz = size
    lobes = (
        (-0.27, -0.08, 0.00, 0.29, 0.34, 0.27),
        (0.02, 0.00, 0.08, 0.33, 0.38, 0.38),
        (0.29, 0.10, -0.01, 0.25, 0.33, 0.30),
        (-0.13, 0.31, -0.10, 0.28, 0.30, 0.23),
        (0.19, -0.31, -0.12, 0.25, 0.29, 0.24),
    )
    shades = (1.0, 0.86, 1.08, 0.92, 0.78)
    for index, (x, y, z, scale_x, scale_y, scale_z) in enumerate(lobes):
        ellipsoid = UsdGeom.Sphere.Define(stage, f"{root_path}/visual/fold_{index}")
        ellipsoid.CreateRadiusAttr(1.0)
        ellipsoid.AddTranslateOp().Set((x * sx, y * sy, z * sz))
        ellipsoid.AddScaleOp().Set(Gf.Vec3f(sx * scale_x, sy * scale_y, sz * scale_z))
        ellipsoid.CreateDisplayColorAttr([Gf.Vec3f(*(
            min(1.0, channel * shades[index]) for channel in color
        ))])

    # Three broad, rippled cloth strips suggest gathered folds without forming
    # the rectangular lattice that appeared in the earlier preview.
    for band_index, offset in enumerate((-0.27, -0.04, 0.20)):
        columns, rows = 24, 4
        points = []
        for row in range(rows + 1):
            v = row / rows
            for column in range(columns + 1):
                u = column / columns
                x = (u - 0.5) * sx * 0.72
                y = (v - 0.5) * sy * 0.10 + offset * sy
                z = sz * (0.31 + 0.16 * math.sin(math.pi * u)
                          + 0.035 * math.sin(u * 28.0 + band_index * 1.3))
                points.append((x, y, z))
        counts, indices = [], []
        for row in range(rows):
            for column in range(columns):
                a = row * (columns + 1) + column
                counts.append(4)
                indices.extend((a, a + 1, a + columns + 2, a + columns + 1))
        mesh = _define_mesh(
            stage, f"{root_path}/visual/fold_ribbon_{band_index}", points,
            counts, indices,
            tuple(min(1.0, channel * (0.82 + band_index * 0.08)) for channel in color),
        )
        UsdGeom.Mesh(mesh).CreateDoubleSidedAttr(True)


def _define_pink_net_v7(stage, root_path, size, color):
    """Gathered open tulle: intersecting fine strands, not solid plastic lobes.

    Visual approximation of the thumbnail only; no deformable-cloth claim.
    """
    from pxr import Gf, Sdf, UsdGeom, UsdShade
    sx, sy, sz = size
    path = f"{root_path}/visual/pink_tulle"
    points, counts = [], []
    for layer in range(3):
        for direction in range(2):
            for line in range(51):
                fixed = -1.0 + 2.0 * line / 50
                for step in range(81):
                    moving = -1.0 + 2.0 * step / 80
                    u, v = (fixed, moving) if direction else (moving, fixed)
                    x = sx * .45 * u
                    y = sy * (.41 * v + .025 * math.sin(u * 14 + layer))
                    z = sz * (-.42 + .10 * layer + .38 * (1-u*u) * (1-v*v)
                              + .12 * math.sin(u*17 + layer) * math.cos(v*13))
                    points.append(Gf.Vec3f(x, y, z))
                counts.append(81)
    curves = UsdGeom.BasisCurves.Define(stage, path)
    curves.CreateTypeAttr(UsdGeom.Tokens.linear)
    curves.CreateWrapAttr(UsdGeom.Tokens.nonperiodic)
    curves.CreateCurveVertexCountsAttr(counts)
    curves.CreatePointsAttr(points)
    curves.CreateWidthsAttr([min(sx, sy) * .0022])
    curves.SetWidthsInterpolation(UsdGeom.Tokens.constant)
    curves.CreateDisplayColorAttr([Gf.Vec3f(*color)])
    material = UsdShade.Material.Define(stage, path + "_material")
    shader = UsdShade.Shader.Define(stage, path + "_material/surface")
    shader.CreateIdAttr("UsdPreviewSurface")
    shader.CreateInput("diffuseColor", Sdf.ValueTypeNames.Color3f).Set(Gf.Vec3f(*color))
    shader.CreateInput("roughness", Sdf.ValueTypeNames.Float).Set(.93)
    material.CreateSurfaceOutput().ConnectToSource(shader.CreateOutput("surface", Sdf.ValueTypeNames.Token))
    UsdShade.MaterialBindingAPI.Apply(curves.GetPrim()).Bind(material)


def _define_glove_pair_visual(
    stage: Any, root_path: str, size: tuple[float, float, float],
    color: tuple[float, float, float],
) -> None:
    from pxr import Gf, UsdGeom

    glove_color = color if color != (0.55, 0.55, 0.58) else (0.085, 0.095, 0.105)
    for glove in (-1.0, 1.0):
        side = "left" if glove < 0 else "right"
        cx = glove * size[0] * 0.24
        palm = UsdGeom.Sphere.Define(stage, f"{root_path}/visual/glove_{side}_palm")
        palm.CreateRadiusAttr(1.0)
        palm.AddTranslateOp().Set((cx, -size[1] * 0.04, -size[2] * 0.03))
        palm.AddScaleOp().Set(Gf.Vec3f(size[0] * 0.19, size[1] * 0.29, size[2] * 0.43))
        palm.CreateDisplayColorAttr([Gf.Vec3f(*glove_color)])
        for finger in range(4):
            spread = (finger - 1.5) * size[0] * 0.075
            finger_len = size[1] * (0.19 + 0.015 * (1 - abs(finger - 1.5)))
            finger_prim = UsdGeom.Sphere.Define(
                stage, f"{root_path}/visual/glove_{side}_finger_{finger}"
            )
            finger_prim.CreateRadiusAttr(1.0)
            finger_prim.AddTranslateOp().Set((cx + spread, size[1] * 0.22, 0.0))
            finger_prim.AddScaleOp().Set(Gf.Vec3f(
                size[0] * 0.065, finger_len, size[2] * 0.29
            ))
            finger_prim.CreateDisplayColorAttr([Gf.Vec3f(*glove_color)])
        thumb = UsdGeom.Sphere.Define(stage, f"{root_path}/visual/glove_{side}_thumb")
        thumb.CreateRadiusAttr(1.0)
        thumb.AddTranslateOp().Set((cx + glove * size[0] * 0.14, -size[1] * 0.06, 0.0))
        thumb.AddScaleOp().Set(Gf.Vec3f(size[0] * 0.085, size[1] * 0.20, size[2] * 0.30))
        thumb.CreateDisplayColorAttr([Gf.Vec3f(*glove_color)])
        cuff = UsdGeom.Sphere.Define(stage, f"{root_path}/visual/glove_{side}_cuff")
        cuff.CreateRadiusAttr(1.0)
        cuff.AddTranslateOp().Set((cx, -size[1] * 0.31, -size[2] * 0.035))
        cuff.AddScaleOp().Set(Gf.Vec3f(size[0] * 0.18, size[1] * 0.15, size[2] * 0.40))
        cuff.CreateDisplayColorAttr([Gf.Vec3f(*(channel * 0.72 for channel in glove_color))])


def _define_burger_visual(
    stage: Any, root_path: str, size: tuple[float, float, float],
    color: tuple[float, float, float],
) -> None:
    """Layer bun, filling, and top bun into a low burger silhouette."""
    sx, sy, sz = size
    base = max(0.002, sz * 0.19)
    _define_cylinder(stage, f"{root_path}/visual/bottom_bun", min(sx, sy) * 0.46, base, (0, 0, -sz * 0.31), (0.70, 0.39, 0.17), collision=False)
    _define_cylinder(stage, f"{root_path}/visual/patty", min(sx, sy) * 0.48, sz * 0.24, (0, 0, -sz * 0.07), (0.31, 0.13, 0.055), collision=False)
    _define_cylinder(stage, f"{root_path}/visual/lettuce", min(sx, sy) * 0.49, sz * 0.075, (0, 0, sz * 0.09), (0.17, 0.40, 0.08), collision=False)
    _define_cylinder(stage, f"{root_path}/visual/top_bun", min(sx, sy) * 0.46, sz * 0.30, (0, 0, sz * 0.30), color if color != (0.55, 0.55, 0.58) else (0.79, 0.48, 0.22), collision=False)


def _define_vegetable_cluster_visual(
    stage: Any, root_path: str, size: tuple[float, float, float],
    color: tuple[float, float, float], *, broccoli: bool,
) -> None:
    """Cluster small smooth florets/segments instead of a single proxy cube."""
    from pxr import Gf, UsdGeom

    sx, sy, sz = size
    base_color = color if color != (0.55, 0.55, 0.58) else ((0.12, 0.40, 0.10) if broccoli else (0.78, 0.06, 0.045))
    if broccoli:
        centers = [
            (-0.22, -0.16, 0.10), (0.02, -0.20, 0.20), (0.24, -0.13, 0.05),
            (-0.30, 0.10, 0.08), (-0.04, 0.12, 0.22), (0.23, 0.12, 0.12),
            (0.0, 0.0, -0.16),
        ]
    else:
        centers = [(-0.22, 0.0, 0.0), (0.0, -0.05, 0.0), (0.22, 0.02, 0.0), (0.05, 0.18, 0.0), (-0.07, -0.18, 0.0)]
    for index, (x, y, z) in enumerate(centers):
        sphere = UsdGeom.Sphere.Define(stage, f"{root_path}/visual/piece_{index}")
        sphere.CreateRadiusAttr(1.0)
        factor = 0.24 if broccoli else 0.31
        sphere.AddTranslateOp().Set((x * sx, y * sy, z * sz))
        sphere.AddScaleOp().Set(Gf.Vec3f(min(sx, sy, sz) * factor, min(sx, sy, sz) * factor, min(sx, sy, sz) * factor))
        sphere.CreateDisplayColorAttr([Gf.Vec3f(*base_color)])
    if broccoli:
        _define_cylinder(stage, f"{root_path}/visual/stalk", min(sx, sy) * 0.10, sz * 0.40, (0, 0, -sz * 0.28), (0.72, 0.73, 0.43), collision=False)


def _define_hex_nut_visual(
    stage: Any, root_path: str, size: tuple[float, float, float],
    color: tuple[float, float, float],
) -> None:
    """Render a small metallic hex nut with a dark center opening."""
    from pxr import Gf, UsdGeom

    sx, sy, sz = size
    outer = min(sx, sy) * 0.50
    inner = outer * 0.39
    metal = color if color != (0.55, 0.55, 0.58) else (0.49, 0.51, 0.52)
    points: list[tuple[float, float, float]] = []
    for radius, z in ((outer, -sz / 2), (outer, sz / 2),
                      (inner, -sz / 2), (inner, sz / 2)):
        points.extend((radius * math.cos(2 * math.pi * i / 6),
                       radius * math.sin(2 * math.pi * i / 6), z)
                      for i in range(6))
    indices: list[int] = []
    counts: list[int] = []
    for i in range(6):
        j = (i + 1) % 6
        indices.extend((i, j, 6 + j, 6 + i)); counts.append(4)               # outside
        indices.extend((12 + i, 18 + i, 18 + j, 12 + j)); counts.append(4)  # bore
        indices.extend((6 + i, 6 + j, 18 + j, 18 + i)); counts.append(4)   # top
        indices.extend((j, i, 12 + i, 12 + j)); counts.append(4)           # bottom
    mesh = _define_mesh(stage, f"{root_path}/visual/hex_nut", points, counts, indices, metal)
    UsdGeom.Mesh(mesh).CreateDoubleSidedAttr(True)


def _define_tray_visual(
    stage: Any, root_path: str, size: tuple[float, float, float],
    color: tuple[float, float, float],
) -> None:
    """Open-top shallow rectangular tray with a darker inner floor."""
    sx, sy, sz = size
    wall = min(0.010, sz * 0.18)
    base_color = color if color != (0.55, 0.55, 0.58) else (0.30, 0.39, 0.42)
    parts = (
        ("floor", (sx, sy, wall), (0, 0, -sz / 2 + wall / 2), tuple(c * 0.72 for c in base_color)),
        ("wall_xn", (wall, sy, sz), (-sx / 2 + wall / 2, 0, 0), base_color),
        ("wall_xp", (wall, sy, sz), (sx / 2 - wall / 2, 0, 0), base_color),
        ("wall_yn", (sx - 2 * wall, wall, sz), (0, -sy / 2 + wall / 2, 0), base_color),
        ("wall_yp", (sx - 2 * wall, wall, sz), (0, sy / 2 - wall / 2, 0), base_color),
    )
    for label, part_size, pos, shade in parts:
        _define_box(stage, f"{root_path}/visual/{label}", part_size, pos, shade, collision=False)


def _define_wire_threading_box_visual(
    stage: Any, root_path: str, size: tuple[float, float, float],
    color: tuple[float, float, float],
) -> None:
    """Pale box with a repeated grid of dark openings on the visible top."""
    from pxr import Gf, UsdGeom

    sx, sy, sz = size
    pale = color if color != (0.55, 0.55, 0.58) else (0.77, 0.75, 0.68)
    _define_box(stage, f"{root_path}/visual/body", size, (0, 0, 0), pale, collision=False)
    hole_r = min(sx, sy) * 0.027
    for row in range(4):
        for col in range(6):
            x = -sx * 0.38 + col * sx * 0.15
            y = -sy * 0.34 + row * sy * 0.22
            _define_cylinder(stage, f"{root_path}/visual/hole_{row}_{col}", hole_r, 0.001, (x, y, sz * 0.501), (0.08, 0.08, 0.07), collision=False)
    for side in (-1.0, 1.0):
        for index in range(4):
            y = -sy * 0.30 + index * sy * 0.20
            side_name = "neg" if side < 0 else "pos"
            _define_box(stage, f"{root_path}/visual/side_slot_{side_name}_{index}", (0.001, sy * 0.06, sz * 0.025), (side * sx * 0.501, y, 0), (0.25, 0.25, 0.23), collision=False)


def _define_green_bundle_visual(
    stage: Any, root_path: str, size: tuple[float, float, float],
    color: tuple[float, float, float],
) -> None:
    """Low irregular leafy bundle for the small green prop behind U04's keyboard."""
    from pxr import Gf, UsdGeom

    sx, sy, sz = size
    shades = (color, tuple(min(1.0, c * 0.82) for c in color),
              tuple(min(1.0, c * 1.08) for c in color))
    leaves = [
        (-0.30, -0.12, -12), (-0.08, 0.12, 18), (0.16, -0.08, -20),
        (0.32, 0.06, 14), (-0.02, -0.28, 8), (0.05, 0.30, -7),
    ]
    for index, (x, y, angle) in enumerate(leaves):
        leaf = UsdGeom.Sphere.Define(stage, f"{root_path}/visual/leaf_{index}")
        leaf.CreateRadiusAttr(1.0)
        leaf.AddTranslateOp().Set((x * sx, y * sy, (index % 2) * sz * 0.14))
        leaf.AddScaleOp().Set(Gf.Vec3f(sx * 0.24, sy * 0.22, sz * 0.34))
        leaf.AddRotateZOp().Set(angle)
        leaf.CreateDisplayColorAttr([Gf.Vec3f(*shades[index % len(shades)])])
    _define_box(stage, f"{root_path}/visual/core", (sx * 0.62, sy * 0.48, sz * 0.38), (0, 0, 0), shades[1], collision=False)


def _define_vented_fixture_visual(
    stage: Any, root_path: str, size: tuple[float, float, float],
    color: tuple[float, float, float],
) -> None:
    """Pale tabletop fixture with the dark horizontal vent slots seen in U19."""
    sx, sy, sz = size
    shell = color if color != (0.55, 0.55, 0.58) else (0.75, 0.71, 0.61)
    _define_box(stage, f"{root_path}/visual/shell", size, (0, 0, 0), shell, collision=False)
    for index in range(8):
        z = -sz * 0.30 + index * sz * 0.085
        _define_box(
            stage, f"{root_path}/visual/front_vent_{index}",
            (0.0015, sy * 0.76, max(0.001, sz * 0.018)),
            (-sx * 0.501, 0, z), (0.10, 0.11, 0.11), collision=False,
        )


def _define_wooden_cubby_shelf_visual(
    stage: Any, root_path: str, size: tuple[float, float, float],
    color: tuple[float, float, float],
) -> None:
    """Open-front wooden multi-level organizer with small lower cubbies."""
    sx, sy, sz = size
    wood = color if color != (0.55, 0.55, 0.58) else (0.66, 0.48, 0.29)
    wall = min(0.012, sx * 0.05, sy * 0.08)
    parts = [
        ("top", (sx, sy, wall), (0, 0, sz / 2 - wall / 2)),
        ("bottom", (sx, sy, wall), (0, 0, -sz / 2 + wall / 2)),
        ("left", (sx, wall, sz), (0, sy / 2 - wall / 2, 0)),
        ("right", (sx, wall, sz), (0, -sy / 2 + wall / 2, 0)),
        ("back", (wall, sy - 2 * wall, sz), (sx / 2 - wall / 2, 0, 0)),
        ("middle_shelf", (sx - wall, sy - 2 * wall, wall), (0, 0, -sz * 0.05)),
        ("lower_divider_left", (sx * 0.48, wall, sz * 0.40), (-sx * 0.25, 0, -sz * 0.27)),
        ("lower_divider_right", (sx * 0.48, wall, sz * 0.40), (sx * 0.25, 0, -sz * 0.27)),
    ]
    for label, part_size, pos in parts:
        _define_box(stage, f"{root_path}/visual/{label}", part_size, pos, wood, collision=False)


def _define_template_visual(
    stage: Any,
    root_path: str,
    name: str,
    template_ref: str | None,
    size: tuple[float, float, float],
    color: tuple[float, float, float],
    *,
    visual_only: bool,
    visual_geometry: dict[str, Any] | None = None,
    stage_output: Path,
) -> bool:
    """Render recognized scene-spec templates; return False for old dispatch."""
    from pxr import Gf, Sdf, UsdGeom

    aliases = {
        "white_paper_cup_v1": "paper_cup",
        "open_cup_v1": "paper_cup",
        "paper_cup_v1": "paper_cup",
        "blue_white_paper_cup_v1": "two_tone_paper_cup",
        "open_cylindrical_cup_v1": "straight_cup",
        "dark_rod_v1": "dark_rod",
        "green_soft_bundle_v1": "green_bundle",
        "vented_fixture_v1": "vented_fixture",
        "wooden_cubby_shelf_v1": "cubby_shelf",
        "folded_towel_rigid_proxy_v1": "towel",
        "folded_towel_v1": "towel",
        "wooden_open_drawer_v1": "drawer",
        "drawer_open_wood_v1": "drawer",
        "glove_pair_proxy_v1": "gloves",
        "fedora_proxy_v1": "hat",
        "wide_brim_hat_v1": "hat",
        "wooden_organizer_v1": "organizer",
        "low_two_tier_drawer_cabinet_v1": "two_tier_cabinet",
        "unidentified_pink_net_distractor_v1": "pink_net",
        "purple_cylinder_distractor_v1": "purple_cylinder",
        "purple_cylinder_v1": "purple_cylinder",
        "shallow_bowl_v1": "bowl",
        "plate_round_v1": "plate",
        "pencil_v1": "pencil",
        "mechanical_pencil_v1": "pencil",
        "marker_white_red_v1": "marker",
        "basket_woven_v1": "basket",
        "wicker_basket_v1": "basket",
        "grape_cluster_v1": "grapes",
        "toaster_v1": "toaster",
        "bread_loaf_v1": "loaf",
        "toast_slice_v1": "toast",
        "keyboard_v1": "keyboard",
        "shape_sorter_box_v1": "sorter",
        "paper_stack_v1": "papers",
        "binder_clip_v1": "clip",
        "drawstring_pouch_v1": "pouch",
        "cable_coil_v1": "cable",
        "tiered_wood_riser_v1": "riser",
        "mustard_bottle_v1": "mustard",
        "croissant_v1": "croissant",
        "orange_v1": "orange",
        "magnet_bar_v1": "magnet",
        "bar_magnet_v1": "magnet",
        "tripod_v1": "tripod",
        "orange_red_bowl_v1": "bowl",
        "orange_round_v1": "orange",
        "burger_layered_v1": "burger",
        "cutting_board_wood_v1": "cutting_board",
        "battery_aa_v1": "battery",
        "hex_nut_m12_v1": "nut",
        "shallow_rectangular_tray_v1": "tray",
        "straw_thin_v1": "straw",
        "tomato_chopped_cluster_v1": "tomato_cluster",
        "broccoli_floret_cluster_v1": "broccoli_cluster",
        "toaster_lever_v1": "toaster_lever",
        "wire_threading_box_v1": "wire_box",
        "sort_item_block_v1": "sort_block",
        "sort_item_round_block_v1": "round_block",
        "sort_item_short_cylinder_v1": "short_cylinder",
        "sort_item_sphere_v1": "sphere",
        "sort_item_triangle_block_v1": "triangle_block",
        "dark_olive_fedora_v1": "hat",
        "warm_red_bowl_v1": "bowl",
        "open_round_bowl_v1": "bowl",
        "shallow_rounded_yellow_vessel_v1": "bowl",
        "rounded_square_dish_v1": "square_dish",
        "shallow_round_plate_v1": "plate",
        "handled_pink_mug_v1": "handled_mug",
        "gently_curved_paper_stack_v1": "curved_papers",
        "multi_face_shape_sorter_box_v1": "sorter",
        "open_side_hole_box_v1": "wire_box",
        "open_two_cubby_shelf_v1": "cubby_shelf",
        "keyboard_keycap_v1": "sort_block",
        "small_reveal_token_v1": "round_block",
        "uncertain_blue_block_like_piece_v1": "sort_block",
        "uncertain_yellow_block_like_piece_v1": "sort_block",
        "uncertain_yellow_block_v1": "sort_block",
        "uncertain_blue_block_v1": "round_block",
        "red_cube_v1": "sort_block",
        "yellow_block_v1": "sort_block",
        "small_gray_metal_bar_v1": "sort_block",
        "slim_metal_implement_v1": "dark_rod",
        "small_metallic_parts_cluster_v1": "metal_parts",
        "handled_metal_pan_v1": "handled_pan",
        "black_qwerty_keyboard_with_legible_H_I_v1": "keyboard",
        "transparent_tall_drinking_glass_v1": "paper_cup",
    }
    template = aliases.get(str(template_ref or ""))
    if template is None:
        legacy_routes = {
            "scissors", "tape_rectangle_outline_v1", "pink_open_lattice_basket_v1",
            "curved_banana_visual_v1", "project_open_folding_fan_v1",
            "project_perforated_turquoise_basket_v1", "shallow_wire_mesh_strainer_v1",
            "apple_red_with_indented_top_v1", "kitchen_knife_v1", "spatula_v1",
        }
        if template_ref and template_ref not in legacy_routes:
            raise ValueError(f"Unimplemented visual template {template_ref!r} for {root_path}; refusing generic fallback")
        return False
    stage.GetPrimAtPath(root_path).CreateAttribute(
        "appendix_g:visual_backend", Sdf.ValueTypeNames.String
    ).Set("procedural:" + template)
    stage.GetPrimAtPath(root_path).CreateAttribute("appendix_g:source_asset", Sdf.ValueTypeNames.String).Set(
        "Project-authored geometry: " + str(template_ref))
    stage.GetPrimAtPath(root_path).CreateAttribute("appendix_g:source_license", Sdf.ValueTypeNames.String).Set(
        "See repository license; not a source scan")
    stage.GetPrimAtPath(root_path).CreateAttribute("appendix_g:proxy_geometry", Sdf.ValueTypeNames.Bool).Set(True)

    if template in {"handled_mug", "handled_pan"}:
        # Curved hollow vessel plus a visible handle, not a box substitute.
        body_size = (size[0] * .72, size[1], size[2]) if template == "handled_mug" else (size[0] * .63, size[1], size[2])
        body = UsdGeom.Xform.Define(stage, root_path + "/visual/vessel")
        body.AddTranslateOp().Set(((-size[0] * .14 if template == "handled_pan" else -size[0] * .12), 0., 0.))
        if template == "handled_mug":
            _define_straight_cup_visual(stage, str(body.GetPath()), body_size, color)
            handle = UsdGeom.Xform.Define(stage, root_path + "/visual/handle")
            handle.AddTranslateOp().Set((size[0] * .26, 0., 0.))
            handle.AddRotateXOp().Set(90.)
            _define_torus(stage, str(handle.GetPath()) + "/loop", (0., 0., 0.),
                          size[2] * .28, min(size) * .045, color, ring_segments=48)
        else:
            pan_color = tuple(channel * 0.78 for channel in color)
            pan_size = (size[0] * 0.62, size[1] * 0.82, max(0.028, size[2] * 0.76))
            _define_shallow_bowl_visual(stage, str(body.GetPath()), pan_size, pan_color)
            # Long, narrow metal handle joined to the pan rim; the old stubby
            # tab made the vessel read as a plate.
            _define_box(
                stage, root_path + "/visual/handle/metal_shank",
                (size[0] * 0.42, size[1] * 0.105, max(0.008, size[2] * 0.20)),
                (size[0] * 0.34, 0.0, -size[2] * 0.01),
                (0.34, 0.36, 0.38), collision=False,
            )
            _define_box(
                stage, root_path + "/visual/handle/grip",
                (size[0] * 0.10, size[1] * 0.12, max(0.010, size[2] * 0.23)),
                (size[0] * 0.50, 0.0, -size[2] * 0.01),
                (0.16, 0.17, 0.18), collision=False,
            )
        if not visual_only:
            _define_open_container(stage, root_path, body_size, color, hide_collision_geometry=True)
    elif template == "square_dish":
        # Superellipse rings yield rounded corners and a real shallow interior.
        sx, sy, sz = size
        points, indices = [], []
        profile = [(0.72,-.45), (.93,.15), (1.,.42), (.97,.5), (.89,.12), (.69,-.25), (0.,-.25)]
        segments = 64
        for radius, z in profile:
            for i in range(segments):
                angle = i * 2*math.pi/segments
                c, s = math.cos(angle), math.sin(angle)
                points.append((sx*.5*radius*math.copysign(abs(c)**.5,c),
                               sy*.5*radius*math.copysign(abs(s)**.5,s),sz*z))
        for ring in range(len(profile)-1):
            for i in range(segments):
                j=(i+1)%segments
                indices.extend((ring*segments+i,ring*segments+j,(ring+1)*segments+j,(ring+1)*segments+i))
        mesh = _define_mesh(stage, root_path+"/visual/rounded_dish", points, [4]*(len(indices)//4), indices, color)
        UsdGeom.Mesh(mesh).CreateDoubleSidedAttr(True)
        if not visual_only:
            _define_hidden_box_proxy(stage, root_path, size)
    elif template == "curved_papers":
        for layer in range(5):
            points, indices = [], []
            for row in range(13):
                y = size[1]*(row/12-.5)
                curl = size[2]*.35*(row/12)**4
                for x in (-size[0]*.5,size[0]*.5):
                    points.append((x,y,-size[2]*.45+layer*size[2]*.12+curl))
            for row in range(12):
                indices.extend((row*2,row*2+1,row*2+3,row*2+2))
            mesh=_define_mesh(stage,root_path+f"/visual/sheet_{layer}",points,[4]*12,indices,(.91,.91,.88))
            UsdGeom.Mesh(mesh).CreateDoubleSidedAttr(True)
        if not visual_only:
            _define_hidden_box_proxy(stage,root_path,size)
    elif template == "metal_parts":
        for i in range(6):
            part = UsdGeom.Xform.Define(stage,root_path+f"/visual/part_{i}")
            part.AddTranslateOp().Set((((i%3)-1)*size[0]*.28, ((i//3)-.5)*size[1]*.45, 0.))
            _define_hex_nut_visual(stage,str(part.GetPath()),(size[0]*.23,size[1]*.35,size[2]*.8),color)
        if not visual_only:
            _define_hidden_box_proxy(stage,root_path,size)
    elif template in {"paper_cup", "two_tone_paper_cup"}:
        if not visual_only:
            _define_open_container(stage, root_path, size, color, hide_collision_geometry=True)
        _define_paper_cup_visual(stage, root_path, size, color)
        appearance = str((visual_geometry or {}).get("appearance", "")).lower()
        if "clear" in appearance or "transparent" in appearance or "glass" in appearance:
            opacity = 1.0 - float((visual_geometry or {}).get("transparency", 0.28))
            glass_color = tuple(float(channel) for channel in
                                (visual_geometry or {}).get(
                                    "material_rgb", color if color != (0.55, 0.55, 0.58)
                                    else (0.72, 0.79, 0.80)))
            for part in ("cup_outer", "cup_inner", "cup_rim", "cup_bottom"):
                _bind_translucent_preview_material(
                    stage, f"{root_path}/visual/{part}",
                    f"{root_path}/material/clear_glass_{part}",
                    glass_color,
                    opacity,
                )
        if template == "two_tone_paper_cup":
            height = size[2] * 0.30
            top_radius = min(size[0], size[1]) * 0.48
            bottom_radius = top_radius * 0.72
            band_parent = UsdGeom.Xform.Define(stage, f"{root_path}/visual/white_top_band")
            band_parent.AddTranslateOp().Set((0, 0, size[2] * 0.32))
            band_bottom = bottom_radius + (top_radius - bottom_radius) * 0.70
            _define_frustum_side(
                stage, f"{root_path}/visual/white_top_band/mesh",
                band_bottom, top_radius, height, (0.94, 0.94, 0.91),
            )
    elif template == "straight_cup":
        if not visual_only:
            _define_open_container(stage, root_path, size, color, hide_collision_geometry=True)
        _define_straight_cup_visual(stage, root_path, size, color)
    elif template == "bowl":
        if not visual_only:
            _define_open_container(stage, root_path, size, color, hide_collision_geometry=True)
        _define_shallow_bowl_visual(stage, root_path, size, color)
    elif template == "plate":
        # A plate has a shallow concave center and raised lip; a flat cylinder
        # made the bread look as if it were resting on a disk.
        _define_shallow_bowl_visual(stage, root_path, size, color)
        if not visual_only:
            _define_hidden_box_proxy(stage, root_path, size)
    elif template == "pencil":
        _define_pencil_visual(stage, root_path, size, color)
        if not visual_only:
            _define_hidden_box_proxy(stage, root_path, size)
    elif template == "marker":
        long_axis = 0 if size[0] >= size[1] else 1
        diameter = min(size[axis] for axis in range(3) if axis != long_axis)
        length, axis = size[long_axis], ("X" if long_axis == 0 else "Y")
        cap_center = length * 0.42
        _define_cylinder(stage, f"{root_path}/visual/barrel", diameter * 0.46, length * 0.82, (0, 0, 0), (0.92, 0.91, 0.87), axis=axis)
        cap_pos = (cap_center, 0, 0) if axis == "X" else (0, cap_center, 0)
        _define_cylinder(stage, f"{root_path}/visual/red_cap", diameter * 0.50, length * 0.16, cap_pos, (0.78, 0.055, 0.035), axis=axis)
        if not visual_only:
            _define_hidden_box_proxy(stage, root_path, size)
    elif template == "towel":
        _define_towel_visual(stage, root_path, size, color, stage_output)
        if not visual_only:
            _define_hidden_box_proxy(stage, root_path, size)
    elif template == "drawer":
        _define_open_container(stage, root_path, size, (0.28, 0.14, 0.07), hide_collision_geometry=True)
        _define_open_drawer_visual(stage, root_path, size)
    elif template == "gloves":
        _define_glove_pair_visual(stage, root_path, size, color)
        if not visual_only:
            _define_hidden_box_proxy(stage, root_path, size)
    elif template == "basket":
        basket_color = color if color != (0.55, 0.55, 0.58) else (0.70, 0.48, 0.22)
        if not visual_only:
            _define_open_container(stage, root_path, size, basket_color, hide_collision_geometry=True)
        from appendix_g_visuals_v7 import draw_wicker_basket
        draw_wicker_basket(stage, root_path, size, basket_color)
    elif template == "hat":
        hat_color = color if color != (0.55, 0.55, 0.58) else (0.055, 0.045, 0.04)
        from appendix_g_visuals_v7 import draw_hat
        draw_hat(stage, root_path, size, hat_color)
        if not visual_only:
            _define_hidden_box_proxy(stage, root_path, size)
    elif template == "organizer":
        _define_two_tier_cabinet_visual(
            stage, root_path, size, color,
            drawer_state=str((visual_geometry or {}).get("drawer_state", "closed")),
        )
        if not visual_only:
            _define_hidden_box_proxy(stage, root_path, size)
    elif template == "two_tier_cabinet":
        _define_two_tier_cabinet_visual(
            stage, root_path, size, color,
            drawer_state=str((visual_geometry or {}).get("drawer_state", "upper_open")),
        )
        if not visual_only:
            if str((visual_geometry or {}).get("drawer_state", "upper_open")) == "visible_closed_fronts":
                # A closed cabinet must support objects on its visible top.
                # Open-container walls leave that supporting surface absent.
                _define_hidden_box_proxy(stage, root_path, size)
            else:
                _define_open_container(
                    stage, root_path, size, (0.25, 0.12, 0.06),
                    hide_collision_geometry=True,
                )
    elif template == "pink_net":
        net_color = color if color != (0.55, 0.55, 0.58) else (0.92, 0.12, 0.48)
        _define_pink_net_v7(stage, root_path, size, net_color)
        if not visual_only:
            _define_hidden_box_proxy(stage, root_path, size)
    elif template == "purple_cylinder":
        _define_cylinder(stage, f"{root_path}/visual/cylinder", min(size[0], size[1]) * 0.48, size[2], (0, 0, 0), color if color != (0.55, 0.55, 0.58) else (0.34, 0.12, 0.53), collision=False)
        if not visual_only:
            _define_hidden_box_proxy(stage, root_path, size)
    elif template == "dark_rod":
        length, radius = max(size), max(0.0015, min(size) * 0.5)
        axis = "X" if size[0] == length else ("Y" if size[1] == length else "Z")
        _define_cylinder(
            stage, f"{root_path}/visual/rod", radius, length, (0, 0, 0),
            color if color != (0.55, 0.55, 0.58) else (0.035, 0.035, 0.04),
            axis=axis, collision=False,
        )
        if not visual_only:
            _define_hidden_box_proxy(stage, root_path, size)
    elif template == "apple":
        # The local YCB apple scan remains the preferred textured model; this
        # branch is only needed when a task uses a separately named red apple.
        apple = UsdGeom.Sphere.Define(stage, f"{root_path}/visual/apple_fallback")
        apple.CreateRadiusAttr(1.0)
        apple.AddScaleOp().Set(Gf.Vec3f(size[0] * 0.48, size[1] * 0.46, size[2] * 0.48))
        apple.CreateDisplayColorAttr([Gf.Vec3f(* (color if color != (0.55, 0.55, 0.58) else (0.78, 0.035, 0.025)))])
        _define_cylinder(stage, f"{root_path}/visual/stem", 0.002, size[2] * 0.12, (0, 0, size[2] * 0.48), (0.24, 0.14, 0.06), collision=False)
        if not visual_only:
            _define_hidden_box_proxy(stage, root_path, size)
    elif template == "grapes":
        from appendix_g_visuals_v7 import draw_grape_cluster
        draw_grape_cluster(stage, root_path, size, color)
        if not visual_only:
            _define_hidden_box_proxy(stage, root_path, size)
    elif template == "toaster":
        _define_toaster_visual(
            stage, root_path, size, color,
            power_cord=bool((visual_geometry or {}).get("power_cord", False)),
        )
        collision_profile = str((visual_geometry or {}).get("collision_profile", ""))
        if collision_profile:
            _define_profile_collision(
                stage, root_path, collision_profile, size, visual_geometry or {}
            )
        elif not visual_only:
            _define_hidden_box_proxy(stage, root_path, size)
    elif template in {"loaf", "toast"}:
        if template == "loaf":
            loaf = UsdGeom.Sphere.Define(stage, f"{root_path}/visual/loaf")
            loaf.CreateRadiusAttr(1.0)
            loaf.AddScaleOp().Set(Gf.Vec3f(size[0] * 0.50, size[1] * 0.50, size[2] * 0.50))
            loaf.CreateDisplayColorAttr([Gf.Vec3f(*(color if color != (0.55, 0.55, 0.58) else (0.70, 0.39, 0.16)))])
            _define_box(stage, f"{root_path}/visual/crust_base", (size[0] * 0.84, size[1] * 0.84, size[2] * 0.20), (0, 0, -size[2] * 0.36), (0.42, 0.22, 0.09), collision=False)
        else:
            _define_toast_visual(stage, root_path, size, color)
        if not visual_only:
            _define_hidden_box_proxy(stage, root_path, size)
    elif template == "keyboard":
        _define_keyboard_visual(stage, root_path, size, color, stage_output)
        if not visual_only:
            _define_hidden_box_proxy(stage, root_path, size)
    elif template == "sorter":
        from appendix_g_holes_v7 import draw_shape_sorter
        visual_root = draw_shape_sorter(stage, root_path, size, color)
        if not visual_only:
            # The old hidden bounding box sealed every aperture. Static mesh
            # collision preserves the through-holes authored in the lid/walls.
            _apply_mesh_collisions(stage, visual_root)
    elif template == "burger":
        _define_burger_visual(stage, root_path, size, color)
        if not visual_only:
            _define_hidden_box_proxy(stage, root_path, size)
    elif template == "cutting_board":
        _define_box(stage, f"{root_path}/visual/board", size, (0, 0, 0), color if color != (0.55, 0.55, 0.58) else (0.55, 0.34, 0.18), collision=False)
        for index in range(5):
            y = -size[1] * 0.38 + index * size[1] * 0.19
            _define_box(stage, f"{root_path}/visual/grain_{index}", (size[0] * 0.80, 0.0015, 0.0008), (0, y, size[2] * 0.51), (0.40, 0.23, 0.11), collision=False)
        if not visual_only:
            _define_hidden_box_proxy(stage, root_path, size)
    elif template == "battery":
        radius = min(size[0], size[1]) * 0.46
        cell_color = color if color != (0.55, 0.55, 0.58) else (0.10, 0.20, 0.48)
        _define_cylinder(stage, f"{root_path}/visual/cell", radius, size[2] * 0.94,
                         (0, 0, 0), cell_color, collision=False)
        _define_cylinder(stage, f"{root_path}/visual/positive_cap", radius * 0.72,
                         max(0.0015, size[2] * 0.035), (0, 0, size[2] * 0.49),
                         (0.72, 0.73, 0.70), collision=False)
        _define_cylinder(stage, f"{root_path}/visual/positive_terminal", radius * 0.25,
                         max(0.0015, size[2] * 0.055), (0, 0, size[2] * 0.53),
                         (0.79, 0.80, 0.77), collision=False)
        _define_cylinder(stage, f"{root_path}/visual/negative_end", radius * 0.98,
                         max(0.001, size[2] * 0.025), (0, 0, -size[2] * 0.48),
                         (0.36, 0.37, 0.38), collision=False)
        for index, z_fraction in enumerate((-0.23, 0.20)):
            _define_cylinder(stage, f"{root_path}/visual/label_band_{index}",
                             radius * 1.012, max(0.0012, size[2] * 0.035),
                             (0, 0, size[2] * z_fraction), (0.80, 0.77, 0.60),
                             collision=False)
        if not visual_only:
            _define_hidden_box_proxy(stage, root_path, size)
    elif template == "nut":
        _define_hex_nut_visual(stage, root_path, size, color)
        if not visual_only:
            _define_hidden_box_proxy(stage, root_path, size)
    elif template == "tray":
        if not visual_only:
            _define_open_container(stage, root_path, size, color, hide_collision_geometry=True)
        _define_tray_visual(stage, root_path, size, color)
    elif template == "green_bundle":
        _define_green_bundle_visual(stage, root_path, size, color)
        if not visual_only:
            _define_hidden_box_proxy(stage, root_path, size)
    elif template == "vented_fixture":
        _define_vented_fixture_visual(stage, root_path, size, color)
        if not visual_only:
            _define_hidden_box_proxy(stage, root_path, size)
    elif template == "cubby_shelf":
        _define_wooden_cubby_shelf_visual(stage, root_path, size, color)
        if not visual_only:
            _define_hidden_box_proxy(stage, root_path, size)
    elif template == "straw":
        axis, length = ("Z", size[2]) if size[2] >= max(size[0], size[1]) else (("X", size[0]) if size[0] >= size[1] else ("Y", size[1]))
        _define_cylinder(stage, f"{root_path}/visual/straw", min(size) * 0.48, length, (0, 0, 0), color, axis=axis, collision=False)
        if not visual_only:
            _define_hidden_box_proxy(stage, root_path, size)
    elif template in {"tomato_cluster", "broccoli_cluster"}:
        _define_vegetable_cluster_visual(stage, root_path, size, color, broccoli=template == "broccoli_cluster")
        if not visual_only:
            _define_hidden_box_proxy(stage, root_path, size)
    elif template == "toaster_lever":
        _define_cylinder(stage, f"{root_path}/visual/lever_stem", min(size[1], size[2]) * 0.35, size[2] * 0.88, (0, 0, 0), color if color != (0.55, 0.55, 0.58) else (0.62, 0.62, 0.60), collision=False)
        _define_box(stage, f"{root_path}/visual/lever_grip", (size[0], size[1] * 1.5, size[2] * 0.24), (0, 0, size[2] * 0.35), (0.30, 0.31, 0.31), collision=False)
        if not visual_only:
            _define_hidden_box_proxy(stage, root_path, size)
    elif template == "wire_box":
        from appendix_g_holes_v7 import draw_wire_box
        visual_root = draw_wire_box(stage, root_path, size, color)
        if not visual_only:
            _apply_mesh_collisions(stage, visual_root)
    elif template in {"sort_block", "round_block", "short_cylinder", "sphere", "triangle_block"}:
        if template == "round_block":
            _define_cylinder(stage, f"{root_path}/visual/round_block", min(size[0], size[1]) * 0.48, size[2], (0, 0, 0), color, collision=False)
        elif template == "short_cylinder":
            _define_cylinder(stage, f"{root_path}/visual/cylinder", min(size[0], size[1]) * 0.48, size[2], (0, 0, 0), color, collision=False)
        elif template == "sphere":
            sphere = UsdGeom.Sphere.Define(stage, f"{root_path}/visual/sphere")
            sphere.CreateRadiusAttr(max(size) * 0.5)
            sphere.AddScaleOp().Set(Gf.Vec3f(size[0] / max(size), size[1] / max(size), size[2] / max(size)))
            sphere.CreateDisplayColorAttr([Gf.Vec3f(*color)])
        elif template == "triangle_block":
            hx, hy, hz = size[0] / 2.0, size[1] / 2.0, size[2] / 2.0
            points = [(-hx, -hy, -hz), (hx, -hy, -hz), (0, hy, -hz),
                      (-hx, -hy, hz), (hx, -hy, hz), (0, hy, hz)]
            _define_mesh(stage, f"{root_path}/visual/triangle_prism", points,
                         [3, 3, 4, 4, 4], [0, 2, 1, 3, 4, 5, 0, 1, 4, 3,
                         1, 2, 5, 4, 2, 0, 3, 5], color)
        else:
            _define_box(stage, f"{root_path}/visual/block", size, (0, 0, 0), color, collision=False)
        if not visual_only:
            _define_hidden_box_proxy(stage, root_path, size)
    elif template == "papers":
        for index in range(5):
            _define_box(stage, f"{root_path}/visual/sheet_{index}", (size[0] * (0.99 - index * 0.012), size[1] * (0.99 - index * 0.012), size[2] / 5.0), (0.0, (index % 2) * size[1] * 0.018, -size[2] * 0.40 + index * size[2] * 0.20), (0.91, 0.91, 0.88), collision=False)
        if not visual_only:
            _define_hidden_box_proxy(stage, root_path, size)
    elif template == "clip":
        _define_box(stage, f"{root_path}/visual/clip_body", (size[0], size[1], size[2] * 0.58), (0, 0, -size[2] * 0.18), (0.12, 0.13, 0.14), collision=False)
        if not visual_only:
            _define_hidden_box_proxy(stage, root_path, size)
    elif template == "pouch":
        _define_drawstring_pouch_visual(stage, root_path, size, color, stage_output)
        if not visual_only:
            _define_hidden_box_proxy(stage, root_path, size)
    elif template == "cable":
        sx, sy, sz = size
        geometry = visual_geometry or {}
        coil_diameter = float(geometry.get("coil_diameter_m", min(sx, sy) * 0.68))
        radius, tube = min(coil_diameter * 0.5, sy * 0.46), max(0.002, min(sy, sz) * 0.028)
        cable_color = color if color != (0.55, 0.55, 0.58) else (0.035, 0.04, 0.045)
        for index in range(3):
            _define_torus(stage, f"{root_path}/visual/coil_{index}", (0, 0, -sz * 0.15 + index * sz * 0.15), radius * (1.0 - index * 0.08), tube, cable_color, ring_segments=40, tube_segments=8)
        _define_box(stage, f"{root_path}/visual/cable_tail_a", (sx * 0.30, tube * 1.5, tube * 1.5), (-sx * 0.36, 0, 0), cable_color, collision=False)
        _define_box(stage, f"{root_path}/visual/cable_tail_b", (sx * 0.24, tube * 1.5, tube * 1.5), (sx * 0.38, 0, sz * 0.08), cable_color, collision=False)
        if not visual_only:
            _define_hidden_box_proxy(stage, root_path, size)
    elif template == "riser":
        sx, sy, sz = size
        wood = color if color != (0.55, 0.55, 0.58) else (0.48, 0.28, 0.14)
        for index in range(3):
            width, depth, height = sx * (1.0 - index * 0.18), sy * (0.40 + index * 0.20), sz * (0.24 + index * 0.08)
            x, z = -sx * 0.30 + index * sx * 0.30, -sz * 0.5 + height * (index + 0.5)
            _define_box(stage, f"{root_path}/visual/step_{index}", (width, depth, height), (x, 0, z), tuple(min(1.0, c * (1.0 - index * 0.06)) for c in wood), collision=False)
        if not visual_only:
            _define_hidden_box_proxy(stage, root_path, size)
    elif template == "mustard":
        sx, sy, sz = size
        radius = min(sx, sy) * 0.46
        yellow = color if color != (0.55, 0.55, 0.58) else (0.91, 0.66, 0.04)
        for label, r, h, z, shade in (
            ("body", radius, sz * 0.68, -sz * 0.06, yellow),
            ("shoulder", radius * 0.68, sz * 0.16, sz * 0.34, (0.92, 0.69, 0.04)),
            ("neck", radius * 0.34, sz * 0.12, sz * 0.47, yellow),
            ("cap", radius * 0.40, sz * 0.08, sz * 0.56, (0.83, 0.08, 0.045)),
        ):
            _define_cylinder(stage, f"{root_path}/visual/{label}", r, h, (0, 0, z), shade, collision=False)
        if not visual_only:
            _define_hidden_box_proxy(stage, root_path, size)
    elif template == "croissant":
        sx, sy, sz = size
        gold = color if color != (0.55, 0.55, 0.58) else (0.80, 0.48, 0.12)
        for index in range(7):
            t = index / 6.0
            x, z = -sx * 0.42 + sx * 0.84 * t, -sz * 0.10 + sz * 0.22 * math.sin(math.pi * t)
            radius = min(sy, sz) * (0.23 + 0.18 * math.sin(math.pi * t))
            segment = UsdGeom.Sphere.Define(stage, f"{root_path}/visual/segment_{index}")
            segment.CreateRadiusAttr(1.0)
            segment.AddTranslateOp().Set((x, 0, z))
            segment.AddScaleOp().Set(Gf.Vec3f(sx * 0.10, radius, radius))
            segment.CreateDisplayColorAttr([Gf.Vec3f(*gold)])
        if not visual_only:
            _define_hidden_box_proxy(stage, root_path, size)
    elif template == "orange":
        orange = UsdGeom.Sphere.Define(stage, f"{root_path}/visual/orange")
        orange.CreateRadiusAttr(1.0)
        orange.AddScaleOp().Set(Gf.Vec3f(size[0] * 0.48, size[1] * 0.48, size[2] * 0.48))
        orange.CreateDisplayColorAttr([Gf.Vec3f(*(color if color != (0.55, 0.55, 0.58) else (0.96, 0.38, 0.035)))])
        _define_cylinder(stage, f"{root_path}/visual/stem", 0.002, size[2] * 0.08, (0, 0, size[2] * 0.47), (0.22, 0.16, 0.06), collision=False)
        if not visual_only:
            _define_hidden_box_proxy(stage, root_path, size)
    elif template == "magnet":
        _define_box(stage, f"{root_path}/visual/bar", size, (0, 0, 0), color if color != (0.55, 0.55, 0.58) else (0.78, 0.04, 0.04), collision=False)
        for sign in (-1.0, 1.0):
            side_name = "neg" if sign < 0 else "pos"
            _define_box(stage, f"{root_path}/visual/end_{side_name}", (size[0] * 0.18, size[1] * 1.02, size[2] * 1.02), (sign * size[0] * 0.41, 0, 0), (0.80, 0.80, 0.78), collision=False)
        if not visual_only:
            _define_hidden_box_proxy(stage, root_path, size)
    elif template == "tripod":
        from appendix_g_visuals_v7 import draw_tripod
        draw_tripod(stage, root_path, size, color)
        if not visual_only:
            _define_hidden_box_proxy(stage, root_path, size)
    else:
        return False
    return True


def _define_u02_folding_fan(
    stage: Any, root_path: str, size: tuple[float, float, float]
) -> None:
    """Create an open folding-fan visual and a stable, hidden box collider."""
    from pxr import Gf, UsdGeom

    span_x, span_y, thickness = size
    half_angle = math.radians(62.0)
    radius = min(span_x * 0.46, span_y * 0.50 / math.sin(half_angle))
    pivot_x = -span_x * 0.26
    panel_z = thickness * 0.05
    segments = 12
    angles = [
        -half_angle + (2.0 * half_angle * index / segments)
        for index in range(segments + 1)
    ]

    fan_points = [Gf.Vec3f(pivot_x, 0.0, panel_z)]
    fan_points.extend(
        Gf.Vec3f(
            pivot_x + radius * math.cos(angle),
            radius * math.sin(angle),
            panel_z,
        )
        for angle in angles
    )
    leaf = UsdGeom.Mesh.Define(stage, f"{root_path}/visual/fan_leaf")
    leaf.CreatePointsAttr(fan_points)
    leaf.CreateFaceVertexCountsAttr([3] * segments)
    leaf.CreateFaceVertexIndicesAttr(
        [index for segment in range(segments) for index in (0, segment + 1, segment + 2)]
    )
    leaf.CreateSubdivisionSchemeAttr(UsdGeom.Tokens.none)
    leaf.CreateDoubleSidedAttr(True)
    leaf.CreateDisplayColorAttr([Gf.Vec3f(0.94, 0.94, 0.91)])

    # Fine gray spokes give the white sector the recognizable folded-rib look.
    for index in range(1, segments):
        angle = angles[index]
        direction_x, direction_y = math.cos(angle), math.sin(angle)
        inner_radius = 0.006
        outer_radius = radius * 0.97
        half_width = 0.0008
        side_x, side_y = -direction_y * half_width, direction_x * half_width
        rib = UsdGeom.Mesh.Define(stage, f"{root_path}/visual/rib_{index:02d}")
        rib.CreatePointsAttr(
            [
                Gf.Vec3f(
                    pivot_x + inner_radius * direction_x + side_x,
                    inner_radius * direction_y + side_y,
                    panel_z + thickness * 0.03,
                ),
                Gf.Vec3f(
                    pivot_x + outer_radius * direction_x + side_x,
                    outer_radius * direction_y + side_y,
                    panel_z + thickness * 0.03,
                ),
                Gf.Vec3f(
                    pivot_x + outer_radius * direction_x - side_x,
                    outer_radius * direction_y - side_y,
                    panel_z + thickness * 0.03,
                ),
                Gf.Vec3f(
                    pivot_x + inner_radius * direction_x - side_x,
                    inner_radius * direction_y - side_y,
                    panel_z + thickness * 0.03,
                ),
            ]
        )
        rib.CreateFaceVertexCountsAttr([4])
        rib.CreateFaceVertexIndicesAttr([0, 1, 2, 3])
        rib.CreateSubdivisionSchemeAttr(UsdGeom.Tokens.none)
        rib.CreateDoubleSidedAttr(True)
        rib.CreateDisplayColorAttr([Gf.Vec3f(0.48, 0.49, 0.50)])

    handle_length = min(span_x * 0.42, 0.062)
    _define_box(
        stage,
        f"{root_path}/visual/fan_handle",
        (handle_length, max(0.006, span_y * 0.055), max(0.003, thickness * 0.48)),
        (pivot_x - handle_length * 0.48, 0.0, -thickness * 0.25),
        (0.78, 0.77, 0.72),
        collision=False,
    )

    # This thin rectangle approximates the fan leaf and handle for contact;
    # the perforated fan mesh itself is deliberately visual-only.
    collider = _define_box(
        stage,
        f"{root_path}/geometry/collision_proxy",
        (span_x * 0.99, span_y * 0.99, max(0.004, thickness * 0.50)),
        (-span_x * 0.16, 0.0, -thickness * 0.25),
        (0.5, 0.5, 0.5),
        collision=True,
    )
    UsdGeom.Imageable(collider).CreateVisibilityAttr().Set(UsdGeom.Tokens.invisible)


def _define_object(
    stage: Any,
    name: str,
    pos: tuple[float, float, float],
    layout_id: int,
    task_id: str,
    target: str | None,
    stage_output: Path,
    object_spec: dict[str, Any] | None = None,
) -> Any:
    from pxr import Gf, Sdf, UsdGeom, UsdPhysics

    object_spec = object_spec or {}
    safe_name = _safe_id(name)
    root_path = f"/World/{safe_name}"
    root = UsdGeom.Xform.Define(stage, root_path)
    root.AddTranslateOp().Set(Gf.Vec3d(*pos))
    # U01 starts with the handle facing -X; its "right" instruction means +X
    # in this local robot-frame proxy convention.
    if task_id in {"S01", "S02"}:
        # YCB 037 scissors has its handles on local -Y; retain the S01
        # image-matched orientation. The marker's red cap faces image-right.
        yaw_deg = {"scissors": -35.0, "marker": 80.0, "blue_box": 180.0}.get(name, 0.0)
        half_angle = math.radians(yaw_deg) / 2.0
        initial_quat = Gf.Quatf(
            math.cos(half_angle), Gf.Vec3f(0.0, 0.0, math.sin(half_angle))
        )
    else:
        initial_quat = (
            Gf.Quatf(0.0, 0.0, 0.0, 1.0)
            if task_id == "U01"
            else Gf.Quatf(1.0, 0.0, 0.0, 0.0)
        )
    pose_rpy = object_spec.get("_pose_rpy_deg")
    if pose_rpy is not None:
        roll, pitch, yaw = (math.radians(float(value)) for value in pose_rpy)
        cr, sr = math.cos(roll / 2.0), math.sin(roll / 2.0)
        cp, sp = math.cos(pitch / 2.0), math.sin(pitch / 2.0)
        cy, sy = math.cos(yaw / 2.0), math.sin(yaw / 2.0)
        initial_quat = Gf.Quatf(
            cr * cp * cy + sr * sp * sy,
            Gf.Vec3f(
                sr * cp * cy - cr * sp * sy,
                cr * sp * cy + sr * cp * sy,
                cr * cp * sy - sr * sp * cy,
            ),
        )
    root.AddOrientOp().Set(initial_quat)
    prim = root.GetPrim()
    mobility = str(object_spec.get("mobility", "dynamic_rigid_body"))
    role = str(object_spec.get("role", ""))
    is_static = bool(
        object_spec.get(
            "static",
            mobility.startswith("static")
            or mobility in {"kinematic", "static_fixture"},
        )
    )
    visual_only = mobility in {"visual_only", "static_visual_distractor"} or (
        object_spec.get("collision_geometry") == "none"
    )
    if not visual_only:
        rigid_body = UsdPhysics.RigidBodyAPI.Apply(prim)
        rigid_body.CreateRigidBodyEnabledAttr(True)
        if is_static:
            rigid_body.CreateKinematicEnabledAttr(True)
        else:
            mass = UsdPhysics.MassAPI.Apply(prim)
            mass.CreateMassAttr(
                0.06 if task_id in {"S01", "S02"} and name == "scissors" else 0.15
            )
    prim.CreateAttribute("appendix_g:semantic_name", Sdf.ValueTypeNames.String).Set(name)
    prim.CreateAttribute("appendix_g:task_id", Sdf.ValueTypeNames.String).Set(task_id)
    prim.CreateAttribute("appendix_g:layout_id", Sdf.ValueTypeNames.Int).Set(layout_id)
    prim.CreateAttribute("appendix_g:target_name", Sdf.ValueTypeNames.String).Set(target or "")
    visual_geometry = object_spec.get("visual_geometry", {})
    if visual_geometry.get("render_hidden", False):
        UsdGeom.Imageable(prim).CreateVisibilityAttr().Set(UsdGeom.Tokens.invisible)
        prim.CreateAttribute("appendix_g:visual_backend", Sdf.ValueTypeNames.String).Set("explicitly_hidden_placeholder")
        # Unimplemented interaction placeholders must not add unseen contact
        # obstacles to a visually reconstructed initial scene.
        if prim.HasAPI(UsdPhysics.RigidBodyAPI):
            prim.RemoveAPI(UsdPhysics.RigidBodyAPI)
        return prim
    template_ref = (
        visual_geometry.get("template_ref")
        if isinstance(visual_geometry, dict)
        else None
    )
    external_asset = (
        visual_geometry.get("asset_path")
        if isinstance(visual_geometry, dict)
        else None
    )
    has_ycb_visual = name in YCB_MODEL_FILES or name == "scissors"
    if template_ref in {
        "shallow_bowl_v1", "orange_red_bowl_v1", "marker_white_red_v1",
    } and name in {"bowl", "marker"}:
        # These image-matched color/silhouette templates deliberately replace
        # the registered YCB scan; do not record a scan as the rendered asset.
        has_ycb_visual = False
    if task_id in {"S01", "S02"} and name == "marker":
        has_ycb_visual = False  # image-matched white/red project-authored marker
    if task_id == "S07" and name == "pan":
        has_ycb_visual = False  # the paper shows a small wire strainer, not a skillet
    if has_ycb_visual:
        source_name = (
            "YCB 037 Scissors"
            if name == "scissors"
            else YCB_MODEL_FILES[name][1]
        )
        prim.CreateAttribute("appendix_g:source_asset", Sdf.ValueTypeNames.String).Set(
            source_name
        )
        prim.CreateAttribute("appendix_g:source_license", Sdf.ValueTypeNames.String).Set(
            "CC-BY-4.0"
        )
    if task_id == "S02" and name == "blue_box":
        prim.CreateAttribute("appendix_g:source_asset", Sdf.ValueTypeNames.String).Set(
            "Project-authored perforated turquoise basket"
        )
        prim.CreateAttribute("appendix_g:source_license", Sdf.ValueTypeNames.String).Set(
            "CC0-1.0"
        )
    if external_asset:
        prim.CreateAttribute("appendix_g:source_asset", Sdf.ValueTypeNames.String).Set(
            str(visual_geometry.get("source_asset", external_asset))
        )
        prim.CreateAttribute("appendix_g:source_license", Sdf.ValueTypeNames.String).Set(
            str(visual_geometry.get("source_license", "unspecified"))
        )
    uses_external_visual = has_ycb_visual or bool(external_asset)
    prim.CreateAttribute("appendix_g:proxy_geometry", Sdf.ValueTypeNames.Bool).Set(
        not uses_external_visual
    )

    size = tuple(
        float(value)
        for value in object_spec.get("dimensions_m", _object_size(name, task_id))
    )
    color = tuple(
        float(value)
        for value in object_spec.get("color_rgb", COLORS.get(name, (0.55, 0.55, 0.58)))
    )
    shape = _shape_for(name)
    effective_template_ref = template_ref or _default_template_for_object(name, task_id)
    uses_open_wicker_collision = (
        bool(external_asset) and effective_template_ref == "wicker_basket_v1"
    )
    if external_asset:
        if uses_open_wicker_collision:
            # Keep the robust open-top contact proxy while replacing only the
            # procedural basket appearance with the textured public scan.
            _define_open_container(
                stage, root_path, size, color, hide_collision_geometry=True
            )
        asset_path = (PROJECT_ROOT / str(external_asset)).resolve()
        if PROJECT_ROOT.resolve() not in asset_path.parents:
            raise ValueError(f"External asset path must stay inside the repository: {external_asset}")
        _define_external_glb_visual(
            stage, root_path, asset_path, size, stage_output,
            str(visual_geometry.get("orientation", "y_up_to_z_up")), color,
            tuple(float(value) for value in visual_geometry.get(
                "texture_tint_rgb", (1.0, 1.0, 1.0)
            )),
        )
        collision_profile = str(visual_geometry.get("collision_profile", ""))
        if collision_profile:
            _define_profile_collision(
                stage, root_path, collision_profile, size, visual_geometry
            )
        elif not visual_only and not uses_open_wicker_collision:
            _define_hidden_box_proxy(stage, root_path, size)
    elif _define_template_visual(
        stage, root_path, name, effective_template_ref, size, color,
        visual_only=visual_only, visual_geometry=visual_geometry,
        stage_output=stage_output,
    ):
        pass
    elif template_ref == "tape_rectangle_outline_v1":
        _define_tape_outline(stage, root_path, size)
    elif template_ref == "pink_open_lattice_basket_v1":
        _define_open_container(
            stage, root_path, size, (0.36, 0.04, 0.11), hide_collision_geometry=True
        )
        _define_lattice_basket_visual(stage, root_path, size)
    elif template_ref == "curved_banana_visual_v1":
        _define_curved_banana_visual(stage, root_path, size)
    elif task_id == "S01" and name == "cup":
        _define_open_container(
            stage, root_path, size, color, hide_collision_geometry=True
        )
        _define_s01_cup_visual(stage, root_path, size)
    elif task_id == "S01" and name == "marker":
        _define_white_red_marker(stage, root_path)
    elif task_id == "S02" and name == "marker":
        _define_white_red_marker(stage, root_path)
    elif task_id in {"S01", "S02", "S09", "U03", "U15"} and name == "scissors":
        _define_s01_scissors(stage, root_path, stage_output)
    elif template_ref == "project_open_folding_fan_v1":
        _define_u02_folding_fan(stage, root_path, size)
    elif task_id == "S02" and name == "blue_box":
        _define_open_container(
            stage, root_path, size, color, hide_collision_geometry=True
        )
        draw_blue_basket(stage, root_path, size, color)
    elif task_id == "S07" and name == "pan":
        _define_open_container(
            stage, root_path, size, color, hide_collision_geometry=True
        )
        _define_s07_wire_strainer_visual(stage, root_path, size)
    elif external_asset:
        asset_path = (PROJECT_ROOT / str(external_asset)).resolve()
        if PROJECT_ROOT.resolve() not in asset_path.parents:
            raise ValueError(f"External asset path must stay inside the repository: {external_asset}")
        _define_external_glb_visual(
            stage,
            root_path,
            asset_path,
            size,
            stage_output,
            str(visual_geometry.get("orientation", "y_up_to_z_up")),
            color,
            tuple(float(value) for value in visual_geometry.get(
                "texture_tint_rgb", (1.0, 1.0, 1.0)
            )),
        )
        collision_profile = str(visual_geometry.get("collision_profile", ""))
        _define_profile_collision(
            stage, root_path, collision_profile, size, visual_geometry
        )
    elif name in {"cup", "mug", "white_cup", "bowl", "pan"}:
        has_ycb_visual = name in YCB_MODEL_FILES
        _define_open_container(
            stage,
            root_path,
            size,
            color,
            hide_collision_geometry=has_ycb_visual,
        )
        if has_ycb_visual:
            _define_ycb_visual(stage, root_path, name, size, stage_output)
        elif name == "mug":
            _define_mug_handle(stage, root_path, size, color)
    elif name in YCB_MODEL_FILES:
        _define_ycb_visual(stage, root_path, name, size, stage_output)
        collider = _define_box(
            stage,
            f"{root_path}/geometry/collision_proxy",
            size,
            (0.0, 0.0, 0.0),
            (0.5, 0.5, 0.5),
            collision=True,
        )
        UsdGeom.Imageable(collider).CreateVisibilityAttr().Set(UsdGeom.Tokens.invisible)
    elif name == "scissors":
        _define_ycb_visual(stage, root_path, name, size, stage_output)
        collider = _define_box(
            stage,
            f"{root_path}/geometry/collision_proxy",
            size,
            (0.0, 0.0, 0.0),
            (0.5, 0.5, 0.5),
            collision=True,
        )
        UsdGeom.Imageable(collider).CreateVisibilityAttr().Set(UsdGeom.Tokens.invisible)
    elif shape == "sphere":
        geom = UsdGeom.Sphere.Define(stage, f"{root_path}/geometry")
        geom.CreateRadiusAttr(max(size) / 2.0)
        geom.AddScaleOp().Set(Gf.Vec3f(1.0, size[1] / size[0], size[2] / size[0]))
        geom.CreateDisplayColorAttr([Gf.Vec3f(*color)])
        UsdPhysics.CollisionAPI.Apply(geom.GetPrim())
    elif shape == "cylinder":
        geom = UsdGeom.Cylinder.Define(stage, f"{root_path}/geometry")
        geom.CreateRadiusAttr(max(size[0], size[1]) / 2.0)
        geom.CreateHeightAttr(size[2])
        geom.CreateDisplayColorAttr([Gf.Vec3f(*color)])
        UsdPhysics.CollisionAPI.Apply(geom.GetPrim())
    else:
        _define_box(stage, f"{root_path}/geometry", size, (0.0, 0.0, 0.0), color)

    return prim


def _build_stage(
    task: dict[str, Any],
    layout_id: int,
    output: Path,
    s01_shift_xy: tuple[float, float] | None = None,
) -> None:
    import numpy as np
    from pxr import Gf, Sdf, Usd, UsdGeom, UsdLux, UsdPhysics

    task_id = str(task["id"])
    instruction = str(task["instruction"])
    objects = [str(item) for item in task.get("objects", [])]
    override_names, object_specs, override_positions = _scene_object_specs(
        task_id, layout_id
    )
    has_scene_override = bool(override_names)
    if has_scene_override:
        objects = override_names
    stage = Usd.Stage.CreateNew(str(output))
    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.z)
    UsdGeom.SetStageMetersPerUnit(stage, 1.0)
    world = UsdGeom.Xform.Define(stage, "/World")
    world_prim = world.GetPrim()
    world_prim.CreateAttribute("appendix_g:task_id", Sdf.ValueTypeNames.String).Set(task_id)
    world_prim.CreateAttribute("appendix_g:layout_id", Sdf.ValueTypeNames.Int).Set(layout_id)
    world_prim.CreateAttribute("appendix_g:instruction", Sdf.ValueTypeNames.String).Set(instruction)
    world_prim.CreateAttribute("appendix_g:env_template", Sdf.ValueTypeNames.String).Set(str(task.get("env_template", task.get("scene_template", "tabletop_basic"))))
    world_prim.CreateAttribute("appendix_g:evaluator", Sdf.ValueTypeNames.String).Set(str(task.get("evaluator", "unknown")))

    # The Appendix photos show tabletop scenes, not the unrelated billiard-room
    # HDRI bundled with the smoke-test scene. Use a neutral studio dome for all
    # 40 reconstructions while retaining the DROID camera/robot rig.
    dome = UsdLux.DomeLight.Define(stage, "/World/DroidSmokeEnvironment")
    dome.CreateIntensityAttr(500.0)
    dome.CreateColorAttr(Gf.Vec3f(0.72, 0.74, 0.77))

    # A static DROID-like tabletop.  It is procedural and deliberately kept
    # at the same prim path in every scene so layouts differ only in objects.
    table_color = (0.26, 0.13, 0.065)
    _define_box(stage, "/World/table_surface", TABLE_TOP_SIZE, (TABLE_CENTER_X, TABLE_CENTER_Y, TABLE_TOP_CENTER_Z), table_color)
    _define_textured_table_top(stage, output)
    if task_id in {"S01", "S02"}:
        _define_s01_table_context(stage)
    # Keep the apron/legs below the tabletop: the DROID side cameras sit near
    # table height and tall edge panels occlude almost the entire workspace.
    for x in (-0.30, 0.30):
        for y in (-0.45, 0.45):
            _define_box(
                stage,
                f"/World/table_leg_{'l' if x < 0 else 'r'}_{'f' if y < 0 else 'b'}",
                (0.07, 0.07, TABLE_LEG_HEIGHT),
                (
                    TABLE_CENTER_X + x,
                    TABLE_CENTER_Y + y,
                    TABLE_LEG_BOTTOM_Z + TABLE_LEG_HEIGHT / 2.0,
                ),
                (0.30, 0.20, 0.10),
            )

    # Keep the two paired layouts visually distinct but deterministic.  The
    # semantic object order is stable, which also makes paired evaluation and
    # failure analysis straightforward.
    # Position-sweep scenes reuse layout 0's exact within-scene placement and
    # add only the requested rigid translation, so variants are comparable.
    jitter_layout = 0 if task_id == "S01" and s01_shift_xy is not None else layout_id
    jitter = _stable_number(task_id, jitter_layout)
    positions: list[tuple[float, float, float]] = []
    if has_scene_override:
        positions = [override_positions[name] for name in objects]
    else:
        movable_objects = [name for name in objects if name != "table"]
        object_index = 0
        for name in objects:
            if name == "table":
                positions.append((TABLE_CENTER_X, TABLE_CENTER_Y, TABLE_TOP_CENTER_Z))
                continue
            x, y = _object_xy(
                task_id, object_index, len(movable_objects), layout_id, jitter, name
            )
            if task_id == "S01" and s01_shift_xy is not None:
                # Diagnostic-only rigid translation of all S01 props. Keeping the
                # relative arrangement fixed isolates workspace placement effects.
                x += s01_shift_xy[0]
                y += s01_shift_xy[1]
            object_index += 1
            z_clearance = 0.0 if task_id in {"S01", "S02"} else 0.005
            z = TABLE_SURFACE_Z + _object_size(name, task_id)[2] / 2.0 + z_clearance
            positions.append((x, y, z))

    for index, name in enumerate(objects):
        if name == "table":
            continue
        if task_id == "U15" and name == "mustard_dose":
            # Emit discrete dynamic droplets at runtime; there are no beads in
            # the reset state and the old single-bead placeholder is removed.
            continue
        if task_id == "S01":
            proxy_cfg = task.get("proxy_evaluation", {})
            target = (
                str(proxy_cfg.get("item"))
                if name == str(proxy_cfg.get("container", "cup"))
                else None
            )
        else:
            target = objects[index + 1] if index + 1 < len(objects) else None
        _define_object(
            stage,
            name,
            positions[index],
            layout_id,
            task_id,
            target,
            output,
            object_specs.get(name),
        )

    if task_id == "U15":
        from pxr import Gf, UsdGeom, UsdPhysics
        bead_origin=np.asarray(positions[objects.index('mustard_dose')],dtype=float)
        for bead_index in range(16):
            name=f'mustard_bead_{bead_index:02d}'
            root=UsdGeom.Xform.Define(stage,f'/World/{name}')
            root.AddTranslateOp().Set(Gf.Vec3d(*bead_origin))
            body=UsdPhysics.RigidBodyAPI.Apply(root.GetPrim())
            UsdPhysics.MassAPI.Apply(root.GetPrim()).CreateMassAttr(.0002)
            sphere=UsdGeom.Sphere.Define(stage,f'/World/{name}/visual')
            sphere.CreateRadiusAttr(.003)
            sphere.CreateDisplayColorAttr([Gf.Vec3f(.92,.69,.035)])
            collision=UsdPhysics.CollisionAPI.Apply(sphere.GetPrim())
            collision.CreateCollisionEnabledAttr(False)
            UsdPhysics.FixedJoint.Define(stage,f'/World/{name}_reset_hold').CreateBody1Rel().SetTargets([root.GetPath()])
            hold=UsdPhysics.FixedJoint.Get(stage,f'/World/{name}_reset_hold')
            hold.CreateLocalPos0Attr(Gf.Vec3f(*bead_origin))
            hold.CreateLocalPos1Attr(Gf.Vec3f(0))
            hold.CreateJointEnabledAttr(True)
            hold.CreateCollisionEnabledAttr(False)
            UsdGeom.Imageable(root.GetPrim()).CreateVisibilityAttr().Set(UsdGeom.Tokens.invisible)
        world_prim.CreateAttribute('appendix_g:mustard_emitter_model',Sdf.ValueTypeNames.String).Set('sixteen_discrete_rigid_droplets_tilt_triggered_not_fluid')

    if task_id == "U18":
        # The lever is an independent rigid body on a single guided slider.
        # Press direction is world -Z; the linear spring returns it to raised.
        from pxr import Gf, UsdPhysics
        body0 = stage.GetPrimAtPath('/World/toaster')
        body1 = stage.GetPrimAtPath('/World/toaster_lever')
        if not body0 or not body1:
            raise ValueError('U18 requires toaster and toaster_lever rigid bodies')
        toaster_pos = np.asarray(positions[objects.index('toaster')], dtype=float)
        lever_pos = np.asarray(positions[objects.index('toaster_lever')], dtype=float)
        joint = UsdPhysics.PrismaticJoint.Define(stage, '/World/u18_lever_joint')
        joint.CreateBody0Rel().SetTargets([body0.GetPath()])
        joint.CreateBody1Rel().SetTargets([body1.GetPath()])
        joint.CreateLocalPos0Attr(Gf.Vec3f(*(lever_pos - toaster_pos)))
        joint.CreateLocalPos1Attr(Gf.Vec3f(0.0))
        joint.CreateLocalRot0Attr(Gf.Quatf(1.0))
        joint.CreateLocalRot1Attr(Gf.Quatf(1.0))
        joint.CreateAxisAttr('Z')
        joint.CreateLowerLimitAttr(-0.030)
        joint.CreateUpperLimitAttr(0.0)
        joint.CreateCollisionEnabledAttr(False)
        drive = UsdPhysics.DriveAPI.Apply(joint.GetPrim(), 'linear')
        drive.CreateTypeAttr('force')
        drive.CreateStiffnessAttr(1.2)
        drive.CreateDampingAttr(0.12)
        drive.CreateMaxForceAttr(1.5)
        world_prim.CreateAttribute('appendix_g:lever_joint_path', Sdf.ValueTypeNames.String).Set('/World/u18_lever_joint')

    if task_id == "U12":
        from pxr import Gf, UsdPhysics
        clip_pos=np.asarray(positions[objects.index('binder_clip')],dtype=float)
        for side,label in [(-1.0,'left'),(1.0,'right')]:
            handle=UsdGeom.Xform.Define(stage,f'/World/clip_handle_{label}')
            angle=math.radians(side*65.0)
            offset=np.asarray([side*.014,0.0,.014])
            handle.AddTranslateOp().Set(Gf.Vec3d(*(clip_pos+offset)))
            handle.AddOrientOp().Set(Gf.Quatf(math.cos(angle/2),Gf.Vec3f(0,math.sin(angle/2),0)))
            UsdPhysics.RigidBodyAPI.Apply(handle.GetPrim())
            UsdPhysics.MassAPI.Apply(handle.GetPrim()).CreateMassAttr(.008)
            _define_box(stage,f'{handle.GetPath()}/wire_loop',(.004,.003,.026),(0,0,0),(.60,.62,.64),collision=True)
            _define_box(stage,f'{handle.GetPath()}/crossbar',(.024,.003,.003),(0,0,.011),(.60,.62,.64),collision=True)
            pivot=UsdPhysics.RevoluteJoint.Define(stage,f'/World/clip_handle_{label}_hinge')
            pivot.CreateBody0Rel().SetTargets(['/World/binder_clip'])
            pivot.CreateBody1Rel().SetTargets([handle.GetPath()])
            pivot.CreateLocalPos0Attr(Gf.Vec3f(side*.014,0,.014))
            pivot.CreateLocalPos1Attr(Gf.Vec3f(0))
            pivot.CreateLocalRot0Attr(Gf.Quatf(1))
            pivot.CreateLocalRot1Attr(Gf.Quatf(math.cos(angle/2),Gf.Vec3f(0,-math.sin(angle/2),0)))
            pivot.CreateAxisAttr('Y')
            pivot.CreateLowerLimitAttr(-75.0)
            pivot.CreateUpperLimitAttr(75.0)
            pivot.CreateCollisionEnabledAttr(False)
        paper_pos=np.asarray(positions[objects.index('papers')],dtype=float)
        release=UsdPhysics.FixedJoint.Define(stage,'/World/clip_paper_release_joint')
        release.CreateBody0Rel().SetTargets(['/World/binder_clip'])
        release.CreateBody1Rel().SetTargets(['/World/papers'])
        release.CreateLocalPos0Attr(Gf.Vec3f(*(paper_pos-clip_pos)))
        release.CreateLocalPos1Attr(Gf.Vec3f(0))
        release.CreateJointEnabledAttr(True)
        release.CreateCollisionEnabledAttr(False)
        world_prim.CreateAttribute('appendix_g:clip_release_joint_path',Sdf.ValueTypeNames.String).Set('/World/clip_paper_release_joint')

    # Evaluation regions are logical predicates, not scene props; never render
    # large colored plates that are absent from the Appendix photographs.

    stage.SetDefaultPrim(world.GetPrim())
    stage.GetRootLayer().Save()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=MANIFEST_DEFAULT)
    parser.add_argument("--output", type=Path, default=Path(os.environ.get("APPENDIX_G_SCENE_DIR", OUTPUT_DEFAULT)))
    parser.add_argument("--task", action="append", help="Only build selected task id(s), e.g. S01 or U01")
    parser.add_argument("--layout", type=int, choices=range(0, 11), help="Only build one layout id")
    parser.add_argument("--s01-shift-x", type=float, default=None,
                        help="Diagnostic translation in meters for all S01 props; negative X moves toward the robot")
    parser.add_argument("--s01-shift-y", type=float, default=None,
                        help="Diagnostic lateral translation in meters for all S01 props")
    parser.add_argument("--headless", action="store_true", default=True)
    args = parser.parse_args()

    with args.manifest.open() as handle:
        manifest = yaml.safe_load(handle)
    tasks = manifest["tasks"]
    wanted = {item.upper() for item in args.task} if args.task else None
    if wanted:
        tasks = [task for task in tasks if str(task["id"]).upper() in wanted]
    if not tasks:
        raise SystemExit("No matching tasks in manifest")

    args.output.mkdir(parents=True, exist_ok=True)
    layouts = [args.layout] if args.layout is not None else [0, 1]
    s01_shift_xy = None
    if args.s01_shift_x is not None or args.s01_shift_y is not None:
        s01_shift_xy = (
            0.0 if args.s01_shift_x is None else args.s01_shift_x,
            0.0 if args.s01_shift_y is None else args.s01_shift_y,
        )
    built = 0
    for task in tasks:
        for layout_id in layouts:
            path = args.output / f"{str(task['id']).lower()}_layout{layout_id}.usd"
            _build_stage(task, layout_id, path, s01_shift_xy=s01_shift_xy)
            built += 1
            print(f"[appendix-g-scenes] wrote {path}", flush=True)
    print(f"[appendix-g-scenes] complete: {built} USD files in {args.output}", flush=True)
    source_files = [Path(__file__).resolve(), args.manifest.resolve()]
    source_files += sorted((PROJECT_ROOT / "scripts").glob("appendix_g_*v7.py"))
    source_files += sorted((PROJECT_ROOT / "assets/appendix_g/task_specs").glob("*/scene_overrides.yaml"))
    source_hashes = {str(p.relative_to(PROJECT_ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                     for p in source_files}
    scene_hashes = {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                    for p in sorted(args.output.glob("*.usd"))}
    (args.output / "build_manifest.json").write_text(json.dumps({
        "sources_sha256": source_hashes, "scenes_sha256": scene_hashes,
        "paper_exact_scene": False, "visual_approval": "pending",
        "physics_approval": "pending", "inference_calls": 0,
    }, indent=2) + "\n")


if __name__ == "__main__":
    # AppLauncher is imported only here so the module remains inspectable and
    # syntax-checkable without starting Isaac Sim.  USD authoring itself does
    # not need a Kit process: the Isaac Sim USD Python bindings are sufficient
    # and avoid competing with an already-running policy server for a GPU.
    if os.environ.get("APPENDIX_G_STANDALONE_PXR") == "1":
        main()
    else:
        import argparse as _argparse

        from isaaclab.app import AppLauncher

        _parser = _argparse.ArgumentParser(add_help=False)
        AppLauncher.add_app_launcher_args(_parser)
        _args, _ = _parser.parse_known_args()
        # USD authoring does not run simulation kernels. Keep the Kit tensor
        # device on CPU; Vulkan remains available for the renderer.
        _args.device = "cpu"
        _args.headless = True
        _args.enable_cameras = False
        _launcher = AppLauncher(_args)
        _simulation_app = _launcher.app
        try:
            main()
        finally:
            _simulation_app.close()
