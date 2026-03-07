import requests
import geopandas as gpd
import pandas as pd
import io
import csv, sys
import os
import json
import re
from dataclasses import dataclass, field
from typing import List, Dict, Any, Literal
import time
from log_handler import log_status
import unicodedata
from shapely.geometry import shape
import difflib

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROTECTED_AREAS_DATA_DIR = os.path.join(SCRIPT_DIR, '..', '..', 'data', 'protected_areas')
CADASTER_DATA_DIR = os.path.join(SCRIPT_DIR, '..', '..', 'data', 'cadaster')

PROXY_URL = os.environ.get('GIS_PROXY_URL', '')
PROXY_AUTH = os.environ.get('GIS_PROXY_AUTH', '')

@dataclass
class CadastralZoningReferenceParcels:
    """Represents a request for parcels within a single cadastral zone."""
    nationalCadastralZoningReference: str
    cadasterType: Literal['C', 'E']
    parcelLabels: List[str]

def _make_request(method, url, caller_name, headers, **kwargs):
    retry_delays = [5, 10, 30, 60, 120]  # Delays in seconds for retries
    
    use_proxy = 'skgeodesy.sk' in url and PROXY_URL
    if use_proxy:
        if headers is None:
            headers = {}
        headers = headers.copy()
        headers['X-Proxy-Auth'] = PROXY_AUTH
        
        # We pass the original full URL as a parameter to the proxy
        params = kwargs.get('params', {}).copy()
        params['url'] = url
        kwargs['params'] = params
        
        request_url = PROXY_URL
    else:
        request_url = url

    for attempt, delay in enumerate(retry_delays + [None]):
        t0 = time.time()
        try:
            print(f'{caller_name}() request {method} url:', url, '(via proxy)' if use_proxy else '')
            if method.upper() == 'GET':
                response = requests.get(request_url, headers=headers, **kwargs)
            elif method.upper() == 'POST':
                response = requests.post(request_url, headers=headers, **kwargs)
            else:
                raise ValueError("Unsupported HTTP method")
            response.raise_for_status()

            print('response:', response)
            print(f'{caller_name}() request duration: {time.time() - t0:.2f} s')
            # print('response:', response.text)
            return response.json()
        except requests.exceptions.HTTPError as e:
            print(f'{caller_name}() request duration: {time.time() - t0:.2f} s')
            if e.response.status_code == 500 and delay is not None:
                print(f"Server vrátil chybu 500. Opakujem pokus o {delay} sekúnd... (Pokus {attempt + 1}/{len(retry_delays)})", file=sys.stderr)
                time.sleep(delay)
                continue
            print(f"{caller_name}() Chyba pri sťahovaní dát (HTTP): {e}", file=sys.stderr)
            if e.response:
                print(f"Odpoveď servera: {e.response.text}", file=sys.stderr)
            return None  # Non-500 error or retries exhausted
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
            print(f'{caller_name}() request duration: {time.time() - t0:.2f} s')
            if delay is not None:
                print(f"{caller_name}() Chyba spojenia/timeout: {e}. Opakujem pokus o {delay} sekúnd... (Pokus {attempt + 1}/{len(retry_delays)})", file=sys.stderr, flush=True)
                time.sleep(delay)
                continue
            print(f"{caller_name}() Chyba pri sťahovaní dát (všetky pokusy zlyhali): {e}", file=sys.stderr, flush=True)
            return None
        except requests.exceptions.RequestException as e:
            print(f'{caller_name}() request duration: {time.time() - t0:.2f} s')
            print(f"{caller_name}() Neočakávaná chyba pri sťahovaní dát: {e}", file=sys.stderr, flush=True)
            return None
    return None

def _merge_gdfs(gdfs: List[gpd.GeoDataFrame]) -> gpd.GeoDataFrame | None:
    """Zlúči zoznam GeoDataFrames do jedného."""
    if not gdfs:
        return None
    # Použijeme concat z pandas, ktorý je základom pre geopandas
    # a je efektívnejší pre zlučovanie viacerých rámcov.
    # ignore_index=True zabezpečí čistý index vo výsledku.
    merged_gdf = pd.concat(gdfs, ignore_index=True)
    # Uistíme sa, že výsledok je stále GeoDataFrame
    return gpd.GeoDataFrame(merged_gdf, geometry=merged_gdf.geometry.name)

