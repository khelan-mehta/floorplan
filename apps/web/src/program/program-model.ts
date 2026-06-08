// Pure model for the program editor. Editor state <-> Phase-02 ProgramGraph document.

import type { AdjacencyEdge, ProgramGraph, RoomNode } from '@fpg/schemas';

export interface ProgramState {
  source: ProgramGraph['source'];
  nodes: RoomNode[];
  edges: AdjacencyEdge[];
  entry?: ProgramGraph['entry'];
}

export function totalTargetAreaMm2(nodes: RoomNode[]): number {
  return nodes.reduce((acc, n) => acc + (n.area_target_mm2 ?? 0) * (n.count ?? 1), 0);
}

export interface BudgetStatus {
  usedMm2: number;
  availableMm2: number;
  ratio: number;
  over: boolean;
}

export function budget(nodes: RoomNode[], availableMm2: number): BudgetStatus {
  const usedMm2 = totalTargetAreaMm2(nodes);
  const ratio = availableMm2 > 0 ? usedMm2 / availableMm2 : 0;
  return { usedMm2, availableMm2, ratio, over: availableMm2 > 0 && usedMm2 > availableMm2 };
}

export interface AdjacencyMatrix {
  ids: string[];
  labels: string[];
  cells: (AdjacencyEdge['relation'] | null)[][];
}

export function adjacencyMatrix(nodes: RoomNode[], edges: AdjacencyEdge[]): AdjacencyMatrix {
  const ids = nodes.map((n) => n.id);
  const labels = nodes.map((n) => n.label ?? n.type);
  const idx = new Map(ids.map((id, i) => [id, i]));
  const cells: (AdjacencyEdge['relation'] | null)[][] = ids.map(() => ids.map(() => null));
  for (const e of edges) {
    const a = idx.get(e.a);
    const b = idx.get(e.b);
    if (a == null || b == null) continue;
    cells[a]![b] = e.relation;
    cells[b]![a] = e.relation;
  }
  return { ids, labels, cells };
}

export interface Contradiction {
  a: string;
  b: string;
  message: string;
}

export function contradictions(edges: AdjacencyEdge[]): Contradiction[] {
  const out: Contradiction[] = [];
  const key = (a: string, b: string) => [a, b].sort().join('|');
  const byPair = new Map<string, Set<string>>();
  for (const e of edges) {
    const k = key(e.a, e.b);
    if (!byPair.has(k)) byPair.set(k, new Set());
    byPair.get(k)!.add(e.relation);
  }
  for (const [k, rels] of byPair) {
    const positive =
      rels.has('adjacent') || rels.has('connected_door') || rels.has('connected_open');
    if (rels.has('not_adjacent') && positive) {
      const [a, b] = k.split('|') as [string, string];
      out.push({ a, b, message: `${a} and ${b} are both required adjacent and not-adjacent` });
    }
  }
  return out;
}

export function buildProgramDoc(state: ProgramState, id?: string): ProgramGraph {
  return {
    schema_version: 1,
    id: id ?? crypto.randomUUID(),
    source: state.source,
    nodes: state.nodes,
    edges: state.edges,
    ...(state.entry ? { entry: state.entry } : {}),
  };
}

export function programToState(doc: ProgramGraph): ProgramState {
  return { source: doc.source, nodes: doc.nodes, edges: doc.edges, entry: doc.entry };
}

// --- Starter templates ---
const node = (
  id: string,
  type: string,
  label: string,
  areaM2: number,
  extra: Partial<RoomNode> = {},
): RoomNode => ({
  id,
  type,
  label,
  area_target_mm2: Math.round(areaM2 * 1_000_000),
  ...extra,
});

const edge = (
  a: string,
  b: string,
  relation: AdjacencyEdge['relation'],
  weight = 0.7,
): AdjacencyEdge => ({
  a,
  b,
  relation,
  weight,
});

export const TEMPLATES: Record<string, ProgramState> = {
  '2-bed apartment': {
    source: 'template',
    nodes: [
      node('entry', 'entry', 'Entry', 4),
      node('living', 'living', 'Living', 22, {
        requires_window: true,
        requires_exterior_wall: true,
      }),
      node('kitchen', 'kitchen', 'Kitchen', 12, { tags: ['wet'] }),
      node('bedroom-1', 'master_bedroom', 'Master Bedroom', 14, { requires_window: true }),
      node('bedroom-2', 'bedroom', 'Bedroom 2', 11, { requires_window: true }),
      node('bathroom', 'bathroom', 'Bathroom', 5, { tags: ['wet'] }),
      node('hallway', 'corridor', 'Hallway', 6),
    ],
    edges: [
      edge('entry', 'living', 'connected_open', 0.9),
      edge('living', 'kitchen', 'connected_open', 0.8),
      edge('entry', 'hallway', 'connected_door'),
      edge('hallway', 'bedroom-1', 'connected_door', 0.9),
      edge('hallway', 'bedroom-2', 'connected_door', 0.9),
      edge('hallway', 'bathroom', 'connected_door', 0.8),
    ],
  },
  'small office': {
    source: 'template',
    nodes: [
      node('reception', 'lobby', 'Reception', 18),
      node('open-office', 'office', 'Open Office', 60, { requires_window: true }),
      node('meeting', 'meeting', 'Meeting Room', 16),
      node('kitchen', 'kitchen', 'Kitchenette', 8),
      node('wc', 'wc', 'WC', 6, { tags: ['wet'] }),
    ],
    edges: [
      edge('reception', 'open-office', 'connected_open', 0.9),
      edge('open-office', 'meeting', 'adjacent', 0.7),
      edge('open-office', 'kitchen', 'adjacent', 0.6),
      edge('reception', 'wc', 'connected_door', 0.6),
    ],
  },
};
