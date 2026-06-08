"""Export a Plan to DXF (AIA-style layers). DWG conversion uses the ODA File Converter add-on
(documented; requires the ODA binary, wired in CI/Phase 18). Units are millimetres.
"""

from __future__ import annotations

import io
from typing import Any

import ezdxf

LAYERS = {
    "A-WALL": 7,  # white
    "A-DOOR": 3,  # green
    "A-GLAZ": 4,  # cyan
    "A-AREA": 5,  # blue
    "A-ANNO-TEXT": 2,  # yellow
}


def _wall_point(a: list[int], b: list[int], offset: int) -> tuple[float, float]:
    length = max(1.0, ((b[0] - a[0]) ** 2 + (b[1] - a[1]) ** 2) ** 0.5)
    t = min(offset / length, 1.0)
    return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)


def build_dxf(plan: dict[str, Any]) -> str:
    doc = ezdxf.new("R2018", setup=True)
    doc.units = ezdxf.units.MM
    for name, color in LAYERS.items():
        doc.layers.add(name, color=color)
    msp = doc.modelspace()

    level = plan["levels"][0] if plan.get("levels") else {"rooms": [], "walls": [], "openings": []}

    walls_by_id = {w["id"]: w for w in level.get("walls", [])}

    for room in level.get("rooms", []):
        pts = [(p[0], p[1]) for p in room["polygon"]["rings"][0]["points"]]
        msp.add_lwpolyline(pts, close=True, dxfattribs={"layer": "A-AREA"})
        area_m2 = room["area_mm2"] / 1_000_000
        cx, cy = room["centroid"]
        mtext = msp.add_mtext(f"{room['type']}\\P{area_m2:.1f} m2", dxfattribs={"layer": "A-ANNO-TEXT"})
        mtext.set_location((cx, cy))
        mtext.dxf.char_height = 200

    for wall in level.get("walls", []):
        msp.add_line(
            tuple(wall["a"]), tuple(wall["b"]), dxfattribs={"layer": "A-WALL"}
        )

    for op in level.get("openings", []):
        wall = walls_by_id.get(op["wall_id"])
        if not wall:
            continue
        x, y = _wall_point(wall["a"], wall["b"], op["offset_mm"])
        layer = "A-DOOR" if op["kind"] == "door" else "A-GLAZ"
        msp.add_circle((x, y), radius=op["width_mm"] / 2, dxfattribs={"layer": layer})

    stream = io.StringIO()
    doc.write(stream)
    return stream.getvalue()


def build_dxf_bytes(plan: dict[str, Any]) -> bytes:
    return build_dxf(plan).encode("utf-8")


def room_schedule_csv(plan: dict[str, Any]) -> str:
    rows = ["room_id,type,area_m2"]
    for level in plan.get("levels", []):
        for room in level["rooms"]:
            rows.append(f"{room['id']},{room['type']},{room['area_mm2'] / 1_000_000:.2f}")
    return "\n".join(rows) + "\n"
