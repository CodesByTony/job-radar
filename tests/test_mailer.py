from radar import mailer
from radar.models import Job


def job(title, gate, tier="Gold"):
    j = Job(id=title, source="t", feed="t", title=title, company="Acme", location="Ulm", url="https://x/" + title,
            apply_url="", date="")
    j.gate, j.tier, j.score, j.german, j.residence, j.flags = gate, tier, 70, "Unclear", "Check salary", []
    return j


def res(rows, down=()):
    return {"results": rows, "down": list(down)}


def test_subject_counts_and_links():
    s, t, h = mailer.build_email(res([job("A", "Pass"), job("B", "Override-only")]))
    assert "1 new to apply" in s and "1 need German" in s and "https://x/A" in t and "https://x/A" in h


def test_empty_day_still_builds():
    s, t, _ = mailer.build_email(res([]))
    assert "0 new" in s and "No new postings" in t


def test_warning_in_subject():
    assert "WARNING" in mailer.build_email(res([], ["rest.arbeitsagentur.de"]))[0]


def test_skips_without_secrets():
    assert "skipped" in mailer.send(res([]), env={})


def test_failure_does_not_raise(monkeypatch):
    def boom(*a, **k):
        raise OSError("no network")
    monkeypatch.setattr(mailer.smtplib, "SMTP_SSL", boom)
    assert "FAILED" in mailer.send(res([]), env={"GMAIL_USER": "a@b.c", "GMAIL_APP_PASSWORD": "x"})


def test_sends_to_self_only(monkeypatch):
    sent = {}

    class S:
        def __init__(self, *a, **k): pass
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def login(self, u, p): sent["login"] = u
        def send_message(self, m): sent["to"] = m["To"]

    monkeypatch.setattr(mailer.smtplib, "SMTP_SSL", S)
    assert "sent" in mailer.send(res([job("A", "Pass")]), env={"GMAIL_USER": "me@gmail.com", "GMAIL_APP_PASSWORD": "x"})
    assert sent["to"] == "me@gmail.com"
