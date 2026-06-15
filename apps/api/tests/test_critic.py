from app import critic

PROGRAM = {
    "schema_version": 1,
    "id": "prog-1",
    "source": "graph",
    "nodes": [
        {"id": "kitchen", "type": "kitchen", "label": "Kitchen", "area_target_mm2": 10_000_000},
        {"id": "laundry", "type": "laundry", "label": "Laundry", "area_target_mm2": 4_000_000},
        {"id": "bedroom", "type": "bedroom", "label": "Bedroom", "area_target_mm2": 12_000_000},
    ],
    "edges": [
        {"a": "kitchen", "b": "laundry", "relation": "connected_door", "weight": 30},
    ],
}


def test_deterministic_bigger_request() -> None:
    adjustments = critic.propose_adjustments("the kitchen is too small", PROGRAM)
    assert {"id": "kitchen", "area_delta_pct": 20} in adjustments["node_adjustments"]
    assert adjustments["notes"]


def test_deterministic_smaller_request() -> None:
    adjustments = critic.propose_adjustments("make the bedroom smaller", PROGRAM)
    assert {"id": "bedroom", "area_delta_pct": -20} in adjustments["node_adjustments"]


def test_deterministic_window_request() -> None:
    adjustments = critic.propose_adjustments("the bedroom needs more natural light", PROGRAM)
    assert {"id": "bedroom", "requires_window": True} in adjustments["node_adjustments"]


def test_deterministic_adjacency_request() -> None:
    adjustments = critic.propose_adjustments("the kitchen should be near the bedroom", PROGRAM)
    edge = adjustments["edge_adjustments"][0]
    assert {edge["a"], edge["b"]} == {"kitchen", "bedroom"}
    assert edge["relation"] == "adjacent"
    assert edge["weight"] == 90


def test_apply_adjustments_scales_area_and_upserts_edge() -> None:
    adjustments = {
        "node_adjustments": [{"id": "kitchen", "area_delta_pct": 20, "requires_window": True}],
        "edge_adjustments": [{"a": "kitchen", "b": "bedroom", "relation": "adjacent", "weight": 90}],
        "notes": "test",
    }
    new_program = critic.apply_adjustments(PROGRAM, adjustments)

    kitchen = next(n for n in new_program["nodes"] if n["id"] == "kitchen")
    assert kitchen["area_target_mm2"] == 12_000_000
    assert kitchen["requires_window"] is True

    new_edge = next(e for e in new_program["edges"] if {e["a"], e["b"]} == {"kitchen", "bedroom"})
    assert new_edge["relation"] == "adjacent"
    assert new_edge["weight"] == 90

    # existing edge updated in place, not duplicated
    assert len(new_program["edges"]) == 2

    # original program untouched
    assert PROGRAM["nodes"][0]["area_target_mm2"] == 10_000_000
    assert "requires_window" not in PROGRAM["nodes"][0]
    assert len(PROGRAM["edges"]) == 1


def test_apply_adjustments_updates_existing_edge() -> None:
    adjustments = {
        "node_adjustments": [],
        "edge_adjustments": [{"a": "kitchen", "b": "laundry", "weight": 80}],
        "notes": "test",
    }
    new_program = critic.apply_adjustments(PROGRAM, adjustments)
    edge = next(e for e in new_program["edges"] if {e["a"], e["b"]} == {"kitchen", "laundry"})
    assert edge["weight"] == 80
    assert edge["relation"] == "connected_door"
    assert len(new_program["edges"]) == 1


def test_no_openai_key_falls_back_to_deterministic() -> None:
    assert critic.settings.openai_api_key == ""
    adjustments = critic.propose_adjustments("the kitchen is too small", PROGRAM)
    assert adjustments["node_adjustments"]


def test_deterministic_partial_name_adjacency_request() -> None:
    program = {
        **PROGRAM,
        "nodes": [
            *PROGRAM["nodes"],
            {"id": "corridor", "type": "corridor", "label": "Corridor", "area_target_mm2": 3_000_000},
            {"id": "living", "type": "living", "label": "Living Room", "area_target_mm2": 18_000_000},
        ],
    }
    adjustments = critic.propose_adjustments("move the corridor next to the living", program)
    edge = adjustments["edge_adjustments"][0]
    assert {edge["a"], edge["b"]} == {"corridor", "living"}
    assert edge["relation"] == "adjacent"
    assert edge["weight"] == 90
