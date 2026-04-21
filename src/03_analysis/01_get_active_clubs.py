import pandas as pd
import unicodedata
import re

# ==============================================================
# Active clubs -> Played at least one federated match since 2020
# ==============================================================
# --- CONFIGURATION ---
INPUT_FILE = 'data/03_final/all_games_geodata.csv'
OUTPUT_FILE = 'data/03_final/active_clubs_geodata.csv'
START_YEAR = 2020 # using the entire dataset for now

def slugify(text):
    """
    Normalize text into a slug format for consistent matching.

    Removes accents, special characters, and converts to lowercase.

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


def compute_match_outcomes(df):
    """
    Compute win, draw, and loss indicators for home and away teams.

    Args:
        df (pd.DataFrame): Matches dataset.

    Returns:
        pd.DataFrame: Dataset with additional outcome columns.
    """
    df['h_win'] = (df['resultado'] == 'H').astype(int)
    df['h_draw'] = (df['resultado'] == 'D').astype(int)
    df['h_loss'] = (df['resultado'] == 'A').astype(int)

    df['a_win'] = (df['resultado'] == 'A').astype(int)
    df['a_draw'] = (df['resultado'] == 'D').astype(int)
    df['a_loss'] = (df['resultado'] == 'H').astype(int)

    return df


def build_team_views(df):
    """
    Create unified home and away perspectives for aggregation.

    Args:
        df (pd.DataFrame): Matches dataset with outcome columns.

    Returns:
        pd.DataFrame: Combined dataset of team-level records.
    """
    home_view = df[[
        'mandante', 'mandante_estado', 'cidade_h', 'lat_h', 'lon_h', 'ibge_h',
        'h_win', 'h_draw', 'h_loss'
    ]].rename(columns={
        'mandante': 'clube', 'mandante_estado': 'estado', 'cidade_h': 'cidade',
        'lat_h': 'lat', 'lon_h': 'lon', 'ibge_h': 'ibge',
        'h_win': 'wins', 'h_draw': 'draws', 'h_loss': 'losses'
    })

    away_view = df[[
        'visitante', 'visitante_estado', 'cidade_a', 'lat_a', 'lon_a', 'ibge_a',
        'a_win', 'a_draw', 'a_loss'
    ]].rename(columns={
        'visitante': 'clube', 'visitante_estado': 'estado', 'cidade_a': 'cidade',
        'lat_a': 'lat', 'lon_a': 'lon', 'ibge_a': 'ibge',
        'a_win': 'wins', 'a_draw': 'draws', 'a_loss': 'losses'
    })

    return pd.concat([home_view, away_view], ignore_index=True)


def aggregate_clubs(df_all):
    """
    Aggregate club statistics and metadata using slug-based keys.

    Args:
        df_all (pd.DataFrame): Combined team-level dataset.

    Returns:
        pd.DataFrame: Aggregated club dataset.
    """
    df_all['club_slug'] = df_all['clube'].apply(slugify)
    df_all['state_slug'] = df_all['estado'].apply(slugify)

    active_clubs = df_all.groupby(['club_slug', 'state_slug']).agg({
        'clube': 'first',
        'estado': 'first',
        'cidade': 'first',
        'lat': 'first',
        'lon': 'first',
        'ibge': 'first',
        'wins': 'sum',
        'draws': 'sum',
        'losses': 'sum'
    }).reset_index()

    return active_clubs


def finalize_dataset(active_clubs):
    """
    Apply final cleanup steps to the aggregated dataset.

    Args:
        active_clubs (pd.DataFrame): Aggregated dataset.

    Returns:
        pd.DataFrame: Cleaned dataset.
    """
    active_clubs = active_clubs.drop(columns=['club_slug', 'state_slug'])
    active_clubs = active_clubs.dropna(subset=['lat', 'lon'])
    active_clubs = active_clubs.sort_values(by='wins', ascending=False)
    return active_clubs


def main():
    df = pd.read_csv(INPUT_FILE, sep=';', encoding='utf-8-sig')
    df_recent = df[df['ano'] >= START_YEAR].copy()

    df_recent = compute_match_outcomes(df_recent)
    df_all = build_team_views(df_recent)

    active_clubs = aggregate_clubs(df_all)
    active_clubs = finalize_dataset(active_clubs)

    active_clubs.to_csv(OUTPUT_FILE, index=False, sep=';', encoding='utf-8-sig')

    print(f"Saved to '{OUTPUT_FILE}'")


if __name__ == "__main__":
    main()