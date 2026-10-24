from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from . import funding, notion_sync, outreach, pipeline, report
from .sources import ats as ats_mod
from .store import State


def _root(args) -> Path:
    return Path(args.root).resolve()


def cmd_scan(args) -> int:
    root = _root(args)
    cfg = pipeline.load_cfg(root)
    state = State.load(root / "state.json")
    result = pipeline.run_scan(cfg, state)
    md = report.write_reports(root, result)
    pushed, errors = notion_sync.push(result["results"], cfg)
    state.save()
    print(md[:1500])
    if pushed or errors:
        print(f"Notion: pushed {pushed}, errors {errors}")
    gh = os.environ.get("GITHUB_OUTPUT")
    if gh:
        with open(gh, "a") as f:
            f.write(f"passed={len(result['results'])}\n")
            f.write(f"title={report.issue_title(result)}\n")
    return 0


def cmd_funding(args) -> int:
    root = _root(args)
    cfg = pipeline.load_cfg(root)
    state = State.load(root / "state.json")
    hits = funding.run(cfg, state, root)
    state.save()
    print(f"funding items: {len(hits)}")
    return 0


def cmd_outreach(args) -> int:
    root = _root(args)
    cfg = pipeline.load_cfg(root)
    try:
        written = outreach.render_all(cfg, root)
    except outreach.OutreachConfigError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2
    print(f"drafts written: {written}")
    return 0


def selfcheck_errors(root: Path) -> list:
    errs = []
    cfg = pipeline.load_cfg(root)
    for key in ("filters", "keywords", "ba_queries", "ba_days", "ba_pages", "arbeitnow_pages"):
        if key not in cfg:
            errs.append(f"config.yaml missing '{key}'")
    for k in ("max_required_years", "salary_floor", "blue_card_threshold", "allow_german_override"):
        if k not in cfg.get("filters", {}):
            errs.append(f"filters.{k} missing")
    for t in ("gold", "silver", "bronze"):
        if not cfg.get("keywords", {}).get(t):
            errs.append(f"keywords.{t} empty")
    for c in cfg["companies"]:
        if not {"name", "ats", "token"} <= set(c):
            errs.append(f"companies entry incomplete: {c}")
        elif c["ats"].lower() not in pipeline.SUPPORTED_ATS:
            errs.append(f"unsupported ATS '{c['ats']}' for {c['name']}")
    for p in cfg["careers_pages"]:
        if not {"name", "url"} <= set(p):
            errs.append(f"careers page entry incomplete: {p}")
    for t in cfg["targets"]:
        if not {"name", "type"} <= set(t):
            errs.append(f"target incomplete: {t}")
        elif not (root / "templates" / f"{t['type']}.md").exists():
            errs.append(f"no template for target type '{t['type']}' ({t['name']})")
    return errs


def cmd_selfcheck(args) -> int:
    errs = selfcheck_errors(_root(args))
    for e in errs:
        print("ERROR:", e)
    print("selfcheck:", "FAILED" if errs else "ok")
    return 1 if errs else 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="radar")
    ap.add_argument("--root", default=".")
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name, fn in (("scan", cmd_scan), ("funding", cmd_funding), ("outreach", cmd_outreach),
                     ("selfcheck", cmd_selfcheck)):
        sub.add_parser(name).set_defaults(fn=fn)
    args = ap.parse_args(argv)
    return args.fn(args)
