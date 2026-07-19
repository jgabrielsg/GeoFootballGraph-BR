import os
import json
import pandas as pd
import networkx as nx
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import io

# --- CONFIGURATION ---
GRAPH_FILE = r'data\03_final\graphs\teams_games.graphml'
GEO_FILE = r'data\03_final\all_unique_teams_geolocalization.csv'
SERIE_C_FILE = r'data\04_results\serie_c_final_proposal.csv'
SERIE_D_FILE = r'data\04_results\serie_d_final_proposal.csv'

OUTPUT_DIR = r'outputs\svelte_data'
TEAMS_DB_OUT = os.path.join(OUTPUT_DIR, 'teams_db.json')
LEAGUES_OUT = os.path.join(OUTPUT_DIR, 'leagues_init.json')
AIRPORTS_OUT = os.path.join(OUTPUT_DIR, 'airports_db.json')

AIRPORTS_CSV_URL = "https://davidmegginson.github.io/ourairports-data/airports.csv"

# --- CONSTANTS ---
UF_MAP = {
    'acre': 'AC', 'alagoas': 'AL', 'amapa': 'AP', 'amazonas': 'AM', 'bahia': 'BA',
    'ceara': 'CE', 'distrito_federal': 'DF', 'espirito_santo': 'ES', 'goias': 'GO',
    'maranhao': 'MA', 'mato_grosso': 'MT', 'mato_grosso_do_sul': 'MS', 'minas_gerais': 'MG',
    'para': 'PA', 'paraiba': 'PB', 'parana': 'PR', 'pernambuco': 'PE', 'piaui': 'PI',
    'rio_de_janeiro': 'RJ', 'rio_grande_do_norte': 'RN', 'rio_grande_do_sul': 'RS',
    'rondonia': 'RO', 'roraima': 'RR', 'santa_catarina': 'SC', 'sao_paulo': 'SP',
    'sergipe': 'SE', 'tocantins': 'TO'
}

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

def get_robust_session():
    """Configures a requests Session with retries and full browser headers."""
    session = requests.Session()
    retry_strategy = Retry(
        total=5,
        backoff_factor=1.5,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"]
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    
    # Simulating a full Chrome browser signature to bypass basic bot protection
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive"
    })
    return session

def load_airports_db():
    print("[PROCESS] Downloading and formatting Airports DB...")
    session = get_robust_session()
    
    # Increased timeout to 30 seconds to handle slower handshake responses
    response = session.get(AIRPORTS_CSV_URL, timeout=30)
    response.raise_for_status()
    
    df = pd.read_csv(io.StringIO(response.content.decode('utf-8')))
    
    br_airports = df[
        (df['iso_country'] == 'BR') & 
        (df['type'].isin(['large_airport', 'medium_airport'])) &
        (df['scheduled_service'] == 'yes')
    ]
    
    airports_dict = {}
    for _, row in br_airports.iterrows():
        iata = str(row['iata_code']).strip()
        if iata and iata != 'nan':
            airports_dict[iata] = {
                "nome": row['name'],
                "lat": float(row['latitude_deg']),
                "lon": float(row['longitude_deg'])
            }
    return airports_dict

