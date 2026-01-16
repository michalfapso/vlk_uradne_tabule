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

    # --- 3. Agregácia a Diffing ---
    print("Agregujem dáta a hľadám nové dokumenty...")
    unified_new = aggregate_and_transform(minv_new, minzp_new)
    unified_old = aggregate_and_transform(minv_old, minzp_old)
    
    old_urls = {doc['url'] for doc in unified_old}
    new_documents = [doc for doc in unified_new if doc['url'] not in old_urls]
    print(f"Nájdených {len(new_documents)} nových dokumentov (podľa URL).")

    # --- 4. Filtrovanie podľa dátumu ---
    DAYS_OLD_THRESHOLD = 1
    print(f"Filtrujem nové dokumenty podľa dátumu (max {DAYS_OLD_THRESHOLD} dní staré)...")
    ten_days_ago = datetime.now() - timedelta(days=DAYS_OLD_THRESHOLD)
    documents_to_process = []
    for doc in new_documents:
        date_str = doc.get('original_data', {}).get('datum')
        if not date_str:
            documents_to_process.append(doc) # Spracujeme, ak nemá dátum
            continue
        try:
            doc_date = datetime.strptime(date_str, '%Y-%m-%d')
            
            # process_specific_doc_id = '555665' # Use for testing specific document:
            process_specific_doc_id = None

            do_process_doc = False
            if process_specific_doc_id:
                doc_id = get_doc_id(doc['url'])
                do_process_doc = doc_id == process_specific_doc_id
            else:
                do_process_doc = doc_date >= ten_days_ago
            if do_process_doc:
                documents_to_process.append(doc)
        except (ValueError, TypeError):
            documents_to_process.append(doc) # Spracujeme, ak je formát dátumu neplatný
    
    print(f"Nájdených {len(documents_to_process)} nových dokumentov na spracovanie starých max {DAYS_OLD_THRESHOLD} dní.")
    
    
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
