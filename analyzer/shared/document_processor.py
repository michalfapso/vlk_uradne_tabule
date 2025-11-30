# analyzer/shared/document_processor.py
import os
import sys
import json
import traceback
import requests
import glob
import shutil
import zipfile
import subprocess
import geopandas as gpd
import re
from bs4 import BeautifulSoup
from markdownify import markdownify as md_func # Alias to avoid conflict
import tempfile

# Importujeme ostatné zdieľané moduly
from log_handler import log_status
from get_doc_id import get_doc_id
from pdf_to_txt import extract_text_from_pdf
from llm_analyzer import analyze_text_document
from law_references import get_law_excerpts_for_text
from cadastral_parcels_ogc import get_geometry_of_a_parcel_set, gdf_save_to_file, gdf_load_from_file, get_intersections_with_protected_areas, get_geometry_of_a_geoname

PANDOC_FORMAT_MAPPINGS = [
    ('.docx', 'docx'), ('.rtf', 'rtf'), ('.odt', 'odt'),
    ('.pptx', 'pptx'), ('.ppt', 'ppt'), ('.xlsx', 'xlsx'), ('.xls', 'xls'),
]

def get_file_suffix(content_type):
    mime_to_suffix = {
        'application/pdf': '.pdf', 'application/msword': '.doc',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document': '.docx',
        'application/vnd.ms-excel': '.xls', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': '.xlsx',
        'text/plain': '.txt', 'application/xml': '.xml', 'application/json': '.json',
        'image/jpeg': '.jpg', 'image/png': '.png', 'image/gif': '.gif',
        'application/vnd.ms-powerpoint': '.ppt', 'application/vnd.openxmlformats-officedocument.presentationml.presentation': '.pptx',
        'application/rtf': '.rtf', 'text/csv': '.csv', 'application/zip': '.zip', 'application/vnd.rar': '.rar',
        'text/html': '.html',
    }
    if content_type:
        main_type = content_type.split(';')[0].strip()
        suffix = mime_to_suffix.get(main_type, None)
        if suffix:
            return suffix
        else:
            print(f'Unsupported content type: {content_type}, defaulting to .bin')
            return '.bin'
    print('Content type not provided, defaulting to .bin')
    return '.bin'

def download_document(doc_url, output_dir, output_filename_nosuffix):
    filepath = None
    try:
        print(f"Sťahujem dokument z: {doc_url}")
        response = requests.get(doc_url, stream=True, timeout=30)
        response.raise_for_status()
        content_type = response.headers.get('Content-Type')
        suffix = get_file_suffix(content_type)
        filename = f"{output_filename_nosuffix}{suffix}"
        filepath = os.path.join(output_dir, filename)
        os.makedirs(output_dir, exist_ok=True)
        with open(filepath, 'wb') as f:
            f.write(response.content)
        print(f"Úspešne stiahnuté a uložené ako: {filepath}")
        return filepath
    except requests.exceptions.RequestException as e:
        raise RuntimeError(f"Chyba pri sťahovaní URL {doc_url}: {e}") from e
    except IOError as e:
        raise RuntimeError(f"Chyba pri zápise súboru {filepath}: {e}") from e

def convert_doc_to_txt(input_doc_path, output_docx_path):
    command = [
        "libreoffice",
        "--headless",
        "--convert-to", "txt",
        "--outdir", os.path.dirname(output_docx_path),
        input_doc_path
    ]
    try:
        result = subprocess.run(command, check=True, capture_output=True, text=True)
        # print(f"Conversion successful: {result.stdout}")
        # print(f"Errors (if any): {result.stderr}")
    except subprocess.CalledProcessError as e:
        print(f"Error during conversion: {e}")
        print(f"Stdout: {e.stdout}")
        print(f"Stderr: {e.stderr}")
        raise

