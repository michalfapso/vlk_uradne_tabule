# analyzer/run_scraping.py
import subprocess
import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.join(SCRIPT_DIR, "..")

def run_scraper_with_args(scraper_name, scraper_info):
    """
    Spustí scraper skript s argumentmi, vypisuje jeho výstup v reálnom čase
    a vracia True/False podľa úspešnosti.
    """
    script_path = os.path.abspath(scraper_info["script"])
    
    command = [sys.executable, script_path]
    if "input" in scraper_info:
        command.extend(['--input', os.path.abspath(scraper_info["input"])])
    if "output" in scraper_info:
        command.extend(['--output', os.path.abspath(scraper_info["output"])])

    print(f"Spúšťam scraper: {scraper_name}")
    try:
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding='utf-8',
            bufsize=1
        )

        # Čítame a vypisujeme výstup v reálnom čase
        for line in process.stdout:
            sys.stdout.write(line)

        return_code = process.wait()
        if return_code != 0:
            raise subprocess.CalledProcessError(return_code, command)

        print(f"\nScraper {scraper_name} úspešne zbehol.")
        return True
    except FileNotFoundError:
        print(f"Chyba: Scraper skript nebol nájdený na ceste: {script_path}", file=sys.stderr)
        return False
    except subprocess.CalledProcessError as e:
        print(f"\nChyba pri spustení scrapera {scraper_name}:", file=sys.stderr)
        print(f"Exit code: {e.returncode}", file=sys.stderr)
        return False
    except Exception as e:
        print(f"\nNeočekávaná chyba pri spracovaní scrapera {scraper_name}: {e}", file=sys.stderr)
        return False

def main():
    """
    Hlavná funkcia, ktorá spúšťa všetky scrapovacie skripty.
    """
    SCRAPERS = {
        "minv_regions": {
            "script": f"{ROOT_DIR}/analyzer/scrapers/minv_1_regions.py",
            "output": f"{ROOT_DIR}/data/scraped/minv_1_regions.json"
        },
        "minv_documents": {
            "script": f"{ROOT_DIR}/analyzer/scrapers/minv_2_documents.py",
            "input" : f"{ROOT_DIR}/data/scraped/minv_1_regions.json",
            "output": f"{ROOT_DIR}/data/scraped/minv_2_documents.json"
        },
        "minzp_documents": {
            "script": f"{ROOT_DIR}/analyzer/scrapers/minzp_documents.py",
            "output": f"{ROOT_DIR}/data/scraped/minzp_documents.json"
        }
    }
    
    os.makedirs(f"{ROOT_DIR}/data/scraped", exist_ok=True)
    
    failed_scrapers = []

    # 1. Spustenie minv_1_regions
    print("--- Krok 1: Získavanie zoznamu regiónov a okresov z minv.sk ---")
    if not run_scraper_with_args("minv_regions", SCRAPERS["minv_regions"]):
        failed_scrapers.append("minv_regions")
        print("Chyba: Získavanie regiónov zlyhalo, krok 2 (dokumenty minv) bude preskočený.", file=sys.stderr)
    else:
        # 2. Spustenie minv_2_documents, len ak krok 1 uspel
        print("\n--- Krok 2: Získavanie zoznamu dokumentov z minv.sk ---")
        if not run_scraper_with_args("minv_documents", SCRAPERS["minv_documents"]):
            failed_scrapers.append("minv_documents")

    # 3. Spustenie minzp_documents
    print("\n--- Krok 3: Získavanie zoznamu dokumentov z minzp.sk ---")
    if not run_scraper_with_args("minzp_documents", SCRAPERS["minzp_documents"]):
        failed_scrapers.append("minzp_documents")
        
    print("\n--- Zhrnutie scrapingu ---")
    if not failed_scrapers:
        print("Scraping bol úspešne dokončený pre všetky zdroje.")
    else:
        print(f"Scraping bol dokončený s chybami. Zlyhali nasledujúce skripty: {', '.join(failed_scrapers)}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
