import pandas as pd
from rapidfuzz import process, fuzz
import unicodedata
import re
import os

# --- CONFIGURATION ---
GAMES_FILE = 'all_games_final_v2_corrigido.csv'
GEODATA_FILE = 'final_brazil_football_geodata_v2.csv'
OUTPUT_FILE = 'final_master_football_atlas.csv'
MISSING_FILE = 'missing_teams.csv'
SIMILARITY_THRESHOLD = 70 

def slugify(text):
    """
    Normalizes and converts strings into a URL-friendly slug format.
    
    Args:
        text (str): The raw string to be transformed.
    Returns:
        str: An ASCII-encoded string with underscores replacing special characters.
    """
    if pd.isna(text): return ""
    text = str(text).lower().strip()
    text = unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode('utf-8')
    text = re.sub(r'[^a-z0-9_]+', '_', text)
    return re.sub(r'_+', '_', text).strip('_')

def main():
    """
    Main execution pipeline to integrate football game results with geographic data.
    
    The process involves:
    1. Loading and cleaning game and location datasets.
    2. Performing fuzzy matching to link teams with their coordinates.
    3. Exporting teams that were not found for manual review.
    4. Merging data back to the main game list using independent state validation.
    """
    print("="*60)
    print("FINAL INTEGRATION: BRAZIL FOOTBALL ATLAS")
    print("="*60)

    # 1. DATA LOADING
    df_games = pd.read_csv(GAMES_FILE, sep=';', encoding='utf-8-sig')
    df_geo = pd.read_csv(GEODATA_FILE, sep=';', encoding='utf-8-sig')

    # 2. GEODATA PREPARATION
    df_geo['estado_slug'] = df_geo['estado'].apply(slugify)
    df_geo['nome_clean'] = df_geo['nome_simplificado'].str.upper().str.strip()

    # 3. UNIQUE TEAMS EXTRACTION
    # We create a lookup table of unique teams per state to optimize fuzzy matching
    h_teams = df_games[['mandante', 'mandante_estado']].rename(columns={'mandante': 'nome', 'mandante_estado': 'estado'})
    v_teams = df_games[['visitante', 'visitante_estado']].rename(columns={'visitante': 'nome', 'visitante_estado': 'estado'})
    
    unique_teams = pd.concat([h_teams, v_teams]).drop_duplicates()
    unique_teams['estado_slug'] = unique_teams['estado'].apply(slugify)
    unique_teams['nome_clean'] = unique_teams['nome'].str.upper().str.strip()

    # 4. FUZZY MATCHING (BLOCKING BY STATE)
    print(f"[PROCESS] Matching {len(unique_teams)} unique teams...")
    mapping_results = []

    for _, row in unique_teams.iterrows():
        team_name = row['nome_clean']
        state_slug = row['estado_slug']
        
        # Filter candidates within the same state to avoid homonyms (e.g., Operário-MS vs Operário-PR)
        candidates = df_geo[df_geo['estado_slug'] == state_slug]
        
        best_match = None
        if not candidates.empty:
            match = process.extractOne(team_name, candidates['nome_clean'].tolist(), scorer=fuzz.WRatio)
            
            if match and match[1] >= SIMILARITY_THRESHOLD:
                match_name = match[0]
                best_match = candidates[candidates['nome_clean'] == match_name].iloc[0]

        if best_match is not None:
            mapping_results.append({
                'nome_original_jogo': row['nome'],
                'estado_slug': state_slug,
                'match_found': True,
                'lat': best_match['latitude'],
                'lon': best_match['longitude'],
                'cidade': best_match['cidade'],
                'ibge': best_match['codigo_ibge']
            })
        else:
            mapping_results.append({
                'nome_original_jogo': row['nome'],
                'estado_slug': state_slug,
                'match_found': False,
                'lat': None, 'lon': None, 'cidade': None, 'ibge': None
            })

    df_mapping = pd.DataFrame(mapping_results)

    # 5. EXPORT UNMATCHED TEAMS
    df_missing = df_mapping[df_mapping['match_found'] == False][['nome_original_jogo', 'estado_slug']]
    df_missing.to_csv(MISSING_FILE, index=False, sep=';', encoding='utf-8-sig')
    print(f"[REPORT] Missing teams saved to: {MISSING_FILE}")

    # 6. CONSOLIDATED MERGE
    print("[MERGE] Merging coordinates into the master game list...")
    
    # We define separate state slugs for Home and Away to handle cross-state matches correctly
    df_games['h_estado_slug'] = df_games['mandante_estado'].apply(slugify)
    df_games['v_estado_slug'] = df_games['visitante_estado'].apply(slugify)

    # Merge Home Team Data
    df_final = pd.merge(
        df_games,
        df_mapping.drop(columns=['match_found']),
        left_on=['mandante', 'h_estado_slug'],
        right_on=['nome_original_jogo', 'estado_slug'],
        how='left'
    ).rename(columns={'lat': 'lat_h', 'lon': 'lon_h', 'cidade': 'cidade_h', 'ibge': 'ibge_h'}).drop(columns=['nome_original_jogo'])

    # Merge Away Team Data
    df_final = pd.merge(
        df_final,
        df_mapping.drop(columns=['match_found']),
        left_on=['visitante', 'v_estado_slug'],
        right_on=['nome_original_jogo', 'estado_slug'],
        how='left'
    ).rename(columns={'lat': 'lat_a', 'lon': 'lon_a', 'cidade': 'cidade_a', 'ibge': 'ibge_a'}).drop(columns=['nome_original_jogo', 'estado_slug'])

    # Final cleanup of auxiliary columns
    df_final = df_final.drop(columns=['h_estado_slug', 'v_estado_slug'])

    # 7. EXPORT FINAL MASTER DATASET
    df_final.to_csv(OUTPUT_FILE, index=False, sep=';', encoding='utf-8-sig')
    
    coverage = (df_final['lat_h'].notna().sum() / len(df_final)) * 100
    print("\n" + "="*60)
    print(f"SUCCESS | Final Data Coverage: {coverage:.2f}%")
    print(f"Master File Exported: {OUTPUT_FILE}")
    print("="*60)

if __name__ == "__main__":
    main()