import os
import pandas as pd
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import time
from geopy.distance import geodesic
import io

# --- CONFIGURATION ---
SERIE_C_FILE = r'data\04_results\serie_c_final_proposal.csv'
SERIE_D_FILE = r'data\04_results\serie_d_final_proposal.csv'
OUTPUT_LOG = r'data\05_logistics\log_viagens_proposed_2026.csv'
OUTPUT_TOTALS = r'data\05_logistics\custo_total_proposed_2026.csv'

OSRM_URL = "http://router.project-osrm.org/route/v1/driving"
AIRPORTS_CSV_URL = "https://davidmegginson.github.io/ourairports-data/airports.csv"
THRESHOLD_KM = 800.0

TARGET_CLUBS = [
    "AMAZONAS/amazonas", "ANÁPOLIS/goias", "BARRA/santa_catarina", "BOTAFOGO/paraiba",
    "BRUSQUE/santa_catarina", "CAXIAS/rio_grande_do_sul", "CONFIANÇA/sergipe",
    "FERROVIÁRIA/sao_paulo", "FIGUEIRENSE/santa_catarina", "FLORESTA/ceara",
    "GUARANI/sao_paulo", "INTER DE LIMEIRA/sao_paulo", "ITABAIANA/sergipe",
    "ITUANO/sao_paulo", "MARANHÃO/maranhao", "MARINGÁ/parana", "PAYSANDU/para",
    "SANTA CRUZ/pernambuco", "VOLTA REDONDA/rio_de_janeiro", "YPIRANGA/rio_grande_do_sul"
]

osrm_cache = {}

def get_http_session():
    session = requests.Session()
    retry_strategy = Retry(total=4, backoff_factor=2, status_forcelist=[429, 500, 502, 503, 504], allowed_methods=["GET"])
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    session.headers.update({"User-Agent": "Mozilla/5.0"})
    return session

HTTP_SESSION = get_http_session()

def get_osrm_route(lat1, lon1, lat2, lon2):
    coord_key = tuple(sorted([(round(lat1, 3), round(lon1, 3)), (round(lat2, 3), round(lon2, 3))]))
    if coord_key in osrm_cache: return osrm_cache[coord_key]
        
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
        print(f"[WARNING] OSRM failed: {e}")
    return None, None

def load_brazilian_airports():
    print("[INIT] Downloading global airports dataset...")
    response = HTTP_SESSION.get(AIRPORTS_CSV_URL, timeout=15)
    df_airports = pd.read_csv(io.StringIO(response.content.decode('utf-8')))
    br_airports = df_airports[
        (df_airports['iso_country'] == 'BR') & 
        (df_airports['type'].isin(['large_airport', 'medium_airport'])) &
        (df_airports['scheduled_service'] == 'yes')
    ].copy()
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

def find_team_league(target_id, df_c, df_d):
    """Finds the team in the new structure and returns its opponents dataframe."""
    row_c = df_c[df_c['clube_id'] == target_id]
    if not row_c.empty:
        c_id = row_c.iloc[0]['cluster_k4']
        league_df = df_c[df_c['cluster_k4'] == c_id].copy()
        return league_df, f"Serie C (Macro {c_id})"
    
    row_d = df_d[df_d['clube_id'] == target_id]
    if not row_d.empty:
        c_id = row_d.iloc[0]['cluster_k4']
        # Handle North macro (0) logic dynamically
        sub_col = 'serie_d_k4' if c_id == 0 else 'serie_d_k3'
        
        # Fallback if specific sub_col not found
        if sub_col not in df_d.columns:
            sub_col = 'serie_d_k4' if 'serie_d_k4' in df_d.columns else 'cluster_k3'
            
        sub_id = row_d.iloc[0][sub_col]
        league_df = df_d[(df_d['cluster_k4'] == c_id) & (df_d[sub_col] == sub_id)].copy()
        return league_df, f"Serie D (Macro {c_id} | Sub {sub_id})"
    
    return pd.DataFrame(), "Not Found"

