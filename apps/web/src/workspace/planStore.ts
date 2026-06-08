import { create } from 'zustand';
import { polygonArea, type Pt } from '@fpg/geometry-core';
import type { Plan } from '@fpg/schemas';
import { autoFurnish } from '../library/furnish';

function clone(plan: Plan): Plan {
  return JSON.parse(JSON.stringify(plan)) as Plan;
}

function centroid(points: number[][]): [number, number] {
  const xs = points.map((p) => p[0]!);
  const ys = points.map((p) => p[1]!);
  return [
    Math.round(xs.reduce((a, b) => a + b, 0) / xs.length),
    Math.round(ys.reduce((a, b) => a + b, 0) / ys.length),
  ];
}

type Wall = Plan['levels'][number]['walls'][number];
type Opening = Plan['levels'][number]['openings'][number];

/** Room id encoded in a generated wall id `w-<roomId>-<edgeIndex>`. */
export function wallRoomId(wallId: string): string {
  return wallId.replace(/^w-/, '').replace(/-\d+$/, '');
}

function wallLen(w: Wall): number {
  return Math.hypot(w.b[0] - w.a[0], w.b[1] - w.a[1]) || 1;
}

/** True if two wall segments are collinear and overlap (i.e. share a party wall). */
function collinearOverlap(w1: Wall, w2: Wall, tol = 50): boolean {
  const dx = w1.b[0] - w1.a[0];
  const dy = w1.b[1] - w1.a[1];
  const len = Math.hypot(dx, dy) || 1;
  const ux = dx / len;
  const uy = dy / len;
  for (const p of [w2.a, w2.b]) {
    const perp = Math.abs((p[0] - w1.a[0]) * -uy + (p[1] - w1.a[1]) * ux);
    if (perp > tol) return false;
  }
  const t1 = (w2.a[0] - w1.a[0]) * ux + (w2.a[1] - w1.a[1]) * uy;
  const t2 = (w2.b[0] - w1.a[0]) * ux + (w2.b[1] - w1.a[1]) * uy;
  const lo = Math.max(0, Math.min(t1, t2));
  const hi = Math.min(len, Math.max(t1, t2));
  return hi - lo > 600;
}

/** Infer what an opening on this wall connects: exterior, or the neighbouring room. */
function inferConnects(level: Plan['levels'][number], wall: Wall): [string, string] {
  const room = wallRoomId(wall.id);
  if (wall.type === 'exterior') return [room, 'exterior'];
  for (const w2 of level.walls) {
    if (w2.id === wall.id) continue;
    const other = wallRoomId(w2.id);
    if (other !== room && collinearOverlap(wall, w2)) return [room, other];
  }
  return [room, 'exterior'];
}

interface PlanEditorState {
  plan: Plan | null;
  past: Plan[];
  future: Plan[];
  dirty: boolean;

  load: (plan: Plan) => void;
  canUndo: () => boolean;
  canRedo: () => boolean;
  undo: () => void;
  redo: () => void;

  setRoomType: (levelIndex: number, roomId: string, type: string) => void;
  moveRoomVertex: (levelIndex: number, roomId: string, ptIndex: number, p: Pt) => void;
  autoFurnishRoom: (levelIndex: number, roomId: string) => void;
  removeFixture: (levelIndex: number, fixtureId: string) => void;
  addOpening: (levelIndex: number, wallId: string, kind: 'door' | 'window') => void;
  moveOpening: (levelIndex: number, openingId: string, offsetMm: number) => void;
  setOpeningWidth: (levelIndex: number, openingId: string, widthMm: number) => void;
  deleteOpening: (levelIndex: number, openingId: string) => void;
  markSaved: () => void;
}

function commit(state: PlanEditorState, next: Plan): Partial<PlanEditorState> {
  if (!state.plan) return {};
  return { plan: next, past: [...state.past, state.plan], future: [], dirty: true };
}

