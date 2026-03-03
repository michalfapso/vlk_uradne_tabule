import json
import re
import os

# --- DEBUG FLAG ---
DEBUG = False

MAX_RECURSION_DEPTH = 3 # Maximálna hĺbka rekurzie
MAX_TREE_TEXT_LENGTH = 2500 # Maximálna dĺžka textu pre jeden strom referencií
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
    
    # Kľúčové slová s gramatickými tvarmi
    ods_kw = r"ods(?:ek(?:y|ov|u|om|och|mi)?|t)?\.?"
    pism_kw = r"písm(?:en(?:a|á|o|u|om|ami|ách)?)?\.?"

    # Regex pre jednotlivé § klauzuly (s pomenovanými skupinami)
    single_ref_pattern_named = fr"""
        (?:
            §\s*(?P<paragraf_start>\d+[a-z]?)
            (?: \s* (?:až|-|\.\.) \s* (?P<paragraf_end>\d+[a-z]?) )?
            (?: \s+ {ods_kw} \s*\(?(?P<odsek_start>\d+)\)? (?: \s* (?:až|-|\.\.) \s* \(?(?P<odsek_end>\d+)\)? )? )?
            (?: \s+ {pism_kw} \s*(?P<pismeno_start>[a-z])\b\)? (?: \s* (?:až|-|\.\.) \s* (?P<pismeno_end>[a-z])\b\)? )? )?
        |
            (?: {ods_kw} )\s*\(?(?P<odsek_only_start>\d+)\)?
            (?: \s* (?:až|-|\.\.) \s* \(?(?P<odsek_only_end>\d+)\)? )?
            (?: \s+ {pism_kw} \s*(?P<pismeno_only_start>[a-z])\b\)? (?: \s* (?:až|-|\.\.) \s* (?P<pismeno_only_end>[a-z])\b\)? )? )?
        |
            (?: {pism_kw} )\s*(?P<pismeno_pure_start>[a-z])\b\)?
            (?: \s* (?:až|-|\.\.) \s* (?P<pismeno_pure_end>[a-z])\b\)? )?
        |
            (?P<bare_num>\d+[a-z]?)
            (?: \s* (?:až|-|\.\.) \s* (?P<bare_num_end>\d+[a-z]?) )?
        |
            (?P<bare_letter>[a-z])\b\)?
            (?: \s* (?:až|-|\.\.) \s* (?P<bare_letter_end>[a-z])\b\)? )?
        )
    """
    sub_ref_regex = re.compile(single_ref_pattern_named, re.IGNORECASE | re.VERBOSE)

    # --- Vzor pre štruktúru jednej referencie (bez pomenovaných skupín) ---
    
    # Plná referencia (musí začínať kľúčovým slovom)
    full_ref_structure_pattern = fr"""
        (?:
            §\s*\d+[a-z]?
            (?: \s* (?:až|-|\.\.) \s* \d+[a-z]? )?
            (?: \s+ {ods_kw} \s*\(?\d+\)? (?: \s* (?:až|-|\.\.) \s* \(?\d+\)? )? )?
            (?: \s+ {pism_kw} \s*[a-z]\b\)? (?: \s* (?:až|-|\.\.) \s* [a-z]\b\)? )? )?
        |
            (?: {ods_kw} )\s*\(?\d+\)?
            (?: \s* (?:až|-|\.\.) \s* \(?\d+\)? )?
            (?: \s+ {pism_kw} \s*[a-z]\b\)? (?: \s* (?:až|-|\.\.) \s* [a-z]\b\)? )? )?
        |
            (?: {pism_kw} )\s*[a-z]\b\)?
            (?: \s* (?:až|-|\.\.) \s* [a-z]\b\)? )?
        )
    """

    # "Holá" referencia (číslo alebo písmeno, povolené len v zozname)
    bare_ref_structure_pattern = r"""
        (?:
            \d+[a-z]? (?: \s* (?:až|-|\.\.) \s* \d+[a-z]? )?
        |
            [a-z]\b\)? (?: \s* (?:až|-|\.\.) \s* [a-z]\b\)? )?
        )
    """

    # --- Hlavný Regex pre celý blok (vrátane zákona na konci) ---
    generic_law_text_pattern = r"""(?:(?:(?! # Stop if current position is followed by:
        §\s*\d | # Start of another paragraph reference
        (?:ods|písm) | # Start of odsek/pismeno reference
        \s\( # Space followed by opening parenthesis
    ).){2,150})"""
    
    # Blok referencií: PlnáRef (separátor (PlnáRef | HoláRef))*
    references_block_pattern = f"(?P<references_block>{full_ref_structure_pattern}(?:\\s*(?:,|a|i|aj)\\s*(?:{full_ref_structure_pattern}|{bare_ref_structure_pattern}))*)"

    main_regex = re.compile(fr"""
        {references_block_pattern}
        (?: # Voliteľná skupina pre identifikáciu zákona
            (?: \s+ | \s* , \s* )
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
        
        # Kontext pre inferenciu "holých" referencií
        last_context_type = None # 'paragraf', 'odsek', 'pismeno'
        last_paragraf = None
        last_odsek = None
        
        for sub_match in sub_ref_regex.finditer(references_block_text):
            sub_match_count += 1
            if DEBUG: print(f"  --- Sub-match #{sub_match_count} v bloku ---")
            
            raw_data = sub_match.groupdict()
            reference_data = {}
            
            # 1. Plné referencie - nastavujú kontext
            if raw_data.get('paragraf_start'):
                reference_data['paragraf_start'] = raw_data['paragraf_start']
                if raw_data.get('paragraf_end'): reference_data['paragraf_end'] = raw_data['paragraf_end']
                if raw_data.get('odsek_start'): reference_data['odsek_start'] = raw_data['odsek_start']
                if raw_data.get('odsek_end'): reference_data['odsek_end'] = raw_data['odsek_end']
                if raw_data.get('pismeno_start'): reference_data['pismeno_start'] = raw_data['pismeno_start']
                if raw_data.get('pismeno_end'): reference_data['pismeno_end'] = raw_data['pismeno_end']
                
                last_context_type = 'paragraf'
                last_paragraf = raw_data['paragraf_start']
                last_odsek = raw_data.get('odsek_start') # Môže byť None
                if raw_data.get('pismeno_start'): last_context_type = 'pismeno'
                elif raw_data.get('odsek_start'): last_context_type = 'odsek'

            elif raw_data.get('odsek_only_start'):
                reference_data['odsek_start'] = raw_data['odsek_only_start']
                if raw_data.get('odsek_only_end'): reference_data['odsek_only_end'] = raw_data['odsek_only_end']
                if raw_data.get('pismeno_only_start'): reference_data['pismeno_only_start'] = raw_data['pismeno_only_start']
                if raw_data.get('pismeno_only_end'): reference_data['pismeno_only_end'] = raw_data['pismeno_only_end']
                
                # Ak máme kontext paragrafu, pridáme ho
                if last_paragraf:
                    reference_data['paragraf_start'] = last_paragraf
                
                last_context_type = 'odsek'
                last_odsek = raw_data['odsek_only_start']
                if raw_data.get('pismeno_only_start'): last_context_type = 'pismeno'
                
            elif raw_data.get('pismeno_pure_start'):
                reference_data['pismeno_start'] = raw_data['pismeno_pure_start']
                if raw_data.get('pismeno_pure_end'): reference_data['pismeno_pure_end'] = raw_data['pismeno_pure_end']
                
                if last_paragraf: reference_data['paragraf_start'] = last_paragraf
                if last_odsek: reference_data['odsek_start'] = last_odsek
                
                last_context_type = 'pismeno'

            # 2. Holé referencie - dedia kontext
            elif raw_data.get('bare_num'):
                # Číslo môže byť paragraf alebo odsek, záleží na kontexte
                if last_context_type == 'paragraf':
                    reference_data['paragraf_start'] = raw_data['bare_num']
                    if raw_data.get('bare_num_end'): reference_data['paragraf_end'] = raw_data['bare_num_end']
                    last_paragraf = raw_data['bare_num']
                    last_odsek = None # Reset odseku pri novom paragrafe
                    
                elif last_context_type == 'odsek':
                    reference_data['odsek_start'] = raw_data['bare_num']
                    if raw_data.get('bare_num_end'): reference_data['odsek_end'] = raw_data['bare_num_end']
                    if last_paragraf: reference_data['paragraf_start'] = last_paragraf
                    last_odsek = raw_data['bare_num']
                    
                elif last_context_type == 'pismeno':
                    # Ak sme v písmenách a príde číslo, predpokladáme, že sa vraciame o úroveň vyššie
                    # Ak máme last_odsek, tak to bude ďalší odsek. Ak nie, tak ďalší paragraf.
                    if last_odsek:
                        reference_data['odsek_start'] = raw_data['bare_num']
                        if raw_data.get('bare_num_end'): reference_data['odsek_end'] = raw_data['bare_num_end']
                        if last_paragraf: reference_data['paragraf_start'] = last_paragraf
                        last_context_type = 'odsek'
                        last_odsek = raw_data['bare_num']
                    else:
                        reference_data['paragraf_start'] = raw_data['bare_num']
                        if raw_data.get('bare_num_end'): reference_data['paragraf_end'] = raw_data['bare_num_end']
                        last_context_type = 'paragraf'
                        last_paragraf = raw_data['bare_num']
                        last_odsek = None
                else:
                    # Fallback ak nie je kontext (nemalo by sa stať vďaka regexu bloku)
                    # Ale ak sa stane, považujme za paragraf? Alebo ignorujme?
                    if DEBUG: print(f"    Ignorovaná holá referencia '{raw_data['bare_num']}' bez kontextu.")
                    continue

            elif raw_data.get('bare_letter'):
                # Fix pre "a" ako spojku: Ak je bare_letter "a" (alebo "i") a nemá zátvorku, ignorujeme ho.
                if raw_data['bare_letter'] in ('a', 'i') and not sub_match.group(0).endswith(')'):
                     if DEBUG: print(f"    Ignorovaná spojka '{raw_data['bare_letter']}' (bez zátvorky).")
                     continue

                reference_data['pismeno_start'] = raw_data['bare_letter']
                if raw_data.get('bare_letter_end'): reference_data['pismeno_end'] = raw_data['bare_letter_end']
                
                if last_paragraf: reference_data['paragraf_start'] = last_paragraf
                if last_odsek: reference_data['odsek_start'] = last_odsek
                last_context_type = 'pismeno'

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

def _fetch_law_text_node(reference: dict, law_registry: dict, laws_dir: str) -> tuple[list[str], list[dict]]:
    """
    Načíta text pre danú referenciu (bez rekurzie).
    Vracia dvojicu: (zoznam textových blokov, zoznam nájdených pod-referencií).
    """
    current_block_texts = [] # Texty pre aktuálne spracovávanú referenciu
    sub_refs_found = []

    zakon_id = reference.get("zakon_id")
    if not zakon_id:
        # original_ref_str = reference.get('str', '(text referencie nebol zachytený)')
        # law_text_in_ref = reference.get('zakon_refname', '(text zákona nebol špecifikovaný alebo rozpoznaný)')
        print(f"Warning: Nebol nájdený kľúč zákona pre referenciu '{reference['zakon_refname']}'.", file=sys.stderr)
        return current_block_texts, []

    law_entry = law_registry.get(zakon_id)
    if not law_entry:
        current_block_texts.append(f"Chyba: Zákon s kľúčom '{zakon_id}' neexistuje v registri.")
        return current_block_texts, []

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
            return current_block_texts, []
        except json.JSONDecodeError:
            current_block_texts.append(f"Chyba: Súbor '{file_path}' neobsahuje validný JSON pre zákon '{zakon_id}'.")
            return current_block_texts, []
        except Exception as e:
            current_block_texts.append(f"Chyba: Nepodarilo sa načítať dáta pre zákon '{zakon_id}' zo súboru '{file_path}': {e}")
            return current_block_texts, []

    p_start = reference.get("paragraf_start")
    p_end = reference.get("paragraf_end", p_start)

    if p_start is None:
        # Ak nemáme paragraf, nemôžeme vyhľadať text (referencia je pravdepodobne neúplná)
        return current_block_texts, []

    # Pre jednoduchosť predpokladáme, že rozsahy paragrafov sú číselné
    try:
        paragraf_numbers = [str(i) for i in range(int(p_start), int(p_end) + 1)]
    except (ValueError, TypeError):
        paragraf_numbers = [p_start] # Ak paragraf nie je číslo (napr. '12a') alebo nastala iná chyba, nespracujeme rozsah

    # Použijeme priamo referenčný názov zákona (napr. "ZOPK", "543/2002 Z. z.")
    display_zakon_ref = reference.get("zakon_refname", zakon_id)

    for paragraf_num in paragraf_numbers:
        paragraf_obj = next((p for p in law_data if p["cislo_paragrafu"] == paragraf_num), None)
        if not paragraf_obj:
            current_block_texts.append(f"Chyba: Paragraf '{paragraf_num}' sa nenašiel.")
            continue

        paragraf_nadpis = paragraf_obj['nadpis']
        
        odsek_start_str = reference.get("odsek_start")
        if not odsek_start_str: # Ak nie je špecifikovaný odsek, vrátime celý paragraf
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
            found_sub_refs = find_law_references_advanced(combined_text_to_scan, law_registry)
            
            for sub_ref in found_sub_refs:
                if sub_ref.get("zakon_id") is None:
                    sub_ref["zakon_id"] = zakon_id
                    sub_ref["zakon_refname"] = display_zakon_ref
                if not sub_ref.get("paragraf_start"):
                    sub_ref["paragraf_start"] = paragraf_num

            sub_refs_found.extend(found_sub_refs)
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

                sub_refs_found.extend(found_sub_refs_for_odsek)
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
            sub_refs_found.extend(found_sub_refs_in_odsek_parent_text)

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
                    sub_refs_found.extend(found_sub_refs_in_pismeno)
                else:
                    current_block_texts.append(f"Chyba: § {paragraf_num} ods. {odsek_num} písm. {pismeno_char}) sa nenašlo.")

    return current_block_texts, sub_refs_found

def get_law_excerpts_for_text(text: str) -> str:
    LAW_REGISTRY = load_main_law_registry(LAW_REGISTRY_PATH)
    laws = ""
    laws_count = 0
    if not LAW_REGISTRY:
        raise RuntimeError("Register zákonov (LAW_REGISTRY) je prázdny alebo sa ho nepodarilo načítať.")
    else:
        # 1. Nájdi všetky primárne referencie v dokumente
        primary_references = find_law_references_advanced(text, LAW_REGISTRY)
        if DEBUG: print("\n--- Nájdené a spracované referencie ---")
        if DEBUG: print(json.dumps(primary_references, indent=2, ensure_ascii=False))
        if DEBUG: print("\n" + "="*30 + "\n")

        # 2. Pre každú primárnu referenciu spracuj strom
        if DEBUG: print("--- Extrahované texty zákonov ---")
        global_visited_references = set()
        
        for primary_ref in primary_references:
            # Inicializácia pre strom
            tree_text_blocks = []
            current_tree_length = 0
            
            # Queue pre BFS: zoznam referencií na spracovanie v aktuálnom leveli
            current_level_refs = [primary_ref]
            for depth in range(MAX_RECURSION_DEPTH + 1):
                if DEBUG: print('primary_ref:', primary_ref, ' depth:', depth)
                next_level_refs = []
                level_text_blocks = []
                level_length = 0
                level_visited_refs = [] # Dočasný zoznam pre tento level
                
                for ref in current_level_refs:
                    canonical_ref = _get_canonical_ref_str(ref)
                    if canonical_ref in global_visited_references:
                        continue
                    
                    # Získaj text a pod-referencie
                    text_blocks, sub_refs = _fetch_law_text_node(ref, LAW_REGISTRY, LAWS_DIR)
                    if DEBUG: print('ref:', ref, ' text_blocks:', text_blocks, ' sub_refs:', sub_refs)
                    
                    if text_blocks:
                        level_text_blocks.append(text_blocks)
                        block_len = sum(len(t) for t in text_blocks)
                        level_length += block_len
                        
                        # Pridáme pod-referencie do queue pre ďalší level
                        # Filtrujeme duplicity v rámci queue
                        for sr in sub_refs:
                            if sr.get("zakon_id") and sr.get("paragraf_start"):
                                next_level_refs.append(sr)
                        
                        level_visited_refs.append(canonical_ref)

                # Rozhodnutie o prijatí levelu
                # Level 0 (primárna referencia) berieme vždy
                if DEBUG: print('level_text_blocks:', level_text_blocks)
                if DEBUG: print('current_tree_length:', current_tree_length, ' level_length:', level_length, ' depth:', depth)
                if depth == 0 or (current_tree_length + level_length <= MAX_TREE_TEXT_LENGTH):
                    if DEBUG: print('Prijatý level:', ref, ' depth:', depth, ' level_visited_refs:', level_visited_refs)
                    # Prijímame level
                    for blocks in level_text_blocks:
                        for text_line in blocks:
                            laws += text_line + "\n"
                        laws += "\n"
                        laws_count += 1
                    
                    current_tree_length += level_length
                    
                    # Označíme referencie ako navštívené globálne
                    for v_ref in level_visited_refs:
                        global_visited_references.add(v_ref)
                        
                    # Posunieme sa na ďalší level
                    current_level_refs = next_level_refs
                else:
                    # Zamietame level a končíme spracovanie tohto stromu
                    if DEBUG: print(f"DEBUG: Level {depth} zamietnutý. Dĺžka levelu: {level_length}, Aktuálna dĺžka stromu: {current_tree_length}, Limit: {MAX_TREE_TEXT_LENGTH}")
                    break
                
                if not current_level_refs:
                    break

        laws = laws.strip()
        if DEBUG: print('laws_count:', laws_count)
        # if DEBUG: print('laws:', laws)
    return laws

# --- Príklad použitia ---
if __name__ == "__main__":
    import argparse
    import sys

    parser = argparse.ArgumentParser(description="Testuje extrakciu odkazov na zákony z textu.")
    parser.add_argument(
        "input",
        type=str,
        help="Cesta k súboru s textom, '-' pre stdin.",
        default=None,
    )
    args = parser.parse_args()

    if args.input == '-':
        dokument_na_analyzu = sys.stdin.read()
    else:
        with open(args.input, 'r', encoding='utf-8') as f:
            dokument_na_analyzu = f.read()

    laws = get_law_excerpts_for_text(dokument_na_analyzu)
    print(laws)
