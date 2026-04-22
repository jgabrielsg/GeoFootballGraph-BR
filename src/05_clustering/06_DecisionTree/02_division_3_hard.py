import pandas as pd
import numpy as np
import networkx as nx
import matplotlib.pyplot as plt
import os
import time

# --- CONFIGURATION ---
INPUT_GRAPH = 'data/03_final/graphs/teams_games.graphml'
OUTPUT_FILE = 'data/04_results/brute_force_k3_optimal.csv'
OUTPUT_PLOT = 'outputs/plots/brute_force_k3_map.png'
TOP_N_ELITE = 40

def calculate_sse(coords):
    if len(coords) == 0: return 0
    return np.sum((coords - np.mean(coords, axis=0))**2)

def main():
    print("="*70)
    print("GLOBAL OPTIMIZATION: EXHAUSTIVE 2D PARTITION (K=3)")
    print("="*70)

    # 1. LOAD DATA
    G = nx.read_graphml(INPUT_GRAPH)
    pr_scores = nx.pagerank(G, weight='weight')
    
    nodes_data = []
    for n, d in G.nodes(data=True):
        nodes_data.append({
            'clube_id': n,
            'clube': n.split('/')[0].title(),
            'lat': float(d['lat']),
            'lon': float(d['lon']),
            'score': pr_scores.get(n, 0)
        })
    
    df_master = pd.DataFrame(nodes_data).sort_values(by='score', ascending=False)
    regional = df_master.iloc[TOP_N_ELITE:].copy()
    X = regional[['lat', 'lon']].values
    
    unique_lats = np.sort(regional['lat'].unique())
    unique_lons = np.sort(regional['lon'].unique())
    
    best_sse = float('inf')
    best_params = None

    start_time = time.time()
    
    # 2. BRUTE FORCE SEARCH (SAME LOGIC)
    axes = [0, 1] 
    for axis1 in axes:
        vals1 = unique_lats if axis1 == 0 else unique_lons
        for v1 in vals1:
            mask_a = X[:, axis1] >= v1
            mask_b = ~mask_a
            X_a, X_b = X[mask_a], X[mask_b]
            if len(X_a) < 10 or len(X_b) < 10: continue

            for part_to_split in ['A', 'B']:
                target_part = X_a if part_to_split == 'A' else X_b
                other_part = X_b if part_to_split == 'A' else X_a
                sse_fixed = calculate_sse(other_part)

                for axis2 in axes:
                    vals2 = unique_lats if axis2 == 0 else unique_lons
                    for v2 in vals2:
                        mask_sub1 = target_part[:, axis2] >= v2
                        mask_sub2 = ~mask_sub1
                        X_sub1, X_sub2 = target_part[mask_sub1], target_part[mask_sub2]
                        
                        if len(X_sub1) < 10 or len(X_sub2) < 10: continue
                        
                        total_sse = sse_fixed + calculate_sse(X_sub1) + calculate_sse(X_sub2)
                        
                        if total_sse < best_sse:
                            best_sse = total_sse
                            best_params = {
                                'axis1': axis1, 'v1': v1,
                                'part_split': part_to_split,
                                'axis2': axis2, 'v2': v2
                            }

    # 3. ASSIGNMENT & CHARACTERIZATION
    a1, v1 = best_params['axis1'], best_params['v1']
    a2, v2 = best_params['axis2'], best_params['v2']
    
    def assign_cluster(row):
        val1 = row['lat'] if a1 == 0 else row['lon']
        if best_params['part_split'] == 'A':
            if val1 < v1: return 0
            val2 = row['lat'] if a2 == 0 else row['lon']
            return 1 if val2 >= v2 else 2
        else:
            if val1 >= v1: return 0
            val2 = row['lat'] if a2 == 0 else row['lon']
            return 1 if val2 >= v2 else 2

    regional['cluster'] = regional.apply(assign_cluster, axis=1)

    # 4. FINAL DETAILED REPORT
    print(f"\n[SUMMARY] SSE Mínima Global: {best_sse:.2f}")
    print(f"[SUMMARY] Tempo de Processamento: {time.time() - start_time:.2f}s")
    print("-" * 70)
    
    stats = []
    for c_id in sorted(regional['cluster'].unique()):
        subset = regional[regional['cluster'] == c_id]
        top_teams = subset.sort_values(by='score', ascending=False).head(3)['clube'].tolist()
        
        c_info = {
            'Cluster': c_id,
            'Qtd Times': len(subset),
            'Lat Média': subset['lat'].mean(),
            'Lon Média': subset['lon'].mean(),
            'Prestigio Médio': subset['score'].mean() * 1000, # Escalado para leitura
            'Polos Regionais': ", ".join(top_teams)
        }
        stats.append(c_info)

    df_stats = pd.DataFrame(stats)
    print(df_stats.to_string(index=False))
    
    imb = df_stats['Qtd Times'].max() / df_stats['Qtd Times'].min()
    print("-" * 70)
    print(f"RAZÃO DE DESEQUILÍBRIO (IMBALANCE): {imb:.2f}")
    print(f"Corte 1: {'Lat' if a1==0 else 'Lon'} em {v1:.3f}")
    print(f"Corte 2: {'Lat' if a2==0 else 'Lon'} em {v2:.3f} na parte {best_params['part_split']}")
    print("-" * 70)

    # 5. VISUALIZAÇÃO
    plt.figure(figsize=(10, 12))
    scatter = plt.scatter(regional['lon'], regional['lat'], c=regional['cluster'], cmap='viridis', s=25, alpha=0.7)
    plt.colorbar(scatter, label='Cluster ID')
    plt.grid(True, linestyle=':', alpha=0.4)
    plt.title("Otimização Global Exaustiva: 3 Quadrantes Ótimos")
    plt.savefig(OUTPUT_PLOT)
    regional.to_csv(OUTPUT_FILE, index=False, sep=';', encoding='utf-8-sig')

if __name__ == "__main__":
    main()