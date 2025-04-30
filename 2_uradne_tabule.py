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
    Raises:
        requests.exceptions.RequestException: If a network error occurs.
        Exception: If any other parsing error occurs.
    """
    # Construct the full URL
    full_url = urljoin(BASE_URL, district_url + DEPARTMENT_SUFFIX)
    print(f"Sťahujem: {full_url}")

    # The function will now raise exceptions on error instead of returning []
    # try...except blocks are moved to the main loop for retry logic

    # Add a small delay and set timeout
    time.sleep(1) # Keep a small delay before each request

    response = requests.get(full_url, timeout=20) # Increased timeout slightly
    response.raise_for_status() # Raise an HTTPError for bad responses (4xx or 5xx)

    soup = BeautifulSoup(response.content, 'html.parser')

    # Find the section containing the main content (usually #popis)
    popis_section = soup.find('div', id='popis')
    if not popis_section:
        # Raise an exception instead of printing and returning []
        raise ValueError(f"Sekcia #popis nenájdená na {full_url}.")

    # Find the specific H2 title for the target content within the #popis section
    # Use a lambda function to match the text containing the target string (case-insensitive)
    h2_target = popis_section.find('h2', string=lambda text: text and 'životné prostredie / úradná tabuľa' in text.lower())

    if not h2_target:
         # Raise an exception instead of printing and returning []
         raise ValueError(f"Nadpis 'Životné prostredie / Úradná tabuľa' nenájdený na {full_url}.")

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
            print(f"Úradná tabuľa je prázdna (žiadne elementy pod nadpisom) pre {district_url}")
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

    # Removed the broad try...except Exception block from here; errors will propagate up


def main(input_json_file, output_json_file):
    """
    Loads input JSON, scrapes data from district environmental boards with retry logic,
    and structures the results, keeping documents nested under categories within each district.
    If scraping fails after retries, an 'error' key is added to the district data.

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
            # Remove original URL if not needed in final output (optional)
            # okres_data.pop('url', None) # Keep URL for processing, remove later if needed

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

                    print(f"Spracovávam okres: {okres_name} (Kraj: {kraj_name})")
                    try:
                        # Add a small delay between districts, especially important during retries
                        time.sleep(0.5)

                        # Call the scraping function
                        district_environmental_data = scrape_district_environmental_board(okres_url)

                        # Success: Assign data and remove any previous error marker
                        okres_data['dokumenty_zivotne_prostredie'] = district_environmental_data
                        okres_data.pop('error', None) # Remove error key if it existed
                        print(f"Okres {okres_name} úspešne spracovaný.")

                    except Exception as e:
                        error_message = f"Chyba pri spracovaní (pokus {attempt + 1}): {e}"
                        print(f"CHYBA: Okres {okres_name} - {error_message}", file=sys.stderr)
                        # Store the error message
                        okres_data['error'] = error_message
                        # Ensure document list is empty or reflects failure state
                        okres_data['dokumenty_zivotne_prostredie'] = []
                        # Add to list for potential retry
                        districts_to_retry.append(okres_data) # Keep track of failed districts

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
    for kraj_data in output_data:
        kraj_data.pop('url', None) # Remove kraj URL
        for okres_data in kraj_data.get('okresy', []):
            okres_data.pop('url', None) # Remove okres URL


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
    output_file = '2_uradne_tabule_test.json'

    main(input_file, output_file)
    # Example for testing a specific district (uncomment if needed)
    # try:
    #     b = scrape_district_environmental_board('/?okresne-urady-klientske-centra&urad=6') # Example district
    #     print('Test scrape result:', json.dumps(b, indent=2, ensure_ascii=False))
    # except Exception as e:
    #     print(f"Test scrape failed: {e}")

