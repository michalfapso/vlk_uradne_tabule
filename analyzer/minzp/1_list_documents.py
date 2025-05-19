import requests
from bs4 import BeautifulSoup
import json
from urllib.parse import urljoin, urlparse, parse_qs
import sys
# import traceback # Odkomentuj pre detailnejší výpis chýb pri parsovaní

BASE_URL = 'https://www.minzp.sk'
START_URL = 'https://www.minzp.sk/uradna-tabula/priroda/'
# TARGET_H1_TEXT = "Ochrana prírody - správne konania" # Ak by sme chceli overovať nadpis

def scrape_minzp_documents():
    all_documents = []
    current_url = START_URL
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    })

    page_num = 1 # Aktuálne číslo stránky, ktorú spracovávame

    while current_url:
        print(f"Spracovávam stránku č. {page_num}: {current_url}", file=sys.stderr)
        try:
            response = session.get(current_url, timeout=10)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            print(f"Chyba pri sťahovaní stránky {current_url}: {e}", file=sys.stderr)
            break

        soup = BeautifulSoup(response.content, 'html.parser')

        # Nájdi hlavný kontajner s novinkami/dokumentmi
        news_container = soup.find('div', class_='news')

        if not news_container:
            if page_num == 1: # Ak na prvej stránke nenájdeme kontajner, je to problém
                print(f"Kontajner 'div.news' nebol nájdený na stránke {current_url}.", file=sys.stderr)
            else: # Na ďalších stránkach to môže znamenať koniec obsahu
                print(f"Kontajner 'div.news' nebol nájdený na stránke {current_url}, pravdepodobne koniec stránkovania obsahu.", file=sys.stderr)
            break
        
        document_items = news_container.find_all('div', class_='news_content', recursive=False)
        
        if not document_items and page_num == 1:
            print(f"Nenašli sa žiadne položky 'div.news_content' v 'div.news' na stránke {current_url}.", file=sys.stderr)
            # Stránkovanie by sa malo stále skontrolovať nižšie.

        for item_div in document_items:
            try:
                link_tag = item_div.find('a', recursive=False) 
                nazov_tag = item_div.find('h4')

                nazov = "N/A"
                doc_url = "N/A"

                if link_tag and link_tag.has_attr('href'):
                    relative_url = link_tag['href']
                    doc_url = urljoin(BASE_URL, relative_url)
                    if nazov_tag:
                        nazov = nazov_tag.get_text(strip=True)
                    elif link_tag.get_text(strip=True): 
                        nazov = link_tag.get_text(strip=True)
                elif nazov_tag: 
                    nazov = nazov_tag.get_text(strip=True)

                news_text_div = item_div.find('div', class_='news_text')
                datum = "N/A"
                popis = "N/A"

                if news_text_div:
                    datum_span = news_text_div.find('span', class_='news_date')
                    if datum_span:
                        datum = datum_span.get_text(strip=True)
                        # Odstránime span s dátumom z news_text_div, aby sme získali čistý popis.
                        # Toto modifikuje news_text_div na mieste, čo je v tomto cykle bezpečné.
                        datum_span.extract() 
                        popis = news_text_div.get_text(separator=' ', strip=True)
                    else:
                        # Ak nie je špecifický span pre dátum, celý text berieme ako popis
                        popis = news_text_div.get_text(separator=' ', strip=True)
                
                all_documents.append({
                    "nazov": nazov,
                    "url": doc_url,
                    "datum": datum,
                    "popis": popis
                })
            except Exception as e:
                print(f"Chyba pri spracovaní položky dokumentu: {item_div}. Chyba: {e}", file=sys.stderr)
                # traceback.print_exc(file=sys.stderr) # Pre detailnejší debug

        # Stránkovanie
        next_page_url_candidate = None
        pagination_div = soup.find('div', class_='news_pages_bottom') # alebo len 'news_pages'
        
        if pagination_div:
            target_page_to_find = page_num + 1
            page_links = pagination_div.find_all('a', href=True)
            for link in page_links:
                href = link['href']
                parsed_href = urlparse(href)
                query_params = parse_qs(parsed_href.query)
                
                if 'page' in query_params:
                    try:
                        link_page_num_str = query_params['page'][0]
                        if link_page_num_str.isdigit(): # Uisti sa, že je to číslo
                           link_page_num = int(link_page_num_str)
                           if link_page_num == target_page_to_find:
                               next_page_url_candidate = urljoin(BASE_URL, href) # Použi BASE_URL pre absolútnu URL
                               break 
                    except (ValueError, IndexError):
                        pass # Ignoruj neplatné 'page' parametre
            
        if next_page_url_candidate:
            current_url = next_page_url_candidate
            page_num += 1
        else:
            current_url = None # Koniec stránkovania

    return all_documents

if __name__ == '__main__':
    documents_data = scrape_minzp_documents()
    
    # Výstup ako JSON na štandardný výstup
    json_output = json.dumps(documents_data, indent=2, ensure_ascii=False)
    print(json_output)

    # Informácia o dokončení na stderr, aby sa nemiešala s JSON výstupom
    print(f"\nSpracovanie dokončené. Nájdených {len(documents_data)} dokumentov.", file=sys.stderr)
