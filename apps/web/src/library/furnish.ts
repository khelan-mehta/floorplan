// Auto-furnish a room: deterministic placement of the room type's default components inside its
// bounds. Simple row-packing along the room; clearance-aware solving is a follow-up (Phase 13+).

import type { Fixture, Room } from '@fpg/schemas';
import { CATALOG_BY_ID, ROOM_FURNITURE } from './catalog';

const MARGIN = 200; // mm from walls
const GAP = 200; // mm between items

function bbox(points: number[][]): { minX: number; minY: number; maxX: number; maxY: number } {
  const xs = points.map((p) => p[0]!);
  const ys = points.map((p) => p[1]!);
  return {
    minX: Math.min(...xs),
    minY: Math.min(...ys),
    maxX: Math.max(...xs),
    maxY: Math.max(...ys),
  };
}

/** Standard ray-casting point-in-polygon test for a closed ring of `[x, y]` points. */
export function pointInPolygon(pt: [number, number], ring: number[][]): boolean {
  const [x, y] = pt;
  let inside = false;
  for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
    const [xi, yi] = ring[i]!;
    const [xj, yj] = ring[j]!;
    if (yi === undefined || yj === undefined || xi === undefined || xj === undefined) continue;
    const intersects = yi > y !== yj > y && x < ((xj - xi) * (y - yi)) / (yj - yi) + xi;
    if (intersects) inside = !inside;
  }
  return inside;
}

/** Total floor area (mm²) covered by the given fixtures' footprints (rotation doesn't change a
 * rectangle's area, so `rot_z_deg` can be ignored). */
export function furnitureFootprintMm2(fixtures: Fixture[]): number {
  return fixtures.reduce((sum, f) => {
    const def = CATALOG_BY_ID[f.component_id];
    if (!def) return sum;
    const [w, d] = def.size_mm;
    return sum + w * d;
  }, 0);
}

/** Produce fixtures for a room (replaces any existing auto fixtures for that room). */
export function autoFurnish(room: Room): Fixture[] {
  const ids = ROOM_FURNITURE[room.type] ?? [];
  const b = bbox(room.polygon.rings[0]!.points);
  const usableW = b.maxX - b.minX - 2 * MARGIN;

  const fixtures: Fixture[] = [];
  let cursorX = b.minX + MARGIN;
  let rowY = b.minY + MARGIN;
  let rowDepth = 0;

  ids.forEach((componentId, i) => {
    const def = CATALOG_BY_ID[componentId];
    if (!def) return;
    const [w, d] = def.size_mm;
    if (w > usableW) return; // doesn't fit the room at all
    if (cursorX + w > b.maxX - MARGIN) {
      // wrap to a new row
      cursorX = b.minX + MARGIN;
      rowY += rowDepth + GAP;
      rowDepth = 0;
    }
    if (rowY + d > b.maxY - MARGIN) return; // out of vertical space
    const cx = cursorX + w / 2;
    const cy = rowY + d / 2;
    const outer = room.polygon.rings[0]!.points;
    const holes = room.polygon.rings.slice(1);
    if (!pointInPolygon([cx, cy], outer)) return; // outside the room outline (e.g. L-shaped room)
    if (holes.some((hole) => pointInPolygon([cx, cy], hole.points))) return; // inside a hole
    fixtures.push({
      id: `fx-${room.id}-${i}`,
      component_id: componentId,
      room_id: room.id,
      transform: { pos: [Math.round(cx), Math.round(cy), 0], rot_z_deg: 0 },
    });
    cursorX += w + GAP;
    rowDepth = Math.max(rowDepth, d);
  });

  return fixtures;
}
