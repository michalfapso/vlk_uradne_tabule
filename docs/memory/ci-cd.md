# CI/CD — GitHub Actions

## Main Orchestrator: `daily-scrape-analyze-deploy.yml`

Triggered manually (`workflow_dispatch`) or on a schedule (currently commented out —
was `0 18 * * *` UTC = 20:00 CEST).

```yaml
jobs:
  scrape:    uses: ./.github/workflows/scrape.yml
  process:   uses: ./.github/workflows/process.yml   # needs: scrape
  deploy:    uses: ./.github/workflows/reusable-build-deploy.yml
             # needs: process, only if process.outputs.data_changed == 'true'
```

## Scrape Job (`scrape.yml`)

- Runs `python analyzer/run_scraping.py`
- Uploads artifact: `scraped-data` (contents of `data/scraped/`)
- Needs: `GEMINI_API_KEY` secret

## Process Job (`process.yml`)

- Installs: `pandoc`, `libreoffice` (for non-PDF document conversion)
- Checks out repo with `submodules: true`
- Sets up Python env via `.github/actions/analyzer-setup`
- Downloads `scraped-data` artifact from scrape job
- Runs `python -u analyzer/run_processing.py`
- Env vars: `GEMINI_API_KEY`, `GIS_PROXY_URL`, `GIS_PROXY_AUTH`
- Archives data: copies `*_documents.json` → `*_documents_old.json` for next run's diff
- Commits changes to `data/` submodule, pushes to submodule remote
- Updates main repo submodule pointer, commits and pushes
- Outputs: `data_changed` (bool), `new_commit_sha`

## Deploy Job (`reusable-build-deploy.yml`)

- Only runs if `process.outputs.data_changed == 'true'`
- Builds Astro site: `npm run build` in `website/`
- Deploys to GitHub Pages via `actions/deploy-pages`
- Deployed URL: `https://michalfapso.github.io/vlk_uradne_tabule/`

## Other Workflows

| File | Purpose |
|---|---|
| `ci.yml` | General code quality checks |
| `website-only.yml` | Manual website rebuild without scraping/processing |

## Reusable Actions (`/.github/actions/`)

**`analyzer-setup/`** — Sets up Python environment:
- Creates venv
- Installs `analyzer/requirements.txt`
- Caches pip downloads

**`download-workflow-artifact/`** — Downloads artifacts from a specific workflow run,
used by `process.yml` to get scraped data from a remote `scrape.yml` run.

## Secrets Required

| Secret | Used by |
|---|---|
| `GEMINI_API_KEY` | scrape.yml, process.yml — Gemini LLM and OCR |
| `GIS_PROXY_URL` | process.yml — Slovak cadastral OGC proxy |
| `GIS_PROXY_AUTH` | process.yml — Auth token for GIS proxy |
| `GH_PAT` | process.yml — GitHub Personal Access Token for pushing to data submodule |
