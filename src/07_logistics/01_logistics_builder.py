import pandas as pd
import networkx as nx
import json
import os
import requests
import time
from geopy.distance import geodesic

# --- CONFIGURATION ---
TEAMS_FILE = 'data/03_final/unique_teams_geo_final.csv'
AIR_GRAPH_FILE = 'outputs/graphs/brazil_air_network_2025.graphml'
OUTPUT_HUBS = 'outputs/svelte_data/city_hubs.json'

OSRM_URL = "http://router.project-osrm.org/route/v1/driving"

def get_osrm_distance(lat1, lon1, lat2, lon2):
    """Fetches real driving distance (km) and time (h) between two coordinates."""
    url = f"{OSRM_URL}/{lon1},{lat1};{lon2},{lat2}?overview=false"
    
    try:
        headers = {'User-Agent': 'TCC-Football-Logistics-Research/1.0'}
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('code') == 'Ok':
                dist_km = data['routes'][0]['distance'] / 1000.0
                tempo_h = data['routes'][0]['duration'] / 3600.0
                time.sleep(1) # Throttle to respect API limits
                return round(dist_km, 2), round(tempo_h, 2)
    except Exception as e:
        print(f"[WARNING] OSRM failed for {lat1},{lon1} to {lat2},{lon2}: {e}")
        time.sleep(2)
        
    # Fallback to straight-line distance * 1.3 if OSRM fails or has no route
    fallback_km = round(geodesic((lat1, lon1), (lat2, lon2)).kilometers * 1.3, 2)
    fallback_h = round(fallback_km / 70.0, 2) # Assume 70km/h average speed
    return fallback_km, fallback_h

def load_valid_airports():
    """Extracts valid commercial airports from the ANAC network graph."""
    if not os.path.exists(AIR_GRAPH_FILE):
        raise FileNotFoundError(f"Missing {AIR_GRAPH_FILE}. Run air network builder first.")
        
    G = nx.read_graphml(AIR_GRAPH_FILE)
    airports = []
    
    for node, data in G.nodes(data=True):
        airports.append({
            'icao': str(node),
            'name': data.get('name', 'Unknown'),
            'city': data.get('city', 'Unknown'),
            'state': data.get('state', 'Unknown'),
            'lat': float(data.get('lat', 0)),
            'lon': float(data.get('lon', 0))
        })
        
    print(f"[INFO] Loaded {len(airports)} active commercial airports from network graph.")
    return airports

def get_nearest_airport(club_lat, club_lon, airports_list):
    """Finds the closest airport by straight-line distance."""
    min_dist = float('inf')
    best_airport = None
    
    for aero in airports_list:
        # Some imported nodes might have 0,0 coords if data was missing
        if aero['lat'] == 0 and aero['lon'] == 0:
            continue
            
        dist = geodesic((club_lat, club_lon), (aero['lat'], aero['lon'])).kilometers
        if dist < min_dist:
            min_dist = dist
            best_airport = aero
            
    return best_airport

def main():
    print("="*70)
    print("MAPPING CLUBS TO NEAREST COMMERCIAL AIRPORTS (HUBS)")
    print("="*70)

    os.makedirs(os.path.dirname(OUTPUT_HUBS), exist_ok=True)

    try:
        df_teams = pd.read_csv(TEAMS_FILE, sep=';', encoding='utf-8-sig')
    except FileNotFoundError:
        print(f"[ERROR] Teams file not found at {TEAMS_FILE}")
        return

    # Drop teams with missing coordinates
    df_teams = df_teams.dropna(subset=['lat', 'lon', 'clube', 'estado'])
    
    try:
        valid_airports = load_valid_airports()
    except Exception as e:
        print(e)
        return

    city_hubs = {}
    total_teams = len(df_teams)
    
    # Optional check to avoid re-running long OSRM calls if JSON already exists
    if os.path.exists(OUTPUT_HUBS):
        with open(OUTPUT_HUBS, 'r', encoding='utf-8') as f:
            city_hubs = json.load(f)
        print(f"[INFO] Loaded existing hubs. Resuming missing entries...")

    print(f"[PROCESS] Processing {total_teams} clubs...")

    for i, row in df_teams.iterrows():
        # Standardize ID matching the rest of the project: "CLUBE/estado"
        clube = str(row['clube']).strip().upper()
        estado = str(row['estado']).strip().lower()
        team_id = f"{clube}/{estado}"
        
        if team_id in city_hubs:
            continue

        club_lat = float(row['lat'])
        club_lon = float(row['lon'])
        
        nearest_aero = get_nearest_airport(club_lat, club_lon, valid_airports)
        
        if not nearest_aero:
            print(f"[WARNING] No valid airport found for {team_id}")
            continue

        # Get real driving distance from stadium to airport
        drive_km, drive_h = get_osrm_distance(club_lat, club_lon, nearest_aero['lat'], nearest_aero['lon'])

        city_hubs[team_id] = {
            "clube": clube,
            "estado": estado,
            "cidade": row.get('cidade', 'Unknown'),
            "lat": club_lat,
            "lon": club_lon,
            "icao": nearest_aero['icao'],
            "hub_aero_nome": nearest_aero['name'],
            "hub_aero_cidade": nearest_aero['city'],
            "hub_aero_lat": nearest_aero['lat'],
            "hub_aero_lon": nearest_aero['lon'],
            "dist_ate_aero_km": drive_km,
            "tempo_ate_aero_h": drive_h
        }
        
        print(f"[{i+1}/{total_teams}] {team_id} -> {nearest_aero['icao']} ({drive_km}km)")
        
        # Save checkpoint every 20 teams to prevent data loss on API interruption
        if (i + 1) % 20 == 0:
            with open(OUTPUT_HUBS, 'w', encoding='utf-8') as f:
                json.dump(city_hubs, f, indent=2, ensure_ascii=False)

    # Final save
    with open(OUTPUT_HUBS, 'w', encoding='utf-8') as f:
        json.dump(city_hubs, f, indent=2, ensure_ascii=False)
        
    print("="*70)
    print(f"[SUCCESS] All hubs mapped! Saved to {OUTPUT_HUBS}")
    print("="*70)

if __name__ == "__main__":
    main()