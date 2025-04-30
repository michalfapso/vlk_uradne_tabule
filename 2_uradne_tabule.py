import json
import requests
from bs4 import BeautifulSoup
import time
import sys
from requests.compat import urljoin
import copy

# Base URL of the website
BASE_URL = "https://www.minv.sk"
# Suffix to add to the district URL to get to the 'Životné prostredie / Úradná tabuľa' section
DEPARTMENT_SUFFIX = "&odbor=10&sekcia=uradna-tabula"

def scrape_district_environmental_board(district_url):
    """
    Scrapes the environmental public notice board for a given district URL.
    Extracts categories and nested documents (name, date, URL).

    Args:
        district_url (str): The base URL for the district page (e.g., "/?okresne-urady-klientske-centra&urad=35").

    Returns:
        list: A list of dictionaries, where each dictionary represents a category
              and contains a list of documents. Each document dictionary includes
              'datum', 'nazov', and 'url'.
              Returns an empty list if the page, the relevant table, or data
              within the table is not found or cannot be parsed correctly.
    """
    # Construct the full URL for the environmental public notice board
    full_url = urljoin(BASE_URL, district_url + DEPARTMENT_SUFFIX)
    print(f"Sťahujem: {full_url}")

    try:
        # Add a small delay to be polite to the server
        time.sleep(1)
        response = requests.get(full_url, timeout=15) # Increased timeout slightly
        response.raise_for_status() # Raise an HTTPError for bad responses (4xx or 5xx)

        soup = BeautifulSoup(response.content, 'html.parser')

        # Find the section containing the tables (usually #popis)
        popis_section = soup.find('div', id='popis')
        if not popis_section:
            print(f"Sekcia #popis nenájdená na {full_url}. Preskakujem s prázdnymi dátami.")
            return [] # Return empty list if the main section is missing

        # Find the specific H2 title for the target table within the #popis section
        # Use a lambda function to match the text containing the target string (case-insensitive)
        h2_target = popis_section.find('h2', string=lambda text: text and 'životné prostredie / úradná tabuľa' in text.lower())

        target_table = None
        if h2_target:
            # The table usually follows the H2 title. Find the next sibling table with class 'tabdoc'
            target_table = h2_target.find_next_sibling('table', class_='tabdoc')
        # Note: If h2_target is None, target_table remains None, handled by the next if.

        if not target_table:
            print(f"Tabuľka 'Životné prostredie / Úradná tabuľa' nenájdená po H2 titulku na {full_url}. Preskakujem s prázdnymi dátami.")
            return [] # Return empty list if the target table is missing

        categories_data_dict = {} # Use a dictionary to group documents by category name
        current_category = None

        # Iterate over table rows
        for row in target_table.find_all('tr'):
            # Check for category row (class="tddocup") - This row contains the category name
            category_cell = row.find('td', class_='tddocup')
            if category_cell:
                # Extract text, strip whitespace and potential bold tags
                category_name = category_cell.get_text(strip=True)
                current_category = category_name
                # Initialize the list of documents for this category if it doesn't exist
                if current_category and current_category not in categories_data_dict: # Ensure category name is not empty
                    categories_data_dict[current_category] = []
                continue # Move to the next row (this row only contains category)

            # Check for document row (class="document-name") - This row contains document info
            document_name_cell = row.find('td', class_='document-name')
            if document_name_cell:
                # Find the link within the document name cell
                link = document_name_cell.find('a', class_='govuk-link')

                # Ensure a link exists and we have a current category to assign the document to
                # Also ensure the current_category exists in our dictionary keys (it might not if a tddocup row was missing/malformed)
                if link and current_category is not None and current_category in categories_data_dict:
                    # Get the full text content of the cell (e.g., "DD. MM. YYYY | Document Name (size)")
                    full_cell_text = document_name_cell.get_text(strip=True)

                    # Get the document name from the link text (e.g., "Document Name (size)")
                    document_name = link.get_text(strip=True)

                    # Attempt to extract the date string by splitting the full cell text by '|'
                    # Find the index of the first '|'
                    pipe_index = full_cell_text.find('|')

                    date_str = None
                    # If '|' is found and is not at the very beginning, the part before it is the date
                    if pipe_index > 0:
                         date_str = full_cell_text[:pipe_index].strip()
                    # If '|' is not found or is at the beginning, date_str remains None

                    # Get the document URL from the link's href attribute
                    relative_url = link.get('href')
                    full_document_url = None
                    if relative_url:
                         # Ensure URL is absolute by joining with the base URL
                         full_document_url = urljoin(BASE_URL, relative_url)

                    # Append the document data if we have a valid URL.
                    # Documents without a URL are not useful in this context.
                    if full_document_url:
                         # Append the document details to the list of documents for the current category
                         categories_data_dict[current_category].append({
                             "datum": date_str, # Add the extracted date string (can be None)
                             "nazov": document_name,
                             "url": full_document_url
                         })
                    else:
                         # Log a warning if a link was found but had no href attribute
                         print(f"Upozornenie: Dokument v kategórii '{current_category}' na {full_url} má odkaz bez platného 'href' atribútu. Preskakujem.", file=sys.stderr)
                # else: Row had 'document-name' but no link, no valid current_category, or current_category not in dict. Ignore.

        # Convert the dictionary format (category: [docs]) to the desired list format ([{"kategoria": k, "dokumenty": v}, ...])
        # Filter out categories that ended up with no documents (shouldn't happen often, but good practice)
        result_list_of_categories = [{"kategoria": k, "dokumenty": v} for k, v in categories_data_dict.items() if v]

        return result_list_of_categories # Return the list of category blocks for this district

    except requests.exceptions.Timeout:
        print(f"Chyba timeout pri sťahovaní {full_url}.", file=sys.stderr)
        return [] # Return empty list on error
    except requests.exceptions.RequestException as e:
        print(f"Chyba pri sťahovaní {full_url}: {e}", file=sys.stderr)
        return [] # Return empty list on error
    except Exception as e:
        print(f"Nastala neočakávaná chyba pri spracovaní {full_url}: {e}", file=sys.stderr)
        # sys.excepthook(type(e), e, e.__traceback__) # Uncomment for detailed traceback if needed
        return []


