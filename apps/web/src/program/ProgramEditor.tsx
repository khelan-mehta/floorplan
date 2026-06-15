import { Badge, Button, Input, Tabs, TabsList, TabsTrigger, Toolbar, toast } from '@fpg/ui';
import { KNOWN_ROOM_TYPES, type ProgramGraph, validate as validateSchema } from '@fpg/schemas';
import { useEffect, useMemo, useRef, useState } from 'react';
import { downloadBlob, exportProgramWorkbook, templateWorkbook } from './excel-export';
import { ProgramGraphView } from './ProgramGraphView';
import { ProgramImportDialog } from './ProgramImportDialog';
import {
  TEMPLATES,
  adjacencyMatrix,
  budget,
  buildProgramDoc,
  contradictions,
} from './program-model';
import { useProgram } from './store';

export function ProgramEditor({
  projectId,
  availableMm2,
  initialDoc,
  onSaved,
}: {
  projectId: string;
  availableMm2: number;
  initialDoc?: ProgramGraph;
  onSaved?: () => void;
}) {
  const s = useProgram();
  const [tab, setTab] = useState('table');
  const [saving, setSaving] = useState(false);
  const loadedRef = useRef(false);
  const jsonRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (initialDoc && !loadedRef.current) {
      loadedRef.current = true;
      s.loadDoc(initialDoc);
    }
  }, [initialDoc, s]);

  // Import a full ProgramGraph JSON (rooms + adjacencies + entry config) — e.g. inputs/program-graph.json.
  const onImportJson = async (file: File) => {
    let doc: ProgramGraph;
    try {
      doc = JSON.parse(await file.text()) as ProgramGraph;
    } catch {
      toast.error('Could not parse JSON');
      return;
    }
    if (!validateSchema('program-graph.schema.json', doc).valid) {
      toast.error('Not a valid ProgramGraph document');
      return;
    }
    s.loadDoc(doc);
    toast.success(
      `Imported ${doc.nodes.length} rooms · ${doc.edges.length} adjacencies${doc.entry ? ' · entry config' : ''}`,
    );
  };

  const b = useMemo(() => budget(s.nodes, availableMm2), [s.nodes, availableMm2]);
  const conflicts = useMemo(() => contradictions(s.edges), [s.edges]);

  const onSave = async () => {
    if (conflicts.length) {
      toast.error(conflicts[0]?.message ?? 'Resolve contradictions first');
      return;
    }
    const doc = buildProgramDoc(s, initialDoc?.id);
    if (!validateSchema('program-graph.schema.json', doc).valid) {
      toast.error('Program failed schema validation');
      return;
    }
    setSaving(true);
    try {
      const { api } = await import('../api/client');
      await api.putProgram(projectId, doc);
      toast.success('Program saved');
      onSaved?.();
    } catch {
      toast.error('Could not save (is the API running?)');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="flex h-full flex-col">
      <Toolbar className="justify-between">
        <div className="flex items-center gap-2">
          <select
            className="h-8 rounded-md border border-line bg-panel-2 px-2 text-sm"
            defaultValue=""
            onChange={(e) => {
              const t = TEMPLATES[e.target.value];
              if (t) s.loadState(t);
            }}
          >
            <option value="">Templates…</option>
            {Object.keys(TEMPLATES).map((name) => (
              <option key={name} value={name}>
                {name}
              </option>
            ))}
          </select>
          <Button size="sm" variant="secondary" onClick={s.addNode}>
            + Room
          </Button>
          <ProgramImportDialog />
          <input
            ref={jsonRef}
            type="file"
            accept=".json,application/json"
            className="hidden"
            onChange={(e) => {
              const f = e.target.files?.[0];
              if (f) void onImportJson(f);
              e.target.value = '';
            }}
          />
          <Button size="sm" variant="secondary" onClick={() => jsonRef.current?.click()}>
            Import JSON
          </Button>
          <Button
            size="sm"
            variant="ghost"
            onClick={() => downloadBlob(exportProgramWorkbook(s.nodes), 'area-program.xlsx')}
          >
            Export
          </Button>
          <Button
            size="sm"
            variant="ghost"
            onClick={() => downloadBlob(templateWorkbook(), 'area-program-template.xlsx')}
          >
            Template
          </Button>
        </div>
        <div className="flex items-center gap-2">
          <Tabs value={tab} onValueChange={setTab}>
            <TabsList>
              <TabsTrigger value="table">Table</TabsTrigger>
              <TabsTrigger value="graph">Graph</TabsTrigger>
              <TabsTrigger value="matrix">Matrix</TabsTrigger>
            </TabsList>
          </Tabs>
          <Button size="sm" variant="primary" onClick={onSave} disabled={saving}>
            {saving ? 'Saving…' : 'Save program'}
          </Button>
        </div>
      </Toolbar>

      <BudgetBar b={b} />
      <EntryControls />

      <div className="min-h-0 flex-1 overflow-auto">
        {tab === 'table' && <ProgramTable />}
        {tab === 'graph' && <ProgramGraphView />}
        {tab === 'matrix' && <MatrixView />}
      </div>

      {conflicts.length > 0 && (
        <div className="border-t border-line bg-danger/10 px-3 py-1 text-xs text-danger">
          {conflicts.length} contradiction(s): {conflicts[0]?.message}
        </div>
      )}
    </div>
  );
}

