import {
  Button,
  Dialog,
  DialogClose,
  DialogContent,
  DialogTitle,
  DialogTrigger,
  Field,
} from '@fpg/ui';
import { useMemo, useRef, useState } from 'react';
import {
  type AreaUnit,
  type ColumnMap,
  type ParsedSheet,
  applyMapping,
  autoDetectMapping,
  parseSpreadsheet,
} from './excel-import';
import { useProgram } from './store';

const FIELDS: { key: keyof ColumnMap; label: string }[] = [
  { key: 'label', label: 'Room name' },
  { key: 'type', label: 'Type' },
  { key: 'count', label: 'Qty' },
  { key: 'area_target', label: 'Target area' },
  { key: 'area_min', label: 'Min area' },
  { key: 'department', label: 'Department' },
  { key: 'occupancy', label: 'Occupancy' },
];

export function ProgramImportDialog() {
  const setNodes = useProgram((s) => s.setNodes);
  const fileRef = useRef<HTMLInputElement>(null);
  const [open, setOpen] = useState(false);
  const [parsed, setParsed] = useState<ParsedSheet | null>(null);
  const [map, setMap] = useState<ColumnMap>({});
  const [unit, setUnit] = useState<AreaUnit>('m2');

  const onFile = async (file: File) => {
    const sheet = await parseSpreadsheet(file);
    setParsed(sheet);
    setMap(autoDetectMapping(sheet.headers));
  };

  const preview = useMemo(
    () => (parsed ? applyMapping(parsed.rows, map, unit) : null),
    [parsed, map, unit],
  );

  const apply = () => {
    if (preview) {
      setNodes(preview.nodes, 'excel');
      setOpen(false);
      setParsed(null);
    }
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button variant="secondary" size="sm">
          Import Excel/CSV
        </Button>
      </DialogTrigger>
      <DialogContent className="max-w-lg">
        <DialogTitle>Import area program</DialogTitle>

        <div className="mt-3 space-y-3">
          <input
            ref={fileRef}
            type="file"
            accept=".xlsx,.xls,.csv"
            className="hidden"
            onChange={(e) => {
              const f = e.target.files?.[0];
              if (f) void onFile(f);
            }}
          />
          <Button variant="secondary" size="sm" onClick={() => fileRef.current?.click()}>
            Choose file…
          </Button>

          {parsed && (
            <>
              <p className="text-xs text-muted">
                Sheet “{parsed.sheetName}” · {parsed.rows.length} rows · {parsed.headers.length}{' '}
                columns
              </p>
              <div className="grid grid-cols-2 gap-2">
                {FIELDS.map((f) => (
                  <Field key={f.key} label={f.label}>
                    <select
                      className="h-9 rounded-md border border-line bg-panel-2 px-2 text-sm"
                      value={map[f.key] ?? ''}
                      onChange={(e) => setMap({ ...map, [f.key]: e.target.value || undefined })}
                    >
                      <option value="">— none —</option>
                      {parsed.headers.map((h) => (
                        <option key={h} value={h}>
                          {h}
                        </option>
                      ))}
                    </select>
                  </Field>
                ))}
                <Field label="Area unit">
                  <select
                    className="h-9 rounded-md border border-line bg-panel-2 px-2 text-sm"
                    value={unit}
                    onChange={(e) => setUnit(e.target.value as AreaUnit)}
                  >
                    <option value="m2">m²</option>
                    <option value="ft2">ft²</option>
                  </select>
                </Field>
              </div>

              {preview && (
                <p className="text-sm">
                  Preview: <b>{preview.nodes.length}</b> rooms ·{' '}
                  <span className="text-warn">{preview.unmatched} need type review</span> ·{' '}
                  {preview.skipped} skipped
                </p>
              )}
            </>
          )}

          <div className="flex justify-end gap-2">
            <DialogClose asChild>
              <Button variant="ghost">Cancel</Button>
            </DialogClose>
            <Button
              variant="primary"
              disabled={!preview || preview.nodes.length === 0}
              onClick={apply}
            >
              Import {preview ? `(${preview.nodes.length})` : ''}
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
