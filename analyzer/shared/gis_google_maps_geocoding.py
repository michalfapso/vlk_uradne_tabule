import os
import requests

def get_google_maps_geocoding(lokalita_text, api_key=None):
    if api_key is None:
        api_key = os.environ.get("GOOGLE_GEOCODING_API_KEY")
    
    if not api_key:
        # print("Warning: GOOGLE_GEOCODING_API_KEY not set")
        return None

    # Pridáme "Slovensko" pre lepšiu presnosť, prípadne môžeš pridať aj okres/kraj z JSONu
    query = f"{lokalita_text}, Slovensko"
    url = f"https://maps.googleapis.com/maps/api/geocode/json?address={query}&key={api_key}"

    response = requests.get(url)
    
    if response.status_code == 200:
        data = response.json()
        if data['status'] == 'OK':
            location = data['results'][0]['geometry']['location']
            formatted_address = data['results'][0]['formatted_address']
            
            return {
                "lat": location['lat'],
                "lon": location['lng'],
                "formatted_address": formatted_address
            }
    return None

if __name__ == '__main__':
    # Príklad použitia:
    GOOGLE_GEOCODING_API_KEY = os.environ.get("GOOGLE_GEOCODING_API_KEY", "")
    vysledok_google = get_google_maps_geocoding("PR Tarbucka", GOOGLE_GEOCODING_API_KEY)
    print("Google Maps vrátil:", vysledok_google)
    # Očakávaný výstup: {'lat': 48.3842, 'lon': 21.7824, 'adresa': 'Tarbucka, 076 43 Streda nad Bodrogom, Slovakia'}