def get_geometry_of_cadastral_zone_parcels(zoningReferenceParcelsList: List[CadastralZoningReferenceParcels]) -> gpd.GeoDataFrame | None:
    """
    Získa geometriu (polygón) parcely C pomocou WFS služby INSPIRE.
    Používa XML filter na obídenie WAF (Web Application Firewall).

    Parcely katastra nehnuteľností C https://inspirews.skgeodesy.sk/geoserver/cp/ogc/features/v1/collections/CP.CadastralParcel/items
    Parcely katastra nehnuteľností E https://inspirews.skgeodesy.sk/geoserver/cp_uo/ogc/features/v1/collections/CP.CadastralParcelUO/items
    """

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36'
    }

    # Group parcels by cadasterType
    parcels_by_type = {'C': [], 'E': []}
    # print('get_geometry_of_cadastral_zone_parcels() zoningReferenceParcelsList:', zoningReferenceParcelsList)
    for item in zoningReferenceParcelsList:
        parcels_by_type[item.cadasterType].append(item)

    # Define endpoints and typeNames for each cadaster type
    configs = {
        'C': {
            'url': "https://inspirews.skgeodesy.sk/geoserver/cp/ogc/features/v1/collections/CP.CadastralParcel/items",
        },
        'E': {
            'url': "https://inspirews.skgeodesy.sk/geoserver/cp_uo/ogc/features/v1/collections/CP.CadastralParcelUO/items",
        }
    }

    all_features = []
    crs_data = None

    for cad_type, parcels_list in parcels_by_type.items():
        if not parcels_list:
            continue

        # print('get_geometry_of_cadastral_zone_parcels() parcels_list:', parcels_list)
        nationalCadastralReferences = []
        for zoningReferenceParcels in parcels_list:
            if zoningReferenceParcels.parcelLabels:
                for parcelLabel in zoningReferenceParcels.parcelLabels:
                    nationalCadastralReferences.append(f"{zoningReferenceParcels.nationalCadastralZoningReference}_{parcelLabel}.{cad_type}")
            else:
                zone_gdf = get_cadastral_zone(zoningReferenceParcels.nationalCadastralZoningReference, cad_type)
                if zone_gdf is not None and not zone_gdf.empty:
                    # Prevedieme GeoDataFrame na GeoJSON features a pridáme ich
                    # print('get_geometry_of_cadastral_zone_parcels() zone_gdf:', zone_gdf)
                    # print('get_geometry_of_cadastral_zone_parcels() zone_gdf columns:', zone_gdf.columns)
                    # print('get_geometry_of_cadastral_zone_parcels() zone_gdf geometry column:', zone_gdf.geometry)
                    # print('get_geometry_of_cadastral_zone_parcels() zone_gdf geometry column:', zone_gdf.geometry.name)
                    zone_jsonstr = zone_gdf.to_json()
                    zone_json = json.loads(zone_jsonstr)
                    # print('get_geometry_of_cadastral_zone_parcels() zone_json:', zone_json)
                    zone_json_features = zone_json.get('features', [])
                    # print('get_geometry_of_cadastral_zone_parcels() zone_json_features:', zone_json_features)
                    all_features.extend(zone_json_features)

        if not nationalCadastralReferences:
            continue

        nationalCadastralReferences_quoted = [f"'{ref}'" for ref in nationalCadastralReferences]
        cql_filter_value = f"nationalCadastralReference IN ({','.join(nationalCadastralReferences_quoted)})"

        params = {
            'limit': 100,  # Stránkovanie pre prípad, že by zoznam bol veľmi dlhý
            'filter-lang': 'cql2-text',
            'filter': cql_filter_value
        }
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36'
        }

        # Aj pri filtrovaní musíme počítať so stránkovaním, hoci je menej pravdepodobné
        next_url = requests.Request('GET', configs[cad_type]['url'], params=params).prepare().url

        while next_url:
            data = _make_request('GET', next_url, 'get_geometry_of_cadastral_zone_parcels', headers=headers, timeout=10)
            # print('get_geometry_of_cadastral_zone_parcels() data:', data)
            if data is None:
                print('get_geometry_of_cadastral_zone_parcels() data is None')
                return None # Request failed

            if not crs_data and 'crs' in data:
                crs_data = data
            
            if "features" in data and data["features"]:
                all_features.extend(data["features"])
            
            next_url = None
            if "links" in data:
                for link in data["links"]:
                    if link.get("rel") == "next":
                        next_url = link.get("href")
                        break

    if not all_features:
        print("Pre zadané referencie neboli nájdené žiadne parcely.", file=sys.stderr)
        return None

    # Create a GeoDataFrame more robustly
    # 1. Create a standard DataFrame from properties
    properties_list = [f['properties'] for f in all_features]
    df = pd.DataFrame(properties_list)
    # 2. Create a GeoSeries from the geometry dictionaries
    geometries = [gpd.geoseries.shapely.geometry.shape(f['geometry']) for f in all_features]
    gs = gpd.GeoSeries(geometries)
    # 3. Combine into a GeoDataFrame
    final_gdf = gpd.GeoDataFrame(df, geometry=gs)
    # The INSPIRE service provides data in ETRS89 (EPSG:4258)
    final_gdf.set_crs("EPSG:4258", inplace=True)

    return final_gdf

def _normalize_string(s: str | None) -> str | None:
    """
    Normalizuje reťazec prevedením na malé písmená a odstránením diakritiky.
    """
    if not s:
        return s
    # NFD normalizácia rozdelí znaky na základný znak a diakritické znamienko.
    # Následne sa odfiltrujú všetky diakritické znamienka (kategória 'Mn').
    return "".join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn').lower()


def get_parcels_by_nationalCadastralReference(national_references: list[str]) -> gpd.GeoDataFrame | None:
    """
    Získa geometrie pre presne zadaný zoznam parciel pomocou ich unikátneho 
    identifikátora 'nationalCadastralReference'.
    Používa moderné OGC API - Features s pokročilým CQL2 filtrom.
    """
    if not national_references:
        print("Zoznam referencií je prázdny.", file=sys.stderr)
        return None

    base_url = "https://inspirews.skgeodesy.sk/geoserver/cp/ogc/features/v1/collections/CP.CadastralParcel/items"
    
    # Zostavenie CQL2 filtra pre operátor IN
    # Každá hodnota v zozname musí byť v apostrofoch
    quoted_references = [f"'{ref}'" for ref in national_references]
    cql_filter_value = f"nationalCadastralReference IN ({','.join(quoted_references)})"

    params = {
        'limit': 100,  # Stránkovanie pre prípad, že by zoznam bol veľmi dlhý
        'filter-lang': 'cql2-text',
        'filter': cql_filter_value
    }
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36'
    }

    all_features = []
    # Aj pri filtrovaní musíme počítať so stránkovaním, hoci je menej pravdepodobné
    next_url = requests.Request('GET', base_url, params=params).prepare().url

    while next_url:
        data = _make_request('GET', next_url, 'get_parcels_by_nationalCadastralReference', headers=headers, timeout=10)
        if data is None:
            return None # Request failed

        if "features" in data and data["features"]:
            all_features.extend(data["features"])
        
        next_url = None
        if "links" in data:
            for link in data["links"]:
                if link.get("rel") == "next":
                    next_url = link.get("href")
                    break

    if not all_features:
        print("Pre zadané referencie neboli nájdené žiadne parcely.", file=sys.stderr)
        return None

    final_gdf = gpd.GeoDataFrame.from_features(all_features)
    # The INSPIRE service provides data in ETRS89 (EPSG:4258)
    final_gdf.set_crs("EPSG:4258", inplace=True)

    return final_gdf

