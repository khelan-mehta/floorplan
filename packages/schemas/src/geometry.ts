// Geometry invariants (Phase 02). Deterministic, dependency-free. Mirrors the Python
// `fpg_schemas.geometry` checks. Coordinates are integer millimetres.
//
// Invariants enforced:
//   - rings have >= 3 points and integer coordinates
//   - outer ring is counter-clockwise (CCW), holes are clockwise (CW)
//   - rings are simple (no self-intersection)

import type { Boundary, Plan } from '../gen/ts/types';

export type Point = [number, number];

export interface GeometryIssue {
  code:
    | 'too_few_points'
    | 'non_integer'
    | 'outer_not_ccw'
    | 'hole_not_cw'
    | 'self_intersection'
    | 'zero_area';
  message: string;
  path: string;
}

/** Shoelace signed area (mm²). Positive = CCW, negative = CW. */
export function signedArea(points: readonly Point[]): number {
  let sum = 0;
  for (let i = 0; i < points.length; i++) {
    const [x1, y1] = points[i] as Point;
    const [x2, y2] = points[(i + 1) % points.length] as Point;
    sum += x1 * y2 - x2 * y1;
  }
  return sum / 2;
}

export const isCCW = (points: readonly Point[]): boolean => signedArea(points) > 0;

function orientation(a: Point, b: Point, c: Point): number {
  const v = (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0]);
  return v > 0 ? 1 : v < 0 ? -1 : 0;
}

function onSegment(a: Point, b: Point, p: Point): boolean {
  return (
    Math.min(a[0], b[0]) <= p[0] &&
    p[0] <= Math.max(a[0], b[0]) &&
    Math.min(a[1], b[1]) <= p[1] &&
    p[1] <= Math.max(a[1], b[1])
  );
}

function segmentsProperlyIntersect(p1: Point, p2: Point, p3: Point, p4: Point): boolean {
  const o1 = orientation(p1, p2, p3);
  const o2 = orientation(p1, p2, p4);
  const o3 = orientation(p3, p4, p1);
  const o4 = orientation(p3, p4, p2);
  if (o1 !== o2 && o3 !== o4) return true;
  if (o1 === 0 && onSegment(p1, p2, p3)) return true;
  if (o2 === 0 && onSegment(p1, p2, p4)) return true;
  if (o3 === 0 && onSegment(p3, p4, p1)) return true;
  if (o4 === 0 && onSegment(p3, p4, p2)) return true;
  return false;
}

/** True if a closed ring (implicit closure) crosses itself. */
export function ringSelfIntersects(points: readonly Point[]): boolean {
  const n = points.length;
  for (let i = 0; i < n; i++) {
    const a1 = points[i] as Point;
    const a2 = points[(i + 1) % n] as Point;
    for (let j = i + 1; j < n; j++) {
      // skip adjacent edges (they legitimately share an endpoint)
      if (j === i) continue;
      if ((i + 1) % n === j || (j + 1) % n === i) continue;
      const b1 = points[j] as Point;
      const b2 = points[(j + 1) % n] as Point;
      if (segmentsProperlyIntersect(a1, a2, b1, b2)) return true;
    }
  }
  return false;
}

interface RingLike {
  points: Point[];
}
interface PolygonLike {
  rings: RingLike[];
}

export function lintPolygon(polygon: PolygonLike, path: string): GeometryIssue[] {
  const issues: GeometryIssue[] = [];
  polygon.rings.forEach((ring, ri) => {
    const rpath = `${path}/rings/${ri}`;
    const pts = ring.points;
    if (pts.length < 3) {
      issues.push({ code: 'too_few_points', message: 'ring needs >= 3 points', path: rpath });
      return;
    }
    for (const [x, y] of pts) {
      if (!Number.isInteger(x) || !Number.isInteger(y)) {
        issues.push({
          code: 'non_integer',
          message: 'coordinates must be integer mm',
          path: rpath,
        });
        break;
      }
    }
    const area = signedArea(pts);
    if (area === 0) {
      issues.push({ code: 'zero_area', message: 'ring has zero area', path: rpath });
    } else if (ri === 0 && area < 0) {
      issues.push({ code: 'outer_not_ccw', message: 'outer ring must be CCW', path: rpath });
    } else if (ri > 0 && area > 0) {
      issues.push({ code: 'hole_not_cw', message: 'hole ring must be CW', path: rpath });
    }
    if (ringSelfIntersects(pts)) {
      issues.push({ code: 'self_intersection', message: 'ring self-intersects', path: rpath });
    }
  });
  return issues;
}

/** Lint every polygon in a Boundary (outlines, cores, voids, parcel). */
export function lintBoundary(boundary: Boundary): GeometryIssue[] {
  const issues: GeometryIssue[] = [];
  boundary.levels.forEach((level, li) => {
    issues.push(...lintPolygon(level.outline, `/levels/${li}/outline`));
    (level.cores ?? []).forEach((c, ci) =>
      issues.push(...lintPolygon(c, `/levels/${li}/cores/${ci}`)),
    );
    (level.voids ?? []).forEach((v, vi) =>
      issues.push(...lintPolygon(v, `/levels/${li}/voids/${vi}`)),
    );
  });
  if (boundary.site) {
    issues.push(...lintPolygon(boundary.site.parcel_polygon, '/site/parcel_polygon'));
  }
  return issues;
}

/** Lint every room polygon in a Plan. */
export function lintPlan(plan: Plan): GeometryIssue[] {
  const issues: GeometryIssue[] = [];
  plan.levels.forEach((level, li) => {
    level.rooms.forEach((room, ri) =>
      issues.push(...lintPolygon(room.polygon, `/levels/${li}/rooms/${ri}/polygon`)),
    );
  });
  return issues;
}
