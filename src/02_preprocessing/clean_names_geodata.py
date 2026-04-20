import pandas as pd
import re

# --- CONFIGURATION ---
INPUT_FILE = 'final_brazil_football_geodata.csv'
OUTPUT_FILE = 'final_brazil_football_geodata_v2.csv'

# Words that define the "administrative" part of the club
NOISE_WORDS = {
    'SPORT', 'CLUB', 'CLUBE', 'SOCIEDADE', 'ESPORTIVA', 'ESPORTE', 'ESPORTIVO', 
    'FUTEBOL', 'REGATAS', 'RECREAÇÃO', 'RECREATIVO', 'RECREATIVA', 'ASSOCIAÇÃO', 
    'NATAÇÃO', 'FOOT-BALL', 'FOOTBALL', 'DESPORTIVA', 'CULTURAL', 'RECREAÇAO', 
    'ASSOCIAÇÃO', 'DESPORTOS', 'DESPORTE', "DESPORTO", "ATLÉTICA", "FOOT", "BALL",
    "FOOT-BALL"
}

PREPOSITIONS = {'DE', 'DO', 'DOS', 'DA', 'DAS', "E"}

def smart_clean_name(name):
    """
    Implements the contextual cleaning logic:
    1. Standardize and tokenize.
    2. Mark noise words for removal.
    3. Remove prepositions ONLY if at least one neighbor was removed.
    """
    if pd.isna(name): return ""
    
    # Pre-cleaning: remove suffixes like -RS, -PE, -AC common in game data
    name = re.sub(r'-[A-Z]{2}$', '', str(name).upper())
    
    # Tokenize (split by space and remove punctuation)
    tokens = re.findall(r"[\w'-]+", name)
    
    # Step 1: Identify tokens to remove
    to_remove = [False] * len(tokens)
    for i, token in enumerate(tokens):
        if token in NOISE_WORDS:
            to_remove[i] = True
            
    # Step 2: Contextual logic for prepositions
    for i, token in enumerate(tokens):
        if token in PREPOSITIONS:
            # Check neighbors
            has_prev_removed = to_remove[i-1] if i > 0 else False
            has_next_removed = to_remove[i+1] if i < len(tokens)-1 else False
            
            # If at least one neighbor is a noise word being removed, remove the preposition
            if has_prev_removed or has_next_removed:
                to_remove[i] = True
                
    # Step 3: Rebuild string with remaining tokens
    clean_tokens = [t for i, t in enumerate(tokens) if not to_remove[i]]
    
    # Fallback: if we removed everything (unlikely), return original
    if not clean_tokens:
        return name
        
    return " ".join(clean_tokens)

def main():
    print("Loading geodata...")
    df = pd.read_csv(INPUT_FILE, sep=';', encoding='utf-8-sig')
    
    # Create the simplified name column
    print("Applying smart cleaning logic...")
    df['nome_simplificado'] = df['nome_clube'].apply(smart_clean_name)
    
    # Reorder columns to put simplified name at the beginning for easy check
    cols = ['nome_simplificado', 'nome_clube'] + [c for c in df.columns if c not in ['nome_simplificado', 'nome_clube']]
    df = df[cols]
    
    # Save the new version
    df.to_csv(OUTPUT_FILE, index=False, sep=';', encoding='utf-8-sig')
    
    print("\n--- SAMPLES OF CLEANING ---")
    for _, row in df.head(15).iterrows():
        print(f"Original: {row['nome_clube']} -> Simplified: {row['nome_simplificado']}")
        
    print(f"\nFile saved as {OUTPUT_FILE}")

if __name__ == "__main__":
    main()