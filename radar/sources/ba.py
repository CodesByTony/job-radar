"""Bundesagentur fuer Arbeit job search (unofficial public interface, public API key)."""
from __future__ import annotations

import base64
import re

from .. import http
from ..models import Job

BASE = "https://rest.arbeitsagentur.de/jobboerse/jobsuche-service"
HEADERS = {"X-API-Key": "jobboerse-jobsuche"}
SOURCE = "BA Jobbörse"


def _strip(html: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html or "")).strip()


def search(cfg: dict) -> list:
    out = []
    for q in cfg["ba_queries"]:
        for page in range(1, cfg["ba_pages"] + 1):
            data = http.fetch(f"{BASE}/pc/v4/jobs", headers=HEADERS, params=dict(
                was=q, size=50, page=page, veroeffentlichtseit=cfg["ba_days"], angebotsart=1))
            if not data:
                break
            items = data.get("stellenangebote") or []
            for it in items:
                ref = it.get("refnr", "")
                ort = it.get("arbeitsort") or {}
                out.append(Job(
                    id="ba:" + ref, source=SOURCE, feed="ba", title=it.get("titel") or it.get("beruf", ""),
                    company=it.get("arbeitgeber", ""), location=ort.get("ort", ""),
                    url="https://www.arbeitsagentur.de/jobsuche/jobdetail/" + ref,
                    apply_url=it.get("externeUrl", "") or "", date=it.get("aktuelleVeroeffentlichungsdatum", "")))
            if len(items) < 50:
                break
    return out


def enrich(job: Job) -> Job:
    ref = job.id[3:]
    data = http.fetch(f"{BASE}/pc/v4/jobdetails/{base64.b64encode(ref.encode()).decode()}", headers=HEADERS)
    if data:
        job.desc = _strip(data.get("stellenbeschreibung", ""))
        job.salary = _strip(str(data.get("verguetungsangabe", "") or ""))
        job.apply_url = job.apply_url or data.get("externeUrl", "") or data.get("allianzpartnerUrl", "") or ""
    return job
