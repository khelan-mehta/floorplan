import { describe, expect, it } from 'vitest';
import { applyMapping } from './excel-import';
import { adjacencyMatrix, budget, contradictions } from './program-model';
import { inferRoomType } from './room-type-infer';
import type { AdjacencyEdge, RoomNode } from '@fpg/schemas';

describe('room type inference', () => {
  it('maps synonyms to canonical types', () => {
    expect(inferRoomType('WC').type).toBe('wc');
    expect(inferRoomType('Master Bedroom').type).toBe('master_bedroom');
    expect(inferRoomType('Mtg Rm').type).toBe('meeting');
    expect(inferRoomType('Lounge').type).toBe('living');
  });
  it('falls back to a slug for unknown types', () => {
    const r = inferRoomType('Zorblax Chamber');
    expect(r.known).toBe(false);
    expect(r.type).toBe('zorblax_chamber');
  });
});

describe('excel applyMapping', () => {
  const rows = [
    { Name: 'Bedroom', Qty: 3, Area: 12 },
    { Name: 'Kitchen', Qty: 1, Area: 10 },
    { Name: '', Qty: 1, Area: 5 },
  ];
  const map = { label: 'Name', count: 'Qty', area_target: 'Area' };

  it('expands quantities and converts m² to mm²', () => {
    const res = applyMapping(rows, map, 'm2');
    expect(res.nodes).toHaveLength(4); // 3 bedrooms + 1 kitchen
    expect(res.skipped).toBe(1);
    const bed = res.nodes.find((n) => n.type === 'bedroom');
    expect(bed?.area_target_mm2).toBe(12_000_000);
    // unique ids
    expect(new Set(res.nodes.map((n) => n.id)).size).toBe(4);
  });

  it('converts ft² to mm²', () => {
    const res = applyMapping(
      [{ Name: 'Office', Area: 100 }],
      { label: 'Name', area_target: 'Area' },
      'ft2',
    );
    expect(res.nodes[0]?.area_target_mm2).toBe(Math.round(100 * 92903.04));
  });
});

describe('program analysis', () => {
  const nodes: RoomNode[] = [
    { id: 'a', type: 'bedroom', area_target_mm2: 10_000_000, count: 2 },
    { id: 'b', type: 'kitchen', area_target_mm2: 12_000_000 },
  ];

  it('sums the space budget with counts and flags over-budget', () => {
    const b = budget(nodes, 30_000_000);
    expect(b.usedMm2).toBe(32_000_000);
    expect(b.over).toBe(true);
  });

  it('builds a symmetric adjacency matrix', () => {
    const edges: AdjacencyEdge[] = [{ a: 'a', b: 'b', relation: 'adjacent' }];
    const m = adjacencyMatrix(nodes, edges);
    expect(m.cells[0]?.[1]).toBe('adjacent');
    expect(m.cells[1]?.[0]).toBe('adjacent');
  });

  it('detects adjacent + not_adjacent contradictions', () => {
    const edges: AdjacencyEdge[] = [
      { a: 'a', b: 'b', relation: 'adjacent' },
      { a: 'b', b: 'a', relation: 'not_adjacent' },
    ];
    expect(contradictions(edges)).toHaveLength(1);
  });
});
