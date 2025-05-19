import argparse
import json
import os
import re
import sys # Added sys module
import requests
from bs4 import BeautifulSoup
from markdownify import markdownify as md_func # Alias to avoid conflict
from urllib.parse import urlparse
from unidecode import unidecode

# Adjust sys.path to include scripts in the parent directory
script_dir = os.path.dirname(os.path.abspath(__file__))
analyzer_dir = os.path.dirname(script_dir) # parent directory of the current script
sys.path.insert(0, analyzer_dir)

from log_status import log_status
from analyze_text_document import analyze_text_document

def sanitize_okres_name(name):
    if not name:
        return ""
    name = re.sub(r"^Okresný úrad\s+", "", name, flags=re.IGNORECASE)
    name = name.strip(" ")  # Remove leading/trailing underscores
    return name

def sanitize_kraj_name(name):
    if not name:
        return ""
    if name == "Minitsterstvo": # Handling the specific case as requested
        return name

    # Názvy krajov budeme používať rovnaké ako na minv.sk
    kraj_mapping = {
        "Kraj Bratislava": "Bratislavský kraj",
        "Kraj Trnava": "Trnavský kraj",
        "Kraj Trenčín": "Trenčiansky kraj",
        "Kraj Nitra": "Nitriansky kraj",
        "Kraj Banská Bystrica": "Banskobystrický kraj",
        "Kraj Žilina": "Žilinský kraj",
        "Kraj Košice": "Košický kraj",
        "Kraj Prešov": "Prešovský kraj"
    }
    return kraj_mapping.get(name, name)


