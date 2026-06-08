import {
  Badge,
  Button,
  Panel,
  Split,
  SplitHandle,
  SplitPane,
  Tabs,
  TabsList,
  TabsTrigger,
  Toolbar,
  Tooltip,
  toast,
} from '@fpg/ui';
import { KNOWN_ROOM_TYPES, type Plan } from '@fpg/schemas';
import { Box, Layers, Maximize2, Redo2, Save, Square, Undo2 } from 'lucide-react';
import { useEffect, useState } from 'react';
import { api } from '../api/client';
import { componentsForRoom } from '../library/catalog';
import { downloadBlob } from '../program/excel-export';
import { useEditor } from '../store/editor';
import { PlanCanvas2D } from '../viewport/PlanCanvas2D';
import { PlanScene3D, type CameraView } from '../viewport/PlanScene3D';
import { getLevel, planLegend } from '../viewport/plan-render';
import { usePlanEditor } from './planStore';

export interface WorkspaceProps {
  plan: Plan;
  title: string;
  canEdit?: boolean;
  onGenerate?: () => void;
  generating?: boolean;
}

export function Workspace({ plan, title, canEdit = true, onGenerate, generating }: WorkspaceProps) {
  const load = usePlanEditor((s) => s.load);
  const editPlan = usePlanEditor((s) => s.plan);

  useEffect(() => {
    load(plan);
  }, [plan, load]);

  const active = editPlan ?? plan;

  return (
    <div className="flex h-full flex-col bg-bg">
      <TopBar
        title={title}
        planId={plan.id}
        canEdit={canEdit}
        onGenerate={onGenerate}
        generating={generating}
      />
      <div className="min-h-0 flex-1">
        <Split>
          <SplitPane defaultSize={20} minSize={14}>
            <LeftPanel plan={active} />
          </SplitPane>
          <SplitHandle />
          <SplitPane defaultSize={58} minSize={30}>
            <Viewport plan={active} canEdit={canEdit} />
          </SplitPane>
          <SplitHandle />
          <SplitPane defaultSize={22} minSize={16}>
            <Inspector plan={active} canEdit={canEdit} />
          </SplitPane>
        </Split>
      </div>
      <StatusBar plan={active} />
    </div>
  );
}

function TopBar({
  title,
  planId,
  canEdit,
  onGenerate,
  generating,
}: {
  title: string;
  planId: string;
  canEdit: boolean;
  onGenerate?: () => void;
  generating?: boolean;
}) {
  const viewMode = useEditor((s) => s.viewMode);
  const setViewMode = useEditor((s) => s.setViewMode);
  const { undo, redo, canUndo, canRedo, dirty, plan, markSaved } = usePlanEditor();
  const [saving, setSaving] = useState(false);

  const save = async () => {
    if (!plan) return;
    setSaving(true);
    try {
      await api.patchPlan(plan.id, { levels: plan.levels }, 'edited');
      markSaved();
      toast.success('Saved as new version');
    } catch {
      toast.error('Save failed (is the API running?)');
    } finally {
      setSaving(false);
    }
  };

  const onExport = async (format: 'dxf' | 'ifc' | 'csv') => {
    try {
      const blob = await api.exportPlan(planId, format);
      downloadBlob(blob, `plan-${planId}.${format}`);
    } catch {
      toast.error(`Export (${format}) failed — needs the API + export service`);
    }
  };

  return (
    <Toolbar className="h-12 justify-between">
      <div className="flex items-center gap-2">
        <span className="font-semibold">{title}</span>
        {!canEdit && <Badge tone="warn">read-only</Badge>}
        {dirty && <Badge tone="accent">unsaved</Badge>}
      </div>
      <div className="flex items-center gap-2">
        {canEdit && (
          <>
            <Tooltip label="Undo">
              <Button size="icon" variant="ghost" disabled={!canUndo()} onClick={undo}>
                <Undo2 className="h-4 w-4" />
              </Button>
            </Tooltip>
            <Tooltip label="Redo">
              <Button size="icon" variant="ghost" disabled={!canRedo()} onClick={redo}>
                <Redo2 className="h-4 w-4" />
              </Button>
            </Tooltip>
          </>
        )}
        <Tabs value={viewMode} onValueChange={(v) => setViewMode(v as '2d' | '3d')}>
          <TabsList>
            <TabsTrigger value="2d">
              <Square className="mr-1 inline h-3.5 w-3.5" /> 2D
            </TabsTrigger>
            <TabsTrigger value="3d">
              <Box className="mr-1 inline h-3.5 w-3.5" /> 3D
            </TabsTrigger>
          </TabsList>
        </Tabs>
        {canEdit && (
          <Button variant="secondary" size="sm" disabled={saving} onClick={save}>
            <Save className="mr-1 h-3.5 w-3.5" /> {saving ? 'Saving…' : 'Save'}
          </Button>
        )}
        <select
          className="h-8 rounded-md border border-line bg-panel-2 px-2 text-sm"
          defaultValue=""
          onChange={(e) => {
            const f = e.target.value as 'dxf' | 'ifc' | 'csv';
            if (f) void onExport(f);
            e.target.value = '';
          }}
        >
          <option value="">Export…</option>
          <option value="dxf">DWG/DXF</option>
          <option value="ifc">IFC (Revit)</option>
          <option value="csv">Room schedule (CSV)</option>
        </select>
        <Button variant="primary" size="sm" disabled={!canEdit || generating} onClick={onGenerate}>
          {generating ? 'Generating…' : 'Generate'}
        </Button>
      </div>
    </Toolbar>
  );
}

