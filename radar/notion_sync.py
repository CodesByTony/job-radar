"""Optional push of passing postings to the Notion 'Jobs' database (needs NOTION_TOKEN and notion.database_id)."""
from __future__ import annotations

import datetime as dt
import os

import requests

API = "https://api.notion.com/v1/pages"
SOURCE_MAP = {"BA Jobbörse": "BA Jobbörse", "Arbeitnow": "Arbeitnow"}
GERMAN_MAP = {"Plus": "Plus", "Mandatory": "Mandatory", "Unclear": "Unclear"}


def _text(s: str) -> dict:
    return {"rich_text": [{"text": {"content": (s or "")[:1900]}}]}


def to_properties(job) -> dict:
    source = SOURCE_MAP.get(job.source, "Company careers")
    return {
        "Title": {"title": [{"text": {"content": job.title[:200]}}]},
        "URL": {"url": job.url or None},
        "Source": {"select": {"name": source}},
        "Date found": {"date": {"start": dt.date.today().isoformat()}},
        "Location": _text(job.location),
        "Tier": {"select": {"name": job.tier}} if job.tier else {"select": None},
        "German requirement": {"select": {"name": GERMAN_MAP.get(job.german, "Unclear")}},
        "German override": {"checkbox": False},
        "Residence path": {"select": {"name": job.residence}},
        "Fit score": {"number": job.score},
        "Confidence": {"select": {"name": "Low"}},
        "Gate": {"select": {"name": "Pass" if job.gate == "Pass" else "Skip"}},
        "Status": {"status": {"name": "Found"}},
        "Notes": _text("radar heuristic score; flags: " + "; ".join(job.flags)),
    }


def push(results: list, cfg: dict, post=requests.post) -> tuple:
    """Return (pushed, errors). Silent no-op when not configured."""
    token = os.environ.get("NOTION_TOKEN")
    db = (cfg.get("notion") or {}).get("database_id")
    if not token or not db or not (cfg.get("notion") or {}).get("enabled"):
        return 0, 0
    pushed = errors = 0
    for job in results:
        if job.gate != "Pass":
            continue
        r = post(API, headers={"Authorization": f"Bearer {token}", "Notion-Version": "2022-06-28",
                               "Content-Type": "application/json"},
                 json={"parent": {"database_id": db}, "properties": to_properties(job)}, timeout=30)
        if getattr(r, "status_code", 500) == 200:
            pushed += 1
        else:
            errors += 1
            print(f"  ! Notion push failed ({getattr(r, 'status_code', '?')}): {job.title}")
    return pushed, errors
