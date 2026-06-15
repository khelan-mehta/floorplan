import { create } from 'zustand';

export type ViewMode = '2d' | '3d';
export type ToolMode = 'select' | 'pan';

export interface Selection {
  kind: 'room' | 'wall' | 'opening' | 'fixture' | null;
  id: string | null;
}

interface EditorState {
  viewMode: ViewMode;
  selectedLevel: number;
  toolMode: ToolMode;
  selection: Selection;
  showCirculation: boolean;
  showSunlight: boolean;
  // Undo/redo scaffold (command stacks wired in Phase 10/13).
  undoStack: string[];
  redoStack: string[];

  setViewMode: (m: ViewMode) => void;
  setSelectedLevel: (i: number) => void;
  setToolMode: (m: ToolMode) => void;
  select: (kind: Selection['kind'], id: string | null) => void;
  clearSelection: () => void;
  setShowCirculation: (v: boolean) => void;
  setShowSunlight: (v: boolean) => void;
}

export const useEditor = create<EditorState>((set) => ({
  viewMode: '2d',
  selectedLevel: 0,
  toolMode: 'select',
  selection: { kind: null, id: null },
  showCirculation: false,
  showSunlight: false,
  undoStack: [],
  redoStack: [],

  setViewMode: (viewMode) => set({ viewMode }),
  setSelectedLevel: (selectedLevel) => set({ selectedLevel }),
  setToolMode: (toolMode) => set({ toolMode }),
  select: (kind, id) => set({ selection: { kind, id } }),
  clearSelection: () => set({ selection: { kind: null, id: null } }),
  setShowCirculation: (showCirculation) => set({ showCirculation }),
  setShowSunlight: (showSunlight) => set({ showSunlight }),
}));
