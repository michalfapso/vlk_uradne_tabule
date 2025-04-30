# -*- coding: utf-8 -*-
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
# Suffix for the specific environmental board
DEPARTMENT_SUFFIX = "&odbor=10&sekcia=uradna-tabula"
# Suffix for the general board (fallback)
GENERAL_BOARD_SUFFIX = "&sekcia=uradna-tabula"

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
    Scrapes the public notice board for a given district URL.
    Tries the specific environmental board first. If it returns 404,
    falls back to the general public notice board.
    Handles both table-based and paragraph-based structures.
    Extracts categories (or uses empty for paragraphs), document name, date, and URL.

    Args:
        district_url (str): The base URL for the district page (e.g., "/?okresne-urady-klientske-centra&urad=35").

    Returns:
        tuple: A tuple containing:
            - list: A list of dictionaries, where each dictionary represents a category
                    and contains a list of documents. Each document dictionary includes
                    'datum', 'nazov', and 'url'. Returns an empty list if the page,
                    the relevant content, or data cannot be found or parsed.
            - str: The URL from which the data was successfully scraped.
    Raises:
        requests.exceptions.RequestException: If a network error occurs (after potential fallback).
        requests.exceptions.HTTPError: If a non-404 HTTP error occurs, or if the fallback also fails.
        ValueError: If expected HTML structure (like #popis or relevant H2) is missing.
        Exception: If any other parsing error occurs.
    """
    # Construct the initial URL for the specific environmental board
    specific_url = urljoin(BASE_URL, district_url + DEPARTMENT_SUFFIX)
    print(f"Skúšam špecifickú URL: {specific_url}")

    response = None
    request_url = specific_url # Keep track of the URL actually requested

    # Add a small delay and set timeout
    time.sleep(1) # Keep a small delay before each request

    try:
        response = requests.get(specific_url, timeout=20) # Increased timeout slightly
        response.raise_for_status() # Raise an HTTPError for bad responses (4xx or 5xx)
        print(f"Úspešne stiahnuté: {specific_url}")
        target_h2_text_specific = 'životné prostredie / úradná tabuľa'
        target_h2_text_general = None # Not needed if specific URL worked

    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            print(f"Špecifická URL {specific_url} vrátila 404. Skúšam všeobecnú úradnú tabuľu.")
            # Construct the fallback URL for the general board
            fallback_url = urljoin(BASE_URL, district_url + GENERAL_BOARD_SUFFIX)
            request_url = fallback_url # Update the URL we are now trying
            print(f"Skúšam všeobecnú URL: {fallback_url}")

            time.sleep(1) # Delay before fallback request

            # Make the second request for the general board
            response = requests.get(fallback_url, timeout=20)
            # Raise status for the *fallback* request. If this fails, the exception propagates.
            response.raise_for_status()
            print(f"Úspešne stiahnuté (všeobecná): {fallback_url}")
            # Set the expected H2 text for the general board
            target_h2_text_specific = None # Specific H2 won't be present
            target_h2_text_general = 'úradná tabuľa'

        else:
            # If the error was not 404, re-raise it
            print(f"Chyba pri sťahovaní {specific_url}: {e}")
            raise e
    except requests.exceptions.RequestException as e:
         # Handle connection errors, timeouts etc. for the first request
         print(f"Chyba pripojenia pri sťahovaní {specific_url}: {e}")
         raise e


    # --- Parsing starts here, using the 'response' from the successful request ---
    soup = BeautifulSoup(response.content, 'html.parser')

    # Find the section containing the main content (usually #popis)
    popis_section = soup.find('div', id='popis')
    if not popis_section:
        # Raise an exception instead of printing and returning []
        raise ValueError(f"Sekcia #popis nenájdená na {request_url}.")

    # Find the specific H2 title for the target content within the #popis section
    h2_target = None
    if target_h2_text_specific:
        # Try finding the specific H2 first (if specific URL was used)
        h2_target = popis_section.find('h2', string=lambda text: text and target_h2_text_specific in text.lower())

    if not h2_target and target_h2_text_general:
         # If specific not found (or fallback URL was used), try the general H2
         print(f"Hľadám všeobecný nadpis '{target_h2_text_general}' na {request_url}")
         # Use strip() and exact match (case-insensitive) for the general title
         h2_target = popis_section.find('h2', string=lambda text: text and text.strip().lower() == target_h2_text_general)

    if not h2_target:
         # If neither relevant H2 is found, raise the error
         error_msg = f"Relevantný nadpis ('{target_h2_text_specific or 'Životné prostredie / Úradná tabuľa'}' ani '{target_h2_text_general or 'Úradná tabuľa'}') nenájdený na {request_url}."
         raise ValueError(error_msg)
    else:
        print(f"Nájdený nadpis: '{h2_target.get_text(strip=True)}'")


    # Try to find the target table immediately following the H2 title
    target_table = h2_target.find_next_sibling('table', class_='tabdoc')

    categories_data_dict = {} # Dictionary to group documents by category name

    if target_table:
        print(f"Nájdená tabuľková štruktúra pre {district_url} na {request_url}")
        # --- Logic for TABLE structure ---
        current_category = None
        for row in target_table.find_all('tr'):
            category_cell = row.find('td', class_='tddocup')
            if category_cell:
                category_name = category_cell.get_text(strip=True)
                # Handle potential empty category names from merged cells
                if category_name:
                    current_category = category_name
                    if current_category not in categories_data_dict:
                        categories_data_dict[current_category] = []
                # If category_name is empty, we assume it continues the previous category
                elif current_category is None:
                    # Edge case: first row has no category name? Use a default.
                    current_category = "Nezaradené (tabuľka)"
                    if current_category not in categories_data_dict:
                        categories_data_dict[current_category] = []

                continue # Skip to next row after processing category cell

            document_name_cell = row.find('td', class_='document-name')
            if document_name_cell:
                link = document_name_cell.find('a', class_='govuk-link')
                # Ensure we have a category context before adding documents
                if link and current_category is not None and current_category in categories_data_dict:
                    full_cell_text = document_name_cell.get_text(strip=True)
                    document_name = link.get_text(strip=True)

                    # Extract date from the text before the link's text, using '|' as a potential separator
                    date_str = None
                    link_text_index = full_cell_text.find(document_name)
                    if link_text_index > 0: # Check if link text is found *and* there's text before it
                        potential_date_part = full_cell_text[:link_text_index].strip()
                        # Remove trailing '|' if present
                        if potential_date_part.endswith('|'):
                            potential_date_part = potential_date_part[:-1].strip()
                        # Basic check if it looks like a date (can be improved with regex if needed)
                        if '.' in potential_date_part and len(potential_date_part) <= 12: # Simple heuristic
                             date_str = potential_date_part
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
                        print(f"Upozornenie: Dokument v kategórii '{current_category}' na {request_url} má odkaz bez platného 'href'.", file=sys.stderr)
    else:
        print(f"Tabuľka nenájdená, pokúšam sa parsovať odstavce pre {district_url} na {request_url}")
        # --- Logic for PARAGRAPH structure ---
        current_date = None
        paragraph_documents = [] # List to collect documents found in paragraphs
        # Use a default/empty category for documents from paragraphs
        default_category_name = "" # Or "Ostatné dokumenty", "Dokumenty bez kategórie" etc.

        # Find all elements that are siblings of the H2 *within* the #popis section
        # Stop when another H2 or non-paragraph element is encountered (that isn't a table already checked)
        next_siblings = h2_target.find_next_siblings()
        if len(next_siblings) == 0:
            print(f"Úradná tabuľa je prázdna (žiadne elementy pod nadpisom) pre {district_url} na {request_url}")
        else:
            processed_paragraph = False # Flag to check if any relevant paragraphs were found
            for element in next_siblings:
                # Stop processing if we hit the end of relevant content (e.g., another H2)
                if element.name == 'h2': # Or check for other structural dividers if necessary
                    break
                # Only process 'p' tags directly under the H2 section
                if element.name != 'p':
                    # Allow specific non-p tags if needed, otherwise ignore
                    # Example: Sometimes <hr> might appear, ignore it.
                    # if element.name not in ['hr', 'br']: # Example
                    #    print(f"Ignorujem element '{element.name}' za nadpisom.")
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
                        processed_paragraph = True # Mark that we found a document
                    else:
                        print(f"Upozornenie: Dokument v odstavci na {request_url} má odkaz bez platného 'href'.", file=sys.stderr)

                elif is_potential_date_paragraph(element):
                     # This paragraph looks like a date marker and has no link
                     current_date = element.get_text(strip=True)
                     processed_paragraph = True # Mark that we found a date
                     #print(f"Detekovaný dátum: {current_date}") # For debugging

                # else: Paragraph is neither a link nor a date, ignore it (e.g., introductory text)

            # After processing all relevant paragraphs, add them under the default category
            if paragraph_documents:
                 # Add the default category with the collected documents only if documents were found
                 categories_data_dict[default_category_name] = paragraph_documents
                 print(f"Nájdené {len(paragraph_documents)} dokumentov v odstavcoch pre {district_url} na {request_url}")
            elif processed_paragraph:
                 # We found dates or other paragraphs but no actual document links
                 print(f"Nenašli sa žiadne odkazy na dokumenty v odstavcoch (možno len dátumy?) pre {district_url} na {request_url}")
            else:
                 # No relevant paragraphs found at all
                 print(f"Nenašli sa žiadne relevantné odstavce (dátumy ani dokumenty) pre {district_url} na {request_url}")


    # Convert the dictionary format (category: [docs]) to the desired list format ([{"kategoria": k, "dokumenty": v}, ...])
    # Include only categories that have documents
    result_list_of_categories = [{"kategoria": k, "dokumenty": v} for k, v in categories_data_dict.items() if v]

    # Optional: Sort categories by name for consistent output order
    result_list_of_categories.sort(key=lambda x: x['kategoria'])

    # *** ZMENA: Vrátiť aj request_url ***
    return result_list_of_categories, request_url

    # Removed the broad try...except Exception block from here; errors will propagate up


def main(input_json_file, output_json_file):
    """
    Loads input JSON, scrapes data from district environmental boards with retry logic,
    and structures the results, keeping documents nested under categories within each district.
    If scraping fails after retries, an 'error' key is added to the district data.
    The source URL used for scraping is also added.

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

    # Initialize the structure for all districts before starting the processing loop
    for kraj_data in output_data:
        for okres_data in kraj_data.get('okresy', []):
            # Initialize with an empty list, will be populated on success
            okres_data['dokumenty_zivotne_prostredie'] = []
            # *** ZMENA: Inicializovať kľúč pre zdrojovú URL ***
            okres_data['url_tabule'] = None
            # Keep URL for processing, remove later if needed
            # okres_data.pop('url', None)

    # --- Retry Logic ---
    retry_delays = [10, 60, 400] # Delays in seconds
    max_attempts = len(retry_delays) + 1 # Initial attempt + retries

    for attempt in range(max_attempts):
        districts_to_retry = []
        print(f"\n--- Pokus {attempt + 1}/{max_attempts} ---")

        # Iterate through kraje and okresy
        for kraj_data in output_data:
            kraj_name = kraj_data.get('kraj', 'Neznámy kraj')
            okresy = kraj_data.get('okresy', [])

            for okres_data in okresy:
                okres_name = okres_data.get('nazov', 'Neznámy okres')
                okres_url = okres_data.get('url')

                # On first attempt, process all. On subsequent attempts, only process those with an 'error' key.
                if attempt == 0 or 'error' in okres_data:
                    if not okres_url:
                        if attempt == 0: # Only report missing URL on the first pass
                             print(f"Upozornenie: Okres '{okres_name}' v kraji '{kraj_name}' nemá 'url'. Pre tento okres nebudú stiahnuté dokumenty.")
                             okres_data['error'] = "Chýba URL okresu" # Mark as error so it's not retried unnecessarily
                        continue # Skip this district if no URL

                    print(f"\nSpracovávam okres: {okres_name} (Kraj: {kraj_name})")
                    try:
                        # Add a small delay between districts, especially important during retries
                        time.sleep(0.5)

                        # *** ZMENA: Získať dáta aj zdrojovú URL ***
                        # Call the scraping function (which now includes fallback logic)
                        district_environmental_data, source_url = scrape_district_environmental_board(okres_url)

                        # Success: Assign data and remove any previous error marker
                        okres_data['url_tabule'] = source_url
                        okres_data['dokumenty_zivotne_prostredie'] = district_environmental_data
                        okres_data.pop('error', None) # Remove error key if it existed
                        print(f"Okres {okres_name} úspešne spracovaný (zdroj: {source_url}).") # Pridaná informácia o zdroji

                    except (requests.exceptions.RequestException, requests.exceptions.HTTPError, ValueError) as e:
                        # Catch specific errors from scraping function (network, HTTP, parsing structure)
                        error_message = f"Chyba pri spracovaní (pokus {attempt + 1}): {type(e).__name__} - {e}"
                        print(f"CHYBA: Okres {okres_name} - {error_message}", file=sys.stderr)
                        # Store the error message
                        okres_data['error'] = error_message
                        okres_data['url_tabule'] = None
                        # Ensure document list is empty or reflects failure state
                        okres_data['dokumenty_zivotne_prostredie'] = []
                        # Add to list for potential retry
                        districts_to_retry.append(okres_data) # Keep track of failed districts
                    except Exception as e:
                        # Catch any other unexpected errors during scraping
                        error_message = f"Neočakávaná chyba pri spracovaní (pokus {attempt + 1}): {type(e).__name__} - {e}"
                        print(f"CHYBA: Okres {okres_name} - {error_message}", file=sys.stderr)
                        okres_data['error'] = error_message
                        okres_data['url_tabule'] = None
                        okres_data['dokumenty_zivotne_prostredie'] = []
                        # *** ZMENA: Nechať zdrojovú URL ako None ***
                        districts_to_retry.append(okres_data)


        # --- End of pass through all districts ---

        # Check if there are districts that failed in this pass
        if not districts_to_retry:
            print("\nÚspech: Všetky okresy spracované (alebo chyby vyriešené pri tomto pokuse).")
            break # Exit the retry loop if no errors occurred in this pass

        # If errors remain and more attempts are left
        if attempt < len(retry_delays):
            delay = retry_delays[attempt]
            print(f"\nChyby pretrvávajú pre {len(districts_to_retry)} okresov. Nasleduje pokus č. {attempt + 2} po {delay} sekundách...")
            time.sleep(delay)
        else:
            # This was the last attempt
            print(f"\nCHYBA: Po {max_attempts} pokusoch pretrvávajú chyby pre {len(districts_to_retry)} okresov. Tieto okresy budú mať v JSON výstupe záznam o chybe.")
            # The loop will end naturally

    # --- Post-processing: Clean up URLs if desired ---
    # for kraj_data in output_data:
    #     kraj_data.pop('url', None) # Remove kraj URL
    #     for okres_data in kraj_data.get('okresy', []):
    #         okres_data.pop('url', None) # Remove okres URL


    # Save the final output JSON
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
    # Use a different name to avoid overwriting the test file during development
    # output_file = '2_uradne_tabule_test.json' # Original test name
    output_file = '2_uradne_tabule_vystup.json' # New output name

    main(input_file, output_file)
    # Example for testing a specific district (uncomment if needed)
    # try:
    #     # Test a district likely needing fallback (e.g., Bratislava)
    #     # Bratislava URL from 1_zoznam_okresov.json might be /?okresne-urady-klientske-centra&urad=1
    #     # Test with a known working one (if any) e.g. '/?okresne-urady-klientske-centra&urad=6'
    #     # Test with one likely using paragraphs (if known)
    #     test_district_url = '/?okresne-urady-klientske-centra&urad=1' # Example: Bratislava
    #     print(f"\n--- Testujem špecifický okres: {test_district_url} ---")
    #     b, source = scrape_district_environmental_board(test_district_url) # *** ZMENA: Získať aj URL ***
    #     print('Test scrape result:', json.dumps(b, indent=2, ensure_ascii=False))
    #     print(f'Test scrape source URL: {source}') # *** ZMENA: Vypísať URL ***
    # except Exception as e:
    #     print(f"Test scrape failed for {test_district_url}: {e}", file=sys.stderr)

