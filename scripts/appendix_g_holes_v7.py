"""Visual-only perforated fixtures for Appendix G tasks U08 and U20.
The generated meshes have real openings: each perforated board is assembled
from front/back surface strips with the apertures omitted, plus exposed inner
tunnel faces.  No physics schemas or collision geometry are authored here.
"""

from __future__ import annotations

import math
from typing import Sequence


_Face = tuple[int, ...]
_Hole = dict[str, object]


def _rgb(color: Sequence[float], factor: float = 1.0) -> tuple[float, float, float]:
    if len(color) < 3:
        raise ValueError("color must contain at least three channels")
    return tuple(max(0.0, min(1.0, float(c) * factor)) for c in color[:3])  # type: ignore[return-value]


class _StageWriter:
    def __init__(self, stage, root_path: str, size: Sequence[float]):
        from pxr import Gf, Sdf, UsdGeom, UsdShade

        if len(size) != 3 or any(not math.isfinite(float(v)) or float(v) <= 0.0 for v in size):
            raise ValueError("size must contain three finite positive dimensions")
        self.Gf, self.Sdf, self.UsdGeom, self.UsdShade = Gf, Sdf, UsdGeom, UsdShade
        self.stage = stage
        self.root = root_path.rstrip("/") + "/visual/v7"
        self.size = tuple(float(v) for v in size)
        self.materials: dict[str, object] = {}
        stage.DefinePrim(root_path, "Xform")
        stage.DefinePrim(root_path.rstrip("/") + "/visual", "Xform")
        stage.DefinePrim(self.root, "Xform")
        stage.DefinePrim(self.root + "/materials", "Scope")

    def _material(self, name: str, color: Sequence[float], roughness: float, metallic: float = 0.0):
        if name in self.materials:
            return self.materials[name]
        Sdf, UsdShade = self.Sdf, self.UsdShade
        path = self.root + "/materials/" + name
        material = UsdShade.Material.Define(self.stage, path)
        shader = UsdShade.Shader.Define(self.stage, path + "/PreviewSurface")
        shader.CreateIdAttr("UsdPreviewSurface")
        shader.CreateInput("diffuseColor", Sdf.ValueTypeNames.Color3f).Set(
            self.Gf.Vec3f(*_rgb(color))
        )
        shader.CreateInput("roughness", Sdf.ValueTypeNames.Float).Set(float(roughness))
        shader.CreateInput("metallic", Sdf.ValueTypeNames.Float).Set(float(metallic))
        shader.CreateInput("specular", Sdf.ValueTypeNames.Float).Set(0.28)
        material.CreateSurfaceOutput().ConnectToSource(
            shader.CreateOutput("surface", Sdf.ValueTypeNames.Token)
        )
        self.materials[name] = material
        return material

    def mesh(
        self,
        name: str,
        points: Sequence[Sequence[float]],
        faces: Sequence[_Face],
        material_name: str,
        color: Sequence[float],
        roughness: float,
        *,
        double_sided: bool = False,
    ) -> None:
        if not points or not faces:
            return
        if any(abs(float(axis)) > 0.500001 for point in points for axis in point):
            raise ValueError(f"{name} exceeds its centered local bounds")
        Gf, UsdGeom = self.Gf, self.UsdGeom
        mesh = UsdGeom.Mesh.Define(self.stage, self.root + "/" + name)
        sx, sy, sz = self.size
        scaled = [Gf.Vec3f(float(p[0]) * sx, float(p[1]) * sy, float(p[2]) * sz) for p in points]
        mesh.CreatePointsAttr(scaled)
        mesh.CreateFaceVertexCountsAttr([len(face) for face in faces])
        mesh.CreateFaceVertexIndicesAttr([int(i) for face in faces for i in face])
        mesh.CreateSubdivisionSchemeAttr(UsdGeom.Tokens.none)
        if double_sided:
            mesh.CreateDoubleSidedAttr(True)

        # Author smooth vertex normals, including the visible aperture tunnels.
        normals = [[0.0, 0.0, 0.0] for _ in scaled]
        for face in faces:
            if len(face) < 3:
                continue
            a = scaled[face[0]]
            for j in range(1, len(face) - 1):
                b, c = scaled[face[j]], scaled[face[j + 1]]
                ab = (b[0] - a[0], b[1] - a[1], b[2] - a[2])
                ac = (c[0] - a[0], c[1] - a[1], c[2] - a[2])
                n = (ab[1] * ac[2] - ab[2] * ac[1], ab[2] * ac[0] - ab[0] * ac[2], ab[0] * ac[1] - ab[1] * ac[0])
                for index in (face[0], face[j], face[j + 1]):
                    for axis in range(3):
                        normals[index][axis] += n[axis]
        normal_values = []
        for normal in normals:
            length = math.sqrt(sum(v * v for v in normal))
            normal_values.append(
                self.Gf.Vec3f(*(v / length for v in normal)) if length > 1e-12
                else self.Gf.Vec3f(0.0, 0.0, 1.0)
            )
        mesh.CreateNormalsAttr(normal_values)
        mesh.SetNormalsInterpolation(UsdGeom.Tokens.vertex)
        mesh.CreateDisplayColorAttr([self.Gf.Vec3f(*_rgb(color))])
        # MaterialBindingAPI is in UsdShade, not UsdGeom.
        self.UsdShade.MaterialBindingAPI.Apply(mesh.GetPrim()).Bind(
            self._material(material_name, color, roughness)
        )

    def box(self, name: str, center: Sequence[float], extent: Sequence[float], color: Sequence[float], material: str, roughness: float):
        cx, cy, cz = center
        hx, hy, hz = (float(v) / self.size[i] * 0.5 for i, v in enumerate(extent))
        x, y, z = cx / self.size[0], cy / self.size[1], cz / self.size[2]
        points = ((x-hx,y-hy,z-hz),(x+hx,y-hy,z-hz),(x+hx,y+hy,z-hz),(x-hx,y+hy,z-hz),
                  (x-hx,y-hy,z+hz),(x+hx,y-hy,z+hz),(x+hx,y+hy,z+hz),(x-hx,y+hy,z+hz))
        faces = ((0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7))
        self.mesh(name, points, faces, material, color, roughness)


