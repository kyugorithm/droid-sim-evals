"""Shared, visual-only procedural geometry for Appendix G scene assets.
All coordinates are authored in a centered unit box and scaled to ``size``.
Each public function creates prims below ``root_path/visual/v7``.  The module
has no USD imports at import time so it can be inspected without Isaac/PXR.
"""

from __future__ import annotations

import math
from typing import Sequence


Vec3 = tuple[float, float, float]
Face = tuple[int, ...]


def _unit_color(color: Sequence[float]) -> Vec3:
    if len(color) < 3:
        raise ValueError("color must contain at least three channels")
    return tuple(max(0.0, min(1.0, float(channel))) for channel in color[:3])  # type: ignore[return-value]


def _shade(color: Sequence[float], factor: float, tint: Sequence[float] = (1.0, 1.0, 1.0)) -> Vec3:
    base = _unit_color(color)
    return tuple(max(0.0, min(1.0, base[i] * factor * tint[i])) for i in range(3))  # type: ignore[return-value]


class _Visual:
    """Small USD mesh/material writer; instantiated only by public builders."""

    def __init__(self, stage, root_path: str, size: Sequence[float]):
        from pxr import Gf, Sdf, UsdGeom, UsdShade

        if len(size) != 3 or any(float(v) <= 0.0 for v in size):
            raise ValueError("size must be three positive dimensions")
        self.Gf, self.Sdf, self.UsdGeom, self.UsdShade = Gf, Sdf, UsdGeom, UsdShade
        self.stage = stage
        self.root = root_path.rstrip("/") + "/visual/v7"
        self.size = tuple(float(v) for v in size)
        self._materials: dict[str, object] = {}
        stage.DefinePrim(root_path, "Xform")
        stage.DefinePrim(root_path.rstrip("/") + "/visual", "Xform")
        stage.DefinePrim(self.root, "Xform")
        stage.DefinePrim(self.root + "/materials", "Scope")

    def material(self, name: str, color: Sequence[float], roughness: float, metallic: float = 0.0):
        if name in self._materials:
            return self._materials[name]
        Sdf, UsdShade = self.Sdf, self.UsdShade
        path = self.root + "/materials/" + name
        material = UsdShade.Material.Define(self.stage, path)
        shader = UsdShade.Shader.Define(self.stage, path + "/PreviewSurface")
        shader.CreateIdAttr("UsdPreviewSurface")
        shader.CreateInput("diffuseColor", Sdf.ValueTypeNames.Color3f).Set(self.Gf.Vec3f(*_unit_color(color)))
        shader.CreateInput("roughness", Sdf.ValueTypeNames.Float).Set(float(roughness))
        shader.CreateInput("metallic", Sdf.ValueTypeNames.Float).Set(float(metallic))
        shader.CreateInput("specular", Sdf.ValueTypeNames.Float).Set(0.32)
        material.CreateSurfaceOutput().ConnectToSource(
            shader.CreateOutput("surface", Sdf.ValueTypeNames.Token)
        )
        self._materials[name] = material
        return material

    def mesh(
        self,
        name: str,
        points: Sequence[Sequence[float]],
        faces: Sequence[Face],
        material_name: str,
        color: Sequence[float],
        roughness: float,
        metallic: float = 0.0,
        *,
        double_sided: bool = False,
    ) -> None:
        if not points or not faces:
            return
        if any(abs(float(axis)) > 0.500001 for point in points for axis in point):
            raise ValueError(f"{name} exceeds the centered unit bounds")
        Gf, UsdGeom = self.Gf, self.UsdGeom
        path = self.root + "/" + name
        mesh = UsdGeom.Mesh.Define(self.stage, path)
        sx, sy, sz = self.size
        scaled = [Gf.Vec3f(float(p[0]) * sx, float(p[1]) * sy, float(p[2]) * sz) for p in points]
        counts = [len(face) for face in faces]
        indices = [int(index) for face in faces for index in face]
        mesh.CreatePointsAttr(scaled)
        mesh.CreateFaceVertexCountsAttr(counts)
        mesh.CreateFaceVertexIndicesAttr(indices)
        mesh.CreateSubdivisionSchemeAttr(UsdGeom.Tokens.none)
        if double_sided:
            mesh.CreateDoubleSidedAttr(True)

        # Smooth vertex normals are accumulated from each polygon fan.
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
            length = math.sqrt(sum(value * value for value in normal))
            if length < 1e-12:
                normal_values.append(Gf.Vec3f(0.0, 0.0, 1.0))
            else:
                normal_values.append(Gf.Vec3f(*(value / length for value in normal)))
        mesh.CreateNormalsAttr(normal_values)
        mesh.SetNormalsInterpolation(UsdGeom.Tokens.vertex)
        mesh.CreateDisplayColorAttr([Gf.Vec3f(*_unit_color(color))])
        self.UsdShade.MaterialBindingAPI.Apply(mesh.GetPrim()).Bind(
            self.material(material_name, color, roughness, metallic)
        )


