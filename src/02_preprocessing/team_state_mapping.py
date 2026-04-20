import pandas as pd
import re

# --- CONFIGURAÇÃO ---
INPUT_FILE = 'all_games_final.csv'
OUTPUT_FILE = 'teams_state_mapping.csv'

# Mapeamento de siglas para nomes por extenso (para bater com o IBGE/Wikipedia)
UF_MAP = {
    'AC': 'acre', 'AL': 'alagoas', 'AP': 'amapa', 'AM': 'amazonas', 
    'BA': 'bahia', 'CE': 'ceara', 'DF': 'distrito federal', 'ES': 'espirito santo', 
    'GO': 'goias', 'MA': 'maranhao', 'MT': 'mato grosso', 'MS': 'mato grosso do sul', 
    'MG': 'minas gerais', 'PA': 'para', 'PB': 'paraiba', 'PR': 'parana', 
    'PE': 'pernambuco', 'PI': 'piaui', 'RJ': 'rio de janeiro', 'RN': 'rio grande do norte', 
    'RS': 'rio grande do sul', 'RO': 'rondonia', 'RR': 'roraima', 'SC': 'santa catarina', 
    'SP': 'sao paulo', 'SE': 'sergipe', 'TO': 'tocantins'
}

def parse_team_and_state(name, league_state):
    """
    Extracts the clean team name and the state.
    Logic: 
    1. If has ' / UF', extract UF and clean name.
    2. If league_state is not 'nacional', use league_state.
    """
    name = str(name).strip()
    
    # 1. Check for suffix " / UF" (common in national games)
    match = re.search(r'^(.*)\s*/\s*([A-Z]{2})$', name)
    if match:
        clean_name = match.group(1).strip()
        uf_code = match.group(2).strip()
        state = UF_MAP.get(uf_code, league_state)
        return clean_name, state
    
    # 2. If no suffix, use the league state from the CSV
    return name, league_state

def main():
    print("Reading games data...")
    df = pd.read_csv(INPUT_FILE, sep=';', encoding='utf-8-sig')
    
    team_data = []

    # Process Mandantes
    print("Processing home teams...")
    for _, row in df.iterrows():
        clean_name, state = parse_team_and_state(row['mandante'], row['estado'])
        team_data.append({'nome_original': row['mandante'], 'nome_limpo': clean_name, 'estado': state})

    # Process Visitantes
    print("Processing away teams...")
    for _, row in df.iterrows():
        clean_name, state = parse_team_and_state(row['visitante'], row['estado'])
        team_data.append({'nome_original': row['visitante'], 'nome_limpo': clean_name, 'estado': state})

    # Create DataFrame and deduplicate
    df_teams = pd.DataFrame(team_data)
    
    # Logic: some teams appear in 'nacional' and 'state' leagues. 
    # We group by clean name and pick the state that is not 'nacional' if available.
    print("Resolving state conflicts...")
    
    def resolve_state(group):
        states = group['estado'].unique()
        # If there is a specific state (not 'nacional'), pick it
        specific_states = [s for s in states if s != 'nacional']
        return specific_states[0] if specific_states else 'nacional'

    final_mapping = df_teams.groupby('nome_limpo').apply(lambda x: pd.Series({
        'estado': resolve_state(x)
    })).reset_index()

    # Save mapping
    final_mapping.to_csv(OUTPUT_FILE, index=False, sep=';', encoding='utf-8-sig')
    
    print(f"\n--- SUCCESS ---")
    print(f"Total unique teams mapped: {len(final_mapping)}")
    print(f"Sample mapping:\n{final_mapping.head(10)}")
    print(f"File saved: {OUTPUT_FILE}")

if __name__ == "__main__":
    main()