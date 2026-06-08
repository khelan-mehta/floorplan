"""Per-jurisdiction source-document registry.

Each jurisdiction lists the code documents it is built from (URL, version, effective date, license).
A small seed jurisdiction ships with the service so downstream phases (08/09) have real rules to
test against. Documents live under ``app/seed_data``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

SEED_DIR = Path(__file__).resolve().parent / "seed_data"


@dataclass(frozen=True)
class SourceDoc:
    doc_id: str
    title: str
    short_code: str  # used as the `doc` field in rule citations, e.g. "Generic IBC"
    version: str
    effective_date: str
    url: str
    license: str
    path: str  # filename under SEED_DIR (relative); absolute paths also accepted

    def resolve(self) -> Path:
        p = Path(self.path)
        return p if p.is_absolute() else SEED_DIR / p

    def to_source_doc(self) -> dict[str, str]:
        """The shape stored under RuleSet.source_docs (Phase 02 schema)."""
        return {"title": self.title, "url": self.url, "effective_date": self.effective_date}


@dataclass(frozen=True)
class Jurisdiction:
    id: str
    name: str
    version: str
    docs: list[SourceDoc] = field(default_factory=list)


GENERIC_IBC = Jurisdiction(
    id="generic-ibc-2021",
    name="Generic (IBC-like) 2021",
    version="2021.0",
    docs=[
        SourceDoc(
            doc_id="generic-ibc",
            title="Generic Residential Building Code (Illustrative)",
            short_code="Generic IBC",
            version="2021.0",
            effective_date="2021-01-01",
            url="https://codes.iccsafe.org/",
            license="Illustrative paraphrase for testing; not an adopted legal code.",
            path="generic-ibc.code.md",
        )
    ],
)

REGISTRY: dict[str, Jurisdiction] = {GENERIC_IBC.id: GENERIC_IBC}


def get_jurisdiction(jurisdiction_id: str) -> Jurisdiction | None:
    return REGISTRY.get(jurisdiction_id)
