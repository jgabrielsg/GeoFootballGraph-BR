import pandas as pd
from rapidfuzz import process, fuzz
import unicodedata
import re
import os

# --- CONFIGURATION ---
GAMES_FILE = 'data/03_final/all_games_weights.csv'   # MATCHES AND WEIGHTS INFO
GEODATA_FILE = 'data/03_final/all_clubs_geodata.csv' # GEODATA INFO
OUTSIDERS_FILE = 'data/01_raw/outsiders.csv'         # CLUBS THAT PLAY FOR ANOTHER STATE
SIMILARITY_THRESHOLD = 85

# --- OUTPUTS ---
OUTPUT_FILE = 'data/03_final/all_games_geodata_9090.csv'
MISSING_FILE = 'archive/data/missing_teams.csv'

def slugify(text):
    """Normalizes strings into a URL-friendly slug format."""
    if pd.isna(text): return ""
    text = str(text).lower().strip()
    text = unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode('utf-8')
    text = re.sub(r'[^a-z0-9_]+', '_', text)
    return re.sub(r'_+', '_', text).strip('_')

def load_outsiders_map(path):
    """Loads outsiders to redirect search to the correct state."""
    if not os.path.exists(path):
        return {}
    df_out = pd.read_csv(path, sep=';', encoding='utf-8-sig')
    return {(slugify(r['clube']), slugify(r['campeonato_jogado'])): slugify(r['estado_origem']) 
            for _, r in df_out.iterrows()}

def main():
    print("="*60)
    print("INTEGRATION: FOOTBALL ATLAS + PAGERANK FLOWS")
    print("="*60)

    # 1. DATA LOADING
    df_games = pd.read_csv(GAMES_FILE, sep=';', encoding='utf-8-sig')
    df_geo = pd.read_csv(GEODATA_FILE, sep=';', encoding='utf-8-sig')
    outsiders_map = load_outsiders_map(OUTSIDERS_FILE)

    # 2. GEODATA PREPARATION
    df_geo['estado_slug'] = df_geo['estado'].apply(slugify)
    df_geo['nome_clean'] = df_geo['nome_simplificado'].str.upper().str.strip()

    # 3. UNIQUE TEAMS EXTRACTION
    h_teams = df_games[['mandante', 'mandante_estado']].rename(columns={'mandante': 'nome', 'mandante_estado': 'estado'})
    v_teams = df_games[['visitante', 'visitante_estado']].rename(columns={'visitante': 'nome', 'visitante_estado': 'estado'})
    unique_teams = pd.concat([h_teams, v_teams]).drop_duplicates()
    unique_teams['nome_clean'] = unique_teams['nome'].str.upper().str.strip()

    # 4. FUZZY MATCHING (WITH REDIRECT LOGIC)
    print(f"[PROCESS] Matching {len(unique_teams)} unique teams...")
    mapping_results = []

    for _, row in unique_teams.iterrows():
        team_name = row['nome_clean']
        original_state_slug = slugify(row['estado'])
        search_state_slug = outsiders_map.get((slugify(team_name), original_state_slug), original_state_slug)
        
        candidates = df_geo[df_geo['estado_slug'] == search_state_slug]
        best_match = None
        if not candidates.empty:
            match = process.extractOne(team_name, candidates['nome_clean'].tolist(), scorer=fuzz.WRatio)
            if match and match[1] >= SIMILARITY_THRESHOLD:
                best_match = candidates[candidates['nome_clean'] == match[0]].iloc[0]

        mapping_results.append({
            'nome_original_jogo': row['nome'],
            'estado_slug_key': original_state_slug,
            'match_found': best_match is not None,
            'lat': best_match['latitude'] if best_match is not None else None,
            'lon': best_match['longitude'] if best_match is not None else None,
            'cidade': best_match['cidade'] if best_match is not None else None,
            'ibge': best_match['codigo_ibge'] if best_match is not None else None
        })

    df_mapping = pd.DataFrame(mapping_results)

    # 5. EXPORT MISSING
    df_missing = df_mapping[df_mapping['match_found'] == False][['nome_original_jogo', 'estado_slug_key']]
    df_missing.to_csv(MISSING_FILE, index=False, sep=';', encoding='utf-8-sig')

    # 6. CONSOLIDATED MERGE
    print("[MERGE] Integrating flows and coordinates...")
    df_games['h_slug_tmp'] = df_games['mandante_estado'].apply(slugify)
    df_games['v_slug_tmp'] = df_games['visitante_estado'].apply(slugify)

    # Merge Home
    df_final = pd.merge(
        df_games, df_mapping.drop(columns=['match_found']),
        left_on=['mandante', 'h_slug_tmp'], right_on=['nome_original_jogo', 'estado_slug_key'],
        how='left'
    ).rename(columns={'lat': 'lat_h', 'lon': 'lon_h', 'cidade': 'cidade_h', 'ibge': 'ibge_h'}).drop(columns=['nome_original_jogo', 'estado_slug_key', 'h_slug_tmp'])

    # Merge Away
    df_final = pd.merge(
        df_final, df_mapping.drop(columns=['match_found']),
        left_on=['visitante', 'v_slug_tmp'], right_on=['nome_original_jogo', 'estado_slug_key'],
        how='left'
    ).rename(columns={'lat': 'lat_a', 'lon': 'lon_a', 'cidade': 'cidade_a', 'ibge': 'ibge_a'}).drop(columns=['nome_original_jogo', 'estado_slug_key', 'v_slug_tmp'])

    # 7. FINAL COLUMN REORDERING
    # Mantemos as colunas de fluxo logo após os dados do jogo
    match_info = ['estado', 'divisao', 'ano', 'data', 'mandante', 'mandante_estado', 'visitante', 'visitante_estado', 'placar', 'resultado']
    flow_info = ['gols_mandante', 'gols_visitante', 'peso_base', 'fluxo_h', 'fluxo_a']
    geo_info = ['lat_h', 'lon_h', 'cidade_h', 'ibge_h', 'lat_a', 'lon_a', 'cidade_a', 'ibge_a']
    
    final_cols = match_info + flow_info + geo_info
    df_final = df_final[final_cols]

    # 8. EXPORT
    df_final.to_csv(OUTPUT_FILE, index=False, sep=';', encoding='utf-8-sig')
    
    coverage = (df_final['lat_h'].notna().sum() / len(df_final)) * 100
    print("\n" + "="*60)
    print(f"SUCCESS | Final Data Coverage: {coverage:.2f}%")
    print(f"Master File Exported with Weights: {OUTPUT_FILE}")
    print("="*60)

if __name__ == "__main__":
    main()