import pandas as pd
import re
import unicodedata
import os

# --- CONFIGURATION ---
INPUT_FILE = 'data/02_processed/all_games.csv'
OUTSIDERS_FILE = 'data/01_raw/outsiders.csv'
OUTPUT_FILE = 'data/02_processed/e3e3e33e3_v2.csv'

UF_MAP = {
    'AC': 'acre', 'AL': 'alagoas', 'AP': 'amapa', 'AM': 'amazonas',
    'BA': 'bahia', 'CE': 'ceara', 'DF': 'distrito_federal', 'ES': 'espirito_santo',
    'GO': 'goias', 'MA': 'maranhao', 'MT': 'mato_grosso', 'MS': 'mato_grosso_do_sul',
    'MG': 'minas_gerais', 'PA': 'para', 'PB': 'paraiba', 'PR': 'parana',
    'PE': 'pernambuco', 'PI': 'piaui', 'RJ': 'rio_de_janeiro', 'RN': 'rio_grande_do_norte',
    'RS': 'rio_grande_do_sul', 'RO': 'rondonia', 'RR': 'roraima', 'SC': 'santa_catarina',
    'SP': 'sao_paulo', 'SE': 'sergipe', 'TO': 'tocantins'
}

def slugify(text):
    """Normalize text into a slug format (lowercase, ASCII, underscores)."""
    if pd.isna(text): return ""
    text = str(text).lower().strip()
    text = unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode('utf-8')
    text = re.sub(r'[^a-z0-9_]+', '_', text)
    return re.sub(r'_+', '_', text).strip('_')

def has_accents(text):
    """Check if a string contains accented characters."""
    return text != unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode('utf-8')

def load_outsiders_map(path):
    """Loads the outsiders CSV and returns a dictionary for mapping."""
    if not os.path.exists(path):
        return {}
    df_out = pd.read_csv(path, sep=';', encoding='utf-8-sig')
    mapping = {}
    for _, row in df_out.iterrows():
        key = (slugify(row['clube']), slugify(row['campeonato_jogado']))
        mapping[key] = slugify(row['estado_origem'])
    return mapping

def clean_and_extract(name, league_state, outsiders_map):
    """
    Step 1 & 2: Identifies the correct state and cleans administrative noise.
    """
    if pd.isna(name):
        return "", slugify(league_state)

    raw_name = str(name).upper().strip()
    identified_state = slugify(league_state)

    # 1. State suffix check (-RJ, /SP)
    match_suffix = re.search(r'[\-/]\s*([A-Z]{2})$', raw_name)
    suffix_found = False
    if match_suffix:
        sigla = match_suffix.group(1)
        if sigla in UF_MAP:
            identified_state = UF_MAP[sigla]
            suffix_found = True

    # 2. Clean name noise
    clean_name = re.sub(r'\s*[\-/]\s*[A-Z]{2}$', '', raw_name)
    acronyms = [r'\bF\.?\s*C\.?\b', r'\bE\.?\s*C\.?\b', r'\bS\.?\s*C\.?\b',
                r'\bS\.?\s*E\.?\b', r'\bA\.?\s*C\.?\b', r'\bA\.?\s*A\.?\b']
    for pattern in acronyms:
        clean_name = re.sub(pattern, '', clean_name)
    clean_name = re.sub(r'^\W+|\W+$', '', clean_name).strip()

    # 3. Outsider override
    if not suffix_found:
        club_slug = slugify(clean_name)
        league_slug = slugify(league_state)
        if (club_slug, league_slug) in outsiders_map:
            identified_state = outsiders_map[(club_slug, league_slug)]

    return clean_name, identified_state

def build_canonical_map(df, outsiders_map):
    """
    Analyzes the entire dataset to find the 'best' version of each team name.
    Prioritizes versions with accents (e.g., 'GRÊMIO' over 'GREMIO').
    """
    print("[INFO] Building Canonical Name Map...")
    temp_map = {} # (slug, state) -> best_name

    # Iterate all matches to collect potential names
    for _, row in df.iterrows():
        for team_col in ['mandante', 'visitante']:
            raw_n, state_s = clean_and_extract(row[team_col], row['estado'], outsiders_map)
            slug_n = slugify(raw_n)
            key = (slug_n, state_s)

            if key not in temp_map:
                temp_map[key] = raw_n
            else:
                # If current name has accents and stored doesn't, update
                if has_accents(raw_n) and not has_accents(temp_map[key]):
                    temp_map[key] = raw_n
                # If both have accents, keep the longest one (e.g. 'SÃO PAULO' vs 'SAO PAULO')
                elif len(raw_n) > len(temp_map[key]):
                     if has_accents(raw_n) == has_accents(temp_map[key]):
                        temp_map[key] = raw_n

    return temp_map

def transform_dataframe(df, outsiders_map, canonical_map):
    """Apply transformation using the Canonical Map for name consistency."""
    new_rows = []
    for _, row in df.iterrows():
        if row["estado"] == "regional":
            continue
        # Get clean names and identified states first
        m_clean, m_state = clean_and_extract(row['mandante'], row['estado'], outsiders_map)
        v_clean, v_state = clean_and_extract(row['visitante'], row['estado'], outsiders_map)

        # Standardize names using the Canonical Map
        m_final_name = canonical_map.get((slugify(m_clean), m_state), m_clean)
        v_final_name = canonical_map.get((slugify(v_clean), v_state), v_clean)

        new_row = row.to_dict()
        new_row['mandante'] = m_final_name
        new_row['visitante'] = v_final_name
        new_row['mandante_estado'] = m_state
        new_row['visitante_estado'] = v_state
        new_rows.append(new_row)

    return pd.DataFrame(new_rows)

def reorder_columns(df):
    base_cols = ['estado', 'divisao', 'ano', 'data', 'mandante', 'mandante_estado',
                 'visitante', 'visitante_estado', 'placar', 'resultado', 'peso_importancia']
    cols = base_cols + [c for c in df.columns if c not in base_cols]
    return df[cols]

def main():
    print("="*60)
    print("PIPELINE: STANDARDIZATION & OUTSIDER CORRECTION")
    print("="*60)
    
    df = pd.read_csv(INPUT_FILE, sep=';', encoding='utf-8-sig')
    outsiders_map = load_outsiders_map(OUTSIDERS_FILE)
    
    # 1. Build the canonical dictionary
    canonical_map = build_canonical_map(df, outsiders_map)
    
    # 2. Transform the data
    print("[INFO] Transforming dataset with canonical names...")
    df_v2 = transform_dataframe(df, outsiders_map, canonical_map)
    df_v2 = reorder_columns(df_v2)

    df_v2.to_csv(OUTPUT_FILE, index=False, sep=';', encoding='utf-8-sig')
    print(f"[SUCCESS] Canonical dataset saved to '{OUTPUT_FILE}'")

if __name__ == "__main__":
    main()