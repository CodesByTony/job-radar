"""Markdown digest, JSON and CSV output."""
from __future__ import annotations

import csv
import datetime as dt
import json
from pathlib import Path

CSV_FIELDS = ["tier", "score", "gate", "title", "company", "location", "german", "residence", "flags", "url", "source", "date"]


def issue_title(result: dict) -> str:
    n = len(result["results"])
    warn = f" | WARNING sources down: {', '.join(result['down'])}" if result["down"] else ""
    return f"Job radar {dt.date.today().isoformat()}: {n} new{warn}"


def build_markdown(result: dict) -> str:
    s, today = result["stats"], dt.date.today().isoformat()
    L = [f"# Job radar {today}", ""]
    if result["down"]:
        L += [f"> **Source problem:** every call failed for {', '.join(result['down'])}. Check the Actions log.", ""]
    L += [f"Fetched {s['fetched']}, unique {s['unique']}, new {s['new']}, passed gates {s['passed']}, feeds ok {s['feeds_ok']}.", ""]
    L += ["<details><summary>Source health (ok/fail calls per host)</summary>", ""]
    L += [f"- {h}: {v['ok']} ok / {v['fail']} failed" for h, v in sorted(result["health"].items())] or ["- no calls made"]
    L += ["", "</details>", ""]
    passing = [r for r in result["results"] if r.gate == "Pass"]
    override = [r for r in result["results"] if r.gate == "Override-only"]
    for tier in ("Gold", "Silver", "Bronze"):
        rows = [r for r in passing if r.tier == tier]
        if rows:
            L += [f"## {tier} ({len(rows)})", ""]
            for r in rows[:40]:
                bits = list(r.flags) + [f"German: {r.german}", r.residence]
                L.append(f"- **{r.title}** | {r.company} | {r.location} | score {r.score} | {' | '.join(bits)}  \n  {r.url}")
            L.append("")
    if override:
        L += [f"## German mandatory: override-only ({len(override)})", "",
              "Listed so you can decide. Applying here is your risk call; tag it in the tracker.", ""]
        for r in override[:25]:
            L.append(f"- {r.title} | {r.company} | {r.location} | {r.tier} | {r.url}")
        L.append("")
    if result["new_companies"]:
        L += ["## New companies added by sweep (polled from the next run)", ""]
        L += [f"- {n} ({a}: {t})" for n, a, t in result["new_companies"]] + [""]
    if result["closed"]:
        L += ["## Shortlisted postings that disappeared", ""]
        L += [f"- {c['title']} | {c['company']} | {c['url']}" for c in result["closed"]] + [""]
    if result["page_notes"]:
        L += ["## Career pages", ""] + [f"- {n}: {note} ({u})" for n, u, note in result["page_notes"]] + [""]
    if not result["results"]:
        L.append("No new postings passed the gates today.")
    return "\n".join(L)


def write_reports(root, result: dict) -> str:
    out = Path(root) / "out"
    out.mkdir(exist_ok=True)
    md = build_markdown(result)
    (out / "latest.md").write_text(md)
    (out / "new.json").write_text(json.dumps([r.to_dict() for r in result["results"]], ensure_ascii=False, indent=1))
    with open(out / "results.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        w.writeheader()
        for r in result["results"]:
            d = r.to_dict()
            d["flags"] = "; ".join(d["flags"])
            w.writerow({k: d.get(k, "") for k in CSV_FIELDS})
    return md
