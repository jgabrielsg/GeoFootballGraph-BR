import os
import json
import pandas as pd
from geopy.distance import geodesic

TEAMS_DB_FILE = r'outputs\svelte_data\teams_db.json'
SERIE_C_FILE = r'data\04_results\serie_c_final_proposal.csv'
SERIE_D_FILE = r'data\04_results\serie_d_final_proposal.csv'
OUTPUT_FILE = r'outputs\svelte_data\leagues_init.json'

SERIE_A_ELITE = [
    ("ATLÉTICO MINEIRO", "minas_gerais"), ("ATHLETICO PARANAENSE", "parana"),
    ("BAHIA", "bahia"), ("BOTAFOGO", "rio_de_janeiro"), ("CHAPECOENSE", "santa_catarina"),
    ("CORINTHIANS", "sao_paulo"), ("CORITIBA", "parana"), ("CRUZEIRO", "minas_gerais"),
    ("FLAMENGO", "rio_de_janeiro"), ("FLUMINENSE", "rio_de_janeiro"),
    ("GRÊMIO", "rio_grande_do_sul"), ("INTERNACIONAL", "rio_grande_do_sul"),
    ("MIRASSOL", "sao_paulo"), ("PALMEIRAS", "sao_paulo"),
    ("RED BULL BRAGANTINO", "sao_paulo"), ("REMO", "para"), ("SANTOS", "sao_paulo"),
    ("SÃO PAULO", "sao_paulo"), ("VASCO DA GAMA", "rio_de_janeiro"), ("VITÓRIA", "bahia")
]

SERIE_B_ELITE = [
    ("AMÉRICA MINEIRO", "minas_gerais"), ("ATHLETIC", "minas_gerais"),
    ("ATLÉTICO GOIANIENSE", "goias"), ("AVAÍ", "santa_catarina"),
    ("BOTAFOGO", "sao_paulo"), ("CEARÁ", "ceara"), ("CRB", "alagoas"),
    ("CRICIÚMA", "santa_catarina"), ("CUIABÁ", "mato_grosso"),
    ("FORTALEZA", "ceara"), ("GOIÁS", "goias"), ("GRÊMIO NOVORIZONTINO", "sao_paulo"),
    ("JUVENTUDE", "rio_grande_do_sul"), ("LONDRINA", "parana"),
    ("NÁUTICO", "pernambuco"), ("OPERÁRIO", "parana"), ("PONTE PRETA", "sao_paulo"),
    ("SÃO BERNARDO", "sao_paulo"), ("SPORT", "pernambuco"), ("VILA NOVA", "goias")
]

def normalize_id(cid):
    """Garante que a chave será CLUBE/estado_slug idêntica ao teams_db"""
    parts = str(cid).split('/')
    if len(parts) == 2:
        return f"{parts[0].upper()}/{parts[1].lower()}"
    return str(cid).upper()

