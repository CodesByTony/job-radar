"""Daily e-mail digest to yourself through Gmail SMTP (app password in GitHub secrets).
Sends only to MAIL_TO (default: the Gmail account itself). Never applies to anything."""
from __future__ import annotations

import datetime as dt
import html
import os
import smtplib
import ssl
from email.message import EmailMessage


def build_email(result: dict) -> tuple[str, str, str]:
    """Return (subject, plain text, html)."""
    today = dt.date.today().isoformat()
    passing = [r for r in result["results"] if r.gate == "Pass"]
    override = [r for r in result["results"] if r.gate == "Override-only"]
    n = len(passing)
    warn = f" | WARNING: {', '.join(result['down'])} down" if result["down"] else ""
    subject = f"Job radar {today}: {n} new to apply" + (f", {len(override)} need German" if override else "") + warn
    T, H = [f"Job radar {today}", ""], [f"<h2>Job radar {today}</h2>"]
    if result["down"]:
        T.append(f"WARNING: every call failed for {', '.join(result['down'])}.\n")
        H.append(f"<p><b>WARNING:</b> every call failed for {html.escape(', '.join(result['down']))}.</p>")
    if not passing:
        T.append("No new postings passed the gates today.")
        H.append("<p>No new postings passed the gates today.</p>")
    for tier in ("Gold", "Silver", "Bronze"):
        rows = sorted([r for r in passing if r.tier == tier], key=lambda r: -r.score)[:25]
        if not rows:
            continue
        T += [f"== {tier} ({len(rows)}) =="]
        H.append(f"<h3>{tier} ({len(rows)})</h3><ul>")
        for r in rows:
            bits = ", ".join(list(r.flags) + [f"German: {r.german}", r.residence])
            T += [f"- {r.title} | {r.company} | {r.location} | score {r.score} | {bits}", f"  {r.url}"]
            H.append(f'<li><a href="{html.escape(r.url)}">{html.escape(r.title)}</a> - {html.escape(r.company)}, '
                     f"{html.escape(r.location)} (score {r.score}; {html.escape(bits)})</li>")
        T.append("")
        H.append("</ul>")
    if override:
        T += [f"== German required, your risk call ({len(override)}) =="]
        H.append(f"<h3>German required, your risk call ({len(override)})</h3><ul>")
        for r in override[:15]:
            T.append(f"- {r.title} | {r.company} | {r.location} | {r.url}")
            H.append(f'<li><a href="{html.escape(r.url)}">{html.escape(r.title)}</a> - {html.escape(r.company)}, {html.escape(r.location)}</li>')
        H.append("</ul>")
    T += ["", "Paste any link to Claude for a full read, a fit score and a tailored CV and letter. Apply yourself."]
    H.append("<p>Paste any link to Claude for a full read, a fit score and a tailored CV and letter. Apply yourself.</p>")
    return subject, "\n".join(T), "\n".join(H)


def send(result: dict, env=None) -> str:
    """Send the digest. Returns a status string; never raises (a mail problem must not fail the scan)."""
    env = env if env is not None else os.environ
    user, pw = env.get("GMAIL_USER", ""), env.get("GMAIL_APP_PASSWORD", "")
    if not user or not pw:
        return "e-mail skipped: GMAIL_USER / GMAIL_APP_PASSWORD secrets not set"
    to = env.get("MAIL_TO") or user
    subject, text, body = build_email(result)
    msg = EmailMessage()
    msg["Subject"], msg["From"], msg["To"] = subject, user, to
    msg.set_content(text)
    msg.add_alternative(body, subtype="html")
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=ssl.create_default_context(), timeout=30) as s:
            s.login(user, pw)
            s.send_message(msg)
        return f"e-mail sent to {to}"
    except Exception as e:  # noqa: BLE001
        return f"e-mail FAILED: {type(e).__name__}: {e}"
