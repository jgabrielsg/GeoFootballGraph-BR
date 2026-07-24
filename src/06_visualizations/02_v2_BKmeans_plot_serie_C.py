import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os

CLUSTER_FILE = 'data/04_results/Bkmeans_prop_division_3.csv'
OUTPUT_MAP = 'outputs/maps/03_BalancedKMeans/serie_c_geography_v2.png'
OUTPUT_TABLES = 'outputs/plots/BalancedKmeansTables/serie_c_league_tables_v2.png'
OUTPUT_CSV = 'data/04_results/serie_c_final_proposal_v2.csv'

UF_MAP = {
    'acre': 'AC', 'alagoas': 'AL', 'amapa': 'AP', 'amazonas': 'AM', 'bahia': 'BA',
    'ceara': 'CE', 'distrito_federal': 'DF', 'espirito_santo': 'ES', 'goias': 'GO',
    'maranhao': 'MA', 'mato_grosso': 'MT', 'mato_grosso_do_sul': 'MS', 'minas_gerais': 'MG',
    'para': 'PA', 'paraiba': 'PB', 'parana': 'PR', 'pernambuco': 'PE', 'piaui': 'PI',
    'rio_de_janeiro': 'RJ', 'rio_grande_do_norte': 'RN', 'rio_grande_do_sul': 'RS',
    'rondonia': 'RO', 'roraima': 'RR', 'santa_catarina': 'SC', 'sao_paulo': 'SP',
    'sergipe': 'SE', 'tocantins': 'TO'
}

def get_color(rank, is_north_league=False):
    if is_north_league:
        if rank <= 2: return '#00008B'
        if 3 <= rank <= 6: return '#ADD8E6' 
        if rank >= 21: return '#FF0000'
    else:
        if rank <= 2: return '#00008B'
        if 3 <= rank <= 6: return '#ADD8E6'
        if rank >= 17: return '#FF0000'
    return 'white'

def main():
    print("="*60)
    print("SERIE C STRUCTURE: HYBRID MODEL (20/24 TEAMS)")
    print("="*60)

    os.makedirs(os.path.dirname(OUTPUT_MAP), exist_ok=True)
    os.makedirs(os.path.dirname(OUTPUT_TABLES), exist_ok=True)
    os.makedirs(os.path.dirname(OUTPUT_CSV), exist_ok=True)

    df = pd.read_csv(CLUSTER_FILE, sep=';', encoding='utf-8-sig')
    
    df['clube'] = df['clube_id'].apply(lambda x: x.split('/')[0].title())
    df['uf_slug'] = df['clube_id'].apply(lambda x: x.split('/')[1])
    df['uf'] = df['uf_slug'].map(UF_MAP).fillna(df['uf_slug'])

    clusters = sorted(df['cluster_k4'].unique())
    
    cluster_lats = df.groupby('cluster_k4')['lat'].mean()
    north_cluster_id = cluster_lats.idxmax()
    print(f"[INFO] Northern League identified as Cluster {north_cluster_id}")

    serie_c_list = []

    for c_id in clusters:
        limit = 24 if c_id == north_cluster_id else 20
        cluster_data = df[df['cluster_k4'] == c_id].sort_values(by='score', ascending=False).head(limit).copy()
        cluster_data['pos'] = range(1, limit + 1)
        cluster_data['is_north'] = (c_id == north_cluster_id)
        serie_c_list.append(cluster_data)

    serie_c_final = pd.concat(serie_c_list)

    fig_tabs, axes = plt.subplots(2, 2, figsize=(20, 26))
    axes = axes.flatten()

    for i, c_id in enumerate(clusters):
        ax = axes[i]
        ax.axis('off')
        data = serie_c_final[serie_c_final['cluster_k4'] == c_id]
        is_north = (c_id == north_cluster_id)
        
        table_data = data[['pos', 'clube', 'uf']].values
        table = ax.table(cellText=table_data, colLabels=['Pos', 'Clube', 'UF'], 
                         loc='center', cellLoc='center', colWidths=[0.1, 0.7, 0.2])
        
        table.auto_set_font_size(False)
        table.set_fontsize(11)
        table.scale(1.2, 2.2)

        for row_idx in range(1, len(data) + 1):
            color = get_color(row_idx, is_north)
            if color != 'white':
                for col_idx in range(3):
                    table[(row_idx, col_idx)].set_facecolor(color)
                    if color in ['#00008B', '#FF0000']:
                        table[(row_idx, col_idx)].get_text().set_color('white')

        title_suffix = "(24 Teams - Hybrid)" if is_north else "(20 Teams)"
        ax.set_title(f"REGIONAL LEAGUE - CLUSTER {c_id} {title_suffix}", fontsize=16, fontweight='bold', pad=20)

    plt.tight_layout()
    plt.savefig(OUTPUT_TABLES, dpi=150)
    print(f"[SUCCESS] Tables saved to {OUTPUT_TABLES}")

    plt.figure(figsize=(10, 12))
    scatter = plt.scatter(serie_c_final['lon'], serie_c_final['lat'], 
                          c=serie_c_final['cluster_k4'], cmap='tab10', s=60, edgecolors='black')
    
    plt.title("GEOGRAPHIC MAP: NEW SERIE C (84 TEAMS)")
    plt.grid(True, linestyle=':', alpha=0.5)
    plt.savefig(OUTPUT_MAP)
    print(f"[SUCCESS] Map saved to {OUTPUT_MAP}")

    serie_c_final.drop(columns=['is_north']).to_csv(OUTPUT_CSV, index=False, sep=';')
    print(f"[SUCCESS] CSV exported to {OUTPUT_CSV}")

if __name__ == "__main__":
    main()