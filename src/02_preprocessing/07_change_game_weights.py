import pandas as pd

# --- CONFIGURATION ---
INPUT_FILE = 'data/02_processed/all_games_v2.csv'
OUTPUT_FILE = 'data/03_final/all_games_weights.csv'


def calculate_base_weight(row):
    """
    Determine the base importance weight of a match.

    The value represents the total prestige available for transfer
    between teams based on competition scope and division.

    Args:
        row (pd.Series): Match row.

    Returns:
        int: Base weight.
    """
    tourney_type = str(row['estado']).lower()
    div = int(row['divisao'])

    if tourney_type == 'nacional':
        if div == 0:
            return 20
        if div == 1:
            return 20
        if div == 2:
            return 10
        if div == 3:
            return 5
        if div == 4:
            return 3
    else:
        if div == 1:
            return 3
        if div == 2:
            return 2
        if div in [3, 4, 5]:
            return 1
        if div == 0:
            return 1

    return 1


def distribute_flow(df):
    """
    Distribute prestige flow between teams based on match result.

    Rules:
    - Home win: full flow to home team.
    - Away win: full flow to away team.
    - Draw: equal bidirectional flow.

    Args:
        df (pd.DataFrame): Matches dataset.

    Returns:
        pd.DataFrame: Updated dataset with flow columns.
    """
    df.loc[df['resultado'] == 'H', 'fluxo_h'] = df['peso_base']
    df.loc[df['resultado'] == 'H', 'fluxo_a'] = 0

    df.loc[df['resultado'] == 'A', 'fluxo_h'] = 0
    df.loc[df['resultado'] == 'A', 'fluxo_a'] = df['peso_base']

    df.loc[df['resultado'] == 'D', 'fluxo_h'] = df['peso_base'] * 0.5
    df.loc[df['resultado'] == 'D', 'fluxo_a'] = df['peso_base'] * 0.5

    return df


def main():
    df = pd.read_csv(INPUT_FILE, sep=';', encoding='utf-8-sig')

    df['peso_base'] = df.apply(calculate_base_weight, axis=1)
    df = distribute_flow(df)

    if 'peso_importancia' in df.columns:
        df = df.drop(columns=['peso_importancia'])

    df.to_csv(OUTPUT_FILE, index=False, sep=';', encoding='utf-8-sig')

    print(f"Saved to '{OUTPUT_FILE}'")


if __name__ == "__main__":
    main()