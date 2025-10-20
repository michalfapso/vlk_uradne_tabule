import json
import re
import os

MAX_RECURSION_DEPTH = 3 # Maximálna hĺbka rekurzie
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(SCRIPT_DIR, "../../data")
LAWS_DIR = os.path.join(DATA_DIR, "laws")
LAW_REGISTRY_PATH = os.path.join(DATA_DIR, "laws/registry.json")

# --- KROK 1: Vytvorenie registra zákonov ---
def load_main_law_registry(registry_path: str) -> dict:
    """
    Načíta hlavný register zákonov z JSON súboru.
    """
    try:
        with open(registry_path, 'r', encoding='utf-8') as f:
            registry = json.load(f)
            print(f"Register zákonov úspešne načítaný z: {registry_path}")
            return registry
    except FileNotFoundError:
        print(f"CHYBA: Súbor s registrom zákonov '{registry_path}' sa nenašiel.")
        return {}
    except json.JSONDecodeError as e:
        print(f"CHYBA: Súbor s registrom zákonov '{registry_path}' obsahuje nevalidný JSON: {e}")
        return {}
    except Exception as e:
        print(f"CHYBA: Vyskytla sa neočakávaná chyba pri načítaní registra zákonov z '{registry_path}': {e}")
        return {}

def build_law_identifier_regex(registry: dict) -> str:
    """Dynamicky vytvorí časť regulárneho výrazu pre identifikáciu zákonov."""
    all_identifiers = []
    for law_id, details in registry.items():
        # Pridáme všetky definované identifikátory
        all_identifiers.extend(details['names'])
    
    # Zoradíme od najdlhšieho po najkratší, aby sa predišlo predčasnej zhode (napr. "Zákon o dani" vs "Zákon o dani z príjmov")
    all_identifiers.sort(key=len, reverse=True)
    
    # Vytvoríme regex skupinu s identifikátormi (ktoré sú už regulárne výrazy)
    return "|".join(f"(?:{id_pattern})" for id_pattern in all_identifiers)

def find_law_references_advanced(text: str, law_registry: dict) -> list[dict]:
    """
    Nájde referencie na zákony vrátane rozsahov a identifikácie podľa názvu.
    """
    normalized_text = text.replace('\n', ' ')
    
    # Dynamicky vložíme všetky možné názvy zákonov do výrazu
    law_identifiers_pattern = build_law_identifier_regex(law_registry)

    # Fallback pattern for capturing unrecognized law names.
    # It tries to match characters that are not a start of a new paragraph reference,
    # newline, opening parenthesis, common punctuation followed by space, or specific conjunctions.
    # This helps make reference['str'] more complete for unknown laws.
    # Non-greedy, stops at logical boundaries.
    # The negative lookahead ensures that the *next character* to be consumed
    # is not the beginning of one of these stop sequences.
    generic_law_text_pattern = r"""(?:(?:(?! # Stop if current position is followed by:
        # More specific/less aggressive stop conditions for generic text
        §\s*\d | # Start of another paragraph reference - strong stop
        \s\( | # Space followed by opening parenthesis - strong stop (e.g. for "(ďalej len...)")
        \s*[\r\n] | # Newline (optional preceding spaces) - strong stop
        # Punctuation that clearly ends a phrase, especially if followed by space or common conjunction
        # (?:[\.,;])(?=\s+(?:a|alebo|aj|i|no|či|že|keď|ak|aby|lebo|pretože|ktorý|ktorá|ktoré|$)) |
        \s-\s | # Hyphen as a separator like "word - word" - strong stop
        \s+(?:a|alebo|aj|i|no|či|teda|avšak|tiež|napríklad|okrem|vrátane|podľa|v zmysle|ktorý|ktorá|ktoré|zákona|predpisu)\b # Common words that usually end a reference
    ).){1,85})""" # Max length for unknown law names, now greedy repetition
    # Note: (?:[\.,;])(?=\s|$) will make the punctuation itself the last consumed char if it's a stop.

    regex_pattern = re.compile(fr"""
        §\s*(?P<paragraf_start>\d+[a-z]?)                               # Začiatok rozsahu paragrafu, napr. § 47
        (?: \s* (?:až|-|\.\.) \s* (?P<paragraf_end>\d+[a-z]?) )?         # Voliteľný koniec rozsahu paragrafu, napr. ..49

        (?:                                                             # Voliteľná skupina pre odsek
            \s+ods(?:t)?\.\s*(?P<odsek_start>\d+)
            (?: \s* (?:až|-|\.\.) \s* (?P<odsek_end>\d+) )?
        )?
        
        (?:                                                             # Voliteľná skupina pre písmeno
            \s+písm\.\s*(?P<pismeno_start>[a-z])\)?
            (?: \s* (?:až|-|\.\.) \s* (?P<pismeno_end>[a-z])\)? )?
        )?

        (?: # START Optional group for law identification
            \s+ # Must be preceded by at least one space
            (?: # Option 1: Has "zákona" or "zákona č."
                zákona \s* (?:č\.\s*)? \s*
                (?P<law_after_zakona> (?:{law_identifiers_pattern}) | (?:{generic_law_text_pattern}) )
            |   # Option 2: No "zákona", just the identifier (or generic text)
                (?P<law_direct> (?:{law_identifiers_pattern}) | (?:{generic_law_text_pattern}) )
            )
        )? # END Optional group for law identification
    """, re.IGNORECASE | re.VERBOSE)

    found_references = []
    for match in regex_pattern.finditer(normalized_text):
        reference_data = match.groupdict()
        reference_data['str'] = match.group(0).strip() # Celý nájdený text referencie
        
        # Get the captured law text from either 'law_after_zakona' or 'law_direct'
        captured_law_text_val = reference_data.get('law_after_zakona') or reference_data.get('law_direct')

        if captured_law_text_val:
            # Try to map the captured text to a known law
            found_known_law = False
            for z_id, details in law_registry.items():
                for name_in_registry in details['names']:
                    # name_in_registry je teraz reťazec s regulárnym výrazom
                    if re.fullmatch(name_in_registry, captured_law_text_val.strip(), re.IGNORECASE):
                        reference_data['zakon_id'] = z_id
                        reference_data['zakon_refname'] = captured_law_text_val.strip() # Text zachytený z dokumentu
                        found_known_law = True
                        break
                if found_known_law:
                    break
            if not found_known_law:
                # Law text was captured (possibly by generic_law_text_pattern) but not resolved to a known law
                reference_data['zakon_refname'] = captured_law_text_val.strip()

        # Remove the temporary parsing groups
        reference_data.pop('law_after_zakona', None)
        reference_data.pop('law_direct', None)

        cleaned_reference = {k: v for k, v in reference_data.items() if v is not None}
        found_references.append(cleaned_reference)

    return found_references

