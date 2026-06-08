"""Solidify a Plan into a 3D scene and export GLB.

Phase 11 core: floor slabs (extruded room polygons) + wall boxes, each tagged with its element id
so downstream IFC export (Phase 15) can map solids -> IfcSlab/IfcWall. Boolean-cut openings,
parametric door/window solids, stairs and roofs are follow-ups. Units: model is metres (mm * 0.001).
"""

from __future__ import annotations

import math
from typing import Any

import trimesh
from shapely.geometry import Polygon as ShapelyPolygon

MM_TO_M = 0.001
SLAB_THICKNESS_M = 0.05


def _slab(points: list[list[int]], elevation_m: float) -> trimesh.Trimesh | None:
    ring = [(p[0] * MM_TO_M, p[1] * MM_TO_M) for p in points]
    poly = ShapelyPolygon(ring)
    if not poly.is_valid or poly.area <= 0:
        return None
    mesh = trimesh.creation.extrude_polygon(poly, height=SLAB_THICKNESS_M)
    mesh.apply_translation([0, 0, elevation_m])
    return mesh


def _wall_box(a: list[int], b: list[int], thickness_mm: int, height_mm: int, base_m: float) -> trimesh.Trimesh:
    ax, ay = a[0] * MM_TO_M, a[1] * MM_TO_M
    bx, by = b[0] * MM_TO_M, b[1] * MM_TO_M
    length = math.hypot(bx - ax, by - ay)
    height = height_mm * MM_TO_M
    thickness = thickness_mm * MM_TO_M
    box = trimesh.creation.box(extents=[max(length, 1e-3), thickness, height])
    angle = math.atan2(by - ay, bx - ax)
    transform = trimesh.transformations.rotation_matrix(angle, [0, 0, 1])
    transform[0][3] = (ax + bx) / 2
    transform[1][3] = (ay + by) / 2
    transform[2][3] = base_m + height / 2
    box.apply_transform(transform)
    return box


def build_scene(plan: dict[str, Any]) -> trimesh.Scene:
    scene = trimesh.Scene()
    for level in plan.get("levels", []):
        base_m = 0.0  # multi-level stacking by elevation is a follow-up (needs boundary levels)
        for room in level.get("rooms", []):
            slab = _slab(room["polygon"]["rings"][0]["points"], base_m)
            if slab is not None:
                scene.add_geometry(slab, node_name=f"slab:{room['id']}", geom_name=f"slab:{room['id']}")
        for wall in level.get("walls", []):
            box = _wall_box(wall["a"], wall["b"], wall["thickness_mm"], wall["height_mm"], base_m)
            scene.add_geometry(box, node_name=f"wall:{wall['id']}", geom_name=f"wall:{wall['id']}")
    return scene


def solidify_to_glb(plan: dict[str, Any]) -> bytes:
    scene = build_scene(plan)
    if not scene.geometry:
        # empty scene: emit a tiny placeholder so exporters never choke
        scene.add_geometry(trimesh.creation.box(extents=[0.01, 0.01, 0.01]))
    glb = scene.export(file_type="glb")
    return glb if isinstance(glb, bytes) else bytes(glb)


def scene_stats(plan: dict[str, Any]) -> dict[str, int]:
    scene = build_scene(plan)
    slabs = sum(1 for name in scene.geometry if name.startswith("slab:"))
    walls = sum(1 for name in scene.geometry if name.startswith("wall:"))
    verts = int(sum(len(g.vertices) for g in scene.geometry.values()))
    return {"nodes": len(scene.geometry), "slabs": slabs, "walls": walls, "vertices": verts}
