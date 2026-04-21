import pandas as pd
import numpy as np
import networkx as nx
from sklearn.neighbors import BallTree
import community.community_louvain as community_louvain
import matplotlib.pyplot as plt

# --- CONFIGURATION ---
INPUT_FILE = 'active_clubs_geodata.csv'
OUTPUT_FILE = 'clubs_with_logistic_clusters.csv'
K_NEIGHBORS = 50
EARTH_RADIUS = 6371


def build_knn_graph(df):
    """
    Build a proximity graph using K-nearest neighbors with geographic distance.

    Args:
        df (pd.DataFrame): Dataset containing latitude and longitude.

    Returns:
        networkx.Graph: Weighted undirected graph.
    """
    coords = np.deg2rad(df[['lat', 'lon']].values)
    tree = BallTree(coords, metric='haversine')

    dist, ind = tree.query(coords, k=K_NEIGHBORS + 1)

    G = nx.Graph()

    for i, neighbors in enumerate(ind):
        origin = f"{df.iloc[i]['clube']}/{df.iloc[i]['estado']}"

        for j, neighbor_idx in enumerate(neighbors):
            if i == neighbor_idx:
                continue

            destination = f"{df.iloc[neighbor_idx]['clube']}/{df.iloc[neighbor_idx]['estado']}"
            dist_km = dist[i][j] * EARTH_RADIUS
            weight = 1 / (dist_km + 10)

            G.add_edge(origin, destination, weight=weight, distance=dist_km)

    return G


def detect_communities(G):
    """
    Detect communities using the Louvain method.

    Args:
        G (networkx.Graph): Input graph.

    Returns:
        dict: Mapping of node to cluster id.
    """
    return community_louvain.best_partition(G, weight='weight')


def assign_clusters(df, partition):
    """
    Assign cluster labels to the dataframe.

    Args:
        df (pd.DataFrame): Input dataset.
        partition (dict): Node-to-cluster mapping.

    Returns:
        pd.DataFrame: Updated dataset with cluster labels.
    """
    df['cluster_logistico'] = df.apply(
        lambda x: partition.get(f"{x['clube']}/{x['estado']}"), axis=1
    )
    return df


def plot_clusters(df):
    """
    Generate and save a scatter plot of clusters.

    Args:
        df (pd.DataFrame): Dataset with cluster labels.
    """
    plt.figure(figsize=(10, 12))
    scatter = plt.scatter(df['lon'], df['lat'], c=df['cluster_logistico'], cmap='tab20', s=30, alpha=0.7)
    plt.colorbar(scatter, label='Cluster ID')
    plt.xlabel('Longitude')
    plt.ylabel('Latitude')
    plt.grid(True, linestyle='--', alpha=0.5)

    plt.tight_layout()
    plt.savefig('clusters_logisticos_brasil.png')
    plt.close()


def summarize(df):
    """
    Print basic statistics about detected clusters.

    Args:
        df (pd.DataFrame): Dataset with cluster labels.
    """
    n_clusters = df['cluster_logistico'].nunique()
    avg_size = len(df) / n_clusters if n_clusters > 0 else 0

    print(f"Clusters: {n_clusters}")
    print(f"Average size: {avg_size:.2f}")


def main():
    df = pd.read_csv(INPUT_FILE, sep=';', encoding='utf-8-sig')

    G = build_knn_graph(df)
    partition = detect_communities(G)

    df = assign_clusters(df, partition)

    df.to_csv(OUTPUT_FILE, index=False, sep=';', encoding='utf-8-sig')

    plot_clusters(df)
    summarize(df)


if __name__ == "__main__":
    main()