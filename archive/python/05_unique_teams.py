import pandas as pd
import os

def main():
    input_file = r"data\02_processed\all_games_v3.csv"
    output_file = r"data\02_processed\all_unique_teams_geolocalization.csv"
    
    print("="*70)
    print("EXTRAÇÃO DE CLUBES ÚNICOS COM MAPEAMENTO CANÔNICO")
    print("="*70)
    
    if not os.path.exists(input_file):
        print(f"[ERROR] Arquivo não encontrado: {input_file}")
        return

    df = pd.read_csv(input_file, sep=';', encoding='utf-8-sig')
    
    # 1. Capturar pares de Mandante e Visitante
    mandantes = df[['mandante', 'mandante_estado']].rename(
        columns={'mandante': 'clube', 'mandante_estado': 'estado'}
    )
    visitantes = df[['visitante', 'visitante_estado']].rename(
        columns={'visitante': 'clube', 'visitante_estado': 'estado'}
    )
    
    combined = pd.concat([mandantes, visitantes], ignore_index=True)
    unique_teams = combined.dropna().drop_duplicates()
    
    # 2. Ordenação por Estado e Clube
    unique_teams = unique_teams.sort_values(by=['estado', 'clube']).reset_index(drop=True)
    
    # 3. Inserção das colunas de Resolução de Entidade e Geocodificação
    # O 'clube_canonical' por padrão nasce igual ao nome do clube
    unique_teams['clube_canonical'] = unique_teams['clube']
    unique_teams['cidade'] = ""
    unique_teams['latitude'] = ""
    unique_teams['longitude'] = ""
    
    # Reorganizar as colunas para o fluxo de preenchimento ficar lógico
    cols_order = ['estado', 'clube', 'clube_canonical', 'cidade', 'latitude', 'longitude']
    unique_teams = unique_teams[cols_order]
    
    # 4. Salvar o arquivo
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    unique_teams.to_csv(output_file, index=False, sep=';', encoding='utf-8-sig')
    
    print(f"[SUCCESS] {len(unique_teams)} strings de clubes extraídas.")
    print(f"[SUCCESS] Tabela gerada em: {output_file}")
    print("="*70)

if __name__ == "__main__":
    main()