"""All network access goes through fetch() so that politeness, retries and health counting live in one place."""
from __future__ import annotations

import sys
import time
import urllib.robotparser
from collections import defaultdict
from urllib.parse import urlparse

import requests

UA = {"User-Agent": "job-radar/1.0 (personal job search tool; contact: tony275706@gmail.com)"}
SLEEP = 0.4
HEALTH: dict = defaultdict(lambda: {"ok": 0, "fail": 0})
_session = requests.Session()
_robots: dict = {}


def reset_health() -> None:
    HEALTH.clear()


def _host(url: str) -> str:
    return urlparse(url).netloc


def fetch(url: str, *, headers: dict | None = None, params: dict | None = None,
          as_json: bool = True, retries: int = 3, timeout: int = 30, sleep: float | None = None):
    """GET url. Returns parsed JSON (or text), or None on failure. 404 counts as a failure."""
    h = {**UA, **(headers or {})}
    host = _host(url)
    for attempt in range(retries):
        try:
            r = _session.get(url, headers=h, params=params, timeout=timeout)
            if r.status_code in (429, 503):
                time.sleep(5 * (attempt + 1))
                continue
            r.raise_for_status()
            HEALTH[host]["ok"] += 1
            time.sleep(SLEEP if sleep is None else sleep)
            return r.json() if as_json else r.text
        except (requests.RequestException, ValueError) as e:
            print(f"  ! {url[:100]} -> {e}", file=sys.stderr)
            time.sleep(1 + attempt)
    HEALTH[host]["fail"] += 1
    return None


def allowed_by_robots(url: str) -> bool:
    """True if our UA may fetch url according to the host's robots.txt (unknown robots = allowed)."""
    p = urlparse(url)
    base = f"{p.scheme}://{p.netloc}"
    if base not in _robots:
        rp = urllib.robotparser.RobotFileParser()
        txt = fetch(base + "/robots.txt", as_json=False, retries=1, sleep=0.1)
        if txt is None:
            _robots[base] = None
        else:
            rp.parse(txt.splitlines())
            _robots[base] = rp
    rp = _robots[base]
    return True if rp is None else rp.can_fetch(UA["User-Agent"], url)


def health_summary() -> dict:
    return {h: dict(v) for h, v in HEALTH.items()}


def sources_down(health: dict | None = None) -> list:
    """Hosts where every call failed."""
    health = health if health is not None else health_summary()
    return [h for h, v in health.items() if v["fail"] > 0 and v["ok"] == 0 and not h.endswith("robots.txt")]
