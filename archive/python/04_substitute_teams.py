import pandas as pd
import os

def main():
    games_file = r"data\02_processed\all_games_v2.csv"
    map_file = r"data\02_processed\map_times_dicionario.csv"
    output_file = r"data\02_processed\all_games_v3.csv"

    print("="*70)
    print("CONSOLIDAÇÃO DOS NOMES DE TIMES (NOME CURTO MAIS FREQUENTE)")
    print("="*70)

    if not os.path.exists(games_file) or not os.path.exists(map_file):
        print("[ERRO] Arquivos de entrada não encontrados.")
        return

    # 1. Leitura dos dados
    df_games = pd.read_csv(games_file, sep=';', encoding='utf-8-sig')
    df_map = pd.read_csv(map_file, sep=';', encoding='utf-8-sig')

    # 2. Contagem de frequência global de cada string original (Mandantes + Visitantes)
    mandantes = df_games[['mandante', 'mandante_estado']].rename(
        columns={'mandante': 'clube', 'mandante_estado': 'estado'}
    )
    visitantes = df_games[['visitante', 'visitante_estado']].rename(
        columns={'visitante': 'clube', 'visitante_estado': 'estado'}
    )
    
    todas_aparicoes = pd.concat([mandantes, visitantes])
    frequencias = todas_aparicoes.groupby(['estado', 'clube']).size().reset_index(name='contagem')

    # 3. Mesclar as frequências com o dicionário canônico
    df_freq_map = pd.merge(df_map, frequencias, on=['estado', 'clube'], how='left')
    df_freq_map['contagem'] = df_freq_map['contagem'].fillna(0)

    # 4. Encontrar o nome curto mais frequente para cada clube_canonical
    # Ordenamos por estado, nome canônico e contagem (decrescente)
    df_freq_map = df_freq_map.sort_values(
        by=['estado', 'clube_canonical', 'contagem'], 
        ascending=[True, True, False]
    )
    
    # O primeiro registro de cada grupo é garantidamente o mais frequente
    nomes_principais = df_freq_map.drop_duplicates(subset=['estado', 'clube_canonical'], keep='first')
    
    # Dicionário intermediário: (estado_canonical) -> nome_curto_principal
    dict_canonical_to_short = dict(zip(
        nomes_principais['estado'] + "_" + nomes_principais['clube_canonical'], 
        nomes_principais['clube']
    ))

    # 5. Criar o dicionário definitivo de substituição: clube_original -> nome_curto_principal
    df_map['nome_curto_principal'] = (df_map['estado'] + "_" + df_map['clube_canonical']).map(dict_canonical_to_short)
    
    dict_final_replace = dict(zip(
        df_map['estado'] + "_" + df_map['clube'], 
        df_map['nome_curto_principal']
    ))

    # 6. Aplicar a substituição no dataframe de jogos
    # Criamos chaves temporárias para o replace considerar o estado correto
    chave_mandante = df_games['mandante_estado'] + "_" + df_games['mandante']
    chave_visitante = df_games['visitante_estado'] + "_" + df_games['visitante']

    df_games['mandante'] = chave_mandante.map(dict_final_replace).fillna(df_games['mandante'])
    df_games['visitante'] = chave_visitante.map(dict_final_replace).fillna(df_games['visitante'])

    # 7. Salvar o resultado
    df_games.to_csv(output_file, index=False, sep=';', encoding='utf-8-sig')

    print("[SUCESSO] Substituição concluída!")
    print(f"[SUCESSO] Arquivo salvo em: {output_file}")
    
    # Exemplo visual do que aconteceu:
    print("\n--- EXEMPLOS DE SUBSTITUIÇÕES REALIZADAS ---")
    exemplo = df_map[df_map['clube'] != df_map['nome_curto_principal']].head(999)
    for _, row in exemplo.iterrows():
        print(f"{row['estado'].upper()}: '{row['clube']}' ---> virou ---> '{row['nome_curto_principal']}'")
        
    print("="*70)

if __name__ == "__main__":
    main()