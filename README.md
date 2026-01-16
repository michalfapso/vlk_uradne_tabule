# Monitorovanie tabúľ okresných úradov životného prostredia

Tento projekt automaticky sleduje, analyzuje dokumenty z tabúľ okresných úradov životného prostredia, ktoré sú zverejnňované na:
- https://www.minzp.sk/uradna-tabula/priroda/
- https://www.minv.sk/?okresne-urady-klientske-centra

Výsledky analýz sú zverejnené na webstránke:
**[https://michalfapso.github.io/vlk_uradne_tabule/](https://michalfapso.github.io/vlk_uradne_tabule/)**

---

## Ako to funguje

Celý proces je plne automatizovaný pomocou [GitHub Actions](.github/workflows/daily-scrape-analyze-deploy.yml) a beží každý deň.

1.  **Zber dát:** Skripty v Pythone stiahnu aktuálne zoznamy dokumentov z webov ministerstiev.
2.  **Analýza zmien:** Porovnajú sa nové dáta s predchádzajúcimi a identifikujú sa nové dokumenty.
3.  **Spracovanie dokumentov:** Nové dokumenty sú spracované pomocou AI (Google Gemini) pre extrakciu kľúčových informácií a zhrnutí. Hlavný prompt je v [analyzer/analyze_text_document_prompt.md](analyzer/analyze_text_document_prompt.md).
4.  **Aktualizácia dát:** Spracované dáta sa uložia priamo do tohto repozitára do adresára `data`.
5.  **Nasadenie webu:** Webstránka postavená na Astro sa automaticky znova vygeneruje s novými dátami a nasadí na GitHub Pages.

## Lokálny vývoj

Ak chcete spúšťať analýzu lokálne, postupujte podľa týchto krokov:

1.  **Stiahnutie dát z GitHubu:** Keďže GIS súbory a niektoré medzivýsledky nie sú súčasťou repozitára (sú v `.gitignore`), môžete si ich stiahnuť z posledných úspešných behov GitHub Actions:
    ```bash
    ./analyzer/sync_github_data.sh
    ```
    *(Vyžaduje nainštalované a prihlásené [GitHub CLI](https://cli.github.com/))*

2.  **Spustenie analýzy:**
    ```bash
    ./analyzer/local_process.sh
    ```
    Tento skript spustí `run_processing.py` a následne `prune_gis_files.py`, čím nasimuluje spracovanie dát tak, ako prebieha v CI.

## Použité technológie

*   **Backend & Scraper:** Python
*   **AI analýza:** Google Gemini (cez lightllm, takže sa dá jednoducho vymeniť za iný LLM)
*   **Frontend:** Astro + Tailwind CSS + Tabulator
*   **Automatizácia & CI/CD:** GitHub Actions
*   **Hosting:** GitHub Pages