def test_get_parcels_by_nationalCadastralReference():
    parcely_na_nacitanie = [
        "800473_1295.C",
        "800473_1616/1.C",
        "800473_1522.C",
        "800473_1246/1.C",
        "800473_1248/1.C",
        "800473_1599/4.C",
        "800473_1507/3.C",
        "800473_1320/8.C",
        "800473_1313/2.C",
        "800473_1314/3.C",
    ]
 
    print(f"Sťahujú sa konkrétne parcely podľa zoznamu ({len(parcely_na_nacitanie)} ks)...")
    vybrane_parcely_gdf = get_parcels_by_nationalCadastralReference(parcely_na_nacitanie)
 
    if vybrane_parcely_gdf is not None and not vybrane_parcely_gdf.empty:
        print(f"\nÚSPECH! Celkovo načítaných {len(vybrane_parcely_gdf)} z {len(parcely_na_nacitanie)} požadovaných parciel.")
        
        print("\nZákladné informácie o načítaných parcelách:")
        print(vybrane_parcely_gdf[['label', 'nationalCadastralReference', 'areaValue']])


def get_nationalCadastralZoningReferences(katastralneUzemie, obec=None, okres=None, kraj=None) -> List[str]:
    # Ak je v obci viacero názvov oddelených čiarkou, spracujeme ich zvlášť   
    obec_split = obec.split(',') if obec else []
    if len(obec_split) > 1:
        found_ids = set()
        for obec_part in obec_split:
            obec_part = obec_part.strip()
            if obec_part:
                ids = _get_nationalCadastralZoningReferences(katastralneUzemie, obec_part, okres, kraj, katastralneUzemie, obec_part, okres, kraj)
                found_ids.update(ids)
        return list(found_ids)
    else:
        return _get_nationalCadastralZoningReferences(katastralneUzemie, obec, okres, kraj, katastralneUzemie, obec, okres, kraj)

_CADASTER_DATA_CACHE = None

def _load_cadaster_data():
    global _CADASTER_DATA_CACHE
    if _CADASTER_DATA_CACHE is not None:
        return _CADASTER_DATA_CACHE
    
    file_path = os.path.join(CADASTER_DATA_DIR, 'USJ_hranice_0.csv')
    data = []
    indices = None
    try:
        with open(file_path, mode='r', encoding='utf-8') as csvfile:
            reader = csv.reader(csvfile)
            header = next(reader)
            try:
                kraj_idx = header.index('NM2')
                okres_idx = header.index('NM3')
                obec_idx = header.index('NM4')
                ku_idx = header.index('NM5')
                idn5_idx = header.index('IDN5')
                indices = (kraj_idx, okres_idx, obec_idx, ku_idx, idn5_idx)
            except ValueError as e:
                print(f"Chyba: Stĺpec {e} sa nenašiel v CSV súbore.")
                return None, None

            for row in reader:
                data.append(row)
    except FileNotFoundError:
        print(f"Chyba: Súbor {file_path} sa nenašiel.")
        return None, None
            
    _CADASTER_DATA_CACHE = (data, indices)
    return _CADASTER_DATA_CACHE

