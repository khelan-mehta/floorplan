import * as XLSX from 'xlsx';
import type { RoomNode } from '@fpg/schemas';
import { inferRoomType, slugify } from './room-type-infer';

export type AreaUnit = 'm2' | 'ft2';

export interface ColumnMap {
  label?: string;
  type?: string;
  count?: string;
  area_target?: string;
  area_min?: string;
  department?: string;
  level?: string;
  occupancy?: string;
}

export interface ParsedSheet {
  sheetName: string;
  headers: string[];
  rows: Record<string, string | number>[];
}

export async function parseSpreadsheet(file: File): Promise<ParsedSheet> {
  const buf = await file.arrayBuffer();
  const wb = XLSX.read(buf, { type: 'array' });
  const sheetName = wb.SheetNames[0] ?? '';
  const ws = wb.Sheets[sheetName];
  if (!ws) return { sheetName, headers: [], rows: [] };
  const aoa = XLSX.utils.sheet_to_json<(string | number)[]>(ws, { header: 1, blankrows: false });
  const headers = (aoa[0] ?? []).map((h) => String(h));
  const rows = aoa.slice(1).map((arr) => {
    const obj: Record<string, string | number> = {};
    headers.forEach((h, i) => (obj[h] = (arr[i] ?? '') as string | number));
    return obj;
  });
  return { sheetName, headers, rows };
}

const HEADER_HINTS: Record<keyof ColumnMap, RegExp> = {
  label: /name|room|space/i,
  type: /type|category|use/i,
  count: /qty|count|quantity|no\.?|number/i,
  area_target: /target.*area|area.*target|area|sqm|sq m|m2|ft2/i,
  area_min: /min.*area|area.*min/i,
  department: /dept|department|zone|group/i,
  level: /level|floor|storey/i,
  occupancy: /occup|persons|people|seats/i,
};

export function autoDetectMapping(headers: string[]): ColumnMap {
  const map: ColumnMap = {};
  for (const key of Object.keys(HEADER_HINTS) as (keyof ColumnMap)[]) {
    const hint = HEADER_HINTS[key];
    const found = headers.find((h) => hint.test(h));
    if (found) map[key] = found;
  }
  return map;
}

const FT2_TO_MM2 = 92903.04;

function toMm2(value: number, unit: AreaUnit): number {
  return Math.round(value * (unit === 'm2' ? 1_000_000 : FT2_TO_MM2));
}

export interface ImportResult {
  nodes: RoomNode[];
  unmatched: number; // rows whose type was inferred via slug fallback
  skipped: number; // rows with no label/type
}

export function applyMapping(
  rows: Record<string, string | number>[],
  map: ColumnMap,
  unit: AreaUnit,
): ImportResult {
  const nodes: RoomNode[] = [];
  const idCounts = new Map<string, number>();
  let unmatched = 0;
  let skipped = 0;

  for (const row of rows) {
    const labelRaw = map.label ? String(row[map.label] ?? '').trim() : '';
    const typeRaw = map.type ? String(row[map.type] ?? '').trim() : '';
    const source = typeRaw || labelRaw;
    if (!source) {
      skipped++;
      continue;
    }
    const inferred = inferRoomType(source);
    if (!inferred.known) unmatched++;

    const count = map.count ? Math.max(1, Math.round(Number(row[map.count]) || 1)) : 1;
    const areaTarget = map.area_target ? Number(row[map.area_target]) || 0 : 0;
    const areaMin = map.area_min ? Number(row[map.area_min]) || 0 : 0;
    const department = map.department ? String(row[map.department] ?? '').trim() : undefined;
    const occupancy = map.occupancy ? Number(row[map.occupancy]) || undefined : undefined;

    const base = slugify(labelRaw || inferred.type) || inferred.type;
    for (let i = 0; i < count; i++) {
      const n = (idCounts.get(base) ?? 0) + 1;
      idCounts.set(base, n);
      const node: RoomNode = {
        id: count > 1 || n > 1 ? `${base}-${n}` : base,
        type: inferred.type,
        label: count > 1 ? `${labelRaw || inferred.type} ${i + 1}` : labelRaw || undefined,
      };
      if (areaTarget > 0) node.area_target_mm2 = toMm2(areaTarget, unit);
      if (areaMin > 0) node.area_min_mm2 = toMm2(areaMin, unit);
      if (department) node.department = department;
      if (occupancy) node.occupancy = occupancy;
      nodes.push(node);
    }
  }
  return { nodes, unmatched, skipped };
}
