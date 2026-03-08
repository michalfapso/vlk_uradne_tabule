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
* [x] "Rozhodnutia" môžeme úplne ignorovať a také dokumenty ani nespracovávať.
* [x] Dôležité frázy sú "povolenie výnimky", "udelenie súhlasu".
* [x] Z dokumentov vytiahnuť a potom aj v tabuľke používateľom vypísať čísla všetkých zákonov a paragrafov priamo spomínaných v dokumente.
* [x] Ak dokument odkazuje na zákon 543/2002 [§ 13](https://www.zakonypreludi.sk/zz/2002-543/znenie-20260101#p13) ... [§ 16](https://www.zakonypreludi.sk/zz/2002-543/znenie-20260101#p16), kde sú definované zákazy podľa stupňov ochrany, môžeme počítať s tým, že sa žiada zásah do stupňa ochrany podľa odkazovaného paragrafu.
* [ ] Premyslieť aj archiváciu pôvodných dokumentov (kvôli prípadným súdom ideálne originálny dokument, ktorý bol zverejnený, nielen prevedený na text). Využije sa tak raz za 5-10 rokov, keď treba nejaký dokument dohľadať v historii.
* [ ] Na konci roka analýza dokumentov, koľko bolo žiadaných rôznych typov výnimiek počas roka v rôznych typoch územií. Možno pre tieto analýzy by bolo dobré sledovať aj "rozhodnutia", aby sme ich vedeli spárovať so žiadosťami o výnimky.
* [ ] **Smart Pre-filtrovanie:** Zavedenie rýchleho a lacného "pre-filtra" (napr. pomocou menšieho LLM modelu alebo na základe pevných pravidiel), ktorý vyradí zjavne nedôležité dokumenty ešte pred spustením nákladnejšej a pomalšej hlavnej analýzy.
    *   Príklady nedôležitých dokumentov: "držba a preprava neživého jedinca chráneného živočícha", "organizovanie športového podujatia, bežecké preteky", "organizácia podujatia" (docid:9995-2026-6-1, ou-bb-oszp1-2026-017470, ou-bb-oszp1-2026-017324-si).
* [ ] **Označovanie podozrivých dokumentov a iteratívny feedback:**
    * [ ] Skontrolovať: niekedy je prázdne `miesto_realizacie.katastralne_uzemia` alebo `nazov_lokality == null` (docid:562616). Lenže inokedy je v dokumente text typu "na území Chránenej krajinnej oblasti Východné Karpaty na ktorom platí 2. st. ochrany" (docid:562674) a hoci je `nazov_lokality == null`, tieto údaje sa správne dostanú do `"typ_uzemia"`.
    * [x] Iteratívna AI analýza s feedbackom na vylepšenie promptu:
        1. Vložiť viacero dokumentov do AI, aby vymyslela vhodný prompt pre extrakciu JSON dát dôležitých pre ochranu prírody. Pridať aj info o dostupnej GIS analýze. (Podobné `analyzer/meta_analysis.py`).
        2. Otestovať prompt na dokumentoch, vložiť výsledky opäť do AI na zhodnotenie použiteľnosti a navrhnutie spôsobu určovania dôležitosti (rizikovosti). Zistiť, či stačia regexy. Dokumenty doplniť aj manuálnu analýzu - kategorizovať a možno aj napísať zdôvodnenie (napr. "nedôležitý, lebo sa jedná len o športové podujatie")
        3. Aplikovať navrhnutý filter na rozdelenie dokumentov na dôležité/nedôležité, zaslať do AI na validáciu.
        4. Vybrať viaceré *iba dôležité* dokumenty a zopakovať proces na dosiahnutie lepšej presnosti.

            ```
            # Získanie zoznamu dôležitých dokumentov
            (IFS=$'\n'; for i in `find data/docs -name 'analysis.json'`; do if [ "`node website/src/scripts/documentAnalysis_cli.js "$i"`" == IMPORTANT ]; then echo "$i"; fi; done) | tee important_docs.list
            
            # Pridanie datumu
            (IFS=$'\n'; for i in `cat important_docs.list`; do d="`jq -c -r '.datum_dokumentu' "$i"`"; if [[ "$d" > '2025-09-01' && "$d" != 'null' ]]; then echo "$d $i"; fi; done) | tee important_docs_new.list

            # Zoradenie
            cat important_docs_new.list | sort -r > important_docs_new.list.sort

            # Zoznam docid - treba pridat do run_processing.py do PROCESS_SPECIFIC_DOC_IDS
            (IFS=$'\n'; for i in `cat important_docs_new.list.sort | cut -d' ' -f2- | head -30`; do basename "`dirname "$i"`"; done) 2>&1 | tee out.log

            # Spracovanie dokumentov cez LLM
            python3 -u analyzer/run_processing.py 2>&1 | tee out.log

            # Celkova cena LLM
            cat out.log | grep 'LLM_cost:' | sed 's/^.*{/{/' | jq -c '.cost' | awk '{a+=$0}END{print a}'

            # Zoznam analysis.json suborov, ktore boli spracovane
            cat out.log | grep -E 'Saving analysis to.*json' | sed 's/\.\.\.$//' | sed 's/^[^\/]*//' | tee important_docs_new.list.sort.processed

            # Znovu získať zoznam dôležitých dokumentov
            (IFS=$'\n'; for i in `cat important_docs_new.list.sort.processed`; do if [ "`node website/src/scripts/documentAnalysis_cli.js "$i"`" == IMPORTANT ]; then echo "$i"; fi; done) | tee important_docs_new.list.sort.processed.important
            
            # A zoznam nedôležitých dokumentov
            diff important_docs_new.list.sort.processed important_docs_new.list.sort.processed.important | grep -E '^<' | sed 's/^< //' | tee important_docs_new.list.sort.processed.unimportant
            
            # Kolko je dolezitych a nedolezitych dokumentov
            wc -l important_docs_new.list.sort.processed.unimportant important_docs_new.list.sort.processed.important
            
            # V "zasiahnute_chranene_uzemia" ponechat len kluce, vsetky analysis.json spojit do jedneho json pola a skopirovat do clipboardu a pastnut do AI
            (IFS=$'\n'; for i in `cat important_docs_new.list.sort.processed.important`; do cat "$i" | jq '.gis.zasiahnute_chranene_uzemia |= map_values("...")' 2>/dev/null; done) | jq -s . | xclip -selection c
            
            # Zaloha povodnych analysis.json suborov
            (IFS=$'\n'; for i in `cat important_docs_new.list.sort.processed.important`; do mv "$i" "$i.old"; done)
            

            ```
            Prvá feedback iterácia znížila počet dôležitých dokumentov z 26 na 14. Druhá už len opravila jednu chybu v regexe.

### 2. Užívateľská zóna a Interaktivita (Frontend & Backend)
* [ ] **Manažment stavu dokumentov:** Po prihlásení bude mať užívateľ (napr. LZ VLK) možnosť manuálne označovať dokumenty stavmi: *nedôležitý / podozrivý / dôležitý / vstupujeme do správneho konania*.
    *   **Backend a Hosting:** Prejsť z čisto statických GitHub Pages na platformu s rozumným "free tier" limitom, ktorá podporuje backend a databázu pre ukladanie stavov a poznámok k dokumentom. Kandidáti: [Convex](https://www.convex.dev), Supabase, Vercel atď.
* [ ] **Frontend UX a Mapy:**
    * [ ] Tabulator v aktuálnej podobe nie je úplne user-friendly (napr. preskakovanie scrollovania pri expandovaní riadku). Treba ho opraviť, lepšie optimalizovať (aj pre mobily) alebo nahradiť.
    * [ ] Pridať interaktívnu mapu pre rýchly prehľad analyzovaných dokumentov a zasiahnutých území za dané obdobie. Použiť https://github.com/michalfapso/vlk_zonacia_tanap/ alebo spraviť vlastnú s MapLibre/Leaflet.

### 3. Generovanie listov (Automatizácia pre LZ VLK)
* [ ] **Automatické generovanie listov:** Doimplementovať funkcionalitu na vygenerovanie formálneho listu (PDF/DOCX), ktorým LZ VLK môže vstúpiť do správneho konania. List by bol predvyplnený o metadáta z dokumentu (číslo konania, žiadateľ, dotknuté parcely) a informácie o chránenom území získané AI a GIS analýzou.

### 4. GIS a Priestorové dáta
* [x] Pridať do analýzy info o type GIS zdroja: PARCELA / KATASTRALNE_UZEMIE / OBEC / GEONAME.
* [ ] Zistiť, či sú parcely priamo v zastavanom území obce alebo mimo nej.
* [ ] **Spoľahlivosť OGC API a Katastra:**
    * [ ] Zanalyzovať logy, aby sme mali lepšiu predstavu, k akým chybám dochádza pri GIS analýze.
    * [x] V prípade, že sa daná parcela nenájde, zobrať a vizualizovať *celé katastrálne územie*.
    * [ ] Keď je použité celé katastrálne územie, pre šetrenie miesta je možné jeho geometriu zjednodušiť.
* [x] **Vylepšenie geokódovania (Nominatim):**
    *   Spracovanie nesprávne zadaných geografických názvov. Dokumenty často uvádzajú len "PR Tarbucka", čo sa v Nominatime nemusí nájsť. Pridať fuzzy matching alebo automatickú expanziu skratiek (PR -> Prírodná rezervácia, NPR atď.). Na to by tiež bola vhodná analýza logov
    *   Príklady:
        *   "Krakovská ulica, Košice" nefunguje, ale "Krakovská, Košice" funguje a vráti `"type": "road"`
        *   "PR Tarbucka" nefunguje, ale "Tarbucka" funguje a vráti `"type": "protected_area"`
        *   "tok rieky Mútňanka" nefunguje, ale "Mútňanka" aj "Mútňanka river" funguje
    *   Získanie aktuálnych miest realizacie na analýzu:
      ```bash
      (export IFS=$'\n'; find data/docs -name 'analysis.json' -newermt $(date +%Y-%m-%d -d '60 days ago') -print0 | xargs -0 jq -c '.miesto_realizacie | del(.katastralne_uzemia)' | grep -v '"nazov_lokality":null' | less)
      ```
* [ ] "zasiahnute_chranene_uzemia" niekedy obsahujú duplikáty, treba prečistiť analysis.json a aj to opraviť v kóde.
* [ ] "zasiahnute_chranene_uzemia" teraz obsahujú len "parcel_label", čo je iba číslo parcely. Malo by tam byť aj katastrálne územie a C/E. Ale zároveň to nemusí byť parcela, ale celé katastrálne územie alebo geoname.

### 5. Analýza referencovaných zákonov
* [ ] Vytiahnuť skript `analyzer/shared/law_references.py` do samostatného repozitára, aby sa dal ľahšie použiť aj v iných externých projektoch.
* [ ] Zanalyzovať warningy v prípade nenájdených zákonov. Vygenerovať sumár úspešných a chýbajúcich referencií pre lepšie doladenie registrov:
      ```bash
      cd analyzer
      (IFS=$'\n'; for i in `find ../../uradne_nastenky_data/docs -name text.txt`; do echo $i; python3 shared/law_references.py "$i" > "${i%text.txt}laws.txt" 2>"${i%text.txt}laws_missing.txt"; done)
      ```
* [ ] Automatizácia sťahovania ďalších zákonov zo slov-lex.sk a vygenerovanie regexov pre ich rôzne formy názvov použitých v textoch a pridanie do `data/laws/registry.json`. V `analysis.json` pre každý dokument máme aj názvy referencovaných zákonov.

### 6. Pridať nové zdroje dokumentov
* [ ] Niektoré úrady začali používať aj nový portál na zverejňovanie dokumentov: https://cuet.slovensko.sk/
* [ ] Pridať aj spracovanie EIA/SEA dokumentov z https://www.enviroportal.sk/eia-sea/informacny-system
* [ ] Monitorovať aj stránky lesných úradov ohľadom PSoL (lesný úrad Košice, Prešov, Žilina, Trenčín)

### 7. PDF -> TXT konverzia
* [x]  Ak sa konvertuje cez LLM, možno stačí obmedziť spracovávaný dokument na prvé 4 strany. Väčšinou sú najdôležitejšie veci práve tam.
