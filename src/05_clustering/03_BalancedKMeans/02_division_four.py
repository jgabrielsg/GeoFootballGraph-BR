import pandas as pd
import numpy as np
from k_means_constrained import KMeansConstrained
import matplotlib.pyplot as plt
import os

# --- CONFIGURATION ---
INPUT_FILE = 'data/04_results/balanced_kmeans_prop_division_3.csv'
OUTPUT_FILE = 'data/04_results/balanced_kmeans_prop_division_4.csv'
OUTPUT_GRID = 'outputs/plots/balanced_kmeans_subclusters_3x3.png'
MACRO_COL = 'cluster_k4' # Usamos K=4 como base
SUB_K_VALUES = [2, 3, 4]
COLORS = ['#e6194b', '#3cb44b', '#ffe119', '#4363d8', '#f58231', '#911eb4']

def main():
    print("="*60)
    print("BALANCED HIERARCHICAL: SERIE D (3x3 GRID)")
    print("="*60)

    df = pd.read_csv(INPUT_FILE, sep=';')
    macro_ids = sorted(df[MACRO_COL].unique())
    
    fig, axes = plt.subplots(len(macro_ids), len(SUB_K_VALUES), figsize=(18, 15))
    final_dfs = []

    for row_idx, m_id in enumerate(macro_ids):
        df_region = df[df[MACRO_COL] == m_id].copy()
        X = df_region[['lat', 'lon']].values
        n_sub = len(df_region)
        
        print(f"[PROCESS] Subdividindo Macro {m_id} | {n_sub} times")

        for col_idx, k_sub in enumerate(SUB_K_VALUES):
            # Restrições locais para a Série D
            s_min = int((n_sub / k_sub) * 0.8)
            s_max = int((n_sub / k_sub) * 1.2)
            
            model = KMeansConstrained(n_clusters=k_sub, size_min=s_min, size_max=s_max, random_state=42)
            labels = model.fit_predict(X)
            df_region[f'serie_d_k{k_sub}'] = labels
            
            # Plot
            ax = axes[row_idx, col_idx]
            for s_id in range(k_sub):
                mask = labels == s_id
                ax.scatter(X[mask, 1], X[mask, 0], s=20, c=COLORS[s_id % len(COLORS)], alpha=0.7)
            
            if row_idx == 0: ax.set_title(f"Sub-divisão K={k_sub}")
            if col_idx == 0: ax.set_ylabel(f"Macro {m_id}")
            ax.set_xticks([]); ax.set_yticks([]); ax.grid(True, alpha=0.3)

        final_dfs.append(df_region)

    plt.tight_layout()
    plt.savefig(OUTPUT_GRID, dpi=200)
    pd.concat(final_dfs).to_csv(OUTPUT_FILE, index=False, sep=';')
    print(f"[SUCCESS] Grid 3x3 Balanceado exportado.")

if __name__ == "__main__":
    main()