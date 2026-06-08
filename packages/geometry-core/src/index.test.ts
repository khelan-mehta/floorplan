import { describe, expect, it } from 'vitest';
import {
  type Pt,
  bbox,
  ensureCCW,
  pointInPolygon,
  polygonArea,
  setbackEnvelope,
  signedArea,
  snapAngle,
  snapToGrid,
} from './index';

const rect: Pt[] = [
  [0, 0],
  [10000, 0],
  [10000, 8000],
  [0, 8000],
];

describe('geometry-core', () => {
  it('snaps to grid', () => {
    expect(snapToGrid([1234, 5678], 100)).toEqual([1200, 5700]);
  });

  it('snaps angle to 45° steps keeping length', () => {
    const p = snapAngle([0, 0], [1000, 100], 45);
    expect(p[1]).toBe(0); // nearly-horizontal snaps to 0°
  });

  it('computes area and bbox', () => {
    expect(polygonArea(rect)).toBe(80_000_000);
    expect(bbox(rect)).toMatchObject({ width: 10000, height: 8000 });
  });

  it('orients rings CCW', () => {
    const cw = [...rect].reverse();
    expect(signedArea(ensureCCW(cw))).toBeGreaterThan(0);
  });

  it('point in polygon', () => {
    expect(pointInPolygon([5000, 4000], rect)).toBe(true);
    expect(pointInPolygon([-1, -1], rect)).toBe(false);
  });

  it('insets a parcel by setbacks', () => {
    const env = setbackEnvelope(rect, {
      front_mm: 1000,
      rear_mm: 1000,
      left_mm: 2000,
      right_mm: 2000,
    });
    expect(env).toEqual([
      [2000, 1000],
      [8000, 1000],
      [8000, 7000],
      [2000, 7000],
    ]);
  });

  it('returns null when setbacks consume the parcel', () => {
    expect(
      setbackEnvelope(rect, { front_mm: 5000, rear_mm: 5000, left_mm: 0, right_mm: 0 }),
    ).toBeNull();
  });
});
