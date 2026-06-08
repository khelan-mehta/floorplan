import * as XLSX from 'xlsx';
import type { RoomNode } from '@fpg/schemas';

const mm2ToM2 = (mm2?: number) => (mm2 ? +(mm2 / 1_000_000).toFixed(2) : '');

function workbookFromRows(rows: Record<string, unknown>[], sheetName = 'Area Program'): Blob {
  const ws = XLSX.utils.json_to_sheet(rows);
  const wb = XLSX.utils.book_new();
  XLSX.utils.book_append_sheet(wb, ws, sheetName);
  const out = XLSX.write(wb, { type: 'array', bookType: 'xlsx' }) as ArrayBuffer;
  return new Blob([out], {
    type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
  });
}

/** Export the current program as an area-program workbook. */
export function exportProgramWorkbook(nodes: RoomNode[]): Blob {
  const rows = nodes.map((n) => ({
    Department: n.department ?? '',
    'Room Name': n.label ?? '',
    Type: n.type,
    Qty: n.count ?? 1,
    'Target Area (m2)': mm2ToM2(n.area_target_mm2),
    'Min Area (m2)': mm2ToM2(n.area_min_mm2),
  }));
  return workbookFromRows(rows);
}

/** A blank template workbook with the expected columns + one example row. */
export function templateWorkbook(): Blob {
  return workbookFromRows([
    {
      Department: 'Private',
      'Room Name': 'Master Bedroom',
      Type: 'master_bedroom',
      Qty: 1,
      'Target Area (m2)': 14,
      'Min Area (m2)': 9,
    },
  ]);
}

export function downloadBlob(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}
