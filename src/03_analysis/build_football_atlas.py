import pandas as pd
import unicodedata
import re
import os

# --- CONFIGURATION ---
pd.set_option('display.max_rows', None)
GAMES_FILE = 'all_games_final.csv'
MAPPING_FILE = 'teams_state_mapping.csv'
GEODATA_FILE = 'final_brazil_football_geodata_v2.csv'
OUTPUT_FILE = 'final_master_football_atlas.csv'

# Mapeamento para converter siglas em slugs de estado
UF_TO_SLUG = {
    'AC': 'acre', 'AL': 'alagoas', 'AP': 'amapa', 'AM': 'amazonas', 'BA': 'bahia',
    'CE': 'ceara', 'DF': 'distrito_federal', 'ES': 'espirito_santo', 'GO': 'goias',
    'MA': 'maranhao', 'MT': 'mato_grosso', 'MS': 'mato_grosso_do_sul', 'MG': 'minas_gerais',
    'PA': 'para', 'PB': 'paraiba', 'PR': 'parana', 'PE': 'pernambuco', 'PI': 'piaui',
    'RJ': 'rio_de_janeiro', 'RN': 'rio_grande_do_norte', 'RS': 'rio_grande_do_sul',
    'RO': 'rondonia', 'RR': 'roraima', 'SC': 'santa_catarina', 'SP': 'sao_paulo',
    'SE': 'sergipe', 'TO': 'tocantins'
}

def slugify(text):
    if pd.isna(text): return ""
    text = str(text).lower().strip()
    text = unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode('utf-8')
    text = re.sub(r'[^a-z0-9_]+', '_', text)
    return re.sub(r'_+', '_', text).strip('_')

def deep_clean_and_extract(name):
    """
    Cleans names and extracts the UF if present (e.g. 'Flamengo / RJ' -> 'FLAMENGO', 'rio_de_janeiro')
    """
    if pd.isna(name): return "", None
    
    name = str(name).upper().strip()
    extracted_state = None
    
    # 1. Extract UF from formats like ' / RJ', '- RJ', ' /RJ'
    match = re.search(r'[\s\-/]+([A-Z]{2})$', name)
    if match:
        uf_sigla = match.group(1)
        extracted_state = UF_TO_SLUG.get(uf_sigla)
        # Remove the suffix from the name
        name = re.sub(r'[\s\-/]+' + uf_sigla + '$', '', name)
    
    # 2. Remove common acronyms (FC, EC, SC, etc)
    name = re.sub(r'\b(F\.?C\.?|E\.?C\.?|S\.?C\.?|S\.?E\.?|S\.?E\.?R\.?|A\.?C\.?|A\.?A\.?)\b', '', name)
    
    # 3. Clean residual punctuation
    name = re.sub(r'^\W+|\W+$', '', name).strip()
    
    return name, extracted_state

def main():
    print("="*60)
    print("BUILDING MASTER FOOTBALL ATLAS - STATE-AWARE VERSION")
    print("="*60)

    if not all(os.path.exists(f) for f in [GAMES_FILE, MAPPING_FILE, GEODATA_FILE]):
        print("[ERROR] Missing input CSV files.")
        return

    df_games = pd.read_csv(GAMES_FILE, sep=';', encoding='utf-8-sig')
    df_map = pd.read_csv(MAPPING_FILE, sep=';', encoding='utf-8-sig')
    df_geo = pd.read_csv(GEODATA_FILE, sep=';', encoding='utf-8-sig')

    # --- STEP 1: PREPARE GEODATA ---
    df_geo['estado_slug'] = df_geo['estado'].apply(slugify)
    df_geo['nome_key'], _ = zip(*df_geo['nome_simplificado'].apply(deep_clean_and_extract))
    
    # Create a unique match key: NAME + STATE
    df_geo['match_key'] = df_geo['nome_key'] + "_" + df_geo['estado_slug']
    geo_bridge = df_geo.drop_duplicates(subset=['match_key'])

    # --- STEP 2: PROCESS GAMES AND EXTRACT STATES ---
    print("[1/3] Processing games and extracting embedded states...")
    
    def process_row(row, team_col):
        raw_name = row[team_col]
        clean_name, ext_state = deep_clean_and_extract(raw_name)
        
        # If the league state is 'nacional', we use the one extracted from the name
        final_state = ext_state if row['estado'] == 'nacional' else slugify(row['estado'])
        
        return pd.Series([clean_name, final_state, f"{clean_name}_{final_state}"])

    df_games[['mandante_clean', 'm_state', 'm_key']] = df_games.apply(process_row, axis=1, team_col='mandante')
    df_games[['visitante_clean', 'v_state', 'v_key']] = df_games.apply(process_row, axis=1, team_col='visitante')

    # --- STEP 3: JOINING ---
    print("[2/3] Joining with geographic database...")
    
    # Home Join
    df_final = pd.merge(
        df_games,
        geo_bridge[['match_key', 'cidade', 'latitude', 'longitude', 'inception', 'codigo_ibge']],
        left_on='m_key', right_on='match_key', how='left'
    ).drop(columns=['match_key']).rename(columns={
        'cidade': 'cidade_h', 'latitude': 'lat_h', 'longitude': 'lon_h', 
        'inception': 'fundacao_h', 'codigo_ibge': 'ibge_h'
    })

    # Away Join
    df_final = pd.merge(
        df_final,
        geo_bridge[['match_key', 'cidade', 'latitude', 'longitude', 'inception', 'codigo_ibge']],
        left_on='v_key', right_on='match_key', how='left'
    ).drop(columns=['match_key']).rename(columns={
        'cidade': 'cidade_a', 'latitude': 'lat_a', 'longitude': 'lon_a', 
        'inception': 'fundacao_a', 'codigo_ibge': 'ibge_a'
    })

    # --- STEP 4: FINAL CLEANUP ---
    # Replace original messy names with clean names in the final CSV
    df_final['mandante'] = df_final['mandante_clean']
    df_final['visitante'] = df_final['visitante_clean']
    
    # Drop helper columns
    df_final = df_final.drop(columns=['mandante_clean', 'visitante_clean', 'm_state', 'v_state', 'm_key', 'v_key'])

    df_final.to_csv(OUTPUT_FILE, index=False, sep=';', encoding='utf-8-sig')

    # --- STATS ---
    coverage = (df_final['lat_h'].notna().sum() / len(df_final)) * 100
    print("\n" + "="*60)
    print(f"FINAL COVERAGE: {coverage:.2f}%")
    
    if coverage < 90:
        print("\n[DEBUG] Persistent Fails (Home Team):")
        print(df_final[df_final['lat_h'].isna()]['mandante'].value_counts().head(10))

if __name__ == "__main__":
    main()