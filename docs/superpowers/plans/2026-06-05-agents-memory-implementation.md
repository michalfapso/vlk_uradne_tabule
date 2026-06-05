# AGENTS.md Files, Project Memory & Update-Memory Skill — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create English-language AGENTS.md files for the root and each major subdirectory, a flat `docs/memory/` topic library, and a `skills/update-memory.md` skill — all populated with real project-specific content.

**Architecture:** Pure documentation — no code changes. Each file is self-contained and written in a single step. All files are committed together in one final commit.

**Tech Stack:** Markdown files, git.

---

## Files to Create or Modify

| Action | Path |
|---|---|
| Modify | `./AGENTS.md` |
| Create | `./analyzer/AGENTS.md` |
| Create | `./data/AGENTS.md` |
| Create | `./website/AGENTS.md` |
| Create | `./docs/memory/INDEX.md` |
| Create | `./docs/memory/architecture-overview.md` |
| Create | `./docs/memory/analyzer-pipeline.md` |
| Create | `./docs/memory/llm-analysis.md` |
| Create | `./docs/memory/gis-geocoding.md` |
| Create | `./docs/memory/data-schema.md` |
| Create | `./docs/memory/website-stack.md` |
| Create | `./docs/memory/convex-auth.md` |
| Create | `./docs/memory/ci-cd.md` |
| Create | `./docs/memory/laws-references.md` |
| Create | `./skills/update-memory.md` |

---

## Task 1: Rewrite `./AGENTS.md`

**Files:** Modify `./AGENTS.md`

- [ ] **Step 1: Overwrite `./AGENTS.md` with the new English content**

```markdown
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
```

- [ ] **Step 2: Verify the file looks correct**

```bash
head -30 AGENTS.md
```

Expected: English content starting with "# VLK Environmental Document Analyzer"

---

## Task 2: Create `./analyzer/AGENTS.md`

**Files:** Create `./analyzer/AGENTS.md`

- [ ] **Step 1: Write `./analyzer/AGENTS.md`**

```markdown
# Analyzer — Agent Guide

Python subsystem for scraping government websites, converting PDFs to text, running LLM analysis,
and performing GIS lookups. All scripts run from the repo root or from within `analyzer/`.

## Entry Points

| Script | Purpose | Run as |
|---|---|---|
| `run_scraping.py` | Orchestrates all scrapers in order | `python analyzer/run_scraping.py` |
| `run_processing.py` | Diffs, filters, and processes new documents | `python analyzer/run_processing.py` |
| `local_process.sh` | Full local pipeline: sync → scrape → process → prepare website | `bash analyzer/local_process.sh` |
| `prune_gis_files.py` | Removes old GIS temp files to save disk space | `python analyzer/prune_gis_files.py` |
| `backfill_meta_json.py` | Re-generates missing analysis.json for existing documents | `python analyzer/backfill_meta_json.py` |

## Pipeline Order

```
run_scraping.py
  → scrapers/minv_1_regions.py       → data/scraped/minv_1_regions.json
  → scrapers/minv_2_documents.py     → data/scraped/minv_2_documents.json
  → scrapers/minzp_2_documents.py    → data/scraped/minzp_2_documents.json

run_processing.py
  → load old + new scraped JSON
  → aggregate_and_transform()        unifies minv + minzp into common format
  → diff against data/docs/          skip already-processed docIds
  → filter by date                   default: last 4 days (DAYS_OLD_THRESHOLD)
  → for each new doc:
      document_processor.process_document()
        → download file (requests)
        → detect MIME type → choose converter
        → pdf_to_txt.py              native PyMuPDF, OCR fallback via Gemini
        → law_references.py          regex-based law citation extraction
        → cadastral_parcels_ogc.py   OGC API → parcel geometry
        → gis_geocoding.py           Nominatim geocoding fallback
        → llm_analyzer.py            Gemini LLM → analysis.json
        → save to data/docs/{source}/{kraj}/{okres}/{docId}/
```

## Key Shared Utilities (`analyzer/shared/`)

| File | Purpose |
|---|---|
| `document_processor.py` | Main per-document orchestration — download, convert, analyze, save |
| `llm_analyzer.py` | Calls Gemini via litellm; reads prompt from `analyze_text_document_prompt.md` |
| `pdf_to_txt.py` | PyMuPDF native extraction; falls back to Gemini OCR for scanned PDFs |
| `law_references.py` | Regex-based extraction of law citations (§, odseky, písmená) |
| `cadastral_parcels_ogc.py` | Queries Slovak cadastral OGC API for parcel geometry; checks protected area intersections |
| `gis_geocoding.py` | Nominatim geocoding for place names when no cadastral parcel is found |
| `gis_overpass.py` | Overpass API queries for geographic boundaries |
| `get_doc_id.py` | Derives unique `docId` string from a document URL |
| `log_handler.py` | Writes `status.json` files for per-document and per-region error tracking |
| `date_converter.py` | Slovak date string → ISO date parsing |
| `analyze_text_document_prompt.md` | The full LLM prompt (~10 KB); defines the JSON output schema |

## External APIs and Environment Variables

| API | Used by | Env var |
|---|---|---|
| Google Gemini (`gemini/gemini-3-flash-preview`) | `llm_analyzer.py`, `pdf_to_txt.py` (OCR) | `GEMINI_API_KEY` |
| Slovak Cadastral OGC API (skgeodesy.sk) | `cadastral_parcels_ogc.py` | `GIS_PROXY_URL`, `GIS_PROXY_AUTH` |
| Nominatim (OpenStreetMap) | `gis_geocoding.py` | none (public, requires User-Agent header) |
| Overpass API | `gis_overpass.py` | none (public) |

The cadastral API is accessed via a private proxy (`GIS_PROXY_URL`). Requests include
`X-Proxy-Auth: $GIS_PROXY_AUTH` header; the proxy forwards the original URL via `?url=` param.

## Python Dependencies

Install with: `pip install -r analyzer/requirements.txt`

Key packages: `litellm==1.79.0`, `geopandas==1.1.1`, `PyMuPDF==1.26.5`,
`beautifulsoup4==4.14.2`, `requests==2.32.5`, `pandas==2.3.3`, `python-dotenv==1.2.1`,
`shapely==2.1.2`.

## Dev Notes

- `run_processing.py` has a `PROCESS_SPECIFIC_DOC_IDS` variable near the top for debugging a single document; set it to a list of docIds and `FORCE_DOCUMENTS_REPROCESSING = True`.
- The LLM model is hardcoded in `llm_analyzer.py` as `"gemini/gemini-3-flash-preview"`.
- libreoffice and pandoc must be installed for non-PDF document conversion (`.docx`, `.rtf`, `.odt`, etc.).
```

