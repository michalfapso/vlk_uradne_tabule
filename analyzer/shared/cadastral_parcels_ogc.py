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

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROTECTED_AREAS_DATA_DIR = os.path.join(SCRIPT_DIR, '..', '..', 'data', 'protected_areas')
CADASTER_DATA_DIR = os.path.join(SCRIPT_DIR, '..', '..', 'data', 'cadaster')

@dataclass
class CadastralZoningReferenceParcels:
    """Represents a request for parcels within a single cadastral zone."""
    nationalCadastralZoningReference: str
    cadasterType: Literal['C', 'E']
    parcelLabels: List[str]

def _make_request(method, url, caller_name, headers, **kwargs):
    retry_delays = [5, 10, 30, 60, 120]  # Delays in seconds for retries
    for attempt, delay in enumerate(retry_delays + [None]):
        try:
            print(f'{caller_name}() request {method} url:', url)
            if method.upper() == 'GET':
                response = requests.get(url, headers=headers, **kwargs)
            elif method.upper() == 'POST':
                response = requests.post(url, headers=headers, **kwargs)
            else:
                raise ValueError("Unsupported HTTP method")
            response.raise_for_status()
            print('response:', response)
            print('response:', response.text)
            return response.json()
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 500 and delay is not None:
                print(f"Server vrátil chybu 500. Opakujem pokus o {delay} sekúnd... (Pokus {attempt + 1}/{len(retry_delays)})", file=sys.stderr)
                time.sleep(delay)
                continue
            print(f"{caller_name}() Chyba pri sťahovaní dát (HTTP): {e}", file=sys.stderr)
            if e.response:
                print(f"Odpoveď servera: {e.response.text}", file=sys.stderr)
            return None  # Non-500 error or retries exhausted
        except requests.exceptions.RequestException as e:
            print(f"{caller_name}() Chyba pri sťahovaní dát: {e}", file=sys.stderr)
            return None  # Other request exception
    return None

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
            data = _make_request('GET', next_url, 'get_geometry_of_cadastral_zone_parcels', headers=headers, timeout=90)
            print('get_geometry_of_cadastral_zone_parcels() data:', data)
            if data is None:
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
        data = _make_request('GET', next_url, 'get_parcels_by_nationalCadastralReference', headers=headers, timeout=90)
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
    """
    Loads the file ../data/cadaster/USJ_hranice_0.csv and finds all rows matching the given arguments.
    NM2 is kraj, NM3 is okres, NM4 is obec, NM5 is katastralneUzemie.
    Returns a list of IDN5 values.
    """
    file_path = os.path.join(CADASTER_DATA_DIR, 'USJ_hranice_0.csv')

    kraj = re.sub(r'\s*kraj', '', kraj) if kraj else None

    # Normalizácia vstupných parametrov
    norm_kraj = _normalize_string(kraj)
    norm_okres = _normalize_string(okres)
    norm_obec = _normalize_string(obec)
    norm_ku = _normalize_string(katastralneUzemie)
    print('get_nationalCadastralZoningReferences() norm_kraj:', norm_kraj, 'norm_okres:', norm_okres, 'norm_obec:', norm_obec, 'norm_ku:', norm_ku)

    found_ids = []
    # print(f'get_nationalCadastralZoningReferences() Loading cadastral data from {file_path}...')
    with open(file_path, mode='r', encoding='utf-8') as csvfile:
        # print('get_nationalCadastralZoningReferences() CSV file opened successfully.')
        reader = csv.reader(csvfile)
        header = next(reader)  # Skip header
        
        # Map columns to indices
        try:
            kraj_idx = header.index('NM2')
            okres_idx = header.index('NM3')
            obec_idx = header.index('NM4')
            ku_idx = header.index('NM5')
            idn5_idx = header.index('IDN5')
        except ValueError as e:
            print(f"Chyba: Stĺpec {e} sa nenašiel v CSV súbore.")
            return []

        for row in reader:
            # print('row:', row)
            # Porovnávame normalizované hodnoty
            if norm_kraj and _normalize_string(row[kraj_idx]) != norm_kraj:
                continue
            if norm_okres and _normalize_string(row[okres_idx]) != norm_okres:
                continue
            if norm_obec and _normalize_string(row[obec_idx]) != norm_obec:
                continue
            if norm_ku and _normalize_string(row[ku_idx]) != norm_ku:
                continue
            
            found_ids.append(row[idn5_idx])

    if len(found_ids) > 1:
        raise Exception(f"Nájdených viacero ID pre zadané parametre: {found_ids}")

    if not found_ids:
        if (obec is not None) and (katastralneUzemie is not None):
            # Skúsime odstrániť obec z názvu katastrálneho územia
            katastralneUzemie2 = re.sub(r'^' + obec + r'\s*-\s*', '', katastralneUzemie)
            if katastralneUzemie2 != katastralneUzemie:
                return get_nationalCadastralZoningReferences(katastralneUzemie2, obec, okres, kraj)
        if (okres is not None) and (katastralneUzemie is not None):
            # Skúsime odstrániť okres z názvu katastrálneho územia
            katastralneUzemie2 = re.sub(r'^' + okres + r'\s*-\s*', '', katastralneUzemie)
            if katastralneUzemie2 != katastralneUzemie:
                return get_nationalCadastralZoningReferences(katastralneUzemie2, obec, okres, kraj)
        if obec is not None:
            # Skúsime zavolať bez obce
            return get_nationalCadastralZoningReferences(katastralneUzemie, None, okres, kraj)
        if okres is not None:
            # Skúsime zavolať bez okresu
            return get_nationalCadastralZoningReferences(katastralneUzemie, obec, None, kraj)
        if kraj is not None:
            # Skúsime zavolať bez kraja
            return get_nationalCadastralZoningReferences(katastralneUzemie, obec, okres, None)
        raise Exception(f"Nenašlo sa žiadne katastrálne uzemie pre zadané parametre kraj:{kraj}, okres:{okres}, obec:{obec}, katastralneUzemie:{katastralneUzemie}")

    return found_ids


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
    data = _make_request('GET', url, 'get_cadastral_zone', headers=headers, timeout=90)
    print('get_cadastral_zone() data:', data)
    if data is None:
        return None

    if "features" in data and data["features"]:
        print('get_cadastral_zone() found features:', data["features"])
        features.extend(data["features"])
    if not features:
        print("Pre zadané nationalCadastralZoningReference nebolo nájdené žiadne katastrálne územie.", file=sys.stderr)
        return None

    properties_list = [f['properties'] for f in features]
    df = pd.DataFrame(properties_list)
    geometries = [gpd.geoseries.shapely.geometry.shape(f['geometry']) if f.get('geometry') else None for f in features]
    final_gdf = gpd.GeoDataFrame(df, geometry=geometries)

    # print('get_cadastral_zone() final_gdf columns:', final_gdf.columns)
    final_gdf.set_crs("EPSG:4258", inplace=True)

    return final_gdf


