import pandas as pd
import numpy as np
from sklearn.cluster import AgglomerativeClustering
import matplotlib.pyplot as plt

# --- CONFIGURATION ---
INPUT_FILE = 'data/04_results/proposal_division_3.csv'
OUTPUT_FILE = 'data/04_results/proposal_division_4.csv'
SUB_K_VALUES = [2, 3, 4]

COLORS = ['#e6194b', '#3cb44b', '#ffe119', '#4363d8',
          '#f58231', '#911eb4', '#46f0f0', '#f032e6']


def hierarchical_subclustering(df):
    """
    Apply hierarchical sub-clustering within each macro cluster.

    Args:
        df (pd.DataFrame): Input dataset containing macro clusters.

    Returns:
        pd.DataFrame: Updated dataset with sub-cluster columns.
    """
    macro_clusters = sorted(df['cluster_k3'].unique())

    for m_id in macro_clusters:
        df_sub = df[df['cluster_k3'] == m_id].copy()
        X = df_sub[['lat', 'lon']].values

        if len(df_sub) < max(SUB_K_VALUES):
            continue

        for k_sub in SUB_K_VALUES:
            model = AgglomerativeClustering(n_clusters=k_sub, linkage='ward')
            sub_labels = model.fit_predict(X)

            col_name = f'sub_cluster_m{m_id}_k{k_sub}'
            df.loc[df['cluster_k3'] == m_id, col_name] = sub_labels

    return df


def plot_subclusters(df):
    """
    Generate visualization of hierarchical sub-clusters.

    Args:
        df (pd.DataFrame): Dataset with sub-cluster labels.
    """
    macro_clusters = sorted(df['cluster_k3'].unique())

    fig, axes = plt.subplots(
        len(macro_clusters),
        len(SUB_K_VALUES),
        figsize=(5 * len(SUB_K_VALUES), 5 * len(macro_clusters))
    )

    axes = np.array(axes).reshape(len(macro_clusters), len(SUB_K_VALUES))

    for row, m_id in enumerate(macro_clusters):
        df_sub = df[df['cluster_k3'] == m_id]
        X = df_sub[['lat', 'lon']].values

        if len(df_sub) < max(SUB_K_VALUES):
            continue

        for col, k_sub in enumerate(SUB_K_VALUES):
            ax = axes[row, col]
            labels = df_sub[f'sub_cluster_m{m_id}_k{k_sub}']

            for s_id in range(k_sub):
                mask = labels == s_id
                ax.scatter(
                    X[mask, 1],
                    X[mask, 0],
                    s=20,
                    alpha=0.7
                )

            ax.set_title(f'Macro {m_id} | K={k_sub}')
            ax.grid(True, linestyle=':', alpha=0.5)

    plt.tight_layout()
    plt.savefig('analise_sub_clusters_hierarquicos.png', dpi=150)
    plt.close()


def main():
    df = pd.read_csv(INPUT_FILE, sep=';', encoding='utf-8-sig')
    df = hierarchical_subclustering(df)

    plot_subclusters(df)
    df.to_csv(OUTPUT_FILE, index=False, sep=';', encoding='utf-8-sig')
    print(f"Saved to '{OUTPUT_FILE}'")


if __name__ == "__main__":
    main()