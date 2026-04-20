import pandas as pd
import numpy as np
import os
import re

# --- CONFIGURATION ---
INPUT_FILES = [
    'jogos_estaduais_full.csv', 
    'jogos_estaduais_full2.csv',
    'jogos_estaduais_full3.csv', 
    'jogos_estaduais_full4.csv',
    'jogos_nacionais_full.csv'
]
OUTPUT_FILE = 'all_games_final.csv'

def clean_and_parse_score(placar_raw):
    """
    Cleans scores like '1-0(5-4 Pen.)' or '2 X 1' and extracts goals.
    Ignores anything after the main score (penalties).
    """
    if pd.isna(placar_raw):
        return None, None, None
    
    try:
        # Regex to find the first two sequences of digits separated by '-' or 'X'
        # It ignores anything that comes after (like parentheses for penalties)
        match = re.search(r'(\d+)\s*[-Xx]\s*(\d+)', str(placar_raw))
        if match:
            h_goals = int(match.group(1))
            a_goals = int(match.group(2))
            
            # Logic for result: Home Win (H), Away Win (A), Draw (D)
            if h_goals > a_goals:
                res = 'H'
            elif a_goals > h_goals:
                res = 'A'
            else:
                res = 'D'
            return h_goals, a_goals, res
    except:
        pass
    return None, None, None

def calculate_importance(row):
    """
    Assigns weight based on league level and scope (National vs State).
    """
    is_national = str(row['estado']).lower() == 'nacional'
    div = int(row['divisao'])
    
    if is_national:
        weights = {
            0: 10.0, # Copa do Brasil
            1: 10.0, # Série A
            2: 7.5,  # Série B
            3: 5.0,  # Série C
            4: 3.0   # Série D
        }
        return weights.get(div, 1.0)
    else:
        # State Leagues weights
        if div == 1:
            return 2.0
        elif div == 2:
            return 1.5
        else:
            return 1.0

def main():
    print("="*60)
    print("STARTING BRAZILIAN FOOTBALL DATA CONSOLIDATION")
    print("="*60)
    
    processed_dfs = []
    
    for file in INPUT_FILES:
        if not os.path.exists(file):
            print(f"[SKIP] File not found: {file}")
            continue
        
        print(f"[LOAD] Processing: {file}...")
        df = pd.read_csv(file, sep=';', encoding='utf-8-sig')
        
        # Pre-cleaning: Ensure 'ano' is integer to avoid sorting errors
        df['ano'] = pd.to_numeric(df['ano'], errors='coerce')
        df = df.dropna(subset=['ano'])
        df['ano'] = df['ano'].astype(int)
        
        # Apply score cleaning and goal extraction
        print(f"       -> Extracting goals and results for {len(df)} matches...")
        score_data = df['placar'].apply(clean_and_parse_score)
        
        # Unpack the results into new columns
        results_df = pd.DataFrame(score_data.tolist(), index=df.index, 
                                  columns=['gols_mandante', 'gols_visitante', 'resultado'])
        
        df = pd.concat([df, results_df], axis=1)
        
        # Drop matches where score couldn't be parsed
        original_count = len(df)
        df = df.dropna(subset=['resultado'])
        print(f"       -> Valid matches: {len(df)} (Dropped {original_count - len(df)})")
        
        processed_dfs.append(df)

    if not processed_dfs:
        print("[CRITICAL] No data processed. Execution halted.")
        return

    # Consolidate all dataframes
    all_games = pd.concat(processed_dfs, ignore_index=True)
    
    # Calculate Importance Weight
    print("[MATH] Calculating importance weights...")
    all_games['peso_importancia'] = all_games.apply(calculate_importance, axis=1)
    
    # Final cleanup of types
    all_games['gols_mandante'] = all_games['gols_mandante'].astype(int)
    all_games['gols_visitante'] = all_games['gols_visitante'].astype(int)
    
    # Save the master CSV
    all_games.to_csv(OUTPUT_FILE, index=False, sep=';', encoding='utf-8-sig')
    
    print("\n" + "="*60)
    print("VALIDATION AND FINAL STATISTICS")
    print("="*60)
    
    print(f"TOTAL MATCHES CONSOLIDATED: {len(all_games)}")
    
    # Unique Teams analysis
    all_teams = set(all_games['mandante'].unique()) | set(all_games['visitante'].unique())
    print(f"UNIQUE TEAMS IDENTIFIED (Nodes): {len(all_teams)}")
    
    # Results Distribution
    print("\nRESULT DISTRIBUTION (%)")
    print(all_games['resultado'].value_counts(normalize=True) * 100)
    
    # Importance breakdown
    print("\nAVERAGE IMPORTANCE BY DIVISION:")
    print(all_games.groupby(['estado', 'divisao'])['peso_importancia'].mean())
    
    # Year analysis
    print("\nMATCHES PER YEAR:")
    print(all_games['ano'].value_counts().sort_index())
    
    print("\n[DONE] Master file saved as 'all_games_final.csv'")
    print("="*60)

if __name__ == "__main__":
    main()