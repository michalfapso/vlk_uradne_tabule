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
