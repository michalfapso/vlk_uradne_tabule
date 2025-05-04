import json
import os
import litellm
from urllib.parse import urlparse, parse_qs
import re
import unicodedata
import sys

# Nastavenie modelu pre litellm (podľa vašej požiadavky)
# Skontrolujte najnovší dostupný model Flash, ak by tento nefungoval
# MODEL_NAME = "gemini/gemini-2.5-pro-preview-03-25"
MODEL_NAME = "gemini/gemini-2.5-flash-preview-04-17"

# --- Pomocné funkcie ---

def sanitize_filename(name: str) -> str:
    """Odstráni diakritiku a nahradí ne-alfanumerické znaky podtržníkom."""
    # Normalizuj (rozloží znaky a diakritiku)
    nfkd_form = unicodedata.normalize('NFKD', name)
    # Ponechaj len ASCII znaky (zbaví sa diakritiky)
    ascii_name = "".join([c for c in nfkd_form if not unicodedata.combining(c)])
    # Nahraď medzery podtržníkom
    name_with_underscores = ascii_name.replace(' ', '_')
    # Nahraď všetky zostávajúce ne-alfanumerické znaky (okrem podtržníka) podtržníkom
    sanitized = re.sub(r'[^\w_]+', '_', name_with_underscores)
    # Odstráň prípadné viacnásobné podtržníky za sebou
    sanitized = re.sub(r'_+', '_', sanitized)
    # Odstráň podtržníky na začiatku/konci
    sanitized = sanitized.strip('_')
    return sanitized

def extract_subor_id(doc_url: str) -> str | None:
    """Extrahuje hodnotu parametra 'subor' z URL."""
    try:
        parsed_url = urlparse(doc_url)
        query_params = parse_qs(parsed_url.query)
        # parse_qs vracia hodnoty ako zoznamy, aj keď je tam len jedna
        subor_list = query_params.get('subor', [])
        if subor_list:
            return subor_list[0]
        else:
            print(f" upozornenie: Parameter 'subor' nenájdený v URL: {doc_url}")
            return None
    except Exception as e:
        print(f" Chyba pri parsovaní URL {doc_url}: {e}")
        return None

# --- Hlavná logika ---

