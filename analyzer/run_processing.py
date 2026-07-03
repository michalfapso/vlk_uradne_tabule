# analyzer/run_processing.py
import json
import os
import sys
from typing import List, Dict, Any

# Úprava cesty, aby sme mohli importovať moduly z 'shared'
script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(script_dir, 'shared'))

from log_handler import log_status
from datetime import datetime, timedelta
from get_doc_id import get_doc_id

def load_json_file(filepath: str, default: Any = None) -> Any:
    """Načíta JSON súbor. V prípade chyby vráti predvolenú hodnotu."""
    try:
        if not os.path.exists(filepath):
            # Súbor neexistuje, čo je v poriadku pre *_old.json pri prvom spustení
            return default
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        print(f"Chyba pri načítaní alebo parsovaní JSON súboru {filepath}: {e}", file=sys.stderr)
        # Vrátime predvolenú hodnotu, aby proces mohol pokračovať
        return default

def aggregate_and_transform(
    minv_data: List[Dict], minzp_data: List[Dict]
) -> List[Dict[str, Any]]:
    """
    Zjednotí dáta z minv a minzp do jedného spoločného formátu.
    Každý dokument bude slovník s kľúčmi: url, source, a original_data.
    """
    unified_documents = []

    # Spracovanie MINV dát
    if isinstance(minv_data, list):
        for kraj in minv_data:
            for okres in kraj.get('okresy', []):
                for kategoria in okres.get('dokumenty_zivotne_prostredie', []):
                    for doc in kategoria.get('dokumenty', []):
                        if doc.get('url'):
                            unified_documents.append({
                                "url": doc['url'],
                                "source": "minv",
                                "original_data": {
                                    "kraj": kraj.get('kraj'),
                                    "okres": okres.get('nazov'),
                                    "kategoria": kategoria.get('kategoria'),
                                    **doc  # Skopíruje všetky ostatné kľúče z dokumentu
                                }
                            })

    # Spracovanie MINZP dát
    if isinstance(minzp_data, list):
        for doc in minzp_data:
            if doc.get('url'):
                unified_documents.append({
                    "url": doc['url'],
                    "source": "minzp",
                    "original_data": doc
                })

    return unified_documents

