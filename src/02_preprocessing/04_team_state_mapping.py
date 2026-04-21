import pandas as pd
import re

# --- CONFIGURATION ---
INPUT_FILE = 'data/02_processed/all_games_v2.csv'
OUTPUT_FILE = 'data/02_processed/teams_state_mapping.csv'

# Mapping of state abbreviations to full names
UF_MAP = {
    'AC': 'acre', 'AL': 'alagoas', 'AP': 'amapa', 'AM': 'amazonas', 
    'BA': 'bahia', 'CE': 'ceara', 'DF': 'distrito_federal', 'ES': 'espirito_santo', 
    'GO': 'goias', 'MA': 'maranhao', 'MT': 'mato_grosso', 'MS': 'mato_grosso_do_sul', 
    'MG': 'minas_gerais', 'PA': 'para', 'PB': 'paraiba', 'PR': 'parana', 
    'PE': 'pernambuco', 'PI': 'piaui', 'RJ': 'rio_de_janeiro', 'RN': 'rio_grande_do_norte', 
    'RS': 'rio_grande_do_sul', 'RO': 'rondonia', 'RR': 'roraima', 'SC': 'santa_catarina', 
    'SP': 'sao_paulo', 'SE': 'sergipe', 'TO': 'tocantins'
}


def parse_team_and_state(name, league_state):
    """
    Extract a clean team name and its associated state.

    Logic:
    1. If the name contains a suffix " / UF", extract UF and clean the name.
    2. Otherwise, use the league state provided.

    Args:
        name (str): Raw team name.
        league_state (str): State from the dataset.

    Returns:
        tuple[str, str]: Clean team name and resolved state.
    """
    name = str(name).strip()

    match = re.search(r'^(.*)\s*/\s*([A-Z]{2})$', name)
    if match:
        clean_name = match.group(1).strip()
        uf_code = match.group(2).strip()
        state = UF_MAP.get(uf_code, league_state)
        return clean_name, state

    return name, league_state


def build_team_dataset(df):
    """
    Build a dataset of teams with cleaned names and associated states.

    Args:
        df (pd.DataFrame): Input matches dataset.

    Returns:
        pd.DataFrame: Dataset with original name, cleaned name, and state.
    """
    team_data = []

    for _, row in df.iterrows():
        clean_name, state = parse_team_and_state(row['mandante'], row['estado'])
        team_data.append({
            'nome_original': row['mandante'],
            'nome_limpo': clean_name,
            'estado': state
        })

    for _, row in df.iterrows():
        clean_name, state = parse_team_and_state(row['visitante'], row['estado'])
        team_data.append({
            'nome_original': row['visitante'],
            'nome_limpo': clean_name,
            'estado': state
        })

    return pd.DataFrame(team_data)


def resolve_state(group):
    """
    Resolve conflicting states for the same team.

    Preference is given to specific states over 'nacional'.

    Args:
        group (pd.DataFrame): Grouped rows for a team.

    Returns:
        str: Resolved state.
    """
    states = group['estado'].unique()
    specific_states = [s for s in states if s != 'nacional']
    return specific_states[0] if specific_states else 'nacional'


def build_final_mapping(df_teams):
    """
    Create a final mapping of team names to states.

    Args:
        df_teams (pd.DataFrame): Intermediate team dataset.

    Returns:
        pd.DataFrame: Final mapping.
    """
    return (
        df_teams
        .groupby('nome_limpo')
        .apply(lambda x: pd.Series({'estado': resolve_state(x)}))
        .reset_index()
    )


def main():
    """
    Main execution function: loads match data, extracts team-state mappings,
    resolves conflicts, and saves the final dataset.
    """
    df = pd.read_csv(INPUT_FILE, sep=';', encoding='utf-8-sig')

    df_teams = build_team_dataset(df)

    final_mapping = build_final_mapping(df_teams)

    final_mapping.to_csv(OUTPUT_FILE, index=False, sep=';', encoding='utf-8-sig')

    print(f"Total unique teams mapped: {len(final_mapping)}")
    print(f"Saved to '{OUTPUT_FILE}'")


if __name__ == "__main__":
    main()