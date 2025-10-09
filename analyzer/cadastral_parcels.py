import requests
import geopandas as gpd
import io
import csv
import os


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
            print(f"Parcela '{parcel_label}' v k.ú. '{cadastral_area_name}' nebola nájdená.")
            return None
            
        gdf = gpd.read_file(io.StringIO(data))
        return gdf

    except requests.exceptions.RequestException as e:
        print(f"Nastala chyba pri komunikácii so serverom: {e}")
        # Vypíšeme aj obsah odpovede, aby sme videli prípadnú chybovú hlášku
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

if __name__ == '__main__':
    # --- Hlavná časť programu ---

    # 1. Získanie polygónu parcely
    katastralne_uzemie = "Trnava"
    cislo_parcely = "2158/2"

    katastralne_uzemie = "Badín"
    cislo_parcely = "1616/1"

    # Test offline function
    nationalCadastralZoningReference = get_cadastral_unit_offline(katastralne_uzemie)
    # nationalCadastralZoningReference = get_cadastral_unit_online(katastralne_uzemie)
    print('nationalCadastralZoningReference:', nationalCadastralZoningReference)



    parcela_gdf = get_parcel_polygon(nationalCadastralZoningReference, cislo_parcely)

    if parcela_gdf is not None and not parcela_gdf.empty:
        print(f"Úspešne načítaný polygón pre parcelu {cislo_parcely} v k.ú. {katastralne_uzemie}.")
        print("CRS parcely:", parcela_gdf.crs)
        print("parcela:", parcela_gdf)
        print("geometria parcely:", parcela_gdf.geometry)

        # Export do CSV (s kódovaním UTF-8 pre slovenskú diakritiku)
        try:
            # Pre čistejší export môžeme vyhodiť stĺpec s geometriou
            parcela_gdf.to_csv("parcela_data.csv", index=False, encoding='utf-8-sig')
            print("\nDáta boli úspešne vyexportované do 'parcela_data.csv'")
        except Exception as e:
            print(f"\nNepodarilo sa uložiť CSV: {e}")
