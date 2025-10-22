import requests
from bs4 import BeautifulSoup
import json
import sys

def main():
    """
    Hlavná funkcia, ktorá scrapuje dáta a ukladá ich do JSON súboru.
    """
    url = "https://www.minv.sk/?okresne-urady-klientske-centra&kraj=1"

    try:
        # Stiahnutie obsahu stránky
        response = requests.get(url)
        response.raise_for_status() # Kontrola chýb pri sťahovaní

        soup = BeautifulSoup(response.content, 'html.parser')

        # Nájdeme kontajner pre ľavé menu
        sidemenu_list_div = soup.find('div', class_='sidemenu_list')

        data = []

        if sidemenu_list_div:
            # Nájdeme div so small-nav vo vnútri sidemenu_list
            small_nav_div = sidemenu_list_div.find('div', class_='small-nav -alt')

            if small_nav_div:
                # Nájdeme hlavný ul zoznam v small-nav
                main_ul = small_nav_div.find('ul', recursive=False) # Hľadáme priameho potomka ul

                if main_ul:
                    # Nájdeme konkrétny li element pre "Okresné úrady / Klientske centrá"
                    # Má id="menu-item-12224"
                    okresne_urady_li = main_ul.find('li', id='menu-item-12224')

                    if okresne_urady_li:
                        # Zoznam krajov je prvý ul s triedou 'sub-menu' priamo vo vnútri tohto li
                        kraje_ul = okresne_urady_li.find('ul', class_='sub-menu', recursive=False)

                        if kraje_ul:
                            # Prechádzame jednotlivé li elementy v zozname krajov
                            kraje_li_items = kraje_ul.find_all('li', class_='menu-item-has-children')

                            for kraj_li in kraje_li_items:
                                kraj_data = {}
                                # Link na kraj je priamo v tomto li
                                kraj_link = kraj_li.find('a', recursive=False)

                                if kraj_link:
                                    kraj_data['kraj'] = kraj_link.get_text(strip=True)
                                    kraj_data['url'] = kraj_link.get('href')
                                    kraj_data['okresy'] = []

                                    # Zoznam okresov je ul s triedou 'sub-menu' priamo vo vnútri li kraja
                                    okresy_ul = kraj_li.find('ul', class_='sub-menu', recursive=False)
                                    if okresy_ul:
                                        # Prechádzame jednotlivé li elementy v zozname okresov
                                        okresy_li_items = okresy_ul.find_all('li')

                                        for okres_li in okresy_li_items:
                                            okres_data = {}
                                            # Link na okres je priamo v tomto li
                                            okres_link = okres_li.find('a', recursive=False)
                                            if okres_link:
                                                okres_data['nazov'] = okres_link.get_text(strip=True)
                                                okres_data['url'] = okres_link.get('href')
                                                kraj_data['okresy'].append(okres_data)

                                # Pridáme dáta kraja, ak boli nájdené
                                if kraj_data.get('kraj'):
                                    data.append(kraj_data)
        
        return data

    except requests.exceptions.RequestException as e:
        print(f"Chyba pri sťahovaní stránky: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Nastala chyba: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == '__main__':
    import argparse
    import os

    parser = argparse.ArgumentParser(description='Scrape region and district data from minv.sk.')
    parser.add_argument('-o', '--output', help='Output JSON file path', required=True)
    args = parser.parse_args()

    scraped_data = main()
    
    try:
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(scraped_data, f, indent=2, ensure_ascii=False)
        print(f"Spracovanie dokončené. Dáta uložené do: {os.path.abspath(args.output)}", file=sys.stderr)
    except IOError as e:
        print(f"Chyba pri zápise do súboru {args.output}: {e}", file=sys.stderr)
        sys.exit(1)
