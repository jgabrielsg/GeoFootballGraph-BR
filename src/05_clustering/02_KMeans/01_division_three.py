import pandas as pd
import numpy as np
import networkx as nx
from sklearn.cluster import KMeans
import matplotlib.pyplot as plt
import json
import os

# --- CONFIGURATION ---
INPUT_GRAPH = 'data/03_final/graphs/teams_games.graphml'
REPORT_FILE = 'outputs/reports/kmeans_clustering_metrics.json'
OUTPUT_FILE = 'data/04_results/kmeans_prop_division_3.csv'
OUTPUT_GRAPHIC = 'outputs/plots/kmeans_division_serie_C.png' 
K_VALUES = [2, 3, 4]
TOP_N_ELITE = 40

def main():
    print("="*60)
    print("K-MEANS CLUSTERING: SERIE C (MACRO REGIONAL)")
    print("="*60)

    # 1. LOAD GRAPH AND EXTRACT DATA
    G = nx.read_graphml(INPUT_GRAPH)
    pr_scores = nx.pagerank(G, weight='weight')
    
    nodes_data = []
    for node_id, attrs in G.nodes(data=True):
        nodes_data.append({
            'clube_id': node_id,
            'lat': float(attrs.get('lat', 0)),
            'lon': float(attrs.get('lon', 0)),
            'score': pr_scores.get(node_id, 0)
        })
    
    df = pd.DataFrame(nodes_data).sort_values(by='score', ascending=False)
    
    # 2. SPLIT ELITE AND REGIONAL
    elite = df.head(TOP_N_ELITE)
    regional = df.iloc[TOP_N_ELITE:].copy()
    X = regional[['lat', 'lon']].values

    # 3. RUN K-MEANS FOR K=2, 3, 4
    metrics = {}
    fig, axes = plt.subplots(1, 3, figsize=(18, 6))

    for i, k in enumerate(K_VALUES):
        # n_init='auto' garante estabilidade no sklearn moderno
        model = KMeans(n_clusters=k, n_init='auto', random_state=42)
        regional[f'cluster_k{k}'] = model.fit_predict(X)
        
        # Coleta de métricas de desequilíbrio
        counts = regional[f'cluster_k{k}'].value_counts()
        metrics[f'k{k}'] = {
            "sizes": counts.to_dict(),
            "imbalance": float(counts.max() / counts.min()),
            "inertia": float(model.inertia_)
        }

        # Plot
        ax = axes[i]
        ax.scatter(regional['lon'], regional['lat'], c=regional[f'cluster_k{k}'], cmap='tab10', s=15)
        ax.scatter(elite['lon'], elite['lat'], c='black', marker='x', s=40)
        ax.set_title(f"Série C | K={k}")

    # 4. SAVE RESULTS
    plt.savefig(OUTPUT_GRAPHIC)
    regional.to_csv(OUTPUT_FILE, index=False, sep=';')
    
    with open(REPORT_FILE, 'w') as f:
        json.dump(metrics, f, indent=4)

    print(f"[SUCCESS] K-Means Série C completa. Arquivos gerados.")

if __name__ == "__main__":
    main()