def _get_canonical_ref_str(reference: dict) -> str:
    """Vytvorí kanonický reťazec pre referenciu na použitie v 'navštívených' setoch."""
    parts = [
        reference.get("zakon_id", ""),
        reference.get("paragraf_start", ""),
        reference.get("paragraf_end", ""),
        reference.get("odsek_start", ""),
        reference.get("odsek_end", ""),
        reference.get("pismeno_start", ""),
        reference.get("pismeno_end", ""),
    ]
    return "|".join(str(p).lower() for p in parts if p is not None)

def get_law_texts_for_range(reference: dict, law_registry: dict, laws_dir: str, visited_references: set = None, recursion_depth: int = 0) -> list[list[str]]:
    """
    Na základe referencie (aj s rozsahmi) vráti zoznam textov zo zákona.
    Vracia zoznam blokov textov (List[List[str]]), kde každý blok zodpovedá
    jednej spracovanej referencii (pôvodnej alebo rekurzívnej).
    """
    current_block_texts = [] # Texty pre aktuálne spracovávanú referenciu

    zakon_id = reference.get("zakon_id")
    if not zakon_id:
        original_ref_str = reference.get('str', '(text referencie nebol zachytený)')
        law_text_in_ref = reference.get('zakon_refname', '(text zákona nebol špecifikovaný alebo rozpoznaný)')
        current_block_texts.append(f"Chyba: Nebol nájdený kľúč zákona pre referenciu '{original_ref_str}'. Text zákona v referencii: '{law_text_in_ref}'.")
        return [current_block_texts]

    if visited_references is None:
        visited_references = set()

    canonical_current_ref_str = _get_canonical_ref_str(reference)
    if canonical_current_ref_str in visited_references or recursion_depth > MAX_RECURSION_DEPTH:
        return [] # Prázdny zoznam blokov
    visited_references.add(canonical_current_ref_str)

    law_entry = law_registry.get(zakon_id)
    if not law_entry:
        current_block_texts.append(f"Chyba: Zákon s kľúčom '{zakon_id}' neexistuje v registri.")
        return [current_block_texts]


    law_data = law_entry.get('data') # Skontrolujeme, či sú dáta už načítané (cachované)

    if law_data is None:
        # Dáta nie sú načítané, pokúsime sa ich načítať z JSON súboru
        file_name_base = zakon_id.replace('/', '-')
        file_path = os.path.join(laws_dir, f"{file_name_base}.json")

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                law_data = json.load(f)
            law_entry['data'] = law_data # Uložíme načítané dáta do cache pre budúce použitie
        except FileNotFoundError:
            current_block_texts.append(f"Chyba: Dátový súbor '{file_path}' pre zákon '{zakon_id}' sa nenašiel.")
            return [current_block_texts]
        except json.JSONDecodeError:
            current_block_texts.append(f"Chyba: Súbor '{file_path}' neobsahuje validný JSON pre zákon '{zakon_id}'.")
            return [current_block_texts]
        except Exception as e:
            current_block_texts.append(f"Chyba: Nepodarilo sa načítať dáta pre zákon '{zakon_id}' zo súboru '{file_path}': {e}")
            return [current_block_texts]

    p_start = reference.get("paragraf_start")
    p_end = reference.get("paragraf_end", p_start)

    # Pre jednoduchosť predpokladáme, že rozsahy paragrafov sú číselné
    try:
        paragraf_numbers = [str(i) for i in range(int(p_start), int(p_end) + 1)]
    except ValueError:
        paragraf_numbers = [p_start] # Ak paragraf nie je číslo (napr. '12a'), nespracujeme rozsah

    # Použijeme priamo referenčný názov zákona (napr. "ZOPK", "543/2002 Z. z.")
    display_zakon_ref = reference.get("zakon_refname", zakon_id)

    all_resulting_blocks = [] # Zoznam všetkých blokov (aktuálny + rekurzívne)
    sub_refs_for_recursion = []

    for paragraf_num in paragraf_numbers:
        paragraf_obj = next((p for p in law_data if p["cislo_paragrafu"] == paragraf_num), None)
        if not paragraf_obj:
            current_block_texts.append(f"Chyba: Paragraf '{paragraf_num}' sa nenašiel.")
            continue

        paragraf_nadpis = paragraf_obj['nadpis']
        # Kontext pre lokálne referencie z tohto paragrafu/odseku/písmena
        current_text_context = {
            "zakon_id": zakon_id,
            "zakon_refname": display_zakon_ref,
            "paragraf_start": paragraf_num
        }

        odsek_start_str = reference.get("odsek_start")
        if not odsek_start_str: # Ak nie je špecifikovaný odsek, vrátime celý paragraf
            # Formát pre celý paragraf: § <num> (<nadpis>):\n<obsah>
            # alebo § <num> <ref_zakona>: <nadpis> ak je to súčasť rozsahu? Testy sú tu nekonzistentné.
            # Pre jednoduchosť a konzistenciu s ostatnými formátmi:
            title_line = f"§ {paragraf_num} {display_zakon_ref}: {paragraf_nadpis}"
            content_parts = []
            text_to_scan_for_sub_refs = []

            odseky = paragraf_obj.get("odseky", [])
            for o in odseky:
                odsek_text_part = (f"({o['cislo_odseku']}) " if len(odseky) > 1 else "") + o['text']
                text_to_scan_for_sub_refs.append(o['text'])
                if o.get("pismena"):
                    for pis in o["pismena"]:
                        odsek_text_part += f"\n  {pis['pismeno']}) {pis['text']}"
                        text_to_scan_for_sub_refs.append(pis['text'])
                content_parts.append(odsek_text_part)
            
            current_block_texts.append(f"{title_line}\n" + "\n".join(content_parts) if content_parts else title_line)

            # Skenovanie obsahu paragrafu
            combined_text_to_scan = "\n".join(text_to_scan_for_sub_refs)

            # Find all § references in the text (explicit or implicit)
            found_sub_refs = find_law_references_advanced(combined_text_to_scan, law_registry)
            
            # For references found without an explicit law identifier, assume they refer to the current law
            for sub_ref in found_sub_refs:
                if sub_ref.get("zakon_id") is None:
                    sub_ref["zakon_id"] = zakon_id # Use the current law's ID
                    sub_ref["zakon_refname"] = display_zakon_ref # Use the current law's ref name
            sub_refs_for_recursion.extend(found_sub_refs)
            continue

        # Ak je špecifikovaný odsek/písmeno, najprv hlavička paragrafu
        current_block_texts.append(f"§ {paragraf_num} {display_zakon_ref}: {paragraf_nadpis}")

        odsek_end_str = reference.get("odsek_end", odsek_start_str)
        odsek_numbers = [i for i in range(int(odsek_start_str), int(odsek_end_str) + 1)]

        for odsek_num in odsek_numbers:
            odsek_obj = next((o for o in paragraf_obj.get("odseky", []) if "cislo_odseku" in o and o["cislo_odseku"] == odsek_num), None)
            if not odsek_obj:
                current_block_texts.append(f"Chyba: § {paragraf_num} ods. {odsek_num} sa nenašiel.")
                continue

            current_text_context["odsek_start"] = str(odsek_num) # Aktualizácia kontextu
            odsek_text_content = odsek_obj['text']
            odsek_header = f"§ {paragraf_num} ods. {odsek_num} {display_zakon_ref}:"

            pi_start_char = reference.get("pismeno_start")
            if not pi_start_char: # Ak nie je špecifikované písmeno
                # Celý odsek vrátane písmen
                odsek_display_parts = [f"{odsek_header}\n{odsek_text_content}"]
                text_to_scan_for_sub_refs = [odsek_text_content]
                for p_obj in odsek_obj.get("pismena", []):
                    odsek_display_parts.append(f"  {p_obj['pismeno']}) {p_obj['text']}")
                    text_to_scan_for_sub_refs.append(p_obj['text'])
                current_block_texts.append("\n".join(odsek_display_parts))

                combined_text_to_scan = "\n".join(text_to_scan_for_sub_refs)
                found_sub_refs_for_odsek = find_law_references_advanced(combined_text_to_scan, law_registry)

                for sub_ref in found_sub_refs_for_odsek:
                    if sub_ref.get("zakon_id") is None:
                        sub_ref["zakon_id"] = zakon_id
                        sub_ref["zakon_refname"] = display_zakon_ref
                sub_refs_for_recursion.extend(found_sub_refs_for_odsek)
                continue
            
            # Ak je špecifikované písmeno, pridáme text rodičovského odseku
            current_block_texts.append(f"{odsek_header}\n{odsek_text_content}")

            # Skenujeme text odseku, pretože písmeno je v jeho kontexte
            found_sub_refs_in_odsek_parent_text = find_law_references_advanced(odsek_text_content, law_registry)
            for sub_ref in found_sub_refs_in_odsek_parent_text:
                 if sub_ref.get("zakon_id") is None:
                    sub_ref["zakon_id"] = zakon_id
                    sub_ref["zakon_refname"] = display_zakon_ref
            sub_refs_for_recursion.extend(found_sub_refs_in_odsek_parent_text)

            pi_end_char = reference.get("pismeno_end", pi_start_char)
            pismeno_chars = [chr(c) for c in range(ord(pi_start_char), ord(pi_end_char) + 1)]

            if not odsek_obj.get("pismena"):
                current_block_texts.append(f"Chyba: § {paragraf_num} ods. {odsek_num} neobsahuje písmená.")
                continue

            for pismeno_char in pismeno_chars:
                pismeno_obj = next((p for p in odsek_obj.get("pismena", []) if p["pismeno"] == pismeno_char), None)
                if pismeno_obj:
                    pismeno_text = pismeno_obj['text']
                    current_block_texts.append(f"§ {paragraf_num} ods. {odsek_num} písm. {pismeno_char}) {display_zakon_ref}:\n{pismeno_text}")

                    # Process sub-references found in pismeno text
                    found_sub_refs_in_pismeno = find_law_references_advanced(pismeno_text, law_registry)
                    for sub_ref in found_sub_refs_in_pismeno:
                         if sub_ref.get("zakon_id") is None:
                            sub_ref["zakon_id"] = zakon_id
                            sub_ref["zakon_refname"] = display_zakon_ref
                    sub_refs_for_recursion.extend(found_sub_refs_in_pismeno)
                else:
                    current_block_texts.append(f"Chyba: § {paragraf_num} ods. {odsek_num} písm. {pismeno_char}) sa nenašlo.")

    # Ak boli pre aktuálnu referenciu zozbierané nejaké texty (vrátane chýb), pridáme ich ako blok.
    if current_block_texts:
        all_resulting_blocks.append(current_block_texts)

    # Rekurzívne spracovanie nájdených pod-referencií
    if sub_refs_for_recursion and recursion_depth < MAX_RECURSION_DEPTH:
        unique_sub_refs_to_call = []
        seen_sub_ref_strs = set()
        for sub_ref in sub_refs_for_recursion:
            sub_ref_canonical = _get_canonical_ref_str(sub_ref)
            if sub_ref_canonical not in visited_references and sub_ref_canonical not in seen_sub_ref_strs:
                # Základná validácia, či má referencia dosť info na spracovanie (musí mať aspoň zákon a paragraf)
                # zakon_id should always be present here due to the logic above
                if sub_ref.get("zakon_id") and sub_ref.get("paragraf_start"):
                    unique_sub_refs_to_call.append(sub_ref)
                    seen_sub_ref_strs.add(sub_ref_canonical)

        if unique_sub_refs_to_call:
            for sub_ref_item in unique_sub_refs_to_call:
                recursive_texts = get_law_texts_for_range(sub_ref_item, law_registry, laws_dir, visited_references, recursion_depth + 1)
                all_resulting_blocks.extend(recursive_texts)

    return all_resulting_blocks

