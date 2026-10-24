"""Cold-outreach drafts for agencies, Nexthink partners and employers. Drafts only: this module never sends anything.

Rules: contacts come from watchlists/targets.yaml (public company contact points that you or Claude verified).
Personal e-mail addresses are never guessed. Rendering is refused while profile.yaml still has SET_ME placeholders.
"""
from __future__ import annotations

import re
from pathlib import Path

PLACEHOLDER = "SET_ME"


class OutreachConfigError(Exception):
    pass


def slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def check_profile(profile: dict) -> None:
    bad = [k for k, v in profile.items()
           if PLACEHOLDER in str(v) or (isinstance(v, list) and any(PLACEHOLDER in str(x) for x in v))]
    missing = [k for k in ("name", "email", "availability_line", "proof_points", "role_focus") if not profile.get(k)]
    if bad or missing:
        raise OutreachConfigError(f"profile.yaml incomplete: placeholders {bad}, missing {missing}")


def render(target: dict, profile: dict, template: str) -> dict:
    proof = "\n".join(f"- {p}" for p in profile["proof_points"])
    body = template.format(
        company=target["name"], region=target.get("region", "Germany"), name=profile["name"], email=profile["email"],
        linkedin=profile.get("linkedin", ""), availability_line=profile["availability_line"], proof_points=proof,
        role_focus=profile["role_focus"], hook=target.get("hook", ""))
    subject, _, rest = body.partition("\n")
    contact = target.get("public_contact") or ""
    to = contact if contact else f"NO PUBLIC CONTACT YET: use {target.get('careers_url') or target.get('url') or 'their website'}"
    return {"to": to, "subject": subject.replace("Subject:", "").strip(), "body": rest.strip()}


def render_all(cfg: dict, root) -> list:
    root = Path(root)
    profile = cfg["profile"]
    check_profile(profile)
    outdir = root / "out" / "outreach"
    outdir.mkdir(parents=True, exist_ok=True)
    written = []
    for t in cfg.get("targets", []):
        if t.get("status") in ("contacted", "skip"):
            continue
        tpl_path = root / "templates" / f"{t['type']}.md"
        if not tpl_path.exists():
            continue
        path = outdir / f"{slug(t['name'])}.md"
        if path.exists():
            continue
        d = render(t, profile, tpl_path.read_text())
        path.write_text(f"To: {d['to']}\nSubject: {d['subject']}\nVerified contact: {bool(t.get('verified'))}\n\n{d['body']}\n")
        written.append(path.name)
    return written