/** Exterior entrance configuration consumed by the generator (Phase 08). */
function EntryControls() {
  const nodes = useProgram((s) => s.nodes);
  const entry = useProgram((s) => s.entry);
  const setEntry = useProgram((s) => s.setEntry);
  const doors = entry?.exterior_doors ?? 1;
  return (
    <div className="flex flex-wrap items-center gap-3 border-b border-line bg-panel px-3 py-1.5 text-xs">
      <span className="text-muted">🚪 Entrances</span>
      <label className="flex items-center gap-1">
        Exterior doors
        <input
          type="number"
          min={1}
          max={8}
          value={doors}
          onChange={(e) =>
            setEntry({ exterior_doors: Math.max(1, Math.min(8, Number(e.target.value) || 1)) })
          }
          className="h-7 w-14 rounded-md border border-line bg-panel-2 px-2"
        />
      </label>
      <label className="flex items-center gap-1">
        Main entry
        <select
          value={entry?.entry_node_id ?? ''}
          onChange={(e) => setEntry({ entry_node_id: e.target.value || undefined })}
          className="h-7 rounded-md border border-line bg-panel-2 px-2"
        >
          <option value="">Auto (pick best)</option>
          {nodes.map((n) => (
            <option key={n.id} value={n.id}>
              {n.label ?? n.type}
            </option>
          ))}
        </select>
      </label>
      <label className="flex items-center gap-1">
        Facing
        <select
          value={entry?.entry_side ?? 'any'}
          onChange={(e) =>
            setEntry({ entry_side: e.target.value as NonNullable<typeof entry>['entry_side'] })
          }
          className="h-7 rounded-md border border-line bg-panel-2 px-2"
        >
          {['any', 'north', 'south', 'east', 'west'].map((sd) => (
            <option key={sd} value={sd}>
              {sd}
            </option>
          ))}
        </select>
      </label>
      <span className="text-muted">
        The generator places {doors} door{doors > 1 ? 's' : ''} to the outside and routes
        circulation so every room is reachable.
      </span>
    </div>
  );
}

function BudgetBar({ b }: { b: ReturnType<typeof budget> }) {
  const pct = Math.min(100, Math.round(b.ratio * 100));
  return (
    <div className="flex items-center gap-3 border-b border-line bg-panel px-3 py-1.5 text-xs">
      <span className="text-muted">Space budget</span>
      <div className="h-2 w-48 overflow-hidden rounded-full bg-panel-2">
        <div className={`h-full ${b.over ? 'bg-danger' : 'bg-ok'}`} style={{ width: `${pct}%` }} />
      </div>
      <span>
        {(b.usedMm2 / 1_000_000).toFixed(1)} m² used
        {b.availableMm2 > 0 && ` / ${(b.availableMm2 / 1_000_000).toFixed(1)} m² available`}
      </span>
      {b.over && <Badge tone="danger">over budget</Badge>}
    </div>
  );
}

