// Pure helpers: turn a Plan level into simple 3D primitives (room floor slabs + wall boxes).
// This is a lightweight Phase-04 scaffold; the real solidifier (CSG openings, slabs, stairs) is
// Phase 11. Units are millimetres; the scene scales to metres for rendering.

import type { PlanLevel } from '@fpg/schemas';
import { roomColor, type Point } from './plan-render';

export const MM_TO_M = 0.001;

export interface WallBox {
  id: string;
  center: [number, number, number];
  size: [number, number, number];
  rotationY: number;
}

export interface RoomSlab {
  id: string;
  type: string;
  color: string;
  // Flat polygon in the XZ plane (metres), y ~ 0.
  points: Point[];
  centroid: [number, number];
}

export function wallBoxes(level: PlanLevel): WallBox[] {
  return level.walls.map((w) => {
    const [ax, ay] = w.a as Point;
    const [bx, by] = w.b as Point;
    const dx = bx - ax;
    const dy = by - ay;
    const length = Math.hypot(dx, dy);
    const cx = (ax + bx) / 2;
    const cy = (ay + by) / 2;
    return {
      id: w.id,
      center: [cx * MM_TO_M, (w.height_mm / 2) * MM_TO_M, cy * MM_TO_M],
      size: [length * MM_TO_M, w.height_mm * MM_TO_M, w.thickness_mm * MM_TO_M],
      rotationY: -Math.atan2(dy, dx),
    };
  });
}

export function roomSlabs(level: PlanLevel): RoomSlab[] {
  return level.rooms.map((r) => ({
    id: r.id,
    type: r.type,
    color: roomColor(r.type),
    points: (r.polygon.rings[0]?.points ?? []).map((p) => [p[0] * MM_TO_M, p[1] * MM_TO_M]),
    centroid: [r.centroid[0] * MM_TO_M, r.centroid[1] * MM_TO_M],
  }));
}

// --- walls with real openings (doors/windows) -----------------------------------------------

/** An oriented box in world space (metres), rotated about Y. */
export interface Box {
  center: [number, number, number];
  size: [number, number, number];
  rotationY: number;
}

export interface Opening3D {
  id: string;
  kind: 'door' | 'window' | 'opening';
  center: [number, number, number]; // centre of the void, metres
  rotationY: number;
  width: number; // along the wall, metres
  height: number; // vertical, metres
  thickness: number; // wall thickness, metres
}

interface WallGeom {
  ax: number;
  ay: number;
  ux: number;
  uy: number;
  len: number;
  H: number;
  thick: number;
  rotationY: number;
}

function wallGeom(w: PlanLevel['walls'][number]): WallGeom {
  const [ax, ay] = w.a as Point;
  const [bx, by] = w.b as Point;
  const dx = bx - ax;
  const dy = by - ay;
  const len = Math.hypot(dx, dy) || 1;
  return {
    ax,
    ay,
    ux: dx / len,
    uy: dy / len,
    len,
    H: w.height_mm,
    thick: w.thickness_mm,
    rotationY: -Math.atan2(dy, dx),
  };
}

/** A box covering the wall span [x0,x1] (mm along wall) and height [z0,z1] (mm). */
function boxAlong(g: WallGeom, x0: number, x1: number, z0: number, z1: number): Box {
  const mid = (x0 + x1) / 2;
  const px = g.ax + g.ux * mid;
  const py = g.ay + g.uy * mid;
  return {
    center: [px * MM_TO_M, ((z0 + z1) / 2) * MM_TO_M, py * MM_TO_M],
    size: [(x1 - x0) * MM_TO_M, (z1 - z0) * MM_TO_M, g.thick * MM_TO_M],
    rotationY: g.rotationY,
  };
}

interface WallOpening {
  o0: number;
  o1: number;
  kind: 'door' | 'window' | 'opening';
  head: number; // top of void (mm)
  sill: number; // bottom of void (mm)
}

function openingsOnWall(g: WallGeom, ops: PlanLevel['openings']): WallOpening[] {
  const out: WallOpening[] = [];
  for (const o of ops) {
    const o0 = Math.max(0, o.offset_mm);
    const o1 = Math.min(g.len, o.offset_mm + o.width_mm);
    if (o1 - o0 < 1) continue;
    const isWindow = o.kind === 'window';
    const sill = isWindow ? (o.sill_mm ?? 900) : 0;
    const head = Math.min(g.H, sill + o.height_mm);
    out.push({ o0, o1, kind: o.kind, head, sill });
  }
  return out.sort((a, b) => a.o0 - b.o0);
}

/**
 * Solid wall pieces with rectangular voids where openings sit: full-height segments between
 * openings, plus a header above each opening and a sill panel below each window. This reads as a
 * real hole through the wall without CSG.
 */
export function wallSegments(level: PlanLevel): Box[] {
  const boxes: Box[] = [];
  for (const w of level.walls) {
    const g = wallGeom(w);
    const ops = openingsOnWall(
      g,
      level.openings.filter((o) => o.wall_id === w.id),
    );
    // Horizontal solids in the gaps between/around openings (full height).
    let p = 0;
    for (const op of ops) {
      if (op.o0 > p) boxes.push(boxAlong(g, p, op.o0, 0, g.H));
      p = Math.max(p, op.o1);
    }
    if (p < g.len) boxes.push(boxAlong(g, p, g.len, 0, g.H));
    // Headers (and window sills) over each opening span.
    for (const op of ops) {
      if (op.sill > 0) boxes.push(boxAlong(g, op.o0, op.o1, 0, op.sill));
      if (op.head < g.H) boxes.push(boxAlong(g, op.o0, op.o1, op.head, g.H));
    }
  }
  return boxes;
}

/** The void of each opening, for placing a door leaf / glazed window in the gap. */
export function openings3D(level: PlanLevel): Opening3D[] {
  const out: Opening3D[] = [];
  const wallById = new Map(level.walls.map((w) => [w.id, w]));
  for (const o of level.openings) {
    const w = wallById.get(o.wall_id);
    if (!w) continue;
    const g = wallGeom(w);
    const o0 = Math.max(0, o.offset_mm);
    const o1 = Math.min(g.len, o.offset_mm + o.width_mm);
    if (o1 - o0 < 1) continue;
    const sill = o.kind === 'window' ? (o.sill_mm ?? 900) : 0;
    const head = Math.min(g.H, sill + o.height_mm);
    const mid = (o0 + o1) / 2;
    const px = g.ax + g.ux * mid;
    const py = g.ay + g.uy * mid;
    out.push({
      id: o.id,
      kind: o.kind,
      center: [px * MM_TO_M, ((sill + head) / 2) * MM_TO_M, py * MM_TO_M],
      rotationY: g.rotationY,
      width: (o1 - o0) * MM_TO_M,
      height: (head - sill) * MM_TO_M,
      thickness: g.thick * MM_TO_M,
    });
  }
  return out;
}
