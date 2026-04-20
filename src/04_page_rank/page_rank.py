import pandas as pd
import networkx as nx
import matplotlib.pyplot as plt

# --- CONFIGURATION ---
INPUT_FILE = 'all_games_clean_final.csv'
ALPHA = 0.85
TOP_N = 20

# Mapping state slugs to official UF abbreviations
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
    """Returns the UF abbreviation from a slug, or the slug itself if not found."""
    slug = str(state_slug).lower().replace('-', '_')
    return UF_MAP.get(slug, slug.upper())

def main():
    """
    Constructs a directed graph using unique identifiers (Name/UF) 
    to prevent entity collision and calculates PageRank.
    """
    print("="*60)
    print("REFINED PAGERANK: ENTITY DIFFERENTIATION BY STATE")
    print("="*60)

    # 1. LOAD DATA
    df = pd.read_csv(INPUT_FILE, sep=';', encoding='utf-8-sig')
    
    # 2. CREATE UNIQUE IDENTIFIERS
    # We combine Name and UF to separate homonymous clubs (e.g., Botafogo/RJ vs Botafogo/PB)
    print("[PROCESS] Creating unique identifiers (Name/UF)...")
    df['h_id'] = df['mandante'] + "/" + df['mandante_estado'].apply(get_uf)
    df['a_id'] = df['visitante'] + "/" + df['visitante_estado'].apply(get_uf)

    # 3. INITIALIZE DIRECTED GRAPH
    G = nx.DiGraph()

    # 4. ADD EDGES (PRESTIGE FLOW)
    print("[PROCESS] Building graph edges with unique nodes...")
    for _, row in df.iterrows():
        # Home team earned prestige
        if row['fluxo_h'] > 0:
            if G.has_edge(row['a_id'], row['h_id']):
                G[row['a_id']][row['h_id']]['weight'] += row['fluxo_h']
            else:
                G.add_edge(row['a_id'], row['h_id'], weight=row['fluxo_h'])
        
        # Away team earned prestige
        if row['fluxo_a'] > 0:
            if G.has_edge(row['h_id'], row['a_id']):
                G[row['h_id']][row['a_id']]['weight'] += row['fluxo_a']
            else:
                G.add_edge(row['h_id'], row['a_id'], weight=row['fluxo_a'])

    # 5. RUN PAGERANK
    print(f"[ALGO] Running PageRank on {G.number_of_nodes()} unique entities...")
    pr_scores = nx.pagerank(G, alpha=ALPHA, weight='weight')

    # 6. RANKING AND EXPORT
    df_rank = pd.DataFrame(list(pr_scores.items()), columns=['clube_uf', 'pagerank_score'])
    df_rank = df_rank.sort_values(by='pagerank_score', ascending=False).reset_index(drop=True)

    # 7. VISUALIZATION
    print(f"[PLOTTING] Plotting Top {TOP_N} Unique Clubs...")
    plt.figure(figsize=(12, 10))
    top_clubs = df_rank.head(TOP_N)
    
    plt.barh(top_clubs['clube_uf'][::-1], top_clubs['pagerank_score'][::-1], color='forestgreen')
    plt.xlabel('PageRank Score (Prestige Authority)')
    plt.title(f'Top {TOP_N} Brazilian Clubs by PageRank (Entity-Level Analysis)')
    plt.grid(axis='x', linestyle='--', alpha=0.6)
    
    plt.tight_layout()
    plt.savefig('football_pagerank_unique_ranking.png')
    plt.show()

    df_rank.to_csv('final_football_pagerank_unique.csv', index=False, sep=';', encoding='utf-8-sig')
    print("[SUCCESS] Refined ranking saved to 'final_football_pagerank_unique.csv'")
    print("="*60)

if __name__ == "__main__":
    main()