def _sphere(writer: _Visual, name: str, center: Vec3, radii: Vec3, color: Vec3, mat: str, roughness: float, rings: int = 10, segments: int = 16) -> None:
    points: list[Vec3] = []
    faces: list[Face] = []
    for row in range(rings + 1):
        phi = -0.5 * math.pi + math.pi * row / rings
        for col in range(segments):
            theta = 2.0 * math.pi * col / segments
            points.append((center[0] + radii[0] * math.cos(phi) * math.cos(theta),
                           center[1] + radii[1] * math.cos(phi) * math.sin(theta),
                           center[2] + radii[2] * math.sin(phi)))
    for row in range(rings):
        for col in range(segments):
            nxt = (col + 1) % segments
            a, b = row * segments + col, row * segments + nxt
            c, d = (row + 1) * segments + nxt, (row + 1) * segments + col
            faces.append((a, b, c, d))
    writer.mesh(name, points, faces, mat, color, roughness)


def _tube(writer: _Visual, name: str, points: Sequence[Vec3], radius: float, color: Vec3, mat: str, roughness: float, sides: int = 8, closed: bool = False) -> None:
    """Create a round tubular strand along a polyline in normalized space."""
    if len(points) < 2:
        return
    rings: list[list[Vec3]] = []
    for i, point in enumerate(points):
        before = points[(i - 1) % len(points)] if (closed or i > 0) else points[i]
        after = points[(i + 1) % len(points)] if (closed or i + 1 < len(points)) else points[i]
        tangent = (after[0] - before[0], after[1] - before[1], after[2] - before[2])
        length = math.sqrt(sum(v * v for v in tangent)) or 1.0
        tangent = tuple(v / length for v in tangent)
        ref = (0.0, 0.0, 1.0) if abs(tangent[2]) < 0.88 else (0.0, 1.0, 0.0)
        u = (tangent[1] * ref[2] - tangent[2] * ref[1], tangent[2] * ref[0] - tangent[0] * ref[2], tangent[0] * ref[1] - tangent[1] * ref[0])
        ul = math.sqrt(sum(v * v for v in u)) or 1.0
        u = tuple(v / ul for v in u)
        v = (tangent[1] * u[2] - tangent[2] * u[1], tangent[2] * u[0] - tangent[0] * u[2], tangent[0] * u[1] - tangent[1] * u[0])
        ring = []
        for j in range(sides):
            theta = 2.0 * math.pi * j / sides
            ring.append(tuple(point[k] + radius * (math.cos(theta) * u[k] + math.sin(theta) * v[k]) for k in range(3)))
        rings.append(ring)  # type: ignore[arg-type]
    faces: list[Face] = []
    for i in range(len(rings) if closed else len(rings) - 1):
        ni = (i + 1) % len(rings)
        for j in range(sides):
            nj = (j + 1) % sides
            faces.append((i * sides + j, i * sides + nj, ni * sides + nj, ni * sides + j))
    writer.mesh(name, [p for ring in rings for p in ring], faces, mat, color, roughness)


