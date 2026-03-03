# Publications automation

This site auto-updates publications from Google Scholar profile `X8GzMrEAAAAJ`.

## What runs

- Script: `scripts/update_publications.py`
- Output: `publications.json`
- Frontend loader: `assets/js/publications.js`
- Workflow: `.github/workflows/update-publications.yml`

## Manual run (local)

```bash
/opt/anaconda3/envs/flow_match/bin/python -m pip install -r scripts/requirements-publications.txt
/opt/anaconda3/envs/flow_match/bin/python scripts/update_publications.py --user X8GzMrEAAAAJ --hl en --output publications.json
```

## Automatic run (GitHub Actions)

- Runs every Monday at 06:00 UTC and on manual trigger.
- If `publications.json` changed, it commits and pushes automatically.

## Caveat

Google Scholar has anti-bot protections. Some runs may fail if Google presents a challenge page. In that case, rerun manually or trigger the workflow later.