def main():
    print("="*80)
    print("CALCULATING PROPOSED CLUSTER LOGISTICS (TARGET: 20 CLUBS)")
    print("="*80)

    airports_df = load_brazilian_airports()
    
    # We assume Serie C file has been saved previously with the top 20 logic. 
    # If not, fallback to using cluster_k4 directly.
    df_c = pd.read_csv(SERIE_C_FILE, sep=';', encoding='utf-8-sig') if os.path.exists(SERIE_C_FILE) else pd.DataFrame()
    df_d = pd.read_csv(SERIE_D_FILE, sep=';', encoding='utf-8-sig') if os.path.exists(SERIE_D_FILE) else pd.DataFrame()

    match_logs = []
    club_totals = {}

    for target in TARGET_CLUBS:
        print(f"\n[PROCESS] Routing for {target}...")
        
        league_df, league_name = find_team_league(target, df_c, df_d)
        
        if league_df.empty:
            print(f" -> ❌ Skipped. Not found in C or D proposals.")
            continue
            
        print(f" -> Found in {league_name}. League size: {len(league_df)} clubs.")
        
        target_row = league_df[league_df['clube_id'] == target].iloc[0]
        opponents = league_df[league_df['clube_id'] != target]
        
        club_totals[target] = {'liga': league_name, 'jogos_fora': 0, 'distancia_km': 0.0, 'tempo_h': 0.0}
        
        for _, opp in opponents.iterrows():
            mandante = opp['clube_id']
            
            # Same city fast-check
            if target_row['lat'] == opp['lat'] and target_row['lon'] == opp['lon']:
                log = {
                    'visitante': target, 'mandante': mandante, 'liga': league_name,
                    'modo': 'LOCAL', 'dist_ida_volta_km': 0, 'tempo_ida_volta_h': 0,
                    'detalhes': "Mesma coordenada. Custo zero."
                }
                match_logs.append(log)
                club_totals[target]['jogos_fora'] += 1
                continue

            rod_dist, rod_tempo = get_osrm_route(target_row['lat'], target_row['lon'], opp['lat'], opp['lon'])
            
            if not rod_dist:
                print(f" -> [ERROR] Route failed: {target} to {mandante}")
                continue

            modo = "ROAD"
            dist_ida, tempo_ida = rod_dist, rod_tempo
            detalhes = f"Ônibus: {dist_ida:.0f}km em {tempo_ida:.1f}h."

            if rod_dist > THRESHOLD_KM:
                aero_v = get_nearest_airport(target_row['lat'], target_row['lon'], airports_df)
                aero_m = get_nearest_airport(opp['lat'], opp['lon'], airports_df)

                if aero_v['iata_code'] != aero_m['iata_code']:
                    modo = "FLIGHT"
                    t1_d, t1_t = get_osrm_route(target_row['lat'], target_row['lon'], aero_v['latitude_deg'], aero_v['longitude_deg'])
                    t3_d, t3_t = get_osrm_route(aero_m['latitude_deg'], aero_m['longitude_deg'], opp['lat'], opp['lon'])
                    
                    voo_d = geodesic((aero_v['latitude_deg'], aero_v['longitude_deg']), 
                                     (aero_m['latitude_deg'], aero_m['longitude_deg'])).kilometers * 1.15
                    voo_t = (voo_d / 800.0) + 4.0 

                    dist_ida = (t1_d or 0) + voo_d + (t3_d or 0)
                    tempo_ida = (t1_t or 0) + voo_t + (t3_t or 0)
                    
                    detalhes = (f"Voo {aero_v['iata_code']}->{aero_m['iata_code']} "
                                f"({voo_d:.0f}km). Ônibus t1:{t1_d or 0:.0f}km, t3:{t3_d or 0:.0f}km.")

            # Round Trip logic
            dist_total = dist_ida * 2
            tempo_total = tempo_ida * 2

            log = {
                'visitante': target, 'mandante': mandante, 'liga': league_name,
                'modo': modo, 'dist_ida_volta_km': round(dist_total, 1), 
                'tempo_ida_volta_h': round(tempo_total, 1), 'detalhes': detalhes
            }
            
            match_logs.append(log)
            club_totals[target]['jogos_fora'] += 1
            club_totals[target]['distancia_km'] += dist_total
            club_totals[target]['tempo_h'] += tempo_total

    # Output
    os.makedirs(os.path.dirname(OUTPUT_LOG), exist_ok=True)
    
    df_logs = pd.DataFrame(match_logs)
    if not df_logs.empty:
        df_logs.to_csv(OUTPUT_LOG, index=False, sep=';', encoding='utf-8-sig')

    df_totals = pd.DataFrame.from_dict(club_totals, orient='index').reset_index()
    if not df_totals.empty:
        df_totals = df_totals.rename(columns={'index': 'clube'})
        df_totals = df_totals.sort_values(by='distancia_km', ascending=False)
        df_totals.to_csv(OUTPUT_TOTALS, index=False, sep=';', encoding='utf-8-sig')

    print("\n" + "="*80)
    print(f"[SUCCESS] Computed logistics for {len(club_totals)} target clubs.")
    print(f" -> Detailed logs: {OUTPUT_LOG}")
    print(f" -> Aggregated totals: {OUTPUT_TOTALS}")
    print("="*80)

if __name__ == "__main__":
    main()