def _get_nationalCadastralZoningReferences(katastralneUzemie, obec=None, okres=None, kraj=None, katastralneUzemieOrig=None, obecOrig=None, okresOrig=None, krajOrig=None) -> List[str]:
    """
    Loads the file ../data/cadaster/USJ_hranice_0.csv and finds all rows matching the given arguments.
    NM2 is kraj, NM3 is okres, NM4 is obec, NM5 is katastralneUzemie.
    Returns a list of IDN5 values.
    """
    cache = _load_cadaster_data()
    if not cache or not cache[0]:
        return []
    rows, (kraj_idx, okres_idx, obec_idx, ku_idx, idn5_idx) = cache

    kraj = re.sub(r'\s*[kK][rR][aA][jJ]', '', kraj) if kraj else None

    # Normalizácia vstupných parametrov
    norm_kraj = _normalize_string(kraj)
    norm_okres = _normalize_string(okres)
    norm_obec = _normalize_string(obec)
    norm_ku = _normalize_string(katastralneUzemie)
    norm_ku = re.sub(r'\s*k\.?\s*u\.?\s*', '', norm_ku) if norm_ku else None
    norm_ku = re.sub(r'katastralne\s*uzemie\s*', '', norm_ku) if norm_ku else None
    print('_get_nationalCadastralZoningReferences() norm_kraj:', norm_kraj, 'norm_okres:', norm_okres, 'norm_obec:', norm_obec, 'norm_ku:', norm_ku)
    
    # Detekcia rímskeho čísla v zadanom okrese (I až X) - normalizované sú malé písmená
    roman_suffix_pattern = re.compile(r'\s+(i|ii|iii|iv|v|vi|vii|viii|ix|x)$')
    input_okres_has_roman = bool(roman_suffix_pattern.search(norm_okres)) if norm_okres else False
        
    found_ids = set()

    for row in rows:
        # Porovnávame normalizované hodnoty
        if norm_kraj and _normalize_string(row[kraj_idx]) != norm_kraj:
            continue

        if norm_okres:
            row_okres_norm = _normalize_string(row[okres_idx])
            if not row_okres_norm:
                continue
                
            if input_okres_has_roman:
                if row_okres_norm != norm_okres:
                    continue
            else:
                # Ak vstup nemá rímske číslo, odstránime ho z dát v CSV pre porovnanie (napr. Košice IV -> košice)
                row_okres_cleaned = roman_suffix_pattern.sub('', row_okres_norm)
                if row_okres_cleaned != norm_okres:
                    continue

        if norm_obec and _normalize_string(row[obec_idx]) != norm_obec:
            continue
        if norm_ku and _normalize_string(row[ku_idx]) != norm_ku:
            continue
        
        found_ids.add(row[idn5_idx])

    if not found_ids:
        # 1. Skúsime odstrániť obec/okres z názvu katastrálneho územia (existujúca logika)
        if katastralneUzemie is not None:
            if obec is not None:
                katastralneUzemie2 = re.sub(r'^' + re.escape(obec) + r'\s*-\s*', '', katastralneUzemie, flags=re.IGNORECASE)
                if katastralneUzemie2 != katastralneUzemie:
                    return _get_nationalCadastralZoningReferences(katastralneUzemie2, obec, okres, kraj)
            if okres is not None:
                katastralneUzemie2 = re.sub(r'^' + re.escape(okres) + r'\s*-\s*', '', katastralneUzemie, flags=re.IGNORECASE)
                if katastralneUzemie2 != katastralneUzemie:
                    return _get_nationalCadastralZoningReferences(katastralneUzemie2, obec, okres, kraj)

        # 2. Fuzzy matching
        if norm_ku:
            candidates = []
            for row in rows:
                if norm_kraj and _normalize_string(row[kraj_idx]) != norm_kraj: continue
                if norm_okres and _normalize_string(row[okres_idx]) != norm_okres: continue
                if norm_obec and _normalize_string(row[obec_idx]) != norm_obec: continue
                candidates.append(row)
            
            if candidates:
                candidate_kus_norm = [_normalize_string(r[ku_idx]) for r in candidates]
                matches = difflib.get_close_matches(norm_ku, candidate_kus_norm, n=1, cutoff=0.75)
                if matches:
                    best_match_norm = matches[0]
                    for r in candidates:
                        if _normalize_string(r[ku_idx]) == best_match_norm:
                            print(f"Fuzzy match found: '{katastralneUzemie}' -> '{r[ku_idx]}' (ID: {r[idn5_idx]})")
                            return [r[idn5_idx]]

        # 3. Relaxácia obmedzení
        if katastralneUzemie is not None:
            if obec is not None:
                # Skúsime zavolať bez obce
                return _get_nationalCadastralZoningReferences(katastralneUzemie, None, okres, kraj)
            if okres is not None:
                # Skúsime zavolať bez okresu
                return _get_nationalCadastralZoningReferences(katastralneUzemie, None, None, kraj)
            if kraj is not None:
                # Skúsime zavolať bez kraja
                return _get_nationalCadastralZoningReferences(katastralneUzemie, None, None, None)
            # Nakoniec skusime odstranit katastralneUzemie, mozno je v nom nejaky preklep a nechame len obec, okres, kraj
            return _get_nationalCadastralZoningReferences(None, obecOrig, okresOrig, krajOrig)
        else:
            # Niekedy sa stane, ze je zadany zoznam viacerych obci oddelenych ciarkou a vacsina patri do daneho okresu, ale niektora obec je v inom okrese
            if obec is not None:
                # Skúsime zavolať bez okresu alebo bez kraja
                if okres is not None:
                    return _get_nationalCadastralZoningReferences(None, obec, None, kraj)
                if kraj is not None:
                    return _get_nationalCadastralZoningReferences(None, obec, None, None)
            if okres is not None:
                # Skúsime zavolať bez kraja
                if kraj is not None:
                    return _get_nationalCadastralZoningReferences(None, None, okres, None)
        raise Exception(f"Nenašlo sa žiadne katastrálne uzemie pre zadané parametre kraj:{kraj}, okres:{okres}, obec:{obec}, katastralneUzemie:{katastralneUzemie}")

    assert len(found_ids) < 5, f"Nájdených príliš veľa katastrálnych území ({len(found_ids)}), pravdepodobne je niekde chyba."

    print('_get_nationalCadastralZoningReferences() found_ids:', found_ids)
    return list(found_ids)


