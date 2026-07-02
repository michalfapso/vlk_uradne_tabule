import requests
import geopandas as gpd
import pandas as pd
from shapely.geometry import shape
import sys
from gis_google_maps_geocoding import get_google_maps_geocoding
import re



def get_geometry_of_a_geoname(nazov_lokality: str, obec: str, okres: str, kraj: str, status_filepath: str) -> tuple[gpd.GeoDataFrame | None, str | None]:
    """
    Získa geometriu (polygón) lokality pomocou Nominatim API.
    Vráti tuple (GeoDataFrame, query_string).
    """ 
    nazov_lokality = nazov_lokality.replace('NPR ', '')
    nazov_lokality = nazov_lokality.replace('PR ', '')
    print('get_geometry_of_a_geoname nazov_lokality:', nazov_lokality)

    def get_url(query: str):
        base_url = f"https://nominatim.openstreetmap.org/search?format=geojson&polygon_geojson=1&accept-language=sk&q="
        full_url = f"{base_url}{query}"
        print('url:', full_url)
        # Nominatim requires a User-Agent header
        headers = {
            'User-Agent': 'VLK_Uradne_Nastenky_Analyzer/1.0'
        }
        response = requests.get(full_url, headers=headers)
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
                     return gpd.GeoDataFrame.from_features(valid_features, crs='EPSG:4326'), query
                else:
                     # Flat dicts
                     geometries = [shape(item.get('geojson') or item.get('geometry')) for item in valid_features]
                     df = pd.DataFrame(valid_features)
                     return gpd.GeoDataFrame(df, geometry=geometries, crs='EPSG:4326'), query
        return None, None

    if obec:
        query = f"{nazov_lokality}, {obec}, Slovensko"
        gdf, q = get_url(query)
        if gdf is not None:
            return gdf, q

    if okres:
        query = f"{nazov_lokality}, {okres}, Slovensko"
        gdf, q = get_url(query)
        if gdf is not None:
            return gdf, q

    if kraj:
        query = f"{nazov_lokality}, {kraj}, Slovensko"
        gdf, q = get_url(query)
        if gdf is not None:
            return gdf, q
        
    query = f"{nazov_lokality}, Slovensko"
    gdf, q = get_url(query)
    if gdf is not None:
        return gdf, q
        
    # Try to normalize the location name via google geocoding API
    normalized = get_google_maps_geocoding(f"{nazov_lokality}, {obec}, {okres}, {kraj}, Slovensko")
    print('normalized:', normalized)
    if normalized is None:
        return None, None
    normalized_geoname = normalized['formatted_address']

    gdf, q = get_url(normalized_geoname)
    if gdf is not None:
        return gdf, q

    # Try to remove ZIP code (PSČ)
    normalized_geoname2 = re.sub(r'\d{3} \d{2}', '', normalized_geoname)
    normalized_geoname2 = re.sub(r'\d{5}', '', normalized_geoname)

    if (normalized_geoname != normalized_geoname2):
        gdf, q = get_url(normalized_geoname2)
        if gdf is not None:
            return gdf, q

    return None, None



if __name__ == '__main__':
    # gdf, query = get_geometry_of_a_geoname('Námestie sv. Egídia', '', '', 'Prešovský kraj', '/tmp/status.json')
    # gdf, query = get_geometry_of_a_geoname('Udava', '', '', '', '/tmp/status.json')
    # gdf, query = get_geometry_of_a_geoname('Leňušská', '', 'Banská Bystrica', 'Banskobystrický kraj', '/tmp/status.json')
    # gdf, query = get_geometry_of_a_geoname('Môlčanský potok', '', 'Banská Bystrica', 'Banskobystrický kraj', '/tmp/status.json')
    # normalized = get_google_maps_geocoding('NPR Sivec, Košice, Košický kraj')
    # print('normalized:', normalized)
    # normalized_geoname = normalized['formatted_address']
    # gdf, query = get_geometry_of_a_geoname('NPR Sivec', '', 'Košice', 'Košický kraj', '/tmp/status.json')
    gdf, query = get_geometry_of_a_geoname('cintorín', 'Hriadky', 'Trebišov', 'Košický kraj', '/tmp/status.json')
    # gdf, query = get_geometry_of_a_geoname('Mútňanka', 'Novoť', 'Žilina', 'Žilinský kraj', '/tmp/status.json')
    # gdf, query = get_geometry_of_a_geoname(normalized_geoname, '', '', '', '/tmp/status.json')
    if gdf is None or gdf.empty:
        print('No geometries found.')
        sys.exit(1)
    print('Query used:', query)
    print('gdf columns:', gdf.columns)
    columns_to_print = [col for col in ['category', 'type', 'addresstype', 'name', 'display_name'] if col in gdf.columns]
    if columns_to_print:
        print(gdf[columns_to_print].to_string())
    else:
        print(gdf)