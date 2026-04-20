import requests
import pandas as pd
import time
import re
import os

# CONFIGURATION
USER_AGENT = 'XXX/2.0 (xxx@fgv.edu.br)'
HEADERS = {'User-Agent': USER_AGENT}
OUTPUT_PATH = os.path.join('data', '01_raw', 'all_clubs_wikidata_geodata.csv')

def get_initial_wikidata():
    """
    Executes a SPARQL query on Wikidata to fetch Brazilian football clubs.
    Retrieves headquarters, coordinates, foundation dates, and administrative units.
    """
    url = 'https://query.wikidata.org/sparql'
    
    query = """
    SELECT ?clubLabel ?wikiTitle ?hqLabel ?coords ?inception ?adminUnitLabel WHERE {
      { ?club wdt:P31 wd:Q476028 . }
      UNION
      { ?club wdt:P641 wd:Q191 . }
      
      ?club wdt:P17 wd:Q155 .
      
      ?article schema:about ?club;
               schema:isPartOf <https://pt.wikipedia.org/>;
               schema:name ?wikiTitle.
      
      OPTIONAL { ?club wdt:P159 ?hq . }
      OPTIONAL { ?club wdt:P625 ?coords . }
      OPTIONAL { ?club wdt:P571 ?inception . }
      OPTIONAL { ?club wdt:P131 ?adminUnit . }
               
      SERVICE wikibase:label { bd:serviceParam wikibase:language "pt". }
    }
    """
    try:
        r = requests.get(url, params={'format': 'json', 'query': query}, headers=HEADERS)
        r.raise_for_status()
        data = r.json()
        
        results = []
        for i in data['results']['bindings']:
            results.append({
                'nome_clube': i['clubLabel']['value'],
                'wiki_title': i['wikiTitle']['value'],
                'sede_wikidata': i.get('hqLabel', {}).get('value'),
                'coords_wikidata': i.get('coords', {}).get('value'),
                'inception': i.get('inception', {}).get('value'),
                'admin_unit': i.get('adminUnitLabel', {}).get('value')
            })
        return pd.DataFrame(results)
    except Exception as e:
        print(f"Query error: {e}")
        return pd.DataFrame()

def get_ibge_data():
    """
    Loads and merges IBGE municipality and state data for normalization.
    """
    url_mun = "https://raw.githubusercontent.com/kelvins/municipios-brasileiros/main/csv/municipios.csv"
    url_est = "https://raw.githubusercontent.com/kelvins/municipios-brasileiros/main/csv/estados.csv"
    
    mun = pd.read_csv(url_mun)
    est = pd.read_csv(url_est)
    
    return pd.merge(mun, est[['codigo_uf', 'nome', 'uf']], on='codigo_uf', suffixes=('_mun', '_estado'))

def extract_city_from_summary(wiki_title, city_list):
    """
    Fallback method to identify a city name within a Wikipedia page summary.
    """
    api_url = f"https://pt.wikipedia.org/api/rest_v1/page/summary/{wiki_title.replace(' ', '_')}"
    try:
        response = requests.get(api_url, headers=HEADERS, timeout=5)
        if response.status_code != 200: return None
        extract = response.json().get('extract', '')
        for city in city_list:
            if city in extract[:400]:
                return city
    except:
        pass
    return None

def main():
    """
    Main execution flow: fetches Wikidata, normalizes with IBGE, and exports CSV.
    """
    df_wikidata = get_initial_wikidata()
    df_ibge = get_ibge_data()
    city_names = df_ibge['nome_mun'].tolist()

    final_data = []

    for index, row in df_wikidata.iterrows():
        city_candidate = row['sede_wikidata']
        if not city_candidate or city_candidate not in city_names:
            city_candidate = extract_city_from_summary(row['wiki_title'], city_names)
        
        if city_candidate and city_candidate in city_names:
            info = df_ibge[df_ibge['nome_mun'] == city_candidate].iloc[0]
            
            lat, lon = info['latitude'], info['longitude']
            if row['coords_wikidata']:
                match = re.search(r'Point\(([-\d.]+) ([-\d.]+)\)', row['coords_wikidata'])
                if match:
                    lon, lat = match.groups()

            final_data.append({
                'nome_clube': row['nome_clube'],
                'estado': info['nome_estado'],
                'uf': info['uf'],
                'cidade': city_candidate,
                'latitude': lat,
                'longitude': lon,
                'inception': row['inception'],
                'codigo_ibge': info['codigo_ibge']
            })

    if final_data:
        os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
        df_final = pd.DataFrame(final_data).drop_duplicates(subset=['nome_clube', 'cidade'])
        df_final.to_csv(OUTPUT_PATH, index=False, sep=';', encoding='utf-8-sig')
        print(f"Process complete. {len(df_final)} clubs mapped to {OUTPUT_PATH}")

if __name__ == "__main__":
    main()