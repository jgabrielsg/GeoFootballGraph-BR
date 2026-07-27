import os
import json
import re

# --- CONFIGURAÇÕES ---
LEAGUES_INIT_FILE = r'outputs\svelte_data\leagues_init.json'
OUTPUT_FILE = r'outputs\svelte_data\mapping_serie_d_96.json'

# Lista bruta dos 96 times mapeados por Estado (Slug)
TEAMS_CBF_D_2026 = [
    ("GALVEZ", "acre"), ("HUMAITÁ", "acre"), ("INDEPENDÊNCIA", "acre"),
    ("ASA", "alagoas"), ("CSE", "alagoas"), ("CSA", "alagoas"),
    ("ORATÓRIO", "amapa"), ("TREM", "amapa"),
    ("MANAUS", "amazonas"), ("MANAUARA", "amazonas"), ("NACIONAL", "amazonas"),
    ("ATLÉTICO", "bahia"), ("JACUIPENSE", "bahia"), ("JUAZEIRENSE", "bahia"), ("PORTO", "bahia"),
    ("ATLÉTICO CEARENSE", "ceara"), ("FERROVIÁRIO", "ceara"), ("IGUATU", "ceara"), ("MARACANÃ", "ceara"), ("TIROL", "ceara"),
    ("BRASILIENSE", "distrito_federal"), ("CAPITAL CF", "distrito_federal"), ("CEILÂNDIA", "distrito_federal"), ("GAMA", "distrito_federal"),
    ("REAL NOROESTE", "espirito_santo"), ("RIO BRANCO", "espirito_santo"), ("VITÓRIA", "espirito_santo"),
    ("ABECAT OUVIDORENSE", "goias"), ("APARECIDENSE", "goias"), ("CRAC", "goias"), ("GOIATUBA", "goias"), ("INHUMAS", "goias"),
    ("IAPE", "maranhao"), ("IMPERATRIZ", "maranhao"), ("MOTO CLUB", "maranhao"), ("SAMPAIO CORRÊA", "maranhao"),
    ("LUVERDENSE", "mato_grosso"), ("MIXTO", "mato_grosso"), ("CEOV OPERÁRIO", "mato_grosso"), ("PRIMAVERA", "mato_grosso"), ("UNIÃO RONDONÓPOLIS", "mato_grosso"),
    ("OPERÁRIO", "mato_grosso_do_sul"), ("IVINHEMA", "mato_grosso_do_sul"), 
    ("BETIM FUTEBOL", "minas_gerais"), ("DEMOCRATA", "minas_gerais"), ("POUSO ALEGRE", "minas_gerais"), ("TOMBENSE", "minas_gerais"), ("UBERLÂNDIA", "minas_gerais"),
    ("AGUIA DE MARABA", "para"), ("TUNA LUSO", "para"),
    ("SERRA BRANCA", "paraiba"), ("SOUSA", "paraiba"), ("TREZE", "paraiba"),
    ("AZURIZ FUTEBOL", "parana"), ("CIANORTE", "parana"), ("CASCAVEL", "parana"), ("SÃO JOSEENSE", "parana"),
    ("CENTRAL", "pernambuco"), ("DECISÃO", "pernambuco"), ("MAGUARY", "pernambuco"), ("RETRÔ", "pernambuco"),
    ("ALTOS", "piaui"), ("FLUMINENSE", "piaui"), ("PARNAHYBA", "piaui"), ("PIAUÍ", "piaui"),
    ("AMERICA", "rio_de_janeiro"), ("MADUREIRA", "rio_de_janeiro"), ("MARICÁ", "rio_de_janeiro"), ("NOVA IGUAÇU", "rio_de_janeiro"), ("PORTUGUESA", "rio_de_janeiro"), ("SAMPAIO CORRÊA", "rio_de_janeiro"),
    ("ABC", "rio_grande_do_norte"), ("AMÉRICA", "rio_grande_do_norte"), ("LAGUNA", "rio_grande_do_norte"),
    ("BRASIL", "rio_grande_do_sul"), ("GUARANY DE BAGÉ", "rio_grande_do_sul"), ("SÃO JOSÉ", "rio_grande_do_sul"), ("SÃO LUIZ", "rio_grande_do_sul"),
    ("GUAPORÉ", "rondonia"), ("GAZIN PORTO VELHO", "rondonia"),
    ("GAS", "roraima"), ("MONTE RORAIMA", "roraima"), ("SÃO RAIMUNDO", "roraima"),
    ("BLUMENAU", "santa_catarina"), ("JOINVILLE", "santa_catarina"), ("MARCÍLIO DIAS", "santa_catarina"), ("SANTA CATARINA", "santa_catarina"),
    ("ÁGUA SANTA", "sao_paulo"), ("NOROESTE", "sao_paulo"), ("PORTUGUESA", "sao_paulo"), ("VELO CLUBE", "sao_paulo"), ("XV DE PIRACICABA", "sao_paulo"),
    ("LAGARTO", "sergipe"), ("SERGIPE", "sergipe"),
    ("ARAGUAÍNA", "tocantins"), ("TOCANTINÓPOLIS", "tocantins")
]

