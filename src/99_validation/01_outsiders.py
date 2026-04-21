import pandas as pd

# --- CONFIGURATION ---
FILE_PATH = 'data/02_processed/all_games_v2.csv'
INTRUDERS_FILE = 'data/01_raw/outsiders.csv'


def load_data():
    return pd.read_csv(FILE_PATH, sep=';', encoding='utf-8-sig')

def filter_state_competitions(df):
    return df[~df['estado'].isin(['nacional', 'regional'])].copy()

def find_intruders(df):
    """
    Identify teams playing outside their home state in state competitions.

    Args:
        df (pd.DataFrame): State competitions dataset.

    Returns:
        pd.DataFrame: Unique intruder cases.
    """
    intruders_h = df[df['estado'] != df['mandante_estado']][
        ['mandante', 'mandante_estado', 'estado']
    ].copy()
    intruders_h.columns = ['clube', 'estado_origem', 'campeonato_jogado']

    intruders_v = df[df['estado'] != df['visitante_estado']][
        ['visitante', 'visitante_estado', 'estado']
    ].copy()
    intruders_v.columns = ['clube', 'estado_origem', 'campeonato_jogado']

    intruders = pd.concat([intruders_h, intruders_v])

    return intruders.drop_duplicates().sort_values(by='clube')


def report_intruders(df_intruders):
    print(f"Intruder cases: {len(df_intruders)}")

    if not df_intruders.empty:
        print(df_intruders.to_string(index=False))


def main():
    df = load_data()
    estaduais = filter_state_competitions(df)
    intruders = find_intruders(estaduais)

    report_intruders(intruders)
    print(f"\n\nCheck if this is exactly as {INTRUDERS_FILE}:\n")
    print(pd.read_csv(INTRUDERS_FILE))


if __name__ == "__main__":
    main()