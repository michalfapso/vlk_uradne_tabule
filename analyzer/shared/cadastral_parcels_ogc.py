import requests
import geopandas as gpd
import pandas as pd
import io
import csv, sys
import os
from dataclasses import dataclass, field
from typing import List, Dict, Any, Literal

@dataclass
class CadastralZoningReferenceParcels:
    """Represents a request for parcels within a single cadastral zone."""
    nationalCadastralZoningReference: str
    cadasterType: Literal['C', 'E']
    parcelLabels: List[str]

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

        nationalCadastralReferences = []
        for zoningReferenceParcels in parcels_list:
            for parcelLabel in zoningReferenceParcels.parcelLabels:
                nationalCadastralReferences.append(f"{zoningReferenceParcels.nationalCadastralZoningReference}_{parcelLabel}.{cad_type}")

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
            try:
                response = requests.get(next_url, headers=headers, timeout=90)
                response.raise_for_status()
                data = response.json()
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
            except requests.exceptions.RequestException as e:
                print(f"Chyba pri sťahovaní dát: {e}")
                if e.response:
                    print("Odpoveď servera:", e.response.text)
                return None

    if not all_features:
        print("Pre zadané referencie neboli nájdené žiadne parcely.")
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

    if crs_data and 'crs' in crs_data:
        final_gdf.set_crs(crs_data['crs']['properties']['name'], inplace=True)
    else:
        # Fallback CRS if not found in any response. EPSG:5514 is S-JTSK.
        print("Warning: CRS not found in API response, falling back to EPSG:5514.", file=sys.stderr)
        final_gdf.set_crs("EPSG:5514", inplace=True)

    return final_gdf


def get_parcels_by_nationalCadastralReference(national_references: list[str]) -> gpd.GeoDataFrame | None:
    """
    Získa geometrie pre presne zadaný zoznam parciel pomocou ich unikátneho 
    identifikátora 'nationalCadastralReference'.
    Používa moderné OGC API - Features s pokročilým CQL2 filtrom.
    """
    if not national_references:
        print("Zoznam referencií je prázdny.")
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
        try:
            response = requests.get(next_url, headers=headers, timeout=90)
            response.raise_for_status()
            data = response.json()
            
            if "features" in data and data["features"]:
                all_features.extend(data["features"])
            
            next_url = None
            if "links" in data:
                for link in data["links"]:
                    if link.get("rel") == "next":
                        next_url = link.get("href")
                        break
        except requests.exceptions.RequestException as e:
            print(f"Chyba pri sťahovaní dát: {e}")
            if e.response:
                print("Odpoveď servera:", e.response.text)
            return None

    if not all_features:
        print("Pre zadané referencie neboli nájdené žiadne parcely.")
        return None

    final_gdf = gpd.GeoDataFrame.from_features(all_features)
    if 'crs' in data:
        final_gdf.set_crs(data['crs']['properties']['name'], inplace=True)

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


