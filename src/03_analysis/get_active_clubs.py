import pandas as pd
import unicodedata
import re

# --- CONFIGURATION ---
INPUT_FILE = 'all_games_geodata.csv'
OUTPUT_FILE = 'active_clubs_geodata.csv'
START_YEAR = 2020

def slugify(text):
    """
    Standardizes strings by removing accents, special characters, and 
    converting to lowercase. Used to create unique keys for matching.
    """
    if pd.isna(text): return ""
    text = str(text).lower().strip()
    text = unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode('utf-8')
    text = re.sub(r'[^a-z0-9_]+', '_', text)
    return re.sub(r'_+', '_', text).strip('_')

def main():
    """
    Consolidates club statistics and geographic metadata while resolving 
    duplicate entities caused by spelling or accentuation differences.
    """
    print("="*60)
    print("UNIFYING ACTIVE CLUBS REGISTRY (ACCENT & STATE CORRECTION)")
    print("="*60)

    # 1. LOAD MASTER DATA
    df = pd.read_csv(INPUT_FILE, sep=';', encoding='utf-8-sig')
    df_recent = df[df['ano'] >= START_YEAR].copy()

    # 2. CALCULATE MATCH PERFORMANCE
    # Home team results
    df_recent['h_win'] = (df_recent['resultado'] == 'H').astype(int)
    df_recent['h_draw'] = (df_recent['resultado'] == 'D').astype(int)
    df_recent['h_loss'] = (df_recent['resultado'] == 'A').astype(int)

    # Away team results
    df_recent['a_win'] = (df_recent['resultado'] == 'A').astype(int)
    df_recent['a_draw'] = (df_recent['resultado'] == 'D').astype(int)
    df_recent['a_loss'] = (df_recent['resultado'] == 'H').astype(int)

    # 3. SPLIT AND STACK PERSPECTIVES
    # We unify both Home and Away columns into a single 'clube' column for grouping
    home_view = df_recent[[
        'mandante', 'mandante_estado', 'cidade_h', 'lat_h', 'lon_h', 'ibge_h', 
        'h_win', 'h_draw', 'h_loss'
    ]].rename(columns={
        'mandante': 'clube', 'mandante_estado': 'estado', 'cidade_h': 'cidade',
        'lat_h': 'lat', 'lon_h': 'lon', 'ibge_h': 'ibge',
        'h_win': 'wins', 'h_draw': 'draws', 'h_loss': 'losses'
    })

    away_view = df_recent[[
        'visitante', 'visitante_estado', 'cidade_a', 'lat_a', 'lon_a', 'ibge_a',
        'a_win', 'a_draw', 'a_loss'
    ]].rename(columns={
        'visitante': 'clube', 'visitante_estado': 'estado', 'cidade_a': 'cidade',
        'lat_a': 'lat', 'lon_a': 'lon', 'ibge_a': 'ibge',
        'a_win': 'wins', 'a_draw': 'draws', 'a_loss': 'losses'
    })

    df_all_active = pd.concat([home_view, away_view], ignore_index=True)

    # --- 4. ENTITY UNIFICATION (THE FIX) ---
    # We create slugs for both club names and states. 
    # This ensures "Camboriú" and "Camboriu" result in the same grouping key.
    df_all_active['club_slug'] = df_all_active['clube'].apply(slugify)
    df_all_active['state_slug'] = df_all_active['estado'].apply(slugify)

    # 5. AGGREGATE STATS AND METADATA
    # We group by the SLUGS to unify duplicates, but aggregate the DISPLAY NAMES.
    active_clubs = df_all_active.groupby(['club_slug', 'state_slug']).agg({
        'clube': 'first',   # Keeps the first display name encountered
        'estado': 'first',  # Keeps the first state name (standardizing "sao-paulo" vs "sao_paulo")
        'cidade': 'first',
        'lat': 'first',
        'lon': 'first',
        'ibge': 'first',
        'wins': 'sum',
        'draws': 'sum',
        'losses': 'sum'
    }).reset_index()

    # 6. FINAL CLEANUP
    # Drop auxiliary slug keys and ensure only teams with valid coordinates remain
    active_clubs = active_clubs.drop(columns=['club_slug', 'state_slug'])
    active_clubs = active_clubs.dropna(subset=['lat', 'lon'])
    
    # Sort by wins to highlight top-performing clubs
    active_clubs = active_clubs.sort_values(by='wins', ascending=False)

    # 7. EXPORT
    active_clubs.to_csv(OUTPUT_FILE, index=False, sep=';', encoding='utf-8-sig')

    print(f"[SUCCESS] Unified registry created: {OUTPUT_FILE}")
    
    # Quick debug check
    try:
        palmeiras_stats = active_clubs[active_clubs['clube'].str.upper() == 'PALMEIRAS']
        if not palmeiras_stats.empty:
            print(f"[STATS] Palmeiras Unified Wins: {palmeiras_stats['wins'].values[0]}")
    except:
        pass
        
    print("="*60)

if __name__ == "__main__":
    main()