function ProgramTable() {
  const s = useProgram();
  return (
    <table className="w-full text-sm">
      <thead className="sticky top-0 bg-panel text-left text-xs uppercase text-muted">
        <tr>
          <th className="p-2">Department</th>
          <th className="p-2">Name</th>
          <th className="p-2">Type</th>
          <th className="p-2">Qty</th>
          <th className="p-2">Target m²</th>
          <th
            className="p-2"
            title="Number of windows. The generator auto-raises glazing to meet the code daylight minimum (≥8% of floor area)."
          >
            Windows
          </th>
          <th
            className="p-2"
            title="Window-to-wall ratio (% of exterior wall that is glazing). Auto-raised to satisfy code daylight."
          >
            Win/Wall&nbsp;%
          </th>
          <th className="p-2" />
        </tr>
      </thead>
      <tbody>
        {s.nodes.map((n) => (
          <tr key={n.id} className="border-t border-line">
            <td className="p-1">
              <Input
                value={n.department ?? ''}
                onChange={(e) => s.updateNode(n.id, { department: e.target.value || undefined })}
              />
            </td>
            <td className="p-1">
              <Input
                value={n.label ?? ''}
                onChange={(e) => s.updateNode(n.id, { label: e.target.value })}
              />
            </td>
            <td className="p-1">
              <input
                list="room-types"
                className="h-9 w-full rounded-md border border-line bg-panel-2 px-2 text-sm"
                value={n.type}
                onChange={(e) => s.updateNode(n.id, { type: e.target.value })}
              />
            </td>
            <td className="p-1 w-16">
              <Input
                type="number"
                value={n.count ?? 1}
                onChange={(e) => s.updateNode(n.id, { count: Math.max(1, Number(e.target.value)) })}
              />
            </td>
            <td className="p-1 w-24">
              <Input
                type="number"
                value={n.area_target_mm2 ? +(n.area_target_mm2 / 1_000_000).toFixed(1) : ''}
                onChange={(e) =>
                  s.updateNode(n.id, {
                    area_target_mm2: Math.round(Number(e.target.value) * 1_000_000),
                  })
                }
              />
            </td>
            <td className="w-16 p-1">
              <Input
                type="number"
                min={0}
                value={n.windows ?? ''}
                onChange={(e) =>
                  s.updateNode(n.id, {
                    windows:
                      e.target.value === '' ? undefined : Math.max(0, Number(e.target.value)),
                  })
                }
              />
            </td>
            <td className="w-16 p-1">
              <Input
                type="number"
                min={0}
                max={95}
                value={n.window_to_wall_ratio ? Math.round(n.window_to_wall_ratio * 100) : ''}
                onChange={(e) =>
                  s.updateNode(n.id, {
                    window_to_wall_ratio:
                      e.target.value === ''
                        ? undefined
                        : Math.min(0.95, Math.max(0, Number(e.target.value) / 100)),
                  })
                }
              />
            </td>
            <td className="p-1">
              <Button size="sm" variant="ghost" onClick={() => s.removeNode(n.id)}>
                ✕
              </Button>
            </td>
          </tr>
        ))}
      </tbody>
      <datalist id="room-types">
        {KNOWN_ROOM_TYPES.map((t) => (
          <option key={t} value={t} />
        ))}
      </datalist>
    </table>
  );
}

function MatrixView() {
  const nodes = useProgram((s) => s.nodes);
  const edges = useProgram((s) => s.edges);
  const updateEdge = useProgram((s) => s.updateEdge);
  const m = useMemo(() => adjacencyMatrix(nodes, edges), [nodes, edges]);
  const glyph: Record<string, string> = {
    adjacent: '▣',
    connected_door: '🚪',
    connected_open: '↔',
    near: '∼',
    not_adjacent: '✕',
  };
  return (
    <div className="overflow-auto p-3">
      <p className="mb-2 text-xs text-muted">
        Adjacency strength (0-100): how strongly two rooms should be placed near each other — e.g.
        dining ↔ kitchen = 90, kitchen ↔ laundry = 30.
      </p>
      <table className="text-xs">
        <thead>
          <tr>
            <th className="p-1" />
            {m.labels.map((l, i) => (
              <th key={m.ids[i]} className="max-w-[80px] truncate p-1 text-muted">
                {l}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {m.ids.map((id, r) => (
            <tr key={id}>
              <td className="whitespace-nowrap p-1 text-muted">{m.labels[r]}</td>
              {m.ids.map((cid, c) => {
                if (r === c)
                  return (
                    <td key={cid} className="p-1 text-center">
                      —
                    </td>
                  );
                const relation = m.cells[r]?.[c];
                if (!relation) return <td key={cid} className="p-1 text-center" />;
                const weight = m.weights[r]?.[c] ?? 50;
                return (
                  <td key={cid} className="p-1 text-center">
                    <div className="flex flex-col items-center gap-0.5">
                      <span title={relation}>{glyph[relation]}</span>
                      <input
                        type="number"
                        min={0}
                        max={100}
                        step={5}
                        value={weight}
                        title={`Adjacency strength ${id} ↔ ${cid} (0-100)`}
                        className="h-6 w-12 rounded border border-line bg-panel-2 px-1 text-center text-xs"
                        onChange={(e) => {
                          const v = Math.max(0, Math.min(100, Number(e.target.value)));
                          updateEdge(id, cid, { weight: v });
                          updateEdge(cid, id, { weight: v });
                        }}
                      />
                    </div>
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
