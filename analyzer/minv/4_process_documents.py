import json
import requests
import os
import sys
import glob
import traceback
import argparse
import hashlib
import zipfile
import shutil
import subprocess
from datetime import datetime

# Adjust sys.path to include scripts in the parent directory
script_dir = os.path.dirname(os.path.abspath(__file__))
analyzer_dir = os.path.dirname(script_dir) # parent directory of the current script
sys.path.insert(0, analyzer_dir)

from pdf_to_txt import extract_text_from_pdf
from get_doc_id import get_doc_id
from analyze_text_document import analyze_text_document
from log_status import log_status

def get_file_suffix(content_type):
    """
    Určí príponu súboru na základe hlavičky Content-Type.
    Vracia '.bin' ako predvolenú hodnotu, ak typ nie je rozpoznaný alebo chýba.
    """
    # Jednoduché mapovanie bežných MIME typov na prípony
    mime_to_suffix = {
        'application/pdf': '.pdf',
        'application/msword': '.doc',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document': '.docx',
        'application/vnd.ms-excel': '.xls',
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': '.xlsx',
        'text/plain': '.txt',
        'application/xml': '.xml',
        'application/json': '.json',
        'image/jpeg': '.jpg',
        'image/png': '.png',
        'image/gif': '.gif',
        'application/vnd.ms-powerpoint': '.ppt',
        'application/vnd.openxmlformats-officedocument.presentationml.presentation': '.pptx',
        'application/rtf': '.rtf',
        'text/csv': '.csv',
        'application/zip': '.zip',
        'application/vnd.rar': '.rar',
        # Podľa potreby môžete pridať ďalšie typy
    }

    if content_type:
        # Rozdelí typ (napr. 'application/pdf; charset=utf-8') a vezme prvú časť
        main_type = content_type.split(';')[0].strip()
        return mime_to_suffix.get(main_type, '.bin') # Predvolená hodnota '.bin'
    return '.bin' # Predvolená hodnota, ak hlavička Content-Type chýba

def download_document(doc_url, output_dir, output_filename_nosuffix):
    """
    Stiahne dokument z danej URL a uloží ho do súboru docs/ID.SUFFIX.
    """
    filepath = None
    try:
        print(f"Pokúšam sa stiahnuť dokument z: {doc_url}")

        # Použitie stream=True je dobré pre veľké súbory, ale tu to nemusí byť nutné
        # Pridaný timeout, aby sa predišlo nekonečnému čakaniu
        response = requests.get(doc_url, stream=True, timeout=30)
        response.raise_for_status() # Vyvolá HTTPError pre chybové status kódy (4xx alebo 5xx)

        content_type = response.headers.get('Content-Type')
        suffix = get_file_suffix(content_type)

        filename = f"{output_filename_nosuffix}{suffix}"
        filepath = os.path.join(output_dir, filename)

        # Vytvorenie výstupného adresára, ak neexistuje
        os.makedirs(output_dir, exist_ok=True)

        # Uloženie obsahu súboru v binárnom režime
        with open(filepath, 'wb') as f:
            # requests.get().content obsahuje celý obsah súboru v pamäti
            f.write(response.content)

        print(f"Úspešne stiahnuté a uložené ako: {filepath}")
        return filepath

    except requests.exceptions.RequestException as e:
        error_message = f"Chyba pri sťahovaní URL {doc_url}: {e}"
        raise type(e)(error_message) from e
    except IOError as e:
        # filepath je inicializovaný na None. Ak chyba nastane pred jeho priradením,
        # správa to reflektuje. Inak obsahuje cestu k súboru.
        error_message = f"Chyba pri zápise súboru {filepath if filepath else 'NEZNÁMY (nedefinovaný pred IO chybou)'}: {e}"
        raise type(e)(error_message) from e
    except Exception as e: # Zachytí akékoľvek iné neočakávané chyby
        error_message = f"Vyskytla sa neočakávaná chyba pre URL {doc_url}: {e}"
        raise type(e)(error_message) from e


