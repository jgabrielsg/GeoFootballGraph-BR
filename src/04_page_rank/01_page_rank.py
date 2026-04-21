import pandas as pd
import networkx as nx
import matplotlib.pyplot as plt

# --- CONFIGURATION ---
INPUT_FILE = 'data/03_final/all_games_weights.csv'
OUTPUT_FILE = 'data/04_results/pagerank.csv'
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


def get_uf(state_slug):
    """
    Convert a state slug into its UF abbreviation.

    Args:
        state_slug (str): State slug.

    Returns:
        str: UF abbreviation.
    """
    slug = str(state_slug).lower().replace('-', '_')
    return UF_MAP.get(slug, slug.upper())


def build_graph(df):
    """
    Build a directed graph representing prestige flow between teams.

    Args:
        df (pd.DataFrame): Matches dataset.

    Returns:
        networkx.DiGraph: Directed weighted graph.
    """
    G = nx.DiGraph()

    for _, row in df.iterrows():
        if row['fluxo_h'] > 0:
            if G.has_edge(row['a_id'], row['h_id']):
                G[row['a_id']][row['h_id']]['weight'] += row['fluxo_h']
            else:
                G.add_edge(row['a_id'], row['h_id'], weight=row['fluxo_h'])

        if row['fluxo_a'] > 0:
            if G.has_edge(row['h_id'], row['a_id']):
                G[row['h_id']][row['a_id']]['weight'] += row['fluxo_a']
            else:
                G.add_edge(row['h_id'], row['a_id'], weight=row['fluxo_a'])

    return G


def compute_pagerank(G):
    """
    Compute PageRank scores for the graph.

    Args:
        G (networkx.DiGraph): Input graph.

    Returns:
        pd.DataFrame: Ranked nodes with scores.
    """
    pr_scores = nx.pagerank(G, alpha=ALPHA, weight='weight')
    df_rank = pd.DataFrame(list(pr_scores.items()), columns=['clube_uf', 'pagerank_score'])
    return df_rank.sort_values(by='pagerank_score', ascending=False).reset_index(drop=True)


def format_output(df_rank):
    """
    Split combined identifiers into club name and UF.

    Args:
        df_rank (pd.DataFrame): Ranking dataframe.

    Returns:
        pd.DataFrame: Formatted output.
    """
    df_rank[['clube', 'uf']] = df_rank['clube_uf'].str.split('/', expand=True)
    df_rank['clube'] = df_rank['clube'].str.title()
    return df_rank[['clube', 'uf', 'pagerank_score']]


def plot_ranking(df_rank):
    """
    Plot top-N PageRank results.

    Args:
        df_rank (pd.DataFrame): Ranking dataframe.
    """
    top_clubs = df_rank.head(TOP_N)

    plt.figure(figsize=(12, 10))
    plt.barh(top_clubs['clube'][::-1], top_clubs['pagerank_score'][::-1])
    plt.xlabel('PageRank Score')
    plt.title(f'Top {TOP_N} Brazilian Clubs by PageRank')
    plt.grid(axis='x', linestyle='--', alpha=0.6)

    plt.tight_layout()
    plt.savefig('football_pagerank_ranking.png')
    plt.show()


def main():
    """
    Main execution function: builds the graph, computes PageRank,
    formats output, and saves results.
    """
    df = pd.read_csv(INPUT_FILE, sep=';', encoding='utf-8-sig')

    df['h_id'] = df['mandante'] + "/" + df['mandante_estado'].apply(get_uf)
    df['a_id'] = df['visitante'] + "/" + df['visitante_estado'].apply(get_uf)

    G = build_graph(df)

    df_rank = compute_pagerank(G)
    df_output = format_output(df_rank)

    df_output.to_csv(OUTPUT_FILE, index=False, sep=';', encoding='utf-8-sig')

    plot_ranking(df_output)

    print(f"Saved to '{OUTPUT_FILE}'")


if __name__ == "__main__":
    main()