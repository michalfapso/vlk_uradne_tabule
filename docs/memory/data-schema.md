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
