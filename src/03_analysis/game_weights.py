import pandas as pd

# --- CONFIGURATION ---
INPUT_FILE = 'all_games_final_v2_corrigido.csv'
OUTPUT_FILE = 'all_games.csv'

def calculate_base_weight(row):
    """
    Determines the match importance based on tournament level and division.
    This serves as the total 'prestige pot' available for transfer.
    """
    # Using 'id_torneio' to distinguish National vs others
    tourney_type = str(row['estado']).lower()
    div = int(row['divisao'])
    
    # NATIONAL TOURNAMENTS
    if tourney_type == 'nacional':
        if div == 0: return 20  # Copa do Brasil
        if div == 1: return 20  # Serie A
        if div == 2: return 10  # Serie B
        if div == 3: return 5   # Serie C
        if div == 4: return 3   # Serie D
        
    # STATE / REGIONAL TOURNAMENTS
    else:
        if div == 1: return 3
        if div == 2: return 2
        if div in [3, 4, 5]: return 1
        if div == 0: return 1   # State Cups / Federation Cups
        
    return 1

def main():
    """
    Generates the final dataset with prestige flow weights for PageRank.
    Logic: 
    - Win: 100% flow from loser to winner.
    - Draw: 50% bidirectional flow.
    """
    print("="*60)
    print("PAGE RANK WEIGHTING: DRAW LOGIC INTEGRATION")
    print("="*60)

    # 1. LOAD DATA
    df = pd.read_csv(INPUT_FILE, sep=';', encoding='utf-8-sig')

    # 2. CALCULATE BASE IMPORTANCE
    print("[PROCESS] Calculating base match importance...")
    df['peso_base'] = df.apply(calculate_base_weight, axis=1)

    # 3. CALCULATE PRESTIGE FLOW (WEIGHTS FOR EDGES)
    # fluxo_h: prestige flowing TO home team (comes from away)
    # fluxo_a: prestige flowing TO away team (comes from home)
    
    print("[PROCESS] Distributing prestige flow based on results...")
    
    # Home Win (H): prestige flows Away -> Home
    df.loc[df['resultado'] == 'H', 'fluxo_h'] = df['peso_base']
    df.loc[df['resultado'] == 'H', 'fluxo_a'] = 0

    # Away Win (A): prestige flows Home -> Away
    df.loc[df['resultado'] == 'A', 'fluxo_h'] = 0
    df.loc[df['resultado'] == 'A', 'fluxo_a'] = df['peso_base']

    # Draw (D): 50/50 bidirectional exchange
    df.loc[df['resultado'] == 'D', 'fluxo_h'] = df['peso_base'] * 0.5
    df.loc[df['resultado'] == 'D', 'fluxo_a'] = df['peso_base'] * 0.5

    # 4. CLEANUP AND EXPORT
    # Dropping 'peso_importancia' if it exists to keep the structure clean
    if 'peso_importancia' in df.columns:
        df = df.drop(columns=["peso_importancia"])
    
    # Keeping 'peso_base' for analytical reference
    df.to_csv(OUTPUT_FILE, index=False, sep=';', encoding='utf-8-sig')

    # 5. QUICK VALIDATION REPORT
    print(f"\n[SUMMARY] Output saved: {OUTPUT_FILE}")
    print(f"Sample - Draw distribution (D):\n{df[df['resultado'] == 'D'][['mandante', 'visitante', 'peso_base', 'fluxo_h', 'fluxo_a']].head(3)}")
    print("="*60)

if __name__ == "__main__":
    main()