- [ ] **Step 2: Verify**

```bash
head -10 analyzer/AGENTS.md
```

Expected: "# Analyzer — Agent Guide"

---

## Task 3: Create `./data/AGENTS.md`

**Files:** Create `./data/AGENTS.md`

- [ ] **Step 1: Write `./data/AGENTS.md`**

```markdown
# Data — Agent Guide

The `data/` directory is a **git submodule** (separate repository) — changes here must be
committed and pushed independently from the main repo. The main repo tracks the submodule
pointer, updated automatically by CI.

## Directory Layout

```
data/
├── scraped/                  Raw JSON from scrapers (committed)
│   ├── minv_1_regions.json
│   ├── minv_2_documents.json
│   ├── minv_2_documents_old.json
│   ├── minzp_2_documents.json
│   └── minzp_2_documents_old.json
├── docs/                     Per-document analysis tree (committed)
│   └── {source}/{kraj}/{okres}/{docId}/
│       ├── meta.json         Document metadata from scraper
│       ├── analysis.json     LLM analysis output
│       ├── text.txt          Extracted document text
│       ├── parcels.geojson   Cadastral parcel geometry (if found)
│       └── status.json       Processing errors/warnings
├── laws/                     Law registry (committed)
│   ├── registry.json         Regex patterns for identifying laws by name/number
│   ├── 543-2002.json         Full text index for nature protection law
│   └── 71-1967.json          Full text index for administrative procedure law
├── protected_areas/          GIS shapefiles — GITIGNORED, synced from CI artifacts
└── cadaster/                 Cadastral boundary data — GITIGNORED
```

Path example: `data/docs/minzp/Košický kraj/Spišská Nová Ves/ou-sn-oszp-2020-005175/`

Source is either `minv` or `minzp`. Kraj (region) and okres (district) come from the scraper.

## `meta.json` Schema

Stored at `data/docs/{source}/{kraj}/{okres}/{docId}/meta.json`.

```json
{
  "url": "https://www.minzp.sk/...",
  "source": "minzp",
  "datum": "2020-02-12",
  "nazov": "OU-SN-OSZP-2020/005175",
  "kraj": "Košický kraj",
  "okres": "Spišská Nová Ves",
  "kategoria": null
}
```

Fields: `url` (original document URL), `source` (`minv`|`minzp`), `datum` (ISO date published),
`nazov` (document title/reference number), `kraj` (region), `okres` (district), `kategoria`
(document category, may be null for minzp).

## `analysis.json` Schema

Produced by `analyzer/shared/llm_analyzer.py`. Key fields:

| Field | Type | Description |
|---|---|---|
| `cislo_konania_spisu` | string | Official case/file number (spis) |
| `cislo_rozhodnutia` | string\|null | Decision number if different from case number |
| `datum_dokumentu` | string | ISO date of document |
| `datum_zverejnenia` | string | ISO date when published on notice board |
| `faza_konania` | string | Phase of proceeding |
| `ucast_v_konani.povolena` | bool\|null | Whether public participation is allowed |
| `ucast_v_konani.lehota_na_vyjadrenie` | string\|null | Deadline for submitting comments |
| `ziadatel_navrhovatel` | string | Applicant name |
| `miesto_realizacie.kraj` | string | Region |
| `miesto_realizacie.okres` | string | District |
| `miesto_realizacie.obec` | string | Municipality |
| `miesto_realizacie.katastralne_uzemia` | array | List of cadastral zones with parcel numbers |
| `miesto_realizacie.nazov_lokality` | string | Exact locality name from document |
| `miesto_realizacie.nazov_lokality_norm` | string | Normalized locality name for Nominatim lookup |
| `typ_dokumentu` | string | Document type |
| `kategorie_vlk` | string[] | VLK-specific relevance categories |
| `typ_zasahu` | string[] | Types of intervention (e.g. "výrub drevín") |
| `typ_uzemia` | string[] | Territory type descriptions |
| `je_v_chranenom_uzemi` | bool\|null | Whether location is in a protected area |
| `dotknute_zivocichy_rastliny` | string[] | Affected species |
| `paragrafy` | array | Law paragraphs cited (each has nazov, cislo, paragraf, odsek) |
| `zhrnutie` | string | AI-generated Slovak-language summary |

## Scraped Data Structure

`data/scraped/minv_2_documents.json` — nested: list of krajov → list of okresy → list of
kategorie dokumentov → list of documents (each with `datum`, `nazov`, `url`).

`data/scraped/minzp_2_documents.json` — flat list of documents (each with `datum`, `nazov`,
`url`, `kraj`, `okres`).

## Gitignored Files

`data/protected_areas/` and `data/cadaster/` contain large GIS shapefiles that are NOT committed.
They are uploaded as CI artifacts by the process workflow and must be synced locally with:
```bash
bash analyzer/sync_github_data.sh
```
```

