import pandas as pd
import numpy as np
import folium
from folium import plugins
import os

# --- CONFIGURATION ---
FILE_C = r'data\04_results\serie_c_final_proposal.csv'
FILE_D = r'data\04_results\serie_d_final_proposal.csv'
BASE_DIR = r'outputs\maps\03_BalancedKMeans'

# Mapeamento de nomes conforme solicitado
CLUSTER_NAMES = {
    0: "Divisão_Norte",
    1: "Divisão_Centro-Sudeste",
    2: "Divisão_Nordeste",
    3: "Divisão_Sul-Mato-Grosso"
}

def add_jitter(val, amount=0.0008):
    """Adiciona um ruído pequeno para evitar sobreposição total em cidades sede."""
    return val + np.random.normal(0, amount)

def get_overall_rank(clube_id, df_rank):
    """Recupera a posição global do time no PageRank."""
    try:
        return df_rank[df_rank['clube_id'] == clube_id].index[0] + 1
    except:
        return "N/A"

def create_advanced_map(df, title):
    """Gera um mapa Folium com hover animado e ferramenta de medição."""
    # Jitter nas coordenadas para visualização
    df['lat_j'] = df['lat'].apply(add_jitter)
    df['lon_j'] = df['lon'].apply(add_jitter)

    m = folium.Map(location=[-15.78, -47.93], zoom_start=4, tiles='cartodbpositron')

    # CSS para animação de Hover (Aumentar bolinha)
    custom_css = """
    <style>
    .leaflet-interactive {
        transition: stroke-width 0.2s, r 0.2s;
    }
    .leaflet-interactive:hover {
        stroke-width: 4;
        r: 12 !important;
    }
    </style>
    """
    m.get_root().header.add_child(folium.Element(custom_css))

    # Adiciona ferramenta de medição (Línea + KM)
    plugins.MeasureControl(position='topleft', primary_length_unit='kilometers', secondary_length_unit='miles').add_to(m)

    for _, row in df.iterrows():
        popup_html = f"""
        <div style='font-family: Arial; width: 200px;'>
            <h4 style='margin-bottom:5px;'>{row['clube']}</h4>
            <b>Estado:</b> {row['uf']}<br>
            <b>Rank Global:</b> {row['overall_rank']}º<br>
            <b>Posição na Liga:</b> {row['pos']}º<br>
            <b>Score PR:</b> {row['score']:.5f}
        </div>
        """
        
        folium.CircleMarker(
            location=[row['lat_j'], row['lon_j']],
            radius=7,
            popup=folium.Popup(popup_html, max_width=250),
            tooltip=f"{row['clube']} ({row['uf']}) - Rank: {row['overall_rank']}º",
            color='#00008B' if row['pos'] <= 2 else '#ADD8E6' if row['pos'] <= 6 else 'red' if row['pos'] >= 16 else 'gray',
            fill=True,
            fill_opacity=0.8,
            weight=1
        ).add_to(m)

    return m

def main():
    # 1. CARREGAR DADOS E RANKING GLOBAL
    df_c = pd.read_csv(FILE_C, sep=';')
    df_d = pd.read_csv(FILE_D, sep=';')
    
    # Criar um ranking global unificado baseado no score
    df_rank = pd.concat([df_c, df_d]).sort_values(by='score', ascending=False).reset_index(drop=True)
    df_c['overall_rank'] = df_c['clube_id'].apply(lambda x: get_overall_rank(x, df_rank))
    df_d['overall_rank'] = df_d['clube_id'].apply(lambda x: get_overall_rank(x, df_rank))

    # 2. PROCESSAR POR MACRO-REGIÃO
    for m_id, folder_name in CLUSTER_NAMES.items():
        path = os.path.join(BASE_DIR, folder_name)
        os.makedirs(path, exist_ok=True)
        print(f"[PROCESS] Gerando mapas para {folder_name}...")

        # Mapas Série C
        subset_c = df_c[df_c['cluster_k4'] == m_id]
        if not subset_c.empty:
            m_c = create_advanced_map(subset_c, f"Série C - {folder_name}")
            m_c.save(os.path.join(path, "serie_c_final.html"))

        # Mapas Série D
        subset_d_macro = df_d[df_d['cluster_k4'] == m_id]
        # Identificar qual coluna de sub-cluster usar
        sub_key = 'serie_d_k4' if m_id == 0 else 'serie_d_k3'
        
        for s_id in sorted(subset_d_macro[sub_key].unique()):
            subset_d = subset_d_macro[subset_d_macro[sub_key] == s_id]
            m_d = create_advanced_map(subset_d, f"Série D - {folder_name} - Liga {s_id+1}")
            m_d.save(os.path.join(path, f"serie_d_liga_{s_id+1}.html"))

    print("\n" + "="*70)
    print(f"SUCESSO! Mapas interativos e estruturados em: {BASE_DIR}")
    print("="*70)

if __name__ == "__main__":
    main()