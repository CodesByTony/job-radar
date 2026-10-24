# Phase 4: Test plan and results

## Automated (pytest, run on every push by `ci.yml`)
| Area | Tests | Covers |
|---|---|---|
| Classification | `test_classify.py` (ten table cases plus edge cases) | F6, F7, F8, N5: senior, years, salary floor, German mandatory / plus / written-in-German, tiers, score bounds |
| Sources | `test_sources.py` | F1-F4: BA search and details (key header, base64 id), Arbeitnow paging, Greenhouse, Lever (EU host), Personio XML, failure handling, JSON-LD, change detection, robots.txt |
| Pipeline | `test_pipeline.py` | F5, F9-F11, F17, N4: dedupe across sources, lifecycle, failed feed does not close jobs, sweep adds the employer, BA detail budget, one source down |
| Modules | `test_modules.py` | F13-F16, F18: funding filter, Notion payload, outreach guard and no-guessing, selfcheck |

Result at build time: **57 passed**. Selfcheck on committed config: ok. Outreach correctly refuses to render while `availability_line` is `SET_ME`.

## Acceptance test (needs the live internet; first run on GitHub)
| # | Step | Pass criterion |
|---|---|---|
| A1 | Actions > daily-scan > Run workflow | Run finishes green |
| A2 | Open the issue or `out/latest.md` | Source health shows ok calls for `rest.arbeitsagentur.de` and `www.arbeitnow.com` |
| A3 | Check five Gold/Silver/Bronze results against the full posting | At least four of five tier, German flag and level gate are correct |
| A4 | Check three skipped German-mandatory examples in `out/new.json` override list | The quoted requirement exists in the posting |
| A5 | Wait for the e-mail from GitHub | Digest arrives |
| A6 | Add one company by hand to `watchlists/companies.yaml` | Next run lists its roles |

Known risks to watch in A2: the BA interface is unofficial. If every call fails, the issue title carries a WARNING and the digest shows the hosts. If BA fails but Arbeitnow works, the rest of the pipeline is still valid; send the log and the BA adapter gets adjusted.

## Defect log
| ID | Defect | Fix |
|---|---|---|
| D1 | "120 years" parsed as 12 years required (false skip) | Regex now requires 1-2 standalone digits (`test_years`) |
