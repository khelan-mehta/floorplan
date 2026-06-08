import { describe, expect, it } from 'vitest';
import { demoPlan } from '../demo/plan';
import { getLevel } from './plan-render';
import { MM_TO_M, openings3D, roomSlabs, wallBoxes, wallSegments } from './plan-3d';

describe('plan-3d helpers', () => {
  const level = getLevel(demoPlan, 0)!;

  it('creates one wall box per wall with metre-scaled dimensions', () => {
    const boxes = wallBoxes(level);
    expect(boxes).toHaveLength(level.walls.length);
    const south = boxes.find((b) => b.id === 'w-s')!;
    // south wall runs 0..10000mm => 10m long, 2.7m tall, 0.2m thick
    expect(south.size[0]).toBeCloseTo(10);
    expect(south.size[1]).toBeCloseTo(2.7);
    expect(south.size[2]).toBeCloseTo(0.2);
  });

  it('creates room slabs scaled to metres', () => {
    const slabs = roomSlabs(level);
    expect(slabs).toHaveLength(2);
    const living = slabs.find((s) => s.id === 'room-living')!;
    expect(living.points[1]).toEqual([5000 * MM_TO_M, 0]);
    expect(living.color).toBe('#3b82f6');
  });

  it('segments walls around openings (more pieces than plain walls)', () => {
    // The demo has a door + a window, so the host walls split into solids + headers/sills.
    expect(wallSegments(level).length).toBeGreaterThan(wallBoxes(level).length);
  });

  it('emits a 3D opening per door/window with positive, metre-scaled dimensions', () => {
    const ops = openings3D(level);
    expect(ops).toHaveLength(level.openings.length);
    for (const o of ops) {
      expect(o.width).toBeGreaterThan(0);
      expect(o.height).toBeGreaterThan(0);
      expect(o.thickness).toBeGreaterThan(0);
    }
    // a window sits above the floor (sill), a door starts at the floor
    const win = ops.find((o) => o.kind === 'window')!;
    const door = ops.find((o) => o.kind === 'door')!;
    expect(win.center[1]).toBeGreaterThan(door.center[1]);
  });
});
