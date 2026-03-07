import requests
import geopandas as gpd
import pandas as pd
from shapely.geometry import shape
import sys



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



if __name__ == '__main__':
    # gdf = get_geometry_of_a_geoname('Námestie sv. Egídia', '', '', 'Prešovský kraj', '/tmp/status.json')
    # gdf = get_geometry_of_a_geoname('Udava', '', '', '', '/tmp/status.json')
    # gdf = get_geometry_of_a_geoname('Leňušská', '', 'Banská Bystrica', 'Banskobystrický kraj', '/tmp/status.json')
    # gdf = get_geometry_of_a_geoname('Môlčanský potok', '', 'Banská Bystrica', 'Banskobystrický kraj', '/tmp/status.json')
    gdf = get_geometry_of_a_geoname('NPR Sivec', '', 'Košice', 'Košický kraj', '/tmp/status.json')
    if gdf is None or gdf.empty:
        print('No geometries found.')
        sys.exit(1)
    print('gdf columns:', gdf.columns)
    columns_to_print = [col for col in ['category', 'type', 'addresstype', 'name', 'display_name'] if col in gdf.columns]
    if columns_to_print:
        print(gdf[columns_to_print].to_string())
    else:
        print(gdf)