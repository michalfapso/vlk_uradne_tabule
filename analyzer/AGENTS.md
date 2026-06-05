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
