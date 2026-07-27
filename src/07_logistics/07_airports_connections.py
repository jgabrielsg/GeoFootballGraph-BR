import os
import json
import glob
import pandas as pd
import networkx as nx

# --- CONFIGURATION ---
AIRPORTS_JSON = 'data/01_raw/airports/airports.json'
VRA_DIR = 'data/01_raw/airports'
OUTPUT_CSV = 'outputs/reports/brazil_flight_routes_2025.csv'
OUTPUT_GRAPH = 'outputs/graphs/brazil_air_network_2025.graphml'

# Minimum flights per year to be considered a regular commercial route
# 52 flights = 1 flight per week.
MIN_FLIGHTS_THRESHOLD = 52 

def main():
    print("="*60)
    print("BUILDING PRUNED DOMESTIC AIR NETWORK (ANAC 2025)")
    print("="*60)

    os.makedirs(os.path.dirname(OUTPUT_CSV), exist_ok=True)
    os.makedirs(os.path.dirname(OUTPUT_GRAPH), exist_ok=True)

    # 1. LOAD AND FILTER BRAZILIAN AIRPORTS
    try:
        with open(AIRPORTS_JSON, 'r', encoding='utf-8') as f:
            all_airports = json.load(f)
    except FileNotFoundError:
        print(f"[ERROR] Airports JSON not found at {AIRPORTS_JSON}.")
        return

    br_airports = {
        icao: data for icao, data in all_airports.items() 
        if data.get('country') == 'BR'
    }
    valid_icaos = set(br_airports.keys())

    # 2. PROCESS ANAC VRA CSV FILES
    vra_files = glob.glob(os.path.join(VRA_DIR, 'VRA_2025*.csv'))
    if not vra_files:
        print(f"[ERROR] No VRA CSV files found in {VRA_DIR}.")
        return
    
    route_counts_list = []

    for file in vra_files:
        try:
            df = pd.read_csv(file, sep=';', encoding='utf-8-sig', skiprows=1, low_memory=False)
        except Exception as e:
            continue
            
        df = df[df['Situação Voo'] == 'REALIZADO']
        
        df_br = df[
            df['ICAO Aeródromo Origem'].isin(valid_icaos) & 
            df['ICAO Aeródromo Destino'].isin(valid_icaos)
        ]
        
        counts = df_br.groupby(['ICAO Aeródromo Origem', 'ICAO Aeródromo Destino']).size().reset_index(name='flights')
        route_counts_list.append(counts)

    # 3. AGGREGATE ALL MONTHS
    if not route_counts_list:
        print("[ERROR] No valid domestic routes found.")
        return

    all_routes_df = pd.concat(route_counts_list, ignore_index=True)
    final_routes = all_routes_df.groupby(['ICAO Aeródromo Origem', 'ICAO Aeródromo Destino'])['flights'].sum().reset_index()
    final_routes = final_routes.sort_values(by='flights', ascending=False).reset_index(drop=True)

    total_initial_routes = len(final_routes)

    # 4. PRUNE RARE ROUTES (THE LOGISTIC FILTER)
    final_routes = final_routes[final_routes['flights'] >= MIN_FLIGHTS_THRESHOLD].reset_index(drop=True)
    
    pruned_routes_count = total_initial_routes - len(final_routes)
    print(f"[INFO] Pruned {pruned_routes_count} irregular routes (under {MIN_FLIGHTS_THRESHOLD} flights/year).")

    # 5. EXPORT ROUTES TO CSV
    final_routes.to_csv(OUTPUT_CSV, index=False, sep=';')

    # 6. BUILD DIRECTED GRAPH
    G = nx.DiGraph()

    for _, row in final_routes.iterrows():
        orig = row['ICAO Aeródromo Origem']
        dest = row['ICAO Aeródromo Destino']
        weight = row['flights']

        if not G.has_node(orig):
            G.add_node(orig, 
                       name=br_airports[orig].get('name', ''),
                       city=br_airports[orig].get('city', ''),
                       state=br_airports[orig].get('state', ''),
                       lat=float(br_airports[orig].get('lat', 0)),
                       lon=float(br_airports[orig].get('lon', 0)))
                       
        if not G.has_node(dest):
            G.add_node(dest, 
                       name=br_airports[dest].get('name', ''),
                       city=br_airports[dest].get('city', ''),
                       state=br_airports[dest].get('state', ''),
                       lat=float(br_airports[dest].get('lat', 0)),
                       lon=float(br_airports[dest].get('lon', 0)))

        G.add_edge(orig, dest, flights=weight)

    # 7. EXPORT GRAPH
    nx.write_graphml(G, OUTPUT_GRAPH)
    print(f"[SUCCESS] Pruned graph exported to {OUTPUT_GRAPH}")
    print(f"[STATS] Airports (Nodes): {G.number_of_nodes()}")
    print(f"[STATS] Commercial Routes (Edges): {G.number_of_edges()}")
    print("="*60)

if __name__ == "__main__":
    main()