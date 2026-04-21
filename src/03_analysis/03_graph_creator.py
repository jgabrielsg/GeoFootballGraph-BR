import pandas as pd
import networkx as nx
import numpy as np
import os

# --- CONFIGURATION ---
INPUT_FILE = 'data/03_final/all_games_geodata.csv'
OUTPUT_COMP = 'data/03_final/graphs/teams_games.graphml'
OUTPUT_LOG = 'data/03_final/graphs/teams_distance.graphml'

EARTH_RADIUS_KM = 6371.0


def ensure_dirs():
    os.makedirs(os.path.dirname(OUTPUT_COMP), exist_ok=True)
    os.makedirs(os.path.dirname(OUTPUT_LOG), exist_ok=True)


def haversine(lat1, lon1, lat2, lon2):
    """Great-circle distance in KM."""
    phi1, phi2 = np.radians(lat1), np.radians(lat2)
    dphi = np.radians(lat2 - lat1)
    dlambda = np.radians(lon2 - lon1)
    a = np.sin(dphi / 2) ** 2 + np.cos(phi1) * np.cos(phi2) * np.sin(dlambda / 2) ** 2
    return 2 * EARTH_RADIUS_KM * np.arctan2(np.sqrt(a), np.sqrt(1 - a))


def validate_row(row):
    """Basic validation to avoid corrupt edges."""
    required = [
        'mandante', 'visitante',
        'mandante_estado', 'visitante_estado',
        'lat_h', 'lon_h', 'lat_a', 'lon_a'
    ]

    for col in required:
        if pd.isna(row[col]):
            return False

    # Avoid invalid coordinates
    if not (-90 <= row['lat_h'] <= 90 and -90 <= row['lat_a'] <= 90):
        return False
    if not (-180 <= row['lon_h'] <= 180 and -180 <= row['lon_a'] <= 180):
        return False

    return True


def main():
    ensure_dirs()

    df = pd.read_csv(INPUT_FILE, sep=';', encoding='utf-8-sig')

    # Drop clearly broken rows early
    df = df.dropna(subset=[
        'mandante', 'visitante',
        'mandante_estado', 'visitante_estado'
    ])

    # Unique node IDs
    df['h_id'] = df['mandante'].astype(str) + "/" + df['mandante_estado'].astype(str)
    df['a_id'] = df['visitante'].astype(str) + "/" + df['visitante_estado'].astype(str)

    G_comp = nx.DiGraph()
    G_log = nx.Graph()

    for _, row in df.iterrows():

        if not validate_row(row):
            continue

        h_id = row['h_id']
        a_id = row['a_id']

        # Avoid self-loop noise
        if h_id == a_id:
            continue

        # --- NODE ATTRIBUTES ---
        h_attrs = {
            'lat': float(row['lat_h']),
            'lon': float(row['lon_h']),
            'cidade': str(row['cidade_h']) if not pd.isna(row['cidade_h']) else ""
        }

        a_attrs = {
            'lat': float(row['lat_a']),
            'lon': float(row['lon_a']),
            'cidade': str(row['cidade_a']) if not pd.isna(row['cidade_a']) else ""
        }

        G_comp.add_node(h_id, **h_attrs)
        G_comp.add_node(a_id, **a_attrs)

        G_log.add_node(h_id, **h_attrs)
        G_log.add_node(a_id, **a_attrs)

        # --- COMPETITION GRAPH ---
        fluxo_h = row.get('fluxo_h', 0) or 0
        fluxo_a = row.get('fluxo_a', 0) or 0

        if fluxo_a > 0:
            if G_comp.has_edge(h_id, a_id):
                G_comp[h_id][a_id]['weight'] += fluxo_a
            else:
                G_comp.add_edge(h_id, a_id, weight=float(fluxo_a))

        if fluxo_h > 0:
            if G_comp.has_edge(a_id, h_id):
                G_comp[a_id][h_id]['weight'] += fluxo_h
            else:
                G_comp.add_edge(a_id, h_id, weight=float(fluxo_h))

        # --- LOGISTICS GRAPH ---
        if not G_log.has_edge(h_id, a_id):
            dist = haversine(
                row['lat_h'], row['lon_h'],
                row['lat_a'], row['lon_a']
            )

            # Avoid zero-distance artifacts (same stadium cases)
            if dist == 0:
                dist = 1.0

            G_log.add_edge(h_id, a_id, weight=float(dist))

    # --- SAVE ---
    nx.write_graphml(G_comp, OUTPUT_COMP)
    nx.write_graphml(G_log, OUTPUT_LOG)


if __name__ == "__main__":
    main()