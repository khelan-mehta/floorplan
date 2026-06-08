import { describe, expect, it } from 'vitest';
import type { Room } from '@fpg/schemas';
import { CATALOG_BY_ID } from './catalog';
import { autoFurnish } from './furnish';

function room(type: string): Room {
  return {
    id: `room-${type}`,
    type,
    polygon: {
      rings: [
        {
          points: [
            [0, 0],
            [5000, 0],
            [5000, 4000],
            [0, 4000],
          ],
        },
      ],
    },
    area_mm2: 20_000_000,
    centroid: [2500, 2000],
  };
}

describe('autoFurnish', () => {
  it('places a bed in a bedroom', () => {
    const fx = autoFurnish(room('master_bedroom'));
    expect(fx.some((f) => f.component_id === 'bed-double')).toBe(true);
  });

  it('places toilet and basin in a bathroom', () => {
    const fx = autoFurnish(room('bathroom'));
    const ids = fx.map((f) => f.component_id);
    expect(ids).toContain('toilet');
    expect(ids).toContain('basin');
  });

  it('keeps fixtures within the room bounds', () => {
    const fx = autoFurnish(room('living'));
    for (const f of fx) {
      const def = CATALOG_BY_ID[f.component_id]!;
      const [x, y] = f.transform.pos;
      expect(x - def.size_mm[0] / 2).toBeGreaterThanOrEqual(0);
      expect(x + def.size_mm[0] / 2).toBeLessThanOrEqual(5000);
      expect(y - def.size_mm[1] / 2).toBeGreaterThanOrEqual(0);
      expect(y + def.size_mm[1] / 2).toBeLessThanOrEqual(4000);
    }
  });

  it('is deterministic', () => {
    expect(autoFurnish(room('office'))).toEqual(autoFurnish(room('office')));
  });
});
