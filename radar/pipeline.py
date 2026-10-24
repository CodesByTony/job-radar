"""Orchestration: collect, dedupe, classify, sweep, track lifecycle."""
from __future__ import annotations

from pathlib import Path

import yaml

from . import classify, http
from .models import Job
from .sources import arbeitnow, ats, ba, careers
from .store import State

SUPPORTED_ATS = {"greenhouse", "lever", "personio", "smartrecruiters", "ashby", "workable", "recruitee"}


def _yaml(path: Path):
    return yaml.safe_load(path.read_text()) if path.exists() else None


def load_cfg(root) -> dict:
    root = Path(root)
    cfg = _yaml(root / "config.yaml") or {}
    cfg["companies"] = (_yaml(root / "watchlists" / "companies.yaml") or {}).get("companies", []) or []
    cfg["careers_pages"] = (_yaml(root / "watchlists" / "careers_pages.yaml") or {}).get("pages", []) or []
    cfg["targets"] = (_yaml(root / "watchlists" / "targets.yaml") or {}).get("targets", []) or []
    cfg["profile"] = _yaml(root / "profile.yaml") or {}
    return cfg


def _company_feeds(cfg: dict, state: State) -> list:
    seen, out = set(), []
    for e in list(cfg.get("companies", [])) + list(state.companies.values()):
        if not e.get("ats") or not e.get("token"):
            continue
        key = f"{e['ats'].lower()}:{e['token']}"
        if key not in seen:
            seen.add(key)
            out.append(e)
    return out


def collect(cfg: dict, state: State, ba_search=ba.search, an_fetch=arbeitnow.fetch_all,
            ats_fetch=ats.fetch_company, page_fetch=careers.fetch_page):
    """Return (jobs in priority order, feeds_ok {feed: set(ids)}, page_notes)."""
    jobs, feeds_ok, page_notes = [], {}, []
    src = cfg.get("sources", {})
    for entry in _company_feeds(cfg, state):
        try:
            got, ok = ats_fetch(entry)
        except Exception as e:  # N4: one company never stops the run
            print(f"  ! ATS {entry.get('name')}: {e}")
            continue
        if ok:
            feeds_ok[f"{entry['ats'].lower()}:{entry['token']}"] = {j.id for j in got}
            jobs.extend(got)
    for entry in cfg.get("careers_pages", []):
        try:
            got, note = page_fetch(entry, state)
        except Exception as e:
            got, note = [], f"error: {e}"
        page_notes.append((entry["name"], entry["url"], note))
        if got:
            feeds_ok[f"page:{entry['url']}"] = {j.id for j in got}
            jobs.extend(got)
    if src.get("ba", True):
        try:
            jobs.extend(ba_search(cfg))
        except Exception as e:
            print(f"  ! BA: {e}")
    if src.get("arbeitnow", True):
        try:
            jobs.extend(an_fetch(cfg))
        except Exception as e:
            print(f"  ! Arbeitnow: {e}")
    return jobs, feeds_ok, page_notes


def run_scan(cfg: dict, state: State, **injected) -> dict:
    http.reset_health()
    enrich = injected.pop("enrich", ba.enrich)
    jobs, feeds_ok, page_notes = collect(cfg, state, **injected)

    unique, by_id, by_key = [], set(), set()
    for j in jobs:
        if j.id in by_id:
            continue
        by_id.add(j.id)
        k = j.key()
        if k.strip("|") and k in by_key:
            continue
        by_key.add(k)
        unique.append(j)

    budget = cfg.get("ba_detail_limit", 150)
    results, new_count = [], 0
    for j in unique:
        if not state.is_new(j.id):
            state.touch(j)
            continue
        new_count += 1
        if j.source == ba.SOURCE and not j.desc:
            classify.evaluate(j, cfg, prefilter_only=True)
            if j.gate == "Skip":
                state.touch(j)
                continue
            if budget <= 0:
                new_count -= 1
                continue          # not recorded: retried on the next run
            enrich(j)
            budget -= 1
        classify.evaluate(j, cfg)
        state.touch(j)
        if j.gate in ("Pass", "Override-only"):
            results.append(j)

    new_companies = []
    for j in results:
        found = ats.detect_ats(j.apply_url or j.url)
        if found and state.add_company(j.company or found[1], found[0], found[1], j.url):
            new_companies.append((j.company or found[1], found[0], found[1]))

    closed = []
    for feed, ids in feeds_ok.items():
        closed.extend(c for c in state.close_missing(feed, ids) if c.get("gate") in ("Pass", "Override-only"))

    results.sort(key=lambda r: -r.score)
    health = http.health_summary()
    stats = {"fetched": len(jobs), "unique": len(unique), "new": new_count, "passed": len(results),
             "feeds_ok": len(feeds_ok)}
    state.runs.append({"date": __import__("datetime").date.today().isoformat(), **stats})
    return {"results": results, "closed": closed, "new_companies": new_companies, "page_notes": page_notes,
            "stats": stats, "health": health, "down": http.sources_down(health)}
