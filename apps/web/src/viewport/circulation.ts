// Derive the entry room and circulation (room-to-room door) graph from a generated plan level,
// for the "how a person walks through the house" overlay. Mirrors the entry/circulation concepts
// from services/generator/app/solver.py (ENTRY_TYPES, the BFS spanning tree of doors from the
// entry room) but is computed here purely from the Plan doc — no backend round-trip.

import type { PlanLevel, Room } from '@fpg/schemas';
import type { Point } from './plan-render';

const ENTRY_TYPES = new Set(['entry', 'foyer', 'lobby', 'vestibule', 'reception', 'mudroom']);
const CORRIDOR_RE = /corridor|hallway/i;

/** The room a person enters the house through: an exterior door's room, preferring an
 * entry/foyer/lobby-type room if one has an exterior door. */
export function findEntryRoom(level: PlanLevel): Room | undefined {
  const exteriorDoorRoomIds = new Set(
    level.openings
      .filter((o) => o.kind === 'door' && (o.connects ?? ([] as string[])).includes('exterior'))
      .flatMap((o) => (o.connects ?? ([] as string[])).filter((id) => id !== 'exterior')),
  );
  const candidates = level.rooms.filter((r) => exteriorDoorRoomIds.has(r.id));
  if (candidates.length === 0) return undefined;
  const named = candidates.find((r) => ENTRY_TYPES.has(r.type));
  return named ?? candidates[0];
}

/** Room ids whose type marks them as circulation space (corridor/hallway). */
export function corridorRoomIds(level: PlanLevel): Set<string> {
  return new Set(level.rooms.filter((r) => CORRIDOR_RE.test(r.type)).map((r) => r.id));
}

export interface CirculationEdge {
  a: Point;
  b: Point;
}

/** Door openings that connect two real rooms (the circulation spanning tree the generator
 * placed, plus any extra adjacency doors) — as centroid-to-centroid segments for drawing. */
export function circulationEdges(level: PlanLevel): CirculationEdge[] {
  const byId = new Map(level.rooms.map((r) => [r.id, r]));
  const edges: CirculationEdge[] = [];
  for (const o of level.openings) {
    if (o.kind !== 'door') continue;
    const [a, b] = o.connects ?? [];
    if (!a || !b || a === 'exterior' || b === 'exterior') continue;
    const ra = byId.get(a);
    const rb = byId.get(b);
    if (!ra || !rb) continue;
    edges.push({ a: ra.centroid as Point, b: rb.centroid as Point });
  }
  return edges;
}

export interface DoorGraphEdge {
  to: string;
  doorId: string;
}

/** Adjacency list of room-to-room door connections (the same doors `circulationEdges` draws),
 * keyed by room id — used for shortest-path (fewest-doors) routing. */
export function roomDoorGraph(level: PlanLevel): Map<string, DoorGraphEdge[]> {
  const roomIds = new Set(level.rooms.map((r) => r.id));
  const graph = new Map<string, DoorGraphEdge[]>();
  const add = (from: string, to: string, doorId: string) => {
    const list = graph.get(from);
    if (list) list.push({ to, doorId });
    else graph.set(from, [{ to, doorId }]);
  };
  for (const o of level.openings) {
    if (o.kind !== 'door') continue;
    const [a, b] = o.connects ?? [];
    if (!a || !b || !roomIds.has(a) || !roomIds.has(b)) continue;
    add(a, b, o.id);
    add(b, a, o.id);
  }
  return graph;
}

export interface DoorPath {
  /** Number of doors from the entry room to this room. */
  distance: number;
  /** Room ids from the entry room to this room, inclusive. */
  path: string[];
}

/** BFS from the entry room over the room-to-room door graph: the fewest-doors ("most
 * preferred") route from the entry to every reachable room. */
export function shortestDoorPaths(level: PlanLevel): Map<string, DoorPath> {
  const result = new Map<string, DoorPath>();
  const entry = findEntryRoom(level);
  if (!entry) return result;

  const graph = roomDoorGraph(level);
  result.set(entry.id, { distance: 0, path: [entry.id] });
  const queue: string[] = [entry.id];
  while (queue.length > 0) {
    const current = queue.shift()!;
    const { distance, path } = result.get(current)!;
    for (const { to } of graph.get(current) ?? []) {
      if (result.has(to)) continue;
      result.set(to, { distance: distance + 1, path: [...path, to] });
      queue.push(to);
    }
  }
  return result;
}
