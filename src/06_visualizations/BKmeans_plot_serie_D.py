import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os

# --- CONFIGURATION ---
INPUT_FILE = r'data\04_results\balanced_kmeans_prop_division_4.csv'
OUTPUT_CSV = r'data\04_results\serie_d_final_proposal.csv'
SERIE_C_TOP_PER_CLUSTER = 20

# Pre-defined Elite Clubs (Serie A & B - 2026)
ELITE_CLUBS = [
    # Serie A
    ("ATLÉTICO MINEIRO", "minas_gerais"),
    ("ATHLETICO PARANAENSE", "parana"),
    ("BAHIA", "bahia"),
    ("BOTAFOGO", "rio_de_janeiro"),
    ("CHAPECOENSE", "santa_catarina"),
    ("CORINTHIANS", "sao_paulo"),
    ("CORITIBA", "parana"),
    ("CRUZEIRO", "minas_gerais"),
    ("FLAMENGO", "rio_de_janeiro"),
    ("FLUMINENSE", "rio_de_janeiro"),
    ("GRÊMIO", "rio_grande_do_sul"),
    ("INTERNACIONAL", "rio_grande_do_sul"),
    ("MIRASSOL", "sao_paulo"),
    ("PALMEIRAS", "sao_paulo"),
    ("RED BULL BRAGANTINO", "sao_paulo"),
    ("REMO", "para"),
    ("SANTOS", "sao_paulo"),
    ("SÃO PAULO", "sao_paulo"),
    ("VASCO DA GAMA", "rio_de_janeiro"),
    ("VITÓRIA", "bahia"),
    
    # Serie B
    ("AMÉRICA MINEIRO", "minas_gerais"),
    ("ATHLETIC", "minas_gerais"),
    ("ATLÉTICO GOIANIENSE", "goias"),
    ("AVAÍ", "santa_catarina"),
    ("BOTAFOGO", "sao_paulo"), 
    ("CEARÁ", "ceara"),
    ("CRB", "alagoas"),
    ("CRICIÚMA", "santa_catarina"),
    ("CUIABÁ", "mato_grosso"),
    ("FORTALEZA", "ceara"),
    ("GOIÁS", "goias"),
    ("GRÊMIO NOVORIZONTINO", "sao_paulo"),
    ("JUVENTUDE", "rio_grande_do_sul"),
    ("LONDRINA", "parana"),
    ("NÁUTICO", "pernambuco"),
    ("OPERÁRIO", "parana"),
    ("PONTE PRETA", "sao_paulo"),
    ("SÃO BERNARDO", "sao_paulo"),
    ("SPORT", "pernambuco"),
    ("VILA NOVA", "goias")
]

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
    """Applies specific coloring rules for Serie D tables."""
    if is_north:
        if pos == 1: return '#00008B', 'white'        # Dark Blue
        if 2 <= pos <= 5: return '#ADD8E6', 'black'   # Light Blue
        if pos >= 13: return '#FF0000', 'white'       # Red
    else:
        if 1 <= pos <= 2: return '#00008B', 'white'
        if 3 <= pos <= 6: return '#ADD8E6', 'black'
        if pos >= 16: return '#FF0000', 'white'
    return 'white', 'black'

