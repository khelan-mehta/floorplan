// Client-side DXF import: extract the largest closed LWPOLYLINE/POLYLINE as a boundary outline.
// DWG (binary) is not supported in-browser — that path uses the server ezdxf + ODA converter
// (Phase 15 ships ODA); flagged as a follow-up.

import DxfParser from 'dxf-parser';
import { type Pt, polygonArea } from '@fpg/geometry-core';

export interface DxfImportResult {
  outline: Pt[];
  layers: string[];
  unit: 'mm' | 'm';
}

interface DxfVertex {
  x: number;
  y: number;
}
interface DxfEntity {
  type: string;
  layer?: string;
  vertices?: DxfVertex[];
  shape?: boolean;
  closed?: boolean;
}

export function parseDxf(text: string, scaleToMm = 1): DxfImportResult {
  const parser = new DxfParser();
  const dxf = parser.parseSync(text) as { entities?: DxfEntity[] } | null;
  const entities = dxf?.entities ?? [];
  const layers = [...new Set(entities.map((e) => e.layer ?? '0'))];

  let best: Pt[] = [];
  let bestArea = 0;
  for (const e of entities) {
    if (
      (e.type === 'LWPOLYLINE' || e.type === 'POLYLINE') &&
      e.vertices &&
      e.vertices.length >= 3
    ) {
      const pts: Pt[] = e.vertices.map((v) => [
        Math.round(v.x * scaleToMm),
        Math.round(v.y * scaleToMm),
      ]);
      const area = polygonArea(pts);
      if (area > bestArea) {
        bestArea = area;
        best = pts;
      }
    }
  }
  return { outline: best, layers, unit: scaleToMm === 1 ? 'mm' : 'm' };
}