def get_cadastral_zone(nationalCadastralZoningReference: str, cadastralType: Literal['C', 'E']):
    configs = {
        'C': {
            'url': "https://inspirews.skgeodesy.sk/geoserver/cp/ogc/features/v1/collections/CP.CadastralZoning/items",
        },
        'E': {
            'url': "https://inspirews.skgeodesy.sk/geoserver/cp_uo/ogc/features/v1/collections/CP.CadastralZoningUO/items",
        }
    }

    params = {
        'limit': 100, # Paging
        'filter-lang': 'cql2-text',
        'filter': f"nationalCadastalZoningReference IN ('{nationalCadastralZoningReference}')", # There seems to be a typo in the database "Cadastal" instead of "Cadastral"
        'f': 'application/geo+json'
    }
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36'
    }

    features = []
    url = requests.Request('GET', configs[cadastralType]['url'], params=params).prepare().url
    data = _make_request('GET', url, 'get_cadastral_zone', headers=headers, timeout=10)
    if data is None:
        print('get_cadastral_zone() response is None')
        return None

    if "features" in data and data["features"]:
        print('get_cadastral_zone() found features:', data["features"])
        features.extend(data["features"])
    if not features:
        print(f"Pre zadané nationalCadastralZoningReference nebolo nájdené žiadne katastrálne územie. Response: {data}", file=sys.stderr)
        return None

    properties_list = [f['properties'] for f in features]
    df = pd.DataFrame(properties_list)
    geometries = [gpd.geoseries.shapely.geometry.shape(f['geometry']) if f.get('geometry') else None for f in features]
    final_gdf = gpd.GeoDataFrame(df, geometry=geometries)

    # print('get_cadastral_zone() final_gdf columns:', final_gdf.columns)
    final_gdf.set_crs("EPSG:4258", inplace=True)

    return final_gdf


def get_geometry_of_a_parcel_set(data: dict, status_filepath: str):
    """
    Finds geometry for each parcel in the input object.

    Args:
        data: An object with cadastral areas and parcel numbers.

    Returns:
        The same object with geometry added to each parcel number.
    """
    # kraj  = data['kraj' ] if 'kraj'  in data else None
    print('data:', data)
    kraj  = data.get('kraj')
    okres = data.get('okres')
    obec  = data.get('obec')
    if isinstance(obec, List):
        obec = ", ".join(obec)

    gdf = None
    katastralne_uzemia = data.get('katastralne_uzemia', [])
    if katastralne_uzemia:
        all_gdfs = []
        for ku in katastralne_uzemia:
            ku_name = ku.get('nazov')
            print(f'ku_name:{ku_name} obec:{obec} okres:{okres} kraj:{kraj}')
            nationalCadastralZoningReferences = get_nationalCadastralZoningReferences(ku_name, obec, okres, kraj)
            print('nationalCadastralZoningReferences:', nationalCadastralZoningReferences)

            if not nationalCadastralZoningReferences:
                log_status(status_filepath, "error", f"Nenašlo sa žiadne katastrálne územie pre zadané parametre kraj:'{kraj}', okres:'{okres}', obec:'{obec}', katastrálne územie:'{ku_name}'")

            def get_gdfs(ku, nationalCadastralZoningReferences):
                ku_gdfs = []
                for nationalCadastralZoningReference in nationalCadastralZoningReferences:
                    parcely = ku.get('parcely', [])
                    if not parcely:
                        parcely = [{"typ": "C", "cisla": []}] # If no parcels specified, request the whole cadastral zone
                    for parcel_set in parcely:
                        parcel_type = parcel_set.get('typ') or ''
                        parcel_types = ['E'] if 'E' in parcel_type.upper() else ['C'] if 'C' in parcel_type.upper() else ['C', 'E']
                        parcel_types_valid_count = 0
                        for parcel_type in parcel_types:
                            request_for_ref: List[CadastralZoningReferenceParcels] = []
                            request_for_ref.append(CadastralZoningReferenceParcels(
                                nationalCadastralZoningReference=nationalCadastralZoningReference,
                                cadasterType=parcel_type,
                                parcelLabels=parcel_set.get('cisla', [])
                            ))
                            gdf_for_ref = get_geometry_of_cadastral_zone_parcels(request_for_ref)
                            if gdf_for_ref is not None and not gdf_for_ref.empty:
                                ku_gdfs.append(gdf_for_ref)
                                parcel_set['typ'] = parcel_type
                                parcel_types_valid_count += 1

                        if parcel_types_valid_count == 0:
                            log_status(status_filepath, "warning", f"Pre parcelu '{parcel_set}' v katastrálnom území '{ku_name}' sa nenašli dáta v katastri.")
                        if parcel_types_valid_count > 1:
                            log_status(status_filepath, "warning", f"Pre parcelu '{parcel_set}' v katastrálnom území '{ku_name}' sa našli dáta v oboch typoch katastra C aj E.")

                if len(ku_gdfs) > 1:
                    log_status(status_filepath, "warning", f"Nejednoznačne zadané katastrálne územie '{ku_name}' - našli sa k nemu {len(ku_gdfs)} zhody a použijú sa všetky, aj keď je pravdepodobne z nich len 1 správne.")
                if not ku_gdfs:
                    log_status(status_filepath, "error", f"Nenašli sa žiadne parcely pre zadané parametre: {data}")
                return ku_gdfs
            
            ku_gdfs = get_gdfs(ku, nationalCadastralZoningReferences)
            print('ku_gdfs:', ku_gdfs)
            if not ku_gdfs:
                changed = False
                for parcel_set in ku.get('parcely', []):
                    original_cisla = parcel_set.get('cisla', [])
                    # Normalize parcel numbers by removing prefixes like '1-'
                    normalized_cisla = [re.sub(r'^.*\-', '', pn) for pn in original_cisla]
                    if original_cisla != normalized_cisla:
                        changed = True
                        parcel_set['cisla'] = normalized_cisla

                if changed:
                    ku_gdfs = get_gdfs(ku, nationalCadastralZoningReferences)

            all_gdfs.extend(ku_gdfs)

        gdf = _merge_gdfs(all_gdfs)
    else:
        nationalCadastralZoningReferences = get_nationalCadastralZoningReferences(None, obec, okres, kraj)
        request: List[CadastralZoningReferenceParcels] = []
        for nationalCadastralZoningReference in nationalCadastralZoningReferences:
            request.append(CadastralZoningReferenceParcels(
                nationalCadastralZoningReference=nationalCadastralZoningReference,
                cadasterType='C',
                parcelLabels=[]
            ))
        gdf = get_geometry_of_cadastral_zone_parcels(request)

    if gdf is None or gdf.empty:
        print("No geometries were found, so no file will be saved.", file=sys.stderr)
        return None

    return gdf

