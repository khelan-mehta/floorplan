// Browser-side geometry helpers. All coordinates are integer millimetres (mm).

export type Pt = [number, number];

export interface BBox {
  minX: number;
  minY: number;
  maxX: number;
  maxY: number;
  width: number;
  height: number;
}

export function distance(a: Pt, b: Pt): number {
  return Math.hypot(b[0] - a[0], b[1] - a[1]);
}

export function snapToGrid(p: Pt, grid: number): Pt {
  if (grid <= 0) return p;
  return [Math.round(p[0] / grid) * grid, Math.round(p[1] / grid) * grid];
}

/** Snap the segment origin→p to the nearest `stepDeg` direction, keeping its length. */
export function snapAngle(origin: Pt, p: Pt, stepDeg = 45): Pt {
  const dx = p[0] - origin[0];
  const dy = p[1] - origin[1];
  const len = Math.hypot(dx, dy);
  if (len === 0) return p;
  const step = (stepDeg * Math.PI) / 180;
  const angle = Math.round(Math.atan2(dy, dx) / step) * step;
  return [
    Math.round(origin[0] + Math.cos(angle) * len),
    Math.round(origin[1] + Math.sin(angle) * len),
  ];
}

export function bbox(points: readonly Pt[]): BBox {
  if (points.length === 0) return { minX: 0, minY: 0, maxX: 0, maxY: 0, width: 0, height: 0 };
  let minX = Infinity;
  let minY = Infinity;
  let maxX = -Infinity;
  let maxY = -Infinity;
  for (const [x, y] of points) {
    minX = Math.min(minX, x);
    minY = Math.min(minY, y);
    maxX = Math.max(maxX, x);
    maxY = Math.max(maxY, y);
  }
  return { minX, minY, maxX, maxY, width: maxX - minX, height: maxY - minY };
}

export function signedArea(points: readonly Pt[]): number {
  let sum = 0;
  for (let i = 0; i < points.length; i++) {
    const a = points[i] as Pt;
    const b = points[(i + 1) % points.length] as Pt;
    sum += a[0] * b[1] - b[0] * a[1];
  }
  return sum / 2;
}

export const polygonArea = (points: readonly Pt[]): number => Math.abs(signedArea(points));

export function ensureCCW(points: Pt[]): Pt[] {
  return signedArea(points) < 0 ? [...points].reverse() : points;
}

export function polygonPerimeter(points: readonly Pt[]): number {
  let total = 0;
  for (let i = 0; i < points.length; i++) {
    total += distance(points[i] as Pt, points[(i + 1) % points.length] as Pt);
  }
  return total;
}

export function pointInPolygon(p: Pt, ring: readonly Pt[]): boolean {
  let inside = false;
  for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
    const a = ring[i] as Pt;
    const b = ring[j] as Pt;
    const intersect =
      a[1] > p[1] !== b[1] > p[1] &&
      p[0] < ((b[0] - a[0]) * (p[1] - a[1])) / (b[1] - a[1] || 1e-9) + a[0];
    if (intersect) inside = !inside;
  }
  return inside;
}

export function nearestVertex(points: readonly Pt[], p: Pt, tol: number): number | null {
  let best = -1;
  let bestD = tol;
  points.forEach((v, i) => {
    const d = distance(v, p);
    if (d <= bestD) {
      best = i;
      bestD = d;
    }
  });
  return best >= 0 ? best : null;
}

export interface Setbacks {
  front_mm: number;
  rear_mm: number;
  left_mm: number;
  right_mm: number;
}

/**
 * Buildable envelope as an axis-aligned rectangle: the parcel's bounding box inset by setbacks.
 * front = +Y (north), rear = -Y, left = -X, right = +X. Returns CCW points (or null if degenerate).
 * NOTE: true polygon offsetting for non-rectangular parcels is a follow-up (needs a clipper).
 */
export function setbackEnvelope(parcel: readonly Pt[], s: Setbacks): Pt[] | null {
  const b = bbox(parcel);
  const minX = b.minX + s.left_mm;
  const maxX = b.maxX - s.right_mm;
  const minY = b.minY + s.rear_mm;
  const maxY = b.maxY - s.front_mm;
  if (maxX <= minX || maxY <= minY) return null;
  return [
    [minX, minY],
    [maxX, minY],
    [maxX, maxY],
    [minX, maxY],
  ];
}
