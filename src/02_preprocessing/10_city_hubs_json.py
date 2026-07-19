import os
import json
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import time
from geopy.distance import geodesic
import io

# --- CONFIGURATION ---
TEAMS_DB_FILE = r'outputs\svelte_data\teams_db.json'
OUTPUT_FILE = r'outputs\svelte_data\city_hubs.json'

OSRM_URL = "http://router.project-osrm.org/route/v1/driving"
AIRPORTS_CSV_URL = "https://davidmegginson.github.io/ourairports-data/airports.csv"

# In-memory cache to avoid redundant OSRM calls for teams in the same city
osrm_cache = {}

def get_http_session():
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
    session.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"})
    return session

HTTP_SESSION = get_http_session()

def load_airports_db():
    print("[INIT] Downloading global airports dataset...")
    import pandas as pd
    response = HTTP_SESSION.get(AIRPORTS_CSV_URL, timeout=15)
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
            time.sleep(1.2) # Throttle to prevent rate limit
            return dist_km, tempo_h
    except Exception as e:
        print(f"[WARNING] OSRM failed for coords {lat1},{lon1} -> {lat2},{lon2}: {e}")
        time.sleep(3) # Backoff
    
    return None, None

def main():
    print("="*70)
    print("BUILDING CITY HUBS JSON (OSRM + AIRPORTS HUB LOGIC)")
    print("="*70)

    if not os.path.exists(TEAMS_DB_FILE):
        print(f"[ERROR] Required input file not found: {TEAMS_DB_FILE}")
        return

    with open(TEAMS_DB_FILE, 'r', encoding='utf-8') as f:
        teams_db = json.load(f)

    airports_df = load_airports_db()
    
    city_hubs = {}
    total_teams = len(teams_db)
    
    print(f"[PROCESS] Processing {total_teams} teams to find their local Hub...")

    for i, (team_id, data) in enumerate(teams_db.items(), 1):
        team_lat = data['lat']
        team_lon = data['lon']
        
        # 1. Find nearest commercial airport
        nearest_aero = get_nearest_airport(team_lat, team_lon, airports_df)
        aero_iata = str(nearest_aero['iata_code'])
        aero_lat = float(nearest_aero['latitude_deg'])
        aero_lon = float(nearest_aero['longitude_deg'])
        
        # 2. Get OSRM Road routing to the airport
        dist_km, tempo_h = get_osrm_route(team_lat, team_lon, aero_lat, aero_lon)
        
        # 3. Fallback Math if OSRM fails (Geodesic * 1.3 Tortuosity Factor, assumed 50km/h urban speed)
        if dist_km is None:
            geo_dist = geodesic((team_lat, team_lon), (aero_lat, aero_lon)).kilometers
            dist_km = geo_dist * 1.3
            tempo_h = dist_km / 50.0
            print(f" -> [FALLBACK] Used mathematical estimation for {team_id}")

        city_hubs[team_id] = {
            "lat": team_lat,
            "lon": team_lon,
            "hub_aero_iata": aero_iata,
            "hub_aero_lat": aero_lat,
            "hub_aero_lon": aero_lon,
            "dist_ate_aero_km": round(dist_km, 2),
            "tempo_ate_aero_h": round(tempo_h, 2)
        }

        if i % 25 == 0 or i == total_teams:
            print(f" -> Completed {i}/{total_teams} teams...")

    # 4. Save JSON
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(city_hubs, f, indent=2, ensure_ascii=False)

    print("\n" + "="*70)
    print(f"[SUCCESS] City Hubs compiled successfully for {len(city_hubs)} teams.")
    print(f" -> Output saved to: {OUTPUT_FILE}")
    print("="*70)

if __name__ == "__main__":
    main()