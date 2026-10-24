from __future__ import annotations

import re
from dataclasses import dataclass, field, asdict


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", (s or "").lower()).strip()


@dataclass
class Job:
    id: str
    source: str                 # e.g. "BA Jobbörse", "Arbeitnow", "Acme (Greenhouse)"
    title: str
    company: str = ""
    location: str = ""
    url: str = ""
    apply_url: str = ""         # employer apply page when known (used to detect the ATS)
    date: str = ""
    desc: str = ""
    tags: str = ""
    salary: str = ""
    feed: str = ""              # identifies the feed this job came from (for disappearance tracking)
    # classification results
    gate: str = ""
    reason: str = ""
    tier: str | None = None
    score: int = 0
    german: str = "Unclear"
    flags: list = field(default_factory=list)
    hits: list = field(default_factory=list)
    residence: str = "Check salary"
    salary_max: int = 0

    def key(self) -> str:
        """Cross-source dedupe key: company + title + city."""
        city = _norm(self.location).split(" ")[0] if self.location else ""
        return f"{_norm(self.company)}|{_norm(self.title)}|{city}"

    def to_dict(self, with_desc: bool = False) -> dict:
        d = asdict(self)
        if not with_desc:
            d["desc"] = ""
        return d