def download_and_parse_document(doc_url, doc_description, base_docs_dir, status_global):
    """
    Downloads an HTML document, parses it for Kraj, Okres, doc_id, and main content,
    converts main content to Markdown, saves it, and returns the extracted information.
    """
    print(f"Spracovávam URL: {doc_url}")
    try:
        response = requests.get(doc_url, timeout=30)
        response.raise_for_status()  # Vyvolá výnimku pre HTTP chyby (4XX alebo 5XX)
        html_content = response.text
    except requests.exceptions.RequestException as e:
        error_msg = f"Chyba pri sťahovaní {doc_url}: {e}"
        log_status(status_global, "error", f"  {error_msg}")
        return {"error": error_msg}

    soup = BeautifulSoup(html_content, 'html.parser')

    # --- Extrakcia KRAJ a OKRES ---
    # Použijeme breadcrumbs (navigačnú cestu), pretože indikujú kontext aktuálnej stránky.
    # Príklad štruktúry breadcrumbs: ... > Odkaz na Kraj > Odkaz na Okres > Názov dokumentu (text)
    breadcrumb_div = soup.find('div', class_='breadcrumb')
    kraj_name_raw = None
    okres_name_raw = None

    if breadcrumb_div:
        breadcrumb_links = breadcrumb_div.find_all('a')
        # Očakávame Kraj na indexe 2 a Okres na indexe 3 v odkazoch v breadcrumbs
        # napr. Domov > Kategória > Kraj > Okres
        if len(breadcrumb_links) > 2: # Potenciálny Kraj
            text_at_idx2 = breadcrumb_links[2].get_text(strip=True)
            if text_at_idx2.startswith("Kraj ") or text_at_idx2 == "Ministerstvo":
                kraj_name_raw = text_at_idx2
        
        if len(breadcrumb_links) > 3: # Potenciálny Okres
            text_at_idx3 = breadcrumb_links[3].get_text(strip=True)
            if text_at_idx3.startswith("Okresný úrad "):
                okres_name_raw = text_at_idx3
    
    if not kraj_name_raw:
        error_msg = f"KRAJ nebol nájdený alebo nemá očakávaný formát v breadcrumbs pre {doc_url}."
        log_status(status_global, "error", error_msg)
        return {"error": error_msg}
    if kraj_name_raw != "Ministerstvo" and not okres_name_raw:
        error_msg = f"OKRES nebol nájdený alebo nemá očakávaný formát v breadcrumbs pre {doc_url} (Kraj: {kraj_name_raw})."
        log_status(status_global, "error", error_msg)
        return {"error": error_msg}

    kraj_name = sanitize_kraj_name(kraj_name_raw)
    okres_name = sanitize_okres_name(okres_name_raw)
    if kraj_name == "Ministerstvo":
        okres_name = "Ministerstvo"

    if not kraj_name:
        error_msg = f"Vyčistený KRAJ je prázdny pre '{kraj_name_raw}' z {doc_url}."
        log_status(status_global, "error", error_msg)
        return {"error": error_msg}
    if not okres_name:
        error_msg = f"Vyčistený OKRES je prázdny pre '{okres_name_raw}' z {doc_url} (Kraj: {kraj_name})."
        log_status(status_global, "error", error_msg)
        return {"error": error_msg}

    # --- Extrakcia DOC_ID z URL ---
    # DOC_ID je názov súboru z URL bez prípony
    parsed_url = urlparse(doc_url)
    doc_id = os.path.splitext(os.path.basename(parsed_url.path))[0]
    if not doc_id:
        error_msg = f"Nepodarilo sa určiť DOC_ID pre {doc_url}."
        log_status(status_global, "error", error_msg)
        return {"error": error_msg}

    # --- Vytvorenie cesty pre dokument ---
    # Cesta: DOCS_DIR/KRAJ/OKRES/DOC_ID
    target_dir = os.path.join(base_docs_dir, kraj_name, okres_name, doc_id)
    try:
        os.makedirs(target_dir, exist_ok=True)
    except OSError as e:
        error_msg = f"Chyba pri vytváraní adresára {target_dir}: {e}."
        log_status(status_global, "error", error_msg)
        return {"error": error_msg}

    status_doc = os.path.join(target_dir, 'status.json')

    # Vymaž status.json na začiatku spracovania pre tento dokument
    if os.path.exists(status_doc):
        try:
            os.remove(status_doc)
        except OSError as e_remove:
            log_status(status_global, "error", f"DOC_ID({doc_id}): Nepodarilo sa odstrániť existujúci status súbor {status_doc}: {e_remove}")

    # --- Extrakcia a konverzia <main> obsahu na Markdown ---
    main_content_tag = soup.find('main')
    if not main_content_tag:
        error_msg = f"Tag <main> nebol nájdený v {doc_url}."
        log_status(status_doc, "error", error_msg)
        return {"error": error_msg}
    
    try:
        # Konvertujeme HTML obsah <main> tagu
        markdown_content = md_func(str(main_content_tag), heading_style='atx')
    except Exception as e:
        error_msg = f"Chyba pri konverzii hlavného obsahu na Markdown pre {doc_url}: {e}."
        log_status(status_doc, "error", error_msg)
        return {"error": error_msg}

    markdown_file_path = os.path.join(target_dir, "text.md")

    try:
        with open(markdown_file_path, 'w', encoding='utf-8') as f:
            f.write(markdown_content)
        print(f"  Úspešne uložené: {os.path.abspath(markdown_file_path)}")
    except IOError as e:
        error_msg = f"Chyba pri zápise Markdown súboru {markdown_file_path}: {e}"
        log_status(status_doc, "error", error_msg)
        return {"error": error_msg}
    
    analysis_filepath_txt = os.path.join(target_dir, "analysis.txt")

    try:
        analysis_result_str = analyze_text_document(doc_description + "\n\n" + markdown_content)
        if analysis_result_str:
            with open(analysis_filepath_txt, 'w', encoding='utf-8') as f:
                f.write(analysis_result_str)
            print(f"Analýza úspešne uložená do: {analysis_filepath_txt}")
        else:
            log_status(status_doc, "error", f"LLM analýza zlyhala alebo nevrátila obsah pre ID {doc_id}.")
            # analysis_result_str zostáva None
    except Exception as e:
        log_status(status_doc, "error", f"Chyba pri LLM analýze alebo ukladaní analysis.txt pre ID {doc_id}: {e}")
        # analysis_result_str zostáva None
    
    analysis_filepath_json = os.path.join(target_dir, "analysis.json")
    try:
        print(f"Generujem/aktualizujem {analysis_filepath_json}")
        analysis_result_data = json.loads(analysis_result_str)
        with open(analysis_filepath_json, 'w', encoding='utf-8') as f:
            json.dump(analysis_result_data, f, indent=2, ensure_ascii=False)
        print(f"Analýza úspešne uložená do: {analysis_filepath_json}")
    except json.JSONDecodeError as json_e:
        error_msg = f"LLM nevrátil platný JSON pre {target_dir}. Odpoveď: {analysis_result_str}. Chyba: {json_e}"
        log_status(status_doc, "error", error_msg)
        return (doc_id, {"error": error_msg})

    return {
        "kraj": kraj_name,
        "okres": okres_name,
        "doc_id": doc_id,
    }
    

