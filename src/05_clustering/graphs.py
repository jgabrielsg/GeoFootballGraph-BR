import pandas as pd
import numpy as np
import networkx as nx
from sklearn.neighbors import BallTree
import community.community_louvain as community_louvain
import matplotlib.pyplot as plt

# --- CONFIGURATION ---
INPUT_FILE = 'active_clubs_geodata.csv'
K_NEIGHBORS = 50  # Cada clube se conecta aos 50 mais próximos
EARTH_RADIUS = 6371  # Raio da Terra em km

def main():
    print("="*60)
    print("ANÁLISE DE CLUSTERIZAÇÃO LOGÍSTICA (KNN + LOUVAIN)")
    print("="*60)

    # 1. CARREGAR DADOS
    df = pd.read_csv(INPUT_FILE, sep=';', encoding='utf-8-sig')
    
    # Preparamos as coordenadas em Radianos para o BallTree (mais rápido que Haversine puro)
    coords = np.deg2rad(df[['lat', 'lon']].values)

    # 2. CONSTRUIR ÁRVORE ESPACIAL (BallTree)
    # O BallTree permite buscas KNN extremamente rápidas em esferas
    tree = BallTree(coords, metric='haversine')

    # 3. BUSCAR OS K VIZINHOS MAIS PRÓXIMOS
    # Retorna distâncias (em radianos) e índices dos vizinhos
    dist, ind = tree.query(coords, k=K_NEIGHBORS + 1) # +1 porque o primeiro é o próprio clube

    # 4. CONSTRUIR O GRAFO DE PROXIMIDADE
    G = nx.Graph()
    
    print(f"[PROCESS] Gerando arestas para {len(df)} clubes...")
    for i, neighbors in enumerate(ind):
        clube_origem = f"{df.iloc[i]['clube']}/{df.iloc[i]['estado']}"
        
        for j, neighbor_idx in enumerate(neighbors):
            if i == neighbor_idx: continue # Pula a conexão consigo mesmo
            
            clube_destino = f"{df.iloc[neighbor_idx]['clube']}/{df.iloc[neighbor_idx]['estado']}"
            
            # Converter distância de radianos para KM
            dist_km = dist[i][j] * EARTH_RADIUS
            
            # Cálculo do Peso: Inversamente proporcional à distância
            # Adicionamos 10km de "offset" para evitar divisões por zero e 
            # representar o custo fixo de saída de qualquer delegação.
            weight = 1 / (dist_km + 10)
            
            G.add_edge(clube_origem, clube_destino, weight=weight, distance=dist_km)

    # 5. DETECÇÃO DE COMUNIDADES (LOUVAIN)
    print("[ALGO] Calculando comunidades via Método de Louvain...")
    partition = community_louvain.best_partition(G, weight='weight')

    # 6. INTEGRAR RESULTADOS AO DATAFRAME
    df['cluster_logistico'] = df.apply(lambda x: partition.get(f"{x['clube']}/{x['estado']}"), axis=1)

    # 7. VISUALIZAÇÃO BÁSICA (MAPA DE CALOR DE CLUSTERS)
    plt.figure(figsize=(10, 12))
    scatter = plt.scatter(df['lon'], df['lat'], c=df['cluster_logistico'], cmap='tab20', s=30, alpha=0.7)
    plt.colorbar(scatter, label='ID do Cluster Logístico')
    plt.title('Clusters Logísticos Ótimos (Louvain + Distância Real)')
    plt.xlabel('Longitude')
    plt.ylabel('Latitude')
    plt.grid(True, linestyle='--', alpha=0.5)
    
    plt.savefig('clusters_logisticos_brasil.png')
    print("[SUCCESS] Mapa de clusters gerado: clusters_logisticos_brasil.png")

    # 8. EXPORTAR RESULTADOS
    df.to_csv('clubs_with_logistic_clusters.csv', index=False, sep=';', encoding='utf-8-sig')
    
    # Relatório de Consistência
    n_clusters = df['cluster_logistico'].nunique()
    print(f"\n[REPORT] Total de comunidades detectadas: {n_clusters}")
    print(f"Média de clubes por cluster: {len(df)/n_clusters:.2f}")
    print("="*60)

if __name__ == "__main__":
    main()