# List of Pandoc-supported file suffixes and their corresponding Pandoc input formats.
# This mapping is used in the _convert_to_text function.
PANDOC_FORMAT_MAPPINGS = [
    # (File Suffix, Pandoc Input Format, Optional Notes)
    ('.docx', 'docx'),
    ('.doc', 'rtf'),  # Using 'rtf' for .doc as Pandoc often handles it well this way
    ('.rtf', 'rtf'),
    ('.pptx', 'pptx'),
    ('.ppt', 'ppt'),   # Note: Pandoc's direct .ppt to text conversion might be limited
    ('.xlsx', 'xlsx'), # Note: Pandoc's direct .xlsx to text conversion might be limited
    ('.xls', 'xls'),   # Note: Pandoc's direct .xls to text conversion might be limited
]

def _convert_to_text(source_file_path: str, output_text_filepath: str) -> bool:
    """
    Konvertuje jeden súbor (PDF, DOC, DOCX, RTF, PPT, PPTX, XLS, XLSX, TXT) na textový obsah.
    Výsledný text je uložený priamo do súboru `output_text_filepath`.
    Vracia True v prípade úspechu, False v prípade neúspechu.
    """
    try:
        if not os.path.exists(source_file_path):
            raise FileNotFoundError(f"Zdrojový súbor pre konverziu do textu neexistuje: {source_file_path}")

        print(f"Pokúšam sa konvertovať súbor na text: {source_file_path}")
        file_lower = source_file_path.lower()

        if file_lower.endswith('.pdf'):
            text_content = extract_text_from_pdf(source_file_path)
            if text_content is not None:
                with open(output_text_filepath, 'w', encoding='utf-8') as f_out:
                    f_out.write(text_content)
                return True
            else:
                raise RuntimeError(f"Extrakcia textu z PDF {source_file_path} zlyhala alebo vrátila None.")
        
        if file_lower.endswith('.txt'):
            try:
                with open(source_file_path, 'r', encoding='utf-8', errors='replace') as f_in, \
                     open(output_text_filepath, 'w', encoding='utf-8') as f_out:
                    f_out.write(f_in.read())
                return True
            except Exception as e_txt:
                raise RuntimeError(f"Chyba pri kopírovaní TXT súboru {source_file_path} do {output_text_filepath}: {e_txt}")

        # Try Pandoc conversion for other supported formats defined in PANDOC_FORMAT_MAPPINGS
        pandoc_input_format = None
        for ext, fmt in PANDOC_FORMAT_MAPPINGS:
            if file_lower.endswith(ext):
                pandoc_input_format = fmt
                break
        
        if pandoc_input_format:
            # Výstupný adresár pre output_text_filepath by mal byť už vytvorený volajúcim
            cmd = ['pandoc', '-f', pandoc_input_format, '-t', 'markdown', '--wrap=none', '-o', output_text_filepath, source_file_path]
            print(f"Spúšťam pandoc: {' '.join(cmd)}")
            result = subprocess.run(cmd, check=True, capture_output=True, text=True, encoding='utf-8', errors='replace')
            
            if os.path.exists(output_text_filepath) and os.path.getsize(output_text_filepath) > 0:
                return True # Úspešne konvertované a uložené
            else:
                error_msg = f"Pandoc síce bežal, ale nevytvoril súbor {output_text_filepath} alebo je prázdny pre {source_file_path}."
                if result.stderr: error_msg += f"\nPandoc stderr: {result.stderr}"
                if os.path.exists(output_text_filepath): # Odstrániť prázdny/neúspešný súbor
                    try:
                        os.remove(output_text_filepath)
                    except OSError as e_rm:
                        error_msg += f"\nNepodarilo sa odstrániť neúspešný výstupný súbor {output_text_filepath}: {e_rm}"
                raise RuntimeError(error_msg)
        
        # If not PDF, TXT, or any Pandoc-supported format from the list
        raise RuntimeError(f"Nepodporovaný typ súboru pre priamu konverziu na text: {source_file_path}")
    except FileNotFoundError: # Špecificky pre pandoc
        raise RuntimeError(f"Príkaz 'pandoc' nebol nájdený. Uistite sa, že je pandoc nainštalovaný a v systémovej PATH.")
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Chyba pri konverzii súboru {source_file_path} pomocou pandoc: {e}\nStdout: {e.stdout}\nStderr: {e.stderr}")
    except Exception as e:
        traceback.print_exc(file=sys.stderr)
        raise RuntimeError(f"Neočakávaná chyba pri konverzii súboru {source_file_path} na text: {e}")

