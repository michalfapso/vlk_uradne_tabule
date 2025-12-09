
import json
import os
import sys
import shutil
from datetime import datetime, timedelta

# Add shared module path
script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(script_dir, 'shared'))

from get_doc_id import get_doc_id

def prune_gis_files():
    print("Starting GIS files pruning...")
    base_dir = os.path.abspath(os.path.join(script_dir, '..'))
    scraped_data_dir = os.path.join(base_dir, 'data', 'scraped')
    docs_output_dir = os.path.join(base_dir, 'data', 'docs')
    
    unified_new_path = os.path.join(scraped_data_dir, 'unified_new.json')
    
    if not os.path.exists(unified_new_path):
        print("unified_new.json not found. Skipping pruning.")
        return

    try:
        with open(unified_new_path, 'r', encoding='utf-8') as f:
            unified_docs = json.load(f)
    except Exception as e:
        print(f"Error loading unified_new.json: {e}")
        return

    # Create a map of doc_id -> date
    active_docs_dates = {}
    for doc in unified_docs:
        url = doc.get('url')
        if not url:
            continue
        
        doc_id = get_doc_id(url)
        if not doc_id:
            continue

        date_str = doc.get('original_data', {}).get('datum')
        if date_str:
            try:
                doc_date = datetime.strptime(date_str, '%Y-%m-%d')
                active_docs_dates[doc_id] = doc_date
            except ValueError:
                pass # Invalid date format, ignore for pruning purposes (or keep safe)
        else:
             # If no date, we assume it's valid/active and don't prune based on date
             # We use a far future date or just None to indicate "keep"
             pass

    # Threshold date
    threshold_date = datetime.now() - timedelta(days=30)
    print(f"Pruning GIS files for documents older than {threshold_date.strftime('%Y-%m-%d')}...")

    deleted_count = 0
    kept_count = 0

    # Walk through the docs directory
    for root, dirs, files in os.walk(docs_output_dir):
        if 'gis.geojson' in files:
            # Extract doc_id from path. 
            # Path structure is typically: .../region/district/doc_id
            doc_id = os.path.basename(root)
            
            gis_file_path = os.path.join(root, 'gis.geojson')
            
            should_delete = False
            reason = ""

            if doc_id not in active_docs_dates:
                # Document is not in the current active list (orphaned)
                # Check if it really is an ID folder or just some coincidence.
                # Assuming folder name is the ID.
                # However, get_doc_id logic might be complex. 
                # If we can't match it to an active doc, we assume it's orphaned.
                # BUT, let's be careful. If unified_new.json is partial? 
                # No, unified_new.json should contain ALL currently scraped documents.
                should_delete = True
                reason = "Orphaned (not in current scrape)"
            else:
                doc_date = active_docs_dates[doc_id]
                if doc_date and doc_date < threshold_date:
                    should_delete = True
                    reason = f"Old (date {doc_date.strftime('%Y-%m-%d')})"
            
            if should_delete:
                print(f"Deleting {gis_file_path} - {reason}")
                try:
                    os.remove(gis_file_path)
                    deleted_count += 1
                except OSError as e:
                    print(f"Error deleting {gis_file_path}: {e}")
            else:
                kept_count += 1

    print(f"Pruning finished. Deleted: {deleted_count}, Kept: {kept_count}")

if __name__ == "__main__":
    prune_gis_files()
