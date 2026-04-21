import pandas as pd
import re

# --- CONFIGURATION ---
INPUT_FILE = 'data/02_processed/all_clubs_geodata.csv'
OUTPUT_FILE = 'data/03_final/all_clubs_geodata.csv'

# Words that define the "administrative" part of the club
NOISE_WORDS = {
    'SPORT', 'CLUB', 'CLUBE', 'SOCIEDADE', 'ESPORTIVA', 'ESPORTE', 'ESPORTIVO', 
    'FUTEBOL', 'REGATAS', 'RECREAÇÃO', 'RECREATIVO', 'RECREATIVA', 'ASSOCIAÇÃO', 
    'NATAÇÃO', 'FOOT-BALL', 'FOOTBALL', 'DESPORTIVA', 'CULTURAL', 'RECREAÇAO', 
    'ASSOCIAÇÃO', 'DESPORTOS', 'DESPORTE', "DESPORTO", "ATLÉTICA", "FOOT", "BALL",
    "FOOT-BALL"
}

PREPOSITIONS = {'DE', 'DO', 'DOS', 'DA', 'DAS', "E"}


def smart_clean_name(name):
    """
    Apply contextual cleaning to club names.

    Steps:
    1. Normalize text and tokenize.
    2. Mark administrative (noise) words for removal.
    3. Remove prepositions only if adjacent to removed tokens.
    4. Rebuild the cleaned name.

    Args:
        name (str): Original club name.

    Returns:
        str: Simplified club name.
    """
    if pd.isna(name):
        return ""

    name = re.sub(r'-[A-Z]{2}$', '', str(name).upper())
    tokens = re.findall(r"[\w'-]+", name)

    to_remove = [False] * len(tokens)

    for i, token in enumerate(tokens):
        if token in NOISE_WORDS:
            to_remove[i] = True

    for i, token in enumerate(tokens):
        if token in PREPOSITIONS:
            has_prev_removed = to_remove[i - 1] if i > 0 else False
            has_next_removed = to_remove[i + 1] if i < len(tokens) - 1 else False
            if has_prev_removed or has_next_removed:
                to_remove[i] = True

    clean_tokens = [t for i, t in enumerate(tokens) if not to_remove[i]]

    if not clean_tokens:
        return name

    return " ".join(clean_tokens)


def reorder_columns(df):
    """
    Reorder dataframe columns to place the simplified name first.

    Args:
        df (pd.DataFrame): Input dataframe.

    Returns:
        pd.DataFrame: Reordered dataframe.
    """
    cols = ['nome_simplificado', 'nome_clube'] + [
        c for c in df.columns if c not in ['nome_simplificado', 'nome_clube']
    ]
    return df[cols]


def main():
    """
    Main execution function: loads geodata, applies name cleaning,
    and saves the updated dataset.
    """
    print("Loading geodata...")
    df = pd.read_csv(INPUT_FILE, sep=';', encoding='utf-8-sig')

    print("Applying smart cleaning logic...")
    df['nome_simplificado'] = df['nome_clube'].apply(smart_clean_name)

    df = reorder_columns(df)

    df.to_csv(OUTPUT_FILE, index=False, sep=';', encoding='utf-8-sig')

    print("\n--- SAMPLES OF CLEANING ---")
    for _, row in df.head(15).iterrows():
        print(f"Original: {row['nome_clube']} -> Simplified: {row['nome_simplificado']}")

    print(f"\nFile saved as {OUTPUT_FILE}")


if __name__ == "__main__":
    main()