def get_law_excerpts_for_text(text: str) -> str:
    LAW_REGISTRY = load_main_law_registry(LAW_REGISTRY_PATH)
    laws = ""
    laws_count = 0
    if not LAW_REGISTRY:
        raise RuntimeError("Register zákonov (LAW_REGISTRY) je prázdny alebo sa ho nepodarilo načítať.")
    else:
        # 1. Nájdi všetky primárne referencie v dokumente
        referencie = find_law_references_advanced(text, LAW_REGISTRY)

        # 2. Pre každú referenciu nájdi a vypíš texty zákona
        for i, ref in enumerate(referencie):
            list_of_blocks = get_law_texts_for_range(ref, LAW_REGISTRY, LAWS_DIR)
            for text_block in list_of_blocks:
                if text_block: # Vytlačíme blok a za ním prázdny riadok, len ak blok nie je prázdny
                    for text_line in text_block:
                        laws += text_line + "\n"
                    laws += "\n" # Prázdny riadok oddeľujúci bloky
                    laws_count += 1
        laws = laws.strip()
        print('laws_count:', laws_count)
        print('laws:', laws)
    return laws

# --- Príklad použitia ---
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Testuje extrakciu odkazov na zákony z textu.")
    parser.add_argument(
        "input_text",
        type=str,
        nargs='?',  # Znamená 0 alebo 1 argument. Ak 0, použije sa default.
        help="Text dokumentu na analýzu. Ak nie je zadaný, použije sa predvolený testovací text.",
        default="""
    Žiadosť podávame v zmysle § 47 ods. 3 zákona o ochrane prírody a krajiny.
    Ďalej sa odvolávame na § 14 ods. 1 písm. a) až c) zákona č. 543/2002 Z. z.
    Rovnako je dôležitý aj § 13 ods. 3 písm. a-c ZOPK.
    Ignorujeme § 99 zákona 123/2099 Z.z. ktorý nepoznáme.
    A taktiež § 1 odst. 3 písm. b..c zákona 543/2002 Z. z.
    """
    )
    args = parser.parse_args()
    dokument_na_analyzu = args.input_text

    LAW_REGISTRY = load_main_law_registry(LAW_REGISTRY_PATH)
    if not LAW_REGISTRY:
        print("Nebolo možné spustiť príklad použitia, pretože register zákonov (LAW_REGISTRY) je prázdny alebo sa nepodarilo načítať.", file=sys.stderr)
    else:
        print("\n--- Príklad použitia ---")
        # 1. Nájdi všetky referencie v dokumente
        referencie = find_law_references_advanced(dokument_na_analyzu, LAW_REGISTRY)

        print("\n--- Nájdené a spracované referencie ---")
        print(json.dumps(referencie, indent=2, ensure_ascii=False))
        print("\n" + "="*30 + "\n")
        
        # 2. Pre každú referenciu nájdi a vypíš texty zákona
        print("--- Extrahované texty zákonov ---")
        for i, ref in enumerate(referencie):
            list_of_blocks = get_law_texts_for_range(ref, LAW_REGISTRY, LAWS_DIR)
            for text_block in list_of_blocks:
                if text_block: # Vytlačíme blok a za ním prázdny riadok, len ak blok nie je prázdny
                    for text_line in text_block:
                        print(text_line)
                    print() # Prázdny riadok oddeľujúci bloky