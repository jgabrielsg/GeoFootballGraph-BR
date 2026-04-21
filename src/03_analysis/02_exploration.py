import pandas as pd
import numpy as np

# --- CONFIGURATION ---
INPUT_FILE = r'data\03_final\all_games_geodata.csv'

REQUIRED_COLUMNS = [
    'estado', 'divisao', 'ano', 'data',
    'mandante', 'mandante_estado',
    'visitante', 'visitante_estado',
    'resultado', 'gols_mandante', 'gols_visitante'
]


def validate_schema(df):
    """
    Validate required columns and basic structure.

    Args:
        df (pd.DataFrame): Input dataset.
    """
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"Missing columns: {missing}")


def validate_values(df):
    """
    Validate core domain constraints.

    - resultado ∈ {H, A, D}
    - goals are non-negative
    - divisao and ano are numeric
    """
    df['resultado'] = df['resultado'].astype(str).str.upper().str.strip()

    valid_results = {'H', 'A', 'D'}
    invalid_results = df[~df['resultado'].isin(valid_results)]
    if not invalid_results.empty:
        print(f"[WARN] Invalid results found: {len(invalid_results)}")

    for col in ['gols_mandante', 'gols_visitante']:
        df[col] = pd.to_numeric(df[col], errors='coerce')
        invalid_goals = df[df[col] < 0]
        if not invalid_goals.empty:
            print(f"[WARN] Negative values in {col}: {len(invalid_goals)}")

    df['divisao'] = pd.to_numeric(df['divisao'], errors='coerce')
    df['ano'] = pd.to_numeric(df['ano'], errors='coerce')

    return df


def validate_consistency(df):
    """
    Validate logical consistency between score and result.
    """
    mismatch = df[
        ((df['gols_mandante'] > df['gols_visitante']) & (df['resultado'] != 'H')) |
        ((df['gols_mandante'] < df['gols_visitante']) & (df['resultado'] != 'A')) |
        ((df['gols_mandante'] == df['gols_visitante']) & (df['resultado'] != 'D'))
    ]

    if not mismatch.empty:
        print(f"[WARN] Inconsistent result vs score: {len(mismatch)}")


def validate_geodata(df):
    """
    Validate geographic fields (lat/lon ranges if present).
    """
    if 'lat_h' in df.columns and 'lon_h' in df.columns:
        invalid_geo = df[
            (df['lat_h'].abs() > 90) | (df['lon_h'].abs() > 180)
        ]
        if not invalid_geo.empty:
            print(f"[WARN] Invalid home coordinates: {len(invalid_geo)}")

    if 'lat_a' in df.columns and 'lon_a' in df.columns:
        invalid_geo = df[
            (df['lat_a'].abs() > 90) | (df['lon_a'].abs() > 180)
        ]
        if not invalid_geo.empty:
            print(f"[WARN] Invalid away coordinates: {len(invalid_geo)}")


def build_long_format(df):
    """
    Convert dataset into long format (team-level view).

    Returns:
        pd.DataFrame: Unified team-level dataset.
    """
    home = df[['mandante', 'mandante_estado', 'resultado',
               'gols_mandante', 'gols_visitante', 'divisao', 'estado']].copy()
    home.columns = ['clube', 'uf_origem', 'res', 'gols_pro', 'gols_contra', 'div', 'liga']
    home['win'] = (home['res'] == 'H').astype(int)
    home['loss'] = (home['res'] == 'A').astype(int)
    home['draw'] = (home['res'] == 'D').astype(int)

    away = df[['visitante', 'visitante_estado', 'resultado',
               'gols_visitante', 'gols_mandante', 'divisao', 'estado']].copy()
    away.columns = ['clube', 'uf_origem', 'res', 'gols_pro', 'gols_contra', 'div', 'liga']
    away['win'] = (away['res'] == 'A').astype(int)
    away['loss'] = (away['res'] == 'H').astype(int)
    away['draw'] = (away['res'] == 'D').astype(int)

    all_teams = pd.concat([home, away], ignore_index=True)
    all_teams['goleada'] = ((all_teams['win'] == 1) &
                            (all_teams['gols_pro'] - all_teams['gols_contra'] >= 4)).astype(int)

    return all_teams


def compute_stats(all_teams):
    """
    Aggregate team statistics.

    Returns:
        pd.DataFrame: Team-level metrics.
    """
    stats = all_teams.groupby(['clube', 'uf_origem']).agg({
        'win': 'sum',
        'draw': 'sum',
        'loss': 'sum',
        'gols_pro': 'sum',
        'gols_contra': 'sum',
        'goleada': 'sum'
    })

    stats['jogos'] = stats['win'] + stats['draw'] + stats['loss']
    stats['aproveitamento'] = np.where(
        stats['jogos'] > 0,
        (stats['win'] * 3 + stats['draw']) / (stats['jogos'] * 3),
        0
    )

    return stats


def main():
    """
    Main execution: validate dataset, transform to long format,
    compute statistics, and print summaries.
    """
    df = pd.read_csv(INPUT_FILE, sep=';', encoding='utf-8-sig')

    validate_schema(df)
    df = validate_values(df)
    validate_consistency(df)
    validate_geodata(df)

    all_teams = build_long_format(df)
    stats = compute_stats(all_teams)

    print(f"Matches: {len(df)}")
    print(f"Teams: {len(stats)}")

    print("\nTop activity:")
    print(stats.sort_values(by='jogos', ascending=False).head(10)[['jogos', 'win']])

    print("\nTop wins:")
    print(stats.sort_values(by='win', ascending=False).head(10)[['win', 'jogos']])

    print("\nTop attack:")
    print(stats.sort_values(by='gols_pro', ascending=False).head(10)[['gols_pro']])

    print("\nTop conceded:")
    print(stats.sort_values(by='gols_contra', ascending=False).head(10)[['gols_contra']])

    print("\nTop goleadas:")
    print(stats.sort_values(by='goleada', ascending=False).head(10)[['goleada']])


if __name__ == "__main__":
    main()