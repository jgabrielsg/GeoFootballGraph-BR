import pandas as pd
import numpy as np
from sklearn.cluster import AgglomerativeClustering
import matplotlib.pyplot as plt
import math

# --- CONFIGURATION ---
INPUT_FILE = 'proposta_divisao_final.csv'
OUTPUT_FILE = 'proposta_divisao_hierarquica.csv'
SUB_K_VALUES = [2, 3, 4]  # Quantos sub-clusters testar para cada macro-região

# Cores para diferenciar as sub-divisões
COLORS = ['#e6194b', '#3cb44b', '#ffe119', '#4363d8', '#f58231', '#911eb4', '#46f0f0', '#f032e6']

def main():
    print("="*60)
    print("DIVISÃO HIERÁRQUICA: SUB-CLUSTERIZAÇÃO DAS MACRO-REGIÕES")
    print("="*60)

    # 1. CARGA DOS DADOS
    # Lemos o arquivo que já contém a coluna 'cluster_k3'
    df = pd.read_csv(INPUT_FILE, sep=';', encoding='utf-8-sig')
    
    # Identificamos os 3 macro-clusters originais
    macro_clusters = sorted(df['cluster_k3'].unique())
    
    # 2. PREPARAÇÃO DO PLOT
    # Teremos uma linha para cada Macro-Cluster (3) e uma coluna para cada Sub-K (3)
    fig, axes = plt.subplots(len(macro_clusters), len(SUB_K_VALUES), 
                             figsize=(5 * len(SUB_K_VALUES), 5 * len(macro_clusters)))

    # 3. PROCESSAMENTO RECURSIVO
    for row, m_id in enumerate(macro_clusters):
        print(f"\n--- Analisando Macro-Região {m_id} ---")
        
        # Filtramos apenas os clubes que pertencem a este macro-cluster
        df_sub = df[df['cluster_k3'] == m_id].copy()
        X = df_sub[['lat', 'lon']].values
        
        if len(df_sub) < max(SUB_K_VALUES):
            print(f"  ! Macro-região {m_id} tem poucos times para sub-dividir.")
            continue

        for col, k_sub in enumerate(SUB_K_VALUES):
            # Aplicamos Ward novamente, mas apenas no subconjunto
            model = AgglomerativeClustering(n_clusters=k_sub, linkage='ward')
            sub_labels = model.fit_predict(X)
            
            # Guardamos no DataFrame original usando o índice para não perder a referência
            col_name = f'sub_cluster_m{m_id}_k{k_sub}'
            df.loc[df['cluster_k3'] == m_id, col_name] = sub_labels

            # Plotagem
            ax = axes[row, col]
            for s_id in range(k_sub):
                mask = sub_labels == s_id
                ax.scatter(X[mask, 1], X[mask, 0], s=20, label=f'Sub {s_id}', alpha=0.7)
            
            ax.set_title(f'Macro {m_id} | Sub-K={k_sub}')
            ax.grid(True, linestyle=':', alpha=0.5)
            if row == 0: ax.set_xlabel(f'Sub-divisão em {k_sub}')
            if col == 0: ax.set_ylabel(f'Macro-Região {m_id}')

    # 4. SALVAMENTO E FINALIZAÇÃO
    plt.tight_layout()
    plt.savefig('analise_sub_clusters_hierarquicos.png', dpi=150)
    
    # Exportamos o CSV final com todas as novas colunas de sub-divisão
    df.to_csv(OUTPUT_FILE, index=False, sep=';', encoding='utf-8-sig')
    
    print("\n" + "="*60)
    print(f"ARQUIVO HIERÁRQUICO GERADO: {OUTPUT_FILE}")
    print(f"VISUALIZAÇÃO DAS SUB-DIVISÕES: analise_sub_clusters_hierarquicos.png")
    print("="*60)

if __name__ == "__main__":
    main()