import argparse
import json
import sys
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://www.minzp.sk"

def clean_district_name(name):
    """Cleans the district name by removing unnecessary prefixes."""
    name = name.replace("Okresný úrad", "").replace("v ", "").strip()
    if name == "Pezinku":
        name = "Pezinok"
    return name


def get_soup(url):
    """Fetches a URL and returns a BeautifulSoup object."""
    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        return BeautifulSoup(response.content, "html.parser")
    except requests.RequestException as e:
        print(f"Chyba pri sťahovaní stránky {url}: {e}", file=sys.stderr)
        return None


def scrape_districts(region_url):
    """Scrapes district information from a region's page."""
    districts = []
    soup = get_soup(region_url)
    if not soup:
        return districts

    # Find the link for the current region (e.g., 'Kraj Bratislava')
    region_link = soup.select_one(f'div.leftMenu a[href="{region_url.replace(BASE_URL, "")}"]')
    if not region_link:
        print(f"Chyba: Nenašiel sa odkaz pre región na stránke {region_url}", file=sys.stderr)
        return districts

    # The districts are in a <ul> that is a sibling to the region link's parent <li>
    region_li = region_link.find_parent('li')
    if not region_li:
        return districts

    districts_ul = region_li.find('ul')
    if not districts_ul:
        print(f"Chyba: Nenašiel sa zoznam okresov pre {region_url}", file=sys.stderr)
        return districts

    for district_li in districts_ul.find_all('li', recursive=False):
        link = district_li.find('a')
        if link and link.has_attr('href'):
            name = link.get_text(strip=True)
            clean_name = clean_district_name(name)
            districts.append({"nazov": clean_name, "url": link['href']})

    return districts


def main():
    """Main function to scrape regions and their districts."""
    parser = argparse.ArgumentParser(description="Scrape districts from minzp.sk.")
    parser.add_argument('--output', required=True, help='Path to the output JSON file.')
    args = parser.parse_args()

    start_url = urljoin(BASE_URL, "/uradna-tabula/priroda/")
    print(f"Sťahujem zoznam krajov z: {start_url}")
    soup = get_soup(start_url)
    if not soup:
        sys.exit(1)

    regions_data = []
    # Find the main navigation list for "Ochrana prírody"
    regions_ul = soup.select_one('div.leftMenu li.open > ul')
    if not regions_ul:
        print("Chyba: Nepodarilo sa nájsť zoznam krajov na hlavnej stránke.", file=sys.stderr)
        sys.exit(1)

    for region_li in regions_ul.find_all('li', recursive=False):
        link = region_li.find('a')
        if link and link.has_attr('href') and "kraj" in link.get_text(strip=True).lower():
            region_name = link.get_text(strip=True).replace("Kraj ", "")
            region_url = urljoin(BASE_URL, link['href'])

            print(f"Spracovávam kraj: {region_name} ({region_url})")
            districts = scrape_districts(region_url)

            regions_data.append({
                "kraj": region_name,
                "okresy": districts
            })

    print(f"Zapisujem dáta do súboru: {args.output}")
    try:
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(regions_data, f, ensure_ascii=False, indent=2)
        print("Scraping úspešne dokončený.")
    except IOError as e:
        print(f"Chyba pri zápise do súboru {args.output}: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()