import litellm

def analyze_text_document(text_content: str):
    """
    Analyzuje textový obsah pomocou LLM (cez litellm) a uloží výsledok ako JSON.
    """
    print(f"Spúšťam analýzu textu cez LLM")
    prompt = """
Analyzuj text dokumentu z úradnej tabule okresného úradu životného prostredia, ktorý bol skonvertovaný z PDF do textu. Tvojou úlohou je extrahovať kľúčové informácie do štruktúrovaného formátu JSON. Tento JSON má pomôcť rýchlo identifikovať dokumenty relevantné pre organizáciu Lesoochranárske zoskupenie VLK (LZ VLK).

Vráť *len* JSON s nasledujúcou štruktúrou. Neuvádzaj žiadny iný text pred ani po JSON objekte.

```json
{
  "cislo_konania_spisu": "...",
  "cislo_rozhodnutia": "...",
  "datum_dokumentu": "...",
  "datum_zverejnenia": "...",
  "lehoty_na_vyjadrenie": "...",
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
    "nazov_lokality": "..."
  },
  "typ_dokumentu": "...",
  "typ_zasahu": ["..."],
  "typ_uzemia": ["..."],
  "je_v_chranenom_uzemi": null,
  "dotknute_zivocichy_rastliny": ["..."],
  "odkaz_enviroportal": "...",
  "paragrafy": [
    {
      "paragraf": "...",
      "odsek": "...",
      "pismena": ["..."],
      "zakon_nazov": "..."
      "zakon_cislo": "..."
    }
  ],
  "zhrnutie": "..."
}
```

**Popis polí:**

*   `cislo_konania_spisu`: Oficiálne číslo konania alebo spisu (napr. začínajúce na OU-...).
*   `cislo_rozhodnutia`: Oficiálne číslo konkrétneho rozhodnutia (ak je dokumentom rozhodnutie a má špecifické číslo odlišné od čísla spisu).
*   `datum_dokumentu`: Dátum vystavenia alebo odoslania dokumentu. Formát preferuj YYYY-MM-DD, ak je možné presne určiť, inak použi textovú formu z dokumentu.
*   `datum_zverejnenia`: Dátum, kedy bol dokument vyvesený/zverejnený na úradnej tabuli/webe (často označené "Vyvesené dňa:", "Zverejnené dňa:", "Začiatok zverejnenia:"). Formát preferuj YYYY-MM-DD.
*   `lehoty_na_vyjadrenie`: Explicitne uvedená lehota, dokedy môže verejnosť alebo účastníci konania podať vyjadrenie, námietky alebo potvrdiť záujem byť účastníkom. Uveď presné znenie z dokumentu (napr. "do 10 dní od zverejnenia", "najneskôr pri ústnom pojednávaní dňa 14.02.2023"). Ak je viac lehot pre rôzne typy vyjadrení, zameraj sa na lehotu pre verejnosť/účastníkov na prvé vyjadrenie/vstup do konania. Ak lehota nie je špecifikovaná (napr. len zmienka o ústnom pojednávaní bez explicitnej lehoty pre vyjadrenia vopred), uveď "Neuvedené". Ak dokument výslovne uvádza, že účasť nie je možná, uveď túto informáciu (napr. "Nie je možné sa prihlásiť do konania").
*   `ziadatel_navrhovatel`: Meno alebo plný obchodný názov subjektu, ktorý žiadosť podal alebo navrhovanej činnosti/stavby. Ak je uvedených viac žiadateľov, uveď hlavného (napr. obec pri obecných stavbách). Ak je uvedený žiadateľ aj zastúpenie, uveď žiadateľa. Ak je uvedený len subjekt, ktorý oznamuje výrub/činnosť, uveď ten (napr. ŽSR, SVP, SPP).
*   `miesto_realizacie`:
    *   `kraj`: Názov kraja, ak je uvedený.
    *   `okres`: Názov okresu, ak je uvedený.
    *   `obec`: Názov obce/mesta, kde sa činnosť realizuje.
    *   `katastralne_uzemia`: Zoznam dotknutých katastrálnych území. Ak nie sú uvedené, ponechaj prázdny zoznam `[]`.
        *   `nazov`: Názov katastrálneho územia
        *   `parcely`: Zoznam dotknutých parciel. Ak nie sú uvedené, ponechaj prázdny zoznam `[]`.
            *   `typ`: typ parciel (C-KN, E-KN).
            *   `cisla`: parcelné čísla.
    *   `nazov_lokality`: Špecifický názov lokality (napr. "Obytná zóna Hviezdoslavova", "BIO resort Šachtičky", "Martinský les"), ak je uvedený.
*   `typ_dokumentu`: Klasifikácia dokumentu (napr. "Oznámenie o začatí konania", "Rozhodnutie zo zisťovacieho konania", "Kolaudačné rozhodnutie", "Stavebné povolenie", "Oznámenie o výrube", "Informácia pre verejnosť", "Žiadosť", "Strategický dokument", "Verejná vyhláška", "Upovedomenie o predĺžení lehoty", "Výzva"). Identifikuj hlavný účel dokumentu.
*   `typ_zasahu`: Zoznam typov navrhovanej činnosti alebo zásahov do životného prostredia. Zameraj sa na kľúčové záujmy LZ VLK. Použi konkrétne termíny z dokumentu, ak sú relevantné (napr. "výrub drevín", "vysekávanie krovia", "ťažba dreva", "odstrel alebo iné usmrcovanie živočíchov", "používanie chemických látok", "výstavba budovy", "výstavba cesty", "výstavba oplotenia", "výstavba energetického diela", "výstavba vodnej stavby", "výstavba kanalizácie", "výstavba vodovodu", "výstavba čistiarne odpadových vôd", "úprava vodného toku", "odber podzemných vôd", "vypúšťanie odpadových vôd", "vsakovanie vôd"). Ak si nie si istý, o aký typ zásahu ide, daj do toho poľa iba "neviem".
*   `typ_uzemia`: Zoznam explicitne spomenutých typov alebo názvov chránených území (napr. "Národný park", "CHKO", "Prírodná rezervácia", "Chránený areál", "Územie európskeho významu", "NATURA 2000", "SKUEV", "SKCHVU", "CHVO", "ochranné pásmo vodárenského zdroja"). Ak je v dokumente číslo stupňa ochrany (napr. "4. stupeň", "5. stupeň"), pridaj to tiež do "typ_uzemia". Ak je v dokumente napísané, že sa netýka chráneného územia, daj tam "nechránené". Ak sa v dokumente nespomína, či ide o chránené územie, daj tam "neviem". Ak sa netýka žiadneho územia, ponechaj prázdny zoznam `[]`.
*   `je_v_chranenom_uzemi`: Booleovská hodnota: `true`, ak je v dokumente explicitne spomenuté akékoľvek chránené územie (vrátane ochranných pásiem alebo CHVO) alebo stupeň ochrany > 0; `false`, ak nie je spomenuté nič o chránených územiach ani stupňoch ochrany. Ak informácia chýba, uveď `null`.
*   `dotknute_zivocichy_rastliny`: Zoznam explicitne spomenutých chránených, ohrozených alebo inak významných živočíchov alebo rastlín, prípadne skupiny (napr. "bobor vodný", "vydra riečna", "ichtyofauna", "bentická fauna", "brehové porasty"). Ak nie sú uvedené, ponechaj prázdny zoznam `[]`.
*   `odkaz_enviroportal`: URL adresa na enviroportal.sk, ak je v dokumente uvedená.
*   `paragrafy`: Zoznam paragrafov ktoré sa vzťahujú na daný dokument. Ak nie sú uvedené, ponechaj prázdny zoznam `[]`. Pre každý paragraf môžeš vyplniť polia: "paragraf" (číslo paragrafu), "odsek" (číslo odseku), "pismena" (pole písmen), "zakon_nazov" (názov zákona) a "zakon_cislo" (číslo zákona). Ak nie sú uvedené žiadne paragrafy, ponechaj prázdny zoznam `[]`.
*   `zhrnutie`: Stručné a výstižné zhrnutie dokumentu (max 2-3 vety) s dôrazom na typ zásahu, miesto (obec, lokalita) a spomenuté chránené územia/druhy, ak sú relevantné pre záujmy LZ VLK.

**Pokyny pre model:**

*   Extrahuj informácie iba z poskytnutého textu dokumentu. Nepridávaj externé znalosti o lokalitách (či sú v chránených územiach, ak to dokument explicitne neuvádza), okrem extrakcie explicitných názvov chránených území alebo stupňov ochrany, ak sú v texte.
*   Vyplň JSON presne podľa definovanej štruktúry.
*   Pre polia s textovou hodnotou, ak informácia chýba, použij `null`.
*   Pre polia so zoznamom hodnôt, ak žiadne položky nie sú nájdené, použi prázdny zoznam `[]`.
*   Pre booleovské pole `je_v_chranenom_uzemi` postupuj podľa popisu vyššie.
*   Zaisti, aby výstup bol validný JSON a neobsahoval nič iné.

Text dokumentu:
""" + text_content
    
    try:
        # Použi litellm na volanie LLM (napr. gpt-4o-mini alebo iný model)
        # Uisti sa, že máš nastavené API kľúče ako environmentálne premenné
        response = litellm.completion(
            model="gemini/gemini-2.5-flash-preview-04-17", # Alebo iný model podľa tvojho výberu a dostupnosti
            messages=[{"role": "user", "content": prompt}],
            response_format={ "type": "json_object" }, # Požiadame o JSON výstup
            # reasoning_effort="medium"
        )

        # Extrahuj obsah odpovede (mal by to byť JSON string)
        analysis_result_str = response.choices[0].message.content
        return analysis_result_str

    except Exception as e:
        print(traceback.format_exc(), file=sys.stderr) # Vypíš detail chyby
        raise RuntimeError(f"Chyba počas LLM analýzy: {e}")