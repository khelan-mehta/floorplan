import { create } from 'zustand';
import type { Pt, Setbacks } from '@fpg/geometry-core';
import {
  type BoundaryEditorState,
  type EditorLevel,
  type EditorSite,
  emptyLevel,
} from './boundary-model';

export type BoundaryTool = 'select' | 'draw-outline' | 'draw-parcel';

/** The slice of state that undo/redo restores (geometry + site + orientation). */
interface Snapshot {
  levels: EditorLevel[];
  northAngleDeg: number;
  site: EditorSite | null;
}

interface BoundaryStore extends BoundaryEditorState {
  selectedLevel: number;
  selectedVertex: number | null;
  tool: BoundaryTool;
  gridMm: number;
  ortho: boolean;
  snap: boolean;
  draft: Pt[];
  past: Snapshot[];
  future: Snapshot[];

  setTool: (t: BoundaryTool) => void;
  setGrid: (mm: number) => void;
  toggleOrtho: () => void;
  toggleSnap: () => void;
  setNorth: (deg: number) => void;

  selectLevel: (i: number) => void;
  addLevel: () => void;
  removeLevel: (i: number) => void;
  updateLevelMeta: (i: number, patch: Partial<EditorLevel>) => void;
  setOutline: (i: number, points: Pt[]) => void;
  clearOutline: (i: number) => void;
  moveVertex: (i: number, idx: number, p: Pt) => void;
  deleteVertex: (i: number, idx: number) => void;
  insertVertex: (i: number, idx: number, p: Pt) => void;
  selectVertex: (idx: number | null) => void;

  setSite: (site: EditorSite | null) => void;
  setSetbacks: (s: Setbacks) => void;

  pushDraft: (p: Pt) => void;
  popDraft: () => void;
  clearDraft: () => void;
  commitDraft: () => void;

  beginHistory: () => void;
  undo: () => void;
  redo: () => void;

  loadState: (s: BoundaryEditorState) => void;
}

const DEFAULT_SETBACKS: Setbacks = { front_mm: 3000, rear_mm: 3000, left_mm: 3000, right_mm: 3000 };
const HISTORY_LIMIT = 100;

const snap = (s: BoundaryEditorState): Snapshot => ({
  levels: s.levels,
  northAngleDeg: s.northAngleDeg,
  site: s.site,
});

export const useBoundary = create<BoundaryStore>((set, get) => {
  /** Apply a state change, recording the prior snapshot for undo (and clearing the redo stack). */
  const withHistory = (patch: Partial<BoundaryStore>) =>
    set((s) => ({
      past: [...s.past, snap(s)].slice(-HISTORY_LIMIT),
      future: [],
      ...patch,
    }));

  const mapLevel = (i: number, fn: (l: EditorLevel) => EditorLevel) =>
    get().levels.map((l) => (l.index === i ? fn(l) : l));

  return {
    levels: [emptyLevel(0)],
    northAngleDeg: 0,
    site: null,
    selectedLevel: 0,
    selectedVertex: null,
    tool: 'draw-outline',
    gridMm: 100,
    ortho: true,
    snap: true,
    draft: [],
    past: [],
    future: [],

    setTool: (tool) => set({ tool, draft: [], selectedVertex: null }),
    setGrid: (gridMm) => set({ gridMm }),
    toggleOrtho: () => set((s) => ({ ortho: !s.ortho })),
    toggleSnap: () => set((s) => ({ snap: !s.snap })),
    setNorth: (northAngleDeg) => withHistory({ northAngleDeg }),

    selectLevel: (selectedLevel) => set({ selectedLevel, draft: [], selectedVertex: null }),
    addLevel: () =>
      withHistory({
        levels: [...get().levels, emptyLevel(get().levels.length)],
        selectedLevel: get().levels.length,
      }),
    removeLevel: (i) => {
      const levels = get()
        .levels.filter((l) => l.index !== i)
        .map((l, n) => ({ ...l, index: n }));
      withHistory({ levels: levels.length ? levels : [emptyLevel(0)], selectedLevel: 0 });
    },
    updateLevelMeta: (i, patch) =>
      withHistory({ levels: mapLevel(i, (l) => ({ ...l, ...patch })) }),
    setOutline: (i, points) =>
      withHistory({ levels: mapLevel(i, (l) => ({ ...l, outline: points })) }),
    clearOutline: (i) =>
      withHistory({ levels: mapLevel(i, (l) => ({ ...l, outline: [] })), selectedVertex: null }),
    moveVertex: (i, idx, p) =>
      // No history push here — beginHistory() is called once at drag start.
      set((s) => ({
        levels: s.levels.map((l) =>
          l.index === i ? { ...l, outline: l.outline.map((v, n) => (n === idx ? p : v)) } : l,
        ),
      })),
    deleteVertex: (i, idx) => {
      const lvl = get().levels.find((l) => l.index === i);
      if (!lvl || lvl.outline.length <= 3) return; // a polygon needs >= 3 vertices
      withHistory({
        levels: mapLevel(i, (l) => ({ ...l, outline: l.outline.filter((_, n) => n !== idx) })),
        selectedVertex: null,
      });
    },
    insertVertex: (i, idx, p) =>
      withHistory({
        levels: mapLevel(i, (l) => {
          const next = [...l.outline];
          next.splice(idx + 1, 0, p);
          return { ...l, outline: next };
        }),
      }),
    selectVertex: (selectedVertex) => set({ selectedVertex }),

    setSite: (site) => withHistory({ site }),
    setSetbacks: (setbacks) =>
      withHistory({
        site: get().site ? { ...get().site!, setbacks } : { parcel: [], setbacks },
      }),

    pushDraft: (p) => set((s) => ({ draft: [...s.draft, p] })),
    popDraft: () => set((s) => ({ draft: s.draft.slice(0, -1) })),
    clearDraft: () => set({ draft: [] }),
    commitDraft: () => {
      const s = get();
      if (s.draft.length < 3) {
        set({ draft: [] });
        return;
      }
      if (s.tool === 'draw-parcel') {
        withHistory({
          site: { parcel: s.draft, setbacks: s.site?.setbacks ?? DEFAULT_SETBACKS },
          draft: [],
          tool: 'select',
        });
        return;
      }
      withHistory({
        levels: s.levels.map((l) => (l.index === s.selectedLevel ? { ...l, outline: s.draft } : l)),
        draft: [],
        tool: 'select',
      });
    },

    beginHistory: () =>
      set((s) => ({ past: [...s.past, snap(s)].slice(-HISTORY_LIMIT), future: [] })),
    undo: () =>
      set((s) => {
        const prev = s.past[s.past.length - 1];
        if (!prev) return {};
        return {
          past: s.past.slice(0, -1),
          future: [snap(s), ...s.future].slice(0, HISTORY_LIMIT),
          ...prev,
          selectedVertex: null,
        };
      }),
    redo: () =>
      set((s) => {
        const next = s.future[0];
        if (!next) return {};
        return {
          future: s.future.slice(1),
          past: [...s.past, snap(s)].slice(-HISTORY_LIMIT),
          ...next,
          selectedVertex: null,
        };
      }),

    loadState: (st) =>
      set({
        ...st,
        selectedLevel: 0,
        selectedVertex: null,
        draft: [],
        tool: 'select',
        past: [],
        future: [],
      }),
  };
});
