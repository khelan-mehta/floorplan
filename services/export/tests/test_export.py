import io
import json
from pathlib import Path

import ezdxf
import ifcopenshell
import pytest

from app.dxf_export import build_dxf, room_schedule_csv
from app.ifc_export import build_ifc_bytes, ifc_stats

EXAMPLES = Path(__file__).resolve().parents[3] / "packages" / "schemas" / "examples"


@pytest.fixture(scope="module")
def plan() -> dict:
    return json.loads((EXAMPLES / "plan-2bed.example.json").read_text(encoding="utf-8"))


def test_dxf_has_layers_and_entities(plan) -> None:
    dxf_text = build_dxf(plan)
    doc = ezdxf.read(io.StringIO(dxf_text))
    layers = {layer.dxf.name for layer in doc.layers}
    for expected in ["A-WALL", "A-DOOR", "A-GLAZ", "A-AREA", "A-ANNO-TEXT"]:
        assert expected in layers

    msp = doc.modelspace()
    walls = msp.query('LINE[layer=="A-WALL"]')
    rooms = msp.query('LWPOLYLINE[layer=="A-AREA"]')
    assert len(walls) == len(plan["levels"][0]["walls"])
    assert len(rooms) == len(plan["levels"][0]["rooms"])


def test_dxf_real_world_scale(plan) -> None:
    # the south wall spans 0..10000 mm; confirm a 10 m line exists
    doc = ezdxf.read(io.StringIO(build_dxf(plan)))
    lines = doc.modelspace().query('LINE[layer=="A-WALL"]')
    lengths = [round((line.dxf.end - line.dxf.start).magnitude) for line in lines]
    assert 10000 in lengths


def test_schedule_csv(plan) -> None:
    csv = room_schedule_csv(plan)
    assert csv.splitlines()[0] == "room_id,type,area_m2"
    assert "room-living,living,40.00" in csv


def test_ifc_spatial_structure(plan, tmp_path) -> None:
    data = build_ifc_bytes(plan)
    path = tmp_path / "out.ifc"
    path.write_bytes(data)
    model = ifcopenshell.open(str(path))
    assert len(model.by_type("IfcProject")) == 1
    assert len(model.by_type("IfcBuildingStorey")) == len(plan["levels"])
    assert len(model.by_type("IfcSpace")) == sum(len(lvl["rooms"]) for lvl in plan["levels"])
    assert len(model.by_type("IfcWall")) == sum(len(lvl["walls"]) for lvl in plan["levels"])


def test_ifc_native_categories(plan) -> None:
    stats = ifc_stats(plan)
    level = plan["levels"][0]
    assert stats["spaces"] == 2
    assert stats["storeys"] == 1
    assert stats["walls"] == len(level["walls"])
    assert stats["doors"] == sum(1 for o in level["openings"] if o["kind"] == "door")
    assert stats["windows"] == sum(1 for o in level["openings"] if o["kind"] == "window")