def get_geometry_of_a_geoname(nazov_lokality: str, obec: str, okres: str, kraj: str, status_filepath: str) -> gpd.GeoDataFrame | None:
    """
    Získa geometriu (polygón) lokality pomocou Nominatim API.
    """ 
    nazov_lokality = nazov_lokality.replace('NPR ', '')
    nazov_lokality = nazov_lokality.replace('PR ', '')
    print('get_geometry_of_a_geoname nazov_lokality:', nazov_lokality)

    def get_url(url: str):
        print('url:', url)
        # Nominatim requires a User-Agent header
        headers = {
            'User-Agent': 'VLK_Uradne_Nastenky_Analyzer/1.0'
        }
        response = requests.get(url, headers=headers)
        print('response:', response)
        if response.status_code == 200:
            data = response.json()
            # Ak je odpoveď FeatureCollection (GeoJSON formát)
            if 'features' in data:
                features = data['features']
            # Ak je odpoveď zoznam objektov (starší formát alebo špecifické query)
            elif isinstance(data, list):
                features = data
            else:
                features = []

            valid_features = []
            for item in features:
                # Nominatim niekedy vracia geometriu priamo v 'geojson' kľúči pre každý item v zozname
                geom_json = item.get('geojson') or item.get('geometry')
                if geom_json and geom_json['type'] in ['Polygon', 'MultiPolygon']:
                    valid_features.append(item)
            
            if valid_features:
                # Check if the first item looks like a Feature
                first = valid_features[0]
                if first.get('type') == 'Feature' and 'properties' in first:
                     return gpd.GeoDataFrame.from_features(valid_features, crs='EPSG:4326')
                else:
                     # Flat dicts
                     geometries = [shape(item.get('geojson') or item.get('geometry')) for item in valid_features]
                     df = pd.DataFrame(valid_features)
                     return gpd.GeoDataFrame(df, geometry=geometries, crs='EPSG:4326')
        return None

    url = f"https://nominatim.openstreetmap.org/search?format=geojson&polygon_geojson=1&accept-language=sk&q={nazov_lokality}"

    if obec:
        gdf = get_url(f"{url}, {obec}")
        if gdf is not None:
            return gdf

    if okres:
        gdf = get_url(f"{url}, {okres}")
        if gdf is not None:
            return gdf

    if kraj:
        gdf = get_url(f"{url}, {kraj}")
        if gdf is not None:
            return gdf

    return get_url(url)


def gdf_save_to_file(gdf: gpd.GeoDataFrame, output_filepath: str):
    # Re-project the GeoDataFrame to the standard web map projection (EPSG:4326 - WGS 84)
    # GeoJSON standard officially recommends WGS 84. OpenLayers can handle the
    # reprojection from 4326 to 3857 (Web Mercator) on the fly.
    # print(f"Original CRS: {gdf.crs}")
    gdf_wgs84 = gdf.to_crs(epsg=4326)
    # print(f"Data re-projected to: {gdf_wgs84.crs}")

    # Save the re-projected data to a GeoJSON file
    # Option A: Standard GeoJSON (Recommended for servers with on-the-fly compression)
    gdf_wgs84.to_file(output_filepath, driver='GeoJSON')
    # print(f"Successfully saved {len(gdf_wgs84)} parcels to '{output_filepath}'")

    # Option B: Pre-compressed Gzip file (for basic servers). For this to work properly with OpenLayers, serve the file with the correct Content-Encoding: gzip and Content-Type: application/json headers.
    # import gzip
    # output_filename_gz = "parcels.geojson.gz"
    # with gzip.open(output_filename_gz, 'wt', encoding='utf-8') as f:
    #     f.write(gdf_wgs84.to_json())
    # print(f"Successfully saved compressed parcels to '{output_filename_gz}'")

    # return gdf_wgs84 # Return the re-projected GeoDataFrame

def gdf_load_from_file(input_filepath: str) -> gpd.GeoDataFrame | None:
    if not os.path.exists(input_filepath):
        print(f"File '{input_filepath}' does not exist.", file=sys.stderr)
        return None

    try:
        gdf = gpd.read_file(input_filepath)
        # print(f"Successfully loaded {len(gdf)} parcels from '{input_filepath}'")
        return gdf
    except Exception as e:
        print(f"Error loading file '{input_filepath}': {e}", file=sys.stderr)
        return None

