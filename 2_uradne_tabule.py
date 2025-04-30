import json
import requests
from bs4 import BeautifulSoup
import time
import sys
import re # Import regex module for more robust date parsing
from requests.compat import urljoin
import copy

# Base URL of the website
BASE_URL = "https://www.minv.sk"
# Suffix to add to the district URL to get to the 'Životné prostredie / Úradná tabuľa' section
DEPARTMENT_SUFFIX = "&odbor=10&sekcia=uradna-tabula"

# Regex to match a date string like "DD.MM.YYYY" or "D.M.YYYY" etc.
# Flexible for leading zeros and space after dot
DATE_REGEX = re.compile(r'\d{1,2}\.\s*\d{1,2}\.\s*\d{2,4}')

def is_potential_date_paragraph(p_tag):
    """
    Checks if a <p> tag potentially contains only a date string and no link.
    This helps distinguish date markers from document links or other text.
    """
    if not p_tag or p_tag.find('a'): # If it contains a link, it's likely a document paragraph
        return False
    text = p_tag.get_text(strip=True)
    if not text:
        return False
    # Check if the text matches the date pattern and is not excessively long
    # Adding a length check helps avoid matching dates buried in other text
    if DATE_REGEX.fullmatch(text) and len(text) < 15: # fullmatch ensures only the pattern is present
        return True
    return False

