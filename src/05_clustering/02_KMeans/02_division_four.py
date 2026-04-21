import pandas as pd
import numpy as np
from sklearn.cluster import KMeans
import matplotlib.pyplot as plt
import os

# --- CONFIGURATION ---
INPUT_FILE = 'data/04_results/kmeans_prop_division_3.csv'
OUTPUT_FILE = 'data/04_results/kmeans_prop_division_4.csv'
OUTPUT_GRAPHIC = 'outputs/plots/kmeans_subclusters_3x3.png'

# Usamos a divisão por 3 da Série C como os eixos das linhas (Rows)
MACRO_COL = 'cluster_k3'
SUB_K_VALUES = [2, 3, 4]  # Colunas (Cols) do grid
COLORS = ['#e6194b', '#3cb44b', '#ffe119', '#4363d8', '#f58231', '#911eb4']

def main():
    print("="*60)
    print("K-MEANS HIERARCHICAL: SERIE D (3x3 SUB-CLUSTERING)")
    print("="*60)

    # 1. LOAD DATA
    if not os.path.exists(INPUT_FILE):
        print(f"[ERROR] Input file {INPUT_FILE} not found. Run division_three first.")
        return

    df = pd.read_csv(INPUT_FILE, sep=';', encoding='utf-8-sig')
    
    # Identificar os macro-clusters da Série C (devem ser 3)
    macro_ids = sorted(df[MACRO_COL].unique())
    n_macros = len(macro_ids)
    
    # 2. SETUP PLOT (3 Rows x 3 Columns)
    fig, axes = plt.subplots(n_macros, len(SUB_K_VALUES), figsize=(18, 15))
    
    final_dfs = []

    # 3. RECURSIVE CLUSTERING
    for row_idx, m_id in enumerate(macro_ids):
        # Filtra apenas os clubes daquela macro-região
        df_region = df[df[MACRO_COL] == m_id].copy()
        X = df_region[['lat', 'lon']].values
        
        print(f"[PROCESS] Subdividindo Macro-Região {m_id} | {len(df_region)} times")

        for col_idx, k_sub in enumerate(SUB_K_VALUES):
            ax = axes[row_idx, col_idx]
            
            # Aplicar K-Means na sub-região
            model = KMeans(n_clusters=k_sub, n_init='auto', random_state=42)
            labels = model.fit_predict(X)
            
            # Salvar labels no dataframe (apenas para o K final desejado ou todos)
            df_region[f'serie_d_k{k_sub}'] = labels
            
            # Plotagem
            for s_id in range(k_sub):
                mask = labels == s_id
                ax.scatter(X[mask, 1], X[mask, 0], s=20, alpha=0.7, 
                           c=COLORS[s_id % len(COLORS)], label=f'Sub {s_id}')
            
            # Formatação do Subplot
            if row_idx == 0:
                ax.set_title(f"Sub-divisão: K={k_sub}", fontsize=14, fontweight='bold')
            if col_idx == 0:
                ax.set_ylabel(f"Macro-Região {m_id}", fontsize=12, fontweight='bold')
            
            ax.grid(True, linestyle=':', alpha=0.5)
            ax.set_xticks([])
            ax.set_yticks([])

        final_dfs.append(df_region)

    # 4. CONSOLIDATION AND EXPORT
    plt.tight_layout()
    plt.savefig(OUTPUT_GRAPHIC, dpi=200)
    
    # O CSV final conterá as colunas da Série C e as novas colunas da Série D
    df_final = pd.concat(final_dfs)
    df_final.to_csv(OUTPUT_FILE, index=False, sep=';', encoding='utf-8-sig')

    print(f"\n[SUCCESS] Grid 3x3 gerado: {OUTPUT_GRAPHIC}")
    print(f"[SUCCESS] Dataset final com Série D: {OUTPUT_FILE}")
    print("="*60)

if __name__ == "__main__":
    # Garantir que a pasta de plots existe
    os.makedirs(os.path.dirname(OUTPUT_GRAPHIC), exist_ok=True)
    main()