- [ ] **Step 2: Verify**

```bash
head -10 data/AGENTS.md
```

Expected: "# Data — Agent Guide"

---

## Task 4: Create `./website/AGENTS.md`

**Files:** Create `./website/AGENTS.md`

- [ ] **Step 1: Write `./website/AGENTS.md`**

```markdown
# Website — Agent Guide

Astro 5 static site + React 19 islands + Tailwind CSS 4, with an optional Convex backend for
user authentication and document tagging. Deployed to GitHub Pages at
`https://michalfapso.github.io/vlk_uradne_tabule/`.

## Dev Commands (run from `./website/`)

```bash
npm install       # install dependencies
npm run dev       # dev server at http://localhost:4321/vlk_uradne_tabule/
npm run build     # build static site to dist/
npm run preview   # preview built site locally
```

## Key Config Files

| File | Purpose |
|---|---|
| `astro.config.mjs` | Astro config — `base: '/vlk_uradne_tabule/'`, integrations: tailwind + react |
| `tailwind.config.mjs` | Tailwind CSS config |
| `convex/schema.ts` | Convex database schema |
| `package.json` | Node dependencies |

## Pages

| Page | Path | Description |
|---|---|---|
| Index | `src/pages/index.astro` | Document grid showing last 7 days of documents |
| Document detail | `src/pages/doc/[docId].astro` | Full analysis, extracted text, law references for one doc |

`index.astro` loads `data/scraped/minv_2_documents_old.json` and `minzp_2_documents_old.json`,
builds a `docIdToPathMap` via glob over `data/docs/*/*/*/*`, then enriches each document with
its `analysis.json`. It renders `TanStackDocumentGrid` and `Header` as React islands.

## Key Components

| Component | Type | Description |
|---|---|---|
| `TanStackDocumentGrid.tsx` | React island | Main sortable/filterable document table using TanStack React Table v8 |
| `Header.tsx` | React island | Navigation + auth section; requires `ConvexClientProvider` as ancestor |
| `ConvexClientProvider.tsx` | React island | Wraps children with Convex auth provider; must be ancestor of any component using Convex hooks |
| `AuthSection.tsx` | React island | Login/logout UI using Convex Auth |
| `OkresyStatus.astro` | Astro component | Shows per-district scraping status |
| `DocumentTable.astro` | Astro component | Legacy Tabulator-based table (being replaced by TanStack) |

**Important:** `ConvexClientProvider` must wrap `Header` and any component using Convex hooks.
Do not nest two `ConvexClientProvider` instances — causes auth state desync.

## Convex Backend

Schema at `convex/schema.ts`. Two table groups:

**`authTables`** (from `@convex-dev/auth`) — users, sessions, accounts, verification codes.

**`docTags`** — user-tagged documents:
```typescript
docTags: defineTable({
  userId: v.id("users"),
  docId: v.string(),       // document ID from scrapers
  tag: v.string(),         // "important" | "unimportant" | "noted"
  docDate: v.string(),     // ISO date string
})
  .index("by_user", ["userId"])
  .index("by_doc", ["docId"])
  .index("by_user_doc", ["userId", "docId"])
```

## Data Flow (website)

```
data/scraped/minv_2_documents_old.json   }
data/scraped/minzp_2_documents_old.json  } → index.astro (build time)
data/docs/{source}/{kraj}/{okres}/{docId}/analysis.json  }
    ↓
TanStackDocumentGrid (React, client-side filtering/sorting)
    ↓
doc/[docId].astro (dynamic route, build time — one page per document)
```

## State Management

- **Nanostores** (`nanostores`, `@nanostores/react`): lightweight auth state shared across islands
- **Convex hooks**: `useQuery`, `useMutation` for real-time DB access inside React islands

## Tech Stack Versions

- Astro 5.7.10, React 19.2.4, Tailwind CSS 4.1.10 (via `@tailwindcss/vite`)
- `@tanstack/react-table` 8.21.3
- `convex` 1.32.0, `@convex-dev/auth` 0.0.91
- `primereact` 10.9.7 (UI components), `marked` 15.0.12 (markdown rendering)
```

- [ ] **Step 2: Verify**

```bash
head -10 website/AGENTS.md
```

Expected: "# Website — Agent Guide"

---

## Task 5: Create `docs/memory/` directory and `INDEX.md`

**Files:** Create `docs/memory/INDEX.md`

- [ ] **Step 1: Create the directory and write `docs/memory/INDEX.md`**

```bash
mkdir -p docs/memory
```

Then write `docs/memory/INDEX.md`:

```markdown
# Project Memory Index

Load this file at session start. Read only the files relevant to your current task.

