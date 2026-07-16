import pandas as pd
import os

# --- CONFIGURATION ---
GAMES_FILE = 'data/03_final/all_games_weights.csv'
GEODATA_FILE = 'data/03_final/all_unique_teams_geolocalization.csv'
MISSING_FILE = 'archive/data/missing_teams.csv'

# --- OUTPUT ---
OUTPUT_FILE = 'data/03_final/all_games_geodata.csv'

def main():
    print("="*60)
    print("INTEGRATION: EXACT GEO MATCH + PAGERANK FLOWS")
    print("="*60)

    # 1. DATA LOADING
    df_games = pd.read_csv(GAMES_FILE, sep=';', encoding='utf-8-sig')
    df_geo = pd.read_csv(GEODATA_FILE, sep=';', encoding='utf-8-sig')

    # 2. CLEAN GEODATA 
    # Remove duplicates to avoid Cartesian product on merge
    df_geo = df_geo.drop_duplicates(subset=['estado', 'clube']).copy()

    # Rename state to avoid column collision with game's 'estado' column
    df_geo.rename(columns={'estado': 'geo_estado'}, inplace=True)

    print("[MERGE] Integrating Home teams coordinates...")
    # 3. MERGE HOME
    df_final = pd.merge(
        df_games,
        df_geo[['geo_estado', 'clube', 'latitude', 'longitude', 'cidade', 'estadio']],
        left_on=['mandante_estado', 'mandante'],
        right_on=['geo_estado', 'clube'],
        how='left'
    ).rename(columns={
        'latitude': 'lat_h',
        'longitude': 'lon_h',
        'cidade': 'cidade_h',
        'estadio': 'estadio_h'
    }).drop(columns=['geo_estado', 'clube'])

    print("[MERGE] Integrating Away teams coordinates...")
    # 4. MERGE AWAY
    df_final = pd.merge(
        df_final,
        df_geo[['geo_estado', 'clube', 'latitude', 'longitude', 'cidade', 'estadio']],
        left_on=['visitante_estado', 'visitante'],
        right_on=['geo_estado', 'clube'],
        how='left'
    ).rename(columns={
        'latitude': 'lat_a',
        'longitude': 'lon_a',
        'cidade': 'cidade_a',
        'estadio': 'estadio_a'
    }).drop(columns=['geo_estado', 'clube'])

    # 5. EXPORT MISSING (For debugging)
    missing_h = df_final[df_final['lat_h'].isna()][['mandante', 'mandante_estado']].rename(columns={'mandante': 'clube', 'mandante_estado': 'estado'})
    missing_a = df_final[df_final['lat_a'].isna()][['visitante', 'visitante_estado']].rename(columns={'visitante': 'clube', 'visitante_estado': 'estado'})
    df_missing = pd.concat([missing_h, missing_a]).drop_duplicates()
    
    if not df_missing.empty:
        os.makedirs(os.path.dirname(MISSING_FILE), exist_ok=True)
        df_missing.to_csv(MISSING_FILE, index=False, sep=';', encoding='utf-8-sig')
        print(f"[WARNING] {len(df_missing)} unique teams without geodata. Saved to missing_teams.csv")

    # 6. FINAL COLUMN REORDERING
    match_info = ['estado', 'divisao', 'ano', 'data', 'mandante', 'mandante_estado', 'visitante', 'visitante_estado', 'placar', 'resultado']
    flow_info = [c for c in ['gols_mandante', 'gols_visitante', 'peso_importancia', 'peso_base', 'fluxo_h', 'fluxo_a'] if c in df_final.columns]
    geo_info = ['lat_h', 'lon_h', 'cidade_h', 'estadio_h', 'lat_a', 'lon_a', 'cidade_a', 'estadio_a']
    
    final_cols = match_info + flow_info + geo_info
    df_final = df_final[final_cols]

    # 7. EXPORT
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    df_final.to_csv(OUTPUT_FILE, index=False, sep=';', encoding='utf-8-sig')
    
    coverage = (df_final['lat_h'].notna().sum() / len(df_final)) * 100
    print("\n" + "="*60)
    print(f"SUCCESS | Final Data Coverage: {coverage:.2f}%")
    print(f"Master File Exported: {OUTPUT_FILE}")
    print("="*60)

if __name__ == "__main__":
    main()