# job-radar v1.0

Daily scan of German IT jobs for Tony: Bundesagentur für Arbeit, Arbeitnow, company ATS feeds and career pages. Gates (German requirement, seniority, years, salary floor), tiers (Gold, Silver, Bronze), company sweeps, a weekly funding radar, Nexthink-partner and agency watchlists, outreach drafts. It never applies and never sends anything.

Docs (waterfall phases): `docs/01-requirements.md`, `docs/02-design.md`, `docs/03-test-plan.md`, `docs/04-operations.md`.

```
python -m radar selfcheck     # validate config and watchlists
python -m radar scan          # daily scan -> out/latest.md, out/new.json, out/results.csv, state.json
python -m radar funding       # weekly funding news -> out/funding.md
python -m radar outreach      # drafts -> out/outreach/*.md (needs profile.yaml completed)
python -m pytest -q
```

Setup and daily/weekly routine: `docs/04-operations.md`. First live run is the acceptance test (`docs/03-test-plan.md`).