def get_geometry_of_a_parcel_set(data: dict):
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

    request : List[CadastralZoningReferenceParcels] = []
    katastralne_uzemia = data.get('katastralne_uzemia', [])
    if katastralne_uzemia:
        for ku in katastralne_uzemia:
            ku_name = ku.get('nazov')
            print(f'ku_name:{ku_name} obec:{obec} okres:{okres} kraj:{kraj}')
            nationalCadastralZoningReferences = get_nationalCadastralZoningReferences(ku_name, obec, okres, kraj)
            print('nationalCadastralZoningReferences:', nationalCadastralZoningReferences)
            for nationalCadastralZoningReference in nationalCadastralZoningReferences:
                # print(f'get_geometry_of_a_parcel_set() nationalCadastralZoningReference: {nationalCadastralZoningReference}')
                parcely = ku.get('parcely', [])
                if not parcely:
                    parcely = [{"typ": "C", "cisla": []}] # If no parcels specified, request the whole cadastral zone
                for parcel_set in parcely:
                    # print('get_geometry_of_a_parcel_set() parcel_set:', parcel_set)
                    parcel_type = parcel_set.get('typ', '').upper()
                    parcel_type = 'C' if 'C' in parcel_type else 'E' if 'E' in parcel_type else 'C'
                    parcel_set['typ'] = parcel_type  # Normalize type
                    
                    request.append(CadastralZoningReferenceParcels(
                        nationalCadastralZoningReference=nationalCadastralZoningReference,
                        cadasterType=parcel_type,
                        parcelLabels=parcel_set.get('cisla', [])
                    ))
    else:
        nationalCadastralZoningReferences = get_nationalCadastralZoningReferences(None, obec, okres, kraj)
        for nationalCadastralZoningReference in nationalCadastralZoningReferences:
            request.append(CadastralZoningReferenceParcels(
                nationalCadastralZoningReference=nationalCadastralZoningReference,
                cadasterType='C',
                parcelLabels=[]
            ))


    # print('get_geometry_of_a_parcel_set() data:', data) 
    # print('get_geometry_of_a_parcel_set() request:', request) 
    gdf = get_geometry_of_cadastral_zone_parcels(request)

    if gdf is None or gdf.empty:
        print("No geometries were found, so no file will be saved.", file=sys.stderr)
        return None

    return gdf

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
        {
            "name": 'rezervacie',
            "path": os.path.join(PROTECTED_AREAS_DATA_DIR, 'sz_protection_degree', 'sz_protection_degree_stupen5.gpkg'),
            "attrs": ['registry_n', 'site_name', 'category_i'],
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
                df_for_export.rename(columns={'label': 'parcel_label'}, inplace=True)
                columns_to_extract = ['parcel_label'] + area_attrs
                intersections[area_name] = df_for_export[columns_to_extract].to_dict(orient='records')
        except Exception as e:
            log_status(status_filepath, "warning", f"Could not process protected area layer '{area_name}' from {area_path}: {e}")

    return intersections

def test_get_geometry_of_a_parcel_set():
    test_data = {
      "kraj": None,
      "okres": "Banská Bystrica",
      "obec": "Banská Bystrica",
      "katastralne_uzemia": [
        {
          "nazov": "Badín",
          "parcely": [
            {
              "typ": "C-KN",
              "cisla": [
                "1295",
                "1616/1",
                "1522",
                "1246/1",
                "1248/1",
                "1599/4",
                "1507/3",
                "1320/8",
                "1313/2",
                "1314/3"
              ]
            }
          ]
        },
        {
          "nazov": "Vlkanová",
          "parcely": [
            {
              "typ": "C-KN",
              "cisla": [
                "499/33"
              ]
            }
          ]
        },
        {
          "nazov": "Kremnička",
          "parcely": [
            {
              "typ": "C-KN",
              "cisla": [
                "843/1",
                "841/1",
                "830/1",
                "829/7",
                "908/4",
                "906/1",
                "907/1",
                "867/1",
                "867/2",
                "869",
                "939/1",
                "908/1",
                "829/2",
                "512",
                "538",
                "486/5",
                "269/52",
                "272/8",
                "269/65",
                "269/2"
              ]
            }
          ]
        }
      ]
    }

    gdf = get_geometry_of_a_parcel_set(test_data)
    print(gdf[['label', 'nationalCadastralReference', 'areaValue']])

if __name__ == '__main__':
    # test_get_parcels_by_nationalCadastralReference()
    # test_get_geometry_of_a_parcel_set()

    # assert get_nationalCadastralZoningReference('Abrahámovce', okres='Bardejov') == '800066'
    # assert get_nationalCadastralZoningReference('Abrahámovce', okres='Kežmarok') == '800074'

    nationalCadastralZoningReference = get_nationalCadastralZoningReference('Hnilec', okres='Spišská Nová Ves')
    print('nationalCadastralZoningReference:', nationalCadastralZoningReference)
    zone = get_cadastral_zone(nationalCadastralZoningReference, 'C')
    print('zone:', zone)
    gdf_save_to_file(zone, '/tmp/zone_hnilec.geojson')