def main():
    print("="*70)
    print("GERANDO LEAGUES_INIT: CLUSTERS EXATOS E AMADORES GEORREFERENCIADOS")
    print("="*70)

    # 1. Carregar Banco de Dados Base
    if not os.path.exists(TEAMS_DB_FILE):
        print(f"[ERRO] {TEAMS_DB_FILE} não encontrado. Gere-o primeiro.")
        return
        
    with open(TEAMS_DB_FILE, 'r', encoding='utf-8') as f:
        teams_db = json.load(f)

    # Inicializar Estruturas
    leagues_init = {
        "serie_A": [normalize_id(f"{c}/{e}") for c, e in SERIE_A_ELITE],
        "serie_B": [normalize_id(f"{c}/{e}") for c, e in SERIE_B_ELITE],
        "serie_C": {},
        "serie_D": {},
        "amador": {},
        "centroids": {} # Guardará os centros de massa para Svelte usar depois
    }
    allocated_ids = set(leagues_init["serie_A"] + leagues_init["serie_B"])

    # 2. Processar SÉRIE C (4 Macro-Regiões)
    print("[1/4] Processando Série C...")
    df_c = pd.read_csv(SERIE_C_FILE, sep=';', encoding='utf-8-sig')
    
    for macro_id in sorted(df_c['cluster_k4'].unique()):
        macro_key = f"macro_{macro_id}"
        teams = [normalize_id(tid) for tid in df_c[df_c['cluster_k4'] == macro_id]['clube_id'].tolist()]
        leagues_init["serie_C"][macro_key] = teams
        allocated_ids.update(teams)
        
        # Calcular Centróide da Macro
        lats = [teams_db[t]['lat'] for t in teams if t in teams_db]
        lons = [teams_db[t]['lon'] for t in teams if t in teams_db]
        if lats and lons:
            leagues_init["centroids"][macro_key] = {"lat": sum(lats)/len(lats), "lon": sum(lons)/len(lons)}

    # 3. Processar SÉRIE D (12 Micro-Regiões exatas baseadas em k4 -> k3)
    print("[2/4] Processando Série D...")
    df_d = pd.read_csv(SERIE_D_FILE, sep=';', encoding='utf-8-sig')
    micro_counter = 0
    
    for macro_id in sorted(df_d['cluster_k4'].unique()):
        macro_df = df_d[df_d['cluster_k4'] == macro_id]
        
        # Pega as 3 sub-divisões exatas usando a coluna serie_d_k3
        sub_clusters = sorted(macro_df['serie_d_k3'].dropna().unique())
        
        for sub_id in sub_clusters:
            micro_key = f"micro_{micro_counter}"
            
            # Filtra os times dessa micro-região específica
            teams = [normalize_id(tid) for tid in macro_df[macro_df['serie_d_k3'] == sub_id]['clube_id'].tolist()]
            
            leagues_init["serie_D"][micro_key] = teams
            allocated_ids.update(teams)
            
            # Calcular Centróide da Micro
            lats = [teams_db[t]['lat'] for t in teams if t in teams_db]
            lons = [teams_db[t]['lon'] for t in teams if t in teams_db]
            if lats and lons:
                leagues_init["centroids"][micro_key] = {"lat": sum(lats)/len(lats), "lon": sum(lons)/len(lons)}
                
            micro_counter += 1

    # 4. Processar AMADORES Georreferenciados
    print(f"[3/4] Alocando times Amadores às {micro_counter} Micro-regiões mais próximas...")
    
    # Inicializa as listas de amadores para cada micro-região
    for i in range(micro_counter):
        leagues_init["amador"][f"micro_{i}"] = []

    for team_id, data in teams_db.items():
        if team_id not in allocated_ids:
            t_lat = data['lat']
            t_lon = data['lon']
            
            # Encontrar a Micro-Região mais próxima (usando os centróides da Série D)
            closest_micro = None
            min_dist = float('inf')
            
            for i in range(micro_counter):
                micro_key = f"micro_{i}"
                if micro_key in leagues_init["centroids"]:
                    cent = leagues_init["centroids"][micro_key]
                    dist = geodesic((t_lat, t_lon), (cent['lat'], cent['lon'])).kilometers
                    
                    if dist < min_dist:
                        min_dist = dist
                        closest_micro = micro_key
            
            if closest_micro:
                leagues_init["amador"][closest_micro].append(team_id)

    # Ordenar os amadores de cada micro-região pelo PageRank (para que os mais fortes subam primeiro)
    for micro_key in leagues_init["amador"]:
        leagues_init["amador"][micro_key] = sorted(
            leagues_init["amador"][micro_key], 
            key=lambda x: teams_db[x]['pagerank'], 
            reverse=True
        )

    # 5. Salvar JSON
    print("[4/4] Salvando arquivo final...")
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(leagues_init, f, indent=2, ensure_ascii=False)

    # Estatísticas Finais
    print("\n" + "="*70)
    print("[SUCESSO] leagues_init.json gerado perfeitamente!")
    print(f" -> Série C: {len(leagues_init['serie_C'])} Macros mapeadas.")
    print(f" -> Série D: {len(leagues_init['serie_D'])} Micros mapeadas.")
    print(" -> Contagem de Times na Série D por Micro:")
    for m_key, m_teams in leagues_init['serie_D'].items():
        print(f"    - {m_key}: {len(m_teams)} times | Amadores na fila: {len(leagues_init['amador'][m_key])}")
    print("="*70)

if __name__ == "__main__":
    main()