function LeftPanel({ plan }: { plan: Plan }) {
  const selectedLevel = useEditor((s) => s.selectedLevel);
  const setSelectedLevel = useEditor((s) => s.setSelectedLevel);
  const level = getLevel(plan, selectedLevel);
  const legend = level ? planLegend(level) : [];
  return (
    <Panel className="m-2 flex h-[calc(100%-1rem)] flex-col gap-3 overflow-auto p-3">
      <section>
        <h3 className="mb-2 flex items-center gap-1 text-xs uppercase text-muted">
          <Layers className="h-3.5 w-3.5" /> Levels
        </h3>
        <div className="flex flex-col gap-1">
          {plan.levels.map((l) => (
            <button
              key={l.index}
              onClick={() => setSelectedLevel(l.index)}
              className={`rounded px-2 py-1 text-left text-sm ${
                l.index === selectedLevel ? 'bg-accent text-white' : 'hover:bg-panel-2'
              }`}
            >
              Level {l.index} · {l.rooms.length} rooms
            </button>
          ))}
        </div>
      </section>
      <section>
        <h3 className="mb-2 text-xs uppercase text-muted">Legend</h3>
        <ul className="flex flex-col gap-1 text-sm">
          {legend.map((e) => (
            <li key={e.type} className="flex items-center gap-2">
              <span className="h-3 w-3 rounded-sm" style={{ background: e.color }} />
              {e.type}
            </li>
          ))}
        </ul>
      </section>
    </Panel>
  );
}

function Viewport({ plan, canEdit }: { plan: Plan; canEdit: boolean }) {
  const viewMode = useEditor((s) => s.viewMode);
  const selectedLevel = useEditor((s) => s.selectedLevel);
  const moveRoomVertex = usePlanEditor((s) => s.moveRoomVertex);
  const moveOpening = usePlanEditor((s) => s.moveOpening);
  const [camera, setCamera] = useState<CameraView>('iso');
  return (
    <div className="relative m-2 h-[calc(100%-1rem)] overflow-hidden rounded-lg border border-line bg-panel">
      {viewMode === '2d' ? (
        <PlanCanvas2D
          plan={plan}
          editable={canEdit}
          onMoveVertex={(roomId, i, p) => moveRoomVertex(selectedLevel, roomId, i, p)}
          onMoveOpening={(id, off) => moveOpening(selectedLevel, id, off)}
        />
      ) : (
        <>
          <PlanScene3D plan={plan} view={camera} />
          <div className="absolute right-2 top-2 flex gap-1">
            <Tooltip label="Isometric view">
              <Button size="icon" variant="secondary" onClick={() => setCamera('iso')}>
                <Maximize2 className="h-4 w-4" />
              </Button>
            </Tooltip>
            <Tooltip label="Top view">
              <Button size="icon" variant="secondary" onClick={() => setCamera('top')}>
                <Square className="h-4 w-4" />
              </Button>
            </Tooltip>
          </div>
        </>
      )}
    </div>
  );
}

