import pandas as pd
import numpy as np
import networkx as nx
from k_means_constrained import KMeansConstrained
import matplotlib.pyplot as plt
import json
import os

# --- CONFIGURATION ---
INPUT_GRAPH = 'data/03_final/graphs/teams_games.graphml'
REPORT_FILE = 'outputs/reports/balanced_kmeans_metrics.json'
OUTPUT_FILE = 'data/04_results/balanced_kmeans_prop_division_3.csv'
OUTPUT_PLOT = 'outputs/plots/balanced_kmeans_division_serie_C.png'
K_VALUES = [2, 3, 4]
TOP_N_ELITE = 40

def main():
    print("="*60)
    print("BALANCED K-MEANS: SERIE C (MACRO REGIONAL OTIMIZADA)")
    print("="*60)

    # 1. LOAD DATA
    G = nx.read_graphml(INPUT_GRAPH)
    pr_scores = nx.pagerank(G, weight='weight')
    
    nodes = []
    for node_id, attrs in G.nodes(data=True):
        nodes.append({
            'clube_id': node_id,
            'lat': float(attrs.get('lat', 0)),
            'lon': float(attrs.get('lon', 0)),
            'score': pr_scores.get(node_id, 0)
        })
    
    df = pd.DataFrame(nodes).sort_values(by='score', ascending=False)
    regional = df.iloc[TOP_N_ELITE:].copy()
    X = regional[['lat', 'lon']].values
    n_samples = len(regional)

    # 2. CLUSTERING WITH CONSTRAINTS
    metrics = {}
    fig, axes = plt.subplots(1, 3, figsize=(18, 6))

    for i, k in enumerate(K_VALUES):
        # Definimos o equilíbrio: n/k com margem de 10%
        size_min = int((n_samples / k) * 0.8)
        size_max = int((n_samples / k) * 1.2)
        
        print(f"[PROCESS] Clustering K={k} | Target size: {size_min}-{size_max} clubs")

        model = KMeansConstrained(
            n_clusters=k,
            size_min=size_min,
            size_max=size_max,
            random_state=42
        )
        
        regional[f'cluster_k{k}'] = model.fit_predict(X)
        
        counts = regional[f'cluster_k{k}'].value_counts()
        metrics[f'k{k}'] = {
            "sizes": counts.to_dict(),
            "imbalance": float(counts.max() / counts.min())
        }

        # Visualização
        ax = axes[i]
        scatter = ax.scatter(regional['lon'], regional['lat'], c=regional[f'cluster_k{k}'], cmap='tab10', s=15, alpha=0.6)
        ax.set_title(f"Balanced K={k}\nImbalance: {metrics[f'k{k}']['imbalance']:.2f}")

    # 3. EXPORT
    plt.tight_layout()
    plt.savefig(OUTPUT_PLOT)
    regional.to_csv(OUTPUT_FILE, index=False, sep=';')
    
    with open(REPORT_FILE, 'w') as f:
        json.dump(metrics, f, indent=4)

    print(f"[SUCCESS] Série C Balanceada gerada.")

if __name__ == "__main__":
    main()