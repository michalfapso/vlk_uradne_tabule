import json
import requests
from bs4 import BeautifulSoup
import time
import sys
from requests.compat import urljoin # Use compat for older python versions if needed, but urljoin is standard
import copy # Import copy module for deep copying the input structure

# Base URL of the website
BASE_URL = "https://www.minv.sk"
# Suffix to add to the district URL to get to the 'Životné prostredie / Úradná tabuľa' section
DEPARTMENT_SUFFIX = "&odbor=10&sekcia=uradna-tabula"

def scrape_district_environmental_board(district_url):
    """
    Scrapes the environmental public notice board for a given district URL.
    Extracts category, document name, date, and URL.

    Args:
        district_url (str): The base URL for the district page (e.g., "/?okresne-urady-klientske-centra&urad=35").

    Returns:
        list: A list of dictionaries, where each dictionary represents a category
              and contains a list of documents. Each document dictionary includes
              'datum', 'nazov', and 'url'.
              Returns an empty list if the page or the relevant table is not found
              or cannot be parsed.
    """
    # Construct the full URL for the environmental public notice board
    full_url = urljoin(BASE_URL, district_url + DEPARTMENT_SUFFIX)
    print(f"Sťahujem: {full_url}")

    try:
        # Add a small delay to be polite to the server
        time.sleep(1)
        response = requests.get(full_url, timeout=10) # Added timeout for robustness
        response.raise_for_status() # Raise an HTTPError for bad responses (4xx or 5xx)

        soup = BeautifulSoup(response.content, 'html.parser')

        # Find the section containing the tables (usually #popis)
        popis_section = soup.find('div', id='popis')
        if not popis_section:
            print(f"Sekcia #popis nenájdená na {full_url}. Preskakujem s prázdnymi dátami.")
            return [] # Return empty list if the main section is missing

        # Find the specific H2 title for the target table within the #popis section
        # Use a lambda function to match the text containing the target string
        # Case-insensitive search just in case
        h2_target = popis_section.find('h2', string=lambda text: text and 'životné prostredie / úradná tabuľa' in text.lower())

        target_table = None
        if h2_target:
            # The table usually follows the H2 title. Find the next sibling table with class 'tabdoc'
            target_table = h2_target.find_next_sibling('table', class_='tabdoc')
        # Note: If h2_target is None, target_table remains None, handled by the next if.

        if not target_table:
            print(f"Tabuľka 'Životné prostredie / Úradná tabuľa' nenájdená po H2 titulku na {full_url}. Preskakujem s prázdnymi dátami.")
            return [] # Return empty list if the target table is missing

        categories_data = {}
        current_category = None

        # Iterate over table rows
        for row in target_table.find_all('tr'):
            # Check for category row (class="tddocup")
            category_cell = row.find('td', class_='tddocup')
            if category_cell:
                # Extract text, strip whitespace and potential bold tags
                # get_text(strip=True) usually handles basic tags like <strong>
                category_name = category_cell.get_text(strip=True)
                current_category = category_name
                # Initialize the list for this category if it doesn't exist
                if current_category and current_category not in categories_data: # Ensure category name is not empty
                    categories_data[current_category] = []
                continue # Move to the next row

            # Check for document row (class="document-name")
            document_name_cell = row.find('td', class_='document-name')
            if document_name_cell:
                link = document_name_cell.find('a', class_='govuk-link') # Find the link within the cell

                # Ensure a link exists and we have a current category to assign the document to
                if link and current_category is not None and current_category in categories_data:
                    # Get the full text content of the cell (e.g., "DD. MM. YYYY | Document Name (size)")
                    full_cell_text = document_name_cell.get_text(strip=True)

                    # Get the document name from the link text (e.g., "Document Name (size)")
                    document_name = link.get_text(strip=True)

                    # Attempt to extract the date string by splitting the full cell text by '|'
                    # Find the index of the first '|'
                    pipe_index = full_cell_text.find('|')

                    date_str = None
                    # If '|' is found and is not at the beginning
                    if pipe_index > 0:
                         # The part before '|' is the date string
                         date_str = full_cell_text[:pipe_index].strip()
                         # Remove the date string and '|' from the document_name if needed,
                         # but we already got the name from the link text, which is safer.

                    # Get the document URL
                    relative_url = link.get('href')
                    full_document_url = None
                    if relative_url:
                         # Ensure URL is absolute by joining with the base URL
                         full_document_url = urljoin(BASE_URL, relative_url)

                    # Append the document data if we have a valid URL.
                    # Documents without a URL are not useful in this context.
                    if full_document_url:
                         categories_data[current_category].append({
                             "datum": date_str, # Add the extracted date string (can be None)
                             "nazov": document_name,
                             "url": full_document_url
                         })
                    else:
                         print(f"Upozornenie: Dokument v kategórii '{current_category}' v okrese {full_url} má odkaz bez platného 'href' atribútu. Preskakujem.", file=sys.stderr)
                # else: Row had 'document-name' but no link or no valid current_category. Ignore.

        # This function originally returned a list of category blocks.
        # For the new output structure, we need a flat list of all documents from this district.
        all_documents_for_district = []
        for category, documents in categories_data.items():
             all_documents_for_district.extend(documents)

        return all_documents_for_district # Return a single list of documents for this district

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
    and structures the results according to the desired output format.

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

    # Iterate through kraje and okresy in the output structure
    for kraj_data in output_data:
        kraj_name = kraj_data.get('kraj', 'Neznámy kraj')
        okresy = kraj_data.get('okresy', [])
        print(f"\nSpracovávam kraj: {kraj_name}")

        for okres_data in okresy:
            okres_name = okres_data.get('nazov', 'Neznámy okres')
            okres_url = okres_data.get('url') # Get the URL from the original input structure

            # Initialize documents list for this district in the output structure
            # Will be populated or remain empty if scraping fails
            okres_data['dokumenty'] = []

            if okres_url:
                print(f"Spracovávam okres: {okres_name}")
                # Scrape the environmental board for this district.
                # This function is modified to return a flat list of documents.
                district_documents = scrape_district_environmental_board(okres_url)

                # Add the scraped documents to the 'dokumenty' list for this district
                okres_data['dokumenty'].extend(district_documents)

                # Remove the original 'url' key for the district itself if it's not needed in the output
                if 'url' in okres_data:
                    del okres_data['url']
            else:
                print(f"Upozornenie: Okres '{okres_name}' v kraji '{kraj_name}' nemá 'url'. Pre tento okres nebudú stiahnuté dokumenty.")


        # Remove the original 'url' key for the kraj itself if it's not needed in the output
        # (Based on the requested output structure, kraj URL is not included)
        if 'url' in kraj_data:
             del kraj_data['url']


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
