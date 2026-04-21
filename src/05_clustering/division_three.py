import pandas as pd
import numpy as np
from sklearn.cluster import AgglomerativeClustering
import matplotlib.pyplot as plt
import json
import math

# --- CONFIGURATION ---
PAGERANK_FILE = 'data/03_final/pagerank.csv'
GEODATA_FILE = 'data/03_final/active_clubs_geodata.csv'
REPORT_FILE = 'data/04_results/clubs_with_logistic_clusters.csv'
OUTPUT_FILE = 'data/04_results/proposal_division_3.csv'
K_VALUES = [2, 3, 4, 5, 6, 7, 8]

HIGH_CONTRAST_COLORS = [
    '#e6194b', '#3cb44b', '#ffe119', '#4363d8',
    '#f58231', '#911eb4', '#46f0f0', '#f032e6'
]


def normalize_columns(df, club_col, state_col):
    """
    Standardize club and state columns.

    Args:
        df (pd.DataFrame): Input dataframe.
        club_col (str): Club column name.
        state_col (str): State column name.

    Returns:
        pd.DataFrame: Normalized dataframe.
    """
    df[club_col] = df[club_col].astype(str).str.upper().str.strip()
    df[state_col] = df[state_col].astype(str).str.upper().str.strip()
    return df


def build_master_dataset(df_geo, df_pr):
    """
    Merge geodata with PageRank data and sort by score.

    Args:
        df_geo (pd.DataFrame): Geolocation dataset.
        df_pr (pd.DataFrame): PageRank dataset.

    Returns:
        pd.DataFrame: Merged dataset.
    """
    df_master = pd.merge(
        df_geo,
        df_pr,
        left_on=['clube', 'estado'],
        right_on=['clube', 'uf']
    ).drop(columns=['uf'])

    return df_master.sort_values(by='pagerank_score', ascending=False)


def split_elite(df_master, top_n=40):
    """
    Split dataset into elite and regional pools.

    Args:
        df_master (pd.DataFrame): Full dataset.
        top_n (int): Number of elite teams.

    Returns:
        tuple[pd.DataFrame, pd.DataFrame]: Elite and regional datasets.
    """
    elite = df_master.head(top_n).copy()
    regional = df_master.iloc[top_n:].copy()
    return elite, regional


def evaluate_clusters(regional_pool, X):
    """
    Perform clustering for multiple K values and collect statistics.

    Args:
        regional_pool (pd.DataFrame): Dataset to cluster.
        X (np.ndarray): Feature matrix.

    Returns:
        dict: Summary statistics per K.
        pd.DataFrame: Updated dataset with cluster labels.
    """
    results_summary = {}

    for k in K_VALUES:
        model = AgglomerativeClustering(n_clusters=k, linkage='ward')
        clusters = model.fit_predict(X)
        regional_pool[f'cluster_k{k}'] = clusters

        counts = regional_pool[f'cluster_k{k}'].value_counts().sort_index()

        results_summary[f'k{k}'] = {
            "counts": counts.to_dict(),
            "mean_size": float(counts.mean()),
            "std_dev": float(counts.std()),
            "imbalance_ratio": float(counts.max() / counts.min())
        }

    return results_summary, regional_pool


def plot_clusters(elite, regional_pool):
    """
    Plot clustering results for different K values.

    Args:
        elite (pd.DataFrame): Elite dataset.
        regional_pool (pd.DataFrame): Clustered dataset.
    """
    n_plots = len(K_VALUES)
    n_cols = 3
    n_rows = math.ceil(n_plots / n_cols)

    fig, axes = plt.subplots(n_rows, n_cols, figsize=(6 * n_cols, 6 * n_rows))
    axes = axes.flatten()

    for i, k in enumerate(K_VALUES):
        ax = axes[i]

        for cluster_id in range(k):
            c_data = regional_pool[regional_pool[f'cluster_k{k}'] == cluster_id]
            ax.scatter(
                c_data['lon'],
                c_data['lat'],
                c=HIGH_CONTRAST_COLORS[cluster_id % len(HIGH_CONTRAST_COLORS)],
                label=f'C{cluster_id} (n={len(c_data)})',
                s=30,
                alpha=0.7
            )

        ax.scatter(elite['lon'], elite['lat'], c='black', marker='x', s=60)
        ax.set_title(f'K={k}')
        ax.grid(True, linestyle=':', alpha=0.5)

    for j in range(i + 1, len(axes)):
        fig.delaxes(axes[j])

    plt.tight_layout()
    plt.savefig('comparativo_clusters_balanceados.png', dpi=150)
    plt.close()


def main():
    df_pr = pd.read_csv(PAGERANK_FILE, sep=';', encoding='utf-8-sig')
    df_geo = pd.read_csv(GEODATA_FILE, sep=';', encoding='utf-8-sig')

    df_pr = normalize_columns(df_pr, 'clube', 'uf')
    df_geo = normalize_columns(df_geo, 'clube', 'estado')

    df_master = build_master_dataset(df_geo, df_pr)

    # TOP 40 teams (Serie A and Serie B) divided
    elite, regional_pool = split_elite(df_master)
    X = regional_pool[['lat', 'lon']].values
    results_summary, regional_pool = evaluate_clusters(regional_pool, X)

    plot_clusters(elite, regional_pool)

    with open(REPORT_FILE, 'w', encoding='utf-8') as f:
        json.dump(results_summary, f, indent=4, ensure_ascii=False)

    regional_pool.to_csv(OUTPUT_FILE, index=False, sep=';', encoding='utf-8-sig')

    print(f"Saved report to '{REPORT_FILE}'")
    print(f"Saved dataset to '{OUTPUT_FILE}'")


if __name__ == "__main__":
    main()