def _rounded_rect_loop(hx: float, hy: float, corner: float, z: float, arc_steps: int = 7) -> list[Vec3]:
    loop: list[Vec3] = []
    corners = ((hx - corner, hy - corner, 0.0), (-hx + corner, hy - corner, 90.0),
               (-hx + corner, -hy + corner, 180.0), (hx - corner, -hy + corner, 270.0))
    for cx, cy, start_deg in corners:
        for step in range(arc_steps + 1):
            angle = math.radians(start_deg + 90.0 * step / arc_steps)
            loop.append((cx + corner * math.cos(angle), cy + corner * math.sin(angle), z))
    return loop


def draw_grape_cluster(stage, root_path, size, color):
    """Draw one compact, tapered, touching bunch of grapes with stem/leaf."""
    base = _unit_color(color)
    w = _Visual(stage, root_path, size)
    # Staggered 3-D rows overlap by design. Outer rows taper toward the bottom;
    # the larger bunch fills the box while the small distractor remains a bunch.
    layout = [
        (-0.12, -0.18, -0.34004, 0.258), (0.12, -0.18, -0.33, 0.25),
        (-0.24, -0.04, -0.14, 0.258), (0.00, -0.04, -0.14, 0.258), (0.24, -0.04, -0.14, 0.258),
        (-0.24, 0.12, 0.06, 0.258), (0.00, 0.12, 0.06, 0.258), (0.24, 0.12, 0.06, 0.258),
        (-0.16, 0.24, 0.26, 0.258), (0.16, 0.24, 0.26, 0.258),
    ]
    for index, (x, y, z, radius) in enumerate(layout):
        # Constant normalized radii preserve berry-to-berry contact and the
        # tapered silhouette at both Appendix G object sizes.
        r = radius * 0.62
        radii = (r, r, r)
        berry_color = _shade(base, (0.91, 1.02, 0.96, 1.08)[index % 4])
        _sphere(w, f"berries/berry_{index:02d}", (x, y, z), radii, berry_color,
                f"berry_{index % 4}", 0.30, rings=9, segments=14)
    stem_color = (0.30, 0.20, 0.08)
    _tube(w, "stem", ((0.0, 0.18, 0.22), (0.01, 0.18, 0.36), (0.0, 0.19, 0.46)),
          0.024, stem_color, "stem", 0.76)
    leaf_color = _shade(stem_color, 1.55, (0.72, 1.35, 0.62))
    _sphere(w, "calyx_leaf", (0.06, 0.18, 0.34), (0.11, 0.045, 0.035), leaf_color, "leaf", 0.68, 6, 10)
    return w.root


