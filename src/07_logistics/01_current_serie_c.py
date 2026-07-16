import os
import pandas as pd
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import time
from geopy.distance import geodesic
import io

# --- CONFIGURATION ---
MATCHES_FILE = r'data\01_raw\jogos_serie_c_2026.csv'
GEO_FILE = r'data\03_final\all_unique_teams_geolocalization.csv'
OUTPUT_LOG = r'data\05_logistics\log_viagens_serie_c_2026.csv'
OUTPUT_TOTALS = r'data\05_logistics\custo_total_clubes_serie_c_2026.csv'

OSRM_URL = "http://router.project-osrm.org/route/v1/driving"
AIRPORTS_CSV_URL = "https://davidmegginson.github.io/ourairports-data/airports.csv"

# Logistical threshold: If one-way road distance > 800 km, use airplane.
THRESHOLD_KM = 800.0 

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
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
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
            time.sleep(1) # Throttle
            return dist_km, tempo_h
    except Exception as e:
        print(f"[WARNING] OSRM routing failed: {e}")
    
    return None, None

def load_brazilian_airports():
    print("[INIT] Downloading global airports dataset...")
    response = HTTP_SESSION.get(AIRPORTS_CSV_URL, timeout=15)
    response.raise_for_status()
    
    df_airports = pd.read_csv(io.StringIO(response.content.decode('utf-8')))
    br_airports = df_airports[
        (df_airports['iso_country'] == 'BR') & 
        (df_airports['type'].isin(['large_airport', 'medium_airport'])) &
        (df_airports['scheduled_service'] == 'yes')
    ].copy()
    
    print(f"[INIT] {len(br_airports)} commercial airports mapped.")
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

