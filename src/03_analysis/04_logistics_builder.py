import os
import pandas as pd
import requests
import time
import itertools
from geopy.distance import geodesic
import io

# --- CONFIGURATION ---
INPUT_FILE = r'data\03_final\all_unique_teams_geolocalization.csv'
OUTPUT_FILE = r'data\03_final\logistics_matrix.csv'
OSRM_URL = "http://router.project-osrm.org/route/v1/driving"
AIRPORTS_CSV_URL = "https://davidmegginson.github.io/ourairports-data/airports.csv"

osrm_cache = {}

def get_osrm_route(lat1, lon1, lat2, lon2):
    coord_key = tuple(sorted([(round(lat1, 3), round(lon1, 3)), (round(lat2, 3), round(lon2, 3))]))
    
    if coord_key in osrm_cache:
        return osrm_cache[coord_key]
        
    url = f"{OSRM_URL}/{lon1},{lat1};{lon2},{lat2}?overview=false"
    
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=10)
        data = response.json()
        
        if data.get('code') == 'Ok':
            dist_km = data['routes'][0]['distance'] / 1000.0
            tempo_h = data['routes'][0]['duration'] / 3600.0
            osrm_cache[coord_key] = (dist_km, tempo_h)
            time.sleep(1.2) # Throttle to respect public API limits
            return dist_km, tempo_h
    except Exception as e:
        print(f"[Warning] OSRM routing failed: {e}")
        time.sleep(5) # Backoff on error
    
    return None, None

def load_brazilian_airports():
    print("[INIT] Downloading global airports dataset...")
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0'
    }
    
    response = requests.get(AIRPORTS_CSV_URL, headers=headers, timeout=15)
    response.raise_for_status() 
    
    df_airports = pd.read_csv(io.StringIO(response.content.decode('utf-8')))
    
    br_airports = df_airports[
        (df_airports['iso_country'] == 'BR') & 
        (df_airports['type'].isin(['large_airport', 'medium_airport'])) &
        (df_airports['scheduled_service'] == 'yes')
    ].copy()
    
    print(f"[INIT] {len(br_airports)} commercial airports mapped in Brazil.")
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
    nome_a, lat_a, lon_a = cidade_a['location_name'], cidade_a['lat'], cidade_a['lon']
    nome_b, lat_b, lon_b = cidade_b['location_name'], cidade_b['lat'], cidade_b['lon']
    
    rod_dist, rod_tempo = get_osrm_route(lat_a, lon_a, lat_b, lon_b)
    
    aero_a = get_nearest_airport(lat_a, lon_a, airports_df)
    aero_b = get_nearest_airport(lat_b, lon_b, airports_df)
    
    if aero_a['iata_code'] == aero_b['iata_code']:
        multi_dist = rod_dist
        multi_tempo = rod_tempo
        solucao_str = f"Local/Regional. Road only: {rod_dist:.0f}km ({rod_tempo:.1f}h)." if rod_dist else "Route Failed"
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
        "Dist_Multi_km": round(multi_dist, 1) if rod_dist else None,
        "Tempo_Multi_h": round(multi_tempo, 1) if rod_dist else None,
        "Solucao_Multimodal": solucao_str
    }

def main():
    print("="*80)
    print("SCALABLE LOGISTICS MATRIX BUILDER (ROAD vs MULTIMODAL)")
    print("="*80)
    
    airports_df = load_brazilian_airports()
    
    # 1. Load and extract unique cities from teams dataset
    df_teams = pd.read_csv(INPUT_FILE, sep=';', encoding='utf-8-sig')
    df_teams = df_teams.dropna(subset=['cidade', 'latitude', 'longitude'])
    
    df_cities = df_teams.drop_duplicates(subset=['estado', 'cidade']).copy()
    df_cities['location_name'] = df_cities['cidade'] + " (" + df_cities['estado'] + ")"
    
    cidades = df_cities[['location_name', 'latitude', 'longitude']].rename(
        columns={'latitude': 'lat', 'longitude': 'lon'}
    ).to_dict('records')
    
    print(f"[INFO] Extracted {len(cidades)} unique cities from database.")
    
    # 2. Generate all unique combinations
    todos_pares = list(itertools.combinations(cidades, 2))
    
    # 3. Checkpoint Logic (Resume if interrupted)
    pares_processados = set()
    resultados = []
    
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    
    if os.path.exists(OUTPUT_FILE):
        df_existente = pd.read_csv(OUTPUT_FILE, sep=';', encoding='utf-8-sig')
        for _, row in df_existente.iterrows():
            # Store tuple of sorted names to ensure bidirectional tracking
            pares_processados.add(tuple(sorted([row['Origem'], row['Destino']])))
        print(f"[INFO] Found existing matrix. {len(pares_processados)} routes already processed.")
        resultados = df_existente.to_dict('records')
    
    pares_pendentes = []
    for cid_a, cid_b in todos_pares:
        chave = tuple(sorted([cid_a['location_name'], cid_b['location_name']]))
        if chave not in pares_processados:
            pares_pendentes.append((cid_a, cid_b))
            
    print(f"[INFO] {len(pares_pendentes)} routes left to process.\n")
    
    # 4. Process pending pairs
    for i, (cid_a, cid_b) in enumerate(pares_pendentes, 1):
        print(f"Routing [{i}/{len(pares_pendentes)}]: {cid_a['location_name']} <-> {cid_b['location_name']}")
        
        res = process_city_pair(cid_a, cid_b, airports_df)
        resultados.append(res)
        
        # Save checkpoint every 10 iterations to prevent data loss
        if i % 10 == 0 or i == len(pares_pendentes):
            df_temp = pd.DataFrame(resultados)
            df_temp.to_csv(OUTPUT_FILE, index=False, sep=';', encoding='utf-8-sig')
            print(f" -> Checkpoint saved ({len(resultados)} total routes).")

    print("\n" + "="*80)
    print("PROCESS COMPLETE! Matrix generated successfully.")
    print(f"Master file saved at: {OUTPUT_FILE}")
    print("="*80)

if __name__ == "__main__":
    main()