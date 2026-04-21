import pandas as pd
import unicodedata
import re

# --- CONFIGURATION ---
INPUT_FILE = 'data/02_processed/all_games.csv'
OUTPUT_FILE = 'data/02_processed/all_games_2121212.csv'


def slugify(text):
    """
    Convert text into a normalized slug for duplicate identification.

    This removes accents, lowercases the text, and replaces non-alphanumeric
    characters with underscores.

    Args:
        text (str): Input text.

    Returns:
        str: Normalized slug string.
    """
    if pd.isna(text):
        return ""
    text = str(text).lower().strip()
    text = unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode('utf-8')
    text = re.sub(r'[^a-z0-9_]+', '_', text)
    return re.sub(r'_+', '_', text).strip('_')


def build_canonical_map(df):
    """
    Build a mapping of normalized (slug + state) keys to canonical names.

    Args:
        df (pd.DataFrame): Input dataset.

    Returns:
        dict: Mapping from slug keys to canonical names.
    """
    all_names = pd.concat([
        df[['mandante', 'mandante_estado']].rename(columns={'mandante': 'nome', 'mandante_estado': 'estado'}),
        df[['visitante', 'visitante_estado']].rename(columns={'visitante': 'nome', 'visitante_estado': 'estado'})
    ]).drop_duplicates()

    all_names['slug_key'] = all_names['nome'].apply(slugify) + "_" + all_names['estado'].apply(slugify)

    canonical_map = (
        all_names
        .sort_values(by='nome', ascending=False)
        .groupby('slug_key')['nome']
        .first()
        .to_dict()
    )

    return canonical_map


def unify_name(name, state, canonical_map):
    """
    Replace a name with its canonical version based on slug and state.

    Args:
        name (str): Original name.
        state (str): State associated with the name.
        canonical_map (dict): Mapping of canonical names.

    Returns:
        str: Canonical name if found, otherwise original name.
    """
    key = slugify(name) + "_" + slugify(state)
    return canonical_map.get(key, name)


def main():
    """
    Main execution function: loads data, normalizes entity names,
    and saves a unified dataset.
    """
    print("=" * 60)
    print("UNIFYING ENTITIES: REMOVING ACCENT-BASED DUPLICATES")
    print("=" * 60)

    df = pd.read_csv(INPUT_FILE, sep=';', encoding='utf-8-sig')

    canonical_map = build_canonical_map(df)

    print("[PROCESS] Applying canonical names...")

    df['mandante'] = df.apply(
        lambda x: unify_name(x['mandante'], x['mandante_estado'], canonical_map), axis=1
    )
    df['visitante'] = df.apply(
        lambda x: unify_name(x['visitante'], x['visitante_estado'], canonical_map), axis=1
    )

    df.to_csv(OUTPUT_FILE, index=False, sep=';', encoding='utf-8-sig')

    print(f"[SUCCESS] Unified dataset saved to: {OUTPUT_FILE}")
    print(f"Example correction: Camboriu -> {unify_name('Camboriu', 'santa-catarina', canonical_map)}")
    print("=" * 60)


if __name__ == "__main__":
    main()