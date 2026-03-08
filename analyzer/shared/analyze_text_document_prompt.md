Analyzuj text dokumentu z úradnej tabule okresného úradu životného prostredia, ktorý bol skonvertovaný z PDF do textu. Tvojou úlohou je extrahovať kľúčové informácie do štruktúrovaného formátu JSON. Tento JSON má pomôcť organizácii Lesoochranárske zoskupenie VLK (LZ VLK) rýchlo identifikovať pre nich relevantné konania (najmä ťažba a výrub v lesoch a voľnej krajine, poľovníctvo, usmrcovanie zvierat, chémia a stavba lesných ciest v chránených územiach).

Vráť *len* JSON s nasledujúcou štruktúrou. Neuvádzaj žiadny iný text pred ani po JSON objekte.

{
  "cislo_konania_spisu": "...",
  "cislo_rozhodnutia": "...",
  "datum_dokumentu": "...",
  "datum_zverejnenia": "...",
  "faza_konania": "...",
  "ucast_v_konani": {
    "povolena": null,
    "lehota_na_vyjadrenie": "..."
  },
  "ziadatel_navrhovatel": "...",
  "miesto_realizacie": {
    "kraj": "...",
    "okres": "...",
    "obec": "...",
    "katastralne_uzemia": [
      {
        "nazov": "...",
        "parcely": [
          {
            "typ": "...",
            "cisla": ["..."]
          }
        ]
      }
    ],
    "lokalita_zastavane_uzemie": null,
    "nazov_lokality": "...",
    "nazov_lokality_norm": "..."
  },
  "typ_dokumentu": "...",
  "kategorie_vlk": ["..."],
  "typ_zasahu": ["..."],
  "rozsah_zasahu": "...",
  "typ_uzemia": ["..."],
  "je_v_chranenom_uzemi": null,
  "dotknute_zivocichy_rastliny": ["..."],
  "odkaz_enviroportal": "...",
  "zakony": [
    {
      "nazov": "...",
      "cislo": "...",
      "paragrafy": ["..."]
    }
  ],
  "zhrnutie": "..."
}

Popis polí a pravidlá extrakcie:

*   `cislo_konania_spisu`: Oficiálne číslo konania alebo spisu (napr. začínajúce na OU-...).
*   `cislo_rozhodnutia`: Oficiálne číslo konkrétneho rozhodnutia (ak je dokumentom rozhodnutie a má špecifické číslo odlišné od čísla spisu).
*   `datum_dokumentu`: Dátum vystavenia alebo odoslania dokumentu. Formát preferuj YYYY-MM-DD, ak je možné presne určiť, inak použi textovú formu z dokumentu.
*   `datum_zverejnenia`: Dátum, kedy bol dokument vyvesený/zverejnený na úradnej tabuli/webe (často označené "Vyvesené dňa:", "Zverejnené dňa:", "Začiatok zverejnenia:"). Formát preferuj YYYY-MM-DD.
*   `ucast_v_konani`:
    *   `povolena`: Boolean hodnota určujúca, či je možné sa do konania prihlásiť. Môže mať hodnoty `true`, `false`, prípadne `null` ak to z dokumentu nie je zrejmé.
    *   `lehota_na_vyjadrenie`: Explicitne uvedená lehota, dokedy môže verejnosť alebo účastníci konania podať vyjadrenie, námietky alebo potvrdiť záujem byť účastníkom. Uveď presné znenie z dokumentu (napr. "do 10 dní od zverejnenia", "najneskôr pri ústnom pojednávaní dňa 14.02.2023"). Ak je viac lehôt pre rôzne typy vyjadrení, zameraj sa na lehotu pre verejnosť/účastníkov na prvé vyjadrenie/vstup do konania. Ak lehota nie je špecifikovaná (napr. len zmienka o ústnom pojednávaní bez explicitnej lehoty pre vyjadrenia vopred), uveď `null`.
