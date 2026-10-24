# Change log

| Date | Change | Requirements | Tests |
|---|---|---|---|
| 2026-10-24 | v1.0.0 initial release | F1-F18 | 57 automated tests |
| 2026-10-24 | v1.0.1 after first live run: Arbeitnow limited to Germany (other country hosts dropped); tiering uses whole words, generic terms only count in the title, body needs 2 specific hits (accountant/lab roles were tiered Gold via "rollout"/"monitoring"); source health records the last error per host | F1, F6, N4 | 63 automated tests |
| 2026-10-24 | weekly.yml invalid YAML (colon in run value) fixed; all workflows now YAML-validated | F13 | manual |
| 2026-10-24 | BA search tries /pc/v6/jobs then v4/app, v4 (v4 returned 403 No match); state reset after tiering fix; Exyte URL replaced | F1, F5 | 64 automated tests |
