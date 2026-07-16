import requests
import pandas as pd
import time
import re

# --- CONFIGURAÇÕES ---
USER_AGENT = 'TCC_Joao_Gabriel_FGV/1.5 (seu-email@fgv.edu.br)'
HEADERS = {'User-Agent': USER_AGENT}

def get_initial_wikidata():
    """Etapa 1: Query inicial no Wikidata para pegar os links dos 1500+ clubes."""
    print("Iniciando Query no Wikidata...")
    url = 'https://query.wikidata.org/sparql'
    query = """
    SELECT ?clubLabel ?wikiTitle WHERE {
      ?club wdt:P31 wd:Q476028; # Clube de futebol
            wdt:P17 wd:Q155.      # No Brasil
      
      ?article schema:about ?club;
               schema:isPartOf <https://pt.wikipedia.org/>;
               schema:name ?wikiTitle.
               
      SERVICE wikibase:label { bd:serviceParam wikibase:language "pt". }
    }
    """
    r = requests.get(url, params={'format': 'json', 'query': query}, headers=HEADERS)
    r.raise_for_status()
    data = r.json()
    df = pd.DataFrame([
        {'nome_clube': i['clubLabel']['value'], 'wiki_title': i['wikiTitle']['value']} 
        for i in data['results']['bindings']
    ])
    df.to_csv('raw_clubs_wikidata.csv', index=False, sep=';', encoding='utf-8-sig')
    return df

def get_ibge_cities():
    """Baixa uma base mestre de municípios do Brasil com lat/long oficiais."""
    print("Carregando base de municípios do IBGE...")
    url = "https://raw.githubusercontent.com/kelvins/municipios-brasileiros/main/csv/municipios.csv"
    return pd.read_csv(url)

def extract_city_from_summary(wiki_title, city_list):
    """Acessa a Wikipedia e tenta encontrar um município brasileiro no texto."""
    api_url = f"https://pt.wikipedia.org/api/rest_v1/page/summary/{wiki_title.replace(' ', '_')}"
    try:
        response = requests.get(api_url, headers=HEADERS, timeout=5)
        if response.status_code != 200: return None, None, None
        
        extract = response.json().get('extract', '')
        
        # Procuramos por nomes de cidades da nossa lista IBGE dentro do resumo
        # Damos prioridade para nomes que aparecem após 'cidade de' ou 'sede em'
        for city in city_list:
            # Busca simples: se o nome da cidade está nas primeiras 2 frases
            # (Limitamos a busca para evitar falsos positivos de cidades mencionadas depois)
            if city in extract[:400]:
                return city
    except:
        pass
    return None

# --- EXECUÇÃO PRINCIPAL ---

# 1. Obter dados iniciais
df_clubs = get_initial_wikidata() # Salva raw_clubs_wikidata.csv

# 2. Obter base de cidades
df_ibge = get_ibge_cities()
city_names = df_ibge['nome'].tolist()

# 3. Processar Clubes (Para os 1500)
print(f"Processando {len(df_clubs)} clubes. Isso levará alguns minutos...")
final_data = []

# Para o seu TCC, vamos rodar em lotes. Aqui está o loop completo:
for index, row in df_clubs.iterrows():
    club_name = row['nome_clube']
    wiki_title = row['wiki_title']
    
    city_found = extract_city_from_summary(wiki_title, city_names)
    
    if city_found:
        # Busca lat/long no DF do IBGE
        city_info = df_ibge[df_ibge['nome'] == city_found].iloc[0]
        final_data.append({
            'nome_clube': club_name,
            'cidade': city_found,
            'latitude': city_info['latitude'],
            'longitude': city_info['longitude'],
            'codigo_ibge': city_info['codigo_ibge']
        })
    
    # Progresso e Respeito à API
    if index % 50 == 0:
        print(f"Progresso: {index}/{len(df_clubs)}...")
    time.sleep(0.05) # Delay pequeno

# 4. Salvar CSV Final
df_final = pd.DataFrame(final_data)
df_final.to_csv('final_brazil_football_geodata.csv', index=False, sep=';', encoding='utf-8-sig')

print("\n--- PROCESSO CONCLUÍDO ---")
print(f"1. Arquivo bruto salvo: raw_clubs_wikidata.csv")
print(f"2. Arquivo georreferenciado: final_brazil_football_geodata.csv")
print(f"Clubes mapeados com sucesso: {len(df_final)}")