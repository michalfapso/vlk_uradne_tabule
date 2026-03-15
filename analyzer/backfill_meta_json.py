#!/usr/bin/env python3
"""
Backfill meta.json files for documents that lack them.

This script:
1. Discovers doc folders without meta.json
2. Iterates git history of the data submodule to find document metadata
3. Falls back to folder path extraction for unmatched docIds
4. Writes meta.json files with available fields
"""

import json
import os
import sys
import glob
import subprocess
from pathlib import Path

# Add analyzer/shared to sys.path to import get_doc_id
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'shared'))
from get_doc_id import get_doc_id


def discover_docs_without_meta():
    """
    Discover all doc folders without meta.json.
    Returns a dict mapping folder_path -> (source, kraj, okres, docId).
    Path structure: data/docs/{source}/{kraj}/{okres}/{docId}/

    Use folder path as key since docIds are not globally unique.
    """
    docs_path = Path(__file__).parent.parent / 'data' / 'docs'
    docs_needing_meta = {}

    # Iterate through all sources
    for source_dir in docs_path.iterdir():
        if not source_dir.is_dir():
            continue

        source = source_dir.name

        # Iterate through all kraje
        for kraj_dir in source_dir.iterdir():
            if not kraj_dir.is_dir():
                continue

            kraj = kraj_dir.name

            # Iterate through all okresy
            for okres_dir in kraj_dir.iterdir():
                if not okres_dir.is_dir():
                    continue

                okres = okres_dir.name

                # Iterate through all docId folders
                for doc_dir in okres_dir.iterdir():
                    if not doc_dir.is_dir():
                        continue

                    docId = doc_dir.name
                    meta_file = doc_dir / 'meta.json'

                    if not meta_file.exists():
                        # Key by absolute folder path to handle duplicate docIds
                        docs_needing_meta[str(doc_dir)] = (source, kraj, okres, docId)

    return docs_needing_meta


def get_git_commits_reverse_chrono(repo_path):
    """
    Get all commits from git history in reverse chronological order.
    Returns list of commit hashes.
    """
    try:
        output = subprocess.check_output(
            ['git', 'log', '--all', '--format=%H'],
            cwd=repo_path,
            stderr=subprocess.DEVNULL
        )
        commits = output.decode('utf-8').strip().split('\n')
        return [c for c in commits if c]  # Filter empty lines
    except subprocess.CalledProcessError:
        return []


def read_json_from_commit(commit, filepath, repo_path):
    """
    Read JSON file from a specific git commit.
    Returns parsed JSON data or None if file doesn't exist at that commit.
    """
    try:
        output = subprocess.check_output(
            ['git', 'show', f'{commit}:{filepath}'],
            cwd=repo_path,
            stderr=subprocess.DEVNULL
        )
        return json.loads(output)
    except (subprocess.CalledProcessError, json.JSONDecodeError):
        return None


def extract_minv_docs(minv_data):
    """
    Extract documents from minv JSON structure.
    Returns list of (docId, doc_dict, kraj, okres, kategoria).
    """
    docs = []

    if not isinstance(minv_data, list):
        return docs

    for kraj_item in minv_data:
        kraj = kraj_item.get('kraj', '')
        okresy = kraj_item.get('okresy', [])

        for okres_item in okresy:
            okres = okres_item.get('nazov', '')
            kategorii = okres_item.get('dokumenty_zivotne_prostredie', [])

            for kategoria_item in kategorii:
                kategoria = kategoria_item.get('kategoria', '')
                dokumenty = kategoria_item.get('dokumenty', [])

                for doc in dokumenty:
                    doc_id = get_doc_id(doc.get('url', ''))
                    if doc_id:
                        docs.append({
                            'docId': doc_id,
                            'doc': doc,
                            'kraj': kraj,
                            'okres': okres,
                            'kategoria': kategoria
                        })

    return docs