def main():
    print("="*70)
    print("CALCULATING SERIE C 2026 LOGISTICS (ROUND-TRIP + THRESHOLD)")
    print("="*70)

    # 1. Load Data
    airports_df = load_brazilian_airports()
    df_geo = pd.read_csv(GEO_FILE, sep=';', encoding='utf-8-sig')
    df_matches = pd.read_csv(MATCHES_FILE, sep=',', encoding='utf-8-sig')

    # 2. Build Geolocation Lookup Dictionary
    geo_lookup = {}
    for _, row in df_geo.iterrows():
        key = f"{str(row['clube']).upper().strip()}/{str(row['estado']).lower().strip()}"
        geo_lookup[key] = {
            'cidade': row['cidade'],
            'lat': float(row['latitude']),
            'lon': float(row['longitude']),
            'estadio': row['estadio']
        }

    match_logs = []
    club_totals = {}

    print(f"[PROCESS] Processing {len(df_matches)} matches...")

    # 3. Process Matches
    for i, row in df_matches.iterrows():
        rodada = row['rodada']
        mandante = str(row['mandante']).upper().strip()
        estado_m = str(row['estado_m']).lower().strip()
        visitante = str(row['visitante']).upper().strip()
        estado_v = str(row['estado_v']).lower().strip()

        key_m = f"{mandante}/{estado_m}"
        key_v = f"{visitante}/{estado_v}"

        # Initialize club in totals dict if not present
        if visitante not in club_totals:
            club_totals[visitante] = {'jogos_fora': 0, 'distancia_km': 0.0, 'tempo_h': 0.0}
        if mandante not in club_totals:
            club_totals[mandante] = {'jogos_fora': 0, 'distancia_km': 0.0, 'tempo_h': 0.0}

        geo_m = geo_lookup.get(key_m)
        geo_v = geo_lookup.get(key_v)

        if not geo_m or not geo_v:
            print(f"[WARNING] Missing geodata for {key_m} or {key_v}. Skipping match.")
            continue

        # Same city check (Derby)
        if geo_m['cidade'] == geo_v['cidade']:
            log = {
                'rodada': rodada, 'visitante': visitante, 'mandante': mandante,
                'modo': 'LOCAL', 'dist_ida_volta_km': 0, 'tempo_ida_volta_h': 0,
                'detalhes': "Mesma cidade. Custo zero considerado."
            }
            match_logs.append(log)
            club_totals[visitante]['jogos_fora'] += 1
            continue

        # Calculate one-way road distance to check threshold
        rod_dist, rod_tempo = get_osrm_route(geo_v['lat'], geo_v['lon'], geo_m['lat'], geo_m['lon'])
        
        if not rod_dist:
            print(f"[ERROR] Routing failed for {visitante} -> {mandante}")
            continue

        modo = "ROAD"
        dist_ida = rod_dist
        tempo_ida = rod_tempo
        detalhes = f"Ônibus: {dist_ida:.0f}km em {tempo_ida:.1f}h."

        # If exceeds threshold, switch to Multimodal
        if rod_dist > THRESHOLD_KM:
            aero_v = get_nearest_airport(geo_v['lat'], geo_v['lon'], airports_df)
            aero_m = get_nearest_airport(geo_m['lat'], geo_m['lon'], airports_df)

            if aero_v['iata_code'] != aero_m['iata_code']:
                modo = "FLIGHT"
                
                t1_d, t1_t = get_osrm_route(geo_v['lat'], geo_v['lon'], aero_v['latitude_deg'], aero_v['longitude_deg'])
                t3_d, t3_t = get_osrm_route(aero_m['latitude_deg'], aero_m['longitude_deg'], geo_m['lat'], geo_m['lon'])
                
                voo_d = geodesic((aero_v['latitude_deg'], aero_v['longitude_deg']), 
                                 (aero_m['latitude_deg'], aero_m['longitude_deg'])).kilometers * 1.15
                voo_t = (voo_d / 800.0) + 4.0 # +4h airport operations

                dist_ida = (t1_d or 0) + voo_d + (t3_d or 0)
                tempo_ida = (t1_t or 0) + voo_t + (t3_t or 0)
                
                detalhes = (f"Voo {aero_v['iata_code']}->{aero_m['iata_code']} "
                            f"({voo_d:.0f}km). Ônibus t1:{t1_d:.0f}km, t3:{t3_d:.0f}km.")

        # Apply Round-Trip multiplier
        dist_total = dist_ida * 2
        tempo_total = tempo_ida * 2

        log = {
            'rodada': rodada, 'visitante': visitante, 'mandante': mandante,
            'modo': modo, 'dist_ida_volta_km': round(dist_total, 1), 
            'tempo_ida_volta_h': round(tempo_total, 1), 'detalhes': detalhes
        }
        
        match_logs.append(log)
        
        # Accumulate totals
        club_totals[visitante]['jogos_fora'] += 1
        club_totals[visitante]['distancia_km'] += dist_total
        club_totals[visitante]['tempo_h'] += tempo_total

        if i % 10 == 0:
            print(f" -> Processed {i}/{len(df_matches)} matches...")

    # 4. Export Outputs
    os.makedirs(os.path.dirname(OUTPUT_LOG), exist_ok=True)
    
    df_logs = pd.DataFrame(match_logs)
    df_logs.to_csv(OUTPUT_LOG, index=False, sep=';', encoding='utf-8-sig')

    # Convert totals dict to dataframe and sort by most traveled
    df_totals = pd.DataFrame.from_dict(club_totals, orient='index').reset_index()
    df_totals = df_totals.rename(columns={'index': 'clube'})
    df_totals = df_totals.sort_values(by='distancia_km', ascending=False)
    
    df_totals.to_csv(OUTPUT_TOTALS, index=False, sep=';', encoding='utf-8-sig')

    print("\n" + "="*70)
    print("[SUCCESS] Logistics calculation complete!")
    print(f" -> Detailed logs: {OUTPUT_LOG}")
    print(f" -> Aggregated totals: {OUTPUT_TOTALS}")
    print("="*70)

if __name__ == "__main__":
    main()