export const usePlanEditor = create<PlanEditorState>((set, get) => ({
  plan: null,
  past: [],
  future: [],
  dirty: false,

  load: (plan) => set({ plan: clone(plan), past: [], future: [], dirty: false }),
  canUndo: () => get().past.length > 0,
  canRedo: () => get().future.length > 0,

  undo: () =>
    set((s) => {
      const prev = s.past[s.past.length - 1];
      if (!prev || !s.plan) return s;
      return { plan: prev, past: s.past.slice(0, -1), future: [s.plan, ...s.future], dirty: true };
    }),
  redo: () =>
    set((s) => {
      const nxt = s.future[0];
      if (!nxt || !s.plan) return s;
      return { plan: nxt, past: [...s.past, s.plan], future: s.future.slice(1), dirty: true };
    }),

  setRoomType: (levelIndex, roomId, type) =>
    set((s) => {
      if (!s.plan) return s;
      const next = clone(s.plan);
      const level = next.levels.find((l) => l.index === levelIndex);
      const room = level?.rooms.find((r) => r.id === roomId);
      if (!room) return s;
      room.type = type;
      return commit(s, next);
    }),

  moveRoomVertex: (levelIndex, roomId, ptIndex, p) =>
    set((s) => {
      if (!s.plan) return s;
      const next = clone(s.plan);
      const level = next.levels.find((l) => l.index === levelIndex);
      const room = level?.rooms.find((r) => r.id === roomId);
      const ring = room?.polygon.rings[0];
      if (!room || !ring || !ring.points[ptIndex]) return s;
      ring.points[ptIndex] = [Math.round(p[0]), Math.round(p[1])];
      room.area_mm2 = Math.round(polygonArea(ring.points.map((q) => [q[0], q[1]] as Pt)));
      room.centroid = centroid(ring.points);
      return commit(s, next);
    }),

  autoFurnishRoom: (levelIndex, roomId) =>
    set((s) => {
      if (!s.plan) return s;
      const next = clone(s.plan);
      const level = next.levels.find((l) => l.index === levelIndex);
      const room = level?.rooms.find((r) => r.id === roomId);
      if (!level || !room) return s;
      level.fixtures = [
        ...level.fixtures.filter((f) => f.room_id !== roomId),
        ...autoFurnish(room),
      ];
      return commit(s, next);
    }),

  removeFixture: (levelIndex, fixtureId) =>
    set((s) => {
      if (!s.plan) return s;
      const next = clone(s.plan);
      const level = next.levels.find((l) => l.index === levelIndex);
      if (!level) return s;
      level.fixtures = level.fixtures.filter((f) => f.id !== fixtureId);
      return commit(s, next);
    }),

  addOpening: (levelIndex, wallId, kind) =>
    set((s) => {
      if (!s.plan) return s;
      const next = clone(s.plan);
      const level = next.levels.find((l) => l.index === levelIndex);
      const wall = level?.walls.find((w) => w.id === wallId);
      if (!level || !wall) return s;
      const len = wallLen(wall);
      const width = Math.min(kind === 'door' ? 900 : 1500, Math.max(600, len - 300));
      const opening = {
        id: `${kind === 'door' ? 'd' : 'win'}-${wallId}-${Date.now() % 100000}`,
        wall_id: wallId,
        kind,
        offset_mm: Math.round((len - width) / 2),
        width_mm: Math.round(width),
        height_mm: kind === 'door' ? 2100 : 1200,
        ...(kind === 'window' ? { sill_mm: 900 } : {}),
        connects: inferConnects(level, wall),
      } as Opening;
      level.openings = [...level.openings, opening];
      return commit(s, next);
    }),

  moveOpening: (levelIndex, openingId, offsetMm) =>
    set((s) => {
      if (!s.plan) return s;
      const next = clone(s.plan);
      const level = next.levels.find((l) => l.index === levelIndex);
      const op = level?.openings.find((o) => o.id === openingId);
      const wall = level?.walls.find((w) => w.id === op?.wall_id);
      if (!level || !op || !wall) return s;
      const max = Math.max(0, wallLen(wall) - op.width_mm);
      op.offset_mm = Math.round(Math.min(max, Math.max(0, offsetMm)));
      return commit(s, next);
    }),

  setOpeningWidth: (levelIndex, openingId, widthMm) =>
    set((s) => {
      if (!s.plan) return s;
      const next = clone(s.plan);
      const level = next.levels.find((l) => l.index === levelIndex);
      const op = level?.openings.find((o) => o.id === openingId);
      const wall = level?.walls.find((w) => w.id === op?.wall_id);
      if (!level || !op || !wall) return s;
      const w = Math.max(400, Math.min(widthMm, wallLen(wall) - 100));
      op.width_mm = Math.round(w);
      op.offset_mm = Math.round(Math.min(op.offset_mm, Math.max(0, wallLen(wall) - w)));
      return commit(s, next);
    }),

  deleteOpening: (levelIndex, openingId) =>
    set((s) => {
      if (!s.plan) return s;
      const next = clone(s.plan);
      const level = next.levels.find((l) => l.index === levelIndex);
      if (!level) return s;
      level.openings = level.openings.filter((o) => o.id !== openingId);
      return commit(s, next);
    }),

  markSaved: () => set({ dirty: false }),
}));
