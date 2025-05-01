import json
import requests
import os
import urllib.parse
import sys
import glob # Import modulu glob

# Import funkcie na extrakciu textu z PDF
from pdf_to_txt import extract_text_from_pdf

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


def process_json_file(json_filepath):
    """
    Načíta JSON súbor, prejde jeho štruktúru a stiahne dokumenty.
    """
    try:
        with open(json_filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"Chyba: JSON súbor nenájdený na ceste: {json_filepath}", file=sys.stderr)
        return
    except json.JSONDecodeError:
        print(f"Chyba: Nepodarilo sa dekódovať JSON zo súboru: {json_filepath}. Skontrolujte formát.", file=sys.stderr)
        return

    if not isinstance(data, list):
        print(f"Chyba: Neočakávaná štruktúra JSON. Očakáva sa zoznam na najvyššej úrovni.", file=sys.stderr)
        return

    docs_dir = 'docs' # Definujeme výstupný adresár
    download_attempts = 0

    # Prejdite štruktúru JSON podľa poskytnutého vzoru
    for kraj_data in data:
        if isinstance(kraj_data, dict) and 'okresy' in kraj_data and isinstance(kraj_data['okresy'], list):
            for okres_data in kraj_data['okresy']:
                if isinstance(okres_data, dict) and 'dokumenty_zivotne_prostredie' in okres_data and isinstance(okres_data['dokumenty_zivotne_prostredie'], list):
                    for kategoria_data in okres_data['dokumenty_zivotne_prostredie']:
                        if isinstance(kategoria_data, dict) and 'dokumenty' in kategoria_data and isinstance(kategoria_data['dokumenty'], list):
                            for dokument_data in kategoria_data['dokumenty']:
                                if isinstance(dokument_data, dict) and 'url' in dokument_data and isinstance(dokument_data['url'], str):
                                    doc_url = dokument_data['url']

                                    # Parsuje URL a extrahuje parameter 'subor'
                                    parsed_url = urllib.parse.urlparse(doc_url)
                                    query_params = urllib.parse.parse_qs(parsed_url.query)

                                    doc_id = None
                                    if 'subor' in query_params and query_params['subor']:
                                         # parse_qs vracia zoznam hodnôt, vezmeme prvý prvok
                                         doc_id = query_params['subor'][0]

                                    if doc_id:
                                        existing_filepath = None

                                        # Skontroluj, či súbor s daným ID už existuje (s akoukoľvek príponou)
                                        # Vytvoríme vzor pre glob, ktorý hľadá súbory začínajúce na doc_id a s ľubovoľnou príponou
                                        output_dir = f"{docs_dir}/{kraj_data['kraj']}/{okres_data['nazov']}/{doc_id}"
                                        existing_files = glob.glob(f"{output_dir}/orig.*")
                                        changed = False
                                        orig_file = None
                                        if bool(existing_files): # Stiahnuť, ak zoznam existujúcich súborov je prázdny
                                            print(f"Súbor pre ID {doc_id} už existuje: {existing_files[0]}. Preskakujem sťahovanie.")
                                            orig_file = existing_files[0]
                                        else:
                                            download_attempts += 1 # Počítame pokus o stiahnutie
                                            orig_file = download_document(doc_url, output_dir, 'orig')
                                            changed = True

                                        # Ak bol súbor úspešne stiahnutý a je to PDF, extrahuj text
                                        # (aj keď .txt už existuje - podľa požiadavky)
                                        if orig_file and orig_file.endswith('.pdf'):
                                            txt_filepath = f"{output_dir}/text.txt"
                                            # Skontroluj, či textový súbor už existuje
                                            if changed or not os.path.exists(txt_filepath):
                                                print(f"Súbor {txt_filepath} neexistuje. Pokúšam sa extrahovať text z PDF: {orig_file}")
                                                try:
                                                    text = extract_text_from_pdf(orig_file)
                                                    with open(txt_filepath, 'w', encoding='utf-8') as txt_file:
                                                        txt_file.write(text)
                                                    print(f"Text úspešne extrahovaný a uložený do: {txt_filepath}")
                                                except Exception as e:
                                                    # Chybu pri extrakcii logujeme, ale pokračujeme ďalej
                                                    print(f"Chyba pri extrakcii textu z {orig_file}: {e}", file=sys.stderr)
                                            else:
                                                print(f"Súbor {txt_filepath} už existuje. Preskakujem extrakciu textu.")
                                                
                                        
                                    else:
                                        print(f"Upozornenie: Nepodarilo sa nájsť parameter 'subor' v URL: {doc_url}. Preskakujem.", file=sys.stderr)
                                else:
                                     print(f"Upozornenie: Chýba alebo má neplatný typ 'url' v zázname dokumentu: {dokument_data}. Preskakujem.", file=sys.stderr)
                        else:
                            print(f"Upozornenie: Neočakávaná štruktúra. 'dokumenty' chýba alebo nie je zoznam v kategórii: {kategoria_data}. Preskakujem.", file=sys.stderr)
                else:
                     print(f"Upozornenie: Neočakávaná štruktúra. 'dokumenty_zivotne_prostredie' chýba alebo nie je zoznam v okrese: {okres_data}. Preskakujem.", file=sys.stderr)
        else:
            print(f"Upozornenie: Neočakávaná štruktúra. 'okresy' chýba alebo nie je zoznam v kraji: {kraj_data}. Preskakujem.", file=sys.stderr)

    print(f"\nSpracovanie dokončené. Pokúsil som sa stiahnuť {download_attempts} nových dokumentov (pre ktoré bolo nájdené ID 'subor' a ešte neexistovali lokálne).")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Použitie: python vas_skript.py <cesta_k_json_suboru>")
        sys.exit(1)

    json_file_path = sys.argv[1]
    process_json_file(json_file_path)