import pandas as pd
import networkx as nx
import matplotlib.pyplot as plt
import os

# --- CONFIGURATION ---
INPUT_GRAPH = 'data/03_final/graphs/teams_games.graphml'
OUTPUT_FILE = 'data/04_results/pagerank.csv'
PLOT_FILE = 'outputs/plots/pagerank_ranking.png'

ALPHA = 0.85
TOP_N = 40

UF_MAP = {
    'acre': 'AC', 'alagoas': 'AL', 'amapa': 'AP', 'amazonas': 'AM', 'bahia': 'BA',
    'ceara': 'CE', 'distrito_federal': 'DF', 'espirito_santo': 'ES', 'goias': 'GO',
    'maranhao': 'MA', 'mato_grosso': 'MT', 'mato_grosso_do_sul': 'MS', 'minas_gerais': 'MG',
    'para': 'PA', 'paraiba': 'PB', 'parana': 'PR', 'pernambuco': 'PE', 'piaui': 'PI',
    'rio_de_janeiro': 'RJ', 'rio_grande_do_norte': 'RN', 'rio_grande_do_sul': 'RS',
    'rondonia': 'RO', 'roraima': 'RR', 'santa_catarina': 'SC', 'sao_paulo': 'SP',
    'sergipe': 'SE', 'tocantins': 'TO', 'nacional': 'BR'
}


def ensure_dirs():
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    os.makedirs(os.path.dirname(PLOT_FILE), exist_ok=True)


def get_uf(state_slug):
    if not state_slug:
        return "???"
    slug = str(state_slug).lower().replace('-', '_')
    return UF_MAP.get(slug, slug.upper())


def compute_pagerank(G):
    pr_scores = nx.pagerank(G, alpha=ALPHA, weight='weight')

    df_rank = pd.DataFrame(
        [(k, float(v)) for k, v in pr_scores.items()],
        columns=['clube_estado_slug', 'pagerank_score']
    )

    return df_rank.sort_values(by='pagerank_score', ascending=False).reset_index(drop=True)


def safe_split(value):
    """Split 'CLUBE/estado' safely."""
    if isinstance(value, str) and '/' in value:
        parts = value.rsplit('/', 1)
        return parts[0], parts[1]
    return value, None


def format_output(df_rank):
    split_cols = df_rank['clube_estado_slug'].apply(safe_split)
    df_rank[['clube', 'estado_slug']] = pd.DataFrame(split_cols.tolist(), index=df_rank.index)

    df_rank['uf'] = df_rank['estado_slug'].apply(get_uf)
    df_rank['clube'] = df_rank['clube'].astype(str).str.title()

    return df_rank[['clube', 'uf', 'pagerank_score']]


def plot_ranking(df_rank):
    top_clubs = df_rank.head(TOP_N)

    labels = [
        f"{row['clube']} ({row['uf']})"
        for _, row in top_clubs.iterrows()
    ]

    plt.figure(figsize=(12, 10))
    plt.barh(labels[::-1], top_clubs['pagerank_score'][::-1])
    plt.xlabel('PageRank Score')
    plt.title(f'Top {TOP_N} Clubs by PageRank')
    plt.grid(axis='x', linestyle='--', alpha=0.6)

    plt.tight_layout()
    plt.savefig(PLOT_FILE)
    plt.close()


def main():
    ensure_dirs()

    if not os.path.exists(INPUT_GRAPH):
        raise FileNotFoundError(f"Graph not found: {INPUT_GRAPH}")

    G = nx.read_graphml(INPUT_GRAPH)

    # Ensure weights are numeric (GraphML sometimes loads as string)
    for u, v, d in G.edges(data=True):
        if 'weight' in d:
            try:
                d['weight'] = float(d['weight'])
            except:
                d['weight'] = 1.0

    df_rank_raw = compute_pagerank(G)
    df_output = format_output(df_rank_raw)

    df_output.to_csv(OUTPUT_FILE, index=False, sep=';', encoding='utf-8-sig')
    plot_ranking(df_output)


if __name__ == "__main__":
    main()