import pandas as pd
import numpy as np
import networkx as nx
from sklearn.cluster import AgglomerativeClustering
import matplotlib.pyplot as plt
import json
import math
import os

# --- CONFIGURATION ---
INPUT_GRAPH = 'data/03_final/graphs/teams_games.graphml'
REPORT_FILE = 'outputs/reports/clustering_metrics.json'
OUTPUT_FILE = 'data/04_results/prop_division_3.csv'
OUTPUT_GRAPHIC = 'outputs/plots/division_serie_C.png'
K_VALUES = [2, 3, 4, 5]
TOP_N_ELITE = 40

HIGH_CONTRAST_COLORS = [
    '#e6194b', '#3cb44b', '#ffe119', '#4363d8',
    '#f58231', '#911eb4', '#46f0f0', '#f032e6'
]

def extract_dataframe_from_graph(G):
    """
    Converte os nós do grafo em um DataFrame e calcula o PageRank.
    """
    print(f"[PROCESS] Extraindo dados de {G.number_of_nodes()} nós...")
    
    # 1. Calcular PageRank para definir a Elite
    pr_scores = nx.pagerank(G, alpha=0.85, weight='weight')
    
    # 2. Extrair atributos dos nós (lat, lon, cidade)
    nodes_data = []
    for node_id, attrs in G.nodes(data=True):
        # O ID do nó é 'CLUBE/ESTADO_SLUG'
        clube, estado = node_id.split('/')
        
        nodes_data.append({
            'clube_id': node_id,
            'clube': clube.title(),
            'estado': estado,
            'lat': float(attrs.get('lat', 0)),
            'lon': float(attrs.get('lon', 0)),
            'cidade': attrs.get('cidade', 'Desconhecida'),
            'pagerank_score': pr_scores.get(node_id, 0)
        })
    
    df = pd.DataFrame(nodes_data)
    # Filtramos coordenadas zeradas (erros de geolocalização)
    return df[df['lat'] != 0].sort_values(by='pagerank_score', ascending=False).reset_index(drop=True)

def evaluate_clusters(regional_pool, X):
    """Executa a clusterização para os valores de K definidos."""
    results_summary = {}
    for k in K_VALUES:
        model = AgglomerativeClustering(n_clusters=k, linkage='ward')
        clusters = model.fit_predict(X)
        regional_pool[f'cluster_k{k}'] = clusters

        counts = regional_pool[f'cluster_k{k}'].value_counts().sort_index()
        results_summary[f'k{k}'] = {
            "counts": counts.to_dict(),
            "mean_size": float(counts.mean()),
            "std_dev": float(counts.std()),
            "imbalance_ratio": float(counts.max() / counts.min())
        }
        print(f"  > K={k}: Desvio Padrão de Tamanho = {results_summary[f'k{k}']['std_dev']:.2f}")

    return results_summary, regional_pool

def plot_clusters(elite, regional_pool):
    """Gera o grid de mapas para comparação visual."""
    n_plots = len(K_VALUES)
    n_cols = 3
    n_rows = math.ceil(n_plots / n_cols)

    fig, axes = plt.subplots(n_rows, n_cols, figsize=(6 * n_cols, 6 * n_rows))
    axes = axes.flatten()

    for i, k in enumerate(K_VALUES):
        ax = axes[i]
        for cluster_id in range(k):
            c_data = regional_pool[regional_pool[f'cluster_k{k}'] == cluster_id]
            ax.scatter(c_data['lon'], c_data['lat'], 
                       c=HIGH_CONTRAST_COLORS[cluster_id % len(HIGH_CONTRAST_COLORS)],
                       s=25, alpha=0.7, label=f'C{cluster_id}')

        ax.scatter(elite['lon'], elite['lat'], c='black', marker='x', s=50, label='Elite A/B')
        ax.set_title(f'Divisão Regional K={k}')
        ax.grid(True, linestyle=':', alpha=0.4)

    for j in range(i + 1, len(axes)): fig.delaxes(axes[j])
    
    plt.tight_layout()
    plt.savefig(OUTPUT_GRAPHIC, dpi=150)
    print(f"Gráfico salvo em {OUTPUT_GRAPHIC}")

def main():
    print("="*60)
    print("CLUSTERIZAÇÃO HIERÁRQUICA VIA GRAPHML")
    print("="*60)

    # 1. CARREGAR GRAFO
    if not os.path.exists(INPUT_GRAPH):
        print(f"Erro: Grafo não encontrado em {INPUT_GRAPH}")
        return

    G = nx.read_graphml(INPUT_GRAPH)
    
    # 2. TRANSFORMAR EM DATAFRAME TÉCNICO
    df_master = extract_dataframe_from_graph(G)

    # 3. SEPARAR ELITE NACIONAL (Baseado no PageRank calculado do grafo)
    elite = df_master.head(TOP_N_ELITE).copy()
    regional_pool = df_master.iloc[TOP_N_ELITE:].copy()

    print(f"[INFO] Elite (Série A/B): {len(elite)} times.")
    print(f"[INFO] Pool Regional: {len(regional_pool)} times.")

    # 4. CLUSTERIZAÇÃO
    X = regional_pool[['lat', 'lon']].values
    summary, regional_pool = evaluate_clusters(regional_pool, X)

    # 5. VISUALIZAÇÃO E EXPORTAÇÃO
    plot_clusters(elite, regional_pool)

    with open(REPORT_FILE, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=4, ensure_ascii=False)

    regional_pool.to_csv(OUTPUT_FILE, index=False, sep=';', encoding='utf-8-sig')

    print(f"[SUCCESS] Relatório salvo: {REPORT_FILE}")
    print(f"[SUCCESS] Dataset com clusters salvo: {OUTPUT_FILE}")
    print("="*60)

if __name__ == "__main__":
    main()