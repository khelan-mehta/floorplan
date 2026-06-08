// Pure model + helpers for the boundary editor. Editor state -> Phase-02 Boundary document.

import type { Boundary } from '@fpg/schemas';
import {
  type Pt,
  type Setbacks,
  bbox,
  ensureCCW,
  polygonArea,
  polygonPerimeter,
  setbackEnvelope,
} from '@fpg/geometry-core';

export interface EditorLevel {
  index: number;
  elevation_mm: number;
  floor_to_floor_mm: number;
  outline: Pt[]; // outer ring (open; closure implicit)
  holes: Pt[][];
}

export interface EditorSite {
  parcel: Pt[];
  setbacks: Setbacks;
}

export interface BoundaryEditorState {
  levels: EditorLevel[];
  northAngleDeg: number;
  site: EditorSite | null;
}

export function emptyLevel(index: number): EditorLevel {
  return {
    index,
    elevation_mm: index * 3000,
    floor_to_floor_mm: 3000,
    outline: [],
    holes: [],
  };
}

export function levelMetrics(level: EditorLevel): { area_mm2: number; perimeter_mm: number } {
  if (level.outline.length < 3) return { area_mm2: 0, perimeter_mm: 0 };
  const holesArea = level.holes.reduce((acc, h) => acc + polygonArea(h), 0);
  return {
    area_mm2: Math.max(0, polygonArea(level.outline) - holesArea),
    perimeter_mm: polygonPerimeter(level.outline),
  };
}

/** Buildable envelope rectangle (parcel inset by setbacks), or null. */
export function envelope(site: EditorSite | null): Pt[] | null {
  if (!site || site.parcel.length < 3) return null;
  return setbackEnvelope(site.parcel, site.setbacks);
}

export interface BoundaryIssue {
  level?: number;
  message: string;
}

export function validate(state: BoundaryEditorState): BoundaryIssue[] {
  const issues: BoundaryIssue[] = [];
  if (state.levels.length === 0) issues.push({ message: 'Add at least one level.' });
  for (const lvl of state.levels) {
    if (lvl.outline.length < 3) {
      issues.push({ level: lvl.index, message: 'Outline needs at least 3 points.' });
      continue;
    }
    if (polygonArea(lvl.outline) <= 0) {
      issues.push({ level: lvl.index, message: 'Outline has zero area.' });
    }
    if (lvl.floor_to_floor_mm <= 0) {
      issues.push({ level: lvl.index, message: 'Floor-to-floor must be positive.' });
    }
  }
  if (state.site && envelope(state.site) === null) {
    issues.push({ message: 'Setbacks consume the entire parcel.' });
  }
  return issues;
}

function ringDoc(points: Pt[]): { points: Pt[] } {
  return { points: ensureCCW(points).map((p) => [Math.round(p[0]), Math.round(p[1])]) as Pt[] };
}

function holeDoc(points: Pt[]): { points: Pt[] } {
  // holes must be CW => reverse the CCW orientation
  const ccw = ensureCCW(points);
  return { points: [...ccw].reverse().map((p) => [Math.round(p[0]), Math.round(p[1])]) as Pt[] };
}

/** Convert editor state into a schema-valid Boundary document.
 *  Built as a plain structure and cast once — the schema's non-empty-tuple ring/level types are
 *  stricter than our runtime arrays; `validate()` + `lintBoundary()` enforce correctness at runtime. */
export function buildBoundaryDoc(state: BoundaryEditorState, id?: string): Boundary {
  const doc = {
    schema_version: 1 as const,
    id: id ?? crypto.randomUUID(),
    north_angle_deg: state.northAngleDeg,
    levels: state.levels.map((lvl) => ({
      index: lvl.index,
      elevation_mm: lvl.elevation_mm,
      floor_to_floor_mm: lvl.floor_to_floor_mm,
      outline: { rings: [ringDoc(lvl.outline), ...lvl.holes.map(holeDoc)] },
    })),
    ...(state.site && state.site.parcel.length >= 3
      ? {
          site: {
            parcel_polygon: { rings: [ringDoc(state.site.parcel)] },
            setbacks: state.site.setbacks,
          },
        }
      : {}),
  };
  return doc as unknown as Boundary;
}

/** Parse a stored Boundary doc back into editor state. */
export function boundaryToState(doc: Boundary): BoundaryEditorState {
  return {
    northAngleDeg: doc.north_angle_deg,
    levels: doc.levels.map((lvl) => ({
      index: lvl.index,
      elevation_mm: lvl.elevation_mm,
      floor_to_floor_mm: lvl.floor_to_floor_mm,
      outline: (lvl.outline.rings[0]?.points ?? []).map((p) => [p[0], p[1]] as Pt),
      holes: lvl.outline.rings.slice(1).map((r) => r.points.map((p) => [p[0], p[1]] as Pt)),
    })),
    site: doc.site
      ? {
          parcel: (doc.site.parcel_polygon.rings[0]?.points ?? []).map((p) => [p[0], p[1]] as Pt),
          setbacks: doc.site.setbacks,
        }
      : null,
  };
}

export { bbox };
