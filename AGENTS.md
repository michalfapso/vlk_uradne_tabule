Tento projekt slúži na analýzu dokumentov zverejnených na nástenkách okresných úradov životného prostredia. Cieľom analýzy je sprehľadniť a zjednodušiť rozhodovanie zamestnancom Lesoochranárskeho zoskupenia VLK, ktorí chcú vstupovať do správnych konaní, ktoré sa týkajú chránených území (rezervácii s 5. stupňom ochrany a územia Natura 2000).

Adresárová štruktúra projektu je nasledovná:
./.github ...Github Actions pre každodenné sťahovanie a analyzovanie nových dokumentov
./analyzer ...skripty na scraping, prevod PDF dokumentov do textu, analýzu pomocou LLM
./analyzer/minv ...skripty špecializované pre stránku www.minv.sk
./analyzer/minzp ...skripty špecializované pre stránku www.minzp.sk
./data/minv ...dáta k dokumentom a ich analýzam pre www.minv.sk
./data/minzp ...dáta k dokumentom a ich analýzam pre www.minzp.sk
./data/laws ...znenia zákonov
./tests ...testy
./website ...AstroJS projekt, ktorý spracováva výsledky analýzy a generuje z nich webovú tabuľku
