import pandas as pd
from rapidfuzz import process, fuzz
import unicodedata
import re
import os

# --- CONFIGURATION ---
GAMES_FILE = 'data/02_processed/e3e3e33e3_v2.csv'
GEODATA_FILE = 'data/03_final/all_clubs_geodata.csv'
OUTSIDERS_FILE = 'data/01_raw/outsiders.csv'
OUTPUT_FILE = 'data/03_final/all_games_geodata222.csv'
MISSING_FILE = 'archive/data/missing_teams.csv'
SIMILARITY_THRESHOLD = 85

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
    # Key: (club_slug, league_slug) -> Value: origin_state_slug
    return {(slugify(r['clube']), slugify(r['campeonato_jogado'])): slugify(r['estado_origem']) 
            for _, r in df_out.iterrows()}

def main():
    print("="*60)
    print("FINAL INTEGRATION: BRAZIL FOOTBALL ATLAS (WITH OUTSIDERS FIX)")
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
        
        # --- REDIRECT LOGIC FOR OUTSIDERS ---
        # Se o time e o estado atual estão no mapa, mudamos o estado de busca
        search_state_slug = outsiders_map.get((slugify(team_name), original_state_slug), original_state_slug)
        
        candidates = df_geo[df_geo['estado_slug'] == search_state_slug]
        
        best_match = None
        if not candidates.empty:
            match = process.extractOne(team_name, candidates['nome_clean'].tolist(), scorer=fuzz.WRatio)
            if match and match[1] >= SIMILARITY_THRESHOLD:
                best_match = candidates[candidates['nome_clean'] == match[0]].iloc[0]

        if best_match is not None:
            mapping_results.append({
                'nome_original_jogo': row['nome'],
                'estado_slug_key': original_state_slug, # Chave original para o merge
                'match_found': True,
                'lat': best_match['latitude'], 'lon': best_match['longitude'],
                'cidade': best_match['cidade'], 'ibge': best_match['codigo_ibge']
            })
        else:
            mapping_results.append({
                'nome_original_jogo': row['nome'],
                'estado_slug_key': original_state_slug,
                'match_found': False,
                'lat': None, 'lon': None, 'cidade': None, 'ibge': None
            })

    df_mapping = pd.DataFrame(mapping_results)

    # 5. EXPORT MISSING
    df_missing = df_mapping[df_mapping['match_found'] == False][['nome_original_jogo', 'estado_slug_key']]
    df_missing.to_csv(MISSING_FILE, index=False, sep=';', encoding='utf-8-sig')

    # 6. CONSOLIDATED MERGE (CLEAN)
    print("[MERGE] Merging coordinates and cleaning redundant columns...")
    df_games['h_slug_tmp'] = df_games['mandante_estado'].apply(slugify)
    df_games['v_slug_tmp'] = df_games['visitante_estado'].apply(slugify)

    # Merge Mandante
    df_final = pd.merge(
        df_games, df_mapping.drop(columns=['match_found']),
        left_on=['mandante', 'h_slug_tmp'], right_on=['nome_original_jogo', 'estado_slug_key'],
        how='left'
    ).rename(columns={'lat': 'lat_h', 'lon': 'lon_h', 'cidade': 'cidade_h', 'ibge': 'ibge_h'}).drop(columns=['nome_original_jogo', 'estado_slug_key', 'h_slug_tmp'])

    # Merge Visitante
    df_final = pd.merge(
        df_final, df_mapping.drop(columns=['match_found']),
        left_on=['visitante', 'v_slug_tmp'], right_on=['nome_original_jogo', 'estado_slug_key'],
        how='left'
    ).rename(columns={'lat': 'lat_a', 'lon': 'lon_a', 'cidade': 'cidade_a', 'ibge': 'ibge_a'}).drop(columns=['nome_original_jogo', 'estado_slug_key', 'v_slug_tmp'])

    # 7. EXPORT
    df_final.to_csv(OUTPUT_FILE, index=False, sep=';', encoding='utf-8-sig')
    
    coverage = (df_final['lat_h'].notna().sum() / len(df_final)) * 100
    print("\n" + "="*60)
    print(f"SUCCESS | Final Data Coverage: {coverage:.2f}%")
    print(f"Master File Exported: {OUTPUT_FILE}")
    print("="*60)

if __name__ == "__main__":
    main()