def get_nationalCadastralZoningReference(katastralneUzemie, obec=None, okres=None, kraj=None):
    """
    Loads the file ../data/cadaster/USJ_hranice_0.csv and finds all rows matching the given arguments.
    NM2 is kraj, NM3 is okres, NM4 is obec, NM5 is katastralneUzemie.
    Returns a list of IDN5 values.
    """
    current_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(current_dir, '..', '..', 'data', 'cadaster', 'USJ_hranice_0.csv')

    found_ids = []
    with open(file_path, mode='r', encoding='utf-8') as csvfile:
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
            match = True
            if kraj and row[kraj_idx] != kraj:
                match = False
            if okres and row[okres_idx] != okres:
                match = False
            if obec and row[obec_idx] != obec:
                match = False
            if katastralneUzemie and row[ku_idx] != katastralneUzemie:
                match = False
            
            if match:
                found_ids.append(row[idn5_idx])

    if len(found_ids) > 1:
        raise Exception(f"Nájdených viacero ID pre zadané parametre: {found_ids}")

    if not found_ids:
        raise Exception("Nenašlo sa žiadne katastrálne uzemie pre zadané parametre.")

    return found_ids[0]


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
    try:
        response = requests.get(url, headers=headers, timeout=90)
        response.raise_for_status()
        data = response.json()
        if "features" in data and data["features"]:
            features.extend(data["features"])
    except requests.exceptions.RequestException as e:
        print(f"Chyba pri sťahovaní dát: {e}")
        if e.response:
            print("Odpoveď servera:", e.response.text)
        return None

    if not features:
        print("Pre zadané nationalCadastralZoningReference nebolo nájdené žiadne katastrálne územie.")
        return None

    final_gdf = gpd.GeoDataFrame.from_features(features)
    if 'crs' in data:
        final_gdf.set_crs(data['crs']['properties']['name'], inplace=True)

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
    kraj  = data.get('kraj')
    okres = data.get('okres')
    obec  = data.get('obec')
    if kraj is not None or okres is not None:
        obec = None # If kraj or okres is specified, ignore obec to allow for zones outside the obec. Maybe also okres could be ignored when kraj is specified?

    request : List[CadastralZoningReferenceParcels] = []
    for ku in data.get('katastralne_uzemia', []):
        ku_name = ku.get('nazov')
        nationalCadastralZoningReference = get_nationalCadastralZoningReference(ku_name, obec, okres, kraj)
        for parcel_set in ku.get('parcely', []):
            parcel_type = parcel_set.get('typ', '').upper()
            parcel_type = 'C' if 'C' in parcel_type else 'E' if 'E' in parcel_type else None
            parcel_set['typ'] = parcel_type  # Normalize type
            
            request.append(CadastralZoningReferenceParcels(
                nationalCadastralZoningReference=nationalCadastralZoningReference,
                cadasterType=parcel_type,
                parcelLabels=parcel_set.get('cisla', [])
            ))
            
    gdf = get_geometry_of_cadastral_zone_parcels(request)

    if gdf is None or gdf.empty:
        print("No geometries were found, so no file will be saved.", file=sys.stderr)
        return None

    return gdf

def save_to_file(gdf: gpd.GeoDataFrame, output_filepath: str):
    # Re-project the GeoDataFrame to the standard web map projection (EPSG:4326 - WGS 84)
    # GeoJSON standard officially recommends WGS 84. OpenLayers can handle the
    # reprojection from 4326 to 3857 (Web Mercator) on the fly.
    print(f"Original CRS: {gdf.crs}")
    gdf_wgs84 = gdf.to_crs(epsg=4326)
    print(f"Data re-projected to: {gdf_wgs84.crs}")

    # Save the re-projected data to a GeoJSON file
    # Option A: Standard GeoJSON (Recommended for servers with on-the-fly compression)
    gdf_wgs84.to_file(output_filepath, driver='GeoJSON')
    print(f"Successfully saved {len(gdf_wgs84)} parcels to '{output_filepath}'")

    # Option B: Pre-compressed Gzip file (for basic servers). For this to work properly with OpenLayers, serve the file with the correct Content-Encoding: gzip and Content-Type: application/json headers.
    # import gzip
    # output_filename_gz = "parcels.geojson.gz"
    # with gzip.open(output_filename_gz, 'wt', encoding='utf-8') as f:
    #     f.write(gdf_wgs84.to_json())
    # print(f"Successfully saved compressed parcels to '{output_filename_gz}'")

    # return gdf_wgs84 # Return the re-projected GeoDataFrame

def load_from_file(input_filepath: str) -> gpd.GeoDataFrame | None:
    if not os.path.exists(input_filepath):
        print(f"File '{input_filepath}' does not exist.", file=sys.stderr)
        return None

    try:
        gdf = gpd.read_file(input_filepath)
        print(f"Successfully loaded {len(gdf)} parcels from '{input_filepath}'")
        return gdf
    except Exception as e:
        print(f"Error loading file '{input_filepath}': {e}", file=sys.stderr)
        return None

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
    test_get_geometry_of_a_parcel_set()

    # assert get_nationalCadastralZoningReference('Abrahámovce', okres='Bardejov') == '800066'
    # assert get_nationalCadastralZoningReference('Abrahámovce', okres='Kežmarok') == '800074'

    # nationalCadastralZoningReference = get_nationalCadastralZoningReference('Abrahámovce', okres='Bardejov')
    # print('nationalCadastralZoningReference:', nationalCadastralZoningReference)
    # zone = get_cadastral_zone(nationalCadastralZoningReference, 'C')
    # print('zone:', zone)