| File | Load when... |
|---|---|
| [architecture-overview.md](architecture-overview.md) | Starting any non-trivial task — end-to-end system map |
| [analyzer-pipeline.md](analyzer-pipeline.md) | Working on scraping, processing, or document flow |
| [llm-analysis.md](llm-analysis.md) | Modifying the LLM prompt, Gemini config, or analysis output schema |
| [gis-geocoding.md](gis-geocoding.md) | Debugging GIS, cadastral lookups, or protected area checks |
| [data-schema.md](data-schema.md) | Reading or writing `analysis.json`, `meta.json`, or scraped JSON |
| [website-stack.md](website-stack.md) | Working on frontend pages, components, or the build process |
| [convex-auth.md](convex-auth.md) | Working on Convex tables, authentication, or document tagging |
| [ci-cd.md](ci-cd.md) | Modifying GitHub Actions workflows |
| [laws-references.md](laws-references.md) | Working on law citation extraction or `registry.json` |
```

- [ ] **Step 2: Verify**

```bash
cat docs/memory/INDEX.md
```

Expected: table with 9 rows linking to memory files.

---

## Task 6: Create `docs/memory/architecture-overview.md`

**Files:** Create `docs/memory/architecture-overview.md`

- [ ] **Step 1: Write the file**

```markdown
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
```

- [ ] **Step 2: Verify**

```bash
head -5 docs/memory/architecture-overview.md
```

---

## Task 7: Create `docs/memory/analyzer-pipeline.md`

**Files:** Create `docs/memory/analyzer-pipeline.md`

- [ ] **Step 1: Write the file**

```markdown
# Analyzer Pipeline

## Scraping (`run_scraping.py`)

Runs 4 scrapers in order via `subprocess.Popen`:

1. `scrapers/minv_1_regions.py` → `data/scraped/minv_1_regions.json` (region/district list)
2. `scrapers/minv_2_documents.py` (needs minv_1_regions.json) → `data/scraped/minv_2_documents.json`
3. (minzp_1_regions.py is commented out — regions are hardcoded)
4. `scrapers/minzp_2_documents.py` → `data/scraped/minzp_2_documents.json`

If step 1 fails, step 2 is skipped. Other scrapers are independent.

## Processing (`run_processing.py`)

**Key variables near the top** (used for debugging):
- `PROCESS_SPECIFIC_DOC_IDS` — set to a list of docIds to process only those docs (searches
  both new and old scraped data). Set to `None` for normal operation.
- `FORCE_DOCUMENTS_REPROCESSING` — if `True`, reprocesses documents even if their directory
  already exists in `data/docs/`.
- `DAYS_OLD_THRESHOLD = 4` — only process documents published in the last N days.

**Processing steps:**
1. Load `minv_2_documents.json`, `minzp_2_documents.json` (new)
2. Load `minv_2_documents_old.json`, `minzp_2_documents_old.json` (previous run)
3. `aggregate_and_transform()` — flatten nested minv structure and merge with flat minzp list
   into `[{url, source, original_data}]`
4. Diff: scan `data/docs/` filesystem for existing docIds, subtract from new list
5. Date filter: keep only documents where `datum >= now - DAYS_OLD_THRESHOLD`
6. For each doc: call `document_processor.process_document(doc, docs_output_dir)`
7. Write `data/scraped/unified_new.json`, `unified_old.json`, `documents_to_process.json`
   (debug output)

## Document Processing (`shared/document_processor.py`)

Per document:
1. `get_doc_id(url)` → unique `docId` string
2. Create output dir: `data/docs/{source}/{kraj}/{okres}/{docId}/`
3. Download file; detect MIME type → file suffix
4. Convert to text:
   - `.pdf` → `pdf_to_txt.extract_text_from_pdf()` (PyMuPDF, OCR fallback)
   - `.docx/.rtf/.odt/.pptx` → libreoffice → text, or pandoc
   - `.html` → markdownify
   - images → Gemini OCR
5. Save `text.txt`
6. `law_references.get_law_excerpts_for_text(text)` → `laws.txt`
7. GIS: parse `katastralne_uzemia` from partial LLM output → `cadastral_parcels_ogc.get_geometry_of_a_parcel_set()` → `parcels.geojson`
8. `llm_analyzer.analyze_text_document(text)` → parse JSON → `analysis.json`
9. If no parcel hit: `gis_geocoding.get_geometry_of_a_geoname(nazov_lokality, ...)` → geocoding
10. `get_intersections_with_protected_areas(parcels_gdf)` → updates `analysis.json` with `je_v_chranenom_uzemi`
11. `log_status()` → `status.json`

## PDF Text Extraction (`shared/pdf_to_txt.py`)

1. Try PyMuPDF (`fitz`) native text extraction
2. If text contains many replacement characters (garbled/scanned PDF): retry with Gemini OCR
3. Returns `(text, ocr_accuracy)` where `ocr_accuracy` is `"native"` or `"gemini_ocr"`

## Error Handling

- Each document is wrapped in try/except in `run_processing.py`; failures logged to
  `data/docs/status.json` (global) and `data/docs/{docId}/status.json` (per-document)
- HTTP 500 from cadastral API: retried up to 5 times with delays [5, 10, 30, 60, 120] seconds
```

- [ ] **Step 2: Verify**

```bash
head -5 docs/memory/analyzer-pipeline.md
```

---

## Task 8: Create `docs/memory/llm-analysis.md`

**Files:** Create `docs/memory/llm-analysis.md`

- [ ] **Step 1: Write the file**

```markdown
# LLM Analysis

## Model and Client

- **Library:** `litellm` (version 1.79.0) — abstraction layer supporting multiple providers
- **Model string:** `"gemini/gemini-3-flash-preview"` (hardcoded in `analyzer/shared/llm_analyzer.py`)
- **Env var:** `GEMINI_API_KEY` (also called `GOOGLE_API_KEY` in some older scripts)
- **Response format:** `{"type": "json_object"}` — litellm instructs Gemini to return pure JSON

## Prompt

**Location:** `analyzer/shared/analyze_text_document_prompt.md` (~10 KB)

The prompt is read at call time and the document text is appended:
```python
prompt = open(PROMPT_FILEPATH).read() + "\n\nText dokumentu:\n" + text_content
```

