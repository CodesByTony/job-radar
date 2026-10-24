"""Company ATS feeds. Only public, documented (or widely used) read endpoints; no logins.

detect_ats(url) finds (ats, token) from an apply URL so that company sweeps can follow a hit to its employer's feed.
"""
from __future__ import annotations

import re
import xml.etree.ElementTree as ET

from .. import http
from ..models import Job

PATTERNS = [
    ("greenhouse", re.compile(r"(?:boards|job-boards)(?:\.eu)?\.greenhouse\.io/(?:embed/job_board\?for=)?([a-z0-9_-]+)", re.I)),
    ("lever", re.compile(r"jobs(?:\.eu)?\.lever\.co/([a-z0-9_.-]+)", re.I)),
    ("personio", re.compile(r"([a-z0-9-]+)\.jobs\.personio\.(?:de|com)", re.I)),
    ("smartrecruiters", re.compile(r"(?:jobs|careers)\.smartrecruiters\.com/([A-Za-z0-9_-]+)", re.I)),
    ("ashby", re.compile(r"jobs\.ashbyhq\.com/([a-z0-9_.-]+)", re.I)),
    ("workable", re.compile(r"apply\.workable\.com/([a-z0-9_-]+)", re.I)),
    ("recruitee", re.compile(r"([a-z0-9-]+)\.recruitee\.com", re.I)),
]


def detect_ats(url: str):
    """Return (ats, token) or None."""
    for ats, rx in PATTERNS:
        m = rx.search(url or "")
        if m:
            tok = m.group(1)
            if ats == "personio" and tok.lower() in ("www", "jobs"):
                continue
            return ats, tok
    return None


def _clean(html: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html or "")).strip()


def fetch_company(entry: dict):
    """Return (jobs, ok). entry: {name, ats, token, eu?}."""
    name, ats, token = entry["name"], entry["ats"].lower(), entry["token"]
    feed = f"{ats}:{token}"
    label = f"{name} ({ats})"
    jobs, ok = [], True
    if ats == "greenhouse":
        d = http.fetch(f"https://boards-api.greenhouse.io/v1/boards/{token}/jobs?content=true")
        if d is None:
            return [], False
        for j in d.get("jobs", []):
            jobs.append(Job(id=f"gh:{token}:{j['id']}", source=label, feed=feed, title=j.get("title", ""), company=name,
                            location=(j.get("location") or {}).get("name", ""), url=j.get("absolute_url", ""),
                            apply_url=j.get("absolute_url", ""), date=j.get("updated_at", ""),
                            desc=_clean(j.get("content", ""))))
    elif ats == "lever":
        host = "api.eu.lever.co" if entry.get("eu") else "api.lever.co"
        d = http.fetch(f"https://{host}/v0/postings/{token}?mode=json")
        if d is None:
            return [], False
        for j in d:
            jobs.append(Job(id=f"lv:{token}:{j['id']}", source=label, feed=feed, title=j.get("text", ""), company=name,
                            location=(j.get("categories") or {}).get("location", ""), url=j.get("hostedUrl", ""),
                            apply_url=j.get("hostedUrl", ""), date=str(j.get("createdAt", "")),
                            desc=j.get("descriptionPlain", "") or _clean(j.get("description", ""))))
    elif ats == "personio":
        txt = http.fetch(f"https://{token}.jobs.personio.de/xml", as_json=False)
        if txt is None:
            return [], False
        try:
            root = ET.fromstring(txt)
        except ET.ParseError:
            return [], False
        for p in root.iter("position"):
            pid = p.findtext("id", "")
            desc = " ".join(" ".join(v.itertext()) for v in p.iter("value"))
            jobs.append(Job(id=f"pe:{token}:{pid}", source=label, feed=feed, title=p.findtext("name", ""), company=name,
                            location=p.findtext("office", ""), url=f"https://{token}.jobs.personio.de/job/{pid}",
                            apply_url=f"https://{token}.jobs.personio.de/job/{pid}", date=p.findtext("createdAt", ""),
                            desc=_clean(desc), tags=p.findtext("seniority", "")))
    elif ats == "smartrecruiters":
        d = http.fetch(f"https://api.smartrecruiters.com/v1/companies/{token}/postings?country=de&limit=100")
        if d is None:
            return [], False
        for j in d.get("content", []):
            url = f"https://jobs.smartrecruiters.com/{token}/{j['id']}"
            jobs.append(Job(id=f"sr:{token}:{j['id']}", source=label, feed=feed, title=j.get("name", ""), company=name,
                            location=(j.get("location") or {}).get("city", ""), url=url, apply_url=url,
                            date=j.get("releasedDate", ""), desc=""))
    elif ats == "ashby":
        d = http.fetch(f"https://api.ashbyhq.com/posting-api/job-board/{token}?includeCompensation=true")
        if d is None:
            return [], False
        for j in d.get("jobs", []):
            jobs.append(Job(id=f"ab:{token}:{j['id']}", source=label, feed=feed, title=j.get("title", ""), company=name,
                            location=j.get("location", ""), url=j.get("jobUrl", ""), apply_url=j.get("jobUrl", ""),
                            date=j.get("publishedAt", ""), desc=j.get("descriptionPlain", "") or ""))
    elif ats == "workable":
        d = http.fetch(f"https://www.workable.com/api/accounts/{token}?details=true")
        if d is None:
            return [], False
        for j in d.get("jobs", []):
            jobs.append(Job(id=f"wk:{token}:{j.get('shortcode')}", source=label, feed=feed, title=j.get("title", ""),
                            company=name, location=j.get("city", ""), url=j.get("url", ""), apply_url=j.get("url", ""),
                            date=j.get("published_on", ""), desc=_clean(j.get("description", ""))))
    elif ats == "recruitee":
        d = http.fetch(f"https://{token}.recruitee.com/api/offers/")
        if d is None:
            return [], False
        for j in d.get("offers", []):
            jobs.append(Job(id=f"rc:{token}:{j.get('id')}", source=label, feed=feed, title=j.get("title", ""),
                            company=name, location=j.get("city", ""), url=j.get("careers_url", ""),
                            apply_url=j.get("careers_url", ""), date=j.get("published_at", ""),
                            desc=_clean(j.get("description", "") + " " + j.get("requirements", ""))))
    else:
        return [], False
    return jobs, ok
