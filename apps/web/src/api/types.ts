import type { Boundary, Plan, ProgramGraph } from '@fpg/schemas';

export type { Boundary, Plan, ProgramGraph };

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface UserOut {
  id: string;
  email: string;
  name: string;
}

export interface ProjectOut {
  id: string;
  org_id: string;
  name: string;
  units: string;
  jurisdiction_id: string | null;
  boundary_id: string | null;
  program_id: string | null;
  current_plan_id: string | null;
  created_at: string;
  updated_at: string;
}

export interface PlanOut {
  id: string;
  project_id: string;
  parent_plan_id: string | null;
  source: string;
  seed: number | null;
  score: number | null;
  layout_score?: number | null;
  validation?: ValidationReport | null;
  doc: Plan;
  created_at: string;
}

// --- building codes (Phase 07) ---
export interface CodeCitation {
  doc: string;
  section: string;
  text: string;
}

export interface CodeQueryResult {
  section: string;
  heading: string;
  chapter: string;
  score: number;
  citation: CodeCitation;
}

export interface CodeQueryResponse {
  jurisdiction_id: string;
  query: string;
  results: CodeQueryResult[];
  disclaimer: string;
}

export interface RuleSetSummary {
  id: string;
  jurisdiction: string;
  version: string;
}

// --- validation report (Phase 09) ---
export interface ValidationResult {
  rule_id: string;
  status: 'pass' | 'fail' | 'na';
  severity: 'error' | 'warning' | 'info';
  message?: string;
  geometry_ref?: string;
  fix_hint?: string;
}

export interface ValidationReport {
  plan_id: string;
  ruleset_id: string;
  score: number;
  category_scores: Record<string, number>;
  results: ValidationResult[];
}

export interface JobOut {
  id: string;
  type: string;
  status: 'queued' | 'running' | 'succeeded' | 'failed';
  progress: number;
  result: { plan_ids?: string[] } | null;
  error: string | null;
  created_at: string;
}

export interface CritiqueOut extends PlanOut {
  notes: string;
  adjustments: {
    node_adjustments: Array<{
      id: string;
      area_delta_pct?: number;
      requires_window?: boolean;
      windows?: number;
    }>;
    edge_adjustments: Array<{ a: string; b: string; relation?: string; weight?: number }>;
    notes: string;
  };
}

export interface DiffOut {
  added: Record<string, unknown>;
  removed: Record<string, unknown>;
  changed: Record<string, unknown>;
}

export interface ProblemDetails {
  type: string;
  title: string;
  status: number;
  detail?: string;
  errors?: unknown;
}
