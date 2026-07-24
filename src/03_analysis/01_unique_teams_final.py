import pandas as pd
import os

INPUT_FILE = 'data/03_final/all_games_geodata.csv'
OUTPUT_FILE = 'data/03_final/unique_teams_geo_final.csv'

def main():
    print("="*60)
    print("GERANDO BASE DEFINITIVA DE TIMES ÚNICOS E ESTATÍSTICAS")
    print("="*60)

    # 1. Carregar a base de jogos processada
    try:
        df = pd.read_csv(INPUT_FILE, sep=';', encoding='utf-8-sig')
    except FileNotFoundError:
        print(f"[ERRO] Arquivo não encontrado: {INPUT_FILE}")
        return

    print(f"[INFO] Total de jogos carregados: {len(df)}")

    # 2. Criar DataFrames separados para Mandantes e Visitantes com suas estatísticas
    
    # --- MANDANTES ---
    df_home = pd.DataFrame({
        'clube': df['mandante'],
        'estado': df['mandante_estado'],
        'lat': df['lat_h'],
        'lon': df['lon_h'],
        'cidade': df['cidade_h'],
        'estadio': df['estadio_h'],
        'wins': (df['resultado'] == 'H').astype(int),
        'draws': (df['resultado'] == 'D').astype(int),
        'losses': (df['resultado'] == 'A').astype(int)
    })

    # --- VISITANTES ---
    df_away = pd.DataFrame({
        'clube': df['visitante'],
        'estado': df['visitante_estado'],
        'lat': df['lat_a'],
        'lon': df['lon_a'],
        'cidade': df['cidade_a'],
        'estadio': df['estadio_a'],
        'wins': (df['resultado'] == 'A').astype(int),
        'draws': (df['resultado'] == 'D').astype(int),
        'losses': (df['resultado'] == 'H').astype(int)
    })

    # 3. Concatenar Mandantes e Visitantes em um único DataFrame vertical
    df_all = pd.concat([df_home, df_away], ignore_index=True)

    # 4. Agrupar por Clube e Estado (Chave Única)
    # Para as estatísticas esportivas (wins, draws, losses), nós somamos.
    # Para os dados geográficos, pegamos a primeira ocorrência válida ('first').
    aggregation_rules = {
        'lat': 'first',
        'lon': 'first',
        'cidade': 'first',
        'estadio': 'first',
        'wins': 'sum',
        'draws': 'sum',
        'losses': 'sum'
    }

    df_unique = df_all.groupby(['clube', 'estado'], as_index=False).agg(aggregation_rules)

    # 5. Calcular o Total de Jogos
    df_unique['total_games'] = df_unique['wins'] + df_unique['draws'] + df_unique['losses']

    # Opcional: Filtrar possíveis linhas com dados geográficos nulos (se existirem)
    df_unique = df_unique.dropna(subset=['lat', 'lon'])

    # 6. Ordenar por quantidade de jogos (times mais ativos no topo)
    df_unique = df_unique.sort_values(by='total_games', ascending=False).reset_index(drop=True)

    # 7. Salvar o arquivo final
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    df_unique.to_csv(OUTPUT_FILE, sep=';', encoding='utf-8-sig', index=False)

    print(f"\n[SUCESSO] Mapeamento concluído!")
    print(f"[INFO] Total de clubes únicos extraídos: {len(df_unique)}")
    print(f"[INFO] Arquivo salvo em: {OUTPUT_FILE}")
    print("="*60)
    
    # Exibir um pequeno preview no terminal
    print("\nPreview dos 5 times mais ativos:")
    print(df_unique[['clube', 'estado', 'total_games', 'wins']].head(5).to_string(index=False))

if __name__ == "__main__":
    main()