import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os

# --- CONFIGURATION ---
CLUSTER_FILE = 'data/04_results/balanced_kmeans_prop_division_3.csv'
OUTPUT_MAP = 'outputs/plots/maps/03_BalancedKMeans/serie_c_geography.png'
OUTPUT_TABLES = 'outputs/plots/BalancedKmeansTables/serie_c_league_tables.png'

UF_MAP = {
    'acre': 'AC', 'alagoas': 'AL', 'amapa': 'AP', 'amazonas': 'AM', 'bahia': 'BA',
    'ceara': 'CE', 'distrito_federal': 'DF', 'espirito_santo': 'ES', 'goias': 'GO',
    'maranhao': 'MA', 'mato_grosso': 'MT', 'mato_grosso_do_sul': 'MS', 'minas_gerais': 'MG',
    'para': 'PA', 'paraiba': 'PB', 'parana': 'PR', 'pernambuco': 'PE', 'piaui': 'PI',
    'rio_de_janeiro': 'RJ', 'rio_grande_do_norte': 'RN', 'rio_grande_do_sul': 'RS',
    'rondonia': 'RO', 'roraima': 'RR', 'santa_catarina': 'SC', 'sao_paulo': 'SP',
    'sergipe': 'SE', 'tocantins': 'TO'
}

def get_color(rank):
    """Aplica a regra de cores da liga baseada na posição."""
    if rank <= 2: return '#00008B'  # Azul Escuro (Subida Direta Playoff Final)
    if 3 <= rank <= 6: return '#ADD8E6'  # Azul Claro (Playoff Regional)
    if rank >= 16: return '#FF0000'  # Vermelho (Rebaixamento)
    return 'white'  # Estabilidade

def main():
    print("="*60)
    print("ESTRUTURAÇÃO SÉRIE C: TOP 18 POR CLUSTER")
    print("="*60)

    # 1. CARGA E MAPEAMENTO
    df = pd.read_csv(CLUSTER_FILE, sep=';', encoding='utf-8-sig')
    
    # Extrair Clube e UF do ID
    df['clube'] = df['clube_id'].apply(lambda x: x.split('/')[0].title())
    df['uf_slug'] = df['clube_id'].apply(lambda x: x.split('/')[1])
    df['uf'] = df['uf_slug'].map(UF_MAP).fillna(df['uf_slug'])

    # 2. SELEÇÃO DOS TOP 18 POR CLUSTER
    serie_c_list = []
    clusters = sorted(df['cluster_k4'].unique())

    for c_id in clusters:
        # Pega os 18 melhores de cada cluster baseado no score (PageRank)
        cluster_data = df[df['cluster_k4'] == c_id].sort_values(by='score', ascending=False).head(18).copy()
        cluster_data['pos'] = range(1, 19)
        serie_c_list.append(cluster_data)

    serie_c_final = pd.concat(serie_c_list)

    # 3. VISUALIZAÇÃO EM TABELAS (GRID 2x2)
    fig_tabs, axes = plt.subplots(2, 2, figsize=(20, 24))
    axes = axes.flatten()

    for i, c_id in enumerate(clusters):
        ax = axes[i]
        ax.axis('off')
        data = serie_c_final[serie_c_final['cluster_k4'] == c_id]
        
        # Criar a tabela
        table_data = data[['pos', 'clube', 'uf']].values
        table = ax.table(cellText=table_data, colLabels=['Pos', 'Clube', 'UF'], 
                         loc='center', cellLoc='center', colWidths=[0.1, 0.7, 0.2])
        
        # Aplicar estilização de cores
        table.auto_set_font_size(False)
        table.set_fontsize(12)
        table.scale(1.2, 2.5)

        for row_idx in range(1, 19): # Pula o header
            color = get_color(row_idx)
            if color != 'white':
                for col_idx in range(3):
                    table[(row_idx, col_idx)].set_facecolor(color)
                    if color == '#00008B' or color == '#FF0000': # Fonte branca para fundos escuros
                        table[(row_idx, col_idx)].get_text().set_color('white')

        ax.set_title(f"LIGA REGIONAL - CLUSTER {c_id}", fontsize=16, fontweight='bold', pad=20)

    plt.tight_layout()
    plt.savefig(OUTPUT_TABLES, dpi=150)
    print(f"[SUCCESS] Tabelas das Ligas geradas em {OUTPUT_TABLES}")

    # 4. PLOT DO MAPA GEOGRÁFICO
    plt.figure(figsize=(10, 12))
    scatter = plt.scatter(serie_c_final['lon'], serie_c_final['lat'], 
                          c=serie_c_final['cluster_k4'], cmap='tab10', s=60, edgecolors='black')
    
    plt.title("MAPA GEOGRÁFICO DA NOVA SÉRIE C (72 TIMES)")
    plt.grid(True, linestyle=':', alpha=0.5)
    plt.savefig(OUTPUT_MAP)
    print(f"[SUCCESS] Mapa Geográfico gerado em {OUTPUT_MAP}")

    # 5. EXPORT FINAL DATASET
    serie_c_final.to_csv('data/04_results/serie_c_final_proposal.csv', index=False, sep=';')

if __name__ == "__main__":
    main()