def main():
    """
    Hlavný skript, ktorý orchestrates diffing a spracovanie dokumentov.
    """
    print('main() begin')
    base_dir = os.path.abspath(os.path.join(script_dir, '..'))
    scraped_data_dir = os.path.join(base_dir, 'data', 'scraped')
    docs_output_dir = os.path.join(base_dir, 'data', 'docs')
    
    # --- 1. Archivácia starých dát ---
    # Tento krok sa vykoná v GitHub Action, tu len načítame súbory
    
    # --- 2. Načítanie dát ---
    print("Načítavam staré a nové dáta...")
    minv_new = load_json_file(os.path.join(scraped_data_dir, 'minv_2_documents.json'), default=[])
    minzp_new = load_json_file(os.path.join(scraped_data_dir, 'minzp_2_documents.json'), default=[])
    
    minv_old = load_json_file(os.path.join(scraped_data_dir, 'minv_2_documents_old.json'), default=[])
    minzp_old = load_json_file(os.path.join(scraped_data_dir, 'minzp_2_documents_old.json'), default=[])

    # --- 3. Agregácia a Výber dokumentov ---
    print("Agregujem staré a nové dáta...")
    unified_new = aggregate_and_transform(minv_new, minzp_new)
    unified_old = aggregate_and_transform(minv_old, minzp_old)

    # Nastavenie pre spracovanie konkrétneho dokumentu (ak nie je None, hľadá sa v nových aj starých dátach)
    # PROCESS_SPECIFIC_DOC_IDS_old = ['ou-za-oszp1-2026-036550-buk', 'ou-bb-oszp1-2026-017755-si', '562994', '563021', '562910', '10061-2026-6-1', '562739', '562738', '562783', '562785', '562718', '9937-2026-6-1', '562558', '562557', '562674', 'ou-za-oszp1-2026-033508-kub', '9909-2026-6-1', '562510', '562460', '562479', '562494', '562493', '562491', '562495', '562635', '562449', '562526', '562439', '559962', '8542-2026-6-1']
    # PROCESS_SPECIFIC_DOC_IDS_new = ['ou-bb-oszp1-2026-017755-si', '562994', '562971', '562718', '562738', '562736', '562785', 'ou-bb-oszp1-2026-017325-si', '562740', '562643', '562617', 'ou-za-oszp1-2026-034919-skv', '9937-2026-6-1', '562595', '562558', '562557', '562748', '562555', 'ou-za-oszp1-2026-033508-kub', '562510', '562460', '562479', '562495', '562459', '562467', '562449', '562526', '562439', '560347', '559962', '8542-2026-6-1', '559647', '559666', '559633', '559644']
    # PROCESS_SPECIFIC_DOC_IDS = list(set(PROCESS_SPECIFIC_DOC_IDS_new) - set(PROCESS_SPECIFIC_DOC_IDS_old))
    # PROCESS_SPECIFIC_DOC_IDS = ['563350']
    # print('PROCESS_SPECIFIC_DOC_IDS:', PROCESS_SPECIFIC_DOC_IDS)
    PROCESS_SPECIFIC_DOC_IDS = None

    FORCE_DOCUMENTS_REPROCESSING = False # Má spracovať dokument aj keď už je preňho vytvorený adresár a teda už bol aspoň do nejakej miery spracovaný predtým?

    documents_to_process = []
    if PROCESS_SPECIFIC_DOC_IDS:
        print(f"Hľadám konkrétny dokument s ID {PROCESS_SPECIFIC_DOC_IDS} v nových aj starých dátach...")
        # Pri spracovaní konkrétneho ID hľadáme v oboch množinách (nové aj staré)
        documents_to_process = [
            doc for doc in (unified_new + unified_old)
            if get_doc_id(doc['url']) in PROCESS_SPECIFIC_DOC_IDS
        ]
        print(f"Nájdených {len(documents_to_process)} dokumentov s ID {PROCESS_SPECIFIC_DOC_IDS}.")
        newest_info = ""
    else:
        # --- 4. Diffing a Filtrovanie podľa dátumu (skenovaním systému súborov) ---
        print(f"Skenujem existujúce dokumenty v {docs_output_dir}...")
        existing_doc_ids = set()
        if os.path.exists(docs_output_dir):
            for root, dirs, files in os.walk(docs_output_dir):
                for d in dirs:
                    existing_doc_ids.add(d)
        # print('existing_doc_ids:', existing_doc_ids)
        
        new_documents = []
        for doc in (unified_new + unified_old):
            doc_id = get_doc_id(doc['url'])
            if doc_id and doc_id not in existing_doc_ids or FORCE_DOCUMENTS_REPROCESSING:
                new_documents.append(doc)
        # print('new_documents:', [get_doc_id(doc['url']) for doc in new_documents])
        
        print(f"Nájdených {len(new_documents)} nových dokumentov (ich docid zatiaľ nebolo spracované).")

        DAYS_OLD_THRESHOLD = 7
        print(f"Filtrujem nové dokumenty podľa dátumu (max {DAYS_OLD_THRESHOLD} dní staré)...")
        threshold_date = datetime.now() - timedelta(days=DAYS_OLD_THRESHOLD)
        
        newest_date = None
        oldest_date = None
        for doc in new_documents:
            date_str = doc.get('original_data', {}).get('datum')
            if not date_str:
                documents_to_process.append(doc) # Spracujeme, ak nemá dátum
                continue
            try:
                doc_date = datetime.strptime(date_str, '%Y-%m-%d')
                if newest_date is None or doc_date > newest_date:
                    newest_date = doc_date
                if doc_date >= threshold_date:
                    documents_to_process.append(doc)
                    if oldest_date is None or doc_date < oldest_date:
                        oldest_date = doc_date
                
            except (ValueError, TypeError):
                documents_to_process.append(doc) # Spracujeme, ak je formát dátumu neplatný
        
        if newest_date:
            days_diff = (datetime.now() - newest_date).days
            print(f"Najnovší dokument je z {newest_date.strftime('%Y-%m-%d')}, čo je pred {days_diff} dňami")
        
        oldest_info = ''
        if oldest_date:
            days_diff = (datetime.now() - oldest_date).days
            oldest_info = f" Najstarší dokument na spracovanie je z {oldest_date.strftime('%Y-%m-%d')}, čo je pred {days_diff} dňami"

        print(f"Nájdených {len(documents_to_process)} nových dokumentov na spracovanie starých max {DAYS_OLD_THRESHOLD} dní.{oldest_info}")
    
        #------------------
        # Just for testing:
        #
        # MAX_DOCS = 1
        # documents_to_process = documents_to_process[:MAX_DOCS]
        # print(f'Kvôli testovaniu spracujem iba {len(documents_to_process)} dokumentov.')
        #------------------
    
    with open(f'{scraped_data_dir}/unified_new.json', 'w', encoding='utf-8') as f:
        json.dump(unified_new, f, indent=2, ensure_ascii=False)
    with open(f'{scraped_data_dir}/unified_old.json', 'w', encoding='utf-8') as f:
        json.dump(unified_old, f, indent=2, ensure_ascii=False)
    with open(f'{scraped_data_dir}/documents_to_process.json', 'w', encoding='utf-8') as f:
        json.dump(documents_to_process, f, indent=2, ensure_ascii=False)


    # --- 5. Spracovanie nových dokumentov ---
    if not documents_to_process:
        print("Žiadne nové dokumenty na spracovanie.")
        return

    from document_processor import process_document
    
    processed_count = 0
    failed_count = 0

    for doc_data in documents_to_process:
        print(f"\n--- {documents_to_process.index(doc_data) + 1}/{len(documents_to_process)} Spracovávam: {doc_data['url']} (zdroj: {doc_data['source']}) ---")
        try:
            # Volanie hlavnej spracovateľskej funkcie
            success = process_document(doc_data, docs_output_dir)
            
            if success:
                processed_count += 1
            else:
                failed_count += 1
                # Chyba by už mala byť zalogovaná v rámci `process_document`
                
        except Exception as e:
            failed_count += 1
            # Toto je záchranný blok, ak by `process_document` vyvolal neočakávanú výnimku
            print(f"KRITICKÁ CHYBA: Neočakávaná výnimka pri spracovaní {doc_data['url']}: {e}", file=sys.stderr)
            # Logujeme do globálneho statusu, lebo nevieme, či máme kontext dokumentu
            log_status(
                os.path.join(docs_output_dir, 'status.json'),
                "critical",
                f"Nezachytená výnimka v run_processing.py pre URL {doc_data['url']}: {e}"
            )
            import traceback
            traceback.print_exc(file=sys.stderr)

        # sys.exit(1) # for debugging only

    print("\n--- Zhrnutie spracovania ---")
    print(f"Úspešne spracovaných: {processed_count}")
    print(f"Zlyhalo: {failed_count}")
    print("Spracovanie dokončené.")


if __name__ == "__main__":
    main()

