import argparse
import json
import sys

def load_json_file(filepath):
    """Načíta JSON súbor a vráti jeho obsah."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data
    except FileNotFoundError:
        print(f"Chyba: Súbor '{filepath}' nebol nájdený.", file=sys.stderr)
        return None
    except json.JSONDecodeError:
        print(f"Chyba: Súbor '{filepath}' neobsahuje validný JSON.", file=sys.stderr)
        return None
    except Exception as e:
        print(f"Nastala neočakávaná chyba pri načítaní súboru '{filepath}': {e}", file=sys.stderr)
        return None

def find_new_items(old_data, new_data):
    """
    Nájde položky, ktoré sú v new_data, ale nie v old_data,
    na základe poľa 'url'.
    """
    if not isinstance(old_data, list):
        print(f"Varovanie: Staré dáta nie sú zoznam (list). Budú považované za prázdne.", file=sys.stderr)
        old_data = []
    if not isinstance(new_data, list):
        print(f"Varovanie: Nové dáta nie sú zoznam (list). Nebudú nájdené žiadne nové položky.", file=sys.stderr)
        new_data = []

    # Vytvorí množinu 'url' hodnôt zo starých dát pre efektívne vyhľadávanie
    # Predpokladá sa, že 'url' je unikátny identifikátor položky
    old_items_identifiers = set()
    for item in old_data:
        if isinstance(item, dict) and 'url' in item:
            old_items_identifiers.add(item['url'])
        else:
            print(f"Varovanie: Položka v starom súbore nemá očakávanú štruktúru alebo chýba 'url': {item}", file=sys.stderr)

    newly_added_items = []
    for item in new_data:
        if isinstance(item, dict) and 'url' in item:
            if item['url'] not in old_items_identifiers:
                newly_added_items.append(item)
        else:
            print(f"Varovanie: Položka v novom súbore nemá očakávanú štruktúru alebo chýba 'url': {item}", file=sys.stderr)

    return newly_added_items

def main():
    parser = argparse.ArgumentParser(description="Porovná dva JSON súbory a vypíše položky, ktoré pribudli v novom súbore.")
    parser.add_argument('--old', dest='old_json_file', required=True, help="Cesta k starému JSON súboru.")
    parser.add_argument('--new', dest='new_json_file', required=True, help="Cesta k novému JSON súboru.")

    args = parser.parse_args()

    old_data = load_json_file(args.old_json_file)
    new_data = load_json_file(args.new_json_file)

    if old_data is None or new_data is None:
        # Chybové hlášky už boli vypísané funkciou load_json_file
        sys.exit(1)

    newly_added_items = find_new_items(old_data, new_data)

    # Vypíše nové položky ako JSON pole, pekne formátované
    # ensure_ascii=False zabezpečí správne zobrazenie diakritiky
    print(json.dumps(newly_added_items, indent=2, ensure_ascii=False))

if __name__ == '__main__':
    main()