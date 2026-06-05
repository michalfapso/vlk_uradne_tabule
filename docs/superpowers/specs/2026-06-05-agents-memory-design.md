# Design: AGENTS.md Files, Project Memory, and Update-Memory Skill

**Date:** 2026-06-05
**Status:** Approved

---

## Overview

This spec covers three related improvements to how AI agents (and human contributors) gain context about this project:

1. **Rewrite `./AGENTS.md`** — translate to English, expand with subdirectory pointers
2. **Create subdirectory `AGENTS.md` files** — in `./analyzer`, `./data`, `./website`
3. **Create `./docs/memory/`** — flat topic files agents load selectively per task
4. **Create `./skills/update-memory.md`** — a skill for updating memory at end of session

All content in English, with Slovak terms in braces where non-obvious (e.g. "district (okres)").

---

## 1. Main `./AGENTS.md`

Replaces the existing Slovak-language file. Sections:

- **Project purpose** — Analyzing documents published on notice boards (úradné tabule) of district environmental offices. Goal: help employees of Lesoochranárske zoskupenie VLK identify administrative proceedings (správne konania) affecting protected areas (chránené územia, 5th degree protection, Natura 2000).
- **Directory structure** — one-line description per top-level directory
- **Subdirectory guides** — explicit list pointing to `analyzer/AGENTS.md`, `data/AGENTS.md`, `website/AGENTS.md`, `docs/memory/INDEX.md`
- **Running the system** — brief notes on local vs. CI execution

---

## 2. Subdirectory `AGENTS.md` Files

### `analyzer/AGENTS.md`
- Purpose of the analyzer subsystem
- Script entry points: `run_scraping.py`, `run_processing.py`
- Pipeline order: scrape → diff → PDF→text → LLM analysis → GIS → save
- Key shared utilities in `shared/`: `document_processor.py`, `llm_analyzer.py`, `pdf_to_txt.py`, `law_references.py`, `cadastral_parcels_ogc.py`, `gis_geocoding.py`
- External APIs: Google Gemini (`GOOGLE_API_KEY`), OGC cadastral proxy (`GIS_PROXY_URL`, `GIS_PROXY_AUTH`), Nominatim, Overpass
- How to run locally: `local_process.sh`
- Python dependencies: `requirements.txt`

### `data/AGENTS.md`
- Directory layout: `scraped/`, `docs/`, `laws/`, `protected_areas/`, `cadaster/`, `convex/`
- Per-document path pattern: `data/docs/{source}/{region}/{district}/{docId}/`
- Files per document: `meta.json`, `analysis.json`, `text.txt`, `parcels.geojson`, `status.json`
- `meta.json` schema (fields: url, source, datum, nazov, kraj, okres, kategoria)
- `analysis.json` schema (all top-level fields with types)
- What is gitignored: `protected_areas/`, `cadaster/` (large GIS files, synced from CI artifacts)
- Data is a git submodule — separate repo from the main codebase

### `website/AGENTS.md`
- Framework: Astro 5 (static output) + React 19 islands + Tailwind CSS 4
- Main pages: `src/pages/index.astro` (document grid, last 7 days), `src/pages/doc/[docId].astro` (detail view)
- Key components: `TanStackDocumentGrid.tsx` (main table), `Header.tsx`, `ConvexClientProvider.tsx`, `AuthSection.tsx`
- Convex backend: `convex/` subdirectory — `docTags` table (userId, docId, tag, docDate), auth tables
- Dev server: `npm run dev` from `./website/`
- Build: `npm run build` → static files deployed to GitHub Pages at `/vlk_uradne_tabule/`

---

## 3. `docs/memory/` — Flat Topic Files

Location: `docs/memory/`

### `INDEX.md`
Lists all memory files with a one-line hook. Referenced from main `AGENTS.md`. Agents read this at session start and load only the files relevant to their current task.

### Topic files (9 files)

| File | Content | Load when... |
|---|---|---|
| `architecture-overview.md` | End-to-end system map, data flow diagram, tech stack summary | Starting any non-trivial task |
| `analyzer-pipeline.md` | Script execution order, subprocess chains, processing flags, date filtering, deduplication logic | Working on scraper or processor |
| `llm-analysis.md` | Gemini model config, litellm usage, prompt file location, output JSON schema, token cost tracking | Modifying LLM prompt or analysis logic |
| `gis-geocoding.md` | GIS fallback chain (parcel → cadastral zone → Nominatim → Overpass), OGC proxy setup, protected area shapefiles | Debugging GIS or geocoding |
| `data-schema.md` | Full `meta.json` and `analysis.json` field-by-field reference, scraped JSON structure | Reading/writing document data |
| `website-stack.md` | Astro config, React islands pattern, TanStack table setup, component hierarchy, Tailwind notes | Working on frontend |
| `convex-auth.md` | Convex table schemas, auth setup, tagging flow, ConvexClientProvider architecture | Working on Convex or auth |
| `ci-cd.md` | GitHub Actions workflow overview, job dependencies, artifact flow, secrets used | Modifying CI/CD pipelines |
| `laws-references.md` | Law citation extraction approach, `registry.json` format, regex patterns, supported laws | Working on law reference features |

---

## 4. `./skills/update-memory.md`

A plain Markdown guide (not a registered superpowers plugin). Invoked manually at end of session with: `Skill` tool pointing to `./skills/update-memory.md`, or by telling the agent to follow the instructions in that file.

### Skill content outline

The skill instructs the agent to:

1. **Identify insights worth saving** — review what was discovered, debugged, or changed in the session; an insight qualifies if it would save a future agent 5+ minutes of exploration
2. **Update relevant memory files** — open the affected `docs/memory/*.md` files and add/correct content; do not duplicate content already present
3. **Add new memory files if needed** — if a topic has no file yet, create one and add it to `INDEX.md`
4. **Update subdirectory `AGENTS.md` if interface changed** — e.g. new env var, new entry point script, schema change
5. **Do not update memory for ephemeral session state** — in-progress work, temporary workarounds, or things already obvious from the code
6. **Commit memory updates** — `git add docs/memory/ analyzer/AGENTS.md data/AGENTS.md website/AGENTS.md AGENTS.md` then commit with message `docs: update project memory`

---

## File Locations Summary

```
./AGENTS.md                          (updated)
./analyzer/AGENTS.md                 (new)
./data/AGENTS.md                     (new)
./website/AGENTS.md                  (new)
./docs/memory/INDEX.md               (new)
./docs/memory/architecture-overview.md
./docs/memory/analyzer-pipeline.md
./docs/memory/llm-analysis.md
./docs/memory/gis-geocoding.md
./docs/memory/data-schema.md
./docs/memory/website-stack.md
./docs/memory/convex-auth.md
./docs/memory/ci-cd.md
./docs/memory/laws-references.md
./skills/update-memory.md            (new)
```

Total: 1 updated file, 14 new files.
