from radar.classify import evaluate
from radar.models import Job

def mk(title, desc=""):
    return Job(id="x", source="t", feed="t", title=title, company="c", location="Ulm", url="u", apply_url="", date="", desc=desc)


def test_german_title_without_description_is_mandatory(cfg):
    j = evaluate(mk("IT-Systemadministrator (m/w/d) Microsoft Intune"), cfg)
    assert j.german == "Mandatory"


def test_english_title_stays_unclear(cfg):
    j = evaluate(mk("Intune Engineer (m/f/d)", "Join our team"), cfg)
    assert j.german == "Unclear"