def _convert_to_text(source_file_path: str, source: str, status_filepath: str) -> str:
    """
    Konvertuje súbor na text. V prípade chyby vyvolá RuntimeError.
    """
    if not os.path.exists(source_file_path):
        raise FileNotFoundError(f"Zdrojový súbor pre konverziu neexistuje: {source_file_path}")

    file_lower = source_file_path.lower()
    
    if source == 'minzp' and (file_lower.endswith('.html') or file_lower.endswith('.htm')):
        with open(source_file_path, 'r', encoding='utf-8', errors='replace') as f:
            html_content = f.read()

            # --- Extrakcia a konverzia <main> obsahu na Markdown ---
            soup = BeautifulSoup(html_content, 'lxml')
            main_content_tag = soup.find('main')
            if not main_content_tag:
                error_msg = f"Tag <main> nebol nájdený v {source_file_path}."
                log_status(status_filepath, "error", error_msg)
                return {"error": error_msg}
            
            try:
                markdown_content = md_func(str(main_content_tag), heading_style='atx')
            except Exception as e:
                error_msg = f"Chyba pri konverzii hlavného obsahu na Markdown pre {source_file_path}: {e}."
                log_status(status_filepath, "error", error_msg)
                return {"error": error_msg}

            return markdown_content

    if file_lower.endswith('.pdf'):
        return extract_text_from_pdf(source_file_path)
    
    if file_lower.endswith('.txt'):
        with open(source_file_path, 'r', encoding='utf-8', errors='replace') as f:
            return f.read()

    if file_lower.endswith('.doc'):
        try:
            cmd = [ "libreoffice", "--headless", "--convert-to", "txt", "--outdir", os.path.dirname(source_file_path), source_file_path ]
            result = subprocess.run(cmd, check=True, capture_output=True, text=True, encoding='utf-8', errors='replace')
            print(f"LibreOffice conversion stdout: {result.stdout}")
            print(f"LibreOffice conversion stderr: {result.stderr}")
            target_file_path = source_file_path.replace('.doc', '.txt')
            with open(target_file_path, 'r', encoding='utf-8', errors='replace') as f:
                return f.read()
        except FileNotFoundError:
            raise RuntimeError("Príkaz 'libreoffice' nebol nájdený. Uistite sa, že je nainštalovaný.")
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"LibreOffice zlyhal s chybou: {e.stderr}")
        except Exception as e:
            raise RuntimeError(f"Chyba pri konverzii .doc na .txt: {e}")

    pandoc_format = next((fmt for ext, fmt in PANDOC_FORMAT_MAPPINGS if file_lower.endswith(ext)), None)
    if pandoc_format:
        try:
            cmd = ['pandoc', '-f', pandoc_format, '-t', 'plain', '--wrap=none', source_file_path]
            result = subprocess.run(cmd, check=True, capture_output=True, text=True, encoding='utf-8', errors='replace')
            return result.stdout
        except FileNotFoundError:
            raise RuntimeError("Príkaz 'pandoc' nebol nájdený. Uistite sa, že je nainštalovaný.")
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Pandoc zlyhal s chybou: {e.stderr}")
        except Exception as e:
            raise RuntimeError(f"Chyba pri konverzii {pandoc_format} na .txt: {e}")

    raise RuntimeError(f"Nepodporovaný typ súboru pre konverziu na text: {source_file_path}")

def sanitize_okres_name(name):
    if not name:
        return ""
    name = re.sub(r"^Okresný úrad\s+", "", name, flags=re.IGNORECASE)
    name = name.strip(" ")
    return name

def sanitize_kraj_name(name):
    if not name:
        return ""
    if name == "Ministerstvo":
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

