# analyzer/run_scraping.py
import subprocess
import os
import sys

def run_scraper(script_path, output_path):
    """Spustí daný scraper skript a uloží jeho výstup."""
    script_full_path = os.path.abspath(script_path)
    output_full_path = os.path.abspath(output_path)
    
    print(f"Spúšťam scraper: {script_full_path}")
    try:
        with open(output_full_path, 'w', encoding='utf-8') as f_out:
            # Spustíme skript ako podproces a presmerujeme jeho stdout do súboru
            result = subprocess.run(
                [sys.executable, script_full_path],
                capture_output=True,
                text=True,
                check=True,
                encoding='utf-8'
            )
            f_out.write(result.stdout)
        print(f"Výstup scrapera bol úspešne uložený do: {output_full_path}")
        return True
    except FileNotFoundError:
        print(f"Chyba: Scraper skript nebol nájdený na ceste: {script_full_path}", file=sys.stderr)
        return False
    except subprocess.CalledProcessError as e:
        print(f"Chyba pri spustení scrapera {script_full_path}:", file=sys.stderr)
        print(f"Exit code: {e.returncode}", file=sys.stderr)
        print(f"Stdout: {e.stdout}", file=sys.stderr)
        print(f"Stderr: {e.stderr}", file=sys.stderr)
        return False
    except Exception as e:
        print(f"Neočekávaná chyba pri spracovaní scrapera {script_full_path}: {e}", file=sys.stderr)
        return False

def main():
    """
    Hlavná funkcia, ktorá spúšťa všetky scrapovacie skripty.
    """
    # Definovanie ciest k scraperom a ich výstupným súborom
    SCRAPERS = {
        "minv_regions": {
            "script": "analyzer/scrapers/minv_1_regions.py",
            "output": "data/scraped/minv_1_regions.json"
        },
        "minv_documents": {
            "script": "analyzer/scrapers/minv_2_documents.py",
            "input": "data/scraped/minv_1_regions.json", # Tento skript potrebuje vstup
            "output": "data/scraped/minv_2_documents.json"
        },
        "minzp_documents": {
            "script": "analyzer/scrapers/minzp_documents.py",
            "output": "data/scraped/minzp_documents.json"
        }
    }
    
    # Vytvorenie adresára pre výstupy, ak neexistuje
    os.makedirs("data/scraped", exist_ok=True)
    
    # Zoznam neúspešných scraperov
    failed_scrapers = []

    # 1. Spustenie minv_1_regions
    print("--- Krok 1: Získavanie zoznamu regiónov a okresov z minv.sk ---")
    if not run_scraper(SCRAPERS["minv_regions"]["script"], SCRAPERS["minv_regions"]["output"]):
        failed_scrapers.append("minv_regions")
        # Ak tento zlyhá, minv_documents nemôže bežať
        print("Chyba: Získavanie regiónov zlyhalo, krok 2 (dokumenty minv) bude preskočený.", file=sys.stderr)
    else:
        # 2. Spustenie minv_2_documents, len ak krok 1 uspel
        print("\n--- Krok 2: Získavanie zoznamu dokumentov z minv.sk ---")
        minv_docs_scraper = SCRAPERS["minv_documents"]
        try:
            subprocess.run(
                [
                    sys.executable, 
                    os.path.abspath(minv_docs_scraper["script"]),
                    '--input', os.path.abspath(minv_docs_scraper["input"]),
                    '--output', os.path.abspath(minv_docs_scraper["output"])
                ],
                check=True,
                capture_output=True,
                text=True,
                encoding='utf-8'
            )
            print(f"Výstup scrapera bol úspešne uložený do: {os.path.abspath(minv_docs_scraper['output'])}")
        except subprocess.CalledProcessError as e:
            print(f"Chyba pri spustení scrapera {minv_docs_scraper['script']}:", file=sys.stderr)
            print(f"Stderr: {e.stderr}", file=sys.stderr)
            failed_scrapers.append("minv_documents")

    # 3. Spustenie minzp_documents
    print("\n--- Krok 3: Získavanie zoznamu dokumentov z minzp.sk ---")
    if not run_scraper(SCRAPERS["minzp_documents"]["script"], SCRAPERS["minzp_documents"]["output"]):
        failed_scrapers.append("minzp_documents")
        
    print("\n--- Zhrnutie scrapingu ---")
    if not failed_scrapers:
        print("Scraping bol úspešne dokončený pre všetky zdroje.")
    else:
        print(f"Scraping bol dokončený s chybami. Zlyhali nasledujúce skripty: {', '.join(failed_scrapers)}", file=sys.stderr)
        sys.exit(1) # Ukončíme s chybovým kódom, aby GitHub Action vedela, že niečo zlyhalo

if __name__ == "__main__":
    main()