The prompt is written in Slovak and defines the full JSON output schema with field-by-field
extraction rules. It instructs the model to extract:
- Case/file numbers, dates, applicant name
- Location with cadastral zones and parcel numbers
- Intervention type, territory type, protected area flag
- Referenced law paragraphs
- Slovak-language summary

The prompt also defines how `nazov_lokality_norm` should be normalized for Nominatim lookups
(strip "PR ", "NPR ", "CHKO ", water body prefixes, etc.).

## Token Usage and Cost Logging

After each call, `llm_analyzer.py` logs:
```
LLM_cost: {"cost": 0.000123}
LLM_tokens: {"input": 4500, "output": 800, "total": 5300, "cached": 0}
```

These appear in stdout/CI logs. No persistent cost tracking is implemented yet.

## Output Handling

`analyze_text_document()` returns a raw JSON string. `document_processor.py` parses it with
`json.loads()` and saves it to `data/docs/{docId}/analysis.json`.

The `paragrafy` field in older documents may differ from the `zakony` field in the prompt schema
— both appear in different document versions. When writing code that reads `analysis.json`,
check for both field names.

## Gemini OCR (fallback in `pdf_to_txt.py`)

When PyMuPDF produces garbled text, `pdf_to_txt.py` calls Gemini with the PDF bytes
directly (as a file upload) and asks it to extract text. This uses the same `GEMINI_API_KEY`.
```

- [ ] **Step 2: Verify**

```bash
head -5 docs/memory/llm-analysis.md
```

---

## Task 9: Create `docs/memory/gis-geocoding.md`

**Files:** Create `docs/memory/gis-geocoding.md`

- [ ] **Step 1: Write the file**

```markdown
# GIS and Geocoding

## GIS Fallback Chain

For each document, the system tries to determine if the location is within a protected area:

```
1. Parse katastralne_uzemia from LLM output
   └── if parcels found:
       cadastral_parcels_ogc.get_geometry_of_a_parcel_set()
           → queries Slovak cadastral OGC API (skgeodesy.sk via proxy)
           → returns GeoDataFrame with parcel polygons
           → get_intersections_with_protected_areas(gdf)
               → intersect with data/protected_areas/ shapefiles
               → sets je_v_chranenom_uzemi in analysis.json

2. If no parcels or OGC returns nothing:
   gis_geocoding.get_geometry_of_a_geoname(nazov_lokality, obec, okres, kraj)
       → Nominatim (OpenStreetMap) geocoding
       → tries several query combinations (locality+obec, locality+okres, etc.)
       → returns GeoDataFrame with polygon/point geometry

3. If Nominatim fails:
   gis_overpass.py queries Overpass API for named areas
```

## Cadastral OGC API (`cadastral_parcels_ogc.py`)

- URL base: `https://kataster.skgeodesy.sk/...` (accessed via proxy)
- **Proxy setup:** set `GIS_PROXY_URL` and `GIS_PROXY_AUTH` env vars. The proxy receives
  the original URL as `?url=<original>` and authenticates with `X-Proxy-Auth: $GIS_PROXY_AUTH`.
- Parcel types: `C` (C-KN, register C) and `E` (E-KN, register E) — both queried separately
- Uses `nationalCadastralZoningReference` (katastrálne územie code) to narrow queries
- Retry logic: HTTP 500 errors are retried with delays [5, 10, 30, 60, 120] seconds

## Protected Areas Data

- Location: `data/protected_areas/` (GITIGNORED — sync from CI artifacts)
- Format: GIS shapefiles (.shp)
- Covers 5th-degree protection reserves (prírodné rezervácie) and Natura 2000 (ÚEV/SKUEV)
- Sync command: `bash analyzer/sync_github_data.sh`

## Nominatim Geocoding (`gis_geocoding.py`)

- Base URL: `https://nominatim.openstreetmap.org/search?format=geojson&polygon_geojson=1&accept-language=sk&q=`
- Requires `User-Agent: VLK_Uradne_Nastenky_Analyzer/1.0` header
- `nazov_lokality_norm` from `analysis.json` is used as query (LLM pre-normalizes it)
- Returns only Polygon/MultiPolygon features (not points) for area intersections
- The function tries multiple query combinations in order (most specific first)

## GIS Libraries

- `geopandas` 1.1.1 — main GIS operations, CRS handling
- `shapely` 2.1.2 — geometry operations
- `pyproj` 3.7.1 — coordinate reference system transformations
- Data stored as `GeoDataFrame` with CRS `EPSG:4326` (WGS84)
```

- [ ] **Step 2: Verify**

```bash
head -5 docs/memory/gis-geocoding.md
```

---

## Task 10: Create `docs/memory/data-schema.md`

**Files:** Create `docs/memory/data-schema.md`

- [ ] **Step 1: Write the file**

```markdown
# Data Schema Reference

## Document Directory Path

```
data/docs/{source}/{kraj}/{okres}/{docId}/
```

- `source`: `minv` or `minzp`
- `kraj`: region name (e.g. `Košický kraj`)
- `okres`: district name (e.g. `Spišská Nová Ves`)
- `docId`: unique string derived from URL by `get_doc_id.py`

## `meta.json`

```json
{
  "url": "https://www.minzp.sk/ou-spisska-nova-ves/ou-sn-oszp-2020-005175.html",
  "source": "minzp",
  "datum": "2020-02-12",
  "nazov": "OU-SN-OSZP-2020/005175",
  "kraj": "Košický kraj",
  "okres": "Spišská Nová Ves",
  "kategoria": null
}
```

`kategoria` is populated for minv documents (from scraper), null for minzp.

