import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


@pytest.fixture
def cfg():
    c = yaml.safe_load((ROOT / "config.yaml").read_text())
    c.update(companies=[], careers_pages=[], targets=[], profile={})
    return c


@pytest.fixture(autouse=True)
def no_sleep(monkeypatch):
    import radar.http as h
    monkeypatch.setattr(h.time, "sleep", lambda *_: None)
