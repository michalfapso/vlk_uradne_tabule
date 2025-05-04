import json
import requests
import os
import urllib.parse
import sys
import glob
import litellm
import traceback
import argparse # Pridaný import pre argparse
import subprocess # Pridaný import pre volanie externých príkazov

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



def analyze(text_content):
    """
    Analyzuje textový obsah pomocou LLM (cez litellm) a uloží výsledok ako JSON.
    """

    print(f"Spúšťam analýzu textu cez LLM")

#     prompt = f"""Analyzuj tento dokument z nástenky okresného úradu životného prostredia, ktorý bol skonvertovaný z PDF do textu. Vráť len JSON s nasledujúcou štruktúrou:
# ```json
# {{
#   "typ_zasahu": [...],
#   "typ_uzemia": "..."
#   "zhrnutie": "..."
# }}
# ```

# Zisti, či sa dokument týka nejakého zásahu ("výrub", "odstrel", "chémia", "stavba", "cesta", ...) a zdetekované typy zásahov zapíš do poľa "typ_zasahu", môžeš do toho poľa zapísať viacero hodnôt, ak treba. Ak si nie si istý, o aký typ zásahu ide, daj do toho poľa iba "neviem".

# Ak sa dokument týka nejakého chráneného územia, do "typ_uzemia" daj "chránené". Ak ale vieš, o aký typ chráneného územia konkrétne ide (CHKO, národný park, prírodná rezervácia, ...) alebo vieš číslo stupňa ochrany (napr. "5. stupeň"), zapíš do "typ_uzemia" takýto konkrétnejší údaj. Ak sa netýka chráneného územia, daj tam "nechránené". Ak sa v dokumente nespomína, či ide o chránené územie, daj tam "neviem". Ak sa netýka žiadneho územia, nechaj tam prázdny reťazec.

# Do "zhrnutie" daj krátke zhrnutie dokumentu hlavne s dôrazom na typy zásahov a chránených území.

# Text dokumentu:
# ---
# {text_content}
# ---
# """

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


