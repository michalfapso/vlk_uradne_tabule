#!/bin/bash

# analyzer/local_process.sh
# Skript na lokálne spustenie spracovania dokumentov.

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
BASE_DIR="$SCRIPT_DIR/.."

# 0. Synchronizácia dát (voliteľné, ak chceš začať s najnovšími dátami z GitHubu)
echo "Synchronizujem dáta..."
bash "$SCRIPT_DIR/sync_github_data.sh"

# 1. Aktivácia prostredia (ak existuje)
if [ -d "$SCRIPT_DIR/.venv" ]; then
    source "$SCRIPT_DIR/.venv/bin/activate"
fi

# 2. Spustenie scrapingu (voliteľné)
echo "Spúšťam scraping..."
python "$SCRIPT_DIR/run_scraping.py"

# 3. Spustenie hlavného spracovania
echo "Spúšťam spracovanie dokumentov..."
python -u "$SCRIPT_DIR/run_processing.py"

# 4. Prerezanie starých GIS súborov
#echo "Premazávam staré GIS súbory..."
#python -u "$SCRIPT_DIR/prune_gis_files.py"

# 5. Príprava dát pre webstránku
echo "Pripravujem dáta pre webstránku..."
bash "$SCRIPT_DIR/prepare_website_data.sh"

echo "Hotovo."
