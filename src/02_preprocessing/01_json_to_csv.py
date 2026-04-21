import json
import csv
import os
import re

# Path configurations
source_folder = 'data/01_raw/json'
output_file = 'data/01_raw/games/jogos_nacionais_full.csv'

# Division mapping as specified
division_map = {
    'Serie_A': '1',
    'Serie_B': '2',
    'Serie_C': '3',
    'Serie_D': '4',
    'CdB': '0'
}


def convert_date(date_str):
    """
    Convert date from DD/MM/YYYY format to YYYY-MM-DD.

    Args:
        date_str (str): Date string in DD/MM/YYYY format.

    Returns:
        str: Date string in YYYY-MM-DD format if valid, otherwise original string.
    """
    try:
        parts = date_str.split('/')
        if len(parts) == 3:
            return f"{parts[2]}-{parts[1]}-{parts[0]}"
    except Exception:
        pass
    return date_str


def process_files():
    """
    Process all JSON files in the source folder, extract match data,
    and return a unified list of games.

    Returns:
        list[dict]: List of processed match records.
    """
    all_games = []

    for filename in os.listdir(source_folder):
        if not filename.endswith('.json'):
            continue

        match = re.match(r'([a-zA-Z_]+)_(\d{4})_games\.json', filename)
        if not match:
            continue

        prefix = match.group(1)
        year = match.group(2)
        division = division_map.get(prefix, 'Desconhecido')

        full_path = os.path.join(source_folder, filename)

        with open(full_path, 'r', encoding='utf-8') as f:
            json_data = json.load(f)

            for _, info in json_data.items():
                date = convert_date(info.get('Date', ''))
                home = info.get('Home', '')
                away = info.get('Away', '')

                raw_result = info.get('Result', '')
                score = raw_result.replace(' X ', '-').strip()

                if '-' in score and any(char.isdigit() for char in score):
                    all_games.append({
                        'estado': 'nacional',
                        'divisao': division,
                        'ano': year,
                        'data': date,
                        'mandante': home,
                        'visitante': away,
                        'placar': score
                    })

    return all_games


def save_to_csv(games):
    """
    Save processed match data into a CSV file.

    Args:
        games (list[dict]): List of match records.
    """
    columns = ['estado', 'divisao', 'ano', 'data', 'mandante', 'visitante', 'placar']

    with open(output_file, 'w', newline='', encoding='utf-8-sig') as f_csv:
        writer = csv.DictWriter(f_csv, fieldnames=columns, delimiter=';')
        writer.writeheader()
        writer.writerows(games)


def main():
    games = process_files()
    save_to_csv(games)
    print(f"Processing completed! {len(games)} national matches unified into '{output_file}'.")


if __name__ == "__main__":
    main()