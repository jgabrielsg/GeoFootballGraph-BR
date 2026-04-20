import pandas as pd
import numpy as np
from sklearn.cluster import AgglomerativeClustering
import matplotlib.pyplot as plt
import json
import math

# --- CONFIGURATION ---
PAGERANK_FILE = 'final_football_pagerank.csv'
GEODATA_FILE = 'active_clubs_geodata.csv'
REPORT_FILE = 'relatorio_clusters_detalhado.json'
K_VALUES = [2, 3, 4, 5, 6, 7, 8]

# Cores de alto contraste (expandido)
HIGH_CONTRAST_COLORS = [
    '#e6194b', '#3cb44b', '#ffe119', '#4363d8',
    '#f58231', '#911eb4', '#46f0f0', '#f032e6'
]

def main():
    print("="*60)
    print("OTIMIZAÇÃO DE PIRÂMIDE: CLUSTERIZAÇÃO BALANCEADA (WARD)")
    print("="*60)

    # 1. CARGA E PADRONIZAÇÃO
    df_pr = pd.read_csv(PAGERANK_FILE, sep=';', encoding='utf-8-sig')
    df_geo = pd.read_csv(GEODATA_FILE, sep=';', encoding='utf-8-sig')

    for df, col_c, col_e in [(df_pr, 'clube', 'uf'), (df_geo, 'clube', 'estado')]:
        df[col_c] = df[col_c].astype(str).str.upper().str.strip()
        df[col_e] = df[col_e].astype(str).str.upper().str.strip()

    # 2. SELEÇÃO DA ELITE (TOP 40)
    df_master = pd.merge(df_geo, df_pr, left_on=['clube', 'estado'], right_on=['clube', 'uf']).drop(columns=['uf'])
    df_master = df_master.sort_values(by='pagerank_score', ascending=False)
    
    elite_40 = df_master.head(40).copy()
    regional_pool = df_master.iloc[40:].copy()

    print(f"[INFO] Elite Nacional: {len(elite_40)} times")
    print(f"[INFO] Pool Regional: {len(regional_pool)} times")

    # 3. CLUSTERIZAÇÃO E VALIDAÇÃO
    X = regional_pool[['lat', 'lon']].values
    results_summary = {}

    # GRID DINÂMICO
    n_plots = len(K_VALUES)
    n_cols = 3
    n_rows = math.ceil(n_plots / n_cols)

    fig, axes = plt.subplots(n_rows, n_cols, figsize=(6*n_cols, 6*n_rows))
    axes = axes.flatten()

    for i, k in enumerate(K_VALUES):
        print(f"\n--- TESTANDO K = {k} ---")
        
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

        for cluster_id, count in counts.items():
            print(f"  > Cluster {cluster_id}: {count} times ({(count/len(regional_pool)*100):.1f}%)")
        print(f"  > Desvio Padrão do Tamanho: {results_summary[f'k{k}']['std_dev']:.2f}")

        # Plot
        ax = axes[i]
        for cluster_id in range(k):
            c_data = regional_pool[regional_pool[f'cluster_k{k}'] == cluster_id]
            ax.scatter(
                c_data['lon'],
                c_data['lat'],
                c=HIGH_CONTRAST_COLORS[cluster_id % len(HIGH_CONTRAST_COLORS)],
                label=f'C{cluster_id} (n={len(c_data)})',
                s=30,
                alpha=0.7
            )

        ax.scatter(elite_40['lon'], elite_40['lat'], c='black', marker='x', s=60, label='Elite A/B')
        ax.set_title(f'K={k} (Ward)')
        ax.legend(loc='lower left', fontsize='x-small')
        ax.grid(True, linestyle=':', alpha=0.5)

    # Remove eixos vazios (caso grid > plots)
    for j in range(i+1, len(axes)):
        fig.delaxes(axes[j])

    plt.tight_layout()
    plt.savefig('comparativo_clusters_balanceados.png', dpi=150)

    # 4. EXPORTAÇÃO
    with open(REPORT_FILE, 'w', encoding='utf-8') as f:
        json.dump(results_summary, f, indent=4, ensure_ascii=False)

    regional_pool.to_csv('proposta_divisao_final.csv', index=False, sep=';', encoding='utf-8-sig')
    
    print("\n" + "="*60)
    print(f"RELATÓRIO FINAL GERADO: {REPORT_FILE}")
    print(f"MAPA DE CALOR: comparativo_clusters_balanceados.png")
    print("="*60)

if __name__ == "__main__":
    main()