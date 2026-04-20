import requests
import pandas as pd
import time
import re

# --- CONFIGURAÇÕES ---
USER_AGENT = 'XXX/2.0 (xxx@fgv.edu.br)'
HEADERS = {'User-Agent': USER_AGENT}

def get_initial_wikidata():
    """
    Query avançada no Wikidata.
    Filtra por Instância de Clube de Futebol OU Propriedade Esporte = Futebol.
    Captura Sede, Coordenadas, Data de Fundação e Unidade Administrativa.
    """
    print("Iniciando Query avançada no Wikidata...")
    url = 'https://query.wikidata.org/sparql'
    
    # Query otimizada: 
    # - P31 wd:Q476028 (Clube de futebol) OU P641 wd:Q191 (Esporte: Futebol)
    # - P159 (Headquarters), P571 (Inception), P625 (Coords), P131 (Admin Unit)
    query = """
    SELECT ?clubLabel ?wikiTitle ?hqLabel ?coords ?inception ?adminUnitLabel WHERE {
      { ?club wdt:P31 wd:Q476028 . }
      UNION
      { ?club wdt:P641 wd:Q191 . }
      
      ?club wdt:P17 wd:Q155 . # No Brasil
      
      # Link Wikipedia
      ?article schema:about ?club;
               schema:isPartOf <https://pt.wikipedia.org/>;
               schema:name ?wikiTitle.
      
      OPTIONAL { ?club wdt:P159 ?hq . } # Sede
      OPTIONAL { ?club wdt:P625 ?coords . } # Coordenadas diretas
      OPTIONAL { ?club wdt:P571 ?inception . } # Fundação
      OPTIONAL { ?club wdt:P131 ?adminUnit . } # Estado/Região
               
      SERVICE wikibase:label { bd:serviceParam wikibase:language "pt". }
    }
    """
    try:
        r = requests.get(url, params={'format': 'json', 'query': query}, headers=HEADERS)
        r.raise_for_status()
        data = r.json()
        
        results = []
        for i in data['results']['bindings']:
            results.append({
                'nome_clube': i['clubLabel']['value'],
                'wiki_title': i['wikiTitle']['value'],
                'sede_wikidata': i.get('hqLabel', {}).get('value'),
                'coords_wikidata': i.get('coords', {}).get('value'),
                'inception': i.get('inception', {}).get('value'),
                'admin_unit': i.get('adminUnitLabel', {}).get('value')
            })
        return pd.DataFrame(results)
    except Exception as e:
        print(f"Erro na query: {e}")
        return pd.DataFrame()

def get_ibge_data():
    """Carrega municípios e estados do IBGE para normalização."""
    print("Carregando base de municípios e estados...")
    # Base de municípios com lat/long e código UF
    url_mun = "https://raw.githubusercontent.com/kelvins/municipios-brasileiros/main/csv/municipios.csv"
    url_est = "https://raw.githubusercontent.com/kelvins/municipios-brasileiros/main/csv/estados.csv"
    
    mun = pd.read_csv(url_mun)
    est = pd.read_csv(url_est)
    
    # Merge para ter o nome do estado no df de municípios
    return pd.merge(mun, est[['codigo_uf', 'nome', 'uf']], on='codigo_uf', suffixes=('_mun', '_estado'))

def extract_city_from_summary(wiki_title, city_list):
    """Fallback: Busca município no resumo da Wikipedia se o Wikidata falhar."""
    api_url = f"https://pt.wikipedia.org/api/rest_v1/page/summary/{wiki_title.replace(' ', '_')}"
    try:
        response = requests.get(api_url, headers=HEADERS, timeout=5)
        if response.status_code != 200: return None
        extract = response.json().get('extract', '')
        for city in city_list:
            if city in extract[:400]:
                return city
    except:
        pass
    return None

# --- EXECUÇÃO ---

df_wikidata = get_initial_wikidata()
df_ibge = get_ibge_data()
city_names = df_ibge['nome_mun'].tolist()

final_data = []

print(f"Processando {len(df_wikidata)} entidades...")

for index, row in df_wikidata.iterrows():
    # 1. Definir a Cidade (Prioridade: Sede Wikidata > Wikipedia Summary)
    city_candidate = row['sede_wikidata']
    if not city_candidate or city_candidate not in city_names:
        city_candidate = extract_city_from_summary(row['wiki_title'], city_names)
    
    if city_candidate and city_candidate in city_names:
        # Busca informações no IBGE
        # Nota: Se houver cidades homônimas, o admin_unit (P131) ajudaria a desempatar, 
        # mas aqui pegamos a primeira ocorrência para simplificar.
        info = df_ibge[df_ibge['nome_mun'] == city_candidate].iloc[0]
        
        # 2. Definir Coordenadas (Prioridade: Coords Diretas Wikidata > Centro da Cidade IBGE)
        lat, lon = info['latitude'], info['longitude']
        if row['coords_wikidata']:
            match = re.search(r'Point\(([-\d.]+) ([-\d.]+)\)', row['coords_wikidata'])
            if match:
                lon, lat = match.groups() # Wikidata inverte (Long, Lat)

        final_data.append({
            'nome_clube': row['nome_clube'],
            'estado': info['nome_estado'],
            'uf': info['uf'],
            'cidade': city_candidate,
            'latitude': lat,
            'longitude': lon,
            'inception': row['inception'],
            'codigo_ibge': info['codigo_ibge']
        })

    if index % 100 == 0: print(f"Progresso: {index}/{len(df_wikidata)}...")

# Salvar
df_final = pd.DataFrame(final_data).drop_duplicates(subset=['nome_clube', 'cidade'])
df_final.to_csv('final_brazil_football_geodata.csv', index=False, sep=';', encoding='utf-8-sig')

print(f"\nConcluído! {len(df_final)} clubes mapeados com sucesso.")