## `analysis.json` (full schema)

```json
{
  "cislo_konania_spisu": "OU-SN-OSZP-2020/005175",
  "cislo_rozhodnutia": null,
  "datum_dokumentu": "2020-02-12",
  "datum_zverejnenia": "2020-02-12",
  "faza_konania": "začatie konania",
  "ucast_v_konani": {
    "povolena": true,
    "lehota_na_vyjadrenie": "do 5 pracovných dní od zverejnenia tohto oznámenia"
  },
  "ziadatel_navrhovatel": "Ing. Peter Zahuranec",
  "miesto_realizacie": {
    "kraj": "Košický kraj",
    "okres": "Spišská Nová Ves",
    "obec": "Smižany",
    "katastralne_uzemia": [
      {
        "nazov": "Smižany",
        "parcely": [
          { "typ": "E", "cisla": ["2095/1"] },
          { "typ": "C", "cisla": ["2037/2", "2037/119"] }
        ]
      }
    ],
    "lokalita_zastavane_uzemie": false,
    "nazov_lokality": "Košiarny briežok",
    "nazov_lokality_norm": "Košiarny briežok"
  },
  "typ_dokumentu": "Oznámenie o začatí konania",
  "kategorie_vlk": ["výrub drevín"],
  "typ_zasahu": ["výrub drevín"],
  "rozsah_zasahu": "7 stromov",
  "typ_uzemia": ["ochranné pásmo NP Slovenský raj", "2. stupeň ochrany"],
  "je_v_chranenom_uzemi": true,
  "dotknute_zivocichy_rastliny": [],
  "odkaz_enviroportal": null,
  "paragrafy": [
    {
      "paragraf": "82",
      "odsek": "7",
      "pismena": [],
      "nazov": "o ochrane prírody a krajiny",
      "cislo": "543/2002 Z. z."
    }
  ],
  "zhrnutie": "Oznámenie o začatí správneho konania..."
}
```

**Note:** Older documents use `"paragrafy"` key; the current prompt schema outputs `"zakony"`.
Code reading `analysis.json` should handle both. The `paragrafy` array items include `paragraf`,
`odsek`, `pismena`, `nazov`, `cislo`. The `zakony` array items include `nazov`, `cislo`,
`paragrafy` (list of paragraph strings).

## `scraped/minv_2_documents.json` Structure

```json
[
  {
    "kraj": "Banskobystrický kraj",
    "okresy": [
      {
        "nazov": "Banská Bystrica",
        "dokumenty_zivotne_prostredie": [
          {
            "kategoria": "Ochrana prírody a krajiny",
            "dokumenty": [
              {
                "datum": "2024-01-15",
                "nazov": "OU-BB-OSZP1-2024/001234",
                "url": "https://..."
              }
            ]
          }
        ]
      }
    ]
  }
]
```

## `scraped/minzp_2_documents.json` Structure

```json
[
  {
    "datum": "2024-01-15",
    "nazov": "OU-SN-OSZP-2024/001234",
    "url": "https://...",
    "kraj": "Košický kraj",
    "okres": "Spišská Nová Ves"
  }
]
```

## `status.json`

Written by `log_handler.log_status()`. Contains error/warning entries per document:
```json
[
  {
    "level": "error",
    "message": "Failed to download document: HTTP 404",
    "timestamp": "2024-01-15T10:30:00"
  }
]
```
```

- [ ] **Step 2: Verify**

```bash
head -5 docs/memory/data-schema.md
```

---

## Task 11: Create `docs/memory/website-stack.md`

**Files:** Create `docs/memory/website-stack.md`

- [ ] **Step 1: Write the file**

```markdown
# Website Stack

## Framework and Build

- **Astro 5.7.10** — static site generator (`output: 'static'`)
- Base path: `/vlk_uradne_tabule/` (GitHub Pages repo name)
- Site URL: `https://michalfapso.github.io`
- Config: `website/astro.config.mjs`

React components are rendered as **islands** (client-side hydration). Most page-level data
loading happens at build time in `.astro` files.

## Pages

**`src/pages/index.astro`** — Homepage
- Loads `data/scraped/minv_2_documents_old.json` and `minzp_2_documents_old.json` at build time
- Builds `docIdToPathMap` using `glob.sync('data/docs/*/*/*/*')` — maps docId → directory path
- Enriches each document with its `analysis.json`
- Filters to last 7 days
- Renders `TanStackDocumentGrid` (client island) and `Header` (client island)

**`src/pages/doc/[docId].astro`** — Document detail (dynamic route, built statically)
- One page per document
- Shows full analysis, extracted text, law references, GIS data
- Includes `Header` component (needs `ConvexClientProvider` wrapper)

## Component Architecture

```
Layout.astro
└── Header.tsx (client:load)                 ← needs ConvexClientProvider as ancestor
    └── ConvexClientProvider.tsx             ← wraps everything needing Convex
        └── AuthSection.tsx                  ← login/logout UI

index.astro
└── TanStackDocumentGrid.tsx (client:load)   ← main data table
└── OkresyStatus.astro                       ← per-district scraping status
```

**Rule:** Never render two `ConvexClientProvider` instances on the same page — causes auth
desync. The provider should wrap `Header` once at the top level.

## Key Components

**`TanStackDocumentGrid.tsx`** — TanStack React Table v8
- Column definitions with sorting, filtering, pagination
- Reads documents array passed as Astro prop at build time
- Client-side filtering/sorting — no server calls

**`ConvexClientProvider.tsx`** — Convex auth provider
- Must wrap any component that uses `useQuery`, `useMutation`, or auth hooks
- Reads `CONVEX_URL` from Astro env