def _hole_contour(hole: _Hole, segments: int = 48) -> list[tuple[float, float]]:
    shape = str(hole["shape"])
    cu, cv = hole["center"]  # type: ignore[misc]
    hu, hv = hole["half"]  # type: ignore[misc]
    if shape == "circle":
        return [(cu + hu * math.cos(2.0 * math.pi * i / segments),
                 cv + hv * math.sin(2.0 * math.pi * i / segments)) for i in range(segments)]
    if shape == "square":
        return [(cu-hu,cv-hv),(cu+hu,cv-hv),(cu+hu,cv+hv),(cu-hu,cv+hv)]
    if shape == "triangle":
        return [(cu-hu,cv-hv),(cu+hu,cv-hv),(cu,cv+hv)]
    raise ValueError(f"unsupported aperture shape {shape!r}")


def _hole_interval(hole: _Hole, v: float) -> tuple[float, float] | None:
    cu, cv = hole["center"]  # type: ignore[misc]
    hu, hv = hole["half"]  # type: ignore[misc]
    dv = v - cv
    if abs(dv) > hv + 1e-10:
        return None
    shape = str(hole["shape"])
    if shape == "circle":
        fraction = math.sqrt(max(0.0, 1.0 - (dv / hv) ** 2))
        reach = hu * fraction
    elif shape == "square":
        reach = hu
    elif shape == "triangle":
        reach = hu * max(0.0, min(1.0, (hv - dv) / (2.0 * hv)))
    else:
        raise ValueError(f"unsupported aperture shape {shape!r}")
    return cu - reach, cu + reach