def get_intersections_with_protected_areas(gdf: gpd.GeoDataFrame | None, status_filepath: str):
    protected_areas = [
        # {
        #     "name": 'rezervacie',
        #     "path": os.path.join(PROTECTED_AREAS_DATA_DIR, 'sz_protection_degree', 'sz_protection_degree_stupen5.gpkg'),
        #     "attrs": ['registry_n', 'site_name', 'category_i'],
        # },
        {
            "name": '5st_konsUEV',
            "path": os.path.join(PROTECTED_AREAS_DATA_DIR, 'konsolidovane_UEV', 'konsolidovane_UEV_st5.gpkg'),
            "attrs": ['NAZOV_UEV', 'KOD_UEV'],
        },
        {
            "name": 'UEV',
            "path": os.path.join(PROTECTED_AREAS_DATA_DIR, 'chranene_uzemia_uev', 'chranene_uzemia_uevPolygon.shp'),
            "attrs": ['NATIONALSI', 'SITETITLE_'],
        },
        {
            "name": "MCHU",
            "path": os.path.join(PROTECTED_AREAS_DATA_DIR, 'chranene_uzemia_mchu', 'chranene_uzemia_mchuPolygon.shp'),
            "attrs": ['NATIONALSI', 'SITETITLE_'],
        },
        {
            "name": "CHVU",
            "path": os.path.join(PROTECTED_AREAS_DATA_DIR, 'chranene_uzemia_chvu', 'chranene_uzemia_chvuPolygon.shp'),
            "attrs": ['NATIONALSI', 'SITETITLE_'],
        },
        {
            "name": "UNESCO",
            "path": os.path.join(PROTECTED_AREAS_DATA_DIR, 'ws_unesco', 'ws_unescoPolygon.shp'),
            "attrs": ['Nazov_chra', 'Kod_chrane'],
        },
    ]
    if gdf is None or gdf.empty:
        return {}

    intersections = {}
    for area in protected_areas:
        area_name = area['name']
        area_path = area['path']
        area_attrs = area['attrs']
        try:
            # print(f"Checking for intersection with '{area_name}' layer...")
            if area_path.endswith('.gpkg'):
                protected_gdf = gpd.read_file(area_path)
            else:
                protected_gdf = gpd.read_file(area_path, encoding='cp1250')

            # Ensure CRS match, reproject if necessary
            if protected_gdf.crs != gdf.crs:
                # print(f"Reprojecting gdf from {gdf.crs} to {protected_gdf.crs} for intersection check.")
                gdf_proj = gdf.to_crs(protected_gdf.crs)
            else:
                gdf_proj = gdf

            # Perform spatial join to find intersections
            intersecting_parcels = gpd.sjoin(gdf_proj, protected_gdf, how="inner", predicate="intersects")

            # print('intersecting_parcels:', intersecting_parcels)
            # print('intersecting_parcels columns:', intersecting_parcels.columns)
            if not intersecting_parcels.empty:
                print(f"Found {len(intersecting_parcels)} intersecting parcels with '{area_name}'.")
                # Store relevant info about the intersection
                df_for_export = intersecting_parcels.copy()
                
                if 'label' in df_for_export.columns:
                    df_for_export.rename(columns={'label': 'parcel_label'}, inplace=True)
                elif 'display_name' in df_for_export.columns:
                    df_for_export.rename(columns={'display_name': 'parcel_label'}, inplace=True)

                columns_to_extract = ['parcel_label'] + area_attrs
                # Filter columns that actually exist in the dataframe
                columns_to_extract = [col for col in columns_to_extract if col in df_for_export.columns]
                
                intersections[area_name] = df_for_export[columns_to_extract].to_dict(orient='records')
        except Exception as e:
            log_status(status_filepath, "warning", f"Could not process protected area layer '{area_name}' from {area_path}: {e}")

    return intersections

