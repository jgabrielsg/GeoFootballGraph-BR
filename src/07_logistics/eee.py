import os
import pandas as pd
import requests
import time
import itertools
from geopy.distance import geodesic

# --- CONFIGURATION ---
INPUT_FILE = 'data/03_final/unique_teams_geo_final.csv'
OUTPUT_FILE = 'outputs/svelte_data/road_matrix_under_1000.csv'
OSRM_URL = "http://router.project-osrm.org/route/v1/driving"
DISTANCE_THRESHOLD_KM = 1000.0
BATCH_SIZE = 50

def get_osrm_route(lat1, lon1, lat2, lon2):
    """Calls OSRM to get real driving distance and duration."""
    url = f"{OSRM_URL}/{lon1},{lat1};{lon2},{lat2}?overview=false"
    
    try:
        headers = {'User-Agent': 'TCC-Football-Logistics/1.0'}
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('code') == 'Ok':
                dist_km = data['routes'][0]['distance'] / 1000.0
                tempo_h = data['routes'][0]['duration'] / 3600.0
                #time.sleep(1)
                return round(dist_km, 2), round(tempo_h, 2)
        elif response.status_code == 429:
            print("[WARNING] Rate limited by OSRM. Sleeping for 30s...")
            time.sleep(30)
            return get_osrm_route(lat1, lon1, lat2, lon2)
            
    except Exception as e:
        print(f"[WARNING] OSRM route failed: {e}")
        time.sleep(3)
        
    return None, None

def main():
    print("="*70)
    print("BUILDING ROAD LOGISTICS MATRIX (< 1000KM RADIUS)")
    print("="*70)

    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)

    # 1. LOAD AND EXTRACT UNIQUE CITIES
    try:
        df_teams = pd.read_csv(INPUT_FILE, sep=';', encoding='utf-8-sig')
    except FileNotFoundError:
        print(f"[ERROR] Input file not found: {INPUT_FILE}")
        return

    # Drop missing coordinates
    df_teams = df_teams.dropna(subset=['lat', 'lon', 'cidade', 'estado'])
    
    # Create unique city identifiers (e.g., "Campinas/SP")
    df_teams['uf_slug'] = df_teams['estado'].apply(lambda x: str(x).strip().upper())
    df_cities = df_teams.drop_duplicates(subset=['cidade', 'uf_slug']).copy()
    df_cities['location_id'] = df_cities['cidade'] + "/" + df_cities['uf_slug']
    
    cities = df_cities[['location_id', 'lat', 'lon']].to_dict('records')
    print(f"[INFO] Extracted {len(cities)} unique cities.")

    # 2. GENERATE ALL PAIRS
    all_pairs = list(itertools.combinations(cities, 2))
    print(f"[INFO] Total mathematical pairs: {len(all_pairs)}")

    # 3. PRE-FILTER PAIRS BY STRAIGHT-LINE DISTANCE
    valid_pairs = []
    for city_a, city_b in all_pairs:
        straight_km = geodesic((city_a['lat'], city_a['lon']), (city_b['lat'], city_b['lon'])).kilometers
        if straight_km <= DISTANCE_THRESHOLD_KM:
            valid_pairs.append((city_a, city_b, straight_km))
            
    print(f"[INFO] Pairs under {DISTANCE_THRESHOLD_KM}km threshold: {len(valid_pairs)}")

    # 4. LOAD CHECKPOINT (RESUME CAPABILITY)
    processed_pairs = set()
    results = []

    if os.path.exists(OUTPUT_FILE):
        df_existing = pd.read_csv(OUTPUT_FILE, sep=';', encoding='utf-8-sig')
        for _, row in df_existing.iterrows():
            # Create a sorted tuple to track bidirectional processing
            pair_key = tuple(sorted([row['origem'], row['destino']]))
            processed_pairs.add(pair_key)
        
        results = df_existing.to_dict('records')
        print(f"[INFO] Checkpoint loaded. {len(processed_pairs)} routes already processed.")

    # Filter out already processed pairs
    pending_pairs = []
    for ca, cb, st_km in valid_pairs:
        pair_key = tuple(sorted([ca['location_id'], cb['location_id']]))
        if pair_key not in processed_pairs:
            pending_pairs.append((ca, cb, st_km))

    print(f"[INFO] {len(pending_pairs)} routes remaining to call OSRM.\n")

    # 5. PROCESS PENDING PAIRS
    total_pending = len(pending_pairs)
    
    for i, (city_a, city_b, straight_km) in enumerate(pending_pairs, 1):
        orig_id = city_a['location_id']
        dest_id = city_b['location_id']
        
        print(f"[{i}/{total_pending}] Routing: {orig_id} <-> {dest_id} (Straight: {straight_km:.1f}km)")
        
        rod_km, rod_h = get_osrm_route(city_a['lat'], city_a['lon'], city_b['lat'], city_b['lon'])
        
        results.append({
            "origem": orig_id,
            "destino": dest_id,
            "dist_reta_km": round(straight_km, 2),
            "dist_rod_km": rod_km,
            "tempo_rod_h": rod_h
        })

        # Save checkpoint in batches
        if i % BATCH_SIZE == 0 or i == total_pending:
            df_temp = pd.DataFrame(results)
            df_temp.to_csv(OUTPUT_FILE, index=False, sep=';', encoding='utf-8-sig')
            print(f" ---> Checkpoint saved ({len(results)} total routes mapped).")

    print("\n" + "="*70)
    print("[SUCCESS] All road routes mapped successfully!")
    print(f"Master file saved at: {OUTPUT_FILE}")
    print("="*70)

if __name__ == "__main__":
    main()