import os
import time
import json
import pandas as pd
import google.generativeai as genai
from dotenv import load_dotenv
import typing_extensions as typing

# --- CONFIGURAÇÃO DE AMBIENTE E API ---
load_dotenv()
API_KEY = os.getenv("GOOGLE_KEY")

if not API_KEY:
    raise ValueError("Chave GOOGLE_KEY não encontrada no arquivo .env.")

genai.configure(api_key=API_KEY)
model = genai.GenerativeModel('models/gemini-3.1-flash-lite')

# --- DEFINIÇÃO DO SCHEMA DE SAÍDA (STRUCTURED OUTPUTS) ---
class TeamInfo(typing.TypedDict):
    clube_original: str
    clube_canonical: str
    cidade: str
    latitude: float
    longitude: float
    estadio: str

class TeamBatchResponse(typing.TypedDict):
    resultados: list[TeamInfo]

# --- ARQUIVOS ---
INPUT_FILE = r"data\02_processed\unique_teams_to_geocode.csv"
OUTPUT_FILE = r"data\02_processed\unique_teams_to_geocode_2.csv"

def process_batch(batch_df):
    """
    Envia um lote de clubes para a LLM e retorna os dados geográficos e de identidade.
    """
    # Prepara a string de entrada com os dados do lote
    lista_clubes = []
    for _, row in batch_df.iterrows():
        lista_clubes.append(f"- Estado: {row['estado']} | Clube Original: {row['clube']}")
    
    input_text = "\n".join(lista_clubes)
    
    prompt = f"""
    Atue como um engenheiro de dados especialista em estatísticas e geografia do futebol brasileiro.
    Analise a lista de clubes de futebol abaixo e preencha as informações solicitadas.
    
    REGRAS DE EXTRAÇÃO:
    1. 'clube_original': Copie exatamente o nome fornecido na entrada.
    2. 'clube_canonical': Qual o nome oficial MAIS RECENTE do clube? Retorne o mesmo nome do original, EXCETO se o clube mudou oficialmente de nome, fundiu-se ou se a grafia original for um apelido desatualizado (Ex: "GE Brasil" -> "Brasil de Pelotas", "Atlético Paranaense" -> "Athletico Paranaense", ou exemplo de "Seu nome foi alterado de 'Oeste Futebol Clube' para 'Osasco Sporting'", e se você receber "Oeste" no nome, colocar "Osasco Sporting" no canonical).
    3. 'cidade': A cidade sede atual e principal do clube.
    4. 'latitude' e 'longitude': As coordenadas exatas (em decimal) da cidade do time.
    5. 'estadio': O nome do estádio principal onde o clube manda seus jogos. Se não possuir estádio próprio, informe o estádio público/municipal que costuma utilizar. Se desconhecido, deixe em branco.

    LISTA DE CLUBES:
    {input_text}
    """
    
    try:
        response = model.generate_content(
            prompt,
            generation_config=genai.GenerationConfig(
                response_mime_type="application/json",
                response_schema=TeamBatchResponse,
                temperature=0.1,
            ),
        )
        return json.loads(response.text).get('resultados', [])
    
    except Exception as e:
        print(f"[ERRO na API] Falha ao processar o lote: {e}")
        return None

def main():
    print("="*60)
    print("INICIANDO GEOCODIFICAÇÃO EM LOTES (RETOMADA SEGURA)")
    print("="*60)
    
    # Lógica de retomada: lê o output se existir; senão, lê o input
    if os.path.exists(OUTPUT_FILE):
        print(f"Lendo progresso salvo de: {OUTPUT_FILE}")
        df = pd.read_csv(OUTPUT_FILE, sep=';', encoding='utf-8-sig')
    else:
        print(f"Iniciando do arquivo original: {INPUT_FILE}")
        df = pd.read_csv(INPUT_FILE, sep=';', encoding='utf-8-sig')
    
    # Garante que a coluna estadio exista
    if 'estadio' not in df.columns:
        df['estadio'] = ""
        
    BATCH_SIZE = 6
    
    # Verifica quais linhas AINDA não tem a cidade preenchida
    indices_pendentes = df[df['cidade'].isna() | (df['cidade'] == "")].index.tolist()
    
    print(f"Total de clubes pendentes: {len(indices_pendentes)}")
    
    for i in range(0, len(indices_pendentes), BATCH_SIZE):
        batch_indices = indices_pendentes[i:i + BATCH_SIZE]
        batch_df = df.loc[batch_indices]
        
        nomes_lote = ", ".join(batch_df['clube'].tolist())
        print(f"\nProcessando Lote [{i+1} a {min(i+BATCH_SIZE, len(indices_pendentes))}]: {nomes_lote}")
        
        resultados = process_batch(batch_df)
        
        if resultados:
            for item in resultados:
                # Extração segura usando .get()
                clube_orig = item.get('clube_original')
                if not clube_orig:
                    continue # Pula se a IA não devolveu nem o nome original
                
                mask = (df['clube'] == clube_orig) & (df.index.isin(batch_indices))
                
                if mask.any():
                    idx = df[mask].index[0]
                    # Substitui o KeyError pela extração segura (.get) com fallback
                    df.at[idx, 'clube_canonical'] = item.get('clube_canonical', df.at[idx, 'clube'])
                    df.at[idx, 'cidade'] = item.get('cidade', '')
                    df.at[idx, 'latitude'] = item.get('latitude', '')
                    df.at[idx, 'longitude'] = item.get('longitude', '')
                    df.at[idx, 'estadio'] = item.get('estadio', '')
            
            # Salvamento atômico
            df.to_csv(OUTPUT_FILE, index=False, sep=';', encoding='utf-8-sig')
            print("-> Salvo com sucesso.")
        else:
            print("-> Falha no lote. Aguardando 10 segundos para retentativa...")
            time.sleep(10)
            
        time.sleep(4)

    print("\n" + "="*60)
    print("PROCESSO CONCLUÍDO.")
    print("="*60)

if __name__ == "__main__":
    main()