def draw_tripod(stage, root_path, size, color):
    """Draw a photographic three-leg camera tripod with head and braces."""
    w = _Visual(stage, root_path, size)
    dark = _unit_color(color)
    metal = _shade(dark, 0.74, (1.05, 1.08, 1.12))
    rubber = _shade(dark, 0.48)
    head_color = _shade(dark, 0.88, (1.08, 1.08, 1.10))
    top = (0.0, 0.0, 0.44)
    leg_ends = ((-0.42, -0.33, -0.43), (0.42, -0.33, -0.43), (0.0, 0.43, -0.43))
    joints = []
    for index, end in enumerate(leg_ends):
        knee = (end[0] * 0.56, end[1] * 0.56, -0.13)
        joints.append(knee)
        _tube(w, f"legs/upper_{index}", (top, knee), 0.055, metal, "anodized_legs", 0.34, 10)
        _tube(w, f"legs/lower_{index}", (knee, end), 0.038, metal, "lower_legs", 0.42, 10)
        foot = (end[0], end[1], -0.50)
        _tube(w, f"feet/rubber_{index}", (end, foot), 0.018, rubber, "rubber_feet", 0.88, 10)
        _sphere(w, f"joints/hinge_{index}", knee, (0.070, 0.070, 0.052), head_color, "hinge", 0.4, 7, 12)
    # Three rigid-looking braces meet at a lower spreader hub, visibly tying
    # all legs together without making a solid block across the tripod.
    hub = (0.0, 0.0, -0.07)
    for index, knee in enumerate(joints):
        _tube(w, f"braces/spreader_{index}", (hub, knee), 0.021, head_color, "braces", 0.45, 8)
    _sphere(w, "braces/hub", hub, (0.085, 0.085, 0.055), head_color, "hub", 0.42, 8, 14)
    _tube(w, "center_column", ((0.0, 0.0, 0.16), (0.0, 0.0, 0.44)), 0.052, metal, "column", 0.31, 12)
    # Camera mounting platform, neck, and screw are distinct readable pieces.
    _tube(w, "head/neck", ((0.0, 0.0, 0.40), (0.0, 0.0, 0.45)), 0.045, head_color, "head", 0.32, 12)
    _sphere(w, "head/ball", (0.0, 0.0, 0.40), (0.105, 0.105, 0.09), head_color, "ball_joint", 0.28, 9, 16)
    # Compact camera shoe, with a narrow pointed post visible above it. The
    # earlier broad plate hid the post and looked too blunt for the hanging
    # setup requested by the task review.
    points = [(-0.13, -0.10, 0.43), (0.13, -0.10, 0.43), (0.13, 0.10, 0.43), (-0.13, 0.10, 0.43),
              (-0.13, -0.10, 0.465), (0.13, -0.10, 0.465), (0.13, 0.10, 0.465), (-0.13, 0.10, 0.465)]
    faces = ((0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7))
    w.mesh("head/mount_plate", points, faces, "mount_plate", _shade(head_color, 0.9), 0.3, 0.18)
    base_ring, tip_ring = [], []
    for index in range(16):
        angle = 2.0 * math.pi * index / 16
        base_ring.append((0.055 * math.cos(angle), 0.055 * math.sin(angle), 0.455))
        tip_ring.append((0.004 * math.cos(angle), 0.004 * math.sin(angle), 0.50))
    pin_points = base_ring + tip_ring
    pin_faces = [(index, (index + 1) % 16, 16 + (index + 1) % 16, 16 + index)
                 for index in range(16)]
    w.mesh("head/pointed_mount_post", pin_points, pin_faces, "pointed_mount_post",
           _shade(metal, 1.18), 0.24, 0.32, double_sided=True)
    return w.root


def draw_hat(stage, root_path, size, color):
    """Draw a brimmed fedora with a pinched, dented crown and hatband."""
    w = _Visual(stage, root_path, size)
    felt = _unit_color(color)
    band_color = _shade(felt, 1.30, (0.86, 0.83, 0.79))
    segments = 56
    # Brim is a shallow curved annular shell, not a filled disc; its crown
    # opening is genuinely open and the edge has a gentle fedora dip.
    brim_profiles = ((0.29, -0.4819311), (0.98, -0.405), (1.00, -0.35), (0.34, -0.27))
    points: list[Vec3] = []
    for ring, (scale, z) in enumerate(brim_profiles):
        for i in range(segments):
            a = 2.0 * math.pi * i / segments
            front_dip = 0.035 * math.cos(2.0 * a) + 0.018 * math.cos(a)
            points.append((scale * 0.5 * math.cos(a), scale * 0.47 * math.sin(a), z + front_dip * (1.0 if ring in (1, 2) else 0.5)))
    faces: list[Face] = []
    for ring in range(len(brim_profiles)):
        nxt_ring = (ring + 1) % len(brim_profiles)
        for i in range(segments):
            j = (i + 1) % segments
            faces.append((ring * segments + i, ring * segments + j, nxt_ring * segments + j, nxt_ring * segments + i))
    w.mesh("brim", points, faces, "felt_brim", felt, 0.82, double_sided=True)

    # Crown widens at the base, rounds into a pinched tapered top, and ends in
    # a concave fedora dent rather than a cone or flat cylinder cap.
    profiles = ((0.34, -0.27), (0.34, -0.12), (0.32, 0.16), (0.28, 0.34), (0.22, 0.43), (0.16, 0.44))
    points = []
    for radius, z in profiles:
        for i in range(segments):
            a = 2.0 * math.pi * i / segments
            pinch = 1.0 - 0.12 * max(0.0, z) * math.cos(2.0 * a)
            points.append((radius * pinch * math.cos(a), radius * 0.91 * pinch * math.sin(a), z))
    faces = []
    for ring in range(len(profiles) - 1):
        for i in range(segments):
            j = (i + 1) % segments
            faces.append((ring * segments + i, ring * segments + j,
                          (ring + 1) * segments + j, (ring + 1) * segments + i))
    center_index = len(points)
    points.append((0.0, 0.0, 0.365))
    top_ring = len(profiles) - 1
    for i in range(segments):
        faces.append((top_ring * segments + i, top_ring * segments + (i + 1) % segments, center_index))
    w.mesh("crown", points, faces, "felt_crown", _shade(felt, 0.94), 0.84, double_sided=True)

    # Wrapped band around the crown base, with a narrow contrasting seam.
    for layer, z in enumerate((-0.205, -0.145)):
        loop = []
        for i in range(segments + 1):
            a = 2.0 * math.pi * (i % segments) / segments
            loop.append((0.345 * math.cos(a), 0.314 * math.sin(a), z))
        _tube(w, f"band/wrap_{layer}", loop, 0.020, band_color, "band", 0.62, 8, closed=True)
    # Short band keeper / bow gives the band a material break visible in profile.
    _tube(w, "band/keeper", ((0.30, -0.09, -0.20), (0.30, 0.09, -0.20)), 0.018,
          _shade(band_color, 0.78), "band_keeper", 0.66)
    return w.root