def _panel(
    writer: _StageWriter,
    name: str,
    *,
    normal_axis: int,
    u_axis: int,
    v_axis: int,
    center_normal_m: float,
    half_u_m: float,
    half_v_m: float,
    thickness_m: float,
    holes: Sequence[_Hole],
    material: str,
    color: Sequence[float],
    roughness: float,
) -> None:
    """Make a finite-thickness planar board with uncapped through-apertures."""
    sizes = writer.size
    half_t = thickness_m * 0.5
    points: list[tuple[float, float, float]] = []
    faces: list[_Face] = []

    def point(u: float, v: float, normal_offset: float) -> tuple[float, float, float]:
        p = [0.0, 0.0, 0.0]
        p[normal_axis] = (center_normal_m + normal_offset) / sizes[normal_axis]
        p[u_axis] = u / sizes[u_axis]
        p[v_axis] = v / sizes[v_axis]
        return tuple(p)  # type: ignore[return-value]

    # Boundary samples form the sweep rows. Circle arcs use many rows; polygon
    # edges remain exact straight segments between their vertices.
    levels = {-half_v_m, half_v_m}
    contours = [_hole_contour(hole) for hole in holes]
    for contour in contours:
        levels.update(max(-half_v_m, min(half_v_m, v)) for _, v in contour)
    rows = sorted(levels)

    def add_quad(coords: Sequence[tuple[float, float, float]]) -> None:
        start = len(points)
        points.extend(coords)
        faces.append((start, start + 1, start + 2, start + 3))

    for y0, y1 in zip(rows, rows[1:]):
        if y1 - y0 < 1e-10:
            continue
        ym = (y0 + y1) * 0.5
        active = [(hole, _hole_interval(hole, ym)) for hole in holes]
        active = [(hole, interval) for hole, interval in active if interval is not None]
        active.sort(key=lambda entry: entry[1][0])  # type: ignore[index]
        boundaries0 = [-half_u_m]
        boundaries1 = [-half_u_m]
        for hole, _ in active:
            interval0, interval1 = _hole_interval(hole, y0), _hole_interval(hole, y1)
            if interval0 is None or interval1 is None:
                raise ValueError("aperture sweep rows do not cover a hole boundary")
            boundaries0.extend(interval0)
            boundaries1.extend(interval1)
        boundaries0.append(half_u_m)
        boundaries1.append(half_u_m)
        for j in range(0, len(boundaries0) - 1, 2):
            left0, right0 = boundaries0[j], boundaries0[j + 1]
            left1, right1 = boundaries1[j], boundaries1[j + 1]
            if max(right0 - left0, right1 - left1) < 1e-10:
                continue
            for depth in (-half_t, half_t):
                add_quad((point(left0,y0,depth), point(right0,y0,depth),
                          point(right1,y1,depth), point(left1,y1,depth)))

    # Hole tunnel surfaces join the front and back contours, leaving the center
    # open all the way through the board thickness.
    for contour in contours:
        for i, (u0, v0) in enumerate(contour):
            u1, v1 = contour[(i + 1) % len(contour)]
            add_quad((point(u0,v0,-half_t), point(u1,v1,-half_t),
                      point(u1,v1,half_t), point(u0,v0,half_t)))

    # Board edges expose a solid cross-section around the perimeter.
    corners = ((-half_u_m,-half_v_m),(half_u_m,-half_v_m),
               (half_u_m,half_v_m),(-half_u_m,half_v_m))
    for i, (u0,v0) in enumerate(corners):
        u1,v1 = corners[(i+1) % 4]
        add_quad((point(u0,v0,-half_t),point(u1,v1,-half_t),
                  point(u1,v1,half_t),point(u0,v0,half_t)))
    writer.mesh(name, points, faces, material, color, roughness, double_sided=True)


def _aperture(shape: str, u: float, v: float, half_u: float, half_v: float | None = None) -> _Hole:
    return {"shape": shape, "center": (u, v), "half": (half_u, half_u if half_v is None else half_v)}


def draw_shape_sorter(stage, root_path, size, color):
    """Create U08's closed wooden sorter shell with top and side cut-throughs."""
    writer = _StageWriter(stage, root_path, size)
    sx, sy, sz = writer.size
    thickness = min(0.015, min(writer.size) * 0.12)
    wood = _rgb(color)
    endgrain = _rgb(color, 0.83)
    top_holes = (
        # The block proxies are about 30 mm across. These 40–48 mm openings
        # leave practical clearance instead of looking passable but binding.
        _aperture("circle", -0.052, -0.043, 0.020),
        _aperture("square", 0.052, -0.043, 0.022),
        _aperture("triangle", 0.000, 0.045, 0.024, 0.022),
    )
    _panel(writer, "sorter/top_perforated_lid", normal_axis=2, u_axis=0, v_axis=1,
           center_normal_m=sz/2-thickness/2, half_u_m=sx/2, half_v_m=sy/2,
           thickness_m=thickness, holes=top_holes, material="wood_top", color=wood, roughness=0.82)
    _panel(writer, "sorter/bottom", normal_axis=2, u_axis=0, v_axis=1,
           center_normal_m=-sz/2+thickness/2, half_u_m=sx/2, half_v_m=sy/2,
           thickness_m=thickness, holes=(), material="wood_endgrain", color=endgrain, roughness=0.86)

    # Closed vertical sides, each with genuine apertures. Hole shapes vary by
    # face to echo the photo's multi-face sorter; exact paper hole layout is
    # unclear at thumbnail resolution, so this is a marked reconstruction.
    side_z_half = max(0.005, sz/2-thickness)
    front_holes = (
        _aperture("circle", -0.055, 0.018, 0.018),
        _aperture("square", 0.052, 0.018, 0.019),
        _aperture("triangle", 0.000, -0.033, 0.022, 0.020),
    )
    _panel(writer, "sorter/front_y_negative", normal_axis=1, u_axis=0, v_axis=2,
           center_normal_m=-sy/2+thickness/2, half_u_m=sx/2, half_v_m=side_z_half,
           thickness_m=thickness, holes=front_holes, material="wood_front", color=wood, roughness=0.84)
    _panel(writer, "sorter/back_y_positive", normal_axis=1, u_axis=0, v_axis=2,
           center_normal_m=sy/2-thickness/2, half_u_m=sx/2, half_v_m=side_z_half,
           thickness_m=thickness, holes=front_holes, material="wood_back", color=endgrain, roughness=0.86)
    side_holes = (
        _aperture("triangle", -sy*0.27, 0.018, 0.020, 0.019),
        _aperture("circle", 0.000, 0.018, 0.019),
        _aperture("square", sy*0.27, 0.018, 0.019),
    )
    for axis, side_name, sign in ((0,"x_negative",-1),(0,"x_positive",1)):
        _panel(writer, f"sorter/{side_name}", normal_axis=axis, u_axis=1, v_axis=2,
               center_normal_m=sign*(sx/2-thickness/2), half_u_m=sy/2, half_v_m=side_z_half,
               thickness_m=thickness, holes=side_holes, material="wood_sides", color=wood, roughness=0.84)
    return writer.root


