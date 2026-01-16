#!/bin/bash

# analyzer/sync_github_data.sh
# Skript na stiahnutie najnovších dátových artefaktov z GitHubu pre lokálny vývoj.

# Ukončiť pri chybe
set -e

# Kontrola, či je gh CLI nainštalované
if ! command -v gh &> /dev/null; then
    echo "Chyba: 'gh' (GitHub CLI) nie je nainštalované. Nainštalujte ho a prihláste sa pomocou 'gh auth login'."
    exit 1
fi

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
BASE_DIR="$SCRIPT_DIR/.."
SCRAPED_DIR="$BASE_DIR/data/scraped"
DOCS_DIR="$BASE_DIR/data/docs"

mkdir -p "$SCRAPED_DIR"
mkdir -p "$DOCS_DIR"

echo "Hľadám posledné úspešné behy GitHub Actions..."

# 1. Stiahnutie scraped-data
echo "--- Scraped Data ---"
RUN_ID=$(gh run list --workflow "scrape.yml" --branch main --status success --limit 1 --json databaseId --jq '.[0].databaseId')
if [ -n "$RUN_ID" ]; then
    echo "Sťahujem 'scraped-data' z behu $RUN_ID..."
    gh run download "$RUN_ID" -n scraped-data -D "$SCRAPED_DIR" --clobber
else
    echo "Upozornenie: Nenašiel sa žiadny úspešný beh 'Scrape Data'."
fi

# 2. Stiahnutie gis-geojson-files
echo "--- GIS GeoJSON Files ---"
# Skúsime najprv daily workflow
GIS_RUN_ID=$(gh run list --workflow "daily-scrape-analyze-deploy.yml" --branch main --status success --limit 1 --json databaseId --jq '.[0].databaseId')
if [ -z "$GIS_RUN_ID" ]; then
    # Skúsime process workflow
    GIS_RUN_ID=$(gh run list --workflow "process.yml" --branch main --status success --limit 1 --json databaseId --jq '.[0].databaseId')
fi

if [ -n "$GIS_RUN_ID" ]; then
    echo "Sťahujem 'gis-geojson-files' z behu $GIS_RUN_ID..."
    gh run download "$GIS_RUN_ID" -n gis-geojson-files -D "$BASE_DIR" --clobber
else
    echo "Upozornenie: Nenašiel sa žiadny úspešný beh produkujúci 'gis-geojson-files'."
fi

echo "--- Synchronizácia dokončená ---"
echo "Dáta sú pripravené v data/scraped a data/docs."
