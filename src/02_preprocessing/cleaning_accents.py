import pandas as pd
import unicodedata
import re

# --- CONFIGURATION ---
INPUT_FILE = 'all_games.csv'
OUTPUT_FILE = 'all_games_clean_final.csv'

def slugify(text):
    """Converts names to a standard slug to identify duplicates (e.g., Camboriu == Camboriú)"""
    if pd.isna(text): return ""
    text = str(text).lower().strip()
    text = unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode('utf-8')
    text = re.sub(r'[^a-z0-9_]+', '_', text)
    return re.sub(r'_+', '_', text).strip('_')

def main():
    print("="*60)
    print("UNIFICANDO ENTIDADES: REMOVENDO DUPLICATAS DE ACENTUAÇÃO")
    print("="*60)

    # 1. LOAD DATA
    df = pd.read_csv(INPUT_FILE, sep=';', encoding='utf-8-sig')

    # 2. CREATE CANONICAL MAPPING
    # Pegamos todos os nomes únicos e seus estados
    all_names = pd.concat([
        df[['mandante', 'mandante_estado']].rename(columns={'mandante': 'nome', 'mandante_estado': 'estado'}),
        df[['visitante', 'visitante_estado']].rename(columns={'visitante': 'nome', 'visitante_estado': 'estado'})
    ]).drop_duplicates()

    # Criamos uma chave de identificação (slug + estado)
    all_names['slug_key'] = all_names['nome'].apply(slugify) + "_" + all_names['estado'].apply(slugify)

    # Elegemos o nome "mais completo" (com acento) para ser o representante do slug
    # Ordenamos para que nomes com caracteres especiais (acentos) tenham prioridade ou apenas pegamos o primeiro
    canonical_map = all_names.sort_values(by='nome', ascending=False).groupby('slug_key')['nome'].first().to_dict()

    # 3. APPLY UNIFICATION
    print("[PROCESS] Aplicando nomes canônicos...")
    
    def unify_name(name, state):
        key = slugify(name) + "_" + slugify(state)
        return canonical_map.get(key, name)

    # Corrigimos mandantes e visitantes
    df['mandante'] = df.apply(lambda x: unify_name(x['mandante'], x['mandante_estado']), axis=1)
    df['visitante'] = df.apply(lambda x: unify_name(x['visitante'], x['visitante_estado']), axis=1)

    # 4. SAVE CLEAN DATASET
    df.to_csv(OUTPUT_FILE, index=False, sep=';', encoding='utf-8-sig')
    
    print(f"[SUCCESS] Dataset unificado salvo em: {OUTPUT_FILE}")
    print(f"Exemplo de correção: Camboriu -> {unify_name('Camboriu', 'santa-catarina')}")
    print("="*60)

if __name__ == "__main__":
    main()