*   `ziadatel_navrhovatel`: Meno alebo plný obchodný názov subjektu, ktorý žiadosť podal alebo navrhovanej činnosti/stavby. Ak je uvedených viac žiadateľov, uveď hlavného (napr. obec pri obecných stavbách). Ak je uvedený žiadateľ aj zastúpenie, uveď žiadateľa. Ak je uvedený len subjekt, ktorý oznamuje výrub/činnosť, uveď ten (napr. ŽSR, SVP, SPP).
*   `miesto_realizacie`:
    *   `kraj`: Názov kraja, ak je uvedený.
    *   `okres`: Názov okresu, ak je uvedený.
    *   `obec`: Názov obce/mesta, kde sa činnosť realizuje.
    *   `katastralne_uzemia`: Zoznam dotknutých katastrálnych území. Ak nie sú uvedené, ponechaj prázdny zoznam `[]`.
        *   `nazov`: Názov katastrálneho územia
        *   `parcely`: Zoznam dotknutých parciel. Ak nie sú uvedené, ponechaj prázdny zoznam `[]`.
            *   `typ`: typ parciel, povolene hodnoty su 'C', 'E' alebo None. 'C-KN' aj 'CKN' oznac ako 'C'. 'E-KN', 'EKN' oznac ako 'E'.
            *   `cisla`: parcelné čísla.
    *   `nazov_lokality`: Špecifický názov lokality presne tak, ako je uvedený v texte (napr. "PR Tarbucka", "tok rieky Mútňanka", "Krakovská ulica").
    *   `nazov_lokality_norm`: Normalizovaný názov lokality upravený špeciálne pre vyhľadávanie v OpenStreetMap (Nominatim). Aplikuj nasledujúce pravidlá:
        1. Odstráň druhové a byrokratické predpony/prípony pre chránené územia: "PR ", "NPR ", "CHKO ", "NP ", "CHA ", "ÚEV ". (napr. "PR Tarbucka" -> "Tarbucka").
        2. Odstráň slová označujúce vodné toky a plochy: "tok rieky ", "rieka ", "vodný tok ", "koryto ", "potok ", "vodná nádrž ", "VN " (napr. "tok rieky Mútňanka" -> "Mútňanka").
        3. Odstráň slová "ulica", "ul.", "námestie", "nám." a ponechaj len samotný názov. Ak ide o ulicu, VŽDY pridaj za čiarku názov obce/mesta z poľa `obec` pre kontext (napr. "Krakovská ulica" v meste Košice -> "Krakovská, Košice").
        4. Odstráň slová ako "areál", "obytná zóna", "sídlisko", "k.ú.".
        5. Vráť len čistý, základný názov (v nominatíve), ktorý má najväčšiu šancu byť nájdený v mapovej databáze. Ak lokalita nie je uvedená, vráť `null`.
    *   `lokalita_zastavane_uzemie`: Boolean. Daj `true`, ak sa činnosť realizuje v intraviláne (zastavanom území obce, pri rodinnom dome, v záhrade, na námestí). Daj `false`, ak sa realizuje v extraviláne (mimo zastavaného územia, v lese, vo voľnej krajine). Ak to z textu nie je zrejmé, daj `null`.
*   `typ_dokumentu`: Identifikuj hlavný účel dokumentu. Doslovný typ dokumentu (napr. "Oznámenie o začatí konania", "Rozhodnutie zo zisťovacieho konania", "Kolaudačné rozhodnutie", "Stavebné povolenie", "Oznámenie o výrube").
*   `faza_konania`: Urči, v akej fáze je správne konanie. Vráť presne jednu z týchto hodnôt:
    - "ZACIATOK": ide o oznámenie o začatí konania, upovedomenie o začatí, žiadosť (štádium, kedy sa verejnosť ešte môže zapojiť a rozhodnutie ešte NEBOLO vydané).
    - "ROZHODNUTIE": ide o samotné konečné rozhodnutie vo veci (súhlas, povolenie, zamietnutie, zastavenie konania), proti ktorému už je možné len podať odvolanie.
    - "INE": iné typy dokumentov (výzvy na doplnenie, prerušenie konania, informácie pre verejnosť).
*   `kategorie_vlk`: Priraď jednu alebo viacero štandardizovaných kategórií podľa toho, o aký zásah ide. Toto je kľúčové pre filtrovanie! Použi len hodnoty z tohto zoznamu:
    - "LES_VYRUB": ťažba dreva, lesnícke zásahy, výruby (vrátane jednotlivých stromov).
    - "ZIVOCICHY_USMRCOVANIE": povolenie na odstrel, lov, plašenie, odchyt živočíchov.
    - "CHEMIA": používanie chemických látok, postrekov, hnojív v prírode.
    - "VYSTAVBA_V_PRIRODE": stavba lesných ciest, vodných diel, zjazdoviek, oplotení v krajine.
    - "INZINIERSKE_SIETE": elektrické vedenia, kanalizácie, vodovody, vysielače, plynovody.
    - "POLNOHOSPODARSTVO": pasenie hospodárskych zvierat, napájanie, ustajnenie mimo stavieb.
    - "VEDA_A_VYSKUM": vedecký výskum, monitorovanie.
    - "VJAZD_VOZIDLA": vjazd motorových vozidiel.
    - "INE": iné zásahy (napr. ťažba štrku, športové podujatia).
