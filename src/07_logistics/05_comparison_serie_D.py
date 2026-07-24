import os
import json
import pandas as pd
from geopy.distance import geodesic

# --- CONFIGURAÇÕES ---
CITY_HUBS_FILE = r'outputs\svelte_data\city_hubs.json'
LEAGUES_INIT_FILE = r'outputs\svelte_data\leagues_init.json'
MAPPING_FILE = r'outputs\svelte_data\mapping_serie_d_96.json'
CBF_MATCHES_FILE = r'data\01_raw\jogos_serie_d_2026.csv'
OUTPUT_FILE = r'outputs\svelte_data\comparison_cbf_serie_D.json'

# Mapeamentos Forçados (Tratamento de acentos e divergências no CSV da CBF)
EXACT_MAPPINGS = {
    "ATLÉTICO DE ALAGOINHAS": "ATLÉTICO/bahia",
    "SAMPAIO CORREA": "SAMPAIO CORRÊA/rio_de_janeiro",
    "SAMPAIO CORRÊA": "SAMPAIO CORRÊA/maranhao",
    "AMERICA": "AMERICA/rio_de_janeiro",
    "PORTUGUESA": "PORTUGUESA/rio_de_janeiro",
    "PORTUGUESA-SP": "PORTUGUESA/sao_paulo",
    "OPERÁRIO": "OPERÁRIO/mato_grosso_do_sul",
    "CEOV OPERÁRIO": "CEOV OPERÁRIO/mato_grosso",
    "ARAGUAINA FUTEBOL E REGATAS": "ARAGUAÍNA/tocantins",
    "ABECAT OUVIDORENSE": "ABECAT OUVIDOURENSE/goias",
    "SANTA CATARINA CLUBE": "SANTA CATARINA/santa_catarina"
}

def load_mappings():
    """Carrega as relações exatas de Nome -> ID para evitar colisões estaduais."""
    mapping_dict = {}
    
    # 1. Carrega o mapeamento gerado previamente (que conectou o nome ao estado correto)
    if os.path.exists(MAPPING_FILE):
        with open(MAPPING_FILE, 'r', encoding='utf-8') as f:
            mapping_data = json.load(f)
            for item in mapping_data.get('times', []):
                cbf_name = str(item['cbf_name']).strip().upper()
                mapping_dict[cbf_name] = item['json_id']
                
    # 2. Sobrescreve ou complementa com as regras manuais tratadas acima
    for k, v in EXACT_MAPPINGS.items():
        mapping_dict[k] = v
        
    return mapping_dict

def get_clube_id(raw_name, mapping_dict):
    """Busca o ID real via chave O(1) no dicionário consolidado."""
    raw_name = str(raw_name).strip().upper()
    return mapping_dict.get(raw_name, None)

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
    print("GERANDO COMPARATIVO LOGÍSTICO: SÉRIE D (CBF vs OTIMIZADO)")
    print("="*70)

    with open(CITY_HUBS_FILE, 'r', encoding='utf-8') as f:
        city_hubs = json.load(f)
        
    with open(LEAGUES_INIT_FILE, 'r', encoding='utf-8') as f:
        leagues_init = json.load(f)
        
    df_cbf = pd.read_csv(CBF_MATCHES_FILE)
    
    # Dicionário definitivo de Mapeamento
    mapping_dict = load_mappings()

    # Mapear as ligas propostas usando o leagues_init.json
    clusters_proposed = {}
    teams_per_cluster = {}
    
    for division, clusters in leagues_init.items():
        if isinstance(clusters, dict):
            for cluster_name, teams in clusters.items():
                league_label = f"{cluster_name.replace('_', ' ').title()} ({division.replace('_', ' ').title()})"
                for t in teams:
                    clusters_proposed[t] = league_label
                    if league_label not in teams_per_cluster: 
                        teams_per_cluster[league_label] = []
                    teams_per_cluster[league_label].append(t)
        else:
            league_label = division.replace('_', ' ').title()
            for t in clusters:
                clusters_proposed[t] = league_label
                if league_label not in teams_per_cluster: 
                    teams_per_cluster[league_label] = []
                teams_per_cluster[league_label].append(t)

    cbf_teams_ids = set()
    comparison = {}
    missing_teams = set()
    
    # 1. Processar Partidas Base (CBF)
    for _, match in df_cbf.iterrows():
        id_mandante = get_clube_id(match['mandante'], mapping_dict)
        if not id_mandante:
            missing_teams.add(match['mandante'])

        id_visitante = get_clube_id(match['visitante'], mapping_dict)
        if not id_visitante:
            missing_teams.add(match['visitante'])
            
        if not id_mandante or not id_visitante:
            continue
            
        cbf_teams_ids.add(id_mandante)
        cbf_teams_ids.add(id_visitante)

        if id_visitante not in comparison:
            clube, estado = id_visitante.split('/')
            current_league = clusters_proposed.get(id_visitante, "Amador")
            comparison[id_visitante] = {
                "nome": clube,
                "estado": estado,
                "liga_proposta": current_league,
                "baseline": {"partidas": [], "km_total": 0},
                "proposto": {"partidas": [], "km_total": 0}
            }

        route_info = calculate_route(id_visitante, id_mandante, city_hubs)
        if route_info:
            comparison[id_visitante]["baseline"]["partidas"].append({
                "adversario": id_mandante,
                "modal": route_info["modal"],
                "km": route_info["km"],
                "rota": route_info["rota"]
            })
            comparison[id_visitante]["baseline"]["km_total"] += route_info["km"]

    # 2. Processar Simulação Proposta
    for tid in cbf_teams_ids:
        current_league = clusters_proposed.get(tid, "Amador")
        
        if current_league != "Amador" and current_league in teams_per_cluster:
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

        # Finalizar métricas médias
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
        
    print(f"[SUCESSO] Mapeados {len(cbf_teams_ids)} times válidos.")
    if missing_teams:
        print(f"[ALERTA] Não foi possível encontrar IDs únicos para {len(missing_teams)} times:")
        for team in sorted(list(missing_teams)):
            print(f"  - {team}")
            
    print(f"[SUCESSO] Arquivo salvo em: {OUTPUT_FILE}")
    print("="*70)

if __name__ == "__main__":
    main()