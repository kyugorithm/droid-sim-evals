#!/usr/bin/env python3
"""Build deterministic USD scenes for the DreamZero Appendix G task proxies.

This is intentionally a small, reproducible scene generator.  It creates a
tabletop, the DROID-style interaction objects, and the two paired layouts used
by the evaluation manifest. Most props are procedural proxies; S01 uses a
textured YCB scissors scan alongside the procedural cup and marker.

Use ``scripts/build_appendix_g_scenes_b300.sh`` to expose Isaac Sim's bundled
``pxr`` bindings and shared libraries. USD authoring does not require starting
the full Kit application or running a simulation.
"""

from __future__ import annotations

import argparse
import hashlib
import math
import os
from pathlib import Path
from typing import Any

import yaml


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


COLORS = {
    "apple": (0.75, 0.05, 0.03),
    "lemon": (0.95, 0.80, 0.05),
    "marker": (0.05, 0.20, 0.80),
    "small_marker": (0.10, 0.55, 0.90),
    "blue_box": (0.03, 0.15, 0.75),
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
}


def _safe_id(value: str) -> str:
    return "".join(ch if ch.isalnum() or ch == "_" else "_" for ch in value)


def _stable_number(task_id: str, layout_id: int) -> float:
    digest = hashlib.sha256(f"{task_id}:{layout_id}".encode()).digest()
    return (int.from_bytes(digest[:2], "big") / 65535.0) - 0.5


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
    if name in {"marker", "small_marker", "pencil", "straw", "wire", "toaster_lever"}:
        return (0.025, 0.18, 0.025)
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
    if name in {"apple", "lemon", "burger", "croissant", "magnet", "hidden_object"}:
        return "sphere"
    if name in {"bowl", "pan", "plate", "matching_bowls", "cup", "mug", "white_cup", "cup_set", "mustard_bottle"}:
        return "cylinder"
    return "cube"


