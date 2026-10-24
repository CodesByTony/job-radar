import json

from radar import http, pipeline, report
from radar.models import Job
from radar.store import State


def mk(id_, title, company="Acme", desc="Intune. English working language.", feed="greenhouse:acme", **kw):
    return Job(id=id_, source="Acme (greenhouse)", feed=feed, title=title, company=company, location="Berlin",
               url=f"https://x/{id_}", apply_url=kw.pop("apply_url", ""), desc=desc, **kw)


def run(cfg, state, ats_jobs=(), ba_jobs=(), an_jobs=(), ok=True, enrich=None):
    cfg["companies"] = [{"name": "Acme", "ats": "greenhouse", "token": "acme"}]
    return pipeline.run_scan(
        cfg, state,
        ba_search=lambda c: list(ba_jobs), an_fetch=lambda c: list(an_jobs),
        ats_fetch=lambda e: (list(ats_jobs), ok), page_fetch=lambda e, s: ([], "n/a"),
        enrich=enrich or (lambda j: j))


def test_end_to_end_dedupe_and_lifecycle(cfg, tmp_path):
    st = State(tmp_path / "s.json")
    a = mk("gh:acme:1", "Endpoint Engineer", apply_url="https://boards.greenhouse.io/acme/jobs/1")
    dup = mk("an:1", "Endpoint Engineer")                      # same company/title/city from another source
    skip = mk("gh:acme:2", "Senior Endpoint Engineer")
    res = run(cfg, st, ats_jobs=[a, skip], an_jobs=[dup])
    assert [r.id for r in res["results"]] == ["gh:acme:1"]
    assert res["stats"]["unique"] == 2
    assert "greenhouse:acme" in st.companies or "greenhouse:acme" in {f"{c['ats']}:{c['token']}" for c in st.companies.values()}
    # second run: nothing new
    res2 = run(cfg, st, ats_jobs=[a, skip])
    assert res2["results"] == [] and res2["stats"]["new"] == 0
    # third run: job disappeared from a successfully fetched feed
    res3 = run(cfg, st, ats_jobs=[skip])
    assert [c["id"] for c in res3["closed"]] == ["gh:acme:1"]


def test_failed_feed_does_not_close_jobs(cfg, tmp_path):
    st = State(tmp_path / "s.json")
    a = mk("gh:acme:1", "Endpoint Engineer")
    run(cfg, st, ats_jobs=[a])
    res = run(cfg, st, ats_jobs=[], ok=False)
    assert res["closed"] == [] and st.jobs["gh:acme:1"]["status"] == "open"


def test_sweep_adds_company_from_apply_url(cfg, tmp_path):
    st = State(tmp_path / "s.json")
    b = Job(id="ba:1", source="BA Jobbörse", feed="ba", title="Endpoint Engineer", company="Beta GmbH", location="Ulm",
            url="https://ba/1", apply_url="https://beta.jobs.personio.de/job/9")
    def enrich(j):
        j.desc = "Intune. English working language."
        return j
    res = run(cfg, st, ba_jobs=[b], enrich=enrich)
    assert ("Beta GmbH", "personio", "beta") in res["new_companies"]
    assert "personio:beta" in st.companies


def test_ba_detail_budget_defers_without_recording(cfg, tmp_path):
    cfg["ba_detail_limit"] = 1
    st = State(tmp_path / "s.json")
    jobs = [Job(id=f"ba:{i}", source="BA Jobbörse", feed="ba", title=f"Intune Engineer {i}", company=f"C{i}", location="Ulm", url="u")
            for i in range(3)]
    res = run(cfg, st, ba_jobs=jobs, enrich=lambda j: setattr(j, "desc", "Intune. English.") or j)
    assert len(st.jobs) == 1 and res["stats"]["new"] == 1       # others retried next run


def test_senior_ba_title_skips_without_detail_call(cfg, tmp_path):
    calls = []
    st = State(tmp_path / "s.json")
    b = Job(id="ba:9", source="BA Jobbörse", feed="ba", title="Senior Intune Engineer", company="C", location="Ulm", url="u")
    run(cfg, st, ba_jobs=[b], enrich=lambda j: calls.append(1) or j)
    assert calls == []


def test_one_failing_source_does_not_stop_run(cfg, tmp_path):
    def boom(c):
        raise RuntimeError("down")
    cfg["companies"] = []
    res = pipeline.run_scan(cfg, State(tmp_path / "s.json"), ba_search=boom,
                            an_fetch=lambda c: [mk("an:7", "Intune Engineer", feed="arbeitnow")],
                            ats_fetch=lambda e: ([], True), page_fetch=lambda e, s: ([], ""), enrich=lambda j: j)
    assert len(res["results"]) == 1


def test_report_and_issue_title(cfg, tmp_path):
    st = State(tmp_path / "s.json")
    res = run(cfg, st, ats_jobs=[mk("gh:acme:1", "Endpoint Engineer")],
              an_jobs=[mk("an:5", "Junior Data Scientist", company="D", desc="machine learning. Fluent in German and English.", feed="arbeitnow")])
    res["down"] = ["rest.arbeitsagentur.de"]
    md = report.write_reports(tmp_path, res)
    assert "## Gold" in md and "override-only" in md.lower() and "Source problem" in md
    assert "WARNING" in report.issue_title(res)
    assert (tmp_path / "out" / "results.csv").exists()
    assert json.loads((tmp_path / "out" / "new.json").read_text())


def test_health_down_detection():
    http.reset_health()
    http.HEALTH["a.example"]["fail"] = 2
    http.HEALTH["b.example"]["ok"] = 3
    http.HEALTH["b.example"]["fail"] = 1
    assert http.sources_down() == ["a.example"]
    http.reset_health()


def test_state_roundtrip(tmp_path):
    st = State(tmp_path / "s.json")
    st.touch(mk("x:1", "T"))
    st.add_company("N", "lever", "n", "u")
    st.save()
    st2 = State.load(tmp_path / "s.json")
    assert "x:1" in st2.jobs and "lever:n" in st2.companies and st2.add_company("N", "lever", "n", "u") is False
