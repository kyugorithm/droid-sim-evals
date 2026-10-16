"""Standalone PXR authoring helper for the Appendix G turquoise basket."""


def draw_blue_basket(stage, root_path, size, color):
    """Author a tapered, perforated turquoise basket under ``visual/v7_blue``.

    ``size`` is the exact outer XYZ bound in meters. The basket is centered in
    X/Y, its base is at ``-size[2] / 2``, and its rim reaches ``+size[2] / 2``.
    This function creates render meshes only: it does not define a root Xform,
    collision geometry, or physics attributes.
    """
    import math

    from pxr import Gf, UsdGeom

    sx, sy, sz = (float(value) for value in size)
    if min(sx, sy, sz) <= 0.0:
        raise ValueError("basket size components must be positive")
    blue = tuple(float(value) for value in color[:3])
    if len(blue) != 3:
        raise ValueError("color must contain three RGB components")

    base_path = f"{root_path.rstrip('/')}/visual/v7_blue"
    UsdGeom.Scope.Define(stage, base_path)

    # Aggregate simple quads into two render meshes, one for the basket and
    # one for the small pale swing handle. Keeping this self-contained avoids
    # dependencies on helpers in the main scene builder.
    parts = {
        "basket": {"points": [], "counts": [], "indices": []},
        "handle": {"points": [], "counts": [], "indices": []},
    }

    def quad(part, points):
        data = parts[part]
        start = len(data["points"])
        data["points"].extend(tuple(float(v) for v in p) for p in points)
        data["counts"].append(4)
        data["indices"].extend((start, start + 1, start + 2, start + 3))

    def triangle(part, points):
        data = parts[part]
        start = len(data["points"])
        data["points"].extend(tuple(float(v) for v in p) for p in points)
        data["counts"].append(3)
        data["indices"].extend((start, start + 1, start + 2))

    def rounded_rect(hx, hy, radius, z, steps=5):
        """Counter-clockwise rounded rectangle contour in the XY plane."""
        radius = min(radius, hx, hy)
        corners = (
            (hx - radius, -hy + radius, -90.0),
            (hx - radius, hy - radius, 0.0),
            (-hx + radius, hy - radius, 90.0),
            (-hx + radius, -hy + radius, 180.0),
        )
        points = []
        for cx, cy, first_angle in corners:
            for step in range(steps + 1):
                angle = math.radians(first_angle + 90.0 * step / steps)
                points.append((cx + radius * math.cos(angle),
                              cy + radius * math.sin(angle), z))
        return points

    # A solid, rounded floor sits exactly on the requested lower bound.
    bottom_z = -sz / 2.0
    floor_top = bottom_z + max(0.004, sz * 0.045)
    floor_hx, floor_hy = sx * 0.365, sy * 0.365
    floor_radius = min(sx, sy) * 0.095
    floor_ring = rounded_rect(floor_hx, floor_hy, floor_radius, floor_top)
    center = (0.0, 0.0, floor_top)
    for index, point in enumerate(floor_ring):
        triangle("basket", (center, point, floor_ring[(index + 1) % len(floor_ring)]))
    # Short vertical fascia around the floor edge.
    floor_lower = [(x, y, bottom_z) for x, y, _ in floor_ring]
    bottom_center = (0.0, 0.0, bottom_z)
    for index in range(len(floor_ring)):
        nxt = (index + 1) % len(floor_ring)
        triangle("basket", (bottom_center, floor_lower[nxt], floor_lower[index]))
        quad("basket", (floor_lower[index], floor_lower[nxt],
                         floor_ring[nxt], floor_ring[index]))

    # Tapered walls: bottom is 76% of the mouth width. Rounded corners are
    # continuous solid panels; the four straight walls contain real through
    # holes made from ring-shaped quads and their inner tunnel faces.
    wall_bottom = floor_top
    wall_top = sz / 2.0 - max(0.004, sz * 0.035)
    bottom_hx, bottom_hy = sx * 0.385, sy * 0.385
    top_hx, top_hy = sx * 0.475, sy * 0.475
    corner_radius = min(sx, sy) * 0.115
    wall_thickness = min(sx, sy) * 0.036

    def profile(z):
        t = (z - wall_bottom) / (wall_top - wall_bottom)
        hx = bottom_hx + (top_hx - bottom_hx) * t
        hy = bottom_hy + (top_hy - bottom_hy) * t
        return hx, hy

    def wall_point(axis, sign, u, z, depth):
        hx, hy = profile(z)
        if axis == "long":
            return (u * (hx - corner_radius), sign * (hy + depth), z)
        return (sign * (hx + depth), u * (hy - corner_radius), z)

    def perforated_cell(axis, sign, u0, u1, z0, z1):
        # Leave sturdy plastic between apertures; these are open apertures,
        # not dark decals or inset circles.
        inset_u = (u1 - u0) * 0.24
        inset_z = (z1 - z0) * 0.25
        outer_uvz = ((u0, z0), (u1, z0), (u1, z1), (u0, z1))
        inner_uvz = ((u0 + inset_u, z0 + inset_z),
                     (u1 - inset_u, z0 + inset_z),
                     (u1 - inset_u, z1 - inset_z),
                     (u0 + inset_u, z1 - inset_z))
        # Front and back face rings.
        for depth, reverse in ((-wall_thickness / 2.0, False),
                               (wall_thickness / 2.0, True)):
            outer = [wall_point(axis, sign, u, z, depth) for u, z in outer_uvz]
            inner = [wall_point(axis, sign, u, z, depth) for u, z in inner_uvz]
            for i in range(4):
                j = (i + 1) % 4
                face = (outer[i], outer[j], inner[j], inner[i])
                quad("basket", tuple(reversed(face)) if reverse else face)
        # Outer thickness and the inside walls reveal a genuine open hole.
        for i in range(4):
            j = (i + 1) % 4
            outer_front = wall_point(axis, sign, *outer_uvz[i], -wall_thickness / 2)
            outer_back = wall_point(axis, sign, *outer_uvz[i], wall_thickness / 2)
            outer_front_next = wall_point(axis, sign, *outer_uvz[j], -wall_thickness / 2)
            outer_back_next = wall_point(axis, sign, *outer_uvz[j], wall_thickness / 2)
            quad("basket", (outer_front, outer_front_next,
                             outer_back_next, outer_back))
            inner_front = wall_point(axis, sign, *inner_uvz[i], -wall_thickness / 2)
            inner_back = wall_point(axis, sign, *inner_uvz[i], wall_thickness / 2)
            inner_front_next = wall_point(axis, sign, *inner_uvz[j], -wall_thickness / 2)
            inner_back_next = wall_point(axis, sign, *inner_uvz[j], wall_thickness / 2)
            quad("basket", (inner_front, inner_back,
                             inner_back_next, inner_front_next))

    rows = 4
    for axis, columns in (("long", 4), ("short", 3)):
        for sign in (-1.0, 1.0):
            for row in range(rows):
                z0 = wall_bottom + (wall_top - wall_bottom) * row / rows
                z1 = wall_bottom + (wall_top - wall_bottom) * (row + 1) / rows
                for column in range(columns):
                    u0 = -0.82 + 1.64 * column / columns
                    u1 = -0.82 + 1.64 * (column + 1) / columns
                    perforated_cell(axis, sign, u0, u1, z0, z1)

    # Solid, curved corner webs join the straight perforated panels. Each
    # quarter-turn has a rounded vertical profile and remains within bounds.
    corner_steps = 8
    for sign_x in (-1.0, 1.0):
        for sign_y in (-1.0, 1.0):
            for step in range(corner_steps):
                a0 = (math.pi / 2.0) * step / corner_steps
                a1 = (math.pi / 2.0) * (step + 1) / corner_steps
                for depth in (-wall_thickness / 2.0, wall_thickness / 2.0):
                    points = []
                    for z, angle in ((wall_bottom, a0), (wall_bottom, a1),
                                     (wall_top, a1), (wall_top, a0)):
                        hx, hy = profile(z)
                        radius = corner_radius + depth
                        cx = sign_x * (hx - corner_radius)
                        cy = sign_y * (hy - corner_radius)
                        points.append((cx + sign_x * radius * math.cos(angle),
                                       cy + sign_y * radius * math.sin(angle), z))
                    quad("basket", points)

    # Rounded rolled lip; its outer contour sets the exact requested XY bounds.
    rim_h = max(0.006, sz * 0.055)
    rim_mid_z = sz / 2.0 - rim_h / 2.0
    rim_outer = rounded_rect(sx / 2.0, sy / 2.0, min(sx, sy) * 0.14, rim_mid_z + rim_h / 2.0)
    rim_inner = rounded_rect(sx / 2.0 - wall_thickness * 1.5,
                             sy / 2.0 - wall_thickness * 1.5,
                             min(sx, sy) * 0.105, rim_mid_z + rim_h / 2.0)
    rim_outer_low = [(x, y, rim_mid_z - rim_h / 2.0) for x, y, _ in rim_outer]
    rim_inner_low = [(x, y, rim_mid_z - rim_h / 2.0) for x, y, _ in rim_inner]
    for index in range(len(rim_outer)):
        nxt = (index + 1) % len(rim_outer)
        quad("basket", (rim_outer_low[index], rim_outer_low[nxt],
                         rim_outer[nxt], rim_outer[index]))
        quad("basket", (rim_inner_low[nxt], rim_inner_low[index],
                         rim_inner[index], rim_inner[nxt]))
        quad("basket", (rim_outer[index], rim_outer[nxt],
                         rim_inner[nxt], rim_inner[index]))
        quad("basket", (rim_inner_low[index], rim_inner_low[nxt],
                         rim_outer_low[nxt], rim_outer_low[index]))

    # The reference appears to show a narrow light-colored swing handle inside
    # the mouth. It stays below the rim top so overall bounds remain exact.
    handle_color = (0.91, 0.83, 0.59)
    handle_radius = min(sx, sy) * 0.018
    half_span = min(sx, sy) * 0.28
    handle_center_y = -sy * 0.04
    handle_base_z = sz / 2.0 - rim_h * 1.65
    handle_rise = min(sz * 0.045, sy * 0.04)
    path = []
    for index in range(17):
        t = index / 16.0
        x = -half_span + 2.0 * half_span * t
        z = handle_base_z + handle_rise * math.sin(math.pi * t)
        path.append((x, handle_center_y, z))
    for index, (start, end) in enumerate(zip(path, path[1:])):
        dx, dy, dz = (end[i] - start[i] for i in range(3))
        length = math.sqrt(dx * dx + dy * dy + dz * dz)
        if length == 0.0:
            continue
        # A small octagonal tube section follows the arch without extra APIs.
        tx, ty, tz = dx / length, dy / length, dz / length
        ref = (0.0, 1.0, 0.0) if abs(ty) < 0.9 else (1.0, 0.0, 0.0)
        nx, ny, nz = (ty * ref[2] - tz * ref[1],
                      tz * ref[0] - tx * ref[2],
                      tx * ref[1] - ty * ref[0])
        norm = math.sqrt(nx * nx + ny * ny + nz * nz)
        nx, ny, nz = nx / norm, ny / norm, nz / norm
        bx, by, bz = (ny * tz - nz * ty,
                      nz * tx - nx * tz,
                      nx * ty - ny * tx)
        rings = []
        for point in (start, end):
            ring = []
            for side in range(8):
                angle = 2.0 * math.pi * side / 8.0
                ring.append((point[0] + handle_radius * (math.cos(angle) * nx + math.sin(angle) * bx),
                             point[1] + handle_radius * (math.cos(angle) * ny + math.sin(angle) * by),
                             point[2] + handle_radius * (math.cos(angle) * nz + math.sin(angle) * bz)))
            rings.append(ring)
        for side in range(8):
            nxt = (side + 1) % 8
            quad("handle", (rings[0][side], rings[0][nxt],
                             rings[1][nxt], rings[1][side]))

    for name, data in parts.items():
        mesh_path = f"{base_path}/{name}"
        mesh = UsdGeom.Mesh.Define(stage, mesh_path)
        mesh.CreatePointsAttr([Gf.Vec3f(*point) for point in data["points"]])
        mesh.CreateFaceVertexCountsAttr(data["counts"])
        mesh.CreateFaceVertexIndicesAttr(data["indices"])
        mesh.CreateSubdivisionSchemeAttr(UsdGeom.Tokens.none)
        mesh.CreateDoubleSidedAttr(True)
        mesh.CreateDisplayColorAttr([
            Gf.Vec3f(*(blue if name == "basket" else handle_color))
        ])
