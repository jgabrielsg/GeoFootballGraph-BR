import time
import json
import os
import random
import pandas as pd
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# CONFIGURAÇÃO
BASE_URL = "https://www.ogol.com.br/edicao/"
JSON_PATH = os.path.join("links", "ogol_games_links.json")
OUTPUT_PATH = os.path.join("data", "01_raw", "games", "jogos_estaduais_full5.csv")

def iniciar_driver():
    """
    Inicializa o undetected-chromedriver com perfil de usuário persistente.
    """
    options = uc.ChromeOptions()
    options.add_argument(r"--user-data-dir=C:\selenium_profile")
    options.add_argument(r"--profile-directory=Default")
    options.add_argument("--start-maximized")
    options.add_argument("--disable-blink-features=AutomationControlled")
    
    driver = uc.Chrome(options=options)
    return driver

def esperar_tabela(driver):
    """
    Aguarda o carregamento do elemento da tabela de jogos na página.
    """
    WebDriverWait(driver, 20).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "table.zztable"))
    )

def extrair_dados_da_pagina(driver, meta):
    """
    Faz o parsing das linhas da tabela HTML e retorna uma lista de dicionários com os jogos.
    """
    jogos_da_pagina = []
    
    try:
        rows = driver.find_elements(By.CSS_SELECTOR, "table.zztable tbody tr.parent")
    except Exception:
        return []

    for row in rows:
        try:
            data = row.find_element(By.CSS_SELECTOR, "td.date").text
            casa = row.find_element(By.CSS_SELECTOR, "td.home").text
            fora = row.find_element(By.CSS_SELECTOR, "td.away").text
            placar = row.find_element(By.CSS_SELECTOR, "td.result").text

            if "-" in placar and any(char.isdigit() for char in placar):
                jogos_da_pagina.append({
                    "estado": meta["estado"],
                    "divisao": meta["divisao"],
                    "ano": meta["ano"],
                    "data": data,
                    "mandante": casa,
                    "visitante": fora,
                    "placar": placar
                })
        except Exception:
            continue
            
    return jogos_da_pagina

def carregar_links():
    """
    Lê o arquivo JSON hierárquico e retorna o dicionário.
    """
    with open(JSON_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def main():
    """
    Executa o fluxo principal de scraping iterando sobre a hierarquia do JSON.
    """
    links_data = carregar_links()
    driver = iniciar_driver()
    todos_jogos = []

    try:
        # Acesso inicial para bypass manual/login
        driver.get("https://www.ogol.com.br")
        input("\nProceda com o login/CAPTCHA e pressione ENTER no console para continuar...")

        for estado_key, divisoes in links_data.items():
            for div_key, anos in divisoes.items():
                for ano, link_path in anos.items():
                    
                    # Lógica de Metadados
                    # Regionais: estado='regional', divisao=0
                    # Copas estaduais: divisao=0
                    meta = {
                        "estado": "regional" if estado_key == "regionais" else estado_key,
                        "divisao": 0 if (div_key == "copas" or estado_key == "regionais") else div_key,
                        "ano": ano
                    }

                    pagina_atual = 1
                    continuar_paginando = True
                    
                    while continuar_paginando:
                        url = f"{BASE_URL}{link_path}/calendario?page={pagina_atual}"
                        print(f"[INFO] {meta['estado']} | Div: {meta['divisao']} | Ano: {meta['ano']} | Pag: {pagina_atual}")
                        
                        driver.get(url)
                        
                        try:
                            esperar_tabela(driver)
                            rows = driver.find_elements(By.CSS_SELECTOR, "table.zztable tbody tr.parent")
                            rows_count = len(rows)
                            
                            jogos_encontrados = extrair_dados_da_pagina(driver, meta)
                            todos_jogos.extend(jogos_encontrados)
                            
                            # O Ogol exibe até 50 resultados por página no calendário
                            if rows_count < 50:
                                continuar_paginando = False
                            else:
                                pagina_atual += 1
                                time.sleep(random.uniform(2, 4))
                        
                        except Exception as e:
                            print(f"[ERRO] Falha no link {link_path}: {e}")
                            continuar_paginando = False

        # Persistência dos dados
        if todos_jogos:
            os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
            df = pd.DataFrame(todos_jogos)
            df.to_csv(OUTPUT_PATH, index=False, sep=";", encoding="utf-8-sig")
            print(f"\nProcesso concluído. Total de jogos salvos: {len(df)}")
        else:
            print("\nNenhum dado foi capturado.")

    finally:
        driver.quit()

if __name__ == "__main__":
    main()