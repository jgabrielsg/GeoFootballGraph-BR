import pandas as pd
import numpy as np
import os
import re

# --- CONFIGURATION ---
INPUT_FILES = [
    'data/01_raw/games/jogos_estaduais_part1.csv', 
    'data/01_raw/games/jogos_estaduais_part2.csv',
    'data/01_raw/games/jogos_estaduais_part3.csv', 
    'data/01_raw/games/jogos_estaduais_part4.csv',
    'data/01_raw/games/jogos_nacionais_full.csv'
]
OUTPUT_FILE = 'data/02_processed/all_games.csv'


def clean_and_parse_score(placar_raw):
    """
    Extract goals and match result from a raw score string.

    Supports formats like '1-0', '2 X 1', or '1-0(5-4 Pen.)'.
    Any content after the main score is ignored.

    Args:
        placar_raw (str): Raw score string.

    Returns:
        tuple[int|None, int|None, str|None]:
            Home goals, away goals, and result ('H', 'A', 'D').
            Returns (None, None, None) if parsing fails.
    """
    if pd.isna(placar_raw):
        return None, None, None

    try:
        match = re.search(r'(\d+)\s*[-Xx]\s*(\d+)', str(placar_raw))
        if match:
            h_goals = int(match.group(1))
            a_goals = int(match.group(2))

            if h_goals > a_goals:
                res = 'H'
            elif a_goals > h_goals:
                res = 'A'
            else:
                res = 'D'

            return h_goals, a_goals, res
    except Exception:
        pass

    return None, None, None


def calculate_importance(row):
    """
    Compute importance weight based on competition scope and division.

    Args:
        row (pd.Series): Match row.

    Returns:
        float: Importance weight.
    """
    is_national = str(row['estado']).lower() == 'nacional'
    div = int(row['divisao'])

    if is_national:
        weights = {
            0: 20.0,
            1: 20.0,
            2: 10.0,
            3: 5.0,
            4: 3.0
        }
        return weights.get(div, 1.0)

    if div == 1:
        return 3.0
    elif div == 2:
        return 1.0
    return 1.0


def load_and_process_file(file_path):
    """
    Load a CSV file, clean scores, and extract structured match data.

    Args:
        file_path (str): Path to input file.

    Returns:
        pd.DataFrame: Processed dataframe.
    """
    df = pd.read_csv(file_path, sep=';', encoding='utf-8-sig')

    df['ano'] = pd.to_numeric(df['ano'], errors='coerce')
    df = df.dropna(subset=['ano'])
    df['ano'] = df['ano'].astype(int)

    score_data = df['placar'].apply(clean_and_parse_score)

    results_df = pd.DataFrame(
        score_data.tolist(),
        index=df.index,
        columns=['gols_mandante', 'gols_visitante', 'resultado']
    )

    df = pd.concat([df, results_df], axis=1)
    df = df.dropna(subset=['resultado'])

    return df


def summarize_dataset(all_games):
    """
    Print key statistics for the consolidated dataset.

    Args:
        all_games (pd.DataFrame): Final dataset.
    """
    print(f"TOTAL MATCHES: {len(all_games)}")

    all_teams = set(all_games['mandante'].unique()) | set(all_games['visitante'].unique())
    print(f"UNIQUE TEAMS: {len(all_teams)}")

    print("\nRESULT DISTRIBUTION (%)")
    print(all_games['resultado'].value_counts(normalize=True) * 100)

    print("\nAVERAGE IMPORTANCE BY DIVISION:")
    print(all_games.groupby(['estado', 'divisao'])['peso_importancia'].mean())

    print("\nMATCHES PER YEAR:")
    print(all_games['ano'].value_counts().sort_index())


def main():
    processed_dfs = []

    for file in INPUT_FILES:
        if not os.path.exists(file):
            continue
        processed_dfs.append(load_and_process_file(file))

    if not processed_dfs:
        print("No data processed.")
        return

    all_games = pd.concat(processed_dfs, ignore_index=True)
    all_games['peso_importancia'] = all_games.apply(calculate_importance, axis=1)
    all_games['gols_mandante'] = all_games['gols_mandante'].astype(int)
    all_games['gols_visitante'] = all_games['gols_visitante'].astype(int)
    
    all_games.to_csv(OUTPUT_FILE, index=False, sep=';', encoding='utf-8-sig')
    summarize_dataset(all_games)
    print(f"\nSaved to '{OUTPUT_FILE}'")


if __name__ == "__main__":
    main()