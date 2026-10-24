"""Weekly funding radar: RSS items about German funding or expansion, for manual follow-up."""
from __future__ import annotations

import datetime as dt
import re
import xml.etree.ElementTree as ET
from pathlib import Path

from . import http

FUNDING = re.compile(r"\b(raises?|raised|funding|series [a-d]|seed round|secures?|invest(?:s|ment|ed)|"
                     r"finanzierungsrunde|millionen|mio\.?|expan(?:ds|sion)|wachstumskapital)\b", re.I)
GERMANY = re.compile(r"\b(german(?:y)?|berlin|munich|münchen|hamburg|frankfurt|stuttgart|cologne|köln|düsseldorf|"
                     r"dresden|leipzig|karlsruhe|deutschland|münster|nuremberg|nürnberg)\b", re.I)


def parse_feed(xml_text: str) -> list:
    items = []
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return items
    for it in root.iter():
        tag = it.tag.split("}")[-1]
        if tag not in ("item", "entry"):
            continue
        title = link = date = desc = ""
        for ch in it:
            t = ch.tag.split("}")[-1]
            if t == "title":
                title = (ch.text or "").strip()
            elif t == "link":
                link = (ch.text or ch.attrib.get("href", "")).strip()
            elif t in ("pubDate", "published", "updated"):
                date = (ch.text or "").strip()
            elif t in ("description", "summary", "content"):
                desc = re.sub(r"<[^>]+>", " ", ch.text or "")[:400]
        items.append(dict(title=title, link=link, date=date, desc=desc))
    return items


def relevant(item: dict) -> bool:
    blob = f"{item['title']} {item['desc']}"
    return bool(FUNDING.search(blob) and GERMANY.search(blob))


def run(cfg: dict, state, root, fetch=http.fetch) -> list:
    hits = []
    for url in (cfg.get("funding") or {}).get("feeds", []):
        txt = fetch(url, as_json=False)
        if not txt:
            continue
        for it in parse_feed(txt):
            key = "funding:" + it["link"]
            if it["link"] and key not in state.pages and relevant(it):
                state.pages[key] = "1"
                hits.append({**it, "feed": url})
    out = Path(root) / "out"
    out.mkdir(exist_ok=True)
    lines = [f"# Funding radar {dt.date.today().isoformat()}", "",
             "German funding or expansion news. For each: open the company's careers page, check IT roles, "
             "note the company in watchlists, and prepare a direct note to the hiring contact if it fits.", ""]
    lines += [f"- **{h['title']}** ({h['date'][:16]})  \n  {h['link']}" for h in hits] or ["No new items."]
    (out / "funding.md").write_text("\n".join(lines))
    return hits
