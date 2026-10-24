"""Deterministic gates, German-requirement detection, tiering and heuristic scoring."""
from __future__ import annotations

import re

from .models import Job

DE_MANDATORY = re.compile(
    r"verhandlungssicher|fl(?:ue|ü)ssig(?:e|es|en)? deutsch|muttersprach|sehr gute deutschkenntnisse|"
    r"gute deutschkenntnisse|deutschkenntnisse (?:sind )?(?:erforderlich|vorausgesetzt|zwingend)|"
    r"deutsch\w*.{0,30}\b(?:c1|c2|b2)\b|\b(?:c1|c2|b2)\b.{0,30}deutsch|"
    r"german.{0,40}\b(?:fluent|c1|c2|b2|native|mandatory|required|business level|written and spoken)\b|"
    r"\b(?:fluent|fluency|native|excellent|very good|strong)\b.{0,20}\bgerman\b|"
    r"\bgerman\b.{0,15}\b(?:language )?skills (?:are )?(?:required|mandatory|essential)",
    re.I | re.S)
DE_PLUS = re.compile(
    r"german.{0,40}\b(?:plus|advantage|preferred|nice to have|desirable|beneficial|asset|a bonus)\b|"
    r"deutschkenntnisse.{0,40}(?:von vorteil|w(?:ue|ü)nschenswert|plus|hilfreich)",
    re.I | re.S)
EN_SIGNAL = re.compile(
    r"working language is english|english (?:is|as) (?:the )?(?:working|company|corporate) language|"
    r"international team|arbeitssprache englisch|englisch als arbeitssprache|"
    r"fluency in english|fluent english|proficiency in english|english (?:is )?required", re.I)
SENIOR_TITLE = re.compile(
    r"\b(?:senior|sr\.?|lead|head of|principal|director|vp|chief|staff|architect|expert)\b|\(senior\)", re.I)
YEARS = re.compile(r"(?<![\d.,])(\d{1,2})(?!\d)\s*\+?\s*(?:-|to|bis)?\s*(?:\d{1,2})?\s*\+?\s*(?:years|jahre|jahren|yrs)", re.I)
JUNIOR = re.compile(
    r"\b(?:junior|entry[- ]level|graduate|berufseinsteiger|trainee|associate|absolvent|early career)\b", re.I)
SALARY = re.compile(r"(\d{2,3})(?:[.,](\d{3}))?\s*(k)?\s*(?:€|eur\b|euro)", re.I)
GERMAN_WORDS = set(
    "und der die das mit für wir sie ist sind oder auch von zu im den dem ein eine einen deine ihre unser "
    "aufgaben profil bieten".split())


def german_written(text: str) -> bool:
    words = re.findall(r"[a-zA-ZäöüßÄÖÜ]+", text.lower())[:400]
    if len(words) < 40:
        return False
    return sum(w in GERMAN_WORDS for w in words) / len(words) > 0.12


def min_required_years(text: str) -> int:
    """Largest lower bound of 'N years' style statements in a plausible range (1-20)."""
    best = 0
    for m in YEARS.finditer(text):
        n = int(m.group(1))
        if 1 <= n <= 20:
            best = max(best, n)
    return best


SALARY_PRE = re.compile(r"(?:€|eur\b|euro)\s*(\d{2,3})(?:[.,](\d{3}))?\s*(k)?", re.I)


def stated_salary_max(text: str) -> int:
    """Largest annual-looking salary figure (25k-250k) in text, 0 if none."""
    best = 0
    for rx in (SALARY, SALARY_PRE):
        for m in rx.finditer(text):
            whole, frac, k = m.group(1), m.group(2), m.group(3)
            val = int(whole) * 1000 + int(frac) if frac else (int(whole) * 1000 if k else int(whole))
            if 25000 <= val <= 250000:
                best = max(best, val)
    return best


GENERIC = {"rollout", "monitoring", "elastic", "recommend", "pmo", "it project", "service owner",
           "project delivery", "reporting analyst", "process automation", "llm", "nlp", "rpa"}


def _has(term: str, text: str) -> bool:
    return re.search(r"(?<![a-z0-9])" + re.escape(term.lower()) + r"(?![a-z0-9])", text) is not None


DE_TITLE = re.compile(r"\b(m/w/d|w/m/d|m/w/x|techniker|administrator|fachinformatiker|systemintegration|"
                      r"experte|berater|leitung|sachbearbeiter|entwickler\b|spezialist|betreuer)", re.I)


def pick_tier(low: str, kw: dict, title: str = ""):
    """Whole-word match. Generic terms count only in the title; specific terms count anywhere
    if they hit the title, otherwise at least two distinct specific hits are needed."""
    t = title.lower()
    for tier, key in (("Gold", "gold"), ("Silver", "silver"), ("Bronze", "bronze")):
        terms = kw.get(key, [])
        title_hits = [k for k in terms if _has(k, t)]
        body_hits = [k for k in terms if k.lower() not in GENERIC and _has(k, low)]
        hits = title_hits + [k for k in body_hits if k not in title_hits]
        if title_hits or len(body_hits) >= 2:
            return tier, hits
    return None, []


def evaluate(job: Job, cfg: dict, prefilter_only: bool = False) -> Job:
    """Fill gate/reason/tier/score/german/flags on job. prefilter_only skips checks that need the description."""
    f, kw = cfg["filters"], cfg["keywords"]
    text = f"{job.title}\n{job.desc}\n{job.tags}\n{job.salary}"
    low = text.lower()
    job.flags, job.hits = [], []
    job.tier, job.hits = pick_tier(low, kw, job.title)

    def skip(reason):
        job.gate, job.reason, job.score = "Skip", reason, 0
        return job

    if SENIOR_TITLE.search(job.title):
        return skip("senior title")
    if prefilter_only:
        job.gate = "Pending"
        return job
    if not job.tier:
        return skip("no lane keyword")
    yrs = min_required_years(job.desc)
    if yrs >= f["max_required_years"]:
        return skip(f"{yrs}+ years required")
    job.salary_max = stated_salary_max(text)
    if job.salary_max and job.salary_max < f["salary_floor"]:
        return skip(f"stated salary {job.salary_max} below floor")
    if DE_MANDATORY.search(text):
        job.german = "Mandatory"
    elif DE_PLUS.search(text):
        job.german = "Plus"
    elif german_written(job.desc):
        job.german = "Mandatory"
        job.flags.append("posting written in German")
    elif DE_TITLE.search(job.title) and not EN_SIGNAL.search(text):
        job.german = "Mandatory"
        job.flags.append("German-language title")
    else:
        job.german = "Unclear"
    english = bool(EN_SIGNAL.search(text))
    if english:
        job.flags.append("English signal")
    if yrs:
        job.flags.append(f"{yrs}+ yrs")
    if job.german == "Mandatory" and not f["allow_german_override"]:
        return skip("German mandatory")
    score = {"Gold": 70, "Silver": 62, "Bronze": 50}[job.tier]
    score += 5 if JUNIOR.search(text) else 0
    score += 5 if english else 0
    score += 3 if job.german == "Plus" else 0
    score += 2 * min(len(job.hits), 3)
    if any(c.lower() in job.location.lower() for c in cfg.get("preferred_cities", [])):
        score += 2
    if job.german == "Mandatory":
        score -= 25
    job.score = max(0, min(100, score))
    job.gate = "Override-only" if job.german == "Mandatory" else "Pass"
    job.reason = ""
    job.residence = "Blue Card likely" if job.salary_max >= f["blue_card_threshold"] else "Check salary"
    return job
