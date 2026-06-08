"""Recursive area-bisection partition of an arbitrary simple polygon.

Splits the polygon into one sub-polygon per weight, areas proportional to the weights, by repeatedly
cutting the *actual* polygon (not its bounding box) with an axis-aligned line. Because each cut is a
half-plane clip, every piece stays inside the original outline — so concave / arc-approximated shapes
are supported.

Quality refinements (so the result reads like a real floor plan, not awkward slivers):
- the cut **axis** is chosen to minimise the worse child's aspect ratio (no thin strips);
- the cut is **snapped to the building's own lines** (outline-vertex coordinates) when close, so
  partitions align to notches (e.g. the inner corner of an L) instead of cutting across them;
- a **minimum-dimension** penalty steers cuts away from leaving unusably narrow spaces.
"""

from __future__ import annotations

from .geometry import Poly, area, aspect, bbox, clip_axis, cut_for_area, min_dim

SNAP_TOL = 1200.0  # mm: snap a cut to an outline line within this distance
MIN_ROOM_DIM = 2000.0  # mm: discourage rooms narrower than this


def partition_polygon(
    weights: list[float],
    poly: Poly,
    snaps_x: list[float] | None = None,
    snaps_y: list[float] | None = None,
) -> list[Poly]:
    """Return one sub-polygon per weight (same order), tiling `poly`."""
    out: list[Poly] = [[] for _ in weights]
    sx = sorted(set(snaps_x or []))
    sy = sorted(set(snaps_y or []))
    _recurse(list(range(len(weights))), [max(w, 1e-6) for w in weights], poly, out, sx, sy)
    return out


def _nearest_snap(cut: float, snaps: list[float], lo: float, hi: float) -> float | None:
    best: float | None = None
    bestd = SNAP_TOL
    for s in snaps:
        if s <= lo + 1 or s >= hi - 1:  # must keep both sides non-degenerate
            continue
        d = abs(s - cut)
        if d < bestd:
            bestd, best = d, s
    return best


def _evaluate(poly: Poly, axis: int, cut: float) -> tuple[float, Poly, Poly]:
    low = clip_axis(poly, axis, cut, True)
    high = clip_axis(poly, axis, cut, False)
    if area(low) <= 1.0 or area(high) <= 1.0:
        return float("inf"), low, high
    cost = max(aspect(low), aspect(high))
    if min(min_dim(low), min_dim(high)) < MIN_ROOM_DIM:
        cost += 8.0  # heavy penalty for narrow leftovers
    return cost, low, high


def _recurse(
    idxs: list[int],
    weights: list[float],
    poly: Poly,
    out: list[Poly],
    snaps_x: list[float],
    snaps_y: list[float],
) -> None:
    if len(idxs) == 1:
        out[idxs[0]] = poly
        return
    if area(poly) <= 0:
        for i in idxs:
            out[i] = poly
        return

    total = sum(weights[i] for i in idxs)
    half = total / 2.0
    k, best_k, cum = 1, float("inf"), 0.0
    for c in range(1, len(idxs)):
        cum += weights[idxs[c - 1]]
        if abs(cum - half) < best_k:
            best_k, k = abs(cum - half), c
    left, right = idxs[:k], idxs[k:]
    frac = sum(weights[i] for i in left) / total

    minx, miny, maxx, maxy = bbox(poly)
    # Try both axes, both the area-exact cut and a snapped-to-outline cut; keep the lowest cost.
    best: tuple[float, int, Poly, Poly] | None = None
    for axis in (0, 1):
        exact = cut_for_area(poly, axis, frac)
        snaps = snaps_x if axis == 0 else snaps_y
        lo, hi = (minx, maxx) if axis == 0 else (miny, maxy)
        candidates = [exact]
        snapped = _nearest_snap(exact, snaps, lo, hi)
        if snapped is not None:
            candidates.append(snapped)
        for cut in candidates:
            cost, low, high = _evaluate(poly, axis, cut)
            # Prefer a snapped cut slightly (aligns to the building) when costs are close.
            if cut == snapped:
                cost -= 0.25
            if best is None or cost < best[0]:
                best = (cost, axis, low, high)

    assert best is not None
    _, _axis, low_poly, high_poly = best
    _recurse(left, weights, low_poly, out, snaps_x, snaps_y)
    _recurse(right, weights, high_poly, out, snaps_x, snaps_y)