def process_json_file(json_filepath_in, json_filepath_out, skip_analysis=False):
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

                                        dokument_data['analyza'] = None # Inicializácia kľúča pre analýzu
                                        #--------------------------------------------------
                                        # Download
                                        output_dir = f"{docs_dir}/{kraj_data['kraj']}/{okres_data['nazov']}/{doc_id}"
                                        existing_files = glob.glob(f"{output_dir}/orig.*")
                                        changed = False
                                        orig_file = None
                                        if not bool(existing_files) or os.path.getsize(existing_files[0]) < 10: # Stiahnuť, ak zoznam existujúcich súborov je prázdny
                                            download_attempts += 1 # Počítame pokus o stiahnutie
                                            orig_file = download_document(doc_url, output_dir, 'orig')
                                            changed = True
                                        else:
                                            print(f"Súbor pre ID {doc_id} už existuje: {existing_files[0]}. Preskakujem sťahovanie.")
                                            orig_file = existing_files[0]

                                        #--------------------------------------------------
                                        # Convert to text
                                        txt_filepath = f"{output_dir}/text.txt"
                                        # Skontroluj, či textový súbor už existuje
                                        if changed or not os.path.exists(txt_filepath) or os.path.getsize(txt_filepath) < 10:
                                            print(f"Súbor {txt_filepath} neexistuje. Pokúšam sa extrahovať text z {orig_file}")
                                            try:
                                                if orig_file.endswith('.pdf'):
                                                    text = extract_text_from_pdf(orig_file)
                                                    with open(txt_filepath, 'w', encoding='utf-8') as txt_file:
                                                        txt_file.write(text)
                                                elif orig_file.endswith(('.doc', '.docx')):
                                                    try:
                                                        # Použi pandoc na konverziu do markdown a uloženie do txt_filepath
                                                        # '-f docx' by mal fungovať aj pre .doc, ale môžeme byť explicitnejší ak treba
                                                        pandoc_format = 'docx' if orig_file.endswith('.docx') else 'doc'
                                                        cmd = ['pandoc', '-f', pandoc_format, '-t', 'markdown', '-o', txt_filepath, orig_file]
                                                        print(f"Spúšťam konverziu word dokumentu: {cmd}")
                                                        result = subprocess.run(cmd, check=True, capture_output=True, text=True, encoding='utf-8', errors='replace') # Added errors='replace' for robustness
                                                        print(f"Pandoc stdout:\n{result.stdout}") # Print stdout
                                                        print(f"Pandoc stderr:\n{result.stderr}") # Print stderr
                                                        print(f'result:{result}')
                                                        print(f"Word dokument úspešne konvertovaný a uložený do: {txt_filepath}")
                                                    except FileNotFoundError:
                                                        print(f"Chyba: Príkaz 'pandoc' nebol nájdený. Uistite sa, že je pandoc nainštalovaný a v systémovej PATH.", file=sys.stderr)
                                                    except subprocess.CalledProcessError as e:
                                                        print(f"Chyba pri konverzii Word dokumentu {orig_file} pomocou pandoc: {e}\nStderr: {e.stderr}", file=sys.stderr)
                                                    except Exception as e:
                                                        print(f"Neočakávaná chyba pri konverzii Word dokumentu {orig_file}: {e}", file=sys.stderr)

                                                changed = True
                                                print(f"Text úspešne extrahovaný a uložený do: {txt_filepath}")
                                            except Exception as e:
                                                # Chybu pri extrakcii logujeme, ale pokračujeme ďalej
                                                print(f"Chyba pri extrakcii textu z {orig_file}: {e}", file=sys.stderr)
                                        else:
                                            print(f"Súbor {txt_filepath} už existuje. Preskakujem extrakciu textu.")

                                        if skip_analysis:
                                            print(f"Preskakujem analýzu pre ID {doc_id} (--skip-analysis).")
                                            continue # Preskoč na ďalší dokument

                                        text = ''
                                        with open(txt_filepath, 'r', encoding='utf-8') as txt_file:
                                            text = txt_file.read()
                                        #--------------------------------------------------
                                        # Analyze with AI
                                        analysis_filepath_txt = f"{output_dir}/analysis.txt"

                                        if changed or not os.path.exists(analysis_filepath_txt) or os.path.getsize(analysis_filepath_txt) < 10:
                                            try: # Try to analyze
                                                analysis_result_str = analyze(text)
                                                changed = True
                                            except Exception as e:
                                                print(f"Chyba pri analýze: {e}", file=sys.stderr)

                                            try:
                                                with open(analysis_filepath_txt, 'w', encoding='utf-8') as f:
                                                    f.write(analysis_result_str)
                                                print(f"Analýza úspešne uložená do: {analysis_filepath_txt}")
                                            except Exception as e:
                                                print(f"Chyba pri ukladaní analýzy do súboru: {e}", file=sys.stderr)
                                        else:
                                            print(f"Súbor {analysis_filepath_txt} už existuje. Preskakujem analyzovanie.")

                                        # Načítanie textovej analýzy (aj keď sme ju práve negenerovali)
                                        if os.path.exists(analysis_filepath_txt):
                                            with open(analysis_filepath_txt, 'r', encoding='utf-8') as f:
                                                analysis_result_str = f.read()

                                        analysis_filepath_json = f"{output_dir}/analysis.json"
                                        if (changed or not os.path.exists(analysis_filepath_json)) and 'analysis_result_str' in locals() and analysis_result_str:
                                            try:
                                                analysis_result_data = json.loads(analysis_result_str)
                                                with open(analysis_filepath_json, 'w', encoding='utf-8') as f:
                                                    json.dump(analysis_result_data, f, indent=2, ensure_ascii=False)
                                                print(f"Analýza úspešne uložená do: {analysis_filepath_json}")
                                            except json.JSONDecodeError as json_e:
                                                print(f"Chyba: LLM nevrátil platný JSON pre {output_dir}. Odpoveď: {analysis_result_str}. Chyba: {json_e}", file=sys.stderr)
                                                # Môžeš sem uložiť pôvodnú odpoveď LLM do error súboru, ak chceš
                                                # with open(os.path.join(output_dir, "analyza_error.txt"), 'w', encoding='utf-8') as f_err:
                                                #     f_err.write(analysis_result_str)
                                        else:
                                            print(f"Súbor {analysis_filepath_json} už existuje. Preskakujem konverziu do JSONu.")

                                        # Načítanie JSON analýzy a pridanie do dokumentu
                                        if os.path.exists(analysis_filepath_json):
                                            try:
                                                with open(analysis_filepath_json, 'r', encoding='utf-8') as f_analysis:
                                                    analysis_data = json.load(f_analysis)
                                                    dokument_data['analyza'] = analysis_data # Pridanie analýzy do dát dokumentu
                                            except json.JSONDecodeError as e:
                                                print(f"Chyba pri načítaní JSON analýzy zo súboru {analysis_filepath_json}: {e}", file=sys.stderr)
                                                dokument_data['analyza'] = {"error": f"Failed to load analysis JSON: {e}"}

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

    # Výpis výsledného JSON na štandardný výstup
    try:
        print("Ukladám výstupný JSON s analýzami")
        # print(json.dumps(data, indent=2, ensure_ascii=False))
        json.dump(data, open(json_filepath_out, 'w', encoding='utf-8'), indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"Nastala chyba pri generovaní výstupného JSON: {e}", file=sys.stderr)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Spracuje JSON súbor s dokumentmi, stiahne ich, extrahuje text a voliteľne analyzuje.")
    parser.add_argument("json_in", help="Cesta k vstupnému JSON súboru.")
    parser.add_argument("json_out", help="Cesta k výstupnému JSON súboru.")
    parser.add_argument("--skip-analysis", action="store_true", help="Preskočí krok analýzy dokumentov pomocou LLM.")

    args = parser.parse_args()

    process_json_file(args.json_in, args.json_out, args.skip_analysis)
