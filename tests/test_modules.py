import pytest

from radar import cli, funding, notion_sync, outreach
from radar.models import Job
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

RSS = """<rss><channel>
<item><title>Berlin startup raises €20M Series A</title><link>https://e/1</link><pubDate>Mon, 19 Oct 2026</pubDate><description>IT platform expands</description></item>
<item><title>US firm raises $50M</title><link>https://e/2</link><pubDate>Mon</pubDate><description>San Francisco</description></item>
<item><title>Munich scale-up secures funding round</title><link>https://e/3</link><pubDate>Tue</pubDate><description>x</description></item>
</channel></rss>"""

ATOM = """<feed xmlns="http://www.w3.org/2005/Atom"><entry><title>Hamburg firm raises seed</title>
<link href="https://e/4"/><updated>2026-10-20</updated><summary>Germany</summary></entry></feed>"""


def test_funding_filters_germany_and_dedupes(cfg, tmp_path):
    from radar.store import State
    cfg["funding"] = {"feeds": ["f1"]}
    st = State(tmp_path / "s.json")
    hits = funding.run(cfg, st, tmp_path, fetch=lambda url, **k: RSS)
    assert [h["link"] for h in hits] == ["https://e/1", "https://e/3"]
    assert funding.run(cfg, st, tmp_path, fetch=lambda url, **k: RSS) == []
    assert (tmp_path / "out" / "funding.md").exists()


def test_funding_parses_atom():
    items = funding.parse_feed(ATOM)
    assert items[0]["link"] == "https://e/4" and funding.relevant(items[0])


def test_funding_bad_xml():
    assert funding.parse_feed("not xml") == []


def test_notion_noop_without_token(cfg, monkeypatch):
    monkeypatch.delenv("NOTION_TOKEN", raising=False)
    assert notion_sync.push([Job(id="a", source="s", title="t", gate="Pass")], cfg) == (0, 0)


def test_notion_push_and_properties(cfg, monkeypatch):
    monkeypatch.setenv("NOTION_TOKEN", "secret")
    cfg["notion"] = {"enabled": True, "database_id": "db123"}
    sent = []

    class R:
        status_code = 200

    def post(url, headers=None, json=None, timeout=0):
        sent.append((headers, json))
        return R()

    j = Job(id="a", source="BA Jobbörse", title="Endpoint Engineer", url="https://u", gate="Pass", tier="Gold",
            score=77, german="Plus", residence="Check salary", location="Ulm", flags=["English signal"])
    assert notion_sync.push([j, Job(id="b", source="s", title="x", gate="Override-only")], cfg, post=post) == (1, 0)
    props = sent[0][1]["properties"]
    assert sent[0][1]["parent"] == {"database_id": "db123"} and sent[0][0]["Authorization"] == "Bearer secret"
    assert props["Tier"]["select"]["name"] == "Gold" and props["Source"]["select"]["name"] == "BA Jobbörse"
    assert props["Fit score"]["number"] == 77


def test_outreach_refuses_placeholders(cfg, tmp_path):
    prof = {"name": "T", "email": "e", "role_focus": "r", "proof_points": ["p"], "availability_line": "SET_ME: say when"}
    with pytest.raises(outreach.OutreachConfigError):
        outreach.check_profile(prof)


def test_outreach_renders_drafts_and_never_guesses_contacts(cfg, tmp_path):
    (tmp_path / "templates").mkdir()
    for n in ("agency", "nexthink_partner", "employer"):
        (tmp_path / "templates" / f"{n}.md").write_text((ROOT / "templates" / f"{n}.md").read_text())
    cfg["profile"] = {"name": "Tony", "email": "t@e.de", "linkedin": "l", "role_focus": "Intune roles",
                      "availability_line": "Available part time now and full time from April.", "proof_points": ["a", "b"]}
    cfg["targets"] = [
        {"name": "Alpha GmbH", "type": "agency", "url": "https://alpha.example"},
        {"name": "Beta AG", "type": "nexthink_partner", "public_contact": "jobs@beta.example", "hook": "you partner with Nexthink"},
        {"name": "Gamma", "type": "employer", "status": "contacted"},
    ]
    written = outreach.render_all(cfg, tmp_path)
    assert sorted(written) == ["alpha-gmbh.md", "beta-ag.md"]
    alpha = (tmp_path / "out" / "outreach" / "alpha-gmbh.md").read_text()
    beta = (tmp_path / "out" / "outreach" / "beta-ag.md").read_text()
    assert "NO PUBLIC CONTACT YET" in alpha and "To: jobs@beta.example" in beta
    assert "Available part time now" in beta and "you partner with Nexthink" in beta and "{" not in beta
    assert outreach.render_all(cfg, tmp_path) == []        # idempotent


def test_selfcheck_on_committed_config():
    assert cli.selfcheck_errors(ROOT) == []


def test_selfcheck_detects_problems(tmp_path):
    import shutil
    for item in ("config.yaml", "profile.yaml", "templates", "watchlists"):
        s = ROOT / item
        shutil.copytree(s, tmp_path / item) if s.is_dir() else shutil.copy(s, tmp_path / item)
    (tmp_path / "watchlists" / "companies.yaml").write_text("companies:\n  - {name: X, ats: workday, token: x}\n")
    assert any("unsupported ATS" in e for e in cli.selfcheck_errors(tmp_path))