def _get_minzp_kraj_okres(html_content: str, doc_url: str, status_global_path: str):
    soup = BeautifulSoup(html_content, 'lxml')
    breadcrumb_div = soup.find('div', class_='breadcrumb')
    kraj_name_raw = None
    okres_name_raw = None

    if breadcrumb_div:
        breadcrumb_links = breadcrumb_div.find_all('a')
        if len(breadcrumb_links) > 2:
            text_at_idx2 = breadcrumb_links[2].get_text(strip=True)
            if text_at_idx2.startswith("Kraj ") or text_at_idx2 == "Ministerstvo":
                kraj_name_raw = text_at_idx2
        
        if len(breadcrumb_links) > 3:
            text_at_idx3 = breadcrumb_links[3].get_text(strip=True)
            if text_at_idx3.startswith("Okresný úrad "):
                okres_name_raw = text_at_idx3
    
    if not kraj_name_raw:
        error_msg = f"KRAJ nebol nájdený alebo nemá očakávaný formát v breadcrumbs pre {doc_url}."
        log_status(status_global_path, "error", error_msg)
        return None, None
    
    if kraj_name_raw != "Ministerstvo" and not okres_name_raw:
        error_msg = f"OKRES nebol nájdený alebo nemá očakávaný formát v breadcrumbs pre {doc_url} (Kraj: {kraj_name_raw})."
        log_status(status_global_path, "error", error_msg)
        return None, None

    kraj_name = sanitize_kraj_name(kraj_name_raw)
    okres_name = sanitize_okres_name(okres_name_raw)
    if kraj_name == "Ministerstvo":
        okres_name = "Ministerstvo"

    if not kraj_name:
        error_msg = f"Vyčistený KRAJ je prázdny pre '{kraj_name_raw}' z {doc_url}."
        log_status(status_global_path, "error", error_msg)
        return None, None
    if not okres_name:
        error_msg = f"Vyčistený OKRES je prázdny pre '{okres_name_raw}' z {doc_url} (Kraj: {kraj_name})."
        log_status(status_global_path, "error", error_msg)
        return None, None
        
    return kraj_name, okres_name

