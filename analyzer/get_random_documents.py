import json
import random
import argparse
import os
from typing import List, Dict, Any, Tuple

def collect_all_documents(data: List[Dict[str, Any]]) -> List[Tuple[Dict, Dict, Dict, Dict]]:
    """
    Collects all documents from the nested structure along with their context.

    Args:
        data: The loaded JSON data (list of kraje).

    Returns:
        A list of tuples, where each tuple contains:
        (kraj_info, okres_info, kategoria_info, document_info)
    """
    all_docs_with_context = []
    for kraj in data:
        kraj_base_info = {'kraj': kraj['kraj'], 'url': kraj['url']}
        for okres in kraj.get('okresy', []):
            okres_base_info = {'nazov': okres['nazov'], 'url': okres['url']}
            for kategoria_obj in okres.get('dokumenty_zivotne_prostredie', []):
                kategoria_base_info = {'kategoria': kategoria_obj['kategoria']}
                for doc in kategoria_obj.get('dokumenty', []):
                    all_docs_with_context.append(
                        (kraj_base_info, okres_base_info, kategoria_base_info, doc)
                    )
    return all_docs_with_context

def build_output_structure(selected_docs_with_context: List[Tuple[Dict, Dict, Dict, Dict]]) -> List[Dict[str, Any]]:
    """
    Builds the output JSON structure from the selected documents and their context.

    Args:
        selected_docs_with_context: A list of tuples containing context and document info.

    Returns:
        A list of kraje dictionaries in the desired output format.
    """
    output_kraje = {} # Use dict for easier lookup by kraj name

    for kraj_info, okres_info, kategoria_info, doc_info in selected_docs_with_context:
        kraj_name = kraj_info['kraj']
        okres_name = okres_info['nazov']
        kategoria_name = kategoria_info['kategoria']

        # Ensure Kraj exists
        if kraj_name not in output_kraje:
            output_kraje[kraj_name] = {
                'kraj': kraj_name,
                'url': kraj_info['url'],
                'okresy': {} # Use dict for easier lookup by okres name
            }

        # Ensure Okres exists within Kraj
        if okres_name not in output_kraje[kraj_name]['okresy']:
             output_kraje[kraj_name]['okresy'][okres_name] = {
                 'nazov': okres_name,
                 'url': okres_info['url'],
                 'dokumenty_zivotne_prostredie': {} # Use dict for easier lookup by kategoria name
             }

        # Ensure Kategoria exists within Okres
        okres_ref = output_kraje[kraj_name]['okresy'][okres_name]
        if kategoria_name not in okres_ref['dokumenty_zivotne_prostredie']:
            okres_ref['dokumenty_zivotne_prostredie'][kategoria_name] = {
                'kategoria': kategoria_name,
                'dokumenty': []
            }

        # Add the document to the Kategoria
        okres_ref['dokumenty_zivotne_prostredie'][kategoria_name]['dokumenty'].append(doc_info)

    # Convert the nested dictionaries back to the original list structure
    final_output = []
    for kraj_data in output_kraje.values():
        kraj_entry = {
            'kraj': kraj_data['kraj'],
            'url': kraj_data['url'],
            'okresy': []
        }
        for okres_data in kraj_data['okresy'].values():
            okres_entry = {
                'nazov': okres_data['nazov'],
                'url': okres_data['url'],
                'dokumenty_zivotne_prostredie': []
            }
            for kategoria_data in okres_data['dokumenty_zivotne_prostredie'].values():
                 # Sort documents by date within category (optional, but nice)
                kategoria_data['dokumenty'].sort(key=lambda x: x.get('datum', ''))
                okres_entry['dokumenty_zivotne_prostredie'].append(kategoria_data)
            # Sort categories by name within okres (optional)
            okres_entry['dokumenty_zivotne_prostredie'].sort(key=lambda x: x.get('kategoria', ''))
            kraj_entry['okresy'].append(okres_entry)
        # Sort okresy by name within kraj (optional)
        kraj_entry['okresy'].sort(key=lambda x: x.get('nazov', ''))
        final_output.append(kraj_entry)
    # Sort kraje by name (optional)
    final_output.sort(key=lambda x: x.get('kraj', ''))

    return final_output


def main():
    parser = argparse.ArgumentParser(description='Randomly select N documents from a JSON file while preserving structure.')
    parser.add_argument('-i', '--input', required=True, help='Path to the input JSON file.')
    parser.add_argument('-o', '--output', required=True, help='Path to the output JSON file.')
    parser.add_argument('-n', '--num-docs', type=int, required=True, help='Number of documents to select randomly.')
    parser.add_argument('--seed', type=int, default=None, help='Optional random seed for reproducibility.')


    args = parser.parse_args()

    input_path = os.path.abspath(args.input)
    output_path = os.path.abspath(args.output)
    num_to_select = args.num_docs

    if args.seed is not None:
        print(f"Using random seed: {args.seed}")
        random.seed(args.seed)

    # Validate inputs
    if not os.path.exists(input_path):
        print(f"Error: Input file not found at {input_path}")
        return
    if num_to_select <= 0:
        print("Error: Number of documents to select must be positive.")
        return

    # Load data
    try:
        with open(input_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        print(f"Successfully loaded data from {input_path}")
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON from {input_path}: {e}")
        return
    except Exception as e:
        print(f"An error occurred while reading {input_path}: {e}")
        return

    # Collect all documents
    all_docs = collect_all_documents(data)
    total_docs = len(all_docs)
    print(f"Found {total_docs} documents in total.")

    if total_docs == 0:
        print("No documents found in the input file. Output file will be empty.")
        selected_docs_with_context = []
    elif num_to_select >= total_docs:
        print(f"Warning: Requested {num_to_select} documents, but only {total_docs} are available. Selecting all documents.")
        selected_docs_with_context = all_docs
        num_to_select = total_docs # Adjust number for final message
    else:
        # Select N random documents
        selected_docs_with_context = random.sample(all_docs, num_to_select)
        print(f"Randomly selected {len(selected_docs_with_context)} documents.")

    # Build the output structure
    output_data = build_output_structure(selected_docs_with_context)

    # Write output data
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2)
        print(f"Successfully wrote {len(selected_docs_with_context)} selected documents to {output_path}")
    except Exception as e:
        print(f"An error occurred while writing to {output_path}: {e}")

if __name__ == "__main__":
    main()
