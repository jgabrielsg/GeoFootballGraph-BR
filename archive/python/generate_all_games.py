import pandas as pd
import re
import unicodedata

INPUT_FILE = 'all_games_final.csv'
OUTPUT_FILE = 'all_games_final_v2.csv'

UF_MAP = {
    'AC': 'acre', 'AL': 'alagoas', 'AP': 'amapa', 'AM': 'amazonas', 
    'BA': 'bahia', 'CE': 'ceara', 'DF': 'distrito_federal', 'ES': 'espirito_santo', 
    'GO': 'goias', 'MA': 'maranhao', 'MT': 'mato_grosso', 'MS': 'mato_grosso_do_sul', 
    'MG': 'minas_gerais', 'PA': 'para', 'PB': 'paraiba', 'PR': 'parana', 
    'PE': 'pernambuco', 'PI': 'piaui', 'RJ': 'rio_de_janeiro', 'RN': 'rio_grande_do_norte', 
    'RS': 'rio_grande_do_sul', 'RO': 'rondonia', 'RR': 'roraima', 'SC': 'santa_catarina', 
    'SP': 'sao_paulo', 'SE': 'sergipe', 'TO': 'tocantins'
}

def slugify(text):
    if pd.isna(text): return ""
    text = str(text).lower().strip()
    text = unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode('utf-8')
    text = re.sub(r'[^a-z0-9_]+', '_', text)
    return re.sub(r'_+', '_', text).strip('_')

def clean_and_extract(name, league_state):
    """
    1. Extrai a sigla do estado se existir ( / RJ ou -SP).
    2. Limpa o nome de siglas (FC, EC, etc) e sufixos.
    3. Retorna (Nome Limpo, Estado Identificado).
    """
    if pd.isna(name): return "", league_state
    
    raw_name = str(name).upper().strip()
    identified_state = slugify(league_state)
    
    # Tenta achar ' / RJ' ou ' - / SP' ou '-RS'
    match_suffix = re.search(r'[- ]*/?\s*([A-Z]{2})$', raw_name)
    if match_suffix:
        sigla = match_suffix.group(1)
        if sigla in UF_MAP:
            identified_state = UF_MAP[sigla]
    
    clean_name = re.sub(r'\s*[-]*\s*/\s*[A-Z]{2}$', '', raw_name)
    clean_name = re.sub(r'-[A-Z]{2}$', '', clean_name)
    
    # Remove siglas administrativas (FC, EC, SC, etc)
    acronyms = [r'\bF\.?\s*C\.?\b', r'\bE\.?\s*C\.?\b', r'\bS\.?\s*C\.?\b', 
                r'\bS\.?\s*E\.?\b', r'\bA\.?\s*C\.?\b', r'\bA\.?\s*A\.?\b']
    for p in acronyms:
        clean_name = re.sub(p, '', clean_name)
    
    # Remove hifens ou espaços que sobraram no fim
    clean_name = re.sub(r'^\W+|\W+$', '', clean_name).strip()
    
    return clean_name, identified_state

def main():
    print("Iniciando processamento para v2...")
    df = pd.read_csv(INPUT_FILE, sep=';', encoding='utf-8-sig')
    
    new_data = []
    
    for _, row in df.iterrows():
        m_nome, m_est = clean_and_extract(row['mandante'], row['estado'])
        v_nome, v_est = clean_and_extract(row['visitante'], row['estado'])
        
        new_row = row.to_dict()
        new_row['mandante'] = m_nome
        new_row['visitante'] = v_nome
        new_row['mandante_estado'] = m_est
        new_row['visitante_estado'] = v_est
        
        new_data.append(new_row)
    
    df_v2 = pd.DataFrame(new_data)
    
    # Reorganizar colunas para facilitar leitura
    cols = ['estado', 'divisao', 'ano', 'data', 'mandante', 'mandante_estado', 
            'visitante', 'visitante_estado', 'placar', 'resultado', 'peso_importancia']
    cols += [c for c in df_v2.columns if c not in cols]
    
    df_v2[cols].to_csv(OUTPUT_FILE, index=False, sep=';', encoding='utf-8-sig')
    print(f"Sucesso! Gerado {OUTPUT_FILE}")
    print(f"Exemplo: Flamengo / RJ -> Nome: {df_v2.iloc[0]['mandante']} | Estado: {df_v2.iloc[0]['mandante_estado']}")

if __name__ == "__main__":
    main()