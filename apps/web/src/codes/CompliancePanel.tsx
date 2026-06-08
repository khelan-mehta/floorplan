import { Badge } from '@fpg/ui';
import { useState } from 'react';
import type { ValidationReport } from '../api/types';

const SEVERITY_TONE = { error: 'danger', warning: 'warn', info: 'default' } as const;

/** Phase 07/09 — shows the active plan's code-compliance report (score + flagged rules). */
export function CompliancePanel({ report }: { report: ValidationReport }) {
  const [open, setOpen] = useState(true);
  const fails = report.results.filter((r) => r.status === 'fail');
  const passes = report.results.filter((r) => r.status === 'pass').length;
  const tone = report.score >= 80 ? 'ok' : report.score >= 50 ? 'warn' : 'danger';

  return (
    <div className="border-b border-line bg-panel text-sm">
      <button
        onClick={() => setOpen((o) => !o)}
        className="flex w-full items-center gap-2 px-3 py-2 text-left"
      >
        <span className="text-xs uppercase text-muted">Code compliance</span>
        <Badge tone={tone}>{report.score.toFixed(0)}/100</Badge>
        <span className="text-xs text-muted">
          {passes} passed · {fails.length} flagged · ruleset {report.ruleset_id}
        </span>
        <span className="ml-auto text-xs text-muted">{open ? '▾' : '▸'}</span>
      </button>
      {open && (
        <div className="max-h-44 overflow-y-auto px-3 pb-2">
          {fails.length === 0 ? (
            <p className="text-xs text-ok">All evaluated rules pass for this plan.</p>
          ) : (
            <ul className="flex flex-col gap-1">
              {fails.map((r) => (
                <li key={r.rule_id} className="flex items-start gap-2">
                  <Badge tone={SEVERITY_TONE[r.severity]}>{r.severity}</Badge>
                  <span className="text-xs text-fg">{r.message ?? r.rule_id}</span>
                </li>
              ))}
            </ul>
          )}
          <p className="mt-1.5 text-[10px] text-muted">
            Decision-support only — verify against the adopted code; not a legal compliance
            guarantee.
          </p>
        </div>
      )}
    </div>
  );
}