def process_document(doc_data: dict, base_docs_dir: str) -> bool:
    doc_url = doc_data['url']
    source = doc_data['source']
    original_data = doc_data['original_data']

    doc_id = get_doc_id(doc_url)
    if not doc_id:
        log_status(os.path.join(base_docs_dir, 'status.json'), "error", f"Nepodarilo sa získať doc_id pre URL: {doc_url}")
        return False

    kraj = original_data.get('kraj')
    okres = original_data.get('okres')
    downloaded_content = None
    response_headers = None

    output_dir_tmp = None
    orig_file_tmp = None
    if source == 'minzp':
        # Parsing kraj and okres from html document for minzp.sk documents
        # use temp_dir, and when done:
        output_dir_tmp = tempfile.TemporaryDirectory()
        print('output_dir_tmp:', output_dir_tmp.name)
        orig_file_tmp = download_document(doc_url, output_dir_tmp.name, 'orig')
        assert orig_file_tmp.lower().endswith(('.html', '.htm'))
        try:
            with open(orig_file_tmp, 'r', encoding='utf-8', errors='replace') as f:
                html_text = f.read()
            
            status_global_path = os.path.join(base_docs_dir, 'status.json')
            kraj, okres = _get_minzp_kraj_okres(html_text, doc_url, status_global_path)
            if not kraj or not okres:
                return False
        except requests.exceptions.RequestException as e:
            log_status(os.path.join(base_docs_dir, 'status.json'), "error", f"Chyba pri sťahovaní HTML pre {doc_url}: {e}")
            return False

    if not kraj:
        kraj = '_neznamy_kraj_'
    if not okres:
        okres = '_neznamy_okres_'

    output_dir = os.path.join(base_docs_dir, source, kraj, okres, doc_id)

    try:
        os.makedirs(output_dir, exist_ok=True)
    except OSError as e:
        log_status(os.path.join(base_docs_dir, 'status.json'), "error", f"Chyba pri vytváraní adresára {output_dir}: {e}")
        return False

    if output_dir_tmp:
        os.replace(orig_file_tmp, os.path.join(output_dir, os.path.basename(orig_file_tmp)))
        output_dir_tmp.cleanup()
    
    status_filepath = os.path.join(output_dir, "status.json")
    if os.path.exists(status_filepath):
        os.remove(status_filepath)

    try:
        invalidate_files = False

        txt_filepath = os.path.join(output_dir, "text.txt")
        if invalidate_files or not os.path.exists(txt_filepath) or os.path.getsize(txt_filepath) < 10:
            invalidate_files = True
            # Search for an existing original file
            existing_orig_files = glob.glob(os.path.join(output_dir, 'orig.*'))
            if existing_orig_files:
                orig_file = existing_orig_files[0]
                print(f"Orig doc already downloaded: {orig_file}")
            else:
                orig_file = download_document(doc_url, output_dir, 'orig')

            if not orig_file:
                raise RuntimeError("Stiahnutie zlyhalo.")
            
            # Converting document to text
            if orig_file.lower().endswith('.zip'):
                extracted_dir = os.path.join(output_dir, "extracted")
                if os.path.exists(extracted_dir):
                    shutil.rmtree(extracted_dir)
                os.makedirs(extracted_dir)
                with zipfile.ZipFile(orig_file, 'r') as zip_ref:
                    zip_ref.extractall(extracted_dir)
                
                all_texts = []
                for root, _, files in os.walk(extracted_dir):
                    for name in files:
                        try:
                            file_path = os.path.join(root, name)
                            all_texts.append(f"--- Obsah súboru: {name} ---\n\n{_convert_to_text(file_path, source, status_filepath)}")
                        except Exception as e:
                            log_status(status_filepath, "warning", f"Nepodarilo sa konvertovať súbor '{name}' z archívu: {e}")
                text_content = "\n\n".join(all_texts)
            else:
                text_content = _convert_to_text(orig_file, source, status_filepath)

            text_content = text_content.strip()
            
            if source == 'minzp':
                # Dokumenty z minzp.sk majú okrem dokumentu aj popis, tak ho pridáme na začiatok
                text_content = f"{original_data.get('popis', '')}\n\n{text_content}"

            text_content = f"Kraj: {kraj}\nOkres: {okres}\n\n{text_content}"

            if not text_content:
                raise RuntimeError("Extrakcia textu vrátila prázdny obsah.")
        
            print(f'Saving text doc to {txt_filepath}...')
            with open(txt_filepath, 'w', encoding='utf-8') as f:
                f.write(text_content)
        else:
            print(f'Loading text doc from {txt_filepath}...')
            with open(txt_filepath, 'r', encoding='utf-8') as f:
                text_content = f.read()


        laws_filepath = os.path.join(output_dir, "laws.txt")
        laws_excerpts = ''
        if invalidate_files or not os.path.exists(laws_filepath) or os.path.getsize(laws_filepath) < 10:
            invalidate_files = True
            try:
                laws_excerpts = get_law_excerpts_for_text(text_content)
                if laws_excerpts:
                    print(f'Saving laws to {laws_filepath}...')
                    with open(laws_filepath, 'w', encoding='utf-8') as f:
                        f.write(laws_excerpts)
            except Exception as e:
                traceback.print_exc(file=sys.stderr)
                log_status(status_filepath, "warning", f"Nepodarilo sa získať znenia zákonov pre dokument: {e}")
                laws_excerpts = ""
        else:
            print(f'Loading laws from {laws_filepath}...')
            with open(laws_filepath, 'r', encoding='utf-8') as f:
                laws_excerpts = f.read()
        laws_excerpts = "# Znenie častí zákonov odkazovaných v dokumente\n\n" + laws_excerpts


        analysis_json_filepath = os.path.join(output_dir, "analysis.json")
        if invalidate_files or not os.path.exists(analysis_json_filepath) or os.path.getsize(analysis_json_filepath) < 10:
            invalidate_files = True
            analysis_input_text = text_content + "\n\n" + laws_excerpts
            analysis_data = None
            analysis_result_str = None

            for attempt in range(3):
                print(f"Pokus o LLM analýzu {attempt + 1}/3...")
                try:
                    analysis_result_str = analyze_text_document(analysis_input_text)
                    if not analysis_result_str:
                        print("LLM analýza vrátila prázdny výsledok.")
                        continue
                    analysis_data = json.loads(analysis_result_str)
                    print("LLM analýza úspešná, získaný platný JSON.")
                    break  # Úspech, vyskočíme z cyklu
                except json.JSONDecodeError as e:
                    print(f"Pokus {attempt + 1} zlyhal: LLM nevrátil platný JSON. Chyba: {e}")
                    analysis_data = None  # Resetujeme v prípade chyby

            if analysis_data is None:
                raise RuntimeError("LLM analýza zlyhala po 3 pokusoch alebo nevrátila platný JSON.")

            analysis_txt_filepath = os.path.join(output_dir, "analysis.txt")
            print(f'Saving analysis to {analysis_txt_filepath}...')
            with open(analysis_txt_filepath, 'w', encoding='utf-8') as f:
                f.write(analysis_result_str)
            print(f'Saving analysis to {analysis_json_filepath}...')
            with open(analysis_json_filepath, 'w', encoding='utf-8') as f:
                json.dump(analysis_data, f, indent=2, ensure_ascii=False)
        else:
            print(f'Loading from {analysis_json_filepath}...')
            with open(analysis_json_filepath, 'r', encoding='utf-8') as f:
                analysis_data = json.load(f)


        def process_analysis_data(analysis_data, status_filepath, invalidate_files):
            # Return analysis_data when modified, else None
            gis_filepath = os.path.join(output_dir, "gis.geojson")
            if invalidate_files or not os.path.exists(gis_filepath) or os.path.getsize(gis_filepath) < 10:
                invalidate_files = True
                print(f'Getting geometry of parcel set...')
                # print('analysis_data:', analysis_data)
                place_info = analysis_data.get('miesto_realizacie', {})
                print(f'place_info:{place_info}')
                gdf_parcelset = None
                if len(place_info.get('katastralne_uzemia', [])) > 0:
                    gdf_parcelset = get_geometry_of_a_parcel_set(place_info, status_filepath) 

                gdf_geoname = None
                nazov_lokality = place_info.get('nazov_lokality', '')
                print('nazov_lokality:', nazov_lokality)
                if nazov_lokality:
                    gdf_geoname = get_geometry_of_a_geoname(nazov_lokality, place_info.get('obec', ''), place_info.get('okres', ''), place_info.get('kraj', ''), status_filepath)
                    print('gdf_geoname:', gdf_geoname)

                print('gdf_parcelset:', gdf_parcelset)
                print('gdf_geoname:', gdf_geoname)
                gdf = None
                if gdf_parcelset is not None and not gdf_parcelset.empty and gdf_geoname is not None and not gdf_geoname.empty:
                    gdf = gdf_parcelset.overlay(gdf_geoname, how='intersection')
                elif gdf_parcelset is not None and not gdf_parcelset.empty:
                    gdf = gdf_parcelset
                elif gdf_geoname is not None and not gdf_geoname.empty:
                    gdf = gdf_geoname
                else:
                    log_status(status_filepath, "warning", "Nepodarilo sa získať geometriu parcel set alebo geoname")
                    return None
                print(f'Saving geometry to {gis_filepath}...')
                gdf_save_to_file(gdf, gis_filepath)
            else:
                print(f'Loading geometry from {gis_filepath}...')
                gdf = gdf_load_from_file(gis_filepath)

            if invalidate_files or 'zasiahnute_chranene_uzemia' not in analysis_data:
                invalidate_files = True
                print('Intersections with protected areas...')
                intersections = get_intersections_with_protected_areas(gdf, status_filepath)
                print('intersections:', intersections)
                analysis_data['zasiahnute_chranene_uzemia'] = intersections
                return analysis_data
            else:
                print('Intersections with protected areas already computed. Skipping...')

            return None
        
        analysis_data_changed = False
        if isinstance(analysis_data, dict):
            analysis_data = process_analysis_data(analysis_data, status_filepath, invalidate_files)
            analysis_data_changed = analysis_data is not None
        elif isinstance(analysis_data, list):
            for i, item in enumerate(analysis_data):
                updated_item = process_analysis_data(item, status_filepath, invalidate_files)
                if updated_item is not None:
                    analysis_data[i] = updated_item
                    analysis_data_changed = True

        if analysis_data_changed:
            invalidate_files = True
            print(f'Updating analysis JSON at {analysis_json_filepath}...')
            with open(analysis_json_filepath, 'w', encoding='utf-8') as f:
                json.dump(analysis_data, f, indent=2, ensure_ascii=False)

        print(f"Dokument {doc_id} bol úspešne spracovaný.")
        return True

    except Exception as e:
        error_message = f"Zlyhalo spracovanie dokumentu {doc_id} ({doc_url}): {e}"
        print(error_message, file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        log_status(status_filepath, "error", error_message)
        return False
