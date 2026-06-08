import { Badge, Button, Field, Input, Panel, Toolbar, toast } from '@fpg/ui';
import { lintBoundary, validate as validateSchema } from '@fpg/schemas';
import { useEffect, useRef, useState } from 'react';
import { boundaryToState, buildBoundaryDoc, levelMetrics, validate } from './boundary-model';
import { BoundaryCanvas } from './BoundaryCanvas';
import { Massing3D } from './Massing3D';
import { parseDxf } from './dxf-import';
import { useBoundary } from './store';

const m2 = (mm2: number) => (mm2 / 1_000_000).toFixed(1);
const m = (mm: number) => (mm / 1000).toFixed(1);

export function BoundaryEditor({
  projectId,
  initialDoc,
  onSaved,
}: {
  projectId: string;
  initialDoc?: import('@fpg/schemas').Boundary;
  onSaved?: () => void;
}) {
  const s = useBoundary();
  const [view, setView] = useState<'2d' | '3d'>('2d');
  const [saving, setSaving] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);
  const loadedRef = useRef(false);

  useEffect(() => {
    if (initialDoc && !loadedRef.current) {
      loadedRef.current = true;
      s.loadState(boundaryToState(initialDoc));
    }
  }, [initialDoc, s]);

  // Keyboard: undo/redo, delete vertex, finish/cancel drawing.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const el = e.target as HTMLElement | null;
      if (el && (el.tagName === 'INPUT' || el.tagName === 'TEXTAREA' || el.isContentEditable))
        return;
      const st = useBoundary.getState();
      const mod = e.ctrlKey || e.metaKey;
      if (mod && e.key.toLowerCase() === 'z' && !e.shiftKey) {
        e.preventDefault();
        if (st.draft.length > 0 && st.tool !== 'select') st.popDraft();
        else st.undo();
      } else if (
        mod &&
        (e.key.toLowerCase() === 'y' || (e.key.toLowerCase() === 'z' && e.shiftKey))
      ) {
        e.preventDefault();
        st.redo();
      } else if (e.key === 'Escape') {
        if (st.draft.length) st.clearDraft();
        st.selectVertex(null);
      } else if (e.key === 'Enter') {
        if (st.tool !== 'select' && st.draft.length >= 3) st.commitDraft();
      } else if (e.key === 'Delete' || e.key === 'Backspace') {
        e.preventDefault();
        if (st.selectedVertex != null) st.deleteVertex(st.selectedLevel, st.selectedVertex);
        else if (st.draft.length) st.popDraft();
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, []);

  const level = s.levels.find((l) => l.index === s.selectedLevel);
  const metrics = level ? levelMetrics(level) : { area_mm2: 0, perimeter_mm: 0 };

  const onImportDxf = async (file: File, scaleToMm: number) => {
    const text = await file.text();
    const result = parseDxf(text, scaleToMm);
    if (result.outline.length < 3) {
      toast.error('No closed polyline found in the DXF.');
      return;
    }
    s.setOutline(s.selectedLevel, result.outline);
    toast.success(`Imported ${result.outline.length} points (layers: ${result.layers.join(', ')})`);
  };

  const onSave = async () => {
    const issues = validate(s);
    if (issues.length) {
      toast.error(issues[0]?.message ?? 'Fix validation issues first');
      return;
    }
    const doc = buildBoundaryDoc(s, initialDoc?.id);
    const schemaResult = validateSchema('boundary.schema.json', doc);
    const geomIssues = lintBoundary(doc);
    if (!schemaResult.valid) {
      toast.error('Boundary failed schema validation');
      return;
    }
    if (geomIssues.length) {
      toast.error(`Geometry issue: ${geomIssues[0]?.message}`);
      return;
    }
    setSaving(true);
    try {
      const { api } = await import('../api/client');
      await api.putBoundary(projectId, doc);
      toast.success('Boundary saved');
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
        <div className="flex items-center gap-1">
          <Button
            variant={s.tool === 'select' ? 'primary' : 'ghost'}
            size="sm"
            onClick={() => s.setTool('select')}
          >
            Select
          </Button>
          <Button
            variant={s.tool === 'draw-outline' ? 'primary' : 'ghost'}
            size="sm"
            onClick={() => s.setTool('draw-outline')}
          >
            Draw outline
          </Button>
          <Button
            variant={s.tool === 'draw-parcel' ? 'primary' : 'ghost'}
            size="sm"
            onClick={() => s.setTool('draw-parcel')}
          >
            Draw parcel
          </Button>
          <Button
            size="sm"
            variant="secondary"
            onClick={() => s.commitDraft()}
            disabled={s.draft.length < 3}
          >
            Finish
          </Button>
          <Button
            size="sm"
            variant="ghost"
            onClick={() => (s.draft.length ? s.clearDraft() : s.clearOutline(s.selectedLevel))}
            disabled={
              !s.draft.length &&
              (s.levels.find((l) => l.index === s.selectedLevel)?.outline.length ?? 0) === 0
            }
          >
            {s.draft.length ? 'Clear draft' : 'Delete outline'}
          </Button>
          <span className="mx-1 h-5 w-px bg-line" />
          <Button
            size="sm"
            variant="ghost"
            onClick={() => s.undo()}
            disabled={!s.past.length}
            title="Undo (Ctrl+Z)"
          >
            ↶ Undo
          </Button>
          <Button
            size="sm"
            variant="ghost"
            onClick={() => s.redo()}
            disabled={!s.future.length}
            title="Redo (Ctrl+Shift+Z)"
          >
            ↷ Redo
          </Button>
          {s.selectedVertex != null && (
            <Button
              size="sm"
              variant="ghost"
              onClick={() => s.deleteVertex(s.selectedLevel, s.selectedVertex!)}
              title="Delete selected vertex (Del)"
            >
              ✕ Vertex
            </Button>
          )}
        </div>
        <div className="flex items-center gap-2 text-xs">
          <label className="flex items-center gap-1">
            <input type="checkbox" checked={s.snap} onChange={s.toggleSnap} /> Snap
          </label>
          <label className="flex items-center gap-1">
            <input type="checkbox" checked={s.ortho} onChange={s.toggleOrtho} /> Ortho
          </label>
          <div className="flex rounded bg-panel-2 p-0.5">
            <button
              className={`px-2 ${view === '2d' ? 'bg-accent text-white rounded' : ''}`}
              onClick={() => setView('2d')}
            >
              2D
            </button>
            <button
              className={`px-2 ${view === '3d' ? 'bg-accent text-white rounded' : ''}`}
              onClick={() => setView('3d')}
            >
              3D
            </button>
          </div>
          <Button size="sm" variant="primary" onClick={onSave} disabled={saving}>
            {saving ? 'Saving…' : 'Save boundary'}
          </Button>
        </div>
      </Toolbar>

      <div className="flex min-h-0 flex-1">
        <div className="relative flex-1 bg-bg">
          {view === '2d' ? <BoundaryCanvas /> : <Massing3D levels={s.levels} />}
          {view === '2d' && (
            <div className="pointer-events-none absolute bottom-2 left-2 rounded bg-panel/80 px-2 py-1 text-[11px] text-muted">
              {s.tool === 'select'
                ? 'Drag vertices · click edge dot to add · right-click / Del to remove · Ctrl+Z undo'
                : 'Click to add points · Enter/double-click to finish · Esc to cancel · Ctrl+Z removes last'}
            </div>
          )}
        </div>

        <Panel className="w-72 shrink-0 space-y-4 overflow-auto rounded-none border-y-0 border-r-0 p-3">
          <section>
            <h3 className="mb-2 text-xs uppercase text-muted">Levels</h3>
            <div className="mb-2 flex flex-col gap-1">
              {s.levels.map((l) => (
                <div key={l.index} className="flex items-center gap-1">
                  <button
                    onClick={() => s.selectLevel(l.index)}
                    className={`flex-1 rounded px-2 py-1 text-left text-sm ${
                      l.index === s.selectedLevel ? 'bg-accent text-white' : 'hover:bg-panel-2'
                    }`}
                  >
                    Level {l.index}
                  </button>
                  <Button size="sm" variant="ghost" onClick={() => s.removeLevel(l.index)}>
                    ✕
                  </Button>
                </div>
              ))}
            </div>
            <Button size="sm" variant="secondary" onClick={s.addLevel}>
              + Add level
            </Button>
          </section>

          {level && (
            <section className="space-y-2">
              <Field label="Floor-to-floor (mm)">
                <Input
                  type="number"
                  value={level.floor_to_floor_mm}
                  onChange={(e) =>
                    s.updateLevelMeta(level.index, { floor_to_floor_mm: Number(e.target.value) })
                  }
                />
              </Field>
              <Field label="Elevation (mm)">
                <Input
                  type="number"
                  value={level.elevation_mm}
                  onChange={(e) =>
                    s.updateLevelMeta(level.index, { elevation_mm: Number(e.target.value) })
                  }
                />
              </Field>
            </section>
          )}

          <section>
            <h3 className="mb-1 text-xs uppercase text-muted">Metrics</h3>
            <div className="flex gap-2 text-sm">
              <Badge tone="accent">{m2(metrics.area_mm2)} m²</Badge>
              <Badge>{m(metrics.perimeter_mm)} m perim</Badge>
            </div>
          </section>

          <section className="space-y-2">
            <h3 className="text-xs uppercase text-muted">Site & setbacks (mm)</h3>
            {(['front_mm', 'rear_mm', 'left_mm', 'right_mm'] as const).map((k) => (
              <Field key={k} label={k.replace('_mm', '')}>
                <Input
                  type="number"
                  value={s.site?.setbacks[k] ?? 3000}
                  onChange={(e) =>
                    s.setSetbacks({
                      front_mm: s.site?.setbacks.front_mm ?? 3000,
                      rear_mm: s.site?.setbacks.rear_mm ?? 3000,
                      left_mm: s.site?.setbacks.left_mm ?? 3000,
                      right_mm: s.site?.setbacks.right_mm ?? 3000,
                      [k]: Number(e.target.value),
                    })
                  }
                />
              </Field>
            ))}
          </section>

          <section>
            <Field label="North angle (°)">
              <Input
                type="number"
                value={s.northAngleDeg}
                onChange={(e) => s.setNorth(Number(e.target.value))}
              />
            </Field>
          </section>

          <section>
            <h3 className="mb-1 text-xs uppercase text-muted">Import</h3>
            <input
              ref={fileRef}
              type="file"
              accept=".dxf"
              className="hidden"
              onChange={(e) => {
                const f = e.target.files?.[0];
                if (f) void onImportDxf(f, 1);
              }}
            />
            <Button size="sm" variant="secondary" onClick={() => fileRef.current?.click()}>
              Import DXF (mm)
            </Button>
            <p className="mt-1 text-xs text-muted">DWG → use server import (Phase 15).</p>
          </section>
        </Panel>
      </div>
    </div>
  );
}
