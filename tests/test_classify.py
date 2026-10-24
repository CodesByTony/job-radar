import pytest

from radar.classify import (evaluate, german_written, min_required_years, stated_salary_max)
from radar.models import Job


def job(title, desc="", **kw):
    return Job(id="t:1", source="test", title=title, desc=desc, **kw)


CASES = [
    # title, desc, expected gate, expected tier, expected german
    ("Modern Workplace Administrator", "Microsoft Intune, Autopilot, PowerShell. International team. Junior welcome. German is a plus.", "Pass", "Gold", "Plus"),
    ("Senior Intune Engineer", "Intune", "Skip", None, None),
    ("Modern Workplace Consultant", "7-10+ years experience in Intune. Fluent English.", "Skip", None, None),
    ("IT Product Owner", "8+ years managing products. Fluency in English is required.", "Skip", None, None),
    ("Junior Data Scientist", "Fluent in both German and English. SQL, Python, machine learning.", "Override-only", "Silver", "Mandatory"),
    ("Endpoint Engineer", "Verhandlungssichere Deutschkenntnisse erforderlich. Intune.", "Override-only", "Gold", "Mandatory"),
    ("IT Technical Consultant - Project Delivery", "Proficiency in English. German language skills preferred. project delivery.", "Pass", "Gold", "Plus"),
    ("Barista", "coffee", "Skip", None, None),
    ("RPA Developer", "UiPath automation. Working language is English.", "Pass", "Bronze", "Unclear"),
    ("Machine Learning Engineer", "Python, PyTorch. German B2 required.", "Override-only", "Silver", "Mandatory"),
]


@pytest.mark.parametrize("title,desc,gate,tier,german", CASES)
def test_cases(cfg, title, desc, gate, tier, german):
    j = evaluate(job(title, desc), cfg)
    assert j.gate == gate, (j.reason, j.flags)
    if tier:
        assert j.tier == tier
    if german:
        assert j.german == german


def test_german_override_off_drops_mandatory(cfg):
    cfg["filters"]["allow_german_override"] = False
    j = evaluate(job("Junior Data Scientist", "Fluent in German and English. machine learning."), cfg)
    assert j.gate == "Skip" and j.reason == "German mandatory"


def test_german_written_posting_is_mandatory(cfg):
    desc = ("Wir suchen Dich für unser Team. Deine Aufgaben: Intune Policies verwalten und mit dem Team der Kunden arbeiten. "
            "Wir bieten Dir ein starkes Team und die Zukunft der IT. Du bringst mit: Erfahrung mit Windows und der "
            "Verwaltung von Endgeräten für unsere Kunden und sie sind bei uns willkommen. Das ist ein Profil für Sie.")
    assert german_written(desc)
    j = evaluate(job("Endpoint Engineer", desc), cfg)
    assert j.german == "Mandatory" and "posting written in German" in j.flags


def test_english_text_not_flagged_as_german():
    assert not german_written("We are looking for an engineer to manage devices and applications for our global team. " * 6)


def test_salary_floor_skips_low_stated_salary(cfg):
    j = evaluate(job("IT Support Engineer", "Intune support. Salary 38.000 € per year."), cfg)
    assert j.gate == "Skip" and "below floor" in j.reason


def test_salary_above_floor_gives_residence_hint(cfg):
    j = evaluate(job("Endpoint Engineer", "Intune. Gehalt 52.000 - 60.000 €."), cfg)
    assert j.gate in ("Pass", "Override-only") and j.residence == "Blue Card likely"


def test_unknown_salary_never_skips(cfg):
    j = evaluate(job("Endpoint Engineer", "Intune. English working language."), cfg)
    assert j.gate == "Pass" and j.residence == "Check salary"


def test_prefilter_only_skips_senior_titles(cfg):
    assert evaluate(job("Lead Endpoint Engineer"), cfg, prefilter_only=True).gate == "Skip"
    assert evaluate(job("Endpoint Engineer"), cfg, prefilter_only=True).gate == "Pending"


def test_score_bounds_and_bonuses(cfg):
    a = evaluate(job("Junior Intune Engineer", "Intune Autopilot Nexthink. International team. German is a plus.", location="Berlin"), cfg)
    b = evaluate(job("Intune Engineer", "Intune."), cfg)
    assert 0 <= b.score <= a.score <= 100


@pytest.mark.parametrize("text,expected", [
    ("3 years of experience", 3), ("5+ years", 5), ("3-5 years", 3), ("mindestens 4 Jahre", 4),
    ("founded 120 years ago", 0), ("no numbers here", 0),
])
def test_years(text, expected):
    assert min_required_years(text) == expected


@pytest.mark.parametrize("text,expected", [
    ("45.000 €", 45000), ("€ 55.000", 55000), ("60k EUR", 60000), ("3.500 € monthly", 0), ("nothing", 0),
])
def test_salary(text, expected):
    assert stated_salary_max(text) == expected