def extract_minzp_docs(minzp_data):
    """
    Extract documents from minzp JSON structure (flat list).
    Returns list of (docId, doc_dict).
    Note: kraj and okres must be derived from folder path.
    """
    docs = []

    if not isinstance(minzp_data, list):
        return docs

    for doc in minzp_data:
        doc_id = get_doc_id(doc.get('url', ''))
        if doc_id:
            docs.append({
                'docId': doc_id,
                'doc': doc,
                'kraj': None,
                'okres': None
            })

    return docs


def extract_krajokres_from_path(folder_path):
    """
    Extract kraj and okres from folder path.
    Path structure: data/docs/{source}/{kraj}/{okres}/{docId}/
    """
    parts = folder_path.parts

    # Expected structure: [..., 'docs', source, kraj, okres, docId]
    if len(parts) >= 5:
        # Get last 4 parts: source, kraj, okres, docId
        kraj = parts[-3]
        okres = parts[-2]
        return kraj, okres

    return None, None


def build_meta(doc_dict, kraj, okres, kategoria=None):
    """
    Build meta.json content from document data.
    """
    meta = {
        'url': doc_dict.get('url'),
        'source': None,  # Will be set from folder path
        'datum': doc_dict.get('datum'),
        'nazov': doc_dict.get('nazov'),
        'kraj': kraj,
        'okres': okres,
        'kategoria': kategoria
    }
    return meta


def derive_source_from_path(folder_path):
    """
    Derive source (minv or minzp) from folder path.
    Path: data/docs/{source}/...
    Expected structure: [..., 'docs', source, kraj, okres, docId]
    """
    parts = folder_path.parts
    if len(parts) >= 4:
        # Source is 4 positions from end
        potential_source = parts[-4]
        if potential_source in ('minv', 'minzp'):
            return potential_source
    return None


def backfill_from_git_history(docs_needing_meta, repo_path, data_repo_path):
    """
    Try to backfill documents from git history.
    Keys in docs_needing_meta are folder paths (string).
    Returns updated dict with remaining unmatched folder paths.
    """
    commits = get_git_commits_reverse_chrono(data_repo_path)
    processed = 0
    backfilled = 0

    print(f"Processing {len(commits)} commits from git history...")

    for commit_idx, commit in enumerate(commits):
        if not docs_needing_meta:
            print(f"All documents backfilled at commit {commit_idx + 1}/{len(commits)}")
            break

        # Try minv
        minv_data = read_json_from_commit(commit, 'scraped/minv_2_documents_old.json', data_repo_path)
        if minv_data:
            minv_docs = extract_minv_docs(minv_data)
            for item in minv_docs:
                doc_id = item['docId']
                git_kraj = item['kraj']
                git_okres = item['okres']

                # Find matching folder: source/kraj/okres/docId
                matching_folders = []
                for folder_str, (source, kraj, okres, docId) in list(docs_needing_meta.items()):
                    if docId == doc_id and source == 'minv' and kraj == git_kraj and okres == git_okres:
                        matching_folders.append(folder_str)

                for folder_str in matching_folders:
                    folder_path = Path(folder_str)
                    meta = build_meta(
                        item['doc'],
                        item['kraj'],
                        item['okres'],
                        item['kategoria']
                    )
                    meta['source'] = 'minv'

                    # Write meta.json
                    meta_file = folder_path / 'meta.json'
                    with open(meta_file, 'w', encoding='utf-8') as f:
                        json.dump(meta, f, ensure_ascii=False, indent=2)

                    del docs_needing_meta[folder_str]
                    backfilled += 1
                    processed += 1

                    if processed % 50 == 0:
                        print(f"Backfilled {processed} documents...")

        # Try minzp
        minzp_data = read_json_from_commit(commit, 'scraped/minzp_2_documents_old.json', data_repo_path)
        if minzp_data:
            minzp_docs = extract_minzp_docs(minzp_data)
            for item in minzp_docs:
                doc_id = item['docId']

                # Find matching folders with this docId in minzp
                matching_folders = []
                for folder_str, (source, kraj, okres, docId_in_dict) in list(docs_needing_meta.items()):
                    if docId_in_dict == doc_id and source == 'minzp':
                        matching_folders.append(folder_str)

                for folder_str in matching_folders:
                    folder_path = Path(folder_str)

                    # For minzp, derive kraj/okres from folder path
                    _, kraj, okres, _ = docs_needing_meta[folder_str]

                    meta = build_meta(
                        item['doc'],
                        kraj,
                        okres,
                        None  # minzp doesn't have kategoria in the same way
                    )
                    meta['source'] = 'minzp'

                    # Write meta.json
                    meta_file = folder_path / 'meta.json'
                    with open(meta_file, 'w', encoding='utf-8') as f:
                        json.dump(meta, f, ensure_ascii=False, indent=2)

                    del docs_needing_meta[folder_str]
                    backfilled += 1
                    processed += 1

                    if processed % 50 == 0:
                        print(f"Backfilled {processed} documents...")

    return docs_needing_meta


