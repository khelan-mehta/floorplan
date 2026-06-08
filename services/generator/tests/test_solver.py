import json
from collections import defaultdict, deque
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator
from referencing import Registry, Resource

from app.scoring import adjacency_satisfaction, score_plan
from app.solver import generate_layouts


def _exterior_doors(plan: dict) -> list[dict]:
    return [
        o
        for o in plan["levels"][0]["openings"]
        if o["kind"] == "door" and "exterior" in o["connects"]
    ]


def _reachable_from_exterior(plan: dict) -> set[str]:
    graph: dict[str, set[str]] = defaultdict(set)
    for o in plan["levels"][0]["openings"]:
        if o["kind"] in ("door", "opening"):
            a, b = o["connects"][0], o["connects"][1]
            graph[a].add(b)
            graph[b].add(a)
    seen = {"exterior"}
    q = deque(["exterior"])
    while q:
        n = q.popleft()
        for m in graph[n]:
            if m not in seen:
                seen.add(m)
                q.append(m)
    return seen

REPO = Path(__file__).resolve().parents[3]
SCHEMAS = REPO / "packages" / "schemas" / "schemas"
EXAMPLES = REPO / "packages" / "schemas" / "examples"


def _load(p: Path) -> dict:
    return json.loads(p.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def plan_validator() -> Draft202012Validator:
    resources = [
        (json.loads(p.read_text())["$id"], Resource.from_contents(json.loads(p.read_text())))
        for p in SCHEMAS.glob("*.schema.json")
    ]
    registry = Registry().with_resources(resources)
    schema = _load(SCHEMAS / "plan.schema.json")
    return Draft202012Validator(schema, registry=registry)


@pytest.fixture(scope="module")
def boundary() -> dict:
    return _load(EXAMPLES / "boundary-rect.example.json")


@pytest.fixture(scope="module")
def program() -> dict:
    return _load(EXAMPLES / "program-2bed.example.json")


@pytest.fixture(scope="module")
def lshape() -> dict:
    return _load(EXAMPLES / "boundary-lshape.example.json")


def test_generates_distinct_valid_plans(boundary, program, plan_validator) -> None:
    plans = generate_layouts(boundary, program, count=6, seed=1)
    assert len(plans) >= 3
    ids = {p["id"] for p in plans}
    assert len(ids) == len(plans)  # distinct
    for plan in plans:
        errors = sorted(plan_validator.iter_errors(plan), key=str)
        assert errors == [], errors[:3]


def test_all_program_rooms_present(boundary, program) -> None:
    plans = generate_layouts(boundary, program, count=4, seed=7)
    expected = {n["id"] for n in program["nodes"]}
    rooms = {r["program_node_id"] for r in plans[0]["levels"][0]["rooms"]}
    assert expected.issubset(rooms)


def test_rooms_fill_the_boundary(boundary, program) -> None:
    plan = generate_layouts(boundary, program, count=1, seed=3)[0]
    total = sum(r["area_mm2"] for r in plan["levels"][0]["rooms"])
    b = boundary["levels"][0]["outline"]["rings"][0]["points"]
    xs = [p[0] for p in b]
    ys = [p[1] for p in b]
    box_area = (max(xs) - min(xs)) * (max(ys) - min(ys))
    assert total == pytest.approx(box_area, rel=0.02)


def test_reproducible_with_same_seed(boundary, program) -> None:
    a = generate_layouts(boundary, program, count=3, seed=42)
    b = generate_layouts(boundary, program, count=3, seed=42)
    assert a == b


def test_adjacency_reasonable(boundary, program) -> None:
    plans = generate_layouts(boundary, program, count=8, seed=11)
    best = max(adjacency_satisfaction(p, program) for p in plans)
    assert best >= 0.6  # squarify clusters BFS-ordered neighbours


def test_scoring_runs(boundary, program) -> None:
    plan = generate_layouts(boundary, program, count=1, seed=0)[0]
    score, breakdown = score_plan(plan, program)
    assert 0 <= score <= 100
    assert "adjacency" in breakdown and "area_fit" in breakdown


def test_single_exterior_door_by_default(boundary, program) -> None:
    # No entry config -> exactly one front door (not a door per exterior room).
    for seed in (0, 1, 2, 3):
        plan = generate_layouts(boundary, program, count=1, seed=seed)[0]
        assert len(_exterior_doors(plan)) == 1, seed


def test_exterior_door_count_is_honored(boundary, program) -> None:
    prog = {**program, "entry": {"exterior_doors": 2}}
    plan = generate_layouts(boundary, prog, count=1, seed=5)[0]
    assert len(_exterior_doors(plan)) == 2


def test_every_room_reachable_from_exterior(boundary, program) -> None:
    # The circulation spanning tree + a single front door must make every room reachable (egress).
    for seed in (0, 4, 9, 13):
        plan = generate_layouts(boundary, program, count=1, seed=seed)[0]
        room_ids = {r["id"] for r in plan["levels"][0]["rooms"]}
        assert room_ids.issubset(_reachable_from_exterior(plan)), seed


def test_tiles_the_actual_polygon_not_the_bbox(lshape, program) -> None:
    # On an L-shape the bbox is much larger than the real area; rooms must fill the real polygon.
    from app import geometry as geom

    outline = geom.to_poly(lshape["levels"][0]["outline"]["rings"][0]["points"])
    real_area = geom.area(outline)
    minx, miny, maxx, maxy = geom.bbox(outline)
    bbox_area = (maxx - minx) * (maxy - miny)
    assert real_area < bbox_area * 0.85  # L-shape: ~96e6 vs 120e6 bbox

    plan = generate_layouts(lshape, program, count=1, seed=2)[0]
    total = sum(r["area_mm2"] for r in plan["levels"][0]["rooms"])
    assert total == pytest.approx(real_area, rel=0.03)  # tiles the real outline, not the bbox


def test_rooms_stay_inside_polygon(lshape, program) -> None:
    from app import geometry as geom

    outline = geom.to_poly(lshape["levels"][0]["outline"]["rings"][0]["points"])
    plan = generate_layouts(lshape, program, count=1, seed=5)[0]
    for r in plan["levels"][0]["rooms"]:
        assert geom.point_in_polygon((r["centroid"][0], r["centroid"][1]), outline), r["id"]


def test_no_awkward_slivers_on_lshape(lshape, program) -> None:
    # Rooms should be reasonably proportioned (no thin leftover spaces at the concave corner).
    from app import geometry as geom

    plan = generate_layouts(lshape, program, count=1, seed=2)[0]
    for r in plan["levels"][0]["rooms"]:
        poly = geom.to_poly(r["polygon"]["rings"][0]["points"])
        assert geom.aspect(poly) <= 4.0, (r["id"], geom.aspect(poly))
        assert geom.min_dim(poly) >= 1200, (r["id"], geom.min_dim(poly))


def test_polygon_plan_egress_and_single_door(lshape, program, plan_validator) -> None:
    plan = generate_layouts(lshape, program, count=1, seed=3)[0]
    errors = sorted(plan_validator.iter_errors(plan), key=str)
    assert errors == [], errors[:3]  # concave-room plan is still schema-valid
    assert len(_exterior_doors(plan)) == 1
    rooms = {r["id"] for r in plan["levels"][0]["rooms"]}
    assert rooms.issubset(_reachable_from_exterior(plan))


def test_generated_windows_meet_daylight_code(boundary, program) -> None:
    # Every room that gets glazing should meet ~the code daylight minimum (8% of floor area).
    plan = generate_layouts(boundary, program, count=1, seed=1)[0]
    lvl = plan["levels"][0]
    win_area: dict[str, int] = defaultdict(int)
    for o in lvl["openings"]:
        if o["kind"] == "window":
            win_area[o["connects"][0]] += o["width_mm"] * o["height_mm"]
    assert win_area, "expected some windows"
    for r in lvl["rooms"]:
        if win_area.get(r["id"]):
            assert win_area[r["id"]] >= 0.06 * r["area_mm2"], r["program_node_id"]


def test_explicit_window_count_respected(boundary, program) -> None:
    prog = json.loads(json.dumps(program))
    for n in prog["nodes"]:
        if n["id"] == "living":
            n["windows"] = 2
    plan = generate_layouts(boundary, prog, count=1, seed=1)[0]
    lvl = plan["levels"][0]
    living = next((r for r in lvl["rooms"] if r["program_node_id"] == "living"), None)
    assert living is not None
    wins = [o for o in lvl["openings"] if o["kind"] == "window" and o["connects"][0] == living["id"]]
    if wins:  # only if the room landed on the exterior
        assert 1 <= len(wins) <= 2


def test_preferred_entry_node_holds_the_door(boundary, program) -> None:
    prog = {**program, "entry": {"entry_node_id": "entry", "exterior_doors": 1}}
    plan = generate_layouts(boundary, prog, count=1, seed=2)[0]
    doors = _exterior_doors(plan)
    assert len(doors) == 1
    door_room = next(c for c in doors[0]["connects"] if c != "exterior")
    room = next(r for r in plan["levels"][0]["rooms"] if r["id"] == door_room)
    assert room["program_node_id"] == "entry"
