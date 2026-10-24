"""Arbeitnow public job board API (no key)."""
from __future__ import annotations

import re
from urllib.parse import urlparse

from .. import http
from ..models import Job

URL = "https://www.arbeitnow.com/api/job-board-api"


def fetch_all(cfg: dict) -> list:
    out, url = [], URL
    for _ in range(cfg["arbeitnow_pages"]):
        data = http.fetch(url)
        if not data:
            break
        for it in data.get("data", []):
            if urlparse(it.get("url", "")).netloc not in ("www.arbeitnow.com", "arbeitnow.com"):
                continue  # arbeitnow.ch/.nl/.co.uk/.fr are other countries
            out.append(Job(
                id="an:" + it.get("slug", ""), source="Arbeitnow", feed="arbeitnow", title=it.get("title", ""),
                company=it.get("company_name", ""), location=it.get("location", ""), url=it.get("url", ""),
                apply_url="", date=str(it.get("created_at", "")),
                desc=re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", it.get("description", "") or "")).strip(),
                tags=" ".join(it.get("tags", []) or [])))
        url = (data.get("links") or {}).get("next")
        if not url:
            break
    return out
