import pandas as pd
import unicodedata
import re
import os

# --- CONFIGURATION ---
pd.set_option('display.max_rows', None)
GAMES_FILE = 'data/03_final/all_games_final.csv'
MAPPING_FILE = 'data/02_processed/teams_state_mapping.csv'
GEODATA_FILE = 'data/03_final/all_clubs_geodata.csv'
OUTPUT_FILE = 'data/03_final/all_games_geodata.csv'

# Mapping from state abbreviations to slug format
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
    """
    Normalize text into a slug format.

    Args:
        text (str): Input text.

    Returns:
        str: Normalized slug.
    """
    if pd.isna(text):
        return ""
    text = str(text).lower().strip()
    text = unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode('utf-8')
    text = re.sub(r'[^a-z0-9_]+', '_', text)
    return re.sub(r'_+', '_', text).strip('_')


def deep_clean_and_extract(name):
    """
    Clean team names and optionally extract state information.

    Handles suffixes such as ' / RJ' or '- RJ', removes common acronyms,
    and trims punctuation.

    Args:
        name (str): Raw team name.

    Returns:
        tuple[str, str|None]: Cleaned name and extracted state slug (if any).
    """
    if pd.isna(name):
        return "", None

    name = str(name).upper().strip()
    extracted_state = None

    match = re.search(r'[\s\-/]+([A-Z]{2})$', name)
    if match:
        uf_sigla = match.group(1)
        extracted_state = UF_TO_SLUG.get(uf_sigla)
        name = re.sub(r'[\s\-/]+' + uf_sigla + '$', '', name)

    name = re.sub(r'\b(F\.?C\.?|E\.?C\.?|S\.?C\.?|S\.?E\.?|S\.?E\.?R\.?|A\.?C\.?|A\.?A\.?)\b', '', name)
    name = re.sub(r'^\W+|\W+$', '', name).strip()

    return name, extracted_state


def prepare_geodata(df_geo):
    """
    Prepare geodata by creating normalized keys for matching.

    Args:
        df_geo (pd.DataFrame): Geolocation dataset.

    Returns:
        pd.DataFrame: Deduplicated geodata with match keys.
    """
    df_geo['estado_slug'] = df_geo['estado'].apply(slugify)
    df_geo['nome_key'], _ = zip(*df_geo['nome_simplificado'].apply(deep_clean_and_extract))
    df_geo['match_key'] = df_geo['nome_key'] + "_" + df_geo['estado_slug']
    return df_geo.drop_duplicates(subset=['match_key'])


def process_games(df_games):
    """
    Process match dataset to extract cleaned names and matching keys.

    Args:
        df_games (pd.DataFrame): Matches dataset.

    Returns:
        pd.DataFrame: Updated dataset with matching keys.
    """
    def process_row(row, team_col):
        raw_name = row[team_col]
        clean_name, ext_state = deep_clean_and_extract(raw_name)
        final_state = ext_state if row['estado'] == 'nacional' else slugify(row['estado'])
        return pd.Series([clean_name, final_state, f"{clean_name}_{final_state}"])

    df_games[['mandante_clean', 'm_state', 'm_key']] = df_games.apply(process_row, axis=1, team_col='mandante')
    df_games[['visitante_clean', 'v_state', 'v_key']] = df_games.apply(process_row, axis=1, team_col='visitante')

    return df_games


def join_geodata(df_games, geo_bridge):
    """
    Join match data with geolocation data for home and away teams.

    Args:
        df_games (pd.DataFrame): Processed matches dataset.
        geo_bridge (pd.DataFrame): Prepared geodata.

    Returns:
        pd.DataFrame: Final merged dataset.
    """
    df_final = pd.merge(
        df_games,
        geo_bridge[['match_key', 'cidade', 'latitude', 'longitude', 'inception', 'codigo_ibge']],
        left_on='m_key', right_on='match_key', how='left'
    ).drop(columns=['match_key']).rename(columns={
        'cidade': 'cidade_h', 'latitude': 'lat_h', 'longitude': 'lon_h',
        'inception': 'fundacao_h', 'codigo_ibge': 'ibge_h'
    })

    df_final = pd.merge(
        df_final,
        geo_bridge[['match_key', 'cidade', 'latitude', 'longitude', 'inception', 'codigo_ibge']],
        left_on='v_key', right_on='match_key', how='left'
    ).drop(columns=['match_key']).rename(columns={
        'cidade': 'cidade_a', 'latitude': 'lat_a', 'longitude': 'lon_a',
        'inception': 'fundacao_a', 'codigo_ibge': 'ibge_a'
    })

    return df_final


def finalize_dataset(df_final):
    """
    Apply final cleanup and overwrite original team names.

    Args:
        df_final (pd.DataFrame): Merged dataset.

    Returns:
        pd.DataFrame: Cleaned dataset.
    """
    df_final['mandante'] = df_final['mandante_clean']
    df_final['visitante'] = df_final['visitante_clean']

    return df_final.drop(columns=[
        'mandante_clean', 'visitante_clean',
        'm_state', 'v_state', 'm_key', 'v_key'
    ])


def main():
    if not all(os.path.exists(f) for f in [GAMES_FILE, MAPPING_FILE, GEODATA_FILE]):
        print("Missing input files.")
        return

    df_games = pd.read_csv(GAMES_FILE, sep=';', encoding='utf-8-sig')
    df_geo = pd.read_csv(GEODATA_FILE, sep=';', encoding='utf-8-sig')

    geo_bridge = prepare_geodata(df_geo)
    df_games = process_games(df_games)
    df_final = join_geodata(df_games, geo_bridge)
    df_final = finalize_dataset(df_final)

    df_final.to_csv(OUTPUT_FILE, index=False, sep=';', encoding='utf-8-sig')

    coverage = (df_final['lat_h'].notna().sum() / len(df_final)) * 100
    print(f"Coverage: {coverage:.2f}%")

    if coverage < 90:
        print(df_final[df_final['lat_h'].isna()]['mandante'].value_counts().head(10))


if __name__ == "__main__":
    main()