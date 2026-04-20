import pandas as pd
from rapidfuzz import process, fuzz
import numpy as np

# --- SETTINGS ---
SIMILARITY_THRESHOLD = 80  # Minimum score to accept a match (0-100)

def load_and_prepare():
    print("[1/4] Loading datasets...")
    # Load games data (the source of our 1171 nodes)
    df_games = pd.read_csv('all_games_final.csv', sep=';', encoding='utf-8-sig')
    
    # Extract unique teams and their associated states
    # We create a map of team -> state
    m_teams = df_games[['mandante', 'estado']].rename(columns={'mandante': 'team'})
    v_teams = df_games[['visitante', 'estado']].rename(columns={'visitante': 'team'})
    df_unique_teams = pd.concat([m_teams, v_teams]).drop_duplicates(subset=['team'])
    
    # Load geographical data (our target nodes)
    df_geo = pd.read_csv('final_brazil_football_geodata.csv', sep=';', encoding='utf-8-sig')
    
    # Standardize state names for better blocking
    df_unique_teams['estado'] = df_unique_teams['estado'].str.lower().str.strip()
    df_geo['estado'] = df_geo['estado'].str.lower().str.strip()
    
    return df_unique_teams, df_geo

def fuzzy_match_teams(df_teams, df_geo):
    print(f"[2/4] Starting matching for {len(df_teams)} unique teams...")
    results = []
    
    for idx, row in df_teams.iterrows():
        team_name = str(row['team']).upper()
        state_filter = row['estado']
        
        # Filtering geo data by state to avoid cross-state duplicates (Blocking)
        if state_filter == 'nacional':
            # For national teams, search the entire geo database
            candidates = df_geo
        else:
            candidates = df_geo[df_geo['estado'] == state_filter]
            # Fallback: if no candidates in that state, search all (resilience)
            if candidates.empty:
                candidates = df_geo

        if not candidates.empty:
            choices = candidates['nome_clube'].tolist()
            # WRatio is excellent for "Vasco" vs "Club de Regatas Vasco da Gama"
            best_match = process.extractOne(team_name, choices, scorer=fuzz.WRatio)
            
            if best_match and best_match[1] >= SIMILARITY_THRESHOLD:
                match_row = candidates[candidates['nome_clube'] == best_match[0]].iloc[0]
                results.append({
                    'original_name': row['team'],
                    'matched_name': match_row['nome_clube'],
                    'similarity': best_match[1],
                    'estado': match_row['estado'],
                    'cidade': match_row['cidade'],
                    'lat': match_row['latitude'],
                    'lon': match_row['longitude'],
                    'ibge': match_row['codigo_ibge']
                })
            else:
                results.append({
                    'original_name': row['team'],
                    'matched_name': None,
                    'similarity': 0,
                    'estado': row['estado'],
                    'cidade': None, 'lat': None, 'lon': None, 'ibge': None
                })
        
        if len(results) % 200 == 0:
            print(f"      Progress: {len(results)}/{len(df_teams)}...")

    return pd.DataFrame(results)

def main():
    df_teams, df_geo = load_and_prepare()
    
    df_mapped = fuzzy_match_teams(df_teams, df_geo)
    
    # [3/4] Exporting results
    df_mapped.to_csv('nodes_georreferenciados.csv', index=False, sep=';', encoding='utf-8-sig')
    
    # [4/4] Final Validation Prints
    success_count = df_mapped['matched_name'].notna().sum()
    print("\n" + "="*50)
    print("MATCHING SUMMARY")
    print("="*50)
    print(f"Total teams to map: {len(df_teams)}")
    print(f"Successfully mapped: {success_count} ({success_count/len(df_teams)*100:.1f}%)")
    print(f"Unmapped teams: {len(df_teams) - success_count}")
    
    # Show some failures for manual review
    if success_count < len(df_teams):
        print("\nTOP UNMAPPED TEAMS (Check these):")
        print(df_mapped[df_mapped['matched_name'].isna()]['original_name'].head(10).tolist())
    print("="*50)

if __name__ == "__main__":
    main()