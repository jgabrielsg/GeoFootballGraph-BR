import pandas as pd
import folium
from folium.plugins import MarkerCluster
import numpy as np
import matplotlib.pyplot as plt
import webbrowser
import os

INPUT_FILE = 'active_clubs_geodata.csv'
OUTPUT_FILE = 'football_clubs_map.html'

def main():
    """
    Generates an interactive clustered map with minimal jitter, improved styling,
    and automatically opens it in the browser.
    """
    df = pd.read_csv(INPUT_FILE, sep=';', encoding='utf-8-sig')

    df['total_games'] = df['wins'] + df['draws'] + df['losses']

    np.random.seed(42)
    jitter_strength = 0.002
    df['lat_jitter'] = df['lat'] + np.random.uniform(-jitter_strength, jitter_strength, len(df))
    df['lon_jitter'] = df['lon'] + np.random.uniform(-jitter_strength, jitter_strength, len(df))

    states = sorted(df['estado'].unique())
    cmap = plt.get_cmap('Set2', len(states))
    state_colors = {
        state: '#%02x%02x%02x' % tuple(int(c*255) for c in cmap(i)[:3])
        for i, state in enumerate(states)
    }

    m = folium.Map(
        location=[-14.235, -51.925],
        zoom_start=4,
        tiles='CartoDB positron'
    )

    cluster = MarkerCluster().add_to(m)

    max_wins = df['wins'].max()

    for _, row in df.iterrows():
        radius = 4 + (row['wins'] / max_wins) * 12

        tooltip = f"""
        <b>{row['clube']}</b><br>
        {row['cidade']} - {row['estado']}<br>
        Wins: {row['wins']}<br>
        Draws: {row['draws']}<br>
        Losses: {row['losses']}<br>
        Total Games: {row['total_games']}
        """

        folium.CircleMarker(
            location=[row['lat_jitter'], row['lon_jitter']],
            radius=radius,
            color=state_colors[row['estado']],
            fill=True,
            fill_color=state_colors[row['estado']],
            fill_opacity=0.75,
            weight=1
        ).add_child(folium.Tooltip(tooltip)).add_to(cluster)

    m.save(OUTPUT_FILE)

    file_path = os.path.abspath(OUTPUT_FILE)
    webbrowser.open(f'file://{file_path}')

if __name__ == "__main__":
    main()