import pandas as pd
import folium
from folium.plugins import MarkerCluster
import numpy as np
import matplotlib.pyplot as plt
import webbrowser
import os

INPUT_FILE = 'data/03_final/unique_teams_geo_final.csv'
OUTPUT_FILE = 'outputs/maps/football_clubs_map.html'

def main():
    try:
        df = pd.read_csv(INPUT_FILE, sep=';', encoding='utf-8-sig')
    except FileNotFoundError:
        print(f"Erro: O arquivo {INPUT_FILE} não foi encontrado.")
        return

    df = df.dropna(subset=['lat', 'lon'])

    # Adição de ruído (jitter) para evitar sobreposição exata de clubes na mesma cidade/estádio
    np.random.seed(42)
    jitter_strength = 0.002
    df['lat_jitter'] = df['lat'] + np.random.uniform(-jitter_strength, jitter_strength, len(df))
    df['lon_jitter'] = df['lon'] + np.random.uniform(-jitter_strength, jitter_strength, len(df))

    # Criação da paleta de cores mapeada por estado
    states = sorted(df['estado'].dropna().unique())
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
    if max_wins == 0:
        max_wins = 1

    for _, row in df.iterrows():
        # O raio do círculo é proporcional ao número de vitórias na base de dados
        radius = 4 + (row['wins'] / max_wins) * 12

        tooltip = f"""
        <b>{row['clube']}</b><br>
        {row['cidade']} - {row['estado']}<br>
        Vitórias: {row['wins']}<br>
        Empates: {row['draws']}<br>
        Derrotas: {row['losses']}<br>
        Total de Jogos: {row['total_games']}
        """

        color = state_colors.get(row['estado'], '#808080')

        folium.CircleMarker(
            location=[row['lat_jitter'], row['lon_jitter']],
            radius=radius,
            color=color,
            fill=True,
            fill_color=color,
            fill_opacity=0.75,
            weight=1
        ).add_child(folium.Tooltip(tooltip)).add_to(cluster)

    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    m.save(OUTPUT_FILE)

    file_path = os.path.abspath(OUTPUT_FILE)
    webbrowser.open(f'file://{file_path}')

if __name__ == "__main__":
    main()