*   `typ_zasahu`: Konkrétne termíny z dokumentu (napr.["výrub 2 ks drevín", "asanačná ťažba", "vjazd motorových vozidiel"]).
*   `typ_zasahu`: Zoznam typov navrhovanej činnosti alebo zásahov do životného prostredia. Zameraj sa na kľúčové záujmy LZ VLK. Použi konkrétne termíny z dokumentu. Ak si nie si istý, o aký typ zásahu ide, daj `null`.
*   `rozsah_zasahu`: Krátky text popisujúci kvantitu alebo objem zásahu, aby sa dala posúdiť jeho závažnosť. Napr. "1 strom (vŕba)", "náletové dreviny na 50m2", "ťažba 1500 m3 dreva", "plocha 2,5 ha", "odstrel 5 ks medveďa". Ak rozsah nie je uvedený, daj `null`.
*   `typ_uzemia`: Zoznam explicitne spomenutých typov alebo názvov chránených území (napr. "Národný park", "CHKO", "Prírodná rezervácia", "Chránený areál", "Územie európskeho významu", "NATURA 2000", "SKUEV", "SKCHVU", "CHVO", "ochranné pásmo vodárenského zdroja", "ochranné pásmo VN vedenia", "ochranné pásmo plynovodu"). Ak je v dokumente číslo stupňa ochrany (napr. "4. stupeň", "5. stupeň") alebo sa v dokumente žiada o výnimku pre zákazy definované v zákon 543/2002 o ochrane prírody § 13 "2. stupeň", § 14 "3. stupeň", § 15 "4. stupeň", § 16 "5. stupeň", pridaj ten ochranný stupeň tiež do "typ_uzemia". Ak je v dokumente napísané, že sa netýka chráneného územia, daj tam "nechránené". Ak sa v dokumente nespomína, či ide o chránené územie, daj tam "neviem". Ak sa netýka žiadneho územia, ponechaj prázdny zoznam `[]`.
*   `je_v_chranenom_uzemi`: Booleovská hodnota: `true`, ak je `typ_uzemia` akékoľvek chránené územie (vrátane ochranných pásiem alebo CHVO) alebo stupeň ochrany > 0; `false`, ak nie je spomenuté nič o chránených územiach ani stupňoch ochrany. Ak informácia chýba, uveď `null`.
*   `dotknute_zivocichy_rastliny`: Zoznam explicitne spomenutých chránených, ohrozených alebo inak významných živočíchov alebo rastlín, prípadne skupiny (napr. "bobor vodný", "vydra riečna", "ichtyofauna", "bentická fauna", "brehové porasty"). Ak nie sú uvedené, ponechaj prázdny zoznam `[]`.
*   `odkaz_enviroportal`: URL adresa na enviroportal.sk, ak je v dokumente uvedená.
*   `zakony`: Zoznam zákonov, ktoré sa vzťahujú na daný dokument. Ak nie sú uvedené, ponechaj prázdny zoznam `[]`. Pre každý zákon spomenutý v dokumente môžeš vyplniť polia: "nazov" (názov zákona), "cislo" (číslo zákona) a "paragrafy" (pole paragrafov daného zákona spomenuté v texte, ale nepridávaj sem paragrafy, ktoré sú v zneniach zákonov pod dokumentom a nie sú súčasťou samotného dokumentu).
*   `zhrnutie`: Stručné zhrnutie (max 3 vety) s dôrazom na to, o aký zásah a v akom rozsahu ide, kde presne sa nachádza a či zasahuje chránené územie.

**Pokyny pre model:**

*   Extrahuj informácie iba z poskytnutého textu dokumentu. Nepridávaj externé znalosti o lokalitách (či sú v chránených územiach, ak to dokument explicitne neuvádza), okrem extrakcie explicitných názvov chránených území alebo stupňov ochrany, ak sú v texte.
*   Dôsledne vyplň JSON presne podľa definovanej štruktúry.
*   Informácie si nevymýšľaj. Pre polia s textovou hodnotou, ak informácia chýba, použij `null`. Pre polia so zoznamom hodnôt, ak žiadne položky nie sú nájdené, použi prázdny zoznam `[]`.
*   Zaisti, aby výstup bol validný JSON a neobsahoval nič iné.

