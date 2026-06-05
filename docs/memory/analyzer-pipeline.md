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
