#!/bin/bash
# analyzer/prepare_website_data.sh
# Skript na prípravu dát pre webstránku (sploštenie adresárovej štruktúry).

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
BASE_DIR="$SCRIPT_DIR/.."
DOCS_DIR="$BASE_DIR/data/docs"
WEBSITE_PUBLIC_DATA_DIR="$BASE_DIR/website/public/data"

echo "Pripravujem dáta pre webstránku v: $WEBSITE_PUBLIC_DATA_DIR"

mkdir -p "$WEBSITE_PUBLIC_DATA_DIR"

if [ -d "$DOCS_DIR" ]; then
    # Používame -print0 a read -d '' na bezpečné spracovanie mien súborov s medzerami
    #find "$DOCS_DIR" -mindepth 4 -maxdepth 4 -type d -print0 | while IFS= read -r -d '' dir; do
    find "$DOCS_DIR" -type f -name 'gis.geojson' -print0 | while IFS= read -r -d '' f_geojson; do
        dir=$(dirname "$f_geojson")
        docid=$(basename "$dir")
        target_dir="$WEBSITE_PUBLIC_DATA_DIR/$docid"
	echo "f_geojson:$f_geojson dir:$dir docid:$docid"
        
        # Vytvoríme cieľový adresár
        mkdir -p "$target_dir"
        
        # Skopírujeme gis subor
        cp "$f_geojson" "$target_dir/"
    done
    echo "Dáta boli úspešne sploštené."
else
    echo "Varovanie: Adresár $DOCS_DIR neexistuje."
fi