function Inspector({ plan, canEdit }: { plan: Plan; canEdit: boolean }) {
  const selection = useEditor((s) => s.selection);
  const selectedLevel = useEditor((s) => s.selectedLevel);
  const {
    setRoomType,
    autoFurnishRoom,
    removeFixture,
    addOpening,
    setOpeningWidth,
    deleteOpening,
  } = usePlanEditor();
  const level = getLevel(plan, selectedLevel);
  const room = level?.rooms.find((r) => r.id === selection.id && selection.kind === 'room');
  const fixture = level?.fixtures.find(
    (f) => f.id === selection.id && selection.kind === 'fixture',
  );
  const wall = level?.walls.find((w) => w.id === selection.id && selection.kind === 'wall');
  const opening = level?.openings.find(
    (o) => o.id === selection.id && selection.kind === 'opening',
  );

  return (
    <Panel className="m-2 h-[calc(100%-1rem)] overflow-auto p-3">
      <h3 className="mb-2 text-xs uppercase text-muted">Inspector</h3>
      {wall && (
        <div className="space-y-2 text-sm">
          <Row label="Wall" value={wall.type} />
          <Row
            label="Length"
            value={`${(Math.hypot(wall.b[0] - wall.a[0], wall.b[1] - wall.a[1]) / 1000).toFixed(2)} m`}
          />
          {canEdit && (
            <div className="flex gap-2">
              <Button
                size="sm"
                variant="secondary"
                onClick={() => addOpening(selectedLevel, wall.id, 'door')}
              >
                + Door
              </Button>
              <Button
                size="sm"
                variant="secondary"
                onClick={() => addOpening(selectedLevel, wall.id, 'window')}
              >
                + Window
              </Button>
            </div>
          )}
          <p className="text-xs text-muted">
            Click a wall, add an opening, then drag it along the wall.
          </p>
        </div>
      )}
      {opening && (
        <div className="space-y-2 text-sm">
          <Row label="Opening" value={opening.kind} />
          <Row label="Connects" value={(opening.connects ?? []).join(' ↔ ')} />
          {canEdit && (
            <label className="flex flex-col gap-1">
              <span className="text-muted">Width (mm)</span>
              <input
                type="number"
                className="h-9 rounded-md border border-line bg-panel-2 px-2"
                defaultValue={opening.width_mm}
                onBlur={(e) => setOpeningWidth(selectedLevel, opening.id, Number(e.target.value))}
              />
            </label>
          )}
          {opening.kind === 'door' && opening.width_mm < 815 && (
            <Badge tone="danger">below code min 815 mm</Badge>
          )}
          {canEdit && (
            <Button
              size="sm"
              variant="danger"
              onClick={() => deleteOpening(selectedLevel, opening.id)}
            >
              Delete opening
            </Button>
          )}
        </div>
      )}
      {room && (
        <div className="space-y-3 text-sm">
          <Row label="Room" value={room.id} />
          <label className="flex flex-col gap-1">
            <span className="text-muted">Type</span>
            <input
              list="ws-room-types"
              className="h-9 rounded-md border border-line bg-panel-2 px-2"
              defaultValue={room.type}
              disabled={!canEdit}
              onBlur={(e) => canEdit && setRoomType(selectedLevel, room.id, e.target.value)}
            />
            <datalist id="ws-room-types">
              {KNOWN_ROOM_TYPES.map((t) => (
                <option key={t} value={t} />
              ))}
            </datalist>
          </label>
          <Row label="Area" value={`${(room.area_mm2 / 1_000_000).toFixed(1)} m²`} />
          {canEdit && (
            <Button
              size="sm"
              variant="secondary"
              onClick={() => autoFurnishRoom(selectedLevel, room.id)}
            >
              Auto-furnish ({componentsForRoom(room.type).length} fit)
            </Button>
          )}
        </div>
      )}
      {fixture && (
        <div className="space-y-2 text-sm">
          <Row label="Fixture" value={fixture.component_id} />
          {canEdit && (
            <Button
              size="sm"
              variant="danger"
              onClick={() => removeFixture(selectedLevel, fixture.id)}
            >
              Remove
            </Button>
          )}
        </div>
      )}
      {!room && !fixture && !wall && !opening && (
        <p className="text-sm text-muted">Select a room, wall, opening, or fixture.</p>
      )}
    </Panel>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between gap-2">
      <span className="text-muted">{label}</span>
      <span className="truncate text-right">{value}</span>
    </div>
  );
}

function StatusBar({ plan }: { plan: Plan }) {
  const total = plan.levels.reduce((acc, l) => acc + l.rooms.length, 0);
  const fixtures = plan.levels.reduce((acc, l) => acc + l.fixtures.length, 0);
  const openings = plan.levels.flatMap((l) => l.openings);
  const doors = openings.filter((o) => o.kind === 'door').length;
  const windows = openings.filter((o) => o.kind === 'window').length;
  return (
    <div className="flex items-center justify-between border-t border-line bg-panel px-3 py-1 text-xs text-muted">
      <span>
        {plan.levels.length} level(s) · {total} rooms · {doors} doors · {windows} windows ·{' '}
        {fixtures} fixtures
      </span>
      <span className="flex items-center gap-2">
        Score
        {plan.score != null ? (
          <Badge tone={plan.score >= 80 ? 'ok' : 'warn'}>{plan.score.toFixed(1)}</Badge>
        ) : (
          <Badge>n/a</Badge>
        )}
      </span>
    </div>
  );
}
