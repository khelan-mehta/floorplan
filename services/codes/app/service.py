"""CodesService: orchestrates registry -> ingest -> index -> extract -> review/publish.

Holds the in-memory state for the dev stack (drafts, published RuleSets, version history, and the
retrieval index). Seeds the bundled jurisdiction on construction so retrieval and a published
RuleSet are immediately available.
"""

from __future__ import annotations

import re
from typing import Any

from .extract import ExtractedRule, extract_rules
from .ingest import Chunk, ingest_document
from .registry import REGISTRY, Jurisdiction, SourceDoc, get_jurisdiction
from .rulesets import RuleDiff, RuleSetDraft, diff_rulesets
from .settings import settings
from .store import SearchHit, VectorStore

DISCLAIMER = (
    "Code-compliance output is decision-support, not legal sign-off. Extracted rules are an "
    "illustrative aid and may be incomplete or inaccurate. Always verify against the adopted code "
    "of the applicable jurisdiction and obtain a licensed professional's review."
)


class CodesService:
    def __init__(self) -> None:
        self.store = VectorStore(dim=settings.embedding_dim, alpha=settings.retrieval_alpha)
        self.drafts: dict[str, RuleSetDraft] = {}  # by jurisdiction_id (current draft)
        self.published: dict[str, dict[str, Any]] = {}  # by ruleset id
        self.history: dict[str, list[str]] = {}  # jurisdiction_id -> [versions...]
        self._chunks: dict[str, list[Chunk]] = {}
        self._uploaded: dict[str, str] = {}  # doc_id -> inline text for uploaded documents
        self._seed()

    def _seed(self) -> None:
        for jid in REGISTRY:
            self.ingest(jid)
            self.publish(jid)

    # --- ingest / extract ---------------------------------------------------
    def ingest(
        self, jurisdiction_id: str, *, text: str | None = None, version: str | None = None
    ) -> dict[str, Any]:
        juris = get_jurisdiction(jurisdiction_id)
        if juris is None:
            raise KeyError(jurisdiction_id)

        chunks: list[Chunk] = []
        for doc in juris.docs:
            t = text if text is not None else self._uploaded.get(doc.doc_id)
            chunks.extend(ingest_document(jurisdiction_id, doc, text=t))
        self._chunks[jurisdiction_id] = chunks
        self.store.upsert(jurisdiction_id, chunks)

        result = extract_rules(jurisdiction_id, chunks)
        new_version = version or self._next_version(jurisdiction_id, juris.version)
        draft = RuleSetDraft(
            id=jurisdiction_id,
            jurisdiction_id=jurisdiction_id,
            jurisdiction=juris.name,
            version=new_version,
            source_docs=[d.to_source_doc() for d in juris.docs],
            rules=result.rules,
            extraction_method=result.method,
        )
        prior = self.drafts.get(jurisdiction_id)
        diff = diff_rulesets(prior, draft)
        # preserve prior human review decisions for unchanged rules
        if prior is not None:
            self._carry_review(prior, draft, diff)
        draft.auto_approve_confident()
        self.drafts[jurisdiction_id] = draft
        self.history.setdefault(jurisdiction_id, []).append(new_version)

        return {
            "ruleset": draft.summary(),
            "chunks": len(chunks),
            "diff": diff.to_dict(),
            "extraction_method": result.method,
        }

    def add_document(
        self,
        *,
        jurisdiction_id: str,
        jurisdiction_name: str,
        doc_title: str,
        text: str,
        version: str = "1.0",
    ) -> dict[str, Any]:
        """Register an uploaded code document (creating the jurisdiction if new), then ingest +
        extract it. Retrieval works immediately; rule extraction uses the OpenAI path when a key is
        set, else the deterministic templates (which only cover the bundled seed jurisdiction)."""
        doc_id = re.sub(r"[^a-z0-9]+", "-", doc_title.lower()).strip("-") or f"{jurisdiction_id}-doc"
        sdoc = SourceDoc(
            doc_id=doc_id,
            title=doc_title,
            short_code=(jurisdiction_name or jurisdiction_id)[:24],
            version=version,
            effective_date="",
            url="uploaded",
            license="user upload",
            path="<inline>",
        )
        juris = REGISTRY.get(jurisdiction_id)
        if juris is None:
            REGISTRY[jurisdiction_id] = Jurisdiction(
                id=jurisdiction_id, name=jurisdiction_name or jurisdiction_id,
                version=version, docs=[sdoc],
            )
        elif doc_id not in {d.doc_id for d in juris.docs}:
            juris.docs.append(sdoc)
        self._uploaded[doc_id] = text
        return self.ingest(jurisdiction_id, version=version)

    def _next_version(self, jurisdiction_id: str, base: str) -> str:
        prior = self.drafts.get(jurisdiction_id)
        if prior is None:
            return base
        # bump the trailing integer: 2021.0 -> 2021.1
        head, _, tail = prior.version.rpartition(".")
        if head and tail.isdigit():
            return f"{head}.{int(tail) + 1}"
        return f"{prior.version}.1"

    @staticmethod
    def _carry_review(prior: RuleSetDraft, new: RuleSetDraft, diff: RuleDiff) -> None:
        changed = {c["id"] for c in diff.changed}
        for r in new.rules:
            rid = r.rule["id"]
            if rid in changed:
                continue  # changed rules need fresh review
            old = prior.rule_by_id(rid)
            if old is not None and old.review_status != "pending":
                r.review_status = old.review_status

    # --- retrieval ----------------------------------------------------------
    def query(self, jurisdiction_id: str, query: str, top_k: int = 5) -> dict[str, Any]:
        hits: list[SearchHit] = self.store.search(jurisdiction_id, query, top_k)
        return {
            "jurisdiction_id": jurisdiction_id,
            "query": query,
            "results": [
                {
                    "section": h.chunk.section,
                    "heading": h.chunk.heading,
                    "chapter": h.chunk.chapter,
                    "score": round(h.score, 4),
                    "citation": h.chunk.citation(),
                }
                for h in hits
            ],
            "disclaimer": DISCLAIMER,
        }

    # --- review / publish ---------------------------------------------------
    def review(
        self, ruleset_id: str, rule_id: str, action: str, rule_override: dict[str, Any] | None
    ) -> ExtractedRule:
        draft = self._require_draft(ruleset_id)
        rule = draft.rule_by_id(rule_id)
        if rule is None:
            raise KeyError(rule_id)
        if action == "approve":
            rule.review_status = "approved"
        elif action == "reject":
            rule.review_status = "rejected"
        elif action == "edit":
            if rule_override:
                rule.rule = {**rule.rule, **rule_override, "id": rule_id}
                rule.notes = "edited by reviewer"
            rule.review_status = "approved"
        else:
            raise ValueError(f"unknown review action: {action}")
        return rule

    def publish(self, ruleset_id: str) -> dict[str, Any]:
        draft = self._require_draft(ruleset_id)
        doc = draft.published_doc()
        draft.status = "published"
        self.published[ruleset_id] = doc
        return doc

    # --- accessors ----------------------------------------------------------
    def _require_draft(self, ruleset_id: str) -> RuleSetDraft:
        draft = self.drafts.get(ruleset_id)
        if draft is None:
            raise KeyError(ruleset_id)
        return draft

    def list_jurisdictions(self, jurisdiction: str | None = None) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for jid, juris in REGISTRY.items():
            if jurisdiction and jurisdiction.lower() not in juris.name.lower():
                continue
            draft = self.drafts.get(jid)
            out.append(
                {
                    "id": jid,
                    "name": juris.name,
                    "version": draft.version if draft else juris.version,
                    "published": jid in self.published,
                    "rule_count": len(draft.rules) if draft else 0,
                    "doc_count": len(juris.docs),
                }
            )
        return out

    def get_published(self, ruleset_id: str) -> dict[str, Any] | None:
        return self.published.get(ruleset_id)

    def get_draft(self, ruleset_id: str) -> RuleSetDraft | None:
        return self.drafts.get(ruleset_id)

    def rules_view(self, ruleset_id: str) -> list[dict[str, Any]]:
        draft = self._require_draft(ruleset_id)
        return [
            {
                "rule": r.rule,
                "confidence": r.confidence,
                "review_status": r.review_status,
                "flagged": r.confidence <= 0.7,
                "source_chunk_id": r.source_chunk_id,
                "source_text": r.source_text,
                "notes": r.notes,
            }
            for r in draft.rules
        ]