def scrape_district_environmental_board(district_url):
    """
    Scrapes the environmental public notice board for a given district URL.
    Handles both table-based and paragraph-based structures.
    Extracts categories (or uses empty for paragraphs), document name, date, and URL.

    Args:
        district_url (str): The base URL for the district page (e.g., "/?okresne-urady-klientske-centra&urad=35").

    Returns:
        list: A list of dictionaries, where each dictionary represents a category
              and contains a list of documents. Each document dictionary includes
              'datum', 'nazov', and 'url'.
              Returns an empty list if the page, the relevant content, or data
              cannot be found or parsed.
    """
    # Construct the full URL
    full_url = urljoin(BASE_URL, district_url + DEPARTMENT_SUFFIX)
    print(f"Sťahujem: {full_url}")

    try:
        # Add a small delay and set timeout
        time.sleep(1)
        
        response = requests.get(full_url, timeout=15)
        response.raise_for_status() # Raise an HTTPError for bad responses (4xx or 5xx)

        soup = BeautifulSoup(response.content, 'html.parser')

        # Find the section containing the main content (usually #popis)
        popis_section = soup.find('div', id='popis')
        if not popis_section:
            print(f"CHYBA: Sekcia #popis nenájdená na {full_url}.", file=sys.stderr)
            return []

        # Find the specific H2 title for the target content within the #popis section
        # Use a lambda function to match the text containing the target string (case-insensitive)
        h2_target = popis_section.find('h2', string=lambda text: text and 'životné prostredie / úradná tabuľa' in text.lower())

        if not h2_target:
             print(f"CHYBA: Nadpis 'Životné prostredie / Úradná tabuľa' nenájdený na {full_url}.", file=sys.stderr)
             return []

        # Try to find the target table immediately following the H2 title
        target_table = h2_target.find_next_sibling('table', class_='tabdoc')

        categories_data_dict = {} # Dictionary to group documents by category name

        if target_table:
            print(f"Nájdená tabuľková štruktúra pre {district_url}")
            # --- Logic for TABLE structure ---
            current_category = None
            for row in target_table.find_all('tr'):
                category_cell = row.find('td', class_='tddocup')
                if category_cell:
                    category_name = category_cell.get_text(strip=True)
                    current_category = category_name
                    if current_category and current_category not in categories_data_dict:
                        categories_data_dict[current_category] = []
                    continue

                document_name_cell = row.find('td', class_='document-name')
                if document_name_cell:
                    link = document_name_cell.find('a', class_='govuk-link')
                    if link and current_category is not None and current_category in categories_data_dict:
                        full_cell_text = document_name_cell.get_text(strip=True)
                        document_name = link.get_text(strip=True)

                        # Extract date from the text before the link's text, using '|' as a potential separator
                        date_str = None
                        link_text_index = full_cell_text.find(document_name)
                        if link_text_index != -1: # If link text is found within the cell text
                            potential_date_part = full_cell_text[:link_text_index].strip()
                            # Now, check if this potential date part contains a '|'
                            pipe_index = potential_date_part.find('|')
                            if pipe_index != -1:
                                date_str = potential_date_part[:pipe_index].strip()
                            # Alternative simpler split if structure is consistent:
                            # parts = full_cell_text.split('|', 1)
                            # if len(parts) > 1: date_str = parts[0].strip()


                        relative_url = link.get('href')
                        full_document_url = urljoin(BASE_URL, relative_url) if relative_url else None

                        if full_document_url:
                            categories_data_dict[current_category].append({
                                "datum": date_str,
                                "nazov": document_name,
                                "url": full_document_url
                            })
                        else:
                            print(f"Upozornenie: Dokument v kategórii '{current_category}' na {full_url} má odkaz bez platného 'href'.", file=sys.stderr)
        else:
            print(f"Tabuľka nenájdená, pokúšam sa parsovať odstavce pre {district_url}")
            # --- Logic for PARAGRAPH structure ---
            current_date = None
            paragraph_documents = [] # List to collect documents found in paragraphs
            # Use a default/empty category for documents from paragraphs
            default_category_name = "" # Or "Ostatné dokumenty", "Dokumenty bez kategórie" etc.

            # Find all elements that are siblings of the H2 *within* the #popis section
            # Stop when another H2 or non-paragraph element is encountered (that isn't a table already checked)
            next_siblings = h2_target.find_next_siblings()
            if len(next_siblings) == 0:
                print("Úradná tabuľa je prázdna, pod nadpisom nič nie je.")
            else:
                for element in next_siblings:
                    # Stop processing if we hit the end of relevant content (e.g., another H2)
                    if element.name == 'h2': # Or check for other structural dividers if necessary
                        break
                    if element.name != 'p':
                        # Ignore non-paragraph elements unless they signal the end of the list
                        continue


                    # Process paragraph elements
                    link = element.find('a') # Check if the paragraph contains a link

                    if link:
                        # This paragraph contains a document link
                        document_name = link.get_text(strip=True)
                        relative_url = link.get('href')
                        full_document_url = urljoin(BASE_URL, relative_url) if relative_url else None

                        if full_document_url:
                            # Append document with the last seen date and the default category
                            paragraph_documents.append({
                                "datum": current_date, # Use the last detected date
                                "nazov": document_name,
                                "url": full_document_url
                            })
                        else:
                            print(f"Upozornenie: Dokument v odstavci na {full_url} má odkaz bez platného 'href'.", file=sys.stderr)

                    elif is_potential_date_paragraph(element):
                         # This paragraph looks like a date marker and has no link
                         current_date = element.get_text(strip=True)
                         #print(f"Detekovaný dátum: {current_date}") # For debugging

                    # else: Paragraph is neither a link nor a date, ignore it (e.g., introductory text)

                # After processing all relevant paragraphs, add them under the default category
                if paragraph_documents:
                     # Add the default category with the collected documents only if documents were found
                     categories_data_dict[default_category_name] = paragraph_documents
                     print(f"Nájdené {len(paragraph_documents)} dokumentov v odstavcoch pre {district_url}")
                else:
                     print(f"Nenašli sa žiadne dokumenty v odstavcoch pre {district_url}")


        # Convert the dictionary format (category: [docs]) to the desired list format ([{"kategoria": k, "dokumenty": v}, ...])
        # Include only categories that have documents
        result_list_of_categories = [{"kategoria": k, "dokumenty": v} for k, v in categories_data_dict.items() if v]

        # Optional: Sort categories by name for consistent output order
        result_list_of_categories.sort(key=lambda x: x['kategoria'])

        return result_list_of_categories

    except requests.exceptions.Timeout:
        print(f"Chyba timeout pri sťahovaní {full_url}.", file=sys.stderr)
        raise
        # return [] # Return empty list on error
    except requests.exceptions.RequestException as e:
        print(f"Chyba pri sťahovaní {full_url}: {e}", file=sys.stderr)
        raise
        # return [] # Return empty list on error
    except Exception as e:
        print(f"Nastala neočakávaná chyba pri spracovaní {full_url}: {e}", file=sys.stderr)
        # sys.excepthook(type(e), e, e.__traceback__) # Uncomment for detailed traceback if needed
        raise
        # return []


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
                # Add a delay between districts as well, in case they are on the same server
                time.sleep(0.5) # Smaller delay between districts than between scraping attempts
                print(f"Spracovávam okres: {okres_name}")
                # Scrape the environmental board for this district.
                # This function returns a list of category blocks (e.g., [{"kategoria": "...", "dokumenty": [...]}, ...]).
                district_environmental_data = scrape_district_environmental_board(okres_url)

                # Assign the scraped category blocks data directly to the new key for this district
                okres_data['dokumenty_zivotne_prostredie'] = district_environmental_data

                # Optional: Remove the original 'url' key for the district itself if it's not needed in the output
                okres_data.pop('url', None)

            else:
                print(f"Upozornenie: Okres '{okres_name}' v kraji '{kraj_name}' nemá 'url'. Pre tento okres nebudú stiahnuté dokumenty.")
                # The 'dokumenty_zivotne_prostredie' list for this district will remain empty [] as initialized.

        # Optional: Remove the original 'url' key for the kraj itself if it's not needed in the output
        kraj_data.pop('url', None)


    # Save the output JSON
    try:
        with open(output_json_file, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)
        print(f"\nDáta boli úspešne uložené do súboru '{output_json_file}'.")
    except IOError as e:
        print(f"Chyba pri zápise do súboru '{output_json_file}': {e}", file=sys.stderr)
    except Exception as e:
         print(f"Nastala neočakávaná chyba pri ukladaní súboru: {e}", file=sys.stderr)


if __name__ == "__main__":
    # Define input and output filenames
    input_file = '1_zoznam_okresov.json'
    output_file = '2_uradne_tabule_test.json'

    main(input_file, output_file)
    #b = scrape_district_environmental_board('/?okresne-urady-klientske-centra&urad=6&odbor=10&sekcia=uradna-tabula')
    #print('b:', b)
