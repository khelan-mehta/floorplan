import { Badge, Button, Input, Panel, Spinner, toast } from '@fpg/ui';
import { useRef, useState } from 'react';
import { api } from '../api/client';
import { useCodeQuery, useProject } from '../hooks/queries';
import type { CodeQueryResult } from '../api/types';

const SAMPLE_QUESTIONS = [
  'minimum bedroom area?',
  'door clear width',
  'ceiling height for habitable rooms',
  'egress requirements',
  'natural light window area',
];

/** Phase 07 — "Ask the code": semantic search over the project's jurisdiction with citations. */
export function CodesPage({ projectId }: { projectId: string }) {
  const { data: project } = useProject(projectId);
  const ask = useCodeQuery();
  const [q, setQ] = useState('');
  const jurisdictionId = project?.jurisdiction_id ?? null;

  function run(question: string) {
    const query = question.trim();
    if (!query || !jurisdictionId) return;
    setQ(query);
    ask.mutate({ jurisdiction_id: jurisdictionId, query, top_k: 5 });
  }

  return (
    <div className="mx-auto flex h-full max-w-3xl flex-col gap-4 overflow-y-auto p-6">
      <header>
        <h1 className="text-lg font-semibold">Building Code Assistant</h1>
        <p className="text-sm text-muted">
          Jurisdiction:{' '}
          {jurisdictionId ? (
            <span className="font-medium text-fg">{jurisdictionId}</span>
          ) : (
            <span className="text-warn">
              none selected — set one on the project to enable search
            </span>
          )}
        </p>
      </header>

      <Disclaimer />

      <UploadCode />

      <form
        className="flex gap-2"
        onSubmit={(e) => {
          e.preventDefault();
          run(q);
        }}
      >
        <Input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Ask about the code, e.g. “minimum bedroom area?”"
          disabled={!jurisdictionId}
          className="flex-1"
        />
        <Button type="submit" variant="primary" disabled={!jurisdictionId || ask.isPending}>
          {ask.isPending ? 'Searching…' : 'Ask'}
        </Button>
      </form>

      <div className="flex flex-wrap gap-1.5">
        {SAMPLE_QUESTIONS.map((s) => (
          <button
            key={s}
            onClick={() => run(s)}
            disabled={!jurisdictionId}
            className="rounded-full border border-line px-2.5 py-0.5 text-xs text-muted hover:bg-panel-2 disabled:opacity-50"
          >
            {s}
          </button>
        ))}
      </div>

      {ask.isPending && (
        <div className="flex items-center gap-2 text-muted">
          <Spinner /> Searching the code…
        </div>
      )}
      {ask.isError && (
        <p className="text-sm text-danger">Search failed. Is the codes service up?</p>
      )}

      {ask.data && (
        <div className="flex flex-col gap-3">
          <p className="text-xs uppercase text-muted">
            {ask.data.results.length} result(s) for “{ask.data.query}”
          </p>
          {ask.data.results.map((r) => (
            <ResultCard key={`${r.citation.doc}-${r.section}`} result={r} />
          ))}
        </div>
      )}
    </div>
  );
}

/** Upload a code document (text / markdown / HTML) to the RAG service for a jurisdiction. */
function UploadCode() {
  const fileRef = useRef<HTMLInputElement>(null);
  const [open, setOpen] = useState(false);
  const [jid, setJid] = useState('');
  const [name, setName] = useState('');
  const [busy, setBusy] = useState(false);

  const onFile = async (file: File) => {
    const id =
      jid.trim() ||
      file.name
        .replace(/\.[^.]+$/, '')
        .replace(/[^a-z0-9]+/gi, '-')
        .toLowerCase();
    setBusy(true);
    try {
      const text = await file.text();
      const res = await api.uploadCode({
        jurisdiction_id: id,
        jurisdiction_name: name.trim() || id,
        doc_title: file.name,
        text,
      });
      toast.success(
        `Ingested “${file.name}” → ${res.chunks} clauses, ${res.ruleset.rule_count} rules`,
      );
      setOpen(false);
    } catch {
      toast.error('Upload failed (is the codes service up?)');
    } finally {
      setBusy(false);
      if (fileRef.current) fileRef.current.value = '';
    }
  };

  if (!open) {
    return (
      <div>
        <Button size="sm" variant="secondary" onClick={() => setOpen(true)}>
          + Upload code document (RAG)
        </Button>
      </div>
    );
  }
  return (
    <Panel className="space-y-2 p-3">
      <div className="text-xs uppercase text-muted">Upload a building-code document</div>
      <div className="grid grid-cols-2 gap-2">
        <Input
          placeholder="Jurisdiction id (e.g. my-city-2025)"
          value={jid}
          onChange={(e) => setJid(e.target.value)}
        />
        <Input
          placeholder="Jurisdiction name"
          value={name}
          onChange={(e) => setName(e.target.value)}
        />
      </div>
      <input
        ref={fileRef}
        type="file"
        accept=".txt,.md,.markdown,.html,.htm"
        className="hidden"
        onChange={(e) => {
          const f = e.target.files?.[0];
          if (f) void onFile(f);
        }}
      />
      <div className="flex items-center gap-2">
        <Button
          size="sm"
          variant="primary"
          disabled={busy}
          onClick={() => fileRef.current?.click()}
        >
          {busy ? 'Ingesting…' : 'Choose .txt / .md / .html'}
        </Button>
        <Button size="sm" variant="ghost" onClick={() => setOpen(false)}>
          Cancel
        </Button>
        <span className="text-xs text-muted">
          Indexed for “ask the code”; rules are extracted (OpenAI when configured) for review.
        </span>
      </div>
    </Panel>
  );
}

function ResultCard({ result }: { result: CodeQueryResult }) {
  return (
    <Panel className="p-3">
      <div className="mb-1 flex items-center gap-2">
        <Badge tone="ok">§{result.section}</Badge>
        <span className="font-medium">{result.heading}</span>
        <span className="ml-auto text-xs text-muted">
          {result.chapter} · score {result.score.toFixed(2)}
        </span>
      </div>
      <p className="text-sm leading-relaxed text-fg">{result.citation.text}</p>
      <p className="mt-1 text-xs text-muted">
        Cited as: {result.citation.doc} §{result.section}
      </p>
    </Panel>
  );
}

export function Disclaimer() {
  return (
    <p className="rounded-md border border-warn/40 bg-warn/10 px-3 py-2 text-xs text-warn">
      ⚠️ Decision-support only — not legal sign-off. Extracted rules are illustrative and may be
      incomplete. Always verify against the adopted code and obtain a licensed professional&apos;s
      review.
    </p>
  );
}
