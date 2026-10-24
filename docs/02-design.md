# Phase 2: Design (job-radar v1.0)

## Architecture
```
GitHub Actions (cron)           config.yaml  profile.yaml  watchlists/*.yaml
        |                                 |
        v                                 v
   radar scan --> sources/ --> [Job] --> classify --> store (state.json) --> report (md/json/csv)
                     |                       ^              |                    |--> GitHub issue
        ba.py  arbeitnow.py                  |              |                    |--> notion_sync (optional)
        ats.py careers.py                    |              v
                     \--- sweep (detect ATS from apply URL) --> discovered companies --> ats.py (next run)

   radar funding  --> funding.py --> out/funding.md           (weekly)
   radar outreach --> outreach.py + templates/ --> out/outreach/*.md   (never sends)
   radar selfcheck
```

## Modules and contracts
| Module | Responsibility | Key functions |
|---|---|---|
| `models.py` | Data class `Job` | `Job.key()` dedupe key |
| `http.py` | One place for network access, retries, delay, health counters | `fetch(url, ...) -> json/text/None`, `HEALTH` |
| `classify.py` | Gates, German detection, tier, score | `evaluate(job, cfg) -> job` |
| `sources/ba.py` | BA search and details | `search(cfg)`, `enrich(job)` |
| `sources/arbeitnow.py` | Arbeitnow API | `fetch_all(cfg)` |
| `sources/ats.py` | Seven ATS adapters, `detect_ats(url)` | `fetch_company(entry)` |
| `sources/careers.py` | JSON-LD and change detection | `fetch_page(entry, state)` |
| `store.py` | JSON state: seen, lifecycle, discovered companies, page hashes | `State.load/save`, `mark_*` |
| `pipeline.py` | Orchestration, sweep, lifecycle | `run_scan(cfg, state)` |
| `report.py` | Markdown, JSON, CSV | `write_reports(...)` |
| `notion_sync.py` | Optional push to Notion | `push(results, cfg)` |
| `funding.py` | RSS funding radar | `run(cfg)` |
| `outreach.py` | Template rendering with guard | `render_all(cfg)` |
| `cli.py` | `scan`, `funding`, `outreach`, `selfcheck` | |

## Data model
`Job`: id, source, feed, title, company, location, url, apply_url, date, desc, tags, salary, plus classification fields gate, reason, tier, score, german, flags, hits, residence.
State file `state.json`: `jobs{id: {first_seen,last_seen,feed,title,company,url,tier,gate,status}}`, `companies{key: {name,ats,token,added,source_job}}`, `pages{url: hash}`, `runs[last 30]`.

## Classification rules (deterministic)
1. Senior title regex, then required years (largest "N years" in text) at or above `max_required_years`.
2. Stated annual salary (maximum figure in a plausible range) below `salary_floor` -> skip.
3. German: mandatory regex -> Mandatory; plus regex -> Plus; text mostly German words -> Mandatory with flag; else Unclear.
4. Tier: first of Gold, Silver, Bronze whose keyword list matches title, tags or description.
5. Score: base (Gold 70, Silver 62, Bronze 50) + junior 5 + English signal 5 + German plus 3 + 2 per matched keyword (max 3) + preferred-city bonus 2, minus 25 if German mandatory (override-only list). Clamp 0-100.
6. Residence hint: stated salary at least `blue_card_threshold` -> "Blue Card likely", else "Check salary".

## Sweep design
A posting that passes and whose `apply_url` matches an ATS pattern yields `(ats, token)`. The company joins `state.companies`; the next run polls its feed and classifies every role. Companies without a recognisable ATS stay in the report as "careers page to watch".

## Failure handling
Each source runs inside a try/except. Network helpers return `None` and increment per-host failure counters. If every call to a source fails, the digest header says so and the issue title carries a warning.

## Security and compliance
No secrets in code. Contacts only from public company pages. Outreach is drafted, not sent. robots.txt is checked before fetching HTML career pages.

## Traceability (requirement -> module -> test)
F1 `sources/ba.py` -> `test_ba.py`; F2 `arbeitnow.py` -> `test_arbeitnow.py`; F3, F5 `ats.py`, `pipeline.py` -> `test_ats.py`, `test_pipeline.py`; F4 `careers.py` -> `test_careers.py`; F6-F8 `classify.py` -> `test_classify.py`; F9-F10 `store.py`, `pipeline.py` -> `test_store.py`, `test_pipeline.py`; F11 `report.py` -> `test_pipeline.py`; F13 `notion_sync.py` -> `test_notion.py`; F14 `funding.py` -> `test_funding.py`; F15-F16 `outreach.py` -> `test_outreach.py`; F17 `http.py` -> `test_pipeline.py`; F18 `cli.py` -> `test_selfcheck.py`.
