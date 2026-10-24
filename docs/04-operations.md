# Phase 5: Deployment and operations

## One-time setup
1. Create the private repo `CodesByTony/job-radar` (empty, no README).
2. Claude pushes the code (or upload the zip contents).
3. Settings > Actions > General > Workflow permissions: **Read and write**; allow GitHub Actions to create issues.
4. Watch the repo for email notifications (Watch > All activity).
5. Edit `profile.yaml`: replace the `SET_ME` availability line with one truthful sentence (start date and hours). Until then outreach drafts are not generated.
6. Optional Notion sync: create a Notion integration, share the Jobs database with it, add the token as repository secret `NOTION_TOKEN`, set `notion.enabled: true` in `config.yaml`.
7. Run the **daily-scan** workflow once by hand and complete the acceptance test in `03-test-plan.md`.

## Daily routine (about 20 minutes)
1. Read the digest e-mail. Gold first.
2. Paste promising links into Claude for a full read, a score with quoted evidence, and a tailored CV and letter from `cv-master.md`.
3. Apply yourself. Mark the row in Notion.
4. Add LinkedIn, Xing and StepStone alert e-mails by pasting them to Claude (no automation on those platforms).

## Weekly routine
- Monday: read the funding issue, shortlist companies, add careers pages or ATS tokens to `watchlists/`.
- Review `out/outreach/*.md` drafts; verify a public contact point on the company's own site; send yourself; set `status: contacted` in `targets.yaml`.
- Fix or delete watchlist URLs that show "fetch failed".

## Tuning
All in YAML: queries, keywords, years limit, salary floor, German override. After 30 results compare scores with outcomes and adjust weights in `classify.py` (one place).

## Troubleshooting
| Symptom | Likely cause | Action |
|---|---|---|
| Issue title has WARNING sources down | Host unreachable or API changed | Open the run log; send it to Claude |
| Zero results for days | Filters too strict | Check `Fetched/new/passed` line; relax `max_required_years` or keywords |
| Same job twice | Different company spelling across sources | Add normalisation in `Job.key()` |
| Push rejected | Concurrent run | Re-run; the workflow rebases |

## Compliance notes
No login, no automation of LinkedIn, Xing, StepStone, Indeed or Glassdoor. The radar reads only public APIs and public career pages, honours robots.txt for HTML, uses delays and an identifying User-Agent. It never sends e-mail or applies. Terms of the Bundesagentur interface and Arbeitnow were not verified; if either objects, switch the source off in `config.yaml`.

## Changes after sign-off
Record in `docs/changes.md` with date, reason, affected requirement IDs and test updates.
