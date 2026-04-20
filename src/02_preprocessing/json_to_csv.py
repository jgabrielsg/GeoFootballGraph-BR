import json
import csv
import os
import re

# Configurações de caminhos
pasta_origem = 'processed'
arquivo_saida = 'jogos_nacionais_full.csv'

# Mapeamento de divisões conforme solicitado
mapa_divisao = {
    'Serie_A': '1',
    'Serie_B': '2',
    'Serie_C': '3',
    'Serie_D': '4',
    'CdB': '0'
}


def converter_data(data_str):
    """Converte DD/MM/AAAA para AAAA-MM-DD"""
    try:
        partes = data_str.split('/')
        if len(partes) == 3:
            return f"{partes[2]}-{partes[1]}-{partes[0]}"
    except:
        pass
    return data_str

# Inicializa a lista de jogos
todos_jogos = []

# Percorrer todos os arquivos na pasta processed
for nome_arquivo in os.listdir(pasta_origem):
    if nome_arquivo.endswith('.json'):
        # Extrair Divisão e Ano do nome do arquivo (Ex: Serie_A_2022_games.json)
        match = re.match(r'([a-zA-Z_]+)_(\d{4})_games\.json', nome_arquivo)
        if match:
            prefixo = match.group(1)
            ano = match.group(2)
            divisao = mapa_divisao.get(prefixo, 'Desconhecido')
            
            caminho_completo = os.path.join(pasta_origem, nome_arquivo)
            
            with open(caminho_completo, 'r', encoding='utf-8') as f:
                dados_json = json.load(f)
                
                for id_jogo, info in dados_json.items():
                    # Extração e Limpeza
                    data = converter_data(info.get('Date', ''))
                    mandante = info.get('Home', '')
                    visitante = info.get('Away', '')
                    
                    # Transformar "3 X 2" em "3-2"
                    resultado_raw = info.get('Result', '')
                    placar = resultado_raw.replace(' X ', '-').strip()
                    
                    # Filtro: Só adicionar se o jogo tiver resultado definido
                    if '-' in placar and any(char.isdigit() for char in placar):
                        todos_jogos.append({
                            'estado': 'nacional',
                            'divisao': divisao,
                            'ano': ano,
                            'data': data,
                            'mandante': mandante,
                            'visitante': visitante,
                            'placar': placar
                        })

# Salvar em CSV
colunas = ['estado', 'divisao', 'ano', 'data', 'mandante', 'visitante', 'placar']

with open(arquivo_saida, 'w', newline='', encoding='utf-8-sig') as f_csv:
    escritor = csv.DictWriter(f_csv, fieldnames=colunas, delimiter=';')
    escritor.writeheader()
    escritor.writerows(todos_jogos)

print(f"Processamento concluído! {len(todos_jogos)} jogos nacionais unificados em '{arquivo_saida}'.")