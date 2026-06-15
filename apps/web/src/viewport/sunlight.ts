// Heuristic per-room daylight overlay: looks at each room's exterior walls that carry windows,
// classifies which compass direction they face (using the project's +X=east, +Y=north
// convention), and scores the room's sun exposure with simplified daylight-orientation weights.
// This is a simplified heuristic for visualization, not a solar-geometry simulation.

import type { PlanLevel, Room } from '@fpg/schemas';
import type { Point } from './plan-render';

export type CompassDir = 'N' | 'S' | 'E' | 'W';

/** Relative daylight contribution by orientation (simplified heuristic, not solar geometry). */
const EXPOSURE_WEIGHT: Record<CompassDir, number> = { S: 1.0, E: 0.75, W: 0.6, N: 0.35 };

function classify(normal: Point): CompassDir {
  const [nx, ny] = normal;
  if (Math.abs(ny) >= Math.abs(nx)) return ny > 0 ? 'N' : 'S';
  return nx > 0 ? 'E' : 'W';
}

/** True if `[ax,ay]-[bx,by]` and `[cx,cy]-[dx,dy]` are the same segment (either direction),
 * within a small tolerance — used to match a room-polygon edge to a Wall. */
function sameSegment(a: Point, b: Point, c: Point, d: Point, tol = 5): boolean {
  const close = (p: Point, q: Point) =>
    Math.abs(p[0] - q[0]) <= tol && Math.abs(p[1] - q[1]) <= tol;
  return (close(a, c) && close(b, d)) || (close(a, d) && close(b, c));
}

export interface SunExposure {
  score: number; // 0 (least sun) .. 1 (most sun)
  dominant: CompassDir | null;
}

/** For one room's polygon, sum exterior-window widths by the compass direction they face
 * (using the project's +X=east, +Y=north convention). Shared by `roomSunExposure` (per-room)
 * and `levelSunDirection` (aggregated across the level). */
export function windowExposureByDirection(
  level: PlanLevel,
  ring: Point[],
  centroid: Point,
): Record<CompassDir, number> {
  const [cx, cy] = centroid;
  const totals: Record<CompassDir, number> = { N: 0, S: 0, E: 0, W: 0 };

  for (let i = 0; i < ring.length; i++) {
    const a = ring[i] as Point;
    const b = ring[(i + 1) % ring.length] as Point;
    const wall = level.walls.find(
      (w) => w.type === 'exterior' && sameSegment(a, b, w.a as Point, w.b as Point),
    );
    if (!wall) continue;
    const windows = level.openings.filter((o) => o.kind === 'window' && o.wall_id === wall.id);
    if (windows.length === 0) continue;

    // outward normal: perpendicular to the edge, pointing away from the room centroid
    const ex = b[0] - a[0];
    const ey = b[1] - a[1];
    let nx = -ey;
    let ny = ex;
    const midX = (a[0] + b[0]) / 2;
    const midY = (a[1] + b[1]) / 2;
    if (nx * (midX - cx) + ny * (midY - cy) < 0) {
      nx = -nx;
      ny = -ny;
    }
    const dir = classify([nx, ny]);
    const width = windows.reduce((sum, o) => sum + o.width_mm, 0);
    totals[dir] += width;
  }

  return totals;
}

export function roomSunExposure(level: PlanLevel, room: Room): SunExposure {
  const ring = room.polygon.rings[0]?.points ?? [];
  const totals = windowExposureByDirection(level, ring as Point[], room.centroid as Point);
  const totalWidth = totals.N + totals.S + totals.E + totals.W;

  if (totalWidth === 0) return { score: 0, dominant: null };

  let score = 0;
  let dominant: CompassDir | null = null;
  let best = -1;
  for (const dir of Object.keys(totals) as CompassDir[]) {
    const w = totals[dir];
    score += (w / totalWidth) * EXPOSURE_WEIGHT[dir];
    if (w > best) {
      best = w;
      dominant = dir;
    }
  }
  return { score, dominant: best > 0 ? dominant : null };
}

export interface SunDirection {
  dir: CompassDir;
  /** Unit-ish vector for placing the sun in the 3D scene: world XZ via +X=east, +Z=north. */
  vector: [number, number, number];
}

const SUN_VECTORS: Record<CompassDir, [number, number, number]> = {
  N: [0, 1, 1],
  S: [0, 1, -1],
  E: [1, 1, 0],
  W: [-1, 1, 0],
};

/** The dominant compass direction of exterior-window exposure across the whole level, used to
 * place a single "sun" in the 3D scene. Returns `null` if the level has no exterior windows. */
export function levelSunDirection(level: PlanLevel): SunDirection | null {
  const totals: Record<CompassDir, number> = { N: 0, S: 0, E: 0, W: 0 };
  for (const room of level.rooms) {
    const ring = room.polygon.rings[0]?.points ?? [];
    const roomTotals = windowExposureByDirection(level, ring as Point[], room.centroid as Point);
    for (const dir of Object.keys(roomTotals) as CompassDir[]) {
      totals[dir] += roomTotals[dir];
    }
  }

  let dominant: CompassDir | null = null;
  let best = 0;
  for (const dir of Object.keys(totals) as CompassDir[]) {
    if (totals[dir] > best) {
      best = totals[dir];
      dominant = dir;
    }
  }
  if (!dominant) return null;
  return { dir: dominant, vector: SUN_VECTORS[dominant] };
}

/** Lerp from a cool (#1e3a8a) to a warm (#fbbf24) color based on `score` in [0,1]. */
export function exposureColor(score: number): string {
  const t = Math.max(0, Math.min(1, score));
  const cool = [30, 58, 138];
  const warm = [251, 191, 36];
  const r = Math.round(cool[0]! + (warm[0]! - cool[0]!) * t);
  const g = Math.round(cool[1]! + (warm[1]! - cool[1]!) * t);
  const b = Math.round(cool[2]! + (warm[2]! - cool[2]!) * t);
  return `rgb(${r}, ${g}, ${b})`;
}
