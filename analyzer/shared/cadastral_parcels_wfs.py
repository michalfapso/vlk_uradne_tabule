import requests
import geopandas as gpd
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

    Parcely katastra nehnuteľností C https://inspirews.skgeodesy.sk/geoserver/cp/ows?service=wfs&version=2.0.0&request=getcapabilities
    Parcely katastra nehnuteľností E https://inspirews.skgeodesy.sk/geoserver/cp_uo/ows?service=wfs&version=2.0.0&request=getcapabilities
    """

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36'
    }

    # Group parcels by cadasterType
    parcels_by_type = {'C': [], 'E': []}
    for item in zoningReferenceParcelsList:
        parcels_by_type[item.cadasterType].append(item)

    # Define endpoints and typeNames for each cadaster type
    type_configs = {
        'C': {
            'url': "https://inspirews.skgeodesy.sk/geoserver/cp/ows",
            'typeName': 'cp:CP.CadastralParcel'
        },
        'E': {
            'url': "https://inspirews.skgeodesy.sk/geoserver/cp_uo/ows",
            'typeName': 'cp_uo:CP.CadastralParcelUO'
        }
    }

    all_gdfs = []

    for cad_type, parcels_list in parcels_by_type.items():
        if not parcels_list:
            continue

        nationalCadastralReferences = []
        for zoningReferenceParcels in parcels_list:
            for parcelLabel in zoningReferenceParcels.parcelLabels:
                nationalCadastralReferences.append(f"{zoningReferenceParcels.nationalCadastralZoningReference}_{parcelLabel}.{cad_type}")

        if not nationalCadastralReferences:
            continue

        conditions = [
            f"""<PropertyIsEqualTo>
                   <PropertyName>nationalCadastralReference</PropertyName>
                   <Literal>{ref}</Literal>
               </PropertyIsEqualTo>""" for ref in nationalCadastralReferences
        ]

        xml_filter = f'<Filter xmlns="http://www.opengis.net/ogc"><Or>{"".join(conditions)}</Or></Filter>'
        print('xml_filter:', xml_filter)

        config = type_configs[cad_type]
        params = {
            'service': 'WFS',
            'version': '2.0.0',
            'request': 'GetFeature',
            'typeNames': config['typeName'],
            'outputFormat': 'application/json',
            'FILTER': xml_filter
        }

        try:
            print('url:', config['url'])
            response = requests.get(config['url'], params=params, headers=headers)
            response.raise_for_status()
            data = response.text
            if '"features": []' not in data and '"totalFeatures": 0' not in data:
                gdf = gpd.read_file(io.StringIO(data))
                all_gdfs.append(gdf)
        except requests.exceptions.RequestException as e:
            print(f"Nastala chyba pri komunikácii so serverom pre parcely typu '{cad_type}': {e}", file=sys.stderr)
            if e.response is not None:
                print("Odpoveď servera:", e.response.text, file=sys.stderr)
        except Exception as e:
            print(f"Nastala chyba pri spracovaní dát pre parcely typu '{cad_type}': {e}", file=sys.stderr)

    if not all_gdfs:
        print("Pre zadané referencie neboli nájdené žiadne parcely.", file=sys.stderr)
        return None

    return gpd.pd.concat(all_gdfs, ignore_index=True)


def get_parcel_polygon(nationalCadastralZoningReference: str, parcel_label: str) -> gpd.GeoDataFrame | None:
    """
    Získa geometriu (polygón) parcely C pomocou WFS služby INSPIRE.
    Používa XML filter na obídenie WAF (Web Application Firewall).

    Args:
        cadastral_area_name: Názov katastrálneho územia (veľkými písmenami, bez diakritiky).
        parcel_label: Číslo parcely v tvare '1234/56'.

    Returns:
        GeoDataFrame s geometriou parcely alebo None, ak sa parcela nenašla.
    """
    base_url = "https://inspirews.skgeodesy.sk/geoserver/cp/ows"
    
    # Hlavička, ktorá imituje bežný prehliadač
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36'
    }

    nationalCadastralReference = f"{nationalCadastralZoningReference}_{parcel_label}.C"

    # Štandardizovaný XML filter namiesto cql_filter
    # Je to robustnejší spôsob, ktorý WAF s menšou pravdepodobnosťou zablokuje.
    xml_filter = f"""
    <Filter xmlns="http://www.opengis.net/ogc">
        <And>
            <PropertyIsEqualTo>
                <PropertyName>nationalCadastralReference</PropertyName>
                <Literal>{nationalCadastralReference}</Literal>
            </PropertyIsEqualTo>
        </And>
    </Filter>
    """    

    xml_filter = f"""
    <Filter xmlns="http://www.opengis.net/ogc">
        <And>
            <PropertyIsLike wildCard="*" singleChar="#" escapeChar="!">
                <PropertyName>nationalCadastralReference</PropertyName>
                <Literal>{nationalCadastralZoningReference}_*</Literal>
            </PropertyIsLike>
        </And>
    </Filter>
    """

#   xml_filter = f"""
#   <Filter xmlns="http://www.opengis.net/ogc">
#       <And>
#           <PropertyIsEqualTo>
#               <PropertyName>label</PropertyName>
#               <Literal>{parcel_label}</Literal>
#           </PropertyIsEqualTo>
#       </And>
#   </Filter>
#   """    

    params = {
        'service': 'WFS',
        'version': '2.0.0',
        'request': 'GetFeature',
        'typeNames': 'cp:CP.CadastralParcel',
        'outputFormat': 'application/json',
        'FILTER': xml_filter  # Použijeme nový XML filter
    }

    try:
        # Pridali sme parameter headers
        response = requests.get(base_url, params=params, headers=headers)
        response.raise_for_status()

        data = response.text
        if '"features": []' in data or '"totalFeatures": 0' in data:
            print(f"Parcela '{parcel_label}' v k.ú. s referenciou '{nationalCadastralZoningReference}' nebola nájdená.", file=sys.stderr)
            return None
            
        gdf = gpd.read_file(io.StringIO(data))
        return gdf

    except requests.exceptions.RequestException as e:
        print(f"Nastala chyba pri komunikácii so serverom: {e}")
        if e.response is not None:
            print("Odpoveď servera:", e.response.text)
        return None
    except Exception as e:
        print(f"Nastala chyba pri spracovaní dát: {e}")
        return None



