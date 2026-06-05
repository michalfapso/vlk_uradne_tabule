# VLK Environmental Document Analyzer — Project Guide

This project analyzes documents published on official notice boards (úradné tabule) of district
environmental offices (okresné úrady životného prostredia). The goal is to help employees of
Lesoochranárske zoskupenie VLK (VLK forest conservation NGO) quickly identify administrative
proceedings (správne konania) affecting protected areas (chránené územia — 5th-degree protection
and Natura 2000 territory).

Two source websites are monitored:
- **minv.sk** — Ministry of Interior district offices
- **minzp.sk** — Ministry of Environment district offices

## Directory Structure

| Path | Description |
|---|---|
| `./.github/` | GitHub Actions workflows for daily scraping, analysis, and deployment |
| `./analyzer/` | Python scripts for scraping, PDF→text conversion, LLM analysis, GIS |
| `./analyzer/scrapers/` | Source-specific scrapers (minv, minzp) |
| `./analyzer/shared/` | Core utilities used by all processing scripts |
| `./data/` | Git submodule — all scraped and processed document data |
| `./data/scraped/` | Raw JSON from scrapers |
| `./data/docs/` | Per-document analysis results |
| `./data/laws/` | Law registry and citation data |
| `./tests/` | Unit tests |
| `./website/` | Astro + React frontend that renders the document grid |
| `./docs/` | Design specs, implementation plans, and project memory |
| `./skills/` | Project-specific AI agent skills |

## Subdirectory Guides

Load these for deeper context on specific areas:

- `analyzer/AGENTS.md` — scraping and analysis pipeline, entry points, env vars
- `data/AGENTS.md` — data schema, directory layout, gitignored files
- `website/AGENTS.md` — frontend stack, components, Convex backend, dev commands
- `docs/memory/INDEX.md` — topic-specific memory files; read the index, then load only files relevant to your current task

## Running the System

**Locally:**
```bash
cd analyzer
bash local_process.sh   # sync data, scrape, process, prepare website
```

**CI (automated daily):** `.github/workflows/daily-scrape-analyze-deploy.yml` — runs scrape → process → deploy on a schedule.

**Required env vars:** `GEMINI_API_KEY`, `GIS_PROXY_URL`, `GIS_PROXY_AUTH` (see `analyzer/AGENTS.md` for details).