**`AuthSection.tsx`** — Auth UI
- Uses `useAuthActions()` from `@convex-dev/auth/react`
- Shows login form or user info + logout button

## Styling

- **Tailwind CSS 4.x** via `@tailwindcss/vite` plugin
- `tailwind.config.mjs` at root of `website/`
- `@tailwindcss/typography` for prose content

## State Management

- **Nanostores** — lightweight signal-based store for cross-island auth state
  (`src/stores/`)
- **Convex hooks** — real-time data in islands (`useQuery`, `useMutation`)

## Important Paths (relative to `website/`)

| Path | Description |
|---|---|
| `src/pages/` | Astro page files |
| `src/components/` | React and Astro components |
| `src/layouts/Layout.astro` | Base layout |
| `src/stores/` | Nanostores state |
| `src/scripts/getDocId.js` | Client-side docId utility |
| `convex/` | Convex schema and server functions |
| `public/` | Static assets |
```

- [ ] **Step 2: Verify**

```bash
head -5 docs/memory/website-stack.md
```

---

## Task 12: Create `docs/memory/convex-auth.md`

**Files:** Create `docs/memory/convex-auth.md`

- [ ] **Step 1: Write the file**

```markdown
# Convex Backend and Auth

## Overview

Convex is used as an optional backend for user authentication and document tagging.
It is NOT required for the static website build — the site renders without Convex.

Convex project config: `website/convex/` directory.

## Database Schema (`convex/schema.ts`)

```typescript
import { defineSchema, defineTable } from "convex/server";
import { v } from "convex/values";
import { authTables } from "@convex-dev/auth/server";

export default defineSchema({
  ...authTables,    // users, sessions, accounts, verificationCodes tables from @convex-dev/auth

  docTags: defineTable({
    userId: v.id("users"),
    docId: v.string(),       // document ID string (from scrapers, e.g. "ou-sn-oszp-2020-005175")
    tag: v.string(),         // "important" | "unimportant" | "noted"
    docDate: v.string(),     // ISO date string of the document
  })
    .index("by_user", ["userId"])
    .index("by_doc", ["docId"])
    .index("by_user_doc", ["userId", "docId"]),
});
```

## Auth Setup

Uses `@convex-dev/auth` (version 0.0.91). Auth is configured in `convex/auth.ts`
(generated by the library). The library provides:
- Password-based auth
- Magic link / OTP options
- `authTables` — merged into the schema to store sessions, accounts, etc.

## Frontend Integration

**Provider:** `website/src/components/ConvexClientProvider.tsx`
- Wraps children in Convex's `ConvexProvider` and `ConvexAuthProvider`
- Must be ancestor of any component using Convex hooks
- **Do not nest two instances** — causes auth state desync (this bug was fixed in commit e963c77)

**Auth hooks** (in React components):
- `useAuthActions()` — from `@convex-dev/auth/react` — provides `signIn`, `signOut`
- `useConvexAuth()` — from `convex/react` — provides `isAuthenticated`, `isLoading`
- `useQuery(api.docTags.getByUser)` — fetches user's tags

**Auth state cross-island sync:**
- Auth state is shared via Nanostores (`src/stores/`)
- Avoids prop-drilling between Astro islands

## Key Convex Files

| File | Purpose |
|---|---|
| `convex/schema.ts` | Database table definitions |
| `convex/auth.ts` | Auth configuration (auto-generated) |
| `convex/docTags.ts` | Query/mutation functions for docTags table |
| `convex/_generated/` | Auto-generated API types (do not edit manually) |

## Environment Variables

- `CONVEX_URL` — Convex deployment URL (set in Astro env or `.env`)
- Convex Auth secrets are configured in the Convex dashboard, not in `.env`
```

- [ ] **Step 2: Verify**

```bash
head -5 docs/memory/convex-auth.md
```

---

## Task 13: Create `docs/memory/ci-cd.md`

**Files:** Create `docs/memory/ci-cd.md`

- [ ] **Step 1: Write the file**

```markdown
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
```

- [ ] **Step 2: Verify**

```bash
head -5 docs/memory/ci-cd.md
```

---

## Task 14: Create `docs/memory/laws-references.md`

**Files:** Create `docs/memory/laws-references.md`

- [ ] **Step 1: Write the file**

```markdown
# Law Citation Extraction

## Purpose

Extracts references to specific paragraphs of Slovak laws from document text. Used to
identify which environmental laws apply to a given proceeding, so VLK staff can quickly
assess relevance.

## Entry Point

`analyzer/shared/law_references.py` — main function: `get_law_excerpts_for_text(text)`

Returns a string saved to `data/docs/{docId}/laws.txt`.

## Law Registry (`data/laws/registry.json`)

Maps law identifiers to regex patterns for recognition:

```json
{
  "543/2002": {
    "names": [
      "(?:NR\\s+SR\\s+)?(?:č\\.\\s*)?543/2002\\s*(?:Z\\.\\s?z\\.)?",
      "o\\s+ochrane\\s+pr[ií]rody(?:\\s+a\\s+krajiny)?",
      "ZOPK",
      "ZOPaK",
      "(?:(?:zákon[ea]?\\s+)?(?:o\\s+)?)?OPaK"
    ]
  },
  "71/1967": {
    "names": [
      "(?:č\\.\\s*)?71/1967\\s*(?:(?:Z\\.\\s?z\\.)|(?:[Zz]b))?",
      "o\\s+spr[aá]vnom\\s+konan[ií]",
      "spr[aá]vny\\s+poriadok",
      "spr[aá]vneho\\s+poriadku"
    ]
  }
}
```

