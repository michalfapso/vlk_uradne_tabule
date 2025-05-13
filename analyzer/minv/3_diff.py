import json
import sys
import argparse

def build_document_url_set(data):
    """
    Prejde štruktúru dát a vytvorí množinu (set) všetkých URL dokumentov.
    Používa sa na rýchle vyhľadávanie existujúcich dokumentov.
    """
    urls = set()
    if not isinstance(data, list):
        print("Varovanie: Vstupné dáta nie sú list. Preskakujem vytvorenie URL setu.", file=sys.stderr)
        return urls

    for kraj in data:
        if isinstance(kraj, dict) and "okresy" in kraj and isinstance(kraj["okresy"], list):
            for okres in kraj["okresy"]:
                if isinstance(okres, dict) and "dokumenty_zivotne_prostredie" in okres and isinstance(okres["dokumenty_zivotne_prostredie"], list):
                    for kategoria in okres["dokumenty_zivotne_prostredie"]:
                        if isinstance(kategoria, dict) and "dokumenty" in kategoria and isinstance(kategoria["dokumenty"], list):
                            for dokument in kategoria["dokumenty"]:
                                if isinstance(dokument, dict) and "url" in dokument:
                                    urls.add(dokument["url"])
    return urls

def find_new_documents(old_urls_set, new_data):
    """
    Porovná nové dáta so setom starých URL a vráti štruktúru
    obsahujúcu iba dokumenty, ktoré nie sú v starom sete URL.
    Zachováva pôvodnú štruktúru (kraj -> okres -> kategoria -> dokumenty).
    """
    new_data_structure = []

    if not isinstance(new_data, list):
        print("Varovanie: Nové vstupné dáta nie sú list. Nemôžem spracovať.", file=sys.stderr)
        return new_data_structure

    for kraj in new_data:
        if isinstance(kraj, dict):
            new_kraj = {
                "kraj": kraj.get("kraj"),
                "url": kraj.get("url"),
                "okresy": []
            }
            if "okresy" in kraj and isinstance(kraj["okresy"], list):
                for okres in kraj["okresy"]:
                    if isinstance(okres, dict):
                        new_okres = {
                            "nazov": okres.get("nazov"),
                            "url": okres.get("url"),
                            "dokumenty_zivotne_prostredie": []
                        }
                        if "dokumenty_zivotne_prostredie" in okres and isinstance(okres["dokumenty_zivotne_prostredie"], list):
                            for kategoria in okres["dokumenty_zivotne_prostredie"]:
                                if isinstance(kategoria, dict):
                                    new_kategoria = {
                                        "kategoria": kategoria.get("kategoria"),
                                        "dokumenty": []
                                    }
                                    if "dokumenty" in kategoria and isinstance(kategoria["dokumenty"], list):
                                        for dokument in kategoria["dokumenty"]:
                                            if isinstance(dokument, dict) and "url" in dokument and dokument["url"] not in old_urls_set:
                                                # Ak dokument nie je v starom sete URL, je nový
                                                new_kategoria["dokumenty"].append(dokument)

                                    # Pridaj kategóriu do okresu len ak obsahuje nové dokumenty
                                    if new_kategoria["dokumenty"]:
                                        new_okres["dokumenty_zivotne_prostredie"].append(new_kategoria)

                        # Pridaj okres do kraja len ak obsahuje kategórie s novými dokumentmi
                        if new_okres["dokumenty_zivotne_prostredie"]:
                            new_kraj["okresy"].append(new_okres)

            # Pridaj kraj do výstupu len ak obsahuje okresy s novými dokumentmi
            if new_kraj["okresy"]:
                new_data_structure.append(new_kraj)

    return new_data_structure

def load_json_file(filepath):
    """Loads a JSON file, handles errors, and exits on failure."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data
    except FileNotFoundError:
        print(f"Chyba: JSON súbor nebol nájdený na '{filepath}'", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError:
        print(f"Chyba: Nepodarilo sa dekódovať JSON zo súboru '{filepath}'", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Nastala neočakávaná chyba pri čítaní JSON súboru '{filepath}': {e}", file=sys.stderr)
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description="Nájde nové dokumenty v novšom JSON súbore oproti staršiemu JSON súboru.")
    parser.add_argument('--old', required=True, help='Cesta k staršiemu JSON súboru.')
    parser.add_argument('--new', required=True, help='Cesta k novšiemu JSON súboru.')

    args = parser.parse_args()

    # Načítanie starého a nového JSON súboru pomocou pomocnej funkcie
    old_data = load_json_file(args.old)
    new_data = load_json_file(args.new)

    # Vytvorenie množiny URL zo starých dát pre rýchle vyhľadávanie
    old_urls_set = build_document_url_set(old_data)

    # Nájdenie nových dokumentov
    new_documents = find_new_documents(old_urls_set, new_data)

    # Výpis výsledku do JSON formátu na štandardný výstup (stdout)
    try:
        print(json.dumps(new_documents, indent=2, ensure_ascii=False))
    except Exception as e:
        print(f"Nastala chyba pri zápise výstupného JSON súboru: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()