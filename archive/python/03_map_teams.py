import pandas as pd
import os

def main():
    input_file = r"data\02_processed\all_unique_teams_geolocalization.csv"
    map_output = r"data\02_processed\teams_name_mapping.csv"
    dim_output = r"data\02_processed\all_teams_geolocalization.csv"

    print("="*60)
    print("ANÁLISE EXPLORATÓRIA E CONSOLIDAÇÃO DE DADOS")
    print("="*60)

    # 1. Leitura dos Dados
    df = pd.read_csv(input_file, sep=';', encoding='utf-8-sig')

    # ==========================================
    # PARTE A: ANÁLISE EXPLORATÓRIA (EDA)
    # ==========================================
    print("\n--- 1. IDENTIFICAÇÃO DE VALORES NULOS ---")
    print(df.isnull().sum())

    print("\n--- 2. TOP 5 ESTADOS COM MAIS STRINGS DE TIMES ---")
    print(df['estado'].value_counts().head(5))

    print("\n--- 3. TOP 5 CIDADES COM MAIS TIMES ---")
    print(df['cidade'].value_counts().head(5))

    print("\n--- 4. TOP 5 ESTÁDIOS MAIS UTILIZADOS ---")
    # Filtra vazios para não contar como estádio
    estadios = df[df['estadio'].notna() & (df['estadio'] != "")]
    print(estadios['estadio'].value_counts().head(5))

    # Identificando as fusões (Quantos nomes originais viraram um único canônico?)
    fusoes = df.groupby(['estado', 'clube_canonical']).size().reset_index(name='variacoes')
    top_fusoes = fusoes[fusoes['variacoes'] > 1].sort_values(by='variacoes', ascending=False)
    
    print("\n--- 5. MAIORES FUSÕES DE NOMES (Sinônimos encontrados) ---")
    print(top_fusoes.head(10))

    # ==========================================
    # PARTE B: CONSOLIDAÇÃO (MERGE DOS CANÔNICOS)
    # ==========================================
    
    # Artefato 1: Dicionário de Mapeamento (De -> Para)
    df_map = df[['estado', 'clube', 'clube_canonical']].copy()
    df_map.to_csv(map_output, index=False, sep=';', encoding='utf-8-sig')

    # Artefato 2: Tabela Dimensão de Clubes (Agrupando pelos canônicos)
    # Como a LLM pode ter escrito "Estádio Doutor Jorge" em uma linha e "Estádio Dr. Jorge" na outra,
    # agrupamos pelo nome canônico e pegamos o PRIMEIRO valor válido das colunas de geolocalização.
    df_dim = df.groupby(['estado', 'clube_canonical']).agg({
        'cidade': 'first',
        'latitude': 'first',
        'longitude': 'first',
        'estadio': 'first'
    }).reset_index()

    df_dim.to_csv(dim_output, index=False, sep=';', encoding='utf-8-sig')

    print("\n" + "="*60)
    print(f"[SUCESSO] Total de nomes originais rastreados: {len(df)}")
    print(f"[SUCESSO] Total de Clubes Únicos Oficiais gerados: {len(df_dim)}")
    print(f"-> Dicionário salvo em: {map_output}")
    print(f"-> Tabela Final de Clubes salva em: {dim_output}")
    print("="*60)

if __name__ == "__main__":
    main()