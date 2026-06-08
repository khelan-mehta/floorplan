import { create } from 'zustand';
import type { AdjacencyEdge, ProgramGraph, RoomNode } from '@fpg/schemas';
import { type ProgramState, programToState } from './program-model';

interface ProgramStore extends ProgramState {
  addNode: () => void;
  updateNode: (id: string, patch: Partial<RoomNode>) => void;
  removeNode: (id: string) => void;
  addEdge: (e: AdjacencyEdge) => void;
  updateEdge: (a: string, b: string, patch: Partial<AdjacencyEdge>) => void;
  removeEdge: (a: string, b: string) => void;
  setNodes: (nodes: RoomNode[], source?: ProgramGraph['source']) => void;
  setEntry: (patch: Partial<NonNullable<ProgramGraph['entry']>>) => void;
  loadDoc: (doc: ProgramGraph) => void;
  loadState: (s: ProgramState) => void;
}

let counter = 0;

export const useProgram = create<ProgramStore>((set) => ({
  source: 'graph',
  nodes: [],
  edges: [],

  addNode: () =>
    set((s) => {
      counter += 1;
      const id = `room-${counter}`;
      return {
        nodes: [
          ...s.nodes,
          { id, type: 'bedroom', label: `Room ${counter}`, area_target_mm2: 10_000_000 },
        ],
        source: 'mixed',
      };
    }),
  updateNode: (id, patch) =>
    set((s) => ({
      nodes: s.nodes.map((n) => (n.id === id ? { ...n, ...patch } : n)),
      source: 'mixed',
    })),
  removeNode: (id) =>
    set((s) => ({
      nodes: s.nodes.filter((n) => n.id !== id),
      edges: s.edges.filter((e) => e.a !== id && e.b !== id),
      source: 'mixed',
    })),
  addEdge: (e) =>
    set((s) => {
      if (e.a === e.b) return s;
      const exists = s.edges.some(
        (x) => (x.a === e.a && x.b === e.b) || (x.a === e.b && x.b === e.a),
      );
      return exists ? s : { edges: [...s.edges, e], source: 'mixed' };
    }),
  updateEdge: (a, b, patch) =>
    set((s) => ({
      edges: s.edges.map((e) => (e.a === a && e.b === b ? { ...e, ...patch } : e)),
    })),
  removeEdge: (a, b) => set((s) => ({ edges: s.edges.filter((e) => !(e.a === a && e.b === b)) })),
  setNodes: (nodes, source = 'mixed') => set({ nodes, source }),
  setEntry: (patch) =>
    set((s) => {
      const next = { exterior_doors: 1, ...s.entry, ...patch };
      // drop empty optional keys so the doc stays clean
      if (!next.entry_node_id) delete next.entry_node_id;
      if (!next.entry_side || next.entry_side === 'any') delete next.entry_side;
      return { entry: next, source: 'mixed' };
    }),
  loadDoc: (doc) => set(programToState(doc)),
  loadState: (st) => set(st),
}));
