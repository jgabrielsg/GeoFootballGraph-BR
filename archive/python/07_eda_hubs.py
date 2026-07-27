import json

# Carrega o arquivo JSON com os dados das cidades e aeroportos
with open('outputs/svelte_data/city_hubs.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# Dicionário para armazenar as cidades por faixa de distância
faixas = {
    "menos de 100 km": [],
    "entre 100 e 200 km": [],
    "+200 km": [],
    "+300 km": [],
    "+400 km": []
}

# Classifica cada cidade com base em 'dist_ate_aero_km'
for cidade, info in data.items():
    dist = info.get("dist_ate_aero_km", 0)
    
    if dist < 100:
        faixas["menos de 100 km"].append((cidade, dist))
    elif 100 <= dist < 200:
        faixas["entre 100 e 200 km"].append((cidade, dist))
    
    if dist >= 200:
        faixas["+200 km"].append((cidade, dist))
    if dist >= 300:
        faixas["+300 km"].append((cidade, dist))
    if dist >= 400:
        faixas["+400 km"].append((cidade, dist))

# Exibe a contagem e exemplos para cada categoria
for faixa, itens in faixas.items():
    print(f"=== {faixa}: {len(itens)} cidades ===")
    for cidade, dist in itens[:5]:  # Mostra até 5 exemplos por categoria
        print(f"  - {cidade}: {dist} km")
    if len(itens) > 5:
        print(f"  ... e mais {len(itens) - 5} cidades.\n")
    else:
        print()