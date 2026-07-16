import pandas as pd
import os

# --- CONFIGURATION ---
INPUT_FILE = r'data\01_raw\jogos_serie_c_2026.csv'
OUTPUT_FILE = r'data\01_raw\jogos_serie_c_2026.csv' # Overwrites with clean data

# Strict mapping from any raw scraped name to our database (CLUBE, estado)
CLUB_CLEANING_MAP = {
    # Raw Name -> (Standardized Name, State Slug)
    'AMAZONAS SAF': ('AMAZONAS', 'amazonas'),
    'AMAZONAS': ('AMAZONAS', 'amazonas'),
    
    'ANÁPOLIS': ('ANÁPOLIS', 'goias'),
    
    'BARRA FUTEBOL CLUBE': ('BARRA', 'santa_catarina'),
    'BARRA': ('BARRA', 'santa_catarina'),
    
    'BOTAFOGO PB SAF': ('BOTAFOGO', 'paraiba'),
    'BOTAFOGO PB': ('BOTAFOGO', 'paraiba'),
    'BOTAFOGO-PB': ('BOTAFOGO', 'paraiba'),
    
    'BRUSQUE': ('BRUSQUE', 'santa_catarina'),
    
    'CAXIAS': ('CAXIAS', 'rio_grande_do_sul'),
    
    'CONFIANÇA S.A.F.': ('CONFIANÇA', 'sergipe'),
    'CONFIANÇA': ('CONFIANÇA', 'sergipe'),
    
    'FERROVIÁRIA': ('FERROVIÁRIA', 'sao_paulo'),
    
    'FIGUEIRENSE': ('FIGUEIRENSE', 'santa_catarina'),
    
    'FLORESTA': ('FLORESTA', 'ceara'),
    
    'GUARANI': ('GUARANI', 'sao_paulo'),
    
    'INTER DE LIMEIRA': ('INTER DE LIMEIRA', 'sao_paulo'),
    
    'ITABAIANA': ('ITABAIANA', 'sergipe'),
    
    'ITUANO FC': ('ITUANO', 'sao_paulo'),
    'ITUANO': ('ITUANO', 'sao_paulo'),
    
    'MARANHÃO': ('MARANHÃO', 'maranhao'),
    
    'MARINGÁ FC SAF': ('MARINGÁ', 'parana'),
    'MARINGÁ': ('MARINGÁ', 'parana'),
    
    'PAYSANDU': ('PAYSANDU', 'para'),
    
    'SANTA CRUZ': ('SANTA CRUZ', 'pernambuco'),
    
    'VOLTA REDONDA': ('VOLTA REDONDA', 'rio_de_janeiro'),
    
    'YPIRANGA': ('YPIRANGA', 'rio_grande_do_sul')
}

def clean_team(raw_name):
    """Normalize and maps raw team string to standardized name and state."""
    if pd.isna(raw_name):
        return None, None
    
    clean_key = str(raw_name).strip().upper()
    
    # Try direct hit in our map
    if clean_key in CLUB_CLEANING_MAP:
        return CLUB_CLEANING_MAP[clean_key]
        
    # Check for substring matches if name varies slightly
    for raw_mapped, (standard_name, state) in CLUB_CLEANING_MAP.items():
        if raw_mapped in clean_key or clean_key in raw_mapped:
            return standard_name, state
            
    return None, None

def main():
    print("="*70)
    print("CLEANING 2026 SERIE C SCHEDULE & MAPPING STATES")
    print("="*70)

    if not os.path.exists(INPUT_FILE):
        print(f"[ERROR] Input file not found: {INPUT_FILE}")
        return

    # Load raw games CSV
    df_raw = pd.read_csv(INPUT_FILE, sep=',', encoding='utf-8-sig')
    
    cleaned_rows = []
    unmapped_teams = set()

    for idx, row in df_raw.iterrows():
        rodada = row['rodada']
        mandante_raw = row['mandante']
        visitante_raw = row['visitante']
        
        m_name, m_state = clean_team(mandante_raw)
        v_name, v_state = clean_team(visitante_raw)
        
        # Log any missing mapping for safety
        if not m_name:
            unmapped_teams.add(mandante_raw)
        if not v_name:
            unmapped_teams.add(visitante_raw)
            
        cleaned_rows.append({
            'rodada': rodada,
            'mandante': m_name,
            'estado_m': m_state,
            'visitante': v_name,
            'estado_v': v_state
        })

    if unmapped_teams:
        print("[WARNING] Could not map the following raw team names:")
        for team in unmapped_teams:
            print(f" -> {team}")
        print("Please update the CLUB_CLEANING_MAP dictionary.\n")
        return

    # Create cleaned DataFrame
    df_clean = pd.DataFrame(cleaned_rows)
    
    # Export overwriting the old CSV file
    df_clean.to_csv(OUTPUT_FILE, index=False, sep=',', encoding='utf-8-sig')
    
    print(f"[SUCCESS] Cleaned schedule saved to: {OUTPUT_FILE}")
    print(f"[SUCCESS] Total processed matches: {len(df_clean)}")
    print("="*70)

    # Preview output
    print("\nPREVIEW:")
    print(df_clean.head(5).to_string(index=False))

if __name__ == "__main__":
    main()