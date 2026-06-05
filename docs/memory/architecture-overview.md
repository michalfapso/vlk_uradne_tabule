# Architecture Overview

## Purpose

Automated monitoring system for Slovak environmental office notice boards (úradné tabule).
Scrapes two government websites daily, converts PDF documents to text, runs LLM analysis,
performs GIS lookups, and publishes results to a web interface.

**Audience:** Employees of Lesoochranárske zoskupenie VLK who need to find administrative
proceedings (správne konania) in protected areas to decide whether to intervene.

## End-to-End Data Flow

```
minv.sk ──┐
           ├──► run_scraping.py ──► data/scraped/*.json
minzp.sk ─┘

data/scraped/*.json ──► run_processing.py
    ├── diff against existing data/docs/ (skip already-processed)
    ├── filter: last 4 days only
    └── for each new document:
         ├── download from URL
         ├── convert to text (PDF→PyMuPDF, OCR fallback via Gemini)
         ├── extract law references (regex)
         ├── GIS: cadastral parcel → protected area intersection
         ├── GIS fallback: Nominatim geocoding
         ├── LLM analysis → analysis.json (Gemini via litellm)
         └── save to data/docs/{source}/{kraj}/{okres}/{docId}/

data/docs/ ──► Astro build ──► static HTML ──► GitHub Pages
```

## System Boundaries

| Component | Language | Location |
|---|---|---|
| Scrapers | Python | `analyzer/scrapers/` |
| Processing orchestrator | Python | `analyzer/run_processing.py` |
| Document processor | Python | `analyzer/shared/document_processor.py` |
| LLM client | Python (litellm) | `analyzer/shared/llm_analyzer.py` |
| GIS analysis | Python (geopandas) | `analyzer/shared/cadastral_parcels_ogc.py` |
| Geocoding fallback | Python | `analyzer/shared/gis_geocoding.py` |
| Web frontend | Astro + React | `website/` |
| User data backend | Convex | `website/convex/` |
| CI/CD | GitHub Actions | `.github/workflows/` |
| Document data | Git submodule | `data/` |

## Key Design Decisions

- **Data is a git submodule** — `data/` lives in a separate repository so it can be updated
  by CI without touching main repo history.
- **GIS files are not committed** — `data/protected_areas/` and `data/cadaster/` are uploaded
  as CI artifacts and synced locally via `analyzer/sync_github_data.sh`.
- **LLM prompt is a file** — `analyzer/shared/analyze_text_document_prompt.md` is the full
  prompt, version-controlled alongside the code.
- **Static frontend** — Astro builds to pure HTML/JS; no server needed. Convex is only needed
  for the optional user tagging feature.
- **Two data sources, unified format** — `run_processing.py` transforms both minv and minzp
  scraped data into a common `{url, source, original_data}` structure before processing.