def draw_wire_box(stage, root_path, size, color):
    """Create U20's pale open-top box with multiple real wall apertures."""
    writer = _StageWriter(stage, root_path, size)
    sx, sy, sz = writer.size
    thickness = min(0.008, min(writer.size) * 0.10)
    body = _rgb(color)
    inner = _rgb(color, 0.88)
    _panel(writer, "wire_box/bottom", normal_axis=2, u_axis=0, v_axis=1,
           center_normal_m=-sz/2+thickness/2, half_u_m=sx/2, half_v_m=sy/2,
           thickness_m=thickness, holes=(), material="box_floor", color=inner, roughness=0.78)

    # Aperture sizes are kept small enough to read as a perforated basket, with
    # the three task-mapped threading waypoints represented on separate walls.
    holes_xneg = (
        _aperture("circle", -0.035, 0.005, 0.0100),
        _aperture("circle", 0.035, -0.022, 0.0090),
        _aperture("circle", 0.030, 0.031, 0.0090),
    )
    holes_ypos = (
        _aperture("circle", 0.025, 0.015, 0.0100),
        _aperture("circle", -0.045, -0.020, 0.0090),
        _aperture("circle", 0.045, 0.040, 0.0090),
    )
    holes_xpos = (
        _aperture("circle", 0.035, 0.020, 0.0100),
        _aperture("circle", -0.040, -0.022, 0.0090),
        _aperture("circle", -0.035, 0.045, 0.0090),
    )
    holes_yneg = (
        _aperture("circle", -sx*0.27, 0.014, 0.0090),
        _aperture("circle", 0.000, 0.035, 0.0090),
        _aperture("circle", sx*0.27, -0.018, 0.0090),
    )
    wall_half_height = sz/2-thickness/2
    side_specs = (
        (1,0,2,-sy/2+thickness/2, sx/2, ("front_y_negative",holes_yneg)),
        (1,0,2, sy/2-thickness/2, sx/2, ("back_y_positive",holes_ypos)),
        (0,1,2,-sx/2+thickness/2, sy/2, ("side_x_negative",holes_xneg)),
        (0,1,2, sx/2-thickness/2, sy/2, ("side_x_positive",holes_xpos)),
    )
    for normal_axis,u_axis,v_axis,center,half_u,(name,holes) in side_specs:
        _panel(writer, "wire_box/"+name, normal_axis=normal_axis, u_axis=u_axis, v_axis=v_axis,
               center_normal_m=center, half_u_m=half_u, half_v_m=wall_half_height,
               thickness_m=thickness, holes=holes, material="pale_box_walls", color=body, roughness=0.74)

    # Four narrow top rails define a rim around an unmistakably empty opening.
    rim_h = thickness * 1.25
    rim_w = thickness * 1.25
    top_z = sz/2-rim_h/2
    writer.box("wire_box/open_rim_x_negative", (-sx/2+rim_w/2,0.0,top_z), (rim_w,sy,rim_h), inner, "rim", 0.72)
    writer.box("wire_box/open_rim_x_positive", ( sx/2-rim_w/2,0.0,top_z), (rim_w,sy,rim_h), inner, "rim", 0.72)
    writer.box("wire_box/open_rim_y_negative", (0.0,-sy/2+rim_w/2,top_z), (sx,rim_w,rim_h), inner, "rim", 0.72)
    writer.box("wire_box/open_rim_y_positive", (0.0, sy/2-rim_w/2,top_z), (sx,rim_w,rim_h), inner, "rim", 0.72)
    return writer.root
