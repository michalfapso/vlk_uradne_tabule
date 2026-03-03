#!/bin/bash

# analyzer/sync_github_data.sh
# Skript na stiahnutie najnovších dátových artefaktov z GitHubu pre lokálny vývoj.

# Ukončiť pri chybe
set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
BASE_DIR="$SCRIPT_DIR/.."

echo "--- Synchronizácia dátového submodulu ---"

cd "$BASE_DIR"

# Inicializácia submodulov (ak ešte nie sú)
git submodule init

# Aktualizácia submodulu na najnovšiu verziu z remote repository
echo "Sťahujem najnovšie dáta z data repozitára..."
git submodule update --remote --merge

echo "--- Synchronizácia dokončená ---"
echo "Dáta sú pripravené v adresári data/."
