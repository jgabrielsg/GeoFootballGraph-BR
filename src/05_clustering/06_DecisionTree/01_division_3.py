import pandas as pd
import numpy as np
import networkx as nx
from sklearn.tree import DecisionTreeRegressor
import matplotlib.pyplot as plt
import json
import os

# --- CONFIGURATION ---
INPUT_GRAPH = 'data/03_final/graphs/teams_games.graphml'
REPORT_FILE = 'outputs/reports/decision_tree_metrics.json'
OUTPUT_FILE = 'data/04_results/decision_tree_prop_division_3.csv'
OUTPUT_PLOT = 'outputs/plots/decision_tree_division_serie_C.png'
K_VALUES = [2, 3, 4]
TOP_N_ELITE = 40

def main():
    print("="*60)
    print("2D DECISION TREE CLUSTERING: SERIE C")
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
    
    # X e y são iguais: [Lat, Lon]
    # O modelo minimizará a soma das variâncias em ambas as dimensões
    coords = regional[['lat', 'lon']].values

    # 2. RUN MULTI-OUTPUT DECISION TREE
    metrics = {}
    fig, axes = plt.subplots(1, 3, figsize=(20, 7))

    for i, k in enumerate(K_VALUES):
        # max_leaf_nodes garante o número exato de clusters (folhas)
        model = DecisionTreeRegressor(max_leaf_nodes=k, random_state=42)
        model.fit(coords, coords)
        
        # Atribuição de clusters baseada nas folhas da árvore
        node_indicator = model.apply(coords)
        unique_nodes = np.unique(node_indicator)
        mapping = {node: idx for idx, node in enumerate(unique_nodes)}
        regional[f'cluster_k{k}'] = [mapping[n] for n in node_indicator]

        # Extração da estrutura da árvore para o relatório
        tree = model.tree_
        splits = []
        for n in range(tree.node_count):
            if tree.children_left[n] != -1: # Se não for folha
                splits.append({
                    "axis": "Latitude" if tree.feature[n] == 0 else "Longitude",
                    "threshold": float(tree.threshold[n])
                })

        metrics[f'k{k}'] = {
            "sizes": regional[f'cluster_k{k}'].value_counts().to_dict(),
            "splits": splits,
            "imbalance": float(regional[f'cluster_k{k}'].value_counts().max() / regional[f'cluster_k{k}'].value_counts().min())
        }

        # 3. VISUALIZAÇÃO
        ax = axes[i]
        scatter = ax.scatter(regional['lon'], regional['lat'], 
                            c=regional[f'cluster_k{k}'], cmap='Set1', s=20, alpha=0.6)
        
        # Desenhar os cortes recursivos
        # Nota: Cortes em árvores são locais, mas para K pequeno, podemos visualizar as linhas principais
        for s in splits:
            if s["axis"] == "Latitude":
                ax.axhline(y=s["threshold"], color='black', linestyle='--', alpha=0.3)
            else:
                ax.axvline(x=s["threshold"], color='black', linestyle=':', alpha=0.3)

        ax.set_title(f"K={k} Clusters (2D Tree)\nImbalance: {metrics[f'k{k}']['imbalance']:.2f}")
        ax.set_xlabel("Longitude")
        ax.set_ylabel("Latitude")

    # 4. SAVE
    plt.tight_layout()
    plt.savefig(OUTPUT_PLOT, dpi=150)
    regional.to_csv(OUTPUT_FILE, index=False, sep=';')
    
    with open(REPORT_FILE, 'w') as f:
        json.dump(metrics, f, indent=4)

    print(f"[SUCCESS] Árvore 2D gerada. Veja os cortes em: {OUTPUT_PLOT}")

if __name__ == "__main__":
    os.makedirs('outputs/reports', exist_ok=True)
    os.makedirs('outputs/plots', exist_ok=True)
    main()