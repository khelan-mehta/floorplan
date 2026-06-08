import { describe, expect, it } from 'vitest';

import {
  isBoundary,
  isPlan,
  isProgramGraph,
  isProject,
  isRuleSet,
  isValidationReport,
  validate,
  lintBoundary,
  lintPlan,
  lintPolygon,
  signedArea,
  isCCW,
  type Boundary,
  type Plan,
} from '../src/index';

import project from '../examples/project.example.json';
import boundaryRect from '../examples/boundary-rect.example.json';
import boundaryL from '../examples/boundary-lshape.example.json';
import boundaryTwo from '../examples/boundary-two-level.example.json';
import program from '../examples/program-2bed.example.json';
import plan from '../examples/plan-2bed.example.json';
import ruleset from '../examples/ruleset.example.json';
import rulesetGenericIbc from '../examples/ruleset-generic-ibc.example.json';
import report from '../examples/validation-report.example.json';

const cases: Array<[string, string, unknown, (d: unknown) => boolean]> = [
  ['project', 'project.schema.json', project, isProject],
  ['boundary-rect', 'boundary.schema.json', boundaryRect, isBoundary],
  ['boundary-lshape', 'boundary.schema.json', boundaryL, isBoundary],
  ['boundary-two-level', 'boundary.schema.json', boundaryTwo, isBoundary],
  ['program', 'program-graph.schema.json', program, isProgramGraph],
  ['plan', 'plan.schema.json', plan, isPlan],
  ['ruleset', 'ruleset.schema.json', ruleset, isRuleSet],
  ['ruleset-generic-ibc', 'ruleset.schema.json', rulesetGenericIbc, isRuleSet],
  ['validation-report', 'validation-report.schema.json', report, isValidationReport],
];

describe('fixtures validate against their schemas', () => {
  for (const [name, schemaId, data, guard] of cases) {
    it(`${name} is valid`, () => {
      const { valid, errors } = validate(schemaId, data);
      if (!valid) console.error(name, errors);
      expect(valid).toBe(true);
      expect(guard(data)).toBe(true);
    });
  }
});

describe('round-trip (serialize -> parse -> revalidate -> deep-equal)', () => {
  for (const [name, schemaId, data] of cases) {
    it(`${name} round-trips`, () => {
      const round = JSON.parse(JSON.stringify(data));
      expect(validate(schemaId, round).valid).toBe(true);
      expect(round).toEqual(data);
    });
  }
});

describe('schema rejects malformed documents', () => {
  it('missing required field', () => {
    const bad = structuredClone(project) as Record<string, unknown>;
    delete bad.name;
    expect(validate('project.schema.json', bad).valid).toBe(false);
  });

  it('wrong schema_version const', () => {
    const bad = structuredClone(project) as Record<string, unknown>;
    bad.schema_version = 2;
    expect(validate('project.schema.json', bad).valid).toBe(false);
  });

  it('additional properties are rejected', () => {
    const bad = structuredClone(project) as Record<string, unknown>;
    bad.surprise = true;
    expect(validate('project.schema.json', bad).valid).toBe(false);
  });

  it('non-integer coordinate is rejected by schema', () => {
    const bad = structuredClone(boundaryRect) as Boundary;
    bad.levels[0]!.outline.rings[0]!.points[0] = [0.5, 0] as [number, number];
    expect(validate('boundary.schema.json', bad).valid).toBe(false);
  });
});

describe('geometry invariants', () => {
  it('a 10m x 8m rectangle measures 80 m² and is CCW', () => {
    const ring = (boundaryRect as Boundary).levels[0]!.outline.rings[0]!.points;
    expect(signedArea(ring)).toBe(80_000_000); // 80 m² in mm²
    expect(isCCW(ring)).toBe(true);
  });

  it('all example boundaries pass lintBoundary', () => {
    expect(lintBoundary(boundaryRect as Boundary)).toEqual([]);
    expect(lintBoundary(boundaryL as Boundary)).toEqual([]);
    expect(lintBoundary(boundaryTwo as Boundary)).toEqual([]);
  });

  it('the example plan passes lintPlan', () => {
    expect(lintPlan(plan as Plan)).toEqual([]);
  });

  it('flags a clockwise outer ring', () => {
    const cw = {
      rings: [
        {
          points: [
            [0, 0],
            [0, 8000],
            [10000, 8000],
            [10000, 0],
          ] as [number, number][],
        },
      ],
    };
    const issues = lintPolygon(cw, '/test');
    expect(issues.some((i) => i.code === 'outer_not_ccw')).toBe(true);
  });

  it('flags a self-intersecting (bowtie) ring', () => {
    const bowtie = {
      rings: [
        {
          points: [
            [0, 0],
            [10000, 10000],
            [10000, 0],
            [0, 10000],
          ] as [number, number][],
        },
      ],
    };
    const issues = lintPolygon(bowtie, '/test');
    expect(issues.some((i) => i.code === 'self_intersection')).toBe(true);
  });
});
