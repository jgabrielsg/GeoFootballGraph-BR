import pandas as pd
import numpy as np
import networkx as nx
from k_means_constrained import KMeansConstrained
import matplotlib.pyplot as plt
import json
import os

# --- CONFIGURATION ---
INPUT_GRAPH = 'data/03_final/graphs/teams_games.graphml'
REPORT_FILE = 'outputs/reports/balanced_kmeans_metrics.json'
OUTPUT_FILE = 'data/04_results/balanced_kmeans_prop_division_3.csv'
OUTPUT_PLOT = 'outputs/maps/03_BalancedKMeans/Bkmeans_serie_C.png'
K_VALUES = [2, 3, 4]

# Pre-defined Elite Clubs (Serie A & B - 2026)
# Format: ("CLUB_NAME", "state_slug")
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

def main():
    print("="*60)
    print("BALANCED K-MEANS: SERIE C (EXCLUDING PREDEFINED ELITE)")
    print("="*60)

    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    os.makedirs(os.path.dirname(OUTPUT_PLOT), exist_ok=True)
    os.makedirs(os.path.dirname(REPORT_FILE), exist_ok=True)

    # 1. LOAD DATA & BUILD ELITE MAPPING
    G = nx.read_graphml(INPUT_GRAPH)
    pr_scores = nx.pagerank(G, weight='weight')
    
    # Create standardized lookup set -> "CLUB_NAME/state"
    elite_set = {f"{clube.upper()}/{estado.lower()}" for clube, estado in ELITE_CLUBS}
    found_elite = set()

    nodes = []
    for node_id, attrs in G.nodes(data=True):
        # Safely split node_id (expected format: "CLUB/state")
        try:
            clube_part, estado_part = str(node_id).split('/')
            normalized_id = f"{clube_part.upper()}/{estado_part.lower()}"
        except ValueError:
            normalized_id = str(node_id).upper()

        is_elite = normalized_id in elite_set
        if is_elite:
            found_elite.add(normalized_id)

        nodes.append({
            'clube_id': node_id,
            'normalized_id': normalized_id,
            'lat': float(attrs.get('lat', 0)),
            'lon': float(attrs.get('lon', 0)),
            'score': pr_scores.get(node_id, 0),
            'is_elite': is_elite
        })
    
    # 2. VALIDATE ELITE EXTRACTION
    missing_elite = elite_set - found_elite
    if missing_elite:
        print("\n[ERROR] The following predefined elite clubs were NOT found in the graph:")
        for missing in sorted(missing_elite):
            print(f" -> {missing}")
        print("Please check the exact spelling in ELITE_CLUBS or your graph data.\n")

    # 3. FILTER CLUBS FOR CLUSTERING
    df = pd.DataFrame(nodes).sort_values(by='score', ascending=False)
    regional = df[~df['is_elite']].copy()
    
    print(f"[INFO] Total clubs: {len(df)}")
    print(f"[INFO] Elite removed: {len(found_elite)}")
    print(f"[INFO] Clubs to cluster: {len(regional)}\n")

    X = regional[['lat', 'lon']].values
    n_samples = len(regional)

    # 4. CLUSTERING WITH CONSTRAINTS
    metrics = {}
    fig, axes = plt.subplots(1, 3, figsize=(18, 6))

    for i, k in enumerate(K_VALUES):
        size_min = int((n_samples / k) * 0.8)
        size_max = int((n_samples / k) * 1.2)
        
        print(f"[PROCESS] Clustering K={k} | Target size: {size_min}-{size_max} clubs")

        model = KMeansConstrained(
            n_clusters=k,
            size_min=size_min,
            size_max=size_max,
            random_state=42
        )
        
        regional[f'cluster_k{k}'] = model.fit_predict(X)
        
        counts = regional[f'cluster_k{k}'].value_counts()
        metrics[f'k{k}'] = {
            "sizes": counts.to_dict(),
            "imbalance": float(counts.max() / counts.min())
        }

        ax = axes[i]
        scatter = ax.scatter(regional['lon'], regional['lat'], c=regional[f'cluster_k{k}'], cmap='tab10', s=15, alpha=0.6)
        ax.set_title(f"Balanced K={k}\nImbalance: {metrics[f'k{k}']['imbalance']:.2f}")

    # 5. EXPORT
    plt.tight_layout()
    plt.savefig(OUTPUT_PLOT)
    
    regional = regional.drop(columns=['normalized_id', 'is_elite'])
    regional.to_csv(OUTPUT_FILE, index=False, sep=';')
    
    with open(REPORT_FILE, 'w') as f:
        json.dump(metrics, f, indent=4)

    print(f"\n[SUCCESS] Balanced clustering completed.")

if __name__ == "__main__":
    main()