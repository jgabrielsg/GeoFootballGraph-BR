import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os

# --- CONFIGURATION ---
INPUT_FILE = r'data\04_results\balanced_kmeans_prop_division_4.csv'
OUTPUT_CSV = r'data\04_results\serie_d_final_proposal.csv'
TOP_N_ELITE = 40
SERIE_C_TOP_PER_CLUSTER = 18

UF_MAP = {
    'acre': 'AC', 'alagoas': 'AL', 'amapa': 'AP', 'amazonas': 'AM', 'bahia': 'BA',
    'ceara': 'CE', 'distrito_federal': 'DF', 'espirito_santo': 'ES', 'goias': 'GO',
    'maranhao': 'MA', 'mato_grosso': 'MT', 'mato_grosso_do_sul': 'MS', 'minas_gerais': 'MG',
    'para': 'PA', 'paraiba': 'PB', 'parana': 'PR', 'pernambuco': 'PE', 'piaui': 'PI',
    'rio_de_janeiro': 'RJ', 'rio_grande_do_norte': 'RN', 'rio_grande_do_sul': 'RS',
    'rondonia': 'RO', 'roraima': 'RR', 'santa_catarina': 'SC', 'sao_paulo': 'SP',
    'sergipe': 'SE', 'tocantins': 'TO'
}

def get_serie_d_color(pos, is_north):
    """Aplica as regras específicas de cores para a Série D."""
    if is_north:
        if pos == 1: return '#00008B', 'white'        # Azul Escuro
        if 2 <= pos <= 5: return '#ADD8E6', 'black'   # Azul Claro
        if pos >= 13: return '#FF0000', 'white'       # Vermelho
    else:
        if 1 <= pos <= 2: return '#00008B', 'white'
        if 3 <= pos <= 6: return '#ADD8E6', 'black'
        if pos >= 16: return '#FF0000', 'white'
    return 'white', 'black'

def main():
    print("="*60)
    print("GERANDO SÉRIE D: FILTRAGEM HIERÁRQUICA E TABELAS")
    print("="*60)

    # 1. CARGA E FILTRAGEM INICIAL
    df_all = pd.read_csv(INPUT_FILE, sep=';', encoding='utf-8-sig')
    df_all['clube'] = df_all['clube_id'].apply(lambda x: x.split('/')[0].title())
    df_all['uf'] = df_all['clube_id'].apply(lambda x: UF_MAP.get(x.split('/')[1], x.split('/')[1].upper()))
    
    # Ordenar por score para identificar Elite e Série C
    df_all = df_all.sort_values(by='score', ascending=False)
    
    # Identificar quem já está na Elite (40)
    elite_ids = df_all.head(TOP_N_ELITE)['clube_id'].tolist()
    
    # Identificar quem já está na Série C (18 melhores por cluster_k4 excluindo elite)
    serie_c_ids = []
    for c_id in range(4):
        mask = (~df_all['clube_id'].isin(elite_ids)) & (df_all['cluster_k4'] == c_id)
        serie_c_ids.extend(df_all[mask].head(SERIE_C_TOP_PER_CLUSTER)['clube_id'].tolist())
    
    # O que sobra é o pool para a Série D
    df_d = df_all[~df_all['clube_id'].isin(elite_ids + serie_c_ids)].copy()
    
    # 2. DEFINIÇÃO DAS LIGAS E PLOTS
    all_d_leagues = []
    
    macro_regions = {
        0: {"name": "Norte", "sub_key": "serie_d_k4", "size": 14, "is_north": True},
        1: {"name": "Sul-Mato-Grosso", "sub_key": "serie_d_k3", "size": 18, "is_north": False},
        2: {"name": "Nordeste", "sub_key": "serie_d_k3", "size": 18, "is_north": False},
        3: {"name": "Centro-Sudeste", "sub_key": "serie_d_k3", "size": 18, "is_north": False}
    }

    for m_id, config in macro_regions.items():
        print(f"[PROCESS] Gerando {config['name']}...")
        df_macro = df_d[df_d['cluster_k4'] == m_id].copy()
        sub_clusters = sorted(df_macro[config['sub_key']].unique())
        
        # Setup do Plot (1 linha para as subdivisões da macro)
        n_subs = len(sub_clusters)
        fig, axes = plt.subplots(1, n_subs, figsize=(n_subs * 6, 12))
        if n_subs == 1: axes = [axes]
        
        for i, s_id in enumerate(sub_clusters):
            ax = axes[i]
            ax.axis('off')
            
            # Pega os N melhores daquela subdivisão
            league = df_macro[df_macro[config['sub_key']] == s_id].sort_values(by='score', ascending=False).head(config['size']).copy()
            league['pos'] = range(1, len(league) + 1)
            all_d_leagues.append(league)
            
            # Gerar Tabela
            table_data = league[['pos', 'clube', 'uf']].values
            table = ax.table(cellText=table_data, colLabels=['Pos', 'Clube', 'UF'], 
                             loc='center', cellLoc='center', colWidths=[0.12, 0.68, 0.2])
            
            table.auto_set_font_size(False)
            table.set_fontsize(10)
            table.scale(1.0, 1.8)

            # Estilização
            for row_idx in range(1, len(league) + 1):
                bg_color, text_color = get_serie_d_color(row_idx, config['is_north'])
                if bg_color != 'white':
                    for col_idx in range(3):
                        table[(row_idx, col_idx)].set_facecolor(bg_color)
                        table[(row_idx, col_idx)].get_text().set_color(text_color)
            
            ax.set_title(f"LIGA {s_id+1}\n({len(league)} times)", fontsize=14, fontweight='bold')

        plt.suptitle(f"SÉRIE D REGIONAL: {config['name'].upper()}", fontsize=20, fontweight='bold', y=0.95)
        plt.tight_layout(rect=[0, 0.03, 1, 0.90])
        plt.savefig(f'outputs/plots/BalancedKmeansTables/serie_d_macro_{m_id}.png', dpi=150)
        plt.close()

    # 3. CONSOLIDAR E EXPORTAR
    pd.concat(all_d_leagues).to_csv(OUTPUT_CSV, index=False, sep=';', encoding='utf-8-sig')
    print(f"\n[SUCCESS] Série D consolidada com {len(all_d_leagues)} ligas regionais.")
    print(f"[SUCCESS] Dataset salvo em {OUTPUT_CSV}")

if __name__ == "__main__":
    os.makedirs('outputs/plots', exist_ok=True)
    main()