def main():
    print("="*60)
    print("GENERATING SERIE D: HIERARCHICAL FILTERING AND TABLES")
    print("="*60)

    # 1. LOAD AND INITIAL FILTERING
    df_all = pd.read_csv(INPUT_FILE, sep=';', encoding='utf-8-sig')
    
    # Extract clean names and UF
    df_all['clube'] = df_all['clube_id'].apply(lambda x: str(x).split('/')[0].title())
    df_all['uf'] = df_all['clube_id'].apply(lambda x: UF_MAP.get(str(x).split('/')[1].lower(), str(x).split('/')[1].upper()))
    
    # Create normalized lookup key for Elite mapping (CLUB/state_slug)
    df_all['normalized_id'] = df_all['clube_id'].apply(
        lambda x: f"{str(x).split('/')[0].upper()}/{str(x).split('/')[1].lower()}"
    )

    # Sort by score to identify top clubs correctly
    df_all = df_all.sort_values(by='score', ascending=False)
    
    # 2. IDENTIFY ELITE (Serie A & B)
    elite_set = {f"{clube.upper()}/{estado.lower()}" for clube, estado in ELITE_CLUBS}
    elite_ids = df_all[df_all['normalized_id'].isin(elite_set)]['clube_id'].tolist()
    
    print(f"[INFO] Total Elite clubs identified: {len(elite_ids)}")

    # 3. IDENTIFY SERIE C (Top N per macro-region, excluding Elite)
    serie_c_ids = []
    # Assuming cluster_k4 has IDs 0, 1, 2, 3 representing the 4 macro-regions
    for c_id in range(4):
        mask = (~df_all['clube_id'].isin(elite_ids)) & (df_all['cluster_k4'] == c_id)
        cluster_serie_c = df_all[mask].head(SERIE_C_TOP_PER_CLUSTER)['clube_id'].tolist()
        serie_c_ids.extend(cluster_serie_c)
        
    print(f"[INFO] Total Serie C clubs allocated: {len(serie_c_ids)}")
    
    # 4. ISOLATE SERIE D POOL (Everything else)
    df_d = df_all[~df_all['clube_id'].isin(elite_ids + serie_c_ids)].copy()
    print(f"[INFO] Total Serie D clubs remaining: {len(df_d)}\n")
    
    # 5. DEFINE LEAGUES AND PLOTS
    all_d_leagues = []
    
    macro_regions = {
        0: {"name": "Norte", "sub_key": "serie_d_k4", "size": 14, "is_north": True},
        1: {"name": "Sul-Mato-Grosso", "sub_key": "serie_d_k3", "size": 18, "is_north": False},
        2: {"name": "Nordeste", "sub_key": "serie_d_k3", "size": 18, "is_north": False},
        3: {"name": "Centro-Sudeste", "sub_key": "serie_d_k3", "size": 18, "is_north": False}
    }

    os.makedirs('outputs/plots/BalancedKmeansTables', exist_ok=True)

    for m_id, config in macro_regions.items():
        print(f"[PROCESS] Generating {config['name']}...")
        df_macro = df_d[df_d['cluster_k4'] == m_id].copy()
        
        # Check if sub_key exists, fallback gracefully if not
        if config['sub_key'] not in df_macro.columns:
            print(f"[WARNING] Column {config['sub_key']} not found for {config['name']}. Skipping plot.")
            continue
            
        sub_clusters = sorted(df_macro[config['sub_key']].dropna().unique())
        
        n_subs = len(sub_clusters)
        if n_subs == 0:
            continue
            
        fig, axes = plt.subplots(1, n_subs, figsize=(n_subs * 6, 12))
        if n_subs == 1: axes = [axes]
        
        for i, s_id in enumerate(sub_clusters):
            ax = axes[i]
            ax.axis('off')
            
            # Extract top N clubs for the sub-league
            league = df_macro[df_macro[config['sub_key']] == s_id].sort_values(by='score', ascending=False).head(config['size']).copy()
            league['pos'] = range(1, len(league) + 1)
            all_d_leagues.append(league)
            
            # Generate Table
            table_data = league[['pos', 'clube', 'uf']].values
            table = ax.table(cellText=table_data, colLabels=['Pos', 'Clube', 'UF'], 
                             loc='center', cellLoc='center', colWidths=[0.12, 0.68, 0.2])
            
            table.auto_set_font_size(False)
            table.set_fontsize(10)
            table.scale(1.0, 1.8)

            # Styling
            for row_idx in range(1, len(league) + 1):
                bg_color, text_color = get_serie_d_color(row_idx, config['is_north'])
                if bg_color != 'white':
                    for col_idx in range(3):
                        table[(row_idx, col_idx)].set_facecolor(bg_color)
                        table[(row_idx, col_idx)].get_text().set_color(text_color)
            
            ax.set_title(f"LIGA {int(s_id)+1}\n({len(league)} times)", fontsize=14, fontweight='bold')

        plt.suptitle(f"SÉRIE D REGIONAL: {config['name'].upper()}", fontsize=20, fontweight='bold', y=0.95)
        plt.tight_layout(rect=[0, 0.03, 1, 0.90])
        plt.savefig(f'outputs/plots/BalancedKmeansTables/serie_d_macro_{m_id}.png', dpi=150)
        plt.close()

    # 6. CONSOLIDATE AND EXPORT
    if all_d_leagues:
        df_final = pd.concat(all_d_leagues)
        df_final.drop(columns=['normalized_id'], errors='ignore', inplace=True)
        os.makedirs(os.path.dirname(OUTPUT_CSV), exist_ok=True)
        df_final.to_csv(OUTPUT_CSV, index=False, sep=';', encoding='utf-8-sig')
        print(f"\n[SUCCESS] Serie D consolidated with {len(all_d_leagues)} regional leagues.")
        print(f"[SUCCESS] Dataset saved to {OUTPUT_CSV}")
    else:
        print("\n[WARNING] No Serie D leagues were generated. Check your sub_keys.")

if __name__ == "__main__":
    main()