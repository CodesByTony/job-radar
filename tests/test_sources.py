import base64
import json

from radar import http
from radar.sources import arbeitnow, ats, ba, careers
from radar.store import State


def test_detect_ats_patterns():
    assert ats.detect_ats("https://boards.greenhouse.io/acme/jobs/123") == ("greenhouse", "acme")
    assert ats.detect_ats("https://job-boards.greenhouse.io/acme/jobs/123") == ("greenhouse", "acme")
    assert ats.detect_ats("https://jobs.lever.co/acme-ag/abc") == ("lever", "acme-ag")
    assert ats.detect_ats("https://acme.jobs.personio.de/job/55") == ("personio", "acme")
    assert ats.detect_ats("https://jobs.smartrecruiters.com/AcmeGmbH/7437") == ("smartrecruiters", "AcmeGmbH")
    assert ats.detect_ats("https://jobs.ashbyhq.com/acme/uuid") == ("ashby", "acme")
    assert ats.detect_ats("https://apply.workable.com/acme/j/ABC/") == ("workable", "acme")
    assert ats.detect_ats("https://acme.recruitee.com/o/job") == ("recruitee", "acme")
    assert ats.detect_ats("https://www.example.com/careers") is None
    assert ats.detect_ats("") is None


def test_greenhouse_adapter(monkeypatch):
    payload = {"jobs": [{"id": 1, "title": "Endpoint Engineer", "absolute_url": "https://boards.greenhouse.io/acme/jobs/1",
                         "location": {"name": "Berlin"}, "updated_at": "2026-10-20", "content": "<p>Intune role</p>"}]}
    monkeypatch.setattr(http, "fetch", lambda url, **k: payload)
    jobs, ok = ats.fetch_company({"name": "Acme", "ats": "greenhouse", "token": "acme"})
    assert ok and jobs[0].id == "gh:acme:1" and jobs[0].desc == "Intune role" and jobs[0].feed == "greenhouse:acme"


def test_lever_adapter_eu_host(monkeypatch):
    seen = {}

    def fake(url, **k):
        seen["url"] = url
        return [{"id": "x", "text": "IT Consultant", "hostedUrl": "https://jobs.lever.co/a/x",
                 "categories": {"location": "Munich"}, "createdAt": 1, "descriptionPlain": "desc"}]

    monkeypatch.setattr(http, "fetch", fake)
    jobs, ok = ats.fetch_company({"name": "A", "ats": "lever", "token": "a", "eu": True})
    assert ok and "api.eu.lever.co" in seen["url"] and jobs[0].location == "Munich"


def test_personio_adapter(monkeypatch):
    xml = ("<workzag-jobs><position><id>9</id><name>IT Support</name><office>Hamburg</office>"
           "<createdAt>2026-10-01</createdAt><jobDescriptions><jobDescription><name>Tasks</name>"
           "<value><![CDATA[<p>Support Intune</p>]]></value></jobDescription></jobDescriptions></position></workzag-jobs>")
    monkeypatch.setattr(http, "fetch", lambda url, **k: xml)
    jobs, ok = ats.fetch_company({"name": "P", "ats": "personio", "token": "p"})
    assert ok and jobs[0].id == "pe:p:9" and "Intune" in jobs[0].desc


def test_adapter_failure_returns_not_ok(monkeypatch):
    monkeypatch.setattr(http, "fetch", lambda url, **k: None)
    assert ats.fetch_company({"name": "A", "ats": "greenhouse", "token": "a"}) == ([], False)
    assert ats.fetch_company({"name": "A", "ats": "unknown", "token": "a"}) == ([], False)


def test_ba_search_and_enrich(monkeypatch, cfg):
    cfg["ba_queries"] = ["Intune"]
    calls = []

    def fake(url, headers=None, params=None, **k):
        calls.append((url, headers, params))
        if "jobdetails" in url:
            return {"stellenbeschreibung": "<p>Intune. German is a plus.</p>", "externeUrl": "https://acme.jobs.personio.de/job/1"}
        return {"stellenangebote": [{"refnr": "10001-ABC-S", "titel": "Endpoint Engineer", "arbeitgeber": "Acme",
                                     "arbeitsort": {"ort": "Stuttgart"}, "aktuelleVeroeffentlichungsdatum": "2026-10-23"}]}

    monkeypatch.setattr(http, "fetch", fake)
    jobs = ba.search(cfg)
    assert len(jobs) == 1 and jobs[0].id == "ba:10001-ABC-S" and calls[0][1]["X-API-Key"] == "jobboerse-jobsuche"
    ba.enrich(jobs[0])
    assert "Intune" in jobs[0].desc and "personio" in jobs[0].apply_url
    assert base64.b64encode(b"10001-ABC-S").decode() in calls[1][0]


def test_arbeitnow_paging(monkeypatch, cfg):
    pages = [{"data": [{"slug": "a", "title": "T1", "company_name": "C", "location": "Berlin", "url": "u1",
                        "created_at": 1, "description": "<b>x</b>", "tags": ["IT"]}], "links": {"next": "https://next"}},
             {"data": [{"slug": "b", "title": "T2", "company_name": "C", "location": "Berlin", "url": "u2",
                        "created_at": 2, "description": "y", "tags": []}], "links": {"next": None}}]
    it = iter(pages)
    monkeypatch.setattr(http, "fetch", lambda url, **k: next(it))
    jobs = arbeitnow.fetch_all(cfg)
    assert [j.id for j in jobs] == ["an:a", "an:b"] and jobs[0].tags == "IT"


HTML_LD = """<html><script type="application/ld+json">{"@context":"https://schema.org","@type":"JobPosting",
"title":"IT Support","hiringOrganization":{"name":"Acme"},"jobLocation":{"address":{"addressLocality":"Ulm"}},
"url":"https://acme.example/jobs/1","description":"<p>Intune</p>"}</script></html>"""


def test_careers_json_ld(monkeypatch, tmp_path):
    monkeypatch.setattr(http, "allowed_by_robots", lambda url: True)
    monkeypatch.setattr(http, "fetch", lambda url, **k: HTML_LD)
    jobs, note = careers.fetch_page({"name": "Acme", "url": "https://acme.example/careers"}, State(tmp_path / "s.json"))
    assert jobs[0].title == "IT Support" and jobs[0].location == "Ulm" and "JSON-LD" in note


def test_careers_change_detection(monkeypatch, tmp_path):
    monkeypatch.setattr(http, "allowed_by_robots", lambda url: True)
    st = State(tmp_path / "s.json")
    entry = {"name": "Acme", "url": "https://acme.example/careers"}
    monkeypatch.setattr(http, "fetch", lambda url, **k: "<html><body>Jobs v1</body></html>")
    assert "first snapshot" in careers.fetch_page(entry, st)[1]
    assert careers.fetch_page(entry, st)[1] == "no change"
    monkeypatch.setattr(http, "fetch", lambda url, **k: "<html><body>Jobs v2</body></html>")
    assert careers.fetch_page(entry, st)[1].startswith("CHANGED")


def test_careers_respects_robots(monkeypatch, tmp_path):
    monkeypatch.setattr(http, "allowed_by_robots", lambda url: False)
    jobs, note = careers.fetch_page({"name": "A", "url": "https://a.example/"}, State(tmp_path / "s.json"))
    assert jobs == [] and "robots" in note
