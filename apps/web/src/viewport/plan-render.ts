// Pure helpers for rendering a Plan. Shared by the 2D (Konva) and 3D (R3F) viewports.

import type { Plan, PlanLevel } from '@fpg/schemas';

export type Point = [number, number];

/** Color palette by room type (with a stable fallback for unknown types). */
const ROOM_COLORS: Record<string, string> = {
  living: '#3b82f6',
  dining: '#6366f1',
  kitchen: '#f59e0b',
  bedroom: '#10b981',
  master_bedroom: '#059669',
  bathroom: '#06b6d4',
  ensuite: '#0891b2',
  wc: '#0e7490',
  hallway: '#94a3b8',
  corridor: '#94a3b8',
  entry: '#a78bfa',
  lobby: '#a78bfa',
  stair: '#f43f5e',
  elevator: '#e11d48',
  closet: '#a3a3a3',
  laundry: '#22d3ee',
  garage: '#64748b',
  office: '#8b5cf6',
  balcony: '#84cc16',
  storage: '#737373',
  mechanical: '#525252',
};

const FALLBACK_COLORS = ['#ef4444', '#f97316', '#eab308', '#22c55e', '#14b8a6', '#8b5cf6'];

export function roomColor(type: string): string {
  if (ROOM_COLORS[type]) return ROOM_COLORS[type];
  let hash = 0;
  for (let i = 0; i < type.length; i++) hash = (hash * 31 + type.charCodeAt(i)) >>> 0;
  return FALLBACK_COLORS[hash % FALLBACK_COLORS.length] as string;
}

export interface LegendEntry {
  type: string;
  color: string;
}

export function planLegend(level: PlanLevel): LegendEntry[] {
  const seen = new Set<string>();
  const out: LegendEntry[] = [];
  for (const room of level.rooms) {
    if (!seen.has(room.type)) {
      seen.add(room.type);
      out.push({ type: room.type, color: roomColor(room.type) });
    }
  }
  return out;
}

export interface BBox {
  minX: number;
  minY: number;
  maxX: number;
  maxY: number;
  width: number;
  height: number;
}

export function levelBBox(level: PlanLevel): BBox {
  let minX = Infinity;
  let minY = Infinity;
  let maxX = -Infinity;
  let maxY = -Infinity;
  const consider = (p: Point) => {
    minX = Math.min(minX, p[0]);
    minY = Math.min(minY, p[1]);
    maxX = Math.max(maxX, p[0]);
    maxY = Math.max(maxY, p[1]);
  };
  for (const room of level.rooms) {
    for (const ring of room.polygon.rings) for (const pt of ring.points) consider(pt as Point);
  }
  for (const wall of level.walls) {
    consider(wall.a as Point);
    consider(wall.b as Point);
  }
  if (!Number.isFinite(minX)) return { minX: 0, minY: 0, maxX: 0, maxY: 0, width: 0, height: 0 };
  return { minX, minY, maxX, maxY, width: maxX - minX, height: maxY - minY };
}

export function getLevel(plan: Plan, index: number): PlanLevel | undefined {
  return plan.levels.find((l) => l.index === index) ?? plan.levels[0];
}

/** Flatten a ring's points into the [x0,y0,x1,y1,...] array Konva expects. */
export function ringToFlatPoints(points: readonly Point[]): number[] {
  return points.flatMap((p) => [p[0], p[1]]);
}
