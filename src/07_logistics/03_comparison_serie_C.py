import os
import json
import pandas as pd
from geopy.distance import geodesic

CITY_HUBS_FILE = r'outputs\svelte_data\city_hubs.json'
CBF_MATCHES_FILE = r'data\01_raw\jogos_serie_c_2026.csv'
SERIE_C_PROP_FILE = r'data\04_results\serie_c_final_proposal.csv'
SERIE_D_PROP_FILE = r'data\04_results\serie_d_final_proposal.csv'
OUTPUT_FILE = r'outputs\svelte_data\comparison_cbf_serie_C.json'

def normalize_id(clube, estado):
    return f"{str(clube).strip().upper()}/{str(estado).strip().lower()}"

def calculate_route(source_id, target_id, city_hubs):
    if source_id not in city_hubs or target_id not in city_hubs:
        return None
        
    orig = city_hubs[source_id]
    dest = city_hubs[target_id]
    
    dist_straight = geodesic((orig['lat'], orig['lon']), (dest['lat'], dest['lon'])).kilometers
    dist_road = dist_straight * 1.3
    
    if dist_road < 800:
        return {
            "modal": "onibus",
            "km": round(dist_road, 2),
            "rota": [[orig['lat'], orig['lon']], [dest['lat'], dest['lon']]]
        }
    else:
        dist_flight = geodesic(
            (orig['hub_aero_lat'], orig['hub_aero_lon']), 
            (dest['hub_aero_lat'], dest['hub_aero_lon'])
        ).kilometers * 1.15
        
        total_km = orig['dist_ate_aero_km'] + dist_flight + dest['dist_ate_aero_km']
        return {
            "modal": "aereo",
            "km": round(total_km, 2),
            "rota": [
                [orig['lat'], orig['lon']],
                [orig['hub_aero_lat'], orig['hub_aero_lon']],
                [dest['hub_aero_lat'], dest['hub_aero_lon']],
                [dest['lat'], dest['lon']]
            ]
        }

def main():
    print("="*70)
    print("BUILDING LOGISTICS COMPARISON: CBF vs PROPOSED MODEL")
    print("="*70)

    with open(CITY_HUBS_FILE, 'r', encoding='utf-8') as f:
        city_hubs = json.load(f)
        
    df_cbf = pd.read_csv(CBF_MATCHES_FILE)
    df_prop_c = pd.read_csv(SERIE_C_PROP_FILE, sep=';')
    df_prop_d = pd.read_csv(SERIE_D_PROP_FILE, sep=';')
    
    cbf_teams_ids = set()
    for _, row in df_cbf.iterrows():
        cbf_teams_ids.add(normalize_id(row['mandante'], row['estado_m']))
        cbf_teams_ids.add(normalize_id(row['visitante'], row['estado_v']))
        
    print(f"[INFO] Identified {len(cbf_teams_ids)} original CBF teams.")

    clusters_proposed = {}
    teams_per_cluster = {}
    
    for _, row in df_prop_c.iterrows():
        tid = normalize_id(row['clube'], row['uf_slug'])
        league = f"Macro {row['cluster_k4']} (Série C)"
        clusters_proposed[tid] = league
        if league not in teams_per_cluster: 
            teams_per_cluster[league] = []
        teams_per_cluster[league].append(tid)

    # Build exact micro-region mapping dictionary
    micro_mapping = {}
    micro_counter = 0
    for macro_id in sorted(df_prop_d['cluster_k4'].unique()):
        macro_df = df_prop_d[df_prop_d['cluster_k4'] == macro_id]
        sub_clusters = sorted(macro_df['serie_d_k3'].dropna().unique())
        for sub_id in sub_clusters:
            micro_mapping[(macro_id, sub_id)] = micro_counter
            micro_counter += 1

    for _, row in df_prop_d.iterrows():
        if pd.isna(row['clube_id']):
            continue
            
        clube_id_parts = str(row['clube_id']).split('/')
        if len(clube_id_parts) == 2:
            tid = normalize_id(clube_id_parts[0], clube_id_parts[1])
            micro_id = micro_mapping.get((row['cluster_k4'], row['serie_d_k3']))
            
            if micro_id is not None:
                league = f"Micro {micro_id} (Série D)"
                clusters_proposed[tid] = league
                if league not in teams_per_cluster: 
                    teams_per_cluster[league] = []
                teams_per_cluster[league].append(tid)

    comparison = {}
    
    for tid in cbf_teams_ids:
        if tid not in city_hubs:
            continue
            
        clube, estado = tid.split('/')
        current_league = clusters_proposed.get(tid, "Amador")
        
        comparison[tid] = {
            "nome": clube,
            "estado": estado,
            "liga_proposta": current_league,
            "baseline": {"partidas": [], "km_total": 0},
            "proposto": {"partidas": [], "km_total": 0}
        }
        
        cbf_matches = df_cbf[(df_cbf['visitante'].str.upper() == clube) & (df_cbf['estado_v'].str.lower() == estado)]
        
        for _, match in cbf_matches.iterrows():
            target_id = normalize_id(match['mandante'], match['estado_m'])
            route_info = calculate_route(tid, target_id, city_hubs)
            if route_info:
                comparison[tid]["baseline"]["partidas"].append({
                    "adversario": target_id,
                    "modal": route_info["modal"],
                    "km": route_info["km"],
                    "rota": route_info["rota"]
                })
                comparison[tid]["baseline"]["km_total"] += route_info["km"]
                
        if current_league in teams_per_cluster:
            cluster_opponents = [t for t in teams_per_cluster[current_league] if t != tid]
            
            for opp_id in cluster_opponents:
                route_info = calculate_route(tid, opp_id, city_hubs)
                if route_info:
                    comparison[tid]["proposto"]["partidas"].append({
                        "adversario": opp_id,
                        "modal": route_info["modal"],
                        "km": route_info["km"],
                        "rota": route_info["rota"]
                    })
                    comparison[tid]["proposto"]["km_total"] += route_info["km"]

        qty_b = len(comparison[tid]["baseline"]["partidas"])
        qty_p = len(comparison[tid]["proposto"]["partidas"])
        
        comparison[tid]["baseline"]["jogos_fora"] = qty_b
        comparison[tid]["baseline"]["km_medio"] = round(comparison[tid]["baseline"]["km_total"] / qty_b, 2) if qty_b > 0 else 0
        comparison[tid]["baseline"]["km_total"] = round(comparison[tid]["baseline"]["km_total"], 2)

        comparison[tid]["proposto"]["jogos_fora"] = qty_p
        comparison[tid]["proposto"]["km_medio"] = round(comparison[tid]["proposto"]["km_total"] / qty_p, 2) if qty_p > 0 else 0
        comparison[tid]["proposto"]["km_total"] = round(comparison[tid]["proposto"]["km_total"], 2)

    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(comparison, f, indent=2, ensure_ascii=False)
        
    print(f"[SUCCESS] Output saved to: {OUTPUT_FILE}")
    print("="*70)

if __name__ == "__main__":
    main()