def _object_xy(
    task_id: str,
    index: int,
    object_count: int,
    layout_id: int,
    jitter: float,
    object_name: str | None = None,
) -> tuple[float, float]:
    """Return a deterministic, non-overlapping XY slot inside the smoke table.

    S01 keeps its forward cup/marker arrangement for the staged proxy metric.
    Other tasks use size-safe slots because their objects can be as large as a
    toaster or basket. These placements are local assumptions, not paper poses.
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


def _define_s01_table_context(stage: Any) -> None:
    """Add a modest wood tabletop and gray equipment panel like the photo."""
    # Subtle non-colliding strips suggest the visible wood grain without
    # changing the existing table collision plane.
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

    # The reference image has a gray vertical machine/backboard behind the
    # tabletop. This simplified panel and two rails provide similar context.
    far_edge_x = TABLE_CENTER_X + TABLE_TOP_SIZE[0] / 2.0
    _define_box(
        stage, "/World/s01_gray_back_panel", (0.025, 1.50, 0.60),
        (far_edge_x + 0.035, TABLE_CENTER_Y, TABLE_SURFACE_Z + 0.32),
        (0.09, 0.10, 0.11), collision=False,
    )
    for index, (y, angle) in enumerate(((-0.30, -17.0), (0.30, 17.0))):
        _define_oriented_box(
            stage, f"/World/s01_back_rail_{index}", (0.018, 0.022, 0.44),
            (far_edge_x - 0.005, TABLE_CENTER_Y + y, TABLE_SURFACE_Z + 0.32),
            (0.14, 0.15, 0.16), rotation_axis=(0.0, 1.0, 0.0), angle_deg=angle,
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


def _define_s01_marker(stage: Any, root_path: str) -> None:
    # The photo appears to show a white-bodied marker with a red cap; the red
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


def _bind_obj_texture(stage: Any, mesh: Any, root_path: str, stage_output: Path) -> None:
    from pxr import Sdf, UsdShade

    material_path = f"{root_path}/material"
    material = UsdShade.Material.Define(stage, material_path)
    surface = UsdShade.Shader.Define(stage, f"{material_path}/PreviewSurface")
    surface.CreateIdAttr("UsdPreviewSurface")
    surface.CreateInput("roughness", Sdf.ValueTypeNames.Float).Set(0.78)

    primvar = UsdShade.Shader.Define(stage, f"{material_path}/PrimvarReader")
    primvar.CreateIdAttr("UsdPrimvarReader_float2")
    primvar.CreateInput("varname", Sdf.ValueTypeNames.Token).Set("st")
    primvar_result = primvar.CreateOutput("result", Sdf.ValueTypeNames.Float2)

    texture = UsdShade.Shader.Define(stage, f"{material_path}/Texture")
    texture.CreateIdAttr("UsdUVTexture")
    texture_file = os.path.relpath(SCISSOR_TEXTURE, stage_output.parent).replace(os.sep, "/")
    texture.CreateInput("file", Sdf.ValueTypeNames.Asset).Set(Sdf.AssetPath(texture_file))
    texture.CreateInput("st", Sdf.ValueTypeNames.Float2).ConnectToSource(primvar_result)
    texture.CreateInput("wrapS", Sdf.ValueTypeNames.Token).Set("repeat")
    texture.CreateInput("wrapT", Sdf.ValueTypeNames.Token).Set("repeat")
    texture_rgb = texture.CreateOutput("rgb", Sdf.ValueTypeNames.Float3)
    surface.CreateInput("diffuseColor", Sdf.ValueTypeNames.Color3f).ConnectToSource(texture_rgb)
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
            "S01 requires the YCB 037 scissors OBJ and texture under "
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
    _bind_obj_texture(stage, mesh.GetPrim(), root_path, stage_output)

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


def _define_object(stage: Any, name: str, pos: tuple[float, float, float], layout_id: int, task_id: str, target: str | None, stage_output: Path) -> Any:
    from pxr import Gf, Sdf, UsdGeom, UsdPhysics

    safe_name = _safe_id(name)
    root_path = f"/World/{safe_name}"
    root = UsdGeom.Xform.Define(stage, root_path)
    root.AddTranslateOp().Set(Gf.Vec3d(*pos))
    # U01 starts with the handle facing -X; its "right" instruction means +X
    # in this local robot-frame proxy convention.
    if task_id == "S01":
        # YCB 037 scissors has its handles on local -Y; rotate them toward the
        # image-right side. The marker's red cap also faces image-right.
        yaw_deg = {"scissors": -35.0, "marker": 80.0}.get(name, 0.0)
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
    root.AddOrientOp().Set(initial_quat)
    prim = root.GetPrim()
    UsdPhysics.RigidBodyAPI.Apply(prim).CreateRigidBodyEnabledAttr(True)
    mass = UsdPhysics.MassAPI.Apply(prim)
    mass.CreateMassAttr(0.06 if task_id == "S01" and name == "scissors" else 0.15)
    prim.CreateAttribute("appendix_g:semantic_name", Sdf.ValueTypeNames.String).Set(name)
    prim.CreateAttribute("appendix_g:task_id", Sdf.ValueTypeNames.String).Set(task_id)
    prim.CreateAttribute("appendix_g:layout_id", Sdf.ValueTypeNames.Int).Set(layout_id)
    prim.CreateAttribute("appendix_g:target_name", Sdf.ValueTypeNames.String).Set(target or "")
    is_scanned_s01_scissors = task_id == "S01" and name == "scissors"
    prim.CreateAttribute("appendix_g:proxy_geometry", Sdf.ValueTypeNames.Bool).Set(not is_scanned_s01_scissors)

    size = _object_size(name, task_id)
    color = COLORS.get(name, (0.55, 0.55, 0.58))
    shape = _shape_for(name)
    if task_id == "S01" and name == "cup":
        _define_open_container(
            stage, root_path, size, color, hide_collision_geometry=True
        )
        _define_s01_cup_visual(stage, root_path, size)
    elif task_id == "S01" and name == "marker":
        _define_s01_marker(stage, root_path)
    elif task_id == "S01" and name == "scissors":
        _define_s01_scissors(stage, root_path, stage_output)
    elif name in {"cup", "mug", "white_cup", "bowl", "pan"}:
        _define_open_container(stage, root_path, size, color)
        if name == "mug":
            _define_mug_handle(stage, root_path, size, color)
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


def _build_stage(task: dict[str, Any], layout_id: int, output: Path) -> None:
    from pxr import Gf, Sdf, Usd, UsdGeom, UsdLux, UsdPhysics

    task_id = str(task["id"])
    instruction = str(task["instruction"])
    objects = [str(item) for item in task.get("objects", [])]
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

    # S01 has a neutral studio-like background matching the reference photo;
    # other proxy tasks reuse the HDRI shipped with the DROID smoke assets.
    dome = UsdLux.DomeLight.Define(stage, "/World/DroidSmokeEnvironment")
    if task_id == "S01":
        dome.CreateIntensityAttr(400.0)
        dome.CreateColorAttr(Gf.Vec3f(0.72, 0.74, 0.77))
    elif BACKGROUND_HDRI.is_file():
        dome.CreateIntensityAttr(500.0)
        dome.CreateTextureFileAttr(Sdf.AssetPath(str(BACKGROUND_HDRI)))
        dome.CreateTextureFormatAttr(UsdLux.Tokens.latlong)

    # A static DROID-like tabletop.  It is procedural and deliberately kept
    # at the same prim path in every scene so layouts differ only in objects.
    table_color = (0.25, 0.10, 0.045) if task_id == "S01" else (0.42, 0.28, 0.16)
    _define_box(stage, "/World/table_surface", TABLE_TOP_SIZE, (TABLE_CENTER_X, TABLE_CENTER_Y, TABLE_TOP_CENTER_Z), table_color)
    if task_id == "S01":
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
    jitter = _stable_number(task_id, layout_id)
    positions: list[tuple[float, float, float]] = []
    movable_objects = [name for name in objects if name != "table"]
    object_index = 0
    for name in objects:
        if name == "table":
            positions.append((TABLE_CENTER_X, TABLE_CENTER_Y, TABLE_TOP_CENTER_Z))
            continue
        x, y = _object_xy(
            task_id, object_index, len(movable_objects), layout_id, jitter, name
        )
        object_index += 1
        z_clearance = 0.0 if task_id == "S01" else 0.005
        z = TABLE_SURFACE_Z + _object_size(name, task_id)[2] / 2.0 + z_clearance
        positions.append((x, y, z))

    for index, name in enumerate(objects):
        if name == "table":
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
        _define_object(stage, name, positions[index], layout_id, task_id, target, output)

    # Semantic anchors help later evaluator versions identify regions without
    # relying on visual names.  They are static trigger volumes, not movable
    # objects and therefore are intentionally not registered as rigid bodies.
    evaluator = str(task.get("evaluator", ""))
    if evaluator == "move_to_region":
        _define_box(stage, "/World/region_left", (0.20, 0.42, 0.015), (TABLE_CENTER_X - 0.18, TABLE_CENTER_Y, TABLE_SURFACE_Z + 0.0075), (0.10, 0.35, 0.10), collision=False)
        _define_box(stage, "/World/region_right", (0.20, 0.42, 0.015), (TABLE_CENTER_X + 0.18, TABLE_CENTER_Y, TABLE_SURFACE_Z + 0.0075), (0.35, 0.10, 0.10), collision=False)

    stage.SetDefaultPrim(world.GetPrim())
    stage.GetRootLayer().Save()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=MANIFEST_DEFAULT)
    parser.add_argument("--output", type=Path, default=Path(os.environ.get("APPENDIX_G_SCENE_DIR", OUTPUT_DEFAULT)))
    parser.add_argument("--task", action="append", help="Only build selected task id(s), e.g. S01 or U01")
    parser.add_argument("--layout", type=int, choices=[0, 1], help="Only build one paired layout")
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
    built = 0
    for task in tasks:
        for layout_id in layouts:
            path = args.output / f"{str(task['id']).lower()}_layout{layout_id}.usd"
            _build_stage(task, layout_id, path)
            built += 1
            print(f"[appendix-g-scenes] wrote {path}", flush=True)
    print(f"[appendix-g-scenes] complete: {built} USD files in {args.output}", flush=True)


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