def main(input_json_file, output_json_file):
    """
    Loads input JSON, scrapes data from district environmental boards,
    and structures the results according to the desired output format,
    keeping documents nested under categories within each district.

    Args:
        input_json_file (str): Path to the input JSON file.
        output_json_file (str): Path to save the output JSON file.
    """
    try:
        with open(input_json_file, 'r', encoding='utf-8') as f:
            input_data = json.load(f)
    except FileNotFoundError:
        print(f"Chyba: Vstupný súbor '{input_json_file}' nenájdený.", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError:
        print(f"Chyba: Vstupný súbor '{input_json_file}' nie je platný JSON.", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
         print(f"Chyba pri načítaní vstupného súboru: {e}", file=sys.stderr)
         sys.exit(1)

    # Create a deep copy of the input data structure to add the scraped documents to
    output_data = copy.deepcopy(input_data)

    # Iterate through kraje and okresy in the output structure (the copied data)
    for kraj_data in output_data:
        kraj_name = kraj_data.get('kraj', 'Neznámy kraj')
        okresy = kraj_data.get('okresy', [])
        print(f"\nSpracovávam kraj: {kraj_name}")

        for okres_data in okresy:
            okres_name = okres_data.get('nazov', 'Neznámy okres')
            # Get the URL from the original structure (which is now in okres_data of output_data)
            okres_url = okres_data.get('url')

            # Initialize the list for scraped documents for this district in the output structure.
            # It will contain the list of category blocks returned by the scraper.
            okres_data['dokumenty_zivotne_prostredie'] = []

            if okres_url:
                print(f"Spracovávam okres: {okres_name}")
                # Scrape the environmental board for this district.
                # This function now returns a list of category blocks (e.g., [{"kategoria": "...", "dokumenty": [...]}, ...]).
                district_environmental_data = scrape_district_environmental_board(okres_url)

                # Assign the scraped category blocks data directly to the new key for this district
                okres_data['dokumenty_zivotne_prostredie'] = district_environmental_data

                # Optional: Remove the original 'url' key for the district itself if it's not needed in the output
                # If you want to keep the district URL, comment out or remove the next line:
                okres_data.pop('url', None) # .pop(key, default) removes key if it exists, without error if not

            else:
                print(f"Upozornenie: Okres '{okres_name}' v kraji '{kraj_name}' nemá 'url'. Pre tento okres nebudú stiahnuté dokumenty.")
                # The 'dokumenty_zivotne_prostredie' list for this district will remain empty [] as initialized.

        # Optional: Remove the original 'url' key for the kraj itself if it's not needed in the output
        # If you want to keep the kraj URL, comment out or remove the next line:
        kraj_data.pop('url', None) # .pop(key, default)


    # Save the output JSON
    try:
        with open(output_json_file, 'w', encoding='utf-8') as f:
            # Use ensure_ascii=False to correctly write Slovak characters in the output file
            json.dump(output_data, f, indent=2, ensure_ascii=False)
        print(f"\nDáta boli úspešne uložené do súboru '{output_json_file}'.")
    except IOError as e:
        print(f"Chyba pri zápise do súboru '{output_json_file}': {e}", file=sys.stderr)
    except Exception as e:
         print(f"Nastala neočakávaná chyba pri ukladaní súboru: {e}", file=sys.stderr)


if __name__ == "__main__":
    # Define input and output filenames
    input_file = '1_zoznam_okresov.json'
    output_file = '2_uradne_tabule.json'

    main(input_file, output_file)