def process_document(kraj: str, okres: str, doc_url: str, docs_dir: str, skip_analysis: bool = False) -> tuple[str | None, dict | None, bool]:
    """
    Spracuje jeden dokument: stiahne, extrahuje text, analyzuje.
    Vracia tuple (doc_id, výsledok_analýzy_alebo_chyba, bol_pokus_o_stiahnutie_suboru).
    """
    doc_id = get_doc_id(doc_url)

    if doc_id is None:
        error_msg = f"Nepodarilo sa získať doc_id pre URL: {doc_url}"
        # Log to kraj/okres status file as doc_id is not available for its own directory
        status_filepath_ko = os.path.join(docs_dir, kraj, okres, "status.json")
        log_status(status_filepath_ko, "error", error_msg)
        # Vrátime None pre doc_id, chybovú hlášku a False pre pokus o stiahnutie
        return (None, {"error": error_msg}, False)

    output_dir = os.path.abspath(os.path.join(docs_dir, kraj, okres, doc_id)) # Použitie absolútnej cesty
    os.makedirs(output_dir, exist_ok=True) # Vytvorenie adresára tu, aby existoval pre všetky súbory

    status_filepath = os.path.join(output_dir, "status.json")

    # Delete status.json at the beginning of processing for this document
    if os.path.exists(status_filepath):
        try:
            os.remove(status_filepath)
        except OSError as e_remove:
            # This is a meta-error, print to stderr directly and it won't be in this doc's status.json
            # (or we could try to log it, but it might fail if the issue is perms)
            log_status(os.path.abspath(os.path.join(docs_dir, kraj, okres, 'status.json')), "error", f"DOC_ID({doc_id}): Nepodarilo sa odstrániť existujúci status súbor {status_filepath}: {e_remove}")

    try:
        #--------------------------------------------------
        # Download
        existing_files = glob.glob(os.path.join(output_dir, "orig.*"))
        changed = False
        orig_file = None

        if not existing_files or (existing_files and os.path.getsize(existing_files[0]) < 10):
            orig_file = download_document(doc_url, output_dir, 'orig')
            if orig_file:
                changed = True
            else:
                # Stiahnutie zlyhalo
                error_msg = f"Download failed for doc_id {doc_id} from {doc_url}"
                log_status(status_filepath, "error", error_msg)
                return (doc_id, {"error": error_msg})
        else:
            print(f"Súbor pre ID {doc_id} už existuje: {existing_files[0]}. Preskakujem sťahovanie.")
            orig_file = existing_files[0]
        
        #--------------------------------------------------
        # Convert to text
        txt_filepath = os.path.join(output_dir, "text.txt")
        text_extraction_successful = False
        text_content_for_analysis = "" 
        text_was_reextracted_this_run = False

        if changed or not os.path.exists(txt_filepath) or os.path.getsize(txt_filepath) < 10:
            print(f"Potrebná (re)extrakcia textu pre {doc_id} (orig_changed={changed}, text_path={txt_filepath}).")
            if orig_file.lower().endswith(('.zip', '.rar')): # Spracovanie archívov
                extracted_dir = os.path.join(output_dir, "extracted")
                if os.path.exists(extracted_dir): # Vždy vyčistiť a re-extrahovať, ak je potrebná extrakcia textu
                    print(f"Čistím predchádzajúci extrahovaný adresár: {extracted_dir}")
                    shutil.rmtree(extracted_dir)
                os.makedirs(extracted_dir, exist_ok=True)

                extracted_files_paths_to_process = []
                if orig_file.lower().endswith('.zip'):
                    try:
                        with zipfile.ZipFile(orig_file, 'r') as zip_ref:
                            zip_ref.extractall(extracted_dir) # Extrahuje so zachovaním štruktúry adresárov
                        print(f"Úspešne extrahovaný ZIP archív {orig_file} do {extracted_dir}")
                        # Prejdi extrahované súbory
                        for root, _, files in os.walk(extracted_dir):
                            for f_name in files:
                                # Ignoruj súbory v našich špeciálnych adresároch (napr. _pandoc_temp)
                                if "_pandoc_temp" not in root:
                                     extracted_files_paths_to_process.append(os.path.join(root, f_name))
                    except zipfile.BadZipFile:
                        log_status(status_filepath, "error", f"Chyba: Poškodený ZIP súbor {orig_file}")
                    except Exception as e_zip:
                        log_status(status_filepath, "error", f"Chyba pri spracovaní ZIP súboru {orig_file}: {e_zip}")
                
                elif orig_file.lower().endswith('.rar'):
                    log_status(status_filepath, "warning", f"Spracovanie RAR súborov ({orig_file}) zatiaľ nie je implementované. Vyžaduje knižnicu 'rarfile' alebo 'patool' a príkaz 'unrar'.")
                    # Pokračujeme, akoby sa nepodarilo extrahovať text z archívu

                all_extracted_texts_content = []
                # temp_conversion_output_dir už nie je potrebný pre _convert_to_text

                for item_path in extracted_files_paths_to_process:
                    if os.path.isfile(item_path):
                        sub_filename_base, _ = os.path.splitext(os.path.basename(item_path))
                        # Adresár pre text.txt konkrétneho extrahovaného súboru
                        sub_item_text_output_dir = os.path.join(extracted_dir, sub_filename_base)
                        os.makedirs(sub_item_text_output_dir, exist_ok=True)
                        
                        sub_item_txt_filepath = os.path.join(sub_item_text_output_dir, "text.txt")
                        conversion_ok = _convert_to_text(item_path, sub_item_txt_filepath)
                        
                        if conversion_ok:
                            with open(sub_item_txt_filepath, 'r', encoding='utf-8') as f_sub_in:
                                item_text_content_from_file = f_sub_in.read()
                            all_extracted_texts_content.append(item_text_content_from_file)
                            print(f"Text extrahovaný z {os.path.basename(item_path)} do {sub_item_txt_filepath}")
                        else:
                            log_status(status_filepath, "error", f"Nepodarilo sa extrahovať text z {os.path.basename(item_path)}.")
                
                if all_extracted_texts_content:
                    # Spojenie textov z jednotlivých súborov v archíve do hlavného text.txt
                    # (Ak by sme chceli zachovať iba odkazy na jednotlivé text.txt súbory, logika by bola iná)
                    final_concatenated_text = "\n\n--- Nový Súbor v Archíve ---\n\n".join(all_extracted_texts_content)
                    with open(txt_filepath, 'w', encoding='utf-8') as main_txt_file:
                        main_txt_file.write(final_concatenated_text)
                    text_extraction_successful = True
                    text_was_reextracted_this_run = True
                    print(f"Všetky texty z archívu {orig_file} spojené do {txt_filepath}")
                else:
                    log_status(status_filepath, "warning", f"Archív {orig_file} spracovaný, ale nepodarilo sa extrahovať žiadny textový obsah z jeho súborov.")
                    if os.path.exists(txt_filepath): os.remove(txt_filepath) # Zaistiť, aby neostal starý/prázdny súbor

            else: # Nie je archív, priama konverzia
                conversion_ok = _convert_to_text(orig_file, txt_filepath)

                if conversion_ok:
                    # _convert_to_text už uložil súbor do txt_filepath
                    text_extraction_successful = True
                    text_was_reextracted_this_run = True
                    print(f"Text úspešne extrahovaný z {orig_file} a uložený do: {txt_filepath}")
                else:
                    log_status(status_filepath, "error", f"Extrakcia textu z {orig_file} nebola vykonaná alebo zlyhala.")
                    if os.path.exists(txt_filepath): os.remove(txt_filepath)
        else:
            print(f"Súbor {txt_filepath} už existuje a je aktuálny. Preskakujem extrakciu textu.")
            if os.path.exists(txt_filepath) and os.path.getsize(txt_filepath) > 0:
                 text_extraction_successful = True
            else:
                 log_status(status_filepath, "warning", f"Textový súbor {txt_filepath} mal existovať, ale neexistuje alebo je prázdny.")
                 text_extraction_successful = False
            # text_was_reextracted_this_run zostáva False

        if skip_analysis:
            print(f"Preskakujem analýzu pre ID {doc_id} (--skip-analysis).")
            log_status(status_filepath, "info", f"Analýza preskočená pre ID {doc_id} (--skip-analysis).")
            return (doc_id, None) # Vráti None pre analýzu

        # Načítanie text_content_for_analysis z finálneho txt_filepath
        if text_extraction_successful and os.path.exists(txt_filepath) and os.path.getsize(txt_filepath) > 0:
            try:
                with open(txt_filepath, 'r', encoding='utf-8') as f_final_txt:
                    text_content_for_analysis = f_final_txt.read()
            except Exception as e:
                log_status(status_filepath, "error", f"Chyba pri čítaní finálneho textového súboru {txt_filepath}: {e}")
                text_extraction_successful = False # Označiť ako neúspešné, ak sa nedá prečítať
        
        if not text_extraction_successful or not text_content_for_analysis.strip():
            error_msg = f"Nie je dostupný žiadny textový obsah pre analýzu pre ID {doc_id} v {txt_filepath} (extraction_successful={text_extraction_successful}). Preskakujem analýzu."
            log_status(status_filepath, "error", error_msg)
            return (doc_id, {"error": error_msg})

        #--------------------------------------------------
        # Analyze with AI
        analysis_filepath_txt = os.path.join(output_dir, "analysis.txt")
        analysis_result_str = None

        needs_ai_analysis_run = text_was_reextracted_this_run or \
                                not os.path.exists(analysis_filepath_txt) or \
                                os.path.getsize(analysis_filepath_txt) < 10

        if needs_ai_analysis_run:
            print(f"Spúšťam AI analýzu pre {doc_id} (text_reextracted={text_was_reextracted_this_run}, analysis_path={analysis_filepath_txt})")
            try:
                analysis_result_str = analyze_text_document(text_content_for_analysis)
                if analysis_result_str:
                    with open(analysis_filepath_txt, 'w', encoding='utf-8') as f:
                        f.write(analysis_result_str)
                    print(f"Analýza úspešne uložená do: {analysis_filepath_txt}")
                else:
                    log_status(status_filepath, "error", f"LLM analýza zlyhala alebo nevrátila obsah pre ID {doc_id}.")
                    # analysis_result_str zostáva None
            except Exception as e:
                log_status(status_filepath, "error", f"Chyba pri LLM analýze alebo ukladaní analysis.txt pre ID {doc_id}: {e}")
                # analysis_result_str zostáva None
        else:
            print(f"Súbor {analysis_filepath_txt} už existuje a je aktuálny. Preskakujem AI analýzu, načítavam existujúci.")
            # Načítaj existujúci analysis.txt, ak sme ho teraz negenerovali
            if os.path.exists(analysis_filepath_txt):
                try:
                    with open(analysis_filepath_txt, 'r', encoding='utf-8') as f:
                        analysis_result_str = f.read()
                except Exception as e:
                    log_status(status_filepath, "error", f"Chyba pri čítaní existujúceho {analysis_filepath_txt}: {e}")

        if not analysis_result_str:
            error_msg = f"Výsledok analýzy (analysis.txt) nie je dostupný pre ID {doc_id}."
            log_status(status_filepath, "error", error_msg)
            return (doc_id, {"error": error_msg})

        analysis_filepath_json = os.path.join(output_dir, "analysis.json")
        # Generuj/aktualizuj JSON, ak bol text analýzy (re)generovaný alebo ak JSON chýba/je malý,
        # alebo ak 'needs_ai_analysis_run' signalizuje potrebu aktualizácie.
        if needs_ai_analysis_run or not os.path.exists(analysis_filepath_json) or os.path.getsize(analysis_filepath_json) < 10:
            try:
                print(f"Generujem/aktualizujem {analysis_filepath_json}")
                analysis_result_data = json.loads(analysis_result_str)
                with open(analysis_filepath_json, 'w', encoding='utf-8') as f:
                    json.dump(analysis_result_data, f, indent=2, ensure_ascii=False)
                print(f"Analýza úspešne uložená do: {analysis_filepath_json}")
            except json.JSONDecodeError as json_e:
                error_msg = f"LLM nevrátil platný JSON pre {output_dir}. Odpoveď: {analysis_result_str}. Chyba: {json_e}"
                log_status(status_filepath, "error", error_msg)
                return (doc_id, {"error": error_msg})
        else:
            print(f"Súbor {analysis_filepath_json} už existuje a je aktuálny. Preskakujem konverziu do JSONu.")

        # Načítanie JSON analýzy a pridanie do dokumentu
        if os.path.exists(analysis_filepath_json):
            try:
                with open(analysis_filepath_json, 'r', encoding='utf-8') as f_analysis:
                    analysis_data = json.load(f_analysis)
                    return (doc_id, analysis_data)
            except json.JSONDecodeError as e:
                error_msg = f"Chyba pri načítaní JSON analýzy zo súboru {analysis_filepath_json}: {e}"
                log_status(status_filepath, "error", error_msg)
                return (doc_id, {"error": error_msg})
        
        final_error_msg = f"Analysis JSON ({analysis_filepath_json}) not found or not created for doc_id {doc_id}"
        log_status(status_filepath, "error", final_error_msg)
        return (doc_id, {"error": final_error_msg})
    except Exception as e:
        error_msg = f"Neočekávaná chyba v process_document pre doc_id {doc_id}, URL {doc_url}: {e}"
        # status_filepath by mal byť definovaný, ak sme sa dostali za doc_id check
        log_status(status_filepath, "error", error_msg)
        traceback.print_exc(file=sys.stderr)
        return (doc_id, {"error": error_msg})

