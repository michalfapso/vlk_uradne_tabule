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

## Použité technológie

*   **Backend & Scraper:** Python
*   **AI analýza:** Google Gemini (cez lightllm, takže sa dá jednoducho vymeniť za iný LLM)
*   **Frontend:** Astro + Tailwind CSS + Tabulator
*   **Automatizácia & CI/CD:** GitHub Actions
*   **Hosting:** GitHub Pages