Each law key maps to a list of regex patterns (`names`) that match the law when found in text.
Patterns are sorted longest-first to avoid premature partial matches.

## Key Implementation Details

- **Two-pass strategy:** First pass finds all `§` references with section/paragraph numbers;
  second pass identifies which law each reference belongs to
- **Slovak grammar handling:** Regex patterns account for Slovak grammatical inflections
  (e.g. `zákon`, `zákona`, `zákonom`, `zákonov`)
- **Paragraph range support:** Handles ranges like `§ 47 až 49` and lists like `§ 47, 48`
- **Constants:**
  - `MAX_RECURSION_DEPTH = 3` — limits recursive reference following
  - `MAX_TREE_TEXT_LENGTH = 2500` — max text excerpt per reference tree
- **Debug flag:** `DEBUG = False` at top of file — set to `True` for verbose output

## Supported Laws

Currently in `registry.json`:
- `543/2002` — Zákon o ochrane prírody a krajiny (Nature and Landscape Protection Act)
- `71/1967` — Zákon o správnom konaní (Administrative Procedure Act)

Additional laws can be added by extending `registry.json` with new entries.

## LLM Also Extracts Laws

The LLM analysis prompt (`analyze_text_document_prompt.md`) also extracts law references
into `analysis.json` under the `paragrafy` or `zakony` field. The regex-based extraction
in `law_references.py` is complementary — it produces a human-readable text excerpt rather
than structured JSON.
```

- [ ] **Step 2: Verify**

```bash
head -5 docs/memory/laws-references.md
```

---

## Task 15: Create `./skills/update-memory.md`

**Files:** Create `./skills/update-memory.md`

- [ ] **Step 1: Create the skills directory and write the skill**

```bash
mkdir -p skills
```

Then write `skills/update-memory.md`:

```markdown
# Skill: Update Project Memory

Invoke this skill manually at the end of a working session to capture insights that will save
future AI agents time.

## When to Invoke

After completing meaningful work in this project — debugging, implementing a feature, exploring
an unfamiliar subsystem, discovering non-obvious behavior.

## Process

### Step 1 — Identify what's worth saving

Review what happened in this session. For each thing you discovered or changed, ask:
**"Would this save a future agent 5+ minutes of exploration?"**

Save it if yes. Skip it if:
- It's already obvious from reading the code
- It's a temporary workaround that should be reverted
- It's ephemeral session state (current task, in-progress work)
- It's already documented in the memory files

Examples of things worth saving:
- A non-obvious field name difference (`paragrafy` vs `zakony` in analysis.json)
- A gotcha (never nest two `ConvexClientProvider` — causes auth desync)
- A new env var or entry point script
- A schema change or new data file format
- A key debugging variable (`PROCESS_SPECIFIC_DOC_IDS` in run_processing.py)

### Step 2 — Update relevant memory files

Read `docs/memory/INDEX.md` to find the right file for each insight.

For each insight:
1. Open the relevant `docs/memory/*.md` file
2. Add the insight to the appropriate section
3. Do not duplicate content already present
4. Keep entries concise — one short paragraph or a table row

### Step 3 — Add new memory files if needed

If no existing file covers the topic:
1. Create `docs/memory/{topic-name}.md` with a clear heading and content
2. Add a row to `docs/memory/INDEX.md`

### Step 4 — Update subdirectory AGENTS.md if the interface changed

Update `analyzer/AGENTS.md`, `data/AGENTS.md`, or `website/AGENTS.md` if:
- A new entry point script was added
- An env var was added or renamed
- A data schema field was added or changed
- A key component was added or restructured

### Step 5 — Commit

```bash
git add docs/memory/ analyzer/AGENTS.md data/AGENTS.md website/AGENTS.md AGENTS.md skills/
git commit -m "docs: update project memory"
```

If only memory files changed (no AGENTS.md changes):
```bash
git add docs/memory/
git commit -m "docs: update project memory"
```

## What NOT to Save

- Code patterns derivable by reading the files
- Git history (use `git log` / `git blame` instead)
- Debugging solutions where the fix is already in the code
- Anything already in AGENTS.md or CLAUDE.md
- In-progress task state or temporary notes
```

- [ ] **Step 2: Verify**

```bash
head -10 skills/update-memory.md
```

---

## Task 16: Final Commit

**Files:** All files created/modified above

- [ ] **Step 1: Verify all files exist**

```bash
ls AGENTS.md analyzer/AGENTS.md data/AGENTS.md website/AGENTS.md
ls docs/memory/
ls skills/update-memory.md
```

Expected output for `docs/memory/`:
```
INDEX.md
architecture-overview.md
analyzer-pipeline.md
llm-analysis.md
gis-geocoding.md
data-schema.md
website-stack.md
convex-auth.md
ci-cd.md
laws-references.md
```

- [ ] **Step 2: Commit everything**

```bash
git add AGENTS.md analyzer/AGENTS.md data/AGENTS.md website/AGENTS.md \
  docs/memory/ skills/update-memory.md
git commit -m "$(cat <<'EOF'
docs: add AGENTS.md files, project memory, and update-memory skill

- Rewrite root AGENTS.md in English with subdirectory guide pointers
- Add analyzer/AGENTS.md, data/AGENTS.md, website/AGENTS.md
- Create docs/memory/ with INDEX.md and 9 topic files
- Add skills/update-memory.md for end-of-session memory updates

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
EOF
)"
```

- [ ] **Step 3: Verify commit**

```bash
git show --stat HEAD
```

Expected: 15 files changed, all the files listed in the File Locations Summary from the spec.