def process_json_file(json_filepath_in, json_filepath_out, docs_dir, skip_analysis=False):
    """
    Načíta JSON súbor, prejde jeho štruktúru a stiahne dokumenty.
    """
    try:
        with open(json_filepath_in, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        err_msg = f"Chyba: JSON súbor nenájdený na ceste: {json_filepath_in}"
        # Log to general status file in docs_dir
        log_status(os.path.join(docs_dir, "status.json"), "critical", err_msg)
        return
    except json.JSONDecodeError:
        err_msg = f"Chyba: Nepodarilo sa dekódovať JSON zo súboru: {json_filepath_in}. Skontrolujte formát."
        # Log to general status file in docs_dir
        log_status(os.path.join(docs_dir, "status.json"), "critical", err_msg)
        return

    if not isinstance(data, list):
        err_msg = f"Chyba: Neočakávaná štruktúra JSON v súbore {json_filepath_in}. Očakáva sa zoznam na najvyššej úrovni."
        # Log to general status file in docs_dir
        log_status(os.path.join(docs_dir, "status.json"), "error", err_msg)
        return
    
    # Prejdite štruktúru JSON podľa poskytnutého vzoru
    for kraj_data in data:
        if isinstance(kraj_data, dict) and 'okresy' in kraj_data and isinstance(kraj_data['okresy'], list):
            for okres_data in kraj_data['okresy']:
                if isinstance(okres_data, dict) and 'dokumenty_zivotne_prostredie' in okres_data and isinstance(okres_data['dokumenty_zivotne_prostredie'], list):
                    for kategoria_data in okres_data['dokumenty_zivotne_prostredie']:
                        if isinstance(kategoria_data, dict) and 'dokumenty' in kategoria_data and isinstance(kategoria_data['dokumenty'], list):
                            for dokument_data in kategoria_data['dokumenty']:
                                if isinstance(dokument_data, dict) and 'url' in dokument_data:
                                    doc_url = dokument_data['url']
                                    if not isinstance(doc_url, str) or not doc_url.strip():
                                        err_msg = f"Upozornenie: Neplatná alebo prázdna URL v dokumente: {dokument_data} (Kraj: {kraj_data.get('kraj')}, Okres: {okres_data.get('nazov')}). Preskakujem."
                                        status_filepath_ko = os.path.join(docs_dir, kraj_data.get('kraj', '_unknown_kraj_'), okres_data.get('nazov', '_unknown_okres_'), "status.json")
                                        log_status(status_filepath_ko, "warning", err_msg)
                                        dokument_data['doc_id'] = None
                                        dokument_data['analyza'] = {"error": "Invalid or empty URL"}
                                        continue

                                    doc_id, analysis_result = process_document(
                                        kraj_data['kraj'], okres_data['nazov'], doc_url, docs_dir, skip_analysis
                                    )
                                    dokument_data['doc_id'] = doc_id
                                    dokument_data['analyza'] = analysis_result
                                else:
                                    err_msg = f"Upozornenie: Chýba alebo má neplatný typ 'url' v zázname dokumentu: {dokument_data} (Kraj: {kraj_data.get('kraj')}, Okres: {okres_data.get('nazov')}). Preskakujem."
                                    status_filepath_ko = os.path.join(docs_dir, kraj_data.get('kraj', '_unknown_kraj_'), okres_data.get('nazov', '_unknown_okres_'), "status.json")
                                    log_status(status_filepath_ko, "warning", err_msg)
                        else:
                            err_msg = f"Upozornenie: Neočakávaná štruktúra. 'dokumenty' chýba alebo nie je zoznam v kategórii: {kategoria_data} (Kraj: {kraj_data.get('kraj')}, Okres: {okres_data.get('nazov')}). Preskakujem."
                            status_filepath_ko = os.path.join(docs_dir, kraj_data.get('kraj', '_unknown_kraj_'), okres_data.get('nazov', '_unknown_okres_'), "status.json")
                            log_status(status_filepath_ko, "warning", err_msg)
                else:
                    err_msg = f"Upozornenie: Neočakávaná štruktúra. 'dokumenty_zivotne_prostredie' chýba alebo nie je zoznam v okrese: {okres_data} (Kraj: {kraj_data.get('kraj')}). Preskakujem."
                    # Okres nie je spolahlivo znamy, logujeme do status.json pre kraj, ak je znamy, inak do generalneho
                    status_filepath_general_kraj = os.path.join(docs_dir, kraj_data.get('kraj', '_unknown_kraj_'), "status.json")
                    log_status(status_filepath_general_kraj, "warning", err_msg) # Ak kraj nie je znamy, cesta bude docs_dir/_unknown_kraj_/status.json
        else:
            err_msg = f"Upozornenie: Neočakávaná štruktúra. 'okresy' chýba alebo nie je zoznam v kraji: {kraj_data}. Preskakujem."
            # Kraj ani okres nie su zname, logujeme do generalneho status.json
            log_status(os.path.join(docs_dir, "status.json"), "warning", err_msg)

    print(f"\nSpracovanie dokončené.")

    # Výpis výsledného JSON na štandardný výstup
    if json_filepath_out:
        try:
            print(f"Ukladám výstupný JSON s analýzami do súboru: {json_filepath_out}")
            with open(json_filepath_out, 'w', encoding='utf-8') as f_out:
                json.dump(data, f_out, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Nastala chyba pri ukladaní výstupného JSON súboru {json_filepath_out}: {e}", file=sys.stderr)


if __name__ == "__main__":
    # TEST:
    # print(f"Spúšťam test")
    # doc_id, analysis = process_document(
    #     'Banskobystrický kraj',
    #     'Banská Bystrica',
    #     'https://www.minv.sk/?okresne-urady-klientske-centra&urad=39&odbor=10&sekcia=uradna-tabula&subor=540792',
    #     # 'https://www.minv.sk/?okresne-urady-klientske-centra&urad=51&odbor=10&sekcia=uradna-tabula&subor=540951', # zip
    #     '../data/minv/docs_test',
    #     skip_analysis=False # Alebo True, ak chces testovat len stahovanie/extrakciu
    # )
    # print(f"Test - Returned DOC_ID: {doc_id}, Result: {analysis}")
    # exit(0)

    parser = argparse.ArgumentParser(description="Spracuje JSON súbor s dokumentmi, stiahne ich, extrahuje text a voliteľne analyzuje.")
    parser.add_argument('--input', required=True, help='Cesta k vstupnému JSON súboru.')
    parser.add_argument('--output', required=False, help='Cesta k výstupnému JSON súboru.')
    parser.add_argument('--docs-dir', required=True, help='Adresár pre ukladanie stiahnutých dokumentov, ich textových verzií a analýz.')
    parser.add_argument("--skip-analysis", action="store_true", help="Preskočí krok analýzy dokumentov pomocou LLM.")

    args = parser.parse_args()

    process_json_file(args.input, args.output, args.docs_dir, args.skip_analysis)
    
