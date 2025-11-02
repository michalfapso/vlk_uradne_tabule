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

# Importujeme ostatné zdieľané moduly
from log_handler import log_status
from get_doc_id import get_doc_id
from pdf_to_txt import extract_text_from_pdf
from llm_analyzer import analyze_text_document
from law_references import get_law_excerpts_for_text

PANDOC_FORMAT_MAPPINGS = [
    ('.docx', 'docx'), ('.doc', 'rtf'), ('.rtf', 'rtf'),
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
    }
    if content_type:
        main_type = content_type.split(';')[0].strip()
        return mime_to_suffix.get(main_type, '.bin')
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

def _convert_to_text(source_file_path: str) -> str:
    """
    Konvertuje súbor na text. V prípade chyby vyvolá RuntimeError.
    """
    if not os.path.exists(source_file_path):
        raise FileNotFoundError(f"Zdrojový súbor pre konverziu neexistuje: {source_file_path}")

    file_lower = source_file_path.lower()
    
    if file_lower.endswith('.pdf'):
        return extract_text_from_pdf(source_file_path)
    
    if file_lower.endswith('.txt'):
        with open(source_file_path, 'r', encoding='utf-8', errors='replace') as f:
            return f.read()

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

    raise RuntimeError(f"Nepodporovaný typ súboru pre konverziu na text: {source_file_path}")

def process_document(doc_data: dict, base_docs_dir: str) -> bool:
    doc_url = doc_data['url']
    source = doc_data['source']
    original_data = doc_data['original_data']

    doc_id = get_doc_id(doc_url)
    if not doc_id:
        log_status(os.path.join(base_docs_dir, 'status.json'), "error", f"Nepodarilo sa získať doc_id pre URL: {doc_url}")
        return False

    if source == 'minv':
        kraj = original_data.get('kraj', '_neznamy_kraj_')
        okres = original_data.get('okres', '_neznamy_okres_')
        output_dir = os.path.join(base_docs_dir, source, kraj, okres, doc_id)
    elif source == 'minzp':
        # TODO: Získať kraj a okres pre minzp z HTML stránky dokumentu
        kraj = original_data.get('kraj', '_neznamy_kraj_')
        okres = original_data.get('okres', '_neznamy_okres_')
        output_dir = os.path.join(base_docs_dir, source, kraj, okres, doc_id)
    else:
        log_status(os.path.join(base_docs_dir, 'status.json'), "error", f"Neznámy zdroj '{source}' pre URL: {doc_url}")
        return False

    try:
        os.makedirs(output_dir, exist_ok=True)
    except OSError as e:
        log_status(os.path.join(base_docs_dir, 'status.json'), "error", f"Chyba pri vytváraní adresára {output_dir}: {e}")
        return False
        
    status_filepath = os.path.join(output_dir, "status.json")
    if os.path.exists(status_filepath):
        os.remove(status_filepath)

    try:
        txt_filepath = os.path.join(output_dir, "text.txt")
        if not os.path.exists(txt_filepath) or os.path.getsize(txt_filepath) < 10:
            orig_file = download_document(doc_url, output_dir, 'orig')
            if not orig_file:
                raise RuntimeError("Stiahnutie zlyhalo.")
            
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
                            all_texts.append(f"--- Obsah súboru: {name} ---\n\n{_convert_to_text(file_path)}")
                        except Exception as e:
                            log_status(status_filepath, "warning", f"Nepodarilo sa konvertovať súbor '{name}' z archívu: {e}")
                text_content = "\n\n".join(all_texts)
            else:
                text_content = _convert_to_text(orig_file)

            text_content = text_content.strip()
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
        if not os.path.exists(laws_filepath) or os.path.getsize(laws_filepath) < 10:
            laws_excerpts = get_law_excerpts_for_text(text_content)
            if laws_excerpts:
                print(f'Saving laws to {laws_filepath}...')
                with open(laws_filepath, 'w', encoding='utf-8') as f:
                    f.write(laws_excerpts)
        else:
            print(f'Loading laws from {laws_filepath}...')
            with open(laws_filepath, 'r', encoding='utf-8') as f:
                laws_excerpts = f.read()
        laws_excerpts = "# Znenie častí zákonov odkazovaných v dokumente\n\n" + laws_excerpts


        analysis_json_filepath = os.path.join(output_dir, "analysis.json")
        if not os.path.exists(analysis_json_filepath) or os.path.getsize(analysis_json_filepath) < 10:
            print(f'Running LLM analysis...')
            analysis_input_text = text_content + "\n\n" + laws_excerpts
            analysis_result_str = analyze_text_document(analysis_input_text)
            if not analysis_result_str:
                raise RuntimeError("LLM analýza nevrátila žiadny výsledok.")

            analysis_txt_filepath = os.path.join(output_dir, "analysis.txt")
            print(f'Saving analysis to {analysis_txt_filepath}...')
            with open(analysis_txt_filepath, 'w', encoding='utf-8') as f:
                f.write(analysis_result_str)

            analysis_data = json.loads(analysis_result_str)
            print(f'Saving analysis to {analysis_json_filepath}...')
            with open(analysis_json_filepath, 'w', encoding='utf-8') as f:
                json.dump(analysis_data, f, indent=2, ensure_ascii=False)
        else:
            print(f'Loading from {analysis_json_filepath}...')
            with open(analysis_json_filepath, 'r', encoding='utf-8') as f:
                analysis_data = json.load(f)


        print(f"Dokument {doc_id} bol úspešne spracovaný.")
        return True

    except Exception as e:
        error_message = f"Zlyhalo spracovanie dokumentu {doc_id} ({doc_url}): {e}"
        print(error_message, file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        log_status(status_filepath, "error", error_message)
        try:
            with open(os.path.join(output_dir, 'status.json'), 'w', encoding='utf-8') as f:
                json.dump({"status": "error", "error_message": str(e)}, f, indent=2, ensure_ascii=False)
        except Exception as e_json:
            log_status(status_filepath, "error", f"Nepodarilo sa zapísať chybový stav do status.json: {e_json}")
        return False
