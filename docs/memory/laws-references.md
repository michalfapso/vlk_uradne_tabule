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
