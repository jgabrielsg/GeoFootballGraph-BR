import pandas as pd
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import time
import itertools
from geopy.distance import geodesic
import io

OSRM_URL = "http://router.project-osrm.org/route/v1/driving"
AIRPORTS_CSV_URL = "https://davidmegginson.github.io/ourairports-data/airports.csv"

osrm_cache = {}

def get_http_session():
    """Creates a requests Session with retries and browser-like headers."""
    session = requests.Session()
    retry_strategy = Retry(
        total=4,
        backoff_factor=2,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"]
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
    })
    return session

HTTP_SESSION = get_http_session()

def get_osrm_route(lat1, lon1, lat2, lon2):
    coord_key = tuple(sorted([(round(lat1, 3), round(lon1, 3)), (round(lat2, 3), round(lon2, 3))]))
    
    if coord_key in osrm_cache:
        return osrm_cache[coord_key]
        
    url = f"{OSRM_URL}/{lon1},{lat1};{lon2},{lat2}?overview=false"
    try:
        response = HTTP_SESSION.get(url, timeout=10)
        data = response.json()
        if data.get('code') == 'Ok':
            dist_km = data['routes'][0]['distance'] / 1000.0
            tempo_h = data['routes'][0]['duration'] / 3600.0
            osrm_cache[coord_key] = (dist_km, tempo_h)
            time.sleep(1)
            return dist_km, tempo_h
    except Exception as e:
        print(f"[Warning] OSRM routing failed: {e}")
    
    return None, None

def load_brazilian_airports():
    print("Downloading global airports dataset...")
    response = HTTP_SESSION.get(AIRPORTS_CSV_URL, timeout=15)
    response.raise_for_status()
    
    df_airports = pd.read_csv(io.StringIO(response.content.decode('utf-8')))
    
    # Filter: BR, medium/large size, scheduled service active
    br_airports = df_airports[
        (df_airports['iso_country'] == 'BR') & 
        (df_airports['type'].isin(['large_airport', 'medium_airport'])) &
        (df_airports['scheduled_service'] == 'yes')
    ].copy()
    
    print(f"[{len(br_airports)}] commercial airports mapped in Brazil.")
    return br_airports

def get_nearest_airport(lat, lon, airports_df):
    min_dist = float('inf')
    best_airport = None
    
    for _, aero in airports_df.iterrows():
        dist = geodesic((lat, lon), (aero['latitude_deg'], aero['longitude_deg'])).kilometers
        if dist < min_dist:
            min_dist = dist
            best_airport = aero
            
    return best_airport

def process_city_pair(cidade_a, cidade_b, airports_df):
    nome_a, lat_a, lon_a = cidade_a['cidade'], cidade_a['lat'], cidade_a['lon']
    nome_b, lat_b, lon_b = cidade_b['cidade'], cidade_b['lat'], cidade_b['lon']
    
    # 1. Direct road route
    rod_dist, rod_tempo = get_osrm_route(lat_a, lon_a, lat_b, lon_b)
    
    # 2. Nearest airports
    aero_a = get_nearest_airport(lat_a, lon_a, airports_df)
    aero_b = get_nearest_airport(lat_b, lon_b, airports_df)
    
    # 3. Multimodal logic
    if aero_a['iata_code'] == aero_b['iata_code']:
        multi_dist = rod_dist
        multi_tempo = rod_tempo
        solucao_str = f"Local trip. Road only: {rod_dist:.0f}km ({rod_tempo:.1f}h)."
    else:
        t1_dist, t1_tempo = get_osrm_route(lat_a, lon_a, aero_a['latitude_deg'], aero_a['longitude_deg'])
        t1_dist, t1_tempo = t1_dist or 0, t1_tempo or 0
        
        voo_dist_geo = geodesic((aero_a['latitude_deg'], aero_a['longitude_deg']), 
                                (aero_b['latitude_deg'], aero_b['longitude_deg'])).kilometers
        voo_dist_real = voo_dist_geo * 1.15
        voo_tempo = (voo_dist_real / 800.0) + 4.0
        
        t3_dist, t3_tempo = get_osrm_route(aero_b['latitude_deg'], aero_b['longitude_deg'], lat_b, lon_b)
        t3_dist, t3_tempo = t3_dist or 0, t3_tempo or 0
        
        multi_dist = t1_dist + voo_dist_real + t3_dist
        multi_tempo = t1_tempo + voo_tempo + t3_tempo
        
        solucao_str = (
            f"{nome_a} -> [Bus {t1_dist:.0f}km, {t1_tempo:.1f}h] -> "
            f"Aero({aero_a['iata_code']}) -> [Flight {voo_dist_real:.0f}km, {voo_tempo:.1f}h] -> "
            f"Aero({aero_b['iata_code']}) -> [Bus {t3_dist:.0f}km, {t3_tempo:.1f}h] -> {nome_b}"
        )

    return {
        "Origem": nome_a,
        "Destino": nome_b,
        "Dist_Rod_km": round(rod_dist, 1) if rod_dist else None,
        "Tempo_Rod_h": round(rod_tempo, 1) if rod_tempo else None,
        "Dist_Multi_km": round(multi_dist, 1) if multi_dist else None,
        "Tempo_Multi_h": round(multi_tempo, 1) if multi_tempo else None,
        "Solucao_Multimodal": solucao_str
    }

def main():
    print("="*80)
    print("LOGISTICS MATRIX GENERATOR (ROAD vs MULTIMODAL)")
    print("="*80)
    
    airports_df = load_brazilian_airports()
    
    cidades = [
        {"cidade": "Porto Alegre (RS)", "lat": -30.0346, "lon": -51.2177},
        {"cidade": "Manaus (AM)", "lat": -3.1190, "lon": -60.0217},
        {"cidade": "Volta Redonda (RJ)", "lat": -22.5230, "lon": -44.1041},
        {"cidade": "Pelotas (RS)", "lat": -31.7654, "lon": -52.3376},
        {"cidade": "Mirassol (SP)", "lat": -20.8197, "lon": -49.5072}
    ]
    
    pares = list(itertools.combinations(cidades, 2))
    print(f"\nMapping {len(pares)} unique routes...")
    
    resultados = []
    for i, (cid_a, cid_b) in enumerate(pares, 1):
        print(f"Processing [{i}/{len(pares)}]: {cid_a['cidade']} <-> {cid_b['cidade']}")
        res = process_city_pair(cid_a, cid_b, airports_df)
        resultados.append(res)
        
    df_resultados = pd.DataFrame(resultados)
    
    output_file = "matriz_logistica_teste.csv"
    df_resultados.to_csv(output_file, index=False, sep=';', encoding='utf-8-sig')
    
    print("\n" + "="*80)
    print("RESULTS SAMPLE:")
    for _, row in df_resultados.head().iterrows():
        print(f"\nRoute: {row['Origem']} -> {row['Destino']}")
        print(f" - Road:       {row['Dist_Rod_km']} km | {row['Tempo_Rod_h']} h")
        print(f" - Multimodal: {row['Dist_Multi_km']} km | {row['Tempo_Multi_h']} h")
        print(f" - Details:    {row['Solucao_Multimodal']}")

if __name__ == "__main__":
    main()