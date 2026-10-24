"""Persistent state in a single JSON file (committed back to the repo by the workflow)."""
from __future__ import annotations

import datetime as dt
import json
from pathlib import Path


def today() -> str:
    return dt.date.today().isoformat()


class State:
    def __init__(self, path: Path, data: dict | None = None):
        self.path = Path(path)
        d = data or {}
        self.jobs: dict = d.get("jobs", {})
        self.companies: dict = d.get("companies", {})
        self.pages: dict = d.get("pages", {})
        self.runs: list = d.get("runs", [])

    @classmethod
    def load(cls, path) -> "State":
        p = Path(path)
        if p.exists():
            return cls(p, json.loads(p.read_text()))
        return cls(p)

    def save(self) -> None:
        self.runs = self.runs[-30:]
        self.path.write_text(json.dumps(
            {"jobs": self.jobs, "companies": self.companies, "pages": self.pages, "runs": self.runs},
            ensure_ascii=False, indent=1, sort_keys=True))

    # --- jobs ---
    def is_new(self, job_id: str) -> bool:
        return job_id not in self.jobs

    def touch(self, job) -> None:
        rec = self.jobs.get(job.id)
        if rec is None:
            self.jobs[job.id] = dict(first_seen=today(), last_seen=today(), feed=job.feed, title=job.title,
                                     company=job.company, url=job.url, tier=job.tier, gate=job.gate, status="open")
        else:
            rec.update(last_seen=today(), status="open", tier=job.tier or rec.get("tier"), gate=job.gate or rec.get("gate"))

    def close_missing(self, feed: str, current_ids: set) -> list:
        """Mark jobs of a successfully fetched feed that are no longer listed. Returns the newly closed records."""
        closed = []
        for jid, rec in self.jobs.items():
            if rec.get("feed") == feed and rec.get("status") == "open" and jid not in current_ids:
                rec["status"] = "closed"
                rec["closed_on"] = today()
                closed.append({"id": jid, **rec})
        return closed

    # --- companies discovered by sweeps ---
    def add_company(self, name: str, ats: str, token: str, source_job: str, **extra) -> bool:
        key = f"{ats}:{token}"
        if key in self.companies:
            return False
        self.companies[key] = dict(name=name, ats=ats, token=token, added=today(), source_job=source_job, **extra)
        return True
