#!/usr/bin/env python3
"""Build reproducible bread GLBs from the CC0 Innerscene bread loaf source.

The loaf is retained unchanged. The thin slice is an extrusion of the loaf's
measured center cross-section, with separately UV-mapped crumb faces and crust
perimeter. All coordinates remain glTF Y-up; output measurements are recorded
in provenance.json after reloading the exported GLBs.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import shutil
from pathlib import Path

import numpy as np
import trimesh
from PIL import Image
from trimesh.visual.material import PBRMaterial


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = Path("/tmp/dreamzero-asset-review.eRB5Fk")
OUT = ROOT / "assets/third_party/bread_v7"
SOURCE_URL = "https://www.innerscene.com/tools/library/3d-parts/bread-loaf-2d5927d5"
SOURCE_LICENSE = "CC0 1.0 / public domain dedication, as stated on official listing"
SLICE_THICKNESS_M = 0.014


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def mesh_from_polygon(points: np.ndarray, faces: np.ndarray, uv: np.ndarray,
                      image_path: Path, name: str) -> trimesh.Trimesh:
    material = PBRMaterial(
        name=name,
        baseColorFactor=[255, 255, 255, 255],
        baseColorTexture=Image.open(image_path).convert("RGB"),
        metallicFactor=0.0,
        roughnessFactor=0.94,
    )
    mesh = trimesh.Trimesh(
        vertices=points,
        faces=faces,
        process=False,
        visual=trimesh.visual.TextureVisuals(uv=uv, material=material),
        metadata={"name": name},
    )
    mesh.fix_normals()
    return mesh


def signed_area(points: np.ndarray) -> float:
    return float(np.sum(points[:, 0] * np.roll(points[:, 1], -1)
                        - np.roll(points[:, 0], -1) * points[:, 1]) * 0.5)


def point_in_triangle(p: np.ndarray, a: np.ndarray, b: np.ndarray,
                      c: np.ndarray, eps: float = 1e-12) -> bool:
    cross = lambda u, v: u[0] * v[1] - u[1] * v[0]
    return (cross(b - a, p - a) >= -eps
            and cross(c - b, p - b) >= -eps
            and cross(a - c, p - c) >= -eps)


def triangulate_simple_polygon(points: np.ndarray) -> np.ndarray:
    """Ear-clip a simple counter-clockwise polygon without Shapely/triangle."""
    if signed_area(points) < 0:
        points[:] = points[::-1]
    remaining = list(range(len(points)))
    triangles: list[tuple[int, int, int]] = []
    guard = 0
    while len(remaining) > 3:
        ear_found = False
        for cursor, current in enumerate(remaining):
            previous = remaining[cursor - 1]
            following = remaining[(cursor + 1) % len(remaining)]
            a, b, c = points[[previous, current, following]]
            cross = np.cross(b - a, c - b)
            if cross <= 1e-12:
                continue
            if any(
                point_in_triangle(points[index], a, b, c)
                for index in remaining
                if index not in (previous, current, following)
            ):
                continue
            triangles.append((previous, current, following))
            del remaining[cursor]
            ear_found = True
            break
        guard += 1
        if not ear_found or guard > len(points) ** 2:
            raise ValueError("Unable to triangulate measured bread cross-section")
    triangles.append(tuple(remaining))
    return np.asarray(triangles, dtype=np.int64)


def cross_section_outline(source_glb: Path) -> np.ndarray:
    scene = trimesh.load(source_glb, force="scene")
    body = scene.geometry.get("Rounded scored bread crust")
    if body is None:
        candidates = [mesh for mesh in scene.geometry.values() if isinstance(mesh, trimesh.Trimesh)]
        if not candidates:
            raise ValueError("Source GLB has no triangular bread body")
        body = max(candidates, key=lambda mesh: mesh.area)
    section = body.section(plane_origin=[0.0, 0.0, 0.0], plane_normal=[1.0, 0.0, 0.0])
    if section is None:
        raise ValueError("Could not section the source loaf at its center")
    loops = [path for path in section.discrete if len(path) >= 4
             and np.linalg.norm(path[0] - path[-1]) < 1e-6]
    if len(loops) != 1:
        raise ValueError(f"Expected one closed center section; found {len(loops)}")
    # Source cross-section is (source Z, source Y), mapped to slice (X, Y).
    outline = np.column_stack((loops[0][:-1, 2], loops[0][:-1, 1]))
    # Remove adjacent duplicate points and near-collinear tiny edges.
    keep = np.ones(len(outline), dtype=bool)
    for i in range(len(outline)):
        prev = outline[(i - 1) % len(outline)]
        curr = outline[i]
        nxt = outline[(i + 1) % len(outline)]
        if np.linalg.norm(curr - prev) < 1e-7:
            keep[i] = False
        elif abs(np.cross(curr - prev, nxt - curr)) < 1e-10:
            keep[i] = False
    outline = outline[keep]
    if signed_area(outline) < 0:
        outline = outline[::-1].copy()
    # Put the lower edge on Y=0, retain original width and height.
    outline[:, 1] -= outline[:, 1].min()
    return outline


def build_slice(source_glb: Path, crumb_map: Path, crust_map: Path, out_glb: Path) -> dict:
    outline = cross_section_outline(source_glb)
    triangulation = triangulate_simple_polygon(outline.copy())
    n = len(outline)
    half = SLICE_THICKNESS_M / 2.0
    min_xy = outline.min(axis=0)
    extent_xy = outline.max(axis=0) - min_xy
    uv_face = (outline - min_xy) / extent_xy
    front_vertices = np.column_stack((outline, np.full(n, half)))
    back_vertices = np.column_stack((outline, np.full(n, -half)))

    front = mesh_from_polygon(
        front_vertices, triangulation, uv_face, crumb_map, "Porous crumb, front cut face"
    )
    back = mesh_from_polygon(
        back_vertices, triangulation[:, ::-1], uv_face, crumb_map, "Porous crumb, back cut face"
    )

    # Side ring: u follows the measured perimeter; v runs across the slice.
    edge_lengths = np.linalg.norm(np.roll(outline, -1, axis=0) - outline, axis=1)
    perimeter_u = np.concatenate(([0.0], np.cumsum(edge_lengths))) / edge_lengths.sum()
    # Duplicate the seam vertex at u=1 so the final side edge does not
    # interpolate across the entire crust texture back to u=0.
    side_outline = np.vstack((outline, outline[0]))
    side_front = np.column_stack((side_outline, np.full(n + 1, half)))
    side_back = np.column_stack((side_outline, np.full(n + 1, -half)))
    side_vertices = np.vstack((side_front, side_back))
    side_uv = np.vstack((np.column_stack((perimeter_u, np.ones(n + 1))),
                         np.column_stack((perimeter_u, np.zeros(n + 1)))))
    side_faces = []
    for i in range(n):
        j = (i + 1) % n
        side_faces.extend(((i, n + 1 + j, j), (i, n + 1 + i, n + 1 + j)))
    side = mesh_from_polygon(
        side_vertices, np.asarray(side_faces), side_uv, crust_map, "Golden crust around slice edge"
    )

    result = trimesh.Scene()
    result.add_geometry(front, node_name="crumb_front")
    result.add_geometry(back, node_name="crumb_back")
    result.add_geometry(side, node_name="crust_edge")
    out_glb.parent.mkdir(parents=True, exist_ok=True)
    result.export(out_glb, file_type="glb")
    return {
        "cross_section_vertices": int(n),
        "slice_thickness_m": SLICE_THICKNESS_M,
        "outline_bounds_m_xyz": [
            [float(outline[:, 0].min()), float(outline[:, 1].min()), -half],
            [float(outline[:, 0].max()), float(outline[:, 1].max()), half],
        ],
    }


def glb_report(path: Path) -> dict:
    scene = trimesh.load(path, force="scene")
    bounds = np.asarray(scene.bounds, dtype=float)
    meshes = [g for g in scene.geometry.values() if isinstance(g, trimesh.Trimesh)]
    mesh_checks = []
    for mesh in meshes:
        uv = getattr(mesh.visual, "uv", None)
        material = getattr(mesh.visual, "material", None)
        texture = getattr(material, "baseColorTexture", None)
        mesh_checks.append({
            "name": mesh.metadata.get("name", ""),
            "vertex_count": len(mesh.vertices),
            "triangle_count": len(mesh.faces),
            "uv_present_and_finite": bool(
                uv is not None and uv.shape == (len(mesh.vertices), 2)
                and np.isfinite(uv).all()
            ),
            "normals_finite_and_unit": bool(
                np.isfinite(mesh.vertex_normals).all()
                and np.allclose(np.linalg.norm(mesh.face_normals, axis=1), 1.0, atol=1e-5)
            ),
            "base_color_texture_size_px": list(texture.size) if texture is not None else None,
            "watertight_component": bool(mesh.is_watertight),
        })
    # Material regions are separate glTF primitives. Check that their shared
    # geometric boundaries form a closed, consistently wound combined shell.
    vertices: list[np.ndarray] = []
    faces: list[np.ndarray] = []
    offset = 0
    for node in scene.graph.nodes_geometry:
        transform, geometry_name = scene.graph.get(node)
        mesh = scene.geometry[geometry_name]
        vertices.append(trimesh.transform_points(mesh.vertices, transform))
        faces.append(mesh.faces + offset)
        offset += len(mesh.vertices)
    assembled = None
    if vertices:
        all_vertices = np.vstack(vertices)
        all_faces = np.vstack(faces)
        welded_vertices, inverse = np.unique(
            np.round(all_vertices, decimals=8), axis=0, return_inverse=True
        )
        assembled = trimesh.Trimesh(
            vertices=welded_vertices, faces=inverse[all_faces], process=False
        )
    return {
        "path": str(path.relative_to(ROOT)),
        "sha256": sha256(path),
        "bytes": path.stat().st_size,
        "axis_convention": "Y-up; source loaf length along X, slice width X / height Y / thickness Z",
        "bounds_m": bounds.tolist(),
        "extents_m_xyz": (bounds[1] - bounds[0]).tolist(),
        "mesh_count": len(meshes),
        "triangle_count": int(sum(len(mesh.faces) for mesh in meshes)),
        "assembled_shell_watertight": bool(assembled.is_watertight) if assembled else False,
        "assembled_shell_winding_consistent": bool(assembled.is_winding_consistent) if assembled else False,
        "components": mesh_checks,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-dir", type=Path,
                        help="Directory containing bread-loaf.glb and both albedo PNGs")
    args = parser.parse_args()
    packaged_sources = OUT / "source"
    packaged_names = ("bread-loaf.glb", "bread-loaf-albedo.png", "crumb-albedo.png")
    if args.source_dir is not None:
        source_dir = args.source_dir.resolve()
    elif all((packaged_sources / name).is_file() for name in packaged_names):
        source_dir = packaged_sources.resolve()
    else:
        source_dir = DEFAULT_SOURCE.resolve()
    inputs = {
        "bread-loaf.glb": source_dir / "bread-loaf.glb",
        "bread-loaf-albedo.png": source_dir / "bread-loaf-albedo.png",
        "crumb-albedo.png": source_dir / "crumb-albedo.png",
    }
    missing = [str(path) for path in inputs.values() if not path.is_file()]
    if missing:
        raise SystemExit("Missing source file(s): " + ", ".join(missing))

    OUT.mkdir(parents=True, exist_ok=True)
    packaged_sources.mkdir(exist_ok=True)
    for name, path in inputs.items():
        destination = packaged_sources / name
        if path.resolve() != destination.resolve():
            shutil.copy2(path, destination)

    loaf_out = OUT / "bread-loaf-v7.glb"
    shutil.copy2(inputs["bread-loaf.glb"], loaf_out)
    slice_info = build_slice(
        inputs["bread-loaf.glb"], inputs["crumb-albedo.png"],
        inputs["bread-loaf-albedo.png"], OUT / "bread-slice-v7.glb",
    )
    reports = {
        "whole_loaf": glb_report(loaf_out),
        "thin_slice": glb_report(OUT / "bread-slice-v7.glb"),
    }
    provenance = {
        "asset_set": "Appendix G bread assets v7",
        "source": {
            "url": SOURCE_URL,
            "listing_title": "Bread loaf",
            "license": SOURCE_LICENSE,
            "official_listing_verified_utc": "2026-10-14",
            "listing_dimensions_m_xyz": [0.240, 0.10959, 0.114],
            "source_files_sha256": {name: sha256(path) for name, path in inputs.items()},
            "packaged_source_files": [f"source/{name}" for name in inputs],
        },
        "generation": {
            "script": "scripts/generate_bread_assets_v7.py",
            "method": "The original GLB is retained unchanged. A center section through the source crust mesh is extracted as a closed contour and extruded to 14 mm. The contour's source Z/Y coordinates become slice X/Y. Both broad faces use the supplied porous crumb albedo; the perimeter uses the supplied crust albedo. UVs are generated for each region.",
            "slice": slice_info,
            "dependencies": {"trimesh": trimesh.__version__, "numpy": np.__version__},
            "suggested_physical_sizes_m": {
                "whole_loaf_xyz": [0.240, 0.10959, 0.114],
                "slice_width_x_height_y_thickness_z": [0.114, 0.109, SLICE_THICKNESS_M],
            },
        },
        "outputs": reports,
        "orientation_note": "Both GLBs are Y-up as required by glTF. The existing parent importer may rotate Y-up to scene Z-up. The loaf long axis is X. The slice is upright with width X, height Y, thickness Z.",
    }
    (OUT / "provenance.json").write_text(json.dumps(provenance, indent=2) + "\n")
    (OUT / "README.md").write_text(
        "# Appendix G bread assets v7\n\n"
        "Two photographic-textured bread assets derived from the official Innerscene "
        "Bread loaf CC0 model. The original GLB is retained as the whole loaf; the "
        "slice is a 14 mm extrusion of its measured center cross-section. Its broad "
        "faces use the supplied porous crumb map and its perimeter uses the loaf crust "
        "map.\n\n"
        "- `bread-loaf-v7.glb` — whole loaf for U03.\n"
        "- `bread-slice-v7.glb` — upright thin slice for S18, U13, U15, and U18.\n"
        "- `source/` — exact input GLB and the two supplied albedo maps.\n"
        "- `provenance.json` — source URL/license, source/output SHA-256, generation "
        "method, actual exported bounds, mesh/UV checks, and suggested physical sizes.\n\n"
        f"Source: [{SOURCE_URL}]({SOURCE_URL}) — {SOURCE_LICENSE}. All models are "
        "Y-up; the parent importer performs any required Y-up to Z-up conversion.\n"
    )
    print(json.dumps({"outputs": reports, "slice": slice_info}, indent=2))


if __name__ == "__main__":
    main()
