import Ajv2020, { type ErrorObject, type ValidateFunction } from 'ajv/dist/2020';
import addFormats from 'ajv-formats';
import { schemas } from '../gen/ts/schemas';
import type {
  Boundary,
  Plan,
  Project,
  ProgramGraph,
  RuleSet,
  ValidationReport,
} from '../gen/ts/types';

const ajv = new Ajv2020({ strict: true, allErrors: true });
addFormats(ajv);
// `tsType` is a json-schema-to-typescript vendor extension; register it so strict mode accepts it.
ajv.addKeyword({ keyword: 'tsType' });

for (const [id, schema] of Object.entries(schemas)) {
  if (!ajv.getSchema(id)) ajv.addSchema(schema, id);
}

export interface ValidationResult {
  valid: boolean;
  errors: ErrorObject[];
}

function getValidator(schemaId: string): ValidateFunction {
  const v = ajv.getSchema(schemaId);
  if (!v) throw new Error(`Unknown schema id: ${schemaId}`);
  return v as ValidateFunction;
}

/** Validate `data` against the schema registered under `schemaId` (e.g. "project.schema.json"). */
export function validate(schemaId: string, data: unknown): ValidationResult {
  const v = getValidator(schemaId);
  const valid = v(data) === true;
  return { valid, errors: valid ? [] : (v.errors ?? []) };
}

/** Throw a descriptive error if `data` does not conform to `schemaId`. */
export function assertValid(schemaId: string, data: unknown): void {
  const { valid, errors } = validate(schemaId, data);
  if (!valid) {
    const detail = errors.map((e) => `${e.instancePath || '/'} ${e.message ?? ''}`).join('; ');
    throw new Error(`Validation failed for ${schemaId}: ${detail}`);
  }
}

export const isProject = (d: unknown): d is Project => validate('project.schema.json', d).valid;
export const isBoundary = (d: unknown): d is Boundary => validate('boundary.schema.json', d).valid;
export const isProgramGraph = (d: unknown): d is ProgramGraph =>
  validate('program-graph.schema.json', d).valid;
export const isPlan = (d: unknown): d is Plan => validate('plan.schema.json', d).valid;
export const isRuleSet = (d: unknown): d is RuleSet => validate('ruleset.schema.json', d).valid;
export const isValidationReport = (d: unknown): d is ValidationReport =>
  validate('validation-report.schema.json', d).valid;
