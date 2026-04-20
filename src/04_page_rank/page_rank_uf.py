import pandas as pd

# 1. Ler o CSV
df = pd.read_csv('final_football_pagerank_unique.csv', sep=';', encoding='utf-8-sig')

# 2. Separar clube e UF
df[['clube', 'uf']] = df['clube_uf'].str.split('/', expand=True)

# 3. (opcional) capitalizar nome do clube
df['clube'] = df['clube'].str.title()

# 4. Reorganizar colunas
df = df[['clube', 'uf', 'pagerank_score']]

# 5. Salvar novo CSV
df.to_csv('final_football_pagerank.csv', sep=';', index=False, encoding='utf-8-sig')

print("[OK] Novo CSV gerado: final_football_pagerank.csv")