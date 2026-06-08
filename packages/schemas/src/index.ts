// @fpg/schemas — the canonical domain model.
// Types are generated from JSON Schema (run `pnpm codegen`); validators + geometry are hand-written
// wrappers over the generated outputs. Everything downstream imports from here.

export * from '../gen/ts/types';
export {
  validate,
  assertValid,
  isProject,
  isBoundary,
  isProgramGraph,
  isPlan,
  isRuleSet,
  isValidationReport,
  type ValidationResult,
} from './validate';
export {
  signedArea,
  isCCW,
  ringSelfIntersects,
  lintPolygon,
  lintBoundary,
  lintPlan,
  type GeometryIssue,
  type Point,
} from './geometry';
export { KNOWN_ROOM_TYPES, isKnownRoomType, type KnownRoomType } from './room-types';
export { schemas, schemaIds, rootEntities, type SchemaId } from '../gen/ts/schemas';