def main():
    parser = argparse.ArgumentParser(
        description="Sťahuje HTML dokumenty z URL v JSON súbore, parsuje ich, "
                    "konvertuje hlavný obsah na Markdown a ukladá ich."
    )
    parser.add_argument(
        "--input",
        required=True,
        dest="json_file",
        help="Cesta k vstupnému JSON súboru s informáciami o dokumentoch."
    )
    parser.add_argument(
        "--docs-dir",
        required=True,
        dest="docs_dir",
        help="Základný adresár, kam sa budú ukladať Markdown dokumenty."
    )
    parser.add_argument(
        "--output",
        required=True,
        dest="output_json_file",
        help="Cesta k výstupnému JSON súboru, ktorý bude obsahovať obohatené dáta."
    )

    args = parser.parse_args()

    status_global = os.path.join(args.docs_dir, 'status.json')

    if not os.path.isfile(args.json_file):
        log_status(status_global, "error", f"Chyba: Vstupný JSON súbor '{args.json_file}' nebol nájdený.")
        return
    
    try:
        with open(args.json_file, 'r', encoding='utf-8') as f:
            documents_data = json.load(f)
    except json.JSONDecodeError:
        log_status(status_global, "error", f"Chyba: Nepodarilo sa dekódovať JSON zo súboru '{args.json_file}'. Skontrolujte validitu JSON.")
        return
    except Exception as e:
        log_status(status_global, "error", f"Chyba pri čítaní JSON súboru '{args.json_file}': {e}")
        return

    os.makedirs(args.docs_dir, exist_ok=True)
    
    if not isinstance(documents_data, list):
        log_status(status_global, "error", f"Chyba: Očakával sa JSON zoznam v '{args.json_file}', ale bol nájdený typ {type(documents_data)}.")
        return

    for item in documents_data:
        if not isinstance(item, dict):
            log_status(status_global, "error", f"  Preskakujem položku, ktorá nie je slovník (dictionary) v JSON: {item}")
            continue
            
        doc_url = item.get("url")
        doc_nazov = item.get("nazov", "N/A") # Pre informačné logovanie
        doc_description = item.get("popis") # Pre informačné logovanie

        if not doc_url:
            log_status(status_global, "error", f"  Preskakujem položku (nazov: {doc_nazov}) kvôli chýbajúcemu poľu 'url'.")
            continue
        
        processing_result = download_and_parse_document(doc_url, doc_description, args.docs_dir, status_global)

        if processing_result:
            item.update(processing_result)
        else:
            # This case should ideally not be reached if download_and_parse_document always returns a dict
            log_status(status_global, "error", "Neznáma chyba počas spracovania dokumentu (žiadny výsledok).")

    # Uloženie obohatených dát do výstupného JSON súboru
    try:
        with open(args.output_json_file, 'w', encoding='utf-8') as f_out:
            json.dump(documents_data, f_out, indent=2, ensure_ascii=False)
        print(f"\nObohatené dáta boli úspešne uložené do: {os.path.abspath(args.output_json_file)}")
    except IOError as e:
        log_status(status_global, "error", f"\nChyba pri zápise výstupného JSON súboru '{args.output_json_file}': {e}")

if __name__ == "__main__":
    main()