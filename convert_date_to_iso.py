import json
import sys
from datetime import datetime

# Definícia formátov dátumu
# Vstupný formát: "d. m. yyyy" (napr. "30. 4. 2025", "18. 3. 2025")
# Medzery a bodky sú dôležité: "D. M. RRRR"
# %d: Deň v mesiaci ako desatinné číslo [01,31]. Jednociferné dni sú akceptované.
# %m: Mesiac ako desatinné číslo [01,12]. Jednociferné mesiace sú akceptované.
# %Y: Rok so storočím ako desatinné číslo (napr. 2025).
INPUT_DATE_FORMAT = "%d. %m. %Y"

# Výstupný formát: "yyyy-mm-dd" (napr. "2025-04-30")
OUTPUT_DATE_FORMAT = "%Y-%m-%d"

def date_str_to_iso(s):
    """
    Konvertuje reťazec s dátumom na ISO formát (YYYY-MM-DD).
    Skúša viacero bežných formátov: "d. m. yyyy", "d.m.yyyy", "d.m. yyyy".
    """
    # Zoznam formátov na vyskúšanie, od najčastejšieho/najprísnejšieho po menej časté
    INPUT_DATE_FORMATS = [
        "%d. %m. %Y", # Pôvodný formát (napr. "30. 4. 2025")
        "%d.%m.%Y",   # Bez medzier (napr. "30.4.2025")
        "%d.%m. %Y",  # Medzera len pred rokom (napr. "30.4. 2025")
        "%d. %m.%Y",  # Medzera len pred rokom (napr. "30.4. 2025")
        "%Y-%m-%d",   # Ked je datum uz v cielovom formate, aby nevypisalo chybu
        # Môžete pridať ďalšie formáty podľa potreby
    ]
    OUTPUT_DATE_FORMAT = "%Y-%m-%d"

    for fmt in INPUT_DATE_FORMATS:
        try:
            # Pokúsi sa parsávať reťazec dátumu pomocou aktuálneho formátu
            date_obj = datetime.strptime(s, fmt)
            # Ak úspešné, formátuje a vráti ISO dátum
            return date_obj.strftime(OUTPUT_DATE_FORMAT)
        except ValueError:
            # Ak tento formát nepasuje, pokračuje na ďalší
            continue

    # Ak žiadny formát nepasoval, vypíše chybu a vráti pôvodný reťazec
    print(f"Chyba: Nepodarilo sa parsovať dátum '{s}' ani v jednom z očakávaných formátov: {INPUT_DATE_FORMATS}. Vraciam pôvodnú hodnotu.", file=sys.stderr)
    return s

def transform_date_format(data):
    """
    Rekurzívne prechádza vnorenú dátovú štruktúru (zoznamy a slovníky)
    a transformuje formát reťazca akejkoľvek hodnoty nájdenej pod kľúčom 'datum'
    zo INPUT_DATE_FORMAT na OUTPUT_DATE_FORMAT.
    Upravuje dátovú štruktúru priamo na mieste (in place).

    Args:
        data: Dátová štruktúra na prechádzanie (očakáva sa zoznam alebo slovník).
    """
    if isinstance(data, list):
        # Ak je aktuálny prvok dát zoznam, prechádza cez jeho položky
        # a rekurzívne volá transform_date_format pre každú položku.
        for item in data:
            transform_date_format(item)
    elif isinstance(data, dict):
        # Ak je aktuálny prvok dát slovník, skontroluje, či obsahuje kľúč 'datum'.
        if 'datum' in data:
            datum_value = data['datum']
            # Skontroluje, či je hodnota priradená k 'datum' reťazec
            if isinstance(datum_value, str):
                data['datum'] = date_str_to_iso(datum_value)

        # Bez ohľadu na to, či bol kľúč 'datum' nájdený/spracovaný v tomto slovníku,
        # rekurzívne spracuje jeho hodnoty, ak sú vnorené zoznamy alebo slovníky.
        for key, value in data.items():
             transform_date_format(value)
    # Ak data nie sú ani zoznam, ani slovník (napr. reťazec, číslo, boolean, None),
    # je to koncový uzol, ktorý nemusíme ďalej prechádzať (pokiaľ to nie je reťazec
    # 'datum' na najvyššej úrovni, čo kontroluje podmienka slovníka).
    # Rekurzia sa tu pre tieto typy zastaví.


def main():
    """
    Načíta JSON zo štandardného vstupu, transformuje formát poľa 'datum'
    a upravený JSON zapíše na štandardný výstup.
    """
    try:
        # Načíta celý JSON vstup zo štandardného vstupu
        input_json_string = sys.stdin.read()

        # Parsuje JSON reťazec do dátovej štruktúry Pythonu
        # Ak je vstup prázdny, json.loads vyvolá chybu.
        if not input_json_string.strip():
             print("Chyba: Vstup je prázdny.", file=sys.stderr)
             sys.exit(1) # Ukončí skript s chybovým kódom

        data = json.loads(input_json_string)

        # Zavolá transformačnú funkciu na načítané dáta
        transform_date_format(data) # Toto upraví objekt 'data' priamo na mieste

        # Zapíše upravenú dátovú štruktúru Pythonu späť do JSON reťazca
        # indent=2 robí výstup prehľadnejším (s odsadením)
        # ensure_ascii=False umožňuje výstup ne-ASCII znakov priamo (ako sú slovenské)
        json.dump(data, sys.stdout, indent=2, ensure_ascii=False)
        sys.stdout.write('\n') # Pridá nový riadok na koniec pre čistý výstup

    except json.JSONDecodeError as e:
        # Spracuje chyby, ak vstup nie je platný JSON
        print(f"Chyba pri dekódovaní JSON zo vstupu: {e}", file=sys.stderr)
        sys.exit(1) # Ukončí skript s ne-nulovým stavovým kódom, ktorý naznačuje chybu
    except Exception as e:
        # Spracuje akékoľvek iné neočakávané chyby
        print(f"Nastala neočakávaná chyba: {e}", file=sys.stderr)
        sys.exit(1) # Ukončí skript s ne-nulovým stavovým kódom

# Vstupný bod skriptu
if __name__ == "__main__":
    main()