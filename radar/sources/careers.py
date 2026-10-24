"""Career pages: read schema.org JobPosting JSON-LD (the format Google Jobs uses); else detect content change."""
from __future__ import annotations

import hashlib
import json
import re

from .. import http
from ..models import Job

LD = re.compile(r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>', re.I | re.S)


def _walk(obj):
    if isinstance(obj, dict):
        yield obj
        for v in obj.values():
            yield from _walk(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from _walk(v)


def parse_jobposting(html: str) -> list:
    """Return dicts of JobPosting objects found in JSON-LD blocks."""
    found = []
    for block in LD.findall(html or ""):
        try:
            data = json.loads(block.strip())
        except ValueError:
            continue
        for node in _walk(data):
            t = node.get("@type")
            if t == "JobPosting" or (isinstance(t, list) and "JobPosting" in t):
                found.append(node)
    return found


def _location(node: dict) -> str:
    loc = node.get("jobLocation")
    if isinstance(loc, list) and loc:
        loc = loc[0]
    if isinstance(loc, dict):
        addr = loc.get("address") or {}
        if isinstance(addr, dict):
            return addr.get("addressLocality", "") or addr.get("addressRegion", "")
    return ""


def fetch_page(entry: dict, state) -> tuple:
    """Return (jobs, note). note is a human string such as 'changed' or 'no change'."""
    url, name = entry["url"], entry["name"]
    if not http.allowed_by_robots(url):
        return [], "blocked by robots.txt"
    html = http.fetch(url, as_json=False)
    if html is None:
        return [], "fetch failed"
    feed = f"page:{url}"
    jobs = []
    for i, node in enumerate(parse_jobposting(html)):
        title = node.get("title", "")
        org = node.get("hiringOrganization")
        company = org.get("name", name) if isinstance(org, dict) else name
        link = node.get("url") or node.get("sameAs") or url
        desc = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", node.get("description", "") or "")).strip()
        jobs.append(Job(id=f"pg:{hashlib.sha1((link + title).encode()).hexdigest()[:16]}", source=f"{name} (career page)",
                        feed=feed, title=title, company=company, location=_location(node), url=link, apply_url=link,
                        date=node.get("datePosted", ""), desc=desc))
    if jobs:
        return jobs, f"{len(jobs)} postings via JSON-LD"
    text = re.sub(r"\s+", " ", re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", html, flags=re.I | re.S))
    text = re.sub(r"<[^>]+>", " ", text)
    digest = hashlib.sha1(text.encode()).hexdigest()
    old = state.pages.get(url)
    state.pages[url] = digest
    if old is None:
        return [], "first snapshot stored (no JSON-LD found)"
    return [], "CHANGED: open the page and look" if old != digest else "no change"
