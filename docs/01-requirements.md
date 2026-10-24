# Phase 1: Requirements specification (job-radar v1.0)

Status: frozen for the build. Changes after sign-off go through a written change request in `docs/changes.md`.

## 1. Purpose
A personal job-search system for Tony Thomas: find, filter, rank and track IT jobs across all of Germany every day, watch Nexthink partners, agencies and employers directly, and prepare outreach drafts. A human reads every result and sends every message and application.

## 2. Users and context
One user (Tony). Runs unattended on GitHub Actions from a private repository. Results reach him as a GitHub issue (email via GitHub notifications), files in `out/`, and optionally Notion.

## 3. Functional requirements
| ID | Requirement |
|---|---|
| F1 | Discover postings nationwide from the Bundesagentur für Arbeit job search (20+ configurable queries, paged, detail fetch for candidates). |
| F2 | Discover postings from the Arbeitnow API (paged). |
| F3 | Poll company ATS feeds: Greenhouse, Lever, Personio, SmartRecruiters, Ashby, Workable, Recruitee. |
| F4 | Read JSON-LD `JobPosting` data from configured career pages; if none exists, detect page changes by content hash. |
| F5 | Company sweep: when a posting passes, detect its employer's ATS from the apply URL; add the company to the discovered list; poll it from then on, scoring all its roles across Germany. |
| F6 | Gate every posting: skip senior titles, required years at or above the configured limit, stated salary below the floor, no lane keyword. |
| F7 | German-language gate: English required; German "a plus" passes; German mandatory is dropped or, if configured, listed separately as override-only. Postings written entirely in German count as German-mandatory. |
| F8 | Tier every passing posting Gold, Silver or Bronze from configurable keyword lists, and compute a heuristic score 0-100. |
| F9 | Deduplicate across runs (stable ids) and across sources (company + title + city key). |
| F10 | Track lifecycle: first seen, last seen, disappeared (for ATS feeds fetched successfully). |
| F11 | Produce a daily Markdown digest, a JSON file of new results and a CSV export. |
| F12 | Open a GitHub issue with the digest when new postings pass. |
| F13 | Optionally push passing postings to the Notion Jobs database (needs a token). |
| F14 | Weekly funding radar: read configured RSS feeds, flag German funding or expansion news, write `out/funding.md`. |
| F15 | Watchlists for Nexthink partners, agencies and employers with public contact data and verification status. |
| F16 | Generate outreach drafts (agency, partner, employer) from templates. Never send. Refuse to render while profile placeholders are unset. |
| F17 | Report source health (successful and failed calls per host) at the top of every digest and in the issue title when a source is fully down. |
| F18 | A self-check command validates configuration and watchlists. |

## 4. Non-functional requirements
| ID | Requirement |
|---|---|
| N1 | Polite access: at least 0.4 s between calls, identifiable User-Agent, retry with backoff on 429/503, honour robots.txt for HTML pages. |
| N2 | No logins, no scraping of LinkedIn, Xing, StepStone, Indeed or Glassdoor, no auto-apply, no sending of messages. |
| N3 | No personal data about third parties beyond public company contact points. No guessing of personal e-mail addresses. |
| N4 | Failure isolation: one failing source or company never stops the run. |
| N5 | Deterministic classification covered by automated tests (at least the cases in the test plan). |
| N6 | Runtime under 15 minutes per daily run on GitHub-hosted runners. |
| N7 | No secrets in the repository; tokens only via GitHub Actions secrets. |
| N8 | Configuration in YAML; no code changes needed to add queries, keywords or companies. |

## 5. Constraints and assumptions
- The Bundesagentur interface is unofficial and uses a public key; its behaviour may change. **Not verified live at build time.** First live run is an acceptance test (see test plan).
- Arbeitnow terms of use and rate limits are not published; keep volume low.
- Salary figures in postings are rarely stated; "unknown" never fails the salary gate.
- German-requirement detection is text based and will have false positives and negatives; every skip records the matching phrase.

## 6. Out of scope for v1.0
Auto-applying, LinkedIn/Xing/StepStone/Indeed scraping, CV generation inside the pipeline (done by Claude with `cv-master.md`), Workday scraping (undocumented endpoint, grey area).

## 7. Acceptance criteria
1. All automated tests pass.
2. First live run completes without an unhandled exception and the health table shows at least one source with successful calls.
3. At least one passing posting is correctly classified when compared by hand against its full text (spot check of five).
4. Digest issue arrives by e-mail.
5. `selfcheck` passes on the committed configuration.
