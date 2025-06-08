import urllib.parse
import os
import hashlib
import sys

def get_doc_id(doc_url: str) -> str | None:
    """
    Určí ID dokumentu z URL.
    1. Skúsi parameter 'subor'.
    2. Skúsi názov súboru z URL cesty.
    3. Ak neúspešné, vráti hash celej URL.
    """
    if not doc_url:
        return None

    parsed_url = urllib.parse.urlparse(doc_url)
    query_params = urllib.parse.parse_qs(parsed_url.query)

    #--------------------------------------------------
    # www.minzp.sk: DOC_ID je názov súboru z URL bez prípony
    if 'www.minzp.sk' in doc_url:
        return os.path.splitext(os.path.basename(parsed_url.path))[0]

    #--------------------------------------------------
    # www.minv.sk:
    # 1. Skontroluj parameter 'subor'
    if 'subor' in query_params and query_params['subor'] and query_params['subor'][0]: # Check for non-empty value
        return query_params['subor'][0]

    # 2. Ak názov súboru začína na 'OU-', použij ho
    path = parsed_url.path
    if path:
        filename_with_ext = os.path.basename(path)
        if filename_with_ext and filename_with_ext.lower().startswith('ou-'):
            filename_without_ext, ext = os.path.splitext(filename_with_ext)
            return filename_without_ext

    # 3. Ak nič z vyššie uvedeného, vygeneruj hash z URL
    try:
        url_bytes = doc_url.encode('utf-8')
        hash_object = hashlib.sha256(url_bytes)
        hex_dig = hash_object.hexdigest()
        return f"urlhash_{hex_dig[:16]}" # Použije prvých 16 znakov hashu
    except Exception as e:
        print(f"Chyba pri generovaní hashu pre URL {doc_url}: {e}", file=sys.stderr)
        return None