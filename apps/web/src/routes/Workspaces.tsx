import { Badge, Button, Spinner, toast } from '@fpg/ui';
import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { demoPlan } from '../demo/plan';
import { CompliancePanel } from '../codes/CompliancePanel';
import { useGenerate, usePlan, usePlans, useProject } from '../hooks/queries';
import { useJob } from '../hooks/useJob';
import type { PlanOut } from '../api/types';
import { Workspace } from '../workspace/Workspace';

/** Offline demo: renders the bundled example plan with no backend. */
export function DemoWorkspace() {
  return <Workspace plan={demoPlan} title="Demo Plan (offline)" canEdit={false} />;
}

/** Live project workspace: loads the project + its plans; lets you compare/open variants. */
export function ProjectWorkspace() {
  const { id } = useParams<{ id: string }>();
  const { data: project, isLoading } = useProject(id);
  const { data: plans } = usePlans(id);
  const generate = useGenerate(id ?? '');
  const { event } = useJob(generate.data?.id ?? null);

  const [selectedPlanId, setSelectedPlanId] = useState<string | null>(null);
  const activeId = selectedPlanId ?? project?.current_plan_id ?? plans?.[0]?.id;
  const { data: plan } = usePlan(activeId);

  useEffect(() => {
    if (event?.status === 'succeeded') toast.success('Plans generated');
    if (event?.status === 'failed') toast.error(event.error ?? 'Generation failed');
  }, [event]);

  if (isLoading) {
    return (
      <div className="flex h-full items-center justify-center gap-2 text-muted">
        <Spinner /> Loading project…
      </div>
    );
  }

  if (!plan) {
    return (
      <div className="flex h-full flex-col items-center justify-center gap-3">
        <p className="text-muted">No plans yet for this project.</p>
        <Button
          variant="primary"
          disabled={generate.isPending}
          onClick={() => generate.mutate({ count: 6 })}
        >
          {generate.isPending ? 'Generating…' : 'Generate options'}
        </Button>
      </div>
    );
  }

  return (
    <div className="flex h-full flex-col">
      {plans && plans.length > 1 && (
        <VariantsBar plans={plans} activeId={activeId ?? ''} onSelect={setSelectedPlanId} />
      )}
      {plan.validation && <CompliancePanel report={plan.validation} />}
      <div className="min-h-0 flex-1">
        <Workspace
          plan={plan.doc}
          title={project?.name ?? 'Project'}
          canEdit
          generating={generate.isPending || event?.status === 'running'}
          onGenerate={() => generate.mutate({ count: 6 })}
        />
      </div>
    </div>
  );
}

/** Phase 14: a strip of generated variants, sorted by score, for quick comparison + open. */
function VariantsBar({
  plans,
  activeId,
  onSelect,
}: {
  plans: PlanOut[];
  activeId: string;
  onSelect: (id: string) => void;
}) {
  const sorted = [...plans].sort((a, b) => (b.score ?? 0) - (a.score ?? 0));
  return (
    <div className="flex items-center gap-2 overflow-x-auto border-b border-line bg-panel px-3 py-2">
      <span className="shrink-0 text-xs uppercase text-muted">Variants ({plans.length})</span>
      {sorted.map((p, i) => {
        const rooms = p.doc.levels.reduce((acc, l) => acc + l.rooms.length, 0);
        return (
          <button
            key={p.id}
            onClick={() => onSelect(p.id)}
            className={`shrink-0 rounded-md border px-3 py-1.5 text-left text-xs ${
              p.id === activeId ? 'border-accent bg-panel-2' : 'border-line hover:bg-panel-2'
            }`}
          >
            <div className="flex items-center gap-2">
              <span className="font-medium">Option {i + 1}</span>
              <Badge tone={(p.score ?? 0) >= 80 ? 'ok' : 'warn'}>{(p.score ?? 0).toFixed(0)}</Badge>
            </div>
            <div className="text-muted">
              {rooms} rooms · seed {p.seed ?? 0}
            </div>
          </button>
        );
      })}
    </div>
  );
}
