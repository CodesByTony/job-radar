"""Bundesagentur fuer Arbeit job search (unofficial public interface, public API key)."""
from __future__ import annotations

import base64
import re

from .. import http
from ..models import Job

BASE = "https://rest.arbeitsagentur.de/jobboerse/jobsuche-service"
HEADERS = {"X-API-Key": "jobboerse-jobsuche"}
SOURCE = "BA Jobbörse"
SEARCH_PATHS = ["/pc/v6/jobs", "/pc/v4/app/jobs", "/pc/v4/jobs"]  # first one that answers is kept
DETAIL_PATHS = ["/pc/v4/jobdetails", "/pc/v3/jobdetails"]
_good = {"search": None, "detail": None}


def _call(kind: str, paths: list, suffix: str, params=None):
    """Try known endpoint versions in order; remember the one that works."""
    order = [_good[kind]] if _good[kind] else paths
    for pth in order:
        data = http.fetch(BASE + pth + suffix, headers=HEADERS, params=params, retries=1)
        if data:
            _good[kind] = pth
            return data
    return None


def _strip(html: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html or "")).strip()


_logged: list = []


def _first(d: dict, *keys) -> str:
    for k in keys:
        if d.get(k):
            return str(d[k])
    return ""


def search(cfg: dict) -> list:
    out = []
    for q in cfg["ba_queries"]:
        for page in range(1, cfg["ba_pages"] + 1):
            data = _call("search", SEARCH_PATHS, "", dict(
                was=q, size=50, page=page, veroeffentlichtseit=cfg["ba_days"], angebotsart=1))
            if not data:
                break
            items = next((data[k] for k in ("stellenangebote", "ergebnisliste", "jobs", "angebote", "items", "results")
                          if isinstance(data.get(k), list)), [])
            if not items and page == 1:
                note = f"{_good['search']} ok but no job list; keys={sorted(data)[:8]} sample={str(data)[:160]}"
                http.HEALTH[http._host(BASE)]["err"] = note
            if items and page == 1 and not _logged:
                _logged.append(1)
                http.HEALTH[http._host(BASE)]["err"] = f"item keys={sorted(items[0])}"
            for it in items:
                ref = _first(it, "refnr", "referenznummer", "hashId", "id")
                ort = it.get("arbeitsort") or it.get("stellenlokationen") or {}
                if isinstance(ort, list):
                    ort = (ort[0].get("adresse") if ort and isinstance(ort[0], dict) else {}) or {}
                out.append(Job(
                    id="ba:" + ref, source=SOURCE, feed="ba",
                    title=_first(it, "titel", "stellenangebotsTitel", "beruf", "title"),
                    company=_first(it, "arbeitgeber", "arbeitgebername", "firma"),
                    location=ort.get("ort", "") if isinstance(ort, dict) else str(ort),
                    url="https://www.arbeitsagentur.de/jobsuche/jobdetail/" + ref,
                    apply_url=it.get("externeUrl", "") or "",
                    date=_first(it, "aktuelleVeroeffentlichungsdatum", "veroeffentlichungsdatum", "modifikationsTimestamp")))
            if len(items) < 50:
                break
    return out


def enrich(job: Job) -> Job:
    ref = job.id[3:]
    data = _call("detail", DETAIL_PATHS, "/" + base64.b64encode(ref.encode()).decode())
    if data:
        job.desc = _strip(data.get("stellenbeschreibung", ""))
        job.salary = _strip(str(data.get("verguetungsangabe", "") or ""))
        job.apply_url = job.apply_url or data.get("externeUrl", "") or data.get("allianzpartnerUrl", "") or ""
    return job
