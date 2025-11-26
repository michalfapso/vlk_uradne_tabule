import json
import re
import os

# --- DEBUG FLAG ---
DEBUG = False

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
            if DEBUG: print(f"DEBUG: Register zákonov úspešne načítaný z: {registry_path}")
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
    Používa dvoj-prechodovú stratégiu na správne spracovanie reťazených odkazov.
    """
    normalized_text = text.replace('\n', ' ')
    if DEBUG: print(f"\n{'='*20}\nDEBUG: Normalizovaný text:\n'{normalized_text}'\n{'='*20}")

    # --- Regex pre jednotlivé § klauzuly (s pomenovanými skupinami) ---
    # --- Regex pre jednotlivé § klauzuly (s pomenovanými skupinami) ---
    # Upravené tak, aby akceptovalo aj začiatok "odsek X" alebo "písmeno Y" bez §
    single_ref_pattern_named = r"""
        (?:
            §\s*(?P<paragraf_start>\d+[a-z]?)
            (?: \s* (?:až|-|\.\.) \s* (?P<paragraf_end>\d+[a-z]?) )?
            (?: \s+ods(?:ek|eku|ekom|t)?\.\s*(?P<odsek_start>\d+) (?: \s* (?:až|-|\.\.) \s* (?P<odsek_end>\d+) )? )?
            (?: \s+písm(?:eno|ena|ená|enom|enami)?\.\s*(?P<pismeno_start>[a-z])\)? (?: \s* (?:až|-|\.\.) \s* (?P<pismeno_end>[a-z])\)? )? )?
        |
            (?:ods(?:ek|eku|ekom|t)?\.?)\s*(?P<odsek_only_start>\d+)
            (?: \s* (?:až|-|\.\.) \s* (?P<odsek_only_end>\d+) )?
            (?: \s+písm(?:eno|ena|ená|enom|enami)?\.\s*(?P<pismeno_only_start>[a-z])\)? (?: \s* (?:až|-|\.\.) \s* (?P<pismeno_only_end>[a-z])\)? )? )?
        |
            (?:písm(?:eno|ena|ená|enom|enami)?\.?)\s*(?P<pismeno_pure_start>[a-z])\)?
            (?: \s* (?:až|-|\.\.) \s* (?P<pismeno_pure_end>[a-z])\)? )?
        )
    """
    sub_ref_regex = re.compile(single_ref_pattern_named, re.IGNORECASE | re.VERBOSE)

    # --- Vzor pre štruktúru jednej referencie (bez pomenovaných skupín) ---
    # Musí byť zosúladený s single_ref_pattern_named
    single_ref_structure_pattern = r"""
        (?:
            §\s*\d+[a-z]?
            (?: \s* (?:až|-|\.\.) \s* \d+[a-z]? )?
            (?: \s+ods(?:ek|eku|ekom|t)?\.\s*\d+ (?: \s* (?:až|-|\.\.) \s* \d+ )? )?
            (?: \s+písm(?:eno|ena|ená|enom|enami)?\.\s*[a-z]\)? (?: \s* (?:až|-|\.\.) \s* [a-z]\)? )? )?
        |
            (?:ods(?:ek|eku|ekom|t)?\.?)\s*\d+
            (?: \s* (?:až|-|\.\.) \s* \d+ )?
            (?: \s+písm(?:eno|ena|ená|enom|enami)?\.\s*[a-z]\)? (?: \s* (?:až|-|\.\.) \s* [a-z]\)? )? )?
        |
            (?:písm(?:eno|ena|ená|enom|enami)?\.?)\s*[a-z]\)?
            (?: \s* (?:až|-|\.\.) \s* [a-z]\)? )?
        )
    """

    # --- Hlavný Regex pre celý blok (vrátane zákona na konci) ---
    generic_law_text_pattern = r"""(?:(?:(?! # Stop if current position is followed by:
        §\s*\d | # Start of another paragraph reference
        (?:ods|písm) | # Start of odsek/pismeno reference
        \s\( | # Space followed by opening parenthesis
        ,\s*   # Comma followed by optional space
    ).){2,150})"""
    
    references_block_pattern = f"(?P<references_block>{single_ref_structure_pattern}(?:\\s*(?:,|a)\\s*{single_ref_structure_pattern})*)"

    main_regex = re.compile(fr"""
        {references_block_pattern}
        (?: # Voliteľná skupina pre identifikáciu zákona
            \s+
            (?:
                zákona \s* (?:č\.\s*)? \s*
                (?P<law_after_zakona> {generic_law_text_pattern} )
            |
                (?P<law_direct> {generic_law_text_pattern} )
            )
        )?
    """, re.IGNORECASE | re.VERBOSE)

    found_references = []
    last_known_zakon_id = None
    last_known_zakon_refname = None
    anaphoric_phrases = {"citovaného zákona"}

    match_count = 0
    for match in main_regex.finditer(normalized_text):
        match_count += 1
        if DEBUG: print(f"\n--- DEBUG: Hlavný Regex Match #{match_count} ---")
        if DEBUG: print(f"  Celý match: '{match.group(0)}'")

        match_dict = match.groupdict()
        if DEBUG: print(f"  Zachyt. skupina 'references_block': '{match_dict.get('references_block')}'")
        
        captured_law_text = match_dict.get('law_after_zakona') or match_dict.get('law_direct')
        if DEBUG: print(f"  Zachyt. text zákona (surový): '{captured_law_text}'")
        
        zakon_id = None
        zakon_refname = None

        if captured_law_text:
            stripped_law_text = captured_law_text.strip().rstrip('.,;')
            if DEBUG: print(f"  Spracovávaný text zákona: '{stripped_law_text}'")

            if stripped_law_text.lower() in anaphoric_phrases:
                if last_known_zakon_id:
                    zakon_id = last_known_zakon_id
                    zakon_refname = last_known_zakon_refname
                    if DEBUG: print(f"  => ANAPHORIC REFERENCE! Použitý posledný známy zákon: ID='{zakon_id}', Meno='{zakon_refname}'")
                else:
                    zakon_refname = stripped_law_text
                    if DEBUG: print(f"  => ANAPHORIC REFERENCE, ale predchádzajúci zákon nebol nájdený. Ponechaný text: '{zakon_refname}'")
            else:
                best_match_id = None
                best_match_name = ""
                for z_id, details in law_registry.items():
                    for name_in_registry in details['names']:
                        law_match = re.match(name_in_registry, stripped_law_text, re.IGNORECASE)
                        if law_match:
                            matched_text = law_match.group(0)
                            if len(matched_text) > len(best_match_name):
                                best_match_name = matched_text
                                best_match_id = z_id
                
                if best_match_id:
                    zakon_id = best_match_id
                    zakon_refname = best_match_name
                    last_known_zakon_id = zakon_id
                    last_known_zakon_refname = zakon_refname
                    if DEBUG: print(f"  => NÁJDENÝ ZNÁMY ZÁKON! ID: '{zakon_id}', Meno: '{zakon_refname}'. Aktualizovaný posledný známy zákon.")
                else:
                    zakon_refname = stripped_law_text
                    if DEBUG: print(f"  => NEZNÁMY ZÁKON. Ponechaný text: '{zakon_refname}'")
        else:
            if DEBUG: print("  Text zákona nebol v tomto matchi nájdený.")

        references_block_text = match_dict['references_block']
        sub_match_count = 0
        for sub_match in sub_ref_regex.finditer(references_block_text):
            sub_match_count += 1
            if DEBUG: print(f"  --- Sub-match #{sub_match_count} v bloku ---")
            
            raw_data = sub_match.groupdict()
            reference_data = {}
            
            # Normalizácia kľúčov (odstránenie _only/_pure suffixov)
            if raw_data.get('paragraf_start'):
                reference_data['paragraf_start'] = raw_data['paragraf_start']
                if raw_data.get('paragraf_end'): reference_data['paragraf_end'] = raw_data['paragraf_end']
                if raw_data.get('odsek_start'): reference_data['odsek_start'] = raw_data['odsek_start']
                if raw_data.get('odsek_end'): reference_data['odsek_end'] = raw_data['odsek_end']
                if raw_data.get('pismeno_start'): reference_data['pismeno_start'] = raw_data['pismeno_start']
                if raw_data.get('pismeno_end'): reference_data['pismeno_end'] = raw_data['pismeno_end']
            
            elif raw_data.get('odsek_only_start'):
                reference_data['odsek_start'] = raw_data['odsek_only_start']
                if raw_data.get('odsek_only_end'): reference_data['odsek_only_end'] = raw_data['odsek_only_end']
                if raw_data.get('pismeno_only_start'): reference_data['pismeno_only_start'] = raw_data['pismeno_only_start']
                if raw_data.get('pismeno_only_end'): reference_data['pismeno_only_end'] = raw_data['pismeno_only_end']
                
            elif raw_data.get('pismeno_pure_start'):
                reference_data['pismeno_start'] = raw_data['pismeno_pure_start']
                if raw_data.get('pismeno_pure_end'): reference_data['pismeno_pure_end'] = raw_data['pismeno_pure_end']

            reference_data['str'] = sub_match.group(0).strip()
            if DEBUG: print(f"    Pôvodné dáta: {reference_data}")
            
            if zakon_id:
                reference_data['zakon_id'] = zakon_id
            if zakon_refname:
                reference_data['zakon_refname'] = zakon_refname
            
            if DEBUG: print(f"    Finálne dáta: {reference_data}")
            found_references.append(reference_data)

    if DEBUG: print(f"\nDEBUG: Celkový počet nájdených referencií: {len(found_references)}")
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
        # print(f"Chyba: Nebol nájdený kľúč zákona pre referenciu '{original_ref_str}'. Text zákona v referencii: '{law_text_in_ref}'.")
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
                
                # Propagate paragraph context if missing
                if not sub_ref.get("paragraf_start"):
                    sub_ref["paragraf_start"] = paragraf_num

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
                    
                    # Propagate paragraph context if missing
                    if not sub_ref.get("paragraf_start"):
                        sub_ref["paragraf_start"] = paragraf_num
                    
                    # NOTE: We generally don't propagate odsek number to sub-references found inside the odsek text,
                    # because "písmeno a)" inside "odsek 3" usually refers to "odsek 3 písmeno a)",
                    # BUT "odsek 5" inside "odsek 3" refers to "odsek 5" of the same paragraph.
                    # So we only propagate paragraph number.
                    # Exception: if it says just "písmeno a)", it implies current paragraph AND current odsek?
                    # Actually, usually "písmeno a)" is a child of an odsek.
                    # If the text says "podľa písmena a)", it refers to "odsek X písmeno a)" where X is likely THIS odsek,
                    # OR it refers to "§ Y písmeno a)" if the paragraph has letters directly (rare in SK laws, usually letters are under odsek).
                    # Let's assume if we find "písmeno X" without odsek/paragraf, it belongs to THIS odsek.
                    if not sub_ref.get("paragraf_start") and not sub_ref.get("odsek_start") and sub_ref.get("pismeno_start"):
                         sub_ref["odsek_start"] = str(odsek_num)

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
                 if not sub_ref.get("paragraf_start"):
                    sub_ref["paragraf_start"] = paragraf_num
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
                         if not sub_ref.get("paragraf_start"):
                            sub_ref["paragraf_start"] = paragraf_num
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
        # print('laws:', laws)
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