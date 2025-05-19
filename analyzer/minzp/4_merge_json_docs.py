import argparse
import json
import os

def load_json_file(filepath):
    """Loads a JSON file and returns its content."""
    abs_filepath = os.path.abspath(filepath)
    try:
        with open(abs_filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Error: File not found at '{abs_filepath}'")
        return None
    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON from '{abs_filepath}'")
        return None
    except Exception as e:
        print(f"An unexpected error occurred while loading '{abs_filepath}': {e}")
        return None

def main():
    parser = argparse.ArgumentParser(description="Merges two JSON files based on a common 'url' field.")
    parser.add_argument('--in', dest='input_files', action='append', required=True,
                        help='Input JSON file. This argument should be provided twice, one for each input file.')
    parser.add_argument('--out', dest='output_file', required=True,
                        help='Path to the output merged JSON file.')

    args = parser.parse_args()

    if len(args.input_files) != 2:
        print("Error: Exactly two --in arguments are required (e.g., --in file1.json --in file2.json).")
        return

    file1_path = args.input_files[0]
    file2_path = args.input_files[1]

    docs1 = load_json_file(file1_path)
    docs2 = load_json_file(file2_path)

    if docs1 is None or docs2 is None:
        return

    if not isinstance(docs1, list) or not isinstance(docs2, list):
        print("Error: Both input files must contain a JSON list at the root.")
        return

    docs2_map = {}
    for doc in docs2:
        if isinstance(doc, dict) and 'url' in doc:
            docs2_map[doc['url']] = doc
        else:
            print(f"Warning: Skipping invalid or URL-less document in {os.path.abspath(file2_path)}: {doc}")

    merged_data = []
    processed_docs1_urls = set() # To keep track of URLs from docs1 that have been processed

    for doc1 in docs1:
        if not (isinstance(doc1, dict) and 'url' in doc1):
            print(f"Warning: Skipping invalid or URL-less document in {os.path.abspath(file1_path)}: {doc1}")
            merged_data.append(doc1) # Add as is, or decide to skip entirely
            continue

        doc1_url = doc1['url']
        processed_docs1_urls.add(doc1_url)
        if doc1_url in docs2_map:
            merged_doc = doc1.copy()
            merged_doc.update(docs2_map[doc1_url])
            merged_data.append(merged_doc)
        else:
            merged_data.append(doc1)

    for doc2_url, doc2_content in docs2_map.items():
        if doc2_url not in processed_docs1_urls:
            merged_data.append(doc2_content)

    output_file_abs_path = os.path.abspath(args.output_file)
    try:
        with open(output_file_abs_path, 'w', encoding='utf-8') as f:
            json.dump(merged_data, f, indent=2, ensure_ascii=False)
        print(f"Successfully merged data into '{output_file_abs_path}'")
    except IOError as e:
        print(f"Error: Could not write to output file '{output_file_abs_path}': {e}")
    except Exception as e:
        print(f"An unexpected error occurred while writing to '{output_file_abs_path}': {e}")

if __name__ == "__main__":
    main()