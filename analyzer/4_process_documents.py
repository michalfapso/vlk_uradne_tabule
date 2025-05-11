import json
import requests
import os
import sys
import glob
import litellm
import traceback
import argparse # Pridaný import pre argparse
import hashlib # Pridaný import pre hashovanie
import zipfile # Pridaný import pre prácu so ZIP súbormi
import shutil # Pridaný import pre operácie so súborovým systémom (napr. rmtree)
import subprocess # Pridaný import pre volanie externých príkazov

# Import funkcie na extrakciu textu z PDF
from pdf_to_txt import extract_text_from_pdf
from get_doc_id import get_doc_id

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
        print(f"Chyba pri sťahovaní URL {doc_url}: {e}", file=sys.stderr)
    except IOError as e:
        print(f"Chyba pri zápise súboru {filepath}: {e}", file=sys.stderr)
    except Exception as e: # Zachytí akékoľvek iné neočakávané chyby
        print(f"Vyskytla sa neočakávaná chyba pre URL {doc_url}: {e}", file=sys.stderr)

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
            print(f"Zdrojový súbor pre konverziu neexistuje: {source_file_path}", file=sys.stderr)
            return None

        print(f"Pokúšam sa konvertovať súbor na text: {source_file_path}")
        file_lower = source_file_path.lower()

        if file_lower.endswith('.pdf'):
            text_content = extract_text_from_pdf(source_file_path)
            if text_content is not None:
                with open(output_text_filepath, 'w', encoding='utf-8') as f_out:
                    f_out.write(text_content)
                return True
            else:
                print(f"Extrakcia textu z PDF {source_file_path} zlyhala alebo vrátila None.", file=sys.stderr)
                return False
        
        if file_lower.endswith('.txt'):
            try:
                with open(source_file_path, 'r', encoding='utf-8', errors='replace') as f_in, \
                     open(output_text_filepath, 'w', encoding='utf-8') as f_out:
                    f_out.write(f_in.read())
                return True
            except Exception as e_txt:
                print(f"Chyba pri kopírovaní TXT súboru {source_file_path} do {output_text_filepath}: {e_txt}", file=sys.stderr)
                return False
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
                print(f"Chyba: Pandoc síce bežal, ale nevytvoril súbor {output_text_filepath} alebo je prázdny pre {source_file_path}.", file=sys.stderr)
                if result.stderr: print(f"Pandoc stderr: {result.stderr}", file=sys.stderr)
                if os.path.exists(output_text_filepath): # Odstrániť prázdny/neúspešný súbor
                    try:
                        os.remove(output_text_filepath)
                    except OSError as e_rm:
                        print(f"Nepodarilo sa odstrániť neúspešný výstupný súbor {output_text_filepath}: {e_rm}", file=sys.stderr)
                return False
        
        # If not PDF, TXT, or any Pandoc-supported format from the list
        print(f"Nepodporovaný typ súboru pre priamu konverziu na text: {source_file_path}", file=sys.stderr)
        return False
    except FileNotFoundError: # Špecificky pre pandoc
        print(f"Chyba: Príkaz 'pandoc' nebol nájdený. Uistite sa, že je pandoc nainštalovaný a v systémovej PATH.", file=sys.stderr)
        return False
    except subprocess.CalledProcessError as e:
        print(f"Chyba pri konverzii súboru {source_file_path} pomocou pandoc: {e}\nStdout: {e.stdout}\nStderr: {e.stderr}", file=sys.stderr)
        return False
    except Exception as e:
        print(f"Neočakávaná chyba pri konverzii súboru {source_file_path} na text: {e}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        return False

def analyze(text_content: str):
    """
    Analyzuje textový obsah pomocou LLM (cez litellm) a uloží výsledok ako JSON.
    """
    print(f"Spúšťam analýzu textu cez LLM")
    prompt = """
Analyzuj text dokumentu z úradnej tabule okresného úradu životného prostredia, ktorý bol skonvertovaný z PDF do textu. Tvojou úlohou je extrahovať kľúčové informácie do štruktúrovaného formátu JSON. Tento JSON má pomôcť rýchlo identifikovať dokumenty relevantné pre organizáciu Lesoochranárske zoskupenie VLK (LZ VLK).

Vráť *len* JSON s nasledujúcou štruktúrou. Neuvádzaj žiadny iný text pred ani po JSON objekte.

```json
{
  "cislo_konania_spisu": "...",
  "cislo_rozhodnutia": "...",
  "datum_dokumentu": "...",
  "datum_zverejnenia": "...",
  "lehoty_na_vyjadrenie": "...",
  "ziadatel_navrhovatel": "...",
  "miesto_realizacie": {
    "kraj": "...",
    "okres": "...",
    "obec": "...",
    "katastralne_uzemia": [
      {
        "nazov": "...",
        "parcely": [
          {
            "typ": "...",
            "cisla": ["..."]
          }
        ]
      }
    ],
    "nazov_lokality": "..."
  },
  "typ_dokumentu": "...",
  "typ_zasahu": ["..."],
  "typ_uzemia": ["..."],
  "je_v_chranenom_uzemi": null,
  "dotknute_zivocichy_rastliny": ["..."],
  "odkaz_enviroportal": "...",
  "zhrnutie": "..."
}
```

**Popis polí:**

*   `cislo_konania_spisu`: Oficiálne číslo konania alebo spisu (napr. začínajúce na OU-...).
*   `cislo_rozhodnutia`: Oficiálne číslo konkrétneho rozhodnutia (ak je dokumentom rozhodnutie a má špecifické číslo odlišné od čísla spisu).
*   `datum_dokumentu`: Dátum vystavenia alebo odoslania dokumentu. Formát preferuj YYYY-MM-DD, ak je možné presne určiť, inak použi textovú formu z dokumentu.
*   `datum_zverejnenia`: Dátum, kedy bol dokument vyvesený/zverejnený na úradnej tabuli/webe (často označené "Vyvesené dňa:", "Zverejnené dňa:", "Začiatok zverejnenia:"). Formát preferuj YYYY-MM-DD.
*   `lehoty_na_vyjadrenie`: Explicitne uvedená lehota, dokedy môže verejnosť alebo účastníci konania podať vyjadrenie, námietky alebo potvrdiť záujem byť účastníkom. Uveď presné znenie z dokumentu (napr. "do 10 dní od zverejnenia", "najneskôr pri ústnom pojednávaní dňa 14.02.2023"). Ak je viac lehot pre rôzne typy vyjadrení, zameraj sa na lehotu pre verejnosť/účastníkov na prvé vyjadrenie/vstup do konania. Ak lehota nie je špecifikovaná (napr. len zmienka o ústnom pojednávaní bez explicitnej lehoty pre vyjadrenia vopred), uveď "Neuvedené". Ak dokument výslovne uvádza, že účasť nie je možná, uveď túto informáciu (napr. "Nie je možné sa prihlásiť do konania").
*   `ziadatel_navrhovatel`: Meno alebo plný obchodný názov subjektu, ktorý žiadosť podal alebo navrhovanej činnosti/stavby. Ak je uvedených viac žiadateľov, uveď hlavného (napr. obec pri obecných stavbách). Ak je uvedený žiadateľ aj zastúpenie, uveď žiadateľa. Ak je uvedený len subjekt, ktorý oznamuje výrub/činnosť, uveď ten (napr. ŽSR, SVP, SPP).
*   `miesto_realizacie`:
    *   `kraj`: Názov kraja, ak je uvedený.
    *   `okres`: Názov okresu, ak je uvedený.
    *   `obec`: Názov obce/mesta, kde sa činnosť realizuje.
    *   `katastralne_uzemia`: Zoznam dotknutých katastrálnych území. Ak nie sú uvedené, ponechaj prázdny zoznam `[]`.
        *   `nazov`: Názov katastrálneho územia
        *   `parcely`: Zoznam dotknutých parciel. Ak nie sú uvedené, ponechaj prázdny zoznam `[]`.
            *   `typ`: typ parciel (C-KN, E-KN).
            *   `cisla`: parcelné čísla.
    *   `nazov_lokality`: Špecifický názov lokality (napr. "Obytná zóna Hviezdoslavova", "BIO resort Šachtičky", "Martinský les"), ak je uvedený.
*   `typ_dokumentu`: Klasifikácia dokumentu (napr. "Oznámenie o začatí konania", "Rozhodnutie zo zisťovacieho konania", "Kolaudačné rozhodnutie", "Stavebné povolenie", "Oznámenie o výrube", "Informácia pre verejnosť", "Žiadosť", "Strategický dokument", "Verejná vyhláška", "Upovedomenie o predĺžení lehoty", "Výzva"). Identifikuj hlavný účel dokumentu.
*   `typ_zasahu`: Zoznam typov navrhovanej činnosti alebo zásahov do životného prostredia. Zameraj sa na kľúčové záujmy LZ VLK. Použi konkrétne termíny z dokumentu, ak sú relevantné (napr. "výrub drevín", "vysekávanie krovia", "ťažba dreva", "odstrel alebo iné usmrcovanie živočíchov", "používanie chemických látok", "výstavba budovy", "výstavba cesty", "výstavba oplotenia", "výstavba energetického diela", "výstavba vodnej stavby", "výstavba kanalizácie", "výstavba vodovodu", "výstavba čistiarne odpadových vôd", "úprava vodného toku", "odber podzemných vôd", "vypúšťanie odpadových vôd", "vsakovanie vôd"). Ak si nie si istý, o aký typ zásahu ide, daj do toho poľa iba "neviem".
*   `typ_uzemia`: Zoznam explicitne spomenutých typov alebo názvov chránených území (napr. "Národný park", "CHKO", "Prírodná rezervácia", "Chránený areál", "Územie európskeho významu", "NATURA 2000", "SKUEV", "SKCHVU", "CHVO", "ochranné pásmo vodárenského zdroja"). Ak je v dokumente číslo stupňa ochrany (napr. "4. stupeň", "5. stupeň"), pridaj to tiež do "typ_uzemia". Ak je v dokumente napísané, že sa netýka chráneného územia, daj tam "nechránené". Ak sa v dokumente nespomína, či ide o chránené územie, daj tam "neviem". Ak sa netýka žiadneho územia, ponechaj prázdny zoznam `[]`.
*   `je_v_chranenom_uzemi`: Booleovská hodnota: `true`, ak je v dokumente explicitne spomenuté akékoľvek chránené územie (vrátane ochranných pásiem alebo CHVO) alebo stupeň ochrany > 0; `false`, ak nie je spomenuté nič o chránených územiach ani stupňoch ochrany. Ak informácia chýba, uveď `null`.
*   `dotknute_zivocichy_rastliny`: Zoznam explicitne spomenutých chránených, ohrozených alebo inak významných živočíchov alebo rastlín, prípadne skupiny (napr. "bobor vodný", "vydra riečna", "ichtyofauna", "bentická fauna", "brehové porasty"). Ak nie sú uvedené, ponechaj prázdny zoznam `[]`.
*   `odkaz_enviroportal`: URL adresa na enviroportal.sk, ak je v dokumente uvedená.
*   `zhrnutie`: Stručné a výstižné zhrnutie dokumentu (max 2-3 vety) s dôrazom na typ zásahu, miesto (obec, lokalita) a spomenuté chránené územia/druhy, ak sú relevantné pre záujmy LZ VLK.

**Pokyny pre model:**

*   Extrahuj informácie iba z poskytnutého textu dokumentu. Nepridávaj externé znalosti o lokalitách (či sú v chránených územiach, ak to dokument explicitne neuvádza), okrem extrakcie explicitných názvov chránených území alebo stupňov ochrany, ak sú v texte.
*   Vyplň JSON presne podľa definovanej štruktúry.
*   Pre polia s textovou hodnotou, ak informácia chýba, použij `null`.
*   Pre polia so zoznamom hodnôt, ak žiadne položky nie sú nájdené, použi prázdny zoznam `[]`.
*   Pre booleovské pole `je_v_chranenom_uzemi` postupuj podľa popisu vyššie.
*   Zaisti, aby výstup bol validný JSON a neobsahoval nič iné.

Text dokumentu:
""" + text_content
    
    try:
        # Použi litellm na volanie LLM (napr. gpt-4o-mini alebo iný model)
        # Uisti sa, že máš nastavené API kľúče ako environmentálne premenné
        response = litellm.completion(
            model="gemini/gemini-2.5-flash-preview-04-17", # Alebo iný model podľa tvojho výberu a dostupnosti
            messages=[{"role": "user", "content": prompt}],
            response_format={ "type": "json_object" }, # Požiadame o JSON výstup
            # reasoning_effort="medium"
        )

        # Extrahuj obsah odpovede (mal by to byť JSON string)
        analysis_result_str = response.choices[0].message.content
        return analysis_result_str

    except Exception as e:
        print(f"Chyba počas LLM analýzy: {e}", file=sys.stderr)
        print(traceback.format_exc(), file=sys.stderr) # Vypíš detail chyby

def process_document(kraj: str, okres: str, doc_url: str, docs_dir: str, skip_analysis: bool = False) -> tuple[str | None, dict | None, bool]:
    """
    Spracuje jeden dokument: stiahne, extrahuje text, analyzuje.
    Vracia tuple (doc_id, výsledok_analýzy_alebo_chyba, bol_pokus_o_stiahnutie_suboru).
    """
    doc_id = get_doc_id(doc_url)

    if doc_id is None:
        error_msg = f"Nepodarilo sa získať doc_id pre URL: {doc_url}"
        print(error_msg, file=sys.stderr)
        # Vrátime None pre doc_id, chybovú hlášku a False pre pokus o stiahnutie
        return (None, {"error": error_msg}, False)
    
    output_dir = os.path.abspath(os.path.join(docs_dir, kraj, okres, doc_id)) # Použitie absolútnej cesty
    os.makedirs(output_dir, exist_ok=True) # Vytvorenie adresára tu, aby existoval pre všetky súbory

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
                return (doc_id, {"error": f"Download failed for doc_id {doc_id} from {doc_url}"}) # Oprava: vrátiť tuple
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
                        print(f"Chyba: Poškodený ZIP súbor {orig_file}", file=sys.stderr)
                    except Exception as e_zip:
                        print(f"Chyba pri spracovaní ZIP súboru {orig_file}: {e_zip}", file=sys.stderr)
                
                elif orig_file.lower().endswith('.rar'):
                    print(f"Spracovanie RAR súborov ({orig_file}) zatiaľ nie je implementované. Vyžaduje knižnicu 'rarfile' alebo 'patool' a príkaz 'unrar'.", file=sys.stderr)
                    # Tu by bola logika pre RAR, napr. s patoolib

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
                            print(f"Nepodarilo sa extrahovať text z {os.path.basename(item_path)}.", file=sys.stderr)
                
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
                    print(f"Archív {orig_file} spracovaný, ale nepodarilo sa extrahovať žiadny textový obsah z jeho súborov.", file=sys.stderr)
                    if os.path.exists(txt_filepath): os.remove(txt_filepath) # Zaistiť, aby neostal starý/prázdny súbor

            else: # Nie je archív, priama konverzia
                conversion_ok = _convert_to_text(orig_file, txt_filepath)

                if conversion_ok:
                    # _convert_to_text už uložil súbor do txt_filepath
                    text_extraction_successful = True
                    text_was_reextracted_this_run = True
                    print(f"Text úspešne extrahovaný z {orig_file} a uložený do: {txt_filepath}")
                else:
                    print(f"Extrakcia textu z {orig_file} nebola vykonaná alebo zlyhala.", file=sys.stderr)
                    if os.path.exists(txt_filepath): os.remove(txt_filepath)
        else:
            print(f"Súbor {txt_filepath} už existuje a je aktuálny. Preskakujem extrakciu textu.")
            if os.path.exists(txt_filepath) and os.path.getsize(txt_filepath) > 0:
                 text_extraction_successful = True
            else:
                 print(f"Upozornenie: Textový súbor {txt_filepath} mal existovať, ale neexistuje alebo je prázdny.", file=sys.stderr)
                 text_extraction_successful = False
            # text_was_reextracted_this_run zostáva False

        if skip_analysis:
            print(f"Preskakujem analýzu pre ID {doc_id} (--skip-analysis).")
            return (doc_id, None) # Vráti None pre analýzu

        # Načítanie text_content_for_analysis z finálneho txt_filepath
        if text_extraction_successful and os.path.exists(txt_filepath) and os.path.getsize(txt_filepath) > 0:
            try:
                with open(txt_filepath, 'r', encoding='utf-8') as f_final_txt:
                    text_content_for_analysis = f_final_txt.read()
            except Exception as e:
                print(f"Chyba pri čítaní finálneho textového súboru {txt_filepath}: {e}", file=sys.stderr)
                text_extraction_successful = False # Označiť ako neúspešné, ak sa nedá prečítať
        
        if not text_extraction_successful or not text_content_for_analysis.strip():
            msg = f"Nie je dostupný žiadny textový obsah pre analýzu pre ID {doc_id} v {txt_filepath} (extraction_successful={text_extraction_successful}). Preskakujem analýzu."
            print(msg, file=sys.stderr)
            return (doc_id, {"error": msg})

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
                analysis_result_str = analyze(text_content_for_analysis)
                if analysis_result_str:
                    with open(analysis_filepath_txt, 'w', encoding='utf-8') as f:
                        f.write(analysis_result_str)
                    print(f"Analýza úspešne uložená do: {analysis_filepath_txt}")
                else:
                    print(f"LLM analýza zlyhala alebo nevrátila obsah pre ID {doc_id}.", file=sys.stderr)
                    # analysis_result_str zostáva None
            except Exception as e:
                print(f"Chyba pri LLM analýze alebo ukladaní analysis.txt pre ID {doc_id}: {e}", file=sys.stderr)
                # analysis_result_str zostáva None
        else:
            print(f"Súbor {analysis_filepath_txt} už existuje a je aktuálny. Preskakujem AI analýzu, načítavam existujúci.")
            # Načítaj existujúci analysis.txt, ak sme ho teraz negenerovali
            if os.path.exists(analysis_filepath_txt):
                try:
                    with open(analysis_filepath_txt, 'r', encoding='utf-8') as f:
                        analysis_result_str = f.read()
                except Exception as e:
                    print(f"Chyba pri čítaní existujúceho {analysis_filepath_txt}: {e}", file=sys.stderr)

        if not analysis_result_str:
            msg = f"Výsledok analýzy (analysis.txt) nie je dostupný pre ID {doc_id}."
            print(msg, file=sys.stderr)
            return (doc_id, {"error": msg})

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
                print(f"Chyba: LLM nevrátil platný JSON pre {output_dir}. Odpoveď: {analysis_result_str}. Chyba: {json_e}", file=sys.stderr)
                return (doc_id, {"error": f"LLM did not return valid JSON for doc_id {doc_id}: {json_e}"})
        else:
            print(f"Súbor {analysis_filepath_json} už existuje a je aktuálny. Preskakujem konverziu do JSONu.")

        # Načítanie JSON analýzy a pridanie do dokumentu
        if os.path.exists(analysis_filepath_json):
            try:
                with open(analysis_filepath_json, 'r', encoding='utf-8') as f_analysis:
                    analysis_data = json.load(f_analysis)
                    return (doc_id, analysis_data)
            except json.JSONDecodeError as e:
                print(f"Chyba pri načítaní JSON analýzy zo súboru {analysis_filepath_json}: {e}", file=sys.stderr)
                return (doc_id, {"error": f"Failed to load analysis JSON for doc_id {doc_id}: {e}"})
        
        return (doc_id, {"error": f"Analysis JSON ({analysis_filepath_json}) not found or not created for doc_id {doc_id}"}) # Ak sa nedostaneme k vráteniu analýzy
    except Exception as e:
        print(f"Neočekávaná chyba v process_document pre doc_id {doc_id}, URL {doc_url}: {e}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        return (doc_id, {"error": f"Unexpected error processing doc_id {doc_id}: {str(e)}"})

def process_json_file(json_filepath_in, json_filepath_out, docs_dir, skip_analysis=False):
    """
    Načíta JSON súbor, prejde jeho štruktúru a stiahne dokumenty.
    """
    try:
        with open(json_filepath_in, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"Chyba: JSON súbor nenájdený na ceste: {json_filepath_in}", file=sys.stderr)
        return
    except json.JSONDecodeError:
        print(f"Chyba: Nepodarilo sa dekódovať JSON zo súboru: {json_filepath_in}. Skontrolujte formát.", file=sys.stderr)
        return

    if not isinstance(data, list):
        print(f"Chyba: Neočakávaná štruktúra JSON. Očakáva sa zoznam na najvyššej úrovni.", file=sys.stderr)
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
                                        print(f"Upozornenie: Neplatná alebo prázdna URL v dokumente: {dokument_data}. Preskakujem.", file=sys.stderr)
                                        dokument_data['doc_id'] = None
                                        dokument_data['analyza'] = {"error": "Invalid or empty URL"}
                                        continue

                                    doc_id, analysis_result = process_document(
                                        kraj_data['kraj'], okres_data['nazov'], doc_url, docs_dir, skip_analysis
                                    )
                                    dokument_data['doc_id'] = doc_id
                                    dokument_data['analyza'] = analysis_result
                                else:
                                    print(f"Upozornenie: Chýba alebo má neplatný typ 'url' v zázname dokumentu: {dokument_data}. Preskakujem.", file=sys.stderr)
                        else:
                            print(f"Upozornenie: Neočakávaná štruktúra. 'dokumenty' chýba alebo nie je zoznam v kategórii: {kategoria_data}. Preskakujem.", file=sys.stderr)
                else:
                    print(f"Upozornenie: Neočakávaná štruktúra. 'dokumenty_zivotne_prostredie' chýba alebo nie je zoznam v okrese: {okres_data}. Preskakujem.", file=sys.stderr)
        else:
            print(f"Upozornenie: Neočakávaná štruktúra. 'okresy' chýba alebo nie je zoznam v kraji: {kraj_data}. Preskakujem.", file=sys.stderr)

    print(f"\nSpracovanie dokončené.")

    # Výpis výsledného JSON na štandardný výstup
    try:
        print("Ukladám výstupný JSON s analýzami")
        # print(json.dumps(data, indent=2, ensure_ascii=False))
        json.dump(data, open(json_filepath_out, 'w', encoding='utf-8'), indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"Nastala chyba pri generovaní výstupného JSON: {e}", file=sys.stderr)


if __name__ == "__main__":
    # TEST:
    # print(f"Spúšťam test")
    # doc_id, analysis = process_document(
    #     'Banskobystrický kraj',
    #     'Banská Bystrica',
    #     # 'https://www.minv.sk/?okresne-urady-klientske-centra&urad=39&odbor=10&sekcia=uradna-tabula&subor=540792',
    #     'https://www.minv.sk/?okresne-urady-klientske-centra&urad=51&odbor=10&sekcia=uradna-tabula&subor=540951', # zip
    #     '../data/docs_test',
    #     skip_analysis=False # Alebo True, ak chces testovat len stahovanie/extrakciu
    # )
    # print(f"Test - Returned DOC_ID: {doc_id}, Result: {analysis}")
    # exit(0)

    parser = argparse.ArgumentParser(description="Spracuje JSON súbor s dokumentmi, stiahne ich, extrahuje text a voliteľne analyzuje.")
    parser.add_argument('--input', required=True, help='Cesta k vstupnému JSON súboru.')
    parser.add_argument('--output', required=True, help='Cesta k výstupnému JSON súboru.')
    parser.add_argument('--docs-dir', required=True, help='Adresár pre ukladanie stiahnutých dokumentov a ich textových verzií.')
    parser.add_argument("--skip-analysis", action="store_true", help="Preskočí krok analýzy dokumentov pomocou LLM.")

    args = parser.parse_args()

    process_json_file(args.input, args.output, args.docs_dir, args.skip_analysis)
    
