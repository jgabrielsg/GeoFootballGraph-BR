import pandas as pd
import os

# --- CONFIGURATION ---
TARGET_CLUBS = [
    "AMAZONAS/amazonas",
    "ANÁPOLIS/goias",
    "BARRA/santa_catarina",
    "BOTAFOGO/paraiba",
    "BRUSQUE/santa_catarina",
    "CAXIAS/rio_grande_do_sul",
    "CONFIANÇA/sergipe",
    "FERROVIÁRIA/sao_paulo",
    "FIGUEIRENSE/santa_catarina",
    "FLORESTA/ceara",
    "GUARANI/sao_paulo",
    "INTER DE LIMEIRA/sao_paulo",
    "ITABAIANA/sergipe",
    "ITUANO/sao_paulo",
    "MARANHÃO/maranhao",
    "MARINGÁ/parana",
    "PAYSANDU/para",
    "SANTA CRUZ/pernambuco",
    "VOLTA REDONDA/rio_de_janeiro",
    "YPIRANGA/rio_grande_do_sul"
]

ALL_CLUSTERS_FILE = r'data\04_results\balanced_kmeans_prop_division_4.csv'
SERIE_D_FILE = r'data\04_results\serie_d_final_proposal.csv'
SERIE_C_TOP_PER_CLUSTER = 20

def main():
    print("="*70)
    print("CROSS-CHECKING 2026 SERIE C CLUBS IN OUR MODEL")
    print("="*70)

    if not os.path.exists(ALL_CLUSTERS_FILE):
        print(f"[ERROR] File not found: {ALL_CLUSTERS_FILE}")
        return

    # Load master clustered data
    df_all = pd.read_csv(ALL_CLUSTERS_FILE, sep=';', encoding='utf-8-sig')
    
    # Check if Serie D file exists to map specific Serie D leagues
    df_d = pd.DataFrame()
    if os.path.exists(SERIE_D_FILE):
        df_d = pd.read_csv(SERIE_D_FILE, sep=';', encoding='utf-8-sig')

    # Recreate the Serie C logic (Top 20 per k=4 cluster) to know who made it
    df_all = df_all.sort_values(by='score', ascending=False)
    
    serie_c_ids = set()
    for c_id in range(4):
        mask = df_all['cluster_k4'] == c_id
        cluster_top = df_all[mask].head(SERIE_C_TOP_PER_CLUSTER)['clube_id'].tolist()
        serie_c_ids.update(cluster_top)

    results = []
    
    for target in TARGET_CLUBS:
        # Find team in the master dataset
        team_data = df_all[df_all['clube_id'] == target]
        
        if team_data.empty:
            results.append(f"❌ {target.ljust(30)} -> NOT FOUND IN GRAPH")
            continue
            
        row = team_data.iloc[0]
        macro_cluster = row.get('cluster_k4', 'N/A')
        
        if target in serie_c_ids:
            results.append(f"🟢 {target.ljust(30)} -> SÉRIE C (Macro-Region {macro_cluster})")
        else:
            # Look up in Serie D file to find exact sub-league if possible
            sub_league = "Unknown"
            if not df_d.empty and 'clube_id' in df_d.columns:
                d_row = df_d[df_d['clube_id'] == target]
                if not d_row.empty:
                    # Depending on how the Serie D file was saved, extract the sub_key
                    sub_league = d_row.iloc[0].get('serie_d_k3', d_row.iloc[0].get('serie_d_k4', 'N/A'))
            
            results.append(f"🔴 {target.ljust(30)} -> SÉRIE D (Macro {macro_cluster} | Sub-League {sub_league})")

    # Print nicely
    for res in sorted(results):
        print(res)
        
    print("="*70)
    
    # Summary stats
    c_count = sum(1 for r in results if "SÉRIE C" in r)
    d_count = sum(1 for r in results if "SÉRIE D" in r)
    miss_count = sum(1 for r in results if "NOT FOUND" in r)
    
    print(f"SUMMARY:")
    print(f" - Allocated to our Serie C: {c_count}/20")
    print(f" - Relegated to our Serie D: {d_count}/20")
    if miss_count > 0:
        print(f" - Missing from dataset: {miss_count}/20")
    print("="*70)

if __name__ == "__main__":
    main()