"""Rectangle partitioning via a squarified treemap (Bruls et al.).

Given target areas and a container rectangle, produce sub-rectangles whose areas are proportional
to the targets while keeping aspect ratios close to 1. This is the deterministic "slice-and-dice"
partition method (Phase 08, method 1). OR-Tools CP-SAT and non-rectilinear partitions are follow-ups.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Rect:
    x: float
    y: float
    dx: float
    dy: float

    @property
    def area(self) -> float:
        return self.dx * self.dy


def _normalize(sizes: list[float], area: float) -> list[float]:
    total = sum(sizes)
    if total <= 0:
        return [area / len(sizes)] * len(sizes)
    return [s * area / total for s in sizes]


def _layout_row(sizes: list[float], x: float, y: float, dy: float) -> list[Rect]:
    width = sum(sizes) / dy
    rects = []
    cy = y
    for s in sizes:
        h = s / width
        rects.append(Rect(x, cy, width, h))
        cy += h
    return rects


def _layout_col(sizes: list[float], x: float, y: float, dx: float) -> list[Rect]:
    height = sum(sizes) / dx
    rects = []
    cx = x
    for s in sizes:
        w = s / height
        rects.append(Rect(cx, y, w, height))
        cx += w
    return rects


def _layout(sizes: list[float], x: float, y: float, dx: float, dy: float) -> list[Rect]:
    return _layout_row(sizes, x, y, dy) if dx >= dy else _layout_col(sizes, x, y, dx)


def _leftover(sizes: list[float], x: float, y: float, dx: float, dy: float) -> tuple[float, float, float, float]:
    covered = sum(sizes)
    if dx >= dy:
        width = covered / dy
        return x + width, y, dx - width, dy
    height = covered / dx
    return x, y + height, dx, dy - height


def _worst_ratio(sizes: list[float], x: float, y: float, dx: float, dy: float) -> float:
    rects = _layout(sizes, x, y, dx, dy)
    return max(max(r.dx / r.dy, r.dy / r.dx) for r in rects if r.dx > 0 and r.dy > 0)


def squarify(weights: list[float], x: float, y: float, dx: float, dy: float) -> list[Rect]:
    """Return one Rect per weight, tiling the (x, y, dx, dy) container."""
    sizes = _normalize([max(w, 1e-6) for w in weights], dx * dy)
    return _squarify(sizes, x, y, dx, dy)


def _squarify(sizes: list[float], x: float, y: float, dx: float, dy: float) -> list[Rect]:
    if not sizes:
        return []
    if len(sizes) == 1:
        return [Rect(x, y, dx, dy)]
    if dx <= 0 or dy <= 0:
        return [Rect(x, y, max(dx, 0), max(dy, 0)) for _ in sizes]

    i = 1
    while i < len(sizes) and _worst_ratio(sizes[:i], x, y, dx, dy) >= _worst_ratio(
        sizes[: i + 1], x, y, dx, dy
    ):
        i += 1

    current = sizes[:i]
    remaining = sizes[i:]
    lx, ly, ldx, ldy = _leftover(current, x, y, dx, dy)
    return _layout(current, x, y, dx, dy) + _squarify(remaining, lx, ly, ldx, ldy)
