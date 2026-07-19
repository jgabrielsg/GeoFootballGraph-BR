from playwright.sync_api import sync_playwright
import os
import time

os.makedirs("escudos_svg", exist_ok=True)

with sync_playwright() as p:
    # headless=False exibe o navegador e minimiza a detecção inicial por bots
    browser = p.chromium.launch(headless=False)
    context = browser.new_context()
    page = context.new_page()
    
    # Acessa a página para gerar o desafio do Cloudflare e registrar os cookies
    page.goto("https://football-logos.cc/brazil/")
    page.wait_for_selector("[data-logo-id]")
    
    # Extrai os nós do DOM
    cards = page.query_selector_all("[data-logo-id][data-svg-hash]")
    
    for card in cards:
        logo_id = card.get_attribute("data-logo-id")
        svg_hash = card.get_attribute("data-svg-hash")
        category = card.get_attribute("data-category-id") or "brazil"
        
        url = f"https://assets.football-logos.cc/logos/{category}/svg/{logo_id}.{svg_hash}.svg"
        
        # A API de requisição do contexto compartilha a autorização do navegador
        response = context.request.get(url)
        
        if response.status == 200:
            with open(f"escudos_svg/{logo_id}.svg", "wb") as f:
                f.write(response.body())
            print(f"Salvo: {logo_id}.svg")
        else:
            print(f"Erro {response.status} ao baixar {logo_id}")
            
        time.sleep(0.5) # Limitação de taxa (Rate limit) para evitar bloqueios por IP
        
    browser.close()