def main(json_file_path: str):
    """Načíta JSON, prečíta texty dokumentov a vygeneruje prompt pomocou LLM."""
    try:
        with open(json_file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"Chyba: Vstupný súbor '{json_file_path}' nebol nájdený.")
        return
    except json.JSONDecodeError:
        print(f"Chyba: Súbor '{json_file_path}' neobsahuje validný JSON.")
        return
    except Exception as e:
        print(f"Nastala neočakávaná chyba pri čítaní JSON súboru: {e}")
        return

    example_docs_content = []
    base_docs_path = "docs"

    print("Spracovávam dokumenty a hľadám textové súbory...")

    for kraj_data in data:
        kraj_name_raw = kraj_data.get("kraj")
        if not kraj_name_raw:
            print(" Varovanie: Nájdený záznam kraja bez názvu.")
            continue

        for okres_data in kraj_data.get("okresy", []):
            okres_name_raw = okres_data.get("nazov")
            if not okres_name_raw:
                print(f" Varovanie: Nájdený záznam okresu bez názvu v kraji '{kraj_name_raw}'.")
                continue

            for kategoria_data in okres_data.get("dokumenty_zivotne_prostredie", []):
                for dokument in kategoria_data.get("dokumenty", []):
                    doc_url = dokument.get("url")
                    doc_nazov = dokument.get("nazov", "Neznámy názov dokumentu")

                    if not doc_url:
                        print(f" Varovanie: Dokument '{doc_nazov}' v {kraj_name_raw}/{okres_name_raw} nemá URL.")
                        continue

                    subor_id = extract_subor_id(doc_url)
                    if not subor_id:
                        print(f" Varovanie: Nepodarilo sa extrahovať 'subor' ID pre dokument '{doc_nazov}' ({doc_url}).")
                        continue

                    # Zostav cestu k súboru
                    file_path = os.path.join(
                        base_docs_path,
                        kraj_name_raw,
                        okres_name_raw,
                        subor_id,
                        "text.txt"
                    )

                    # Skús prečítať súbor
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                        example_docs_content.append({
                            "path": file_path,
                            "content": content
                        })
                        print(f"  OK: Načítaný súbor: {file_path}")
                    except FileNotFoundError:
                        print(f"  CHYBA: Súbor nenájdený: {file_path}", file=sys.stderr)
                    except Exception as e:
                        print(f"  CHYBA: Nepodarilo sa prečítať súbor {file_path}: {e}", file=sys.stderr)

    if not example_docs_content:
        print("\nNeboli nájdené žiadne textové súbory pre príklady. Ukončujem.")
        return

    print(f"\nNačítaných {len(example_docs_content)} príkladov dokumentov.")
    print("Pripravujem požiadavku pre LLM...")

    # Zostav text príkladov pre LLM
    examples_text = "\n\n---\n\n".join([
        # f"Príklad dokumentu (z {doc['path']}):\n\n{doc['content'][:2000]}..." # Môžeme skrátiť, ak je textov veľa
        # if len(doc['content']) > 2000 else
        f"Príklad dokumentu (z {doc['path']}):\n\n{doc['content']}"
        for doc in example_docs_content
    ])

    # Zostav prompt pre LLM (meta-prompt)
    meta_prompt = f"""
Ahoj, tu sú príklady dokumentov vyvesených na úradných tabuliach okresných úradov, odborov starostlivosti o životné prostredie. Tieto dokumenty boli skonvertované z pôvodných formátov (často PDF) na čistý text.

Potrebujem, aby si vytvoril(a) *nový, vylepšený prompt* pre jazykový model (LLM). Tento nový prompt bude slúžiť na analýzu *jednotlivých* takýchto dokumentov (poskytnutých ako čistý text). Cieľom analýzy je získať štruktúrované informácie vo formáte JSON, ktoré pomôžu organizácii Lesoochranárske zoskupenie VLK (LZ VLK) rýchlo sa rozhodnúť, či má záujem vstúpiť do správneho konania týkajúceho sa daného dokumentu.

**Kľúčové záujmy LZ VLK:**
LZ VLK vstupuje do konaní najmä v prípadoch, keď sa konanie týka:
1.  **Zásahov do chránených území:** Zvláštny dôraz na prírodné rezervácie (najmä s 5. stupňom ochrany), chránené areály, národné parky, CHKO a územia európskeho významu (NATURA 2000 - SKUEV, SKCHVU).
2.  **Typov zásahov:** Najmä výruby drevín, ťažba dreva, odstrel alebo iné usmrcovanie chránených živočíchov, používanie chemických látok v prírodnom prostredí, výstavba (cesty, budovy, energetické diela, vodné stavby, oplotenia atď.) v prírodnom alebo blízkoprírodnom prostredí.
3.  **Usmrcovania chránených živočíchov:** Povolenia na odstrel (napr. medveď, vlk), plašenie, odchyt, alebo iné konania týkajúce sa chránených druhov.

**Môj aktuálny návrh promptu (ktorý chcem, aby si vylepšil):**

```prompt
Analyzuj tento dokument z nástenky okresného úradu životného prostredia, ktorý bol skonvertovaný z PDF do textu. Vráť len JSON s nasledujúcou štruktúrou:

{{
  "typ_zasahu": [...],
  "typ_uzemia": "..."
  "zhrnutie": "..."
}}

Zisti, či sa dokument týka nejakého zásahu ("výrub", "odstrel", "chémia", "stavba", "cesta", ...) a zdetekované typy zásahov zapíš do poľa "typ_zasahu", môžeš do toho poľa zapísať viacero hodnôt, ak treba. Ak si nie si istý, o aký typ zásahu ide, daj do toho poľa iba "neviem".

Ak sa dokument týka nejakého chráneného územia, do "typ_uzemia" daj "chránené". Ak ale vieš, o aký typ chráneného územia konkrétne ide (CHKO, národný park, prírodná rezervácia, ...) alebo vieš číslo stupňa ochrany (napr. "5. stupeň"), zapíš do "typ_uzemia" takýto konkrétnejší údaj. Ak sa netýka chráneného územia, daj tam "nechránené". Ak sa v dokumente nespomína, či ide o chránené územie, daj tam "neviem". Ak sa netýka žiadneho územia (napr. ide len o organizačné oznámenie), nechaj tam prázdny reťazec.

Do "zhrnutie" daj krátke zhrnutie dokumentu hlavne s dôrazom na typy zásahov a chránených území.

Text dokumentu:
{{text_content}}
```

      
**Tvoja úloha:**
Na základe poskytnutých príkladov dokumentov a popisu záujmov LZ VLK, navrhni **finálny, čo najlepší prompt**, ktorý bude LLM inštruovať, aby z textu *jedného* dokumentu (ktorý bude v promte označený ako `{{text_content}}`) extrahoval relevantné informácie do JSON štruktúry. Výsledný JSON by mal byť čo najužitočnejší pre rozhodovanie LZ VLK. Zváž, či je existujúca JSON štruktúra dostatočná, alebo či by bolo vhodné ju upraviť (napr. pridať polia pre konkrétne parcely, katastrálne územia, názvy chránených území, stupeň ochrany, názov konania/rozhodnutia, identifikáciu žiadateľa/dotknutej osoby, lehoty na vyjadrenie a pod.).

**Výstupom tvojej odpovede má byť iba samotný text nového promptu.** Nezahŕňaj žiadne vysvetlenia pred alebo po prompte, len čistý text promptu.

**Príklady textov dokumentov:**
{examples_text}

**Teraz, prosím, vygeneruj ten vylepšený prompt:**
"""

    with open('meta_analysis_prompt.md', 'w', encoding='utf-8') as f:
        f.write(meta_prompt)
        
    return

    print("\nPosielam požiadavku na LLM...")

    try:
        # Zavolaj LLM cez litellm
        response = litellm.completion(
            model=MODEL_NAME,
            messages=[
                {"role": "user", "content": meta_prompt}
            ],
            temperature=0.5, # Nižšia teplota pre konzistentnejší prompt
            max_tokens=2000 # Zvýšenie limitu pre komplexnejší prompt
        )

        # Extrahuj vygenerovaný prompt z odpovede
        # Štruktúra odpovede sa môže mierne líšiť, prispôsobte podľa potreby
        if response.choices and response.choices[0].message and response.choices[0].message.content:
            generated_prompt = response.choices[0].message.content.strip()

            print("\n--- Vygenerovaný Prompt od LLM ---")
            print(generated_prompt)
            print("--- Koniec vygenerovaného Promptu ---")

            # Uloženie promptu do súboru (voliteľné)
            try:
                with open("generated_llm_prompt.txt", "w", encoding="utf-8") as f:
                    f.write(generated_prompt)
                print("\nVygenerovaný prompt bol uložený do súboru 'generated_llm_prompt.txt'")
            except Exception as e:
                print(f"\nChyba pri ukladaní vygenerovaného promptu do súboru: {e}")

        else:
            print("\nChyba: LLM nevrátil očakávaný obsah.")
            print("Celá odpoveď LLM:", response)

    except Exception as e:
        print(f"\nChyba pri komunikácii s LLM ({MODEL_NAME}): {e}")
        import traceback
        traceback.print_exc() # Vypíše detailnejší traceback chyby

# --- Spustenie skriptu ---
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} input_json_file", file=sys.stderr)
        sys.exit(1)

    input_json_file = sys.argv[1] # Názov vášho vstupného JSON súboru
    main(input_json_file)

    