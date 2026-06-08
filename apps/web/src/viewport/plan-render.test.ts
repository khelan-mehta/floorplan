import { describe, expect, it } from 'vitest';
import { demoPlan } from '../demo/plan';
import { getLevel, levelBBox, planLegend, ringToFlatPoints, roomColor } from './plan-render';

describe('plan-render helpers', () => {
  it('maps known room types to stable colors', () => {
    expect(roomColor('living')).toBe('#3b82f6');
    expect(roomColor('bedroom')).toBe('#10b981');
  });

  it('returns a deterministic fallback for unknown types', () => {
    expect(roomColor('unobtanium')).toBe(roomColor('unobtanium'));
  });

  it('computes the level bounding box from the demo plan', () => {
    const level = getLevel(demoPlan, 0)!;
    const bbox = levelBBox(level);
    expect(bbox.minX).toBe(0);
    expect(bbox.minY).toBe(0);
    expect(bbox.maxX).toBe(10000);
    expect(bbox.maxY).toBe(8000);
    expect(bbox.width).toBe(10000);
    expect(bbox.height).toBe(8000);
  });

  it('builds a legend with one entry per distinct room type', () => {
    const level = getLevel(demoPlan, 0)!;
    const legend = planLegend(level);
    expect(legend.map((e) => e.type).sort()).toEqual(['living', 'master_bedroom']);
  });

  it('flattens ring points for Konva', () => {
    expect(
      ringToFlatPoints([
        [0, 0],
        [1, 2],
      ]),
    ).toEqual([0, 0, 1, 2]);
  });
});