def main():
    print("="*60)
    print("SVELTEKIT JSON EXPORTER: PREPARING STATIC DATABASE")
    print("="*60)
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # 1. BUILD TEAMS DB
    print("[PROCESS] Building Teams Database...")
    G = nx.read_graphml(GRAPH_FILE)
    pr_scores = nx.pagerank(G, weight='weight')
    
    df_geo = pd.read_csv(GEO_FILE, sep=';', encoding='utf-8-sig')
    geo_lookup = {}
    for _, row in df_geo.iterrows():
        key = f"{str(row['clube']).upper().strip()}/{str(row['estado']).lower().strip()}"
        geo_lookup[key] = {
            "estadio": row['estadio'] if not pd.isna(row['estadio']) else "Desconhecido",
            "cidade": row['cidade'] if not pd.isna(row['cidade']) else "Desconhecida"
        }

    teams_db = {}
    for node_id, attrs in G.nodes(data=True):
        try:
            clube, estado = str(node_id).split('/')
            normalized_id = f"{clube.upper()}/{estado.lower()}"
        except:
            normalized_id = str(node_id).upper()
            clube, estado = normalized_id, ""

        uf = UF_MAP.get(estado.lower(), estado.upper())
        geo_info = geo_lookup.get(normalized_id, {"estadio": "Desconhecido", "cidade": "Desconhecida"})

        teams_db[normalized_id] = {
            "nome": clube.title(),
            "estado": estado.title().replace('_', ' '),
            "uf": uf,
            "cidade": geo_info['cidade'],
            "estadio": geo_info['estadio'],
            "lat": float(attrs.get('lat', 0)),
            "lon": float(attrs.get('lon', 0)),
            "pagerank": float(pr_scores.get(node_id, 0))
        }

    # 2. BUILD LEAGUES INIT
    print("[PROCESS] Compiling Initial Leagues Structure...")
    leagues_init = {
        "serie_A": [f"{c.upper()}/{e.lower()}" for c, e in SERIE_A_ELITE],
        "serie_B": [f"{c.upper()}/{e.lower()}" for c, e in SERIE_B_ELITE],
        "serie_C": {},
        "serie_D": {},
        "amador": []
    }
    
    allocated_ids = set(leagues_init["serie_A"] + leagues_init["serie_B"])

    # Serie C
    if os.path.exists(SERIE_C_FILE):
        df_c = pd.read_csv(SERIE_C_FILE, sep=';', encoding='utf-8-sig')
        for c_id in sorted(df_c['cluster_k4'].unique()):
            macro_key = f"macro_{c_id}"
            league_teams = df_c[df_c['cluster_k4'] == c_id]['clube_id'].tolist()
            leagues_init["serie_C"][macro_key] = league_teams
            allocated_ids.update(league_teams)

    # Serie D
    if os.path.exists(SERIE_D_FILE):
        df_d = pd.read_csv(SERIE_D_FILE, sep=';', encoding='utf-8-sig')
        micro_counter = 0
        for macro_id in sorted(df_d['cluster_k4'].unique()):
            macro_df = df_d[df_d['cluster_k4'] == macro_id]
            sub_col = 'serie_d_k4' if macro_id == 0 else 'serie_d_k3'
            if sub_col not in macro_df.columns: sub_col = 'cluster_k3' # Fallback
            
            for sub_id in sorted(macro_df[sub_col].dropna().unique()):
                micro_key = f"micro_{micro_counter}"
                league_teams = macro_df[macro_df[sub_col] == sub_id]['clube_id'].tolist()
                leagues_init["serie_D"][micro_key] = league_teams
                allocated_ids.update(league_teams)
                micro_counter += 1

    # Amador
    for team_id in teams_db.keys():
        if team_id not in allocated_ids:
            leagues_init["amador"].append(team_id)

    leagues_init["amador"] = sorted(
        leagues_init["amador"], 
        key=lambda x: teams_db[x]['pagerank'], 
        reverse=True
    )

    # 3. EXPORT TO JSON
    with open(TEAMS_DB_OUT, 'w', encoding='utf-8') as f:
        json.dump(teams_db, f, indent=2, ensure_ascii=False)

    with open(LEAGUES_OUT, 'w', encoding='utf-8') as f:
        json.dump(leagues_init, f, indent=2, ensure_ascii=False)

    airports_db = load_airports_db()
    with open(AIRPORTS_OUT, 'w', encoding='utf-8') as f:
        json.dump(airports_db, f, indent=2, ensure_ascii=False)

    print(f"\n[SUCCESS] Files exported to {OUTPUT_DIR}/")
    print(f" -> {len(teams_db)} Teams mapped.")
    print(f" -> {sum(len(v) for v in leagues_init['serie_C'].values())} Serie C clubs allocated.")
    print(f" -> {sum(len(v) for v in leagues_init['serie_D'].values())} Serie D clubs allocated.")
    print(f" -> {len(leagues_init['amador'])} Amateur clubs ready for promotion.")
    print(f" -> {len(airports_db)} Airports mapped.")
    print("="*60)

if __name__ == "__main__":
    main()