def fallback_backfill(docs_needing_meta):
    """
    For remaining unmatched docIds, try fallback strategies:
    1. Extract kraj/okres from folder path
    2. For minv: reconstruct URL as https://www.minv.sk/?subor={docId}
    3. For minzp: try to extract datum from analysis.json

    docs_needing_meta keys are folder paths (string), values are (source, kraj, okres, docId).
    """
    backfilled_fallback = 0
    failed = []

    for folder_str, (source, kraj, okres, doc_id) in list(docs_needing_meta.items()):
        try:
            folder_path = Path(folder_str)

            # Try to read analysis.json for additional info
            analysis_file = folder_path / 'analysis.json'
            datum = None
            if analysis_file.exists():
                try:
                    with open(analysis_file, 'r', encoding='utf-8') as f:
                        analysis = json.load(f)
                        datum = analysis.get('datum_dokumentu')
                except Exception:
                    pass

            # Build meta with available information
            meta = {
                'url': None,
                'source': source,
                'datum': datum,
                'nazov': None,
                'kraj': kraj,
                'okres': okres,
                'kategoria': None
            }

            # Try to reconstruct URL for minv documents
            if source == 'minv' and doc_id.isdigit():
                meta['url'] = f'https://www.minv.sk/?subor={doc_id}'

            # Write meta.json
            meta_file = folder_path / 'meta.json'
            with open(meta_file, 'w', encoding='utf-8') as f:
                json.dump(meta, f, ensure_ascii=False, indent=2)

            del docs_needing_meta[folder_str]
            backfilled_fallback += 1
        except Exception as e:
            failed.append((doc_id, str(e)))

    if failed:
        print(f"  Failed to backfill {len(failed)} docIds:")
        for doc_id, error in failed[:5]:
            print(f"    {doc_id}: {error}")

    return backfilled_fallback


def main():
    print("Scanning documents without meta.json...")
    docs_needing_meta = discover_docs_without_meta()
    print(f"Found {len(docs_needing_meta)} docIds needing backfill")

    if not docs_needing_meta:
        print("No documents need backfilling.")
        return

    # Get data repo path
    repo_path = Path(__file__).parent.parent
    data_repo_path = repo_path / 'data'

    print("\nProcessing git history from data/ submodule...")
    docs_needing_meta = backfill_from_git_history(docs_needing_meta, repo_path, data_repo_path)

    print(f"\nAfter git history: {len(docs_needing_meta)} docIds still need backfilling")

    if docs_needing_meta:
        print("\nApplying fallback strategy...")
        fallback_count = fallback_backfill(docs_needing_meta)
        print(f"Backfilled {fallback_count} documents via fallback")

    # Final check
    remaining = discover_docs_without_meta()
    if remaining:
        print(f"\n⚠ WARNING: {len(remaining)} documents still lack meta.json:")
        for folder_str, (source, kraj, okres, docId) in list(remaining.items())[:10]:
            print(f"  {Path(folder_str).parts[-4:]}")
        if len(remaining) > 10:
            print(f"  ... and {len(remaining) - 10} more")
    else:
        print("\nBackfill complete: All documents now have meta.json")
        print("✓ No documents remaining.")


if __name__ == '__main__':
    main()