def clean_text(text):
    """Remove caracteres especiais para facilitar o match."""
    return re.sub(r'[^A-Z0-9]', '', str(text).upper())

def main():
    print("Iniciando varredura dos 96 times da Série D...")

    if not os.path.exists(LEAGUES_INIT_FILE):
        print(f"Erro: Arquivo {LEAGUES_INIT_FILE} não encontrado.")
        return

    with open(LEAGUES_INIT_FILE, 'r', encoding='utf-8') as f:
        leagues = json.load(f)

    # 1. Achatar o JSON para um dicionário reverso: "CLUBE/estado" -> "Liga"
    team_to_league = {}
    for division, clusters in leagues.items():
        if isinstance(clusters, dict):
            for cluster_name, teams in clusters.items():
                for t in teams:
                    team_to_league[t] = f"{division} - {cluster_name}"
        else:
            for t in clusters:
                team_to_league[t] = division

    # 2. Processar a busca dos 96 times
    mapped_results = []
    nao_encontrados = []

    for raw_name, state_slug in TEAMS_CBF_D_2026:
        clean_target = clean_text(raw_name)
        found = False
        
        # Filtra os times do JSON que pertencem ao mesmo estado para otimizar a busca
        teams_in_state = {k: v for k, v in team_to_league.items() if k.endswith(f"/{state_slug}")}
        
        for json_id, league_val in teams_in_state.items():
            json_name = json_id.split('/')[0]
            clean_json = clean_text(json_name)
            
            # Lógica de match (Exato ou Contido)
            if clean_target == clean_json:
                mapped_results.append({
                    "cbf_name": raw_name,
                    "state": state_slug,
                    "json_id": json_id,
                    "proposed_league": league_val
                })
                found = True
                break
                
        if not found:
            nao_encontrados.append(f"{raw_name}/{state_slug}")

    # 3. Exibir Resumo no Terminal
    print("\n--- RESUMO DO MAPEAMENTO ---")
    print(f"Times Encontrados e Alocados: {len(mapped_results)} de 96")
    
    if nao_encontrados:
        print(f"\nTimes não encontrados no JSON (verifique nomes/estados):")
        for t in nao_encontrados:
            print(f"- {t}")

    # 4. Agrupar resultados para o frontend (SvelteKit)
    output_data = {
        "metadata": {
            "total_analisado": len(TEAMS_CBF_D_2026),
            "total_alocado": len(mapped_results)
        },
        "times": mapped_results
    }

    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)

    print(f"\n[SUCESSO] JSON de mapeamento da Série D gerado em: {OUTPUT_FILE}")

if __name__ == "__main__":
    main()