def get_cadastral_unit_online(unit_name: str) -> str | None:
    """
    Získa názov katastrálneho územia z vrstvy CadastralZoning na základe jeho ID.
    """
    base_url = "https://inspirews.skgeodesy.sk/geoserver/cp/ows"
    
    xml_filter = f"""
    <Filter xmlns="http://www.opengis.net/ogc">
        <PropertyIsEqualTo>
            <PropertyName>label</PropertyName>
            <Literal>{unit_name}</Literal>
        </PropertyIsEqualTo>
    </Filter>
    """
    
    params = {
        'service': 'WFS',
        'version': '1.1.0',
        'request': 'GetFeature',
        'typeNames': 'cp:CP.CadastralZoning', # Správna vrstva!
        'outputFormat': 'application/json',
        'FILTER': xml_filter
    }

#    try:
    response = requests.get(base_url, params=params, timeout=30)
    response.raise_for_status()
    data = response.json()
    print('data:', data)
    if data.get("features"):
        # Názov sa nachádza v poli 'properties' -> 'name'
        return data["features"][0]["properties"]["nationalCadastalZoningReference"]
    return "Názov sa nenašiel"
#    except Exception:
#        return "Chyba pri zisťovaní názvu"

def get_cadastral_unit_offline(katastralneUzemie, obec=None, okres=None, kraj=None):
    """
    Loads the file ../data/cadaster/USJ_hranice_0.csv and finds all rows matching the given arguments.
    NM2 is kraj, NM3 is okres, NM4 is obec, NM5 is katastralneUzemie.
    Returns a list of IDN5 values.
    """
    current_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(current_dir, '..', 'data', 'cadaster', 'USJ_hranice_0.csv')

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
        nationalCadastralZoningReference = get_cadastral_unit_offline(ku_name, obec, okres, kraj)
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
    return gdf


if __name__ == '__main__':
    # --- Hlavná časť programu ---

#   # 1. Získanie polygónu parcely
#   katastralne_uzemie = "Badín"
#   cislo_parcely = "1616/1"
# 
#   # Test offline function
#   nationalCadastralZoningReference = get_cadastral_unit_offline(katastralne_uzemie)
#   # nationalCadastralZoningReference = get_cadastral_unit_online(katastralne_uzemie)
#   print('nationalCadastralZoningReference:', nationalCadastralZoningReference)
# 
#   # Create a list of request objects
#   # parcel_requests = [
#   #     CadastralZoningReferenceParcels(
#   #         nationalCadastralZoningReference=nationalCadastralZoningReference,
#   #         cadasterType='C',
#   #         parcelLabels=[cislo_parcely]
#   #     )]
#   # parcela_gdf = get_geometry_of_cadastral_zone_parcels(parcel_requests)
#   parcela_gdf = get_parcel_polygon(nationalCadastralZoningReference, cislo_parcely)
# 
#   if parcela_gdf is not None and not parcela_gdf.empty:
#       print(f"Úspešne načítaný polygón pre parcelu {cislo_parcely} v k.ú. {katastralne_uzemie}.")
#       print("CRS parcely:", parcela_gdf.crs)
#       print("parcela:", parcela_gdf)
#       print("geometria parcely:", parcela_gdf.geometry)
# 
#       # Export do CSV (s kódovaním UTF-8 pre slovenskú diakritiku)
#       try:
#           # Pre čistejší export môžeme vyhodiť stĺpec s geometriou
#           parcela_gdf.to_csv("parcela_data.csv", index=False, encoding='utf-8-sig')
#           print("\nDáta boli úspešne vyexportované do 'parcela_data.csv'")
#       except Exception as e:
#           print(f"\nNepodarilo sa uložiť CSV: {e}")
#
#   sys.exit(0)

    # --- Testovanie funkcie get_geometry_of_cadastral_zone_parcels ---
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
        # },
        # {
        #   "nazov": "Vlkanová",
        #   "parcely": [
        #     {
        #       "typ": "C-KN",
        #       "cisla": [
        #         "499/33"
        #       ]
        #     }
        #   ]
        # },
        # {
        #   "nazov": "Kremnička",
        #   "parcely": [
        #     {
        #       "typ": "C-KN",
        #       "cisla": [
        #         "843/1",
        #         "841/1",
        #         "830/1",
        #         "829/7",
        #         "908/4",
        #         "906/1",
        #         "907/1",
        #         "867/1",
        #         "867/2",
        #         "869",
        #         "939/1",
        #         "908/1",
        #         "829/2",
        #         "512",
        #         "538",
        #         "486/5",
        #         "269/52",
        #         "272/8",
        #         "269/65",
        #         "269/2"
        #       ]
        #     }
        #   ]
        }
      ]
    }

    gdf = get_geometry_of_a_parcel_set(test_data)
    if gdf is not None and not gdf.empty:
        print("Úspešne načítaná geometria pre testovacie dáta.")
        print("CRS:", gdf.crs)
        print("geometria:", gdf.geometry)