def draw_wicker_basket(stage, root_path, size, color):
    """Draw a rounded tapered woven basket with an open gingham-lined mouth."""
    w = _Visual(stage, root_path, size)
    wicker = _unit_color(color)
    wicker_light = _shade(wicker, 1.23, (1.04, 0.98, 0.86))
    wicker_dark = _shade(wicker, 0.78, (0.95, 0.91, 0.81))
    interior = _shade(wicker, 0.67, (0.91, 0.88, 0.79))
    # The side is made of many narrow strands. The cavity stays open: no top
    # polygon or opaque insert spans the mouth.
    base_loop = _rounded_rect_loop(0.34, 0.33, 0.12, -0.47)
    rim_loop = _rounded_rect_loop(0.45, 0.42, 0.14, 0.40)
    count = len(base_loop)
    # Four fine bottom slats and perimeter rails suggest a woven floor while
    # leaving visible gaps between slats.
    for index in range(5):
        y = -0.27 + index * 0.135
        _tube(w, f"base/slat_x_{index}", ((-0.29, y, -0.455), (0.29, y, -0.455)), 0.024,
              wicker_light if index % 2 else wicker_dark, "base_slats", 0.9, 7)
    for index in range(5):
        x = -0.28 + index * 0.14
        _tube(w, f"base/slat_y_{index}", ((x, -0.27, -0.448), (x, 0.27, -0.448)), 0.022,
              wicker_dark if index % 2 else wicker_light, "cross_slats", 0.9, 7)
    _tube(w, "base/perimeter_foot", _rounded_rect_loop(0.34, 0.33, 0.12, -0.48), 0.020,
          wicker_dark, "basket_foot", 0.9, 8, closed=True)

    # Vertical willow stakes taper outwards with the basket wall.
    stake_count = 36
    for index in range(stake_count):
        source = int(index * count / stake_count)
        bx, by, _ = base_loop[source]
        tx, ty, _ = rim_loop[source]
        offset = 0.010 if index % 2 else -0.006
        points = ((bx, by, -0.43),
                  (bx * 0.68 + tx * 0.32 + offset, by * 0.68 + ty * 0.32, -0.12),
                  (bx * 0.32 + tx * 0.68 + offset, by * 0.32 + ty * 0.68, 0.18),
                  (tx, ty, 0.39))
        _tube(w, f"weave/stake_{index:02d}", points, 0.014,
              wicker_light if index % 3 else wicker_dark, "vertical_wicker", 0.88, 7)
    # Continuous horizontal weavers form the recognizable alternating weave.
    for row, z in enumerate((-0.37, -0.28, -0.19, -0.10, -0.01, 0.08, 0.17, 0.26, 0.34)):
        t = (z + 0.47) / 0.87
        loop = []
        for bx, by, _ in base_loop:
            corresponding = len(loop)
            rx, ry, _ = rim_loop[corresponding]
            loop.append((bx * (1.0 - t) + rx * t, by * (1.0 - t) + ry * t, z + (0.009 if row % 2 else -0.006)))
        _tube(w, f"weave/course_{row:02d}", loop, 0.022,
              wicker_dark if row % 2 else wicker_light, "horizontal_wicker", 0.9, 7, closed=True)
    # Reinforced rolled lip is a softly rounded, double course.
    _tube(w, "rim/rolled_outer", _rounded_rect_loop(0.45, 0.42, 0.14, 0.405), 0.025, wicker_light, "rolled_rim", 0.84, 9, closed=True)
    _tube(w, "rim/rolled_inner", _rounded_rect_loop(0.42, 0.39, 0.12, 0.39), 0.018, wicker_dark, "rim_inner", 0.88, 8, closed=True)

    # Thin inner wall under the rim, tiled with alternating red/cream gingham
    # patches. These are surface panels following the basket and never cover
    # its opening; their top edge folds just over the wicker lip.
    cloth_red = (0.58, 0.075, 0.085)
    cloth_cream = (0.91, 0.82, 0.70)
    panel_count, rows = 32, 5
    perimeter = _rounded_rect_loop(0.425, 0.395, 0.12, 0.0, arc_steps=10)
    pcount = len(perimeter)
    cloth_points: dict[str, list[Vec3]] = {"red": [], "cream": []}
    cloth_faces: dict[str, list[Face]] = {"red": [], "cream": []}
    for cell in range(panel_count):
        a = int(cell * pcount / panel_count)
        b = int((cell + 1) * pcount / panel_count) % pcount
        p0, p1 = perimeter[a], perimeter[b]
        for row in range(rows):
            z0 = 0.02 + row * 0.072
            z1 = z0 + 0.075
            # Leave a narrow top reveal and follow the cavity's tapered inside.
            t0, t1 = (z0 + 0.47) / 0.87, (z1 + 0.47) / 0.87
            f0, f1 = (0.34 + 0.14 * t0) / 0.425, (0.34 + 0.14 * t1) / 0.425
            q0 = (p0[0] * f0, p0[1] * f0, z0)
            q1 = (p1[0] * f0, p1[1] * f0, z0)
            q2 = (p1[0] * f1, p1[1] * f1, z1)
            q3 = (p0[0] * f1, p0[1] * f1, z1)
            face_color = cloth_red if (cell + row) % 2 == 0 else cloth_cream
            key = "red" if face_color == cloth_red else "cream"
            offset = len(cloth_points[key])
            cloth_points[key].extend((q0, q1, q2, q3))
            cloth_faces[key].append((offset, offset + 1, offset + 2, offset + 3))
    w.mesh("lining/gingham_red", cloth_points["red"], cloth_faces["red"], "gingham_red", cloth_red, 0.96, double_sided=True)
    w.mesh("lining/gingham_cream", cloth_points["cream"], cloth_faces["cream"], "gingham_cream", cloth_cream, 0.96, double_sided=True)
    # A narrow fabric fold drapes over the inside rim as a scalloped edge.
    hem = []
    for i, (x, y, _) in enumerate(_rounded_rect_loop(0.438, 0.408, 0.13, 0.34, arc_steps=10)):
        hem.append((x, y, 0.34 + 0.012 * math.sin(i * 1.7)))
    _tube(w, "lining/folded_hem", hem, 0.018, cloth_red, "cloth_hem", 0.94, 8, closed=True)
    return w.root
