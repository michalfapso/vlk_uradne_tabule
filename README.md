# Monitorovanie tabúľ okresných úradov životného prostredia

Tento projekt automaticky sleduje, analyzuje dokumenty z tabúľ okresných úradov životného prostredia, ktoré sú zverejnňované na:
- https://www.minzp.sk/uradna-tabula/priroda/
- https://www.minv.sk/?okresne-urady-klientske-centra

Výsledky analýz sú zverejnené na webstránke:
**[https://michalfapso.github.io/vlk_uradne_tabule/](https://michalfapso.github.io/vlk_uradne_tabule/)**

---

## Ako to funguje

Celý proces je plne automatizovaný pomocou [GitHub Actions](.github/workflows/daily-scrape-analyze-deploy.yml) a beží každý deň.

1.  **Zber dát:** Skripty v Pythone stiahnu aktuálne zoznamy dokumentov z webov ministerstiev (minv.sk, minzp.sk).
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
*   **AI analýza:** Google Gemini (cez lightllm - podporuje rôzne LLM modely)
*   **Frontend:** Astro + Tailwind CSS + Tabulator
*   **Automatizácia & CI/CD:** GitHub Actions
*   **Hosting:** GitHub Pages - zatiaľ je celý web kompletne statický

## TODO

### 1. AI Analýza a Filtrovanie (Efektivita)
*   **Smart Pre-filtrovanie:** Zavedenie rýchleho a lacného "pre-filtra" (napr. pomocou menšieho LLM modelu alebo na základe pevných pravidiel), ktorý vyradí zjavne nedôležité dokumenty ešte pred spustením nákladnejšej a pomalšej hlavnej analýzy.
    *   Príklady nedôležitých dokumentov: "držba a preprava neživého jedinca chráneného živočícha", "organizovanie športového podujatia, bežecké preteky", "organizácia podujatia" (docid:9995-2026-6-1, ou-bb-oszp1-2026-017470, ou-bb-oszp1-2026-017324-si).
*   **Označovanie podozrivých dokumentov a iteratívny feedback:**
    *   Niekedy je prázdne `miesto_realizacie.katastralne_uzemia` alebo `nazov_lokality == null` (docid:562616). Lenže inokedy je v dokumente text typu "na území Chránenej krajinnej oblasti Východné Karpaty na ktorom platí 2. st. ochrany" (docid:562674) a hoci je `nazov_lokality == null`, tieto údaje sa správne dostanú do `"typ_uzemia"`.
    *   Iteratívna AI analýza s feedbackom na vylepšenie promptu:
        1. Vložiť viacero dokumentov do AI, aby vymyslela vhodný prompt pre extrakciu JSON dát dôležitých pre ochranu prírody. Pridať aj info o dostupnej GIS analýze. (Podobné `analyzer/meta_analysis.py`).
        2. Otestovať prompt na dokumentoch, vložiť výsledky opäť do AI na zhodnotenie použiteľnosti a navrhnutie spôsobu určovania dôležitosti (rizikovosti). Zistiť, či stačia regexy. Dokumenty doplniť aj manuálnu analýzu - kategorizovať a možno aj napísať zdôvodnenie (napr. "nedôležitý, lebo sa jedná len o športové podujatie")
        3. Aplikovať navrhnutý filter na rozdelenie dokumentov na dôležité/nedôležité, zaslať do AI na validáciu.
        4. Vybrať viaceré *iba dôležité* dokumenty a zopakovať proces na dosiahnutie lepšej presnosti.

### 2. Užívateľská zóna a Interaktivita (Frontend & Backend)
*   **Manažment stavu dokumentov:** Po prihlásení bude mať užívateľ (napr. LZ VLK) možnosť manuálne označovať dokumenty stavmi: *nedôležitý / podozrivý / dôležitý / vstupujeme do správneho konania*.
*   **Backend a Hosting:** Prejsť z čisto statických GitHub Pages na platformu s rozumným "free tier" limitom, ktorá podporuje backend a databázu pre ukladanie stavov a poznámok k dokumentom.
    *   Kandidáti: [Convex](https://www.convex.dev), Supabase, Vercel atď.
*   **Frontend UX a Mapy:**
    *   Tabulator v aktuálnej podobe nie je úplne user-friendly (napr. preskakovanie scrollovania pri expandovaní riadku). Treba ho opraviť, lepšie optimalizovať (aj pre mobily) alebo nahradiť.
    *   Pridať interaktívnu mapu pre rýchly prehľad analyzovaných dokumentov a zasiahnutých území za dané obdobie. Použiť https://github.com/michalfapso/vlk_zonacia_tanap/ alebo spraviť vlastnú s MapLibre/Leaflet.

### 3. Generovanie listov (Automatizácia pre LZ VLK)
*   **Automatické generovanie listov:** Doimplementovať funkcionalitu na vygenerovanie formálneho listu (PDF/DOCX), ktorým LZ VLK môže vstúpiť do správneho konania. List by bol predvyplnený o metadáta z dokumentu (číslo konania, žiadateľ, dotknuté parcely) a informácie o chránenom území získané AI a GIS analýzou.

### 4. GIS a Priestorové dáta
*   Zistiť, či sú parcely priamo v zastavanom území obce alebo mimo nej.
*   **Spoľahlivosť OGC API a Katastra:**
    *   Zanalyzovať logy, aby sme mali lepšiu predstavu, k akým chybám dochádza pri GIS analýze.
    *   V prípade, že sa daná parcela nenájde, zobrať a vizualizovať *celé katastrálne územie*. Pre šetrenie miesta je možné jeho geometriu zjednodušiť. Na frontende potom užívateľa upozorniť, že zobrazené je celé KÚ, nielen relevantné parcely.
*   **Vylepšenie geokódovania (Nominatim):**
    *   Spracovanie nesprávne zadaných geografických názvov. Dokumenty často uvádzajú len "PR Tarbucka", čo sa v Nominatime nemusí nájsť. Pridať fuzzy matching alebo automatickú expanziu skratiek (PR -> Prírodná rezervácia, NPR atď.). Na to by tiež bola vhodná analýza logov
    *   Získanie aktuálnych miest realizacie na analýzu:
      ```bash
      (export IFS=$'\n'; find data/docs -name 'analysis.json' -newermt $(date +%Y-%m-%d -d '60 days ago') -print0 | xargs -0 jq -c '.miesto_realizacie | del(.katastralne_uzemia)' | grep -v '"nazov_lokality":null' | less)
      ```

### 5. Analýza referencovaných zákonov
*   `analyzer/shared/law_references.py`
*   Vytiahnuť skript do samostatného repozitára, aby sa dal ľahšie použiť aj v iných externých projektoch.
*   Zanalyzovať warningy v prípade nenájdených zákonov. Vygenerovať sumár úspešných a chýbajúcich referencií pre lepšie doladenie registrov:
      ```bash
      cd analyzer
      (IFS=$'\n'; for i in `find ../../uradne_nastenky_data/docs -name text.txt`; do echo $i; python3 shared/law_references.py "$i" > "${i%text.txt}laws.txt" 2>"${i%text.txt}laws_missing.txt"; done)
      ```
*   V `analysis.json` pre každý dokument máme aj názvy referencovaných zákonov.
*   Automatizácia sťahovania ďalších zákonov zo slov-lex.sk a vygenerovanie regexov pre ich rôzne formy názvov použitých v textoch a pridanie do `data/laws/registry.json`

### 6. Nový portál, kde úrady umiestňujú dokumenty
*   V logoch na github action bol link na nejaký nový portál na zverejňovanie dokumentov, ale nepamätám si jeho url.