def test_get_geometry_of_a_parcel_set():
    # test_data = {'kraj': None, 'okres': 'Malacky', 'obec': 'Marianka', 'katastralne_uzemia': [], 'nazov_lokality': None}
    # test_data = {'kraj': None, 'okres': 'Komárno', 'obec': 'Komárno', 'katastralne_uzemia': [{'nazov': 'Komárno', 'parcely': [{'typ': None, 'cisla': ['6441/1']}]}], 'nazov_lokality': None}
    # test_data = {'kraj': None, 'okres': 'Komárno', 'obec': 'Kolárovo', 'katastralne_uzemia': [{'nazov': 'Kolárovo', 'parcely': [{'typ': None, 'cisla': ['28445/37']}, {'typ': None, 'cisla': ['28447/1']}, {'typ': None, 'cisla': ['28451/743']}]}], 'nazov_lokality': None}
    # test_data = {'kraj': None, 'okres': 'Bardejov', 'obec': 'Bardejov', 'katastralne_uzemia': [{'nazov': 'Bardejov', 'parcely': [{'typ': 'C KN', 'cisla': ['4945/79', '4945/80', '4945/81', '4945/82', '4945/93']}]}], 'nazov_lokality': None}
    # test_data = {'kraj': None, 'okres': 'Nové Mesto nad Váhom', 'obec': 'Kočovce', 'katastralne_uzemia': [], 'nazov_lokality': 'IBV TOP DLHÉ DIELY'}
    # test_data = {'kraj': 'Trenciansky', 'okres': 'Prievidza', 'obec': 'Handlova', 'katastralne_uzemia': [{'nazov': 'Handlova', 'parcely': [{'typ': 'E-KN', 'cisla': ['18032/1']}]}], 'nazov_lokality': 'ŽST Handlova, v km. 18,455 - 18,465'}
    # test_data = {'kraj': None, 'okres': 'Čadca', 'obec': 'Svrčinovec', 'katastralne_uzemia': [], 'nazov_lokality': 'Skladová hala METALCOM'}
    # test_data = {'kraj': 'Žilinský Kraj', 'okres': 'Liptovský Mikuláš', 'obec': 'Liptovský Mikuláš', 'katastralne_uzemia': [], 'nazov_lokality': 'Územný plán mesta Liptovský Mikuláš – Zmeny a doplnky č. 7'}
    # test_data = {'kraj': None, 'okres': 'Žarnovica', 'obec': 'Nová Baňa, Brehy, Rudno nad Hronom, Voznica', 'katastralne_uzemia': [{'nazov': 'Brehy', 'parcely': [{'typ': None, 'cisla': ['1215/1', '1215/2', '1216/1', '1442/1', '1448/6', '1437', '1438/1', '1438/2', '1438/3', '1439/2', '1442/2', '1445', '1446', '1447', '1448/1', '1448/5', '1448/2', '1139', '1143', '1144', '1156', '1341/3', '1461/12', '1448/7']}]}, {'nazov': 'Nová Baňa', 'parcely': [{'typ': None, 'cisla': ['1349/1', '1348', '1349', '1349/2', '1355', '1356', '5104/3', '6492/24', '6492/26', '30000', '1595/1', '5314', '1341/32', '1357']}]}, {'nazov': 'Rudno nad Hronom', 'parcely': [{'typ': None, 'cisla': ['400/6', '400/8', '461/4', '461/7', '481/6', '241/2', '241/3', '242/3', '242/2', '243/1', '246/1', '244', '245/4', '257/1', '258', '261/1', '261/2', '262', '263/1', '264', '266/2', '351/2', '354', '367/2', '366/2', '368/1', '368/2', '461/2', '769/3', '769/4', '771', '239', '352', '854/3', '857/2', '259', '349/1', '257/2', '349/2', '417/10', '60/1', '351/3', '353', '366/11', '858/1', '853/2', '366/1', '871', '869/2', '886/2', '461/1', '461/2', '461/3', '882/3']}]}, {'nazov': 'Voznica', 'parcely': [{'typ': None, 'cisla': ['427', '430', '440/2', '461/2', '310', '312', '327', '728/3', '728/9']}]}], 'nazov_lokality': 'ochrannom pásme/pod elektrickým vedením VN č. 305_k20'}
    # test_data = {'kraj': 'Banskobystrický kraj', 'okres': 'Rimavská Sobota', 'obec': None, 'katastralne_uzemia': [{'nazov': 'Dudikovany', 'parcely': [{'typ': 'C-KN', 'cisla': ['1115', '1114', '1151']}]}, {'nazov': 'Padarovce', 'parcely': [{'typ': 'C-KN', 'cisla': ['837', '893', '894', '921', '924', '925', '926', '1030', '896']}]}, {'nazov': 'Drienčany', 'parcely': [{'typ': 'C-KN', 'cisla': ['824', '825', '826']}]}, {'nazov': 'Ostrany', 'parcely': [{'typ': 'E-KN', 'cisla': ['272/45']}]}, {'nazov': 'Vyšný Blh', 'parcely': [{'typ': 'C-KN', 'cisla': ['3218']}]}], 'nazov_lokality': None}
    test_data = {'kraj': 'Košický kraj', 'okres': 'Košice', 'obec': None, 'katastralne_uzemia': [], 'nazov_lokality': 'NPR Sivec'}

    gdf = get_geometry_of_a_parcel_set(test_data, '/tmp/status.json')
    if gdf is None or gdf.empty:
        print('No geometries found.')
        return
    print('gdf columns:', gdf.columns)
    columns_to_print = [col for col in ['label', 'nationalCadastralReference', 'areaValue'] if col in gdf.columns]
    if columns_to_print:
        print(gdf[columns_to_print])
    else:
        print(gdf)

def test_get_geometry_of_a_geoname():
    # gdf = get_geometry_of_a_geoname('Námestie sv. Egídia', '', '', 'Prešovský kraj', '/tmp/status.json')
    # gdf = get_geometry_of_a_geoname('Udava', '', '', '', '/tmp/status.json')
    # gdf = get_geometry_of_a_geoname('Leňušská', '', 'Banská Bystrica', 'Banskobystrický kraj', '/tmp/status.json')
    # gdf = get_geometry_of_a_geoname('Môlčanský potok', '', 'Banská Bystrica', 'Banskobystrický kraj', '/tmp/status.json')
    gdf = get_geometry_of_a_geoname('NPR Sivec', '', 'Košice', 'Košický kraj', '/tmp/status.json')
    if gdf is None or gdf.empty:
        print('No geometries found.')
        return
    print('gdf columns:', gdf.columns)
    columns_to_print = [col for col in ['category', 'type', 'addresstype', 'name', 'display_name'] if col in gdf.columns]
    if columns_to_print:
        print(gdf[columns_to_print].to_string())
    else:
        print(gdf)

if __name__ == '__main__':
    # test_get_parcels_by_nationalCadastralReference()
    # test_get_geometry_of_a_parcel_set()
    test_get_geometry_of_a_geoname()

    # assert get_nationalCadastralZoningReferences('Abrahámovce', okres='Bardejov')[0] == '800066'
    # assert get_nationalCadastralZoningReferences('Abrahámovce', okres='Kežmarok')[0] == '800074'

    # nationalCadastralZoningReferences = get_nationalCadastralZoningReferences('Hnilec', okres='Spišská Nová Ves')
    # print('nationalCadastralZoningReferences:', nationalCadastralZoningReferences)
    # zone = get_cadastral_zone(nationalCadastralZoningReferences[0], 'C')
    # print('zone:', zone)
    # gdf_save_to_file(zone, '/tmp/zone_hnilec.geojson')
