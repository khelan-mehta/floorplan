from app.versioning import diff_docs, inputs_hash, next_plan_doc


def test_inputs_hash_is_deterministic_and_order_independent() -> None:
    a = inputs_hash("generate", "p1", {"count": 4, "seed": 1})
    b = inputs_hash("generate", "p1", {"seed": 1, "count": 4})
    assert a == b
    assert a != inputs_hash("generate", "p1", {"count": 6, "seed": 1})


def test_next_plan_doc_lineage_and_immutability() -> None:
    parent = {"id": "parent-1", "source": "generated", "score": 10, "levels": []}
    child = next_plan_doc(parent, new_id="child-1", patch={"score": 20}, source="edited")
    assert child["id"] == "child-1"
    assert child["parent_plan_id"] == "parent-1"
    assert child["source"] == "edited"
    assert child["score"] == 20
    # parent is untouched
    assert parent["id"] == "parent-1"
    assert parent["score"] == 10


def test_diff_docs() -> None:
    a = {"id": "x", "a": 1, "b": {"c": 2}, "gone": True}
    b = {"id": "y", "a": 9, "b": {"c": 2}, "new": 5}
    d = diff_docs(a, b)
    assert d["changed"]["/a"] == {"from": 1, "to": 9}
    assert d["removed"] == {"/gone": True}
    assert d["added"] == {"/new": 5}
    # volatile /id is ignored
    assert "/id" not in d["changed"]
