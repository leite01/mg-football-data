import requests
import argparse
from datetime import datetime, timedelta
import json
import os

parser = argparse.ArgumentParser(description='Consulta estatísticas de jogador.')
parser.add_argument('-player', type=int, required=True, help='ID do jogador')
parser.add_argument('-season', type=int, required=True, help='Temporada')
args = parser.parse_args()

api_key = "abf3dd77c070ae97adf7cbbac4dae856"
player_id = args.player
season = args.season

headers = {
    "x-apisports-key": api_key
}

# Nome do arquivo JSON para armazenar dados do jogador
json_filename = os.path.join("data", f"player_{player_id}.json")

# Se o arquivo existir e for recente (menos de 24h), carregar e usar
if os.path.exists(json_filename):
    mod_time = os.path.getmtime(json_filename)
    if (datetime.now().timestamp() - mod_time) < 24*3600:
        with open(json_filename, 'r', encoding='utf-8') as f:
            data_json = json.load(f)
        print(f"⚡ Usando dados em cache de {json_filename}")
        # Só mostrar uma mensagem e sair ou fazer algo com o JSON carregado
        # Você pode também retornar os dados aqui se for uma API
        exit()

# Caso contrário, faz a requisição e monta o JSON do zero

url = "https://v3.football.api-sports.io/players"
params = {
    "id": player_id,
    "season": season
}

response = requests.get(url, headers=headers, params=params)
if response.status_code != 200:
    print(f"❌ Erro {response.status_code}: {response.text}")
    exit()

data = response.json()
player = data['response'][0]['player']
stats_list = data['response'][0]['statistics']

# Dicionário principal que vai guardar todos os dados do jogador
output_data = {
    "player": {
        "name": player['name'],
        "firstname": player['firstname'],
        "lastname": player['lastname'],
        "birth": player['birth'],
        "age": player['age'],
        "nationality": player['nationality'],
        "height": player['height'],
        "weight": player['weight'],
        "photo": player['photo']
    },
    "statistics": [],
    "match_today_tomorrow": None,
    "next_opponent_stats": None
}

max_appearances = -1
player_team_id = None
player_team_name = ""

for stat in stats_list:
    appearances = stat['games'].get('appearences')
    if appearances is not None and appearances > max_appearances:
        max_appearances = appearances
        player_team_id = stat['team']['id']
        player_team_name = stat['team']['name']

    if appearances is None or appearances <= 0:
        continue

    league = stat['league']
    team = stat['team']
    games = stat['games']
    goals = stat['goals']
    passes = stat['passes']
    shots = stat['shots']
    dribbles = stat['dribbles']
    duels = stat['duels']
    tackles = stat['tackles']
    cards = stat['cards']
    fouls = stat['fouls']
    rating = games.get('rating')

    stat_entry = {
        "league": {
            "name": league['name'],
            "country": league['country'],
            "season": league['season']
        },
        "team": {
            "id": team['id'],
            "name": team['name']
        },
        "games": {
            "position": games['position'],
            "appearences": games['appearences'],
            "lineups": games['lineups'],
            "minutes": games['minutes'],
            "rating": float(rating) if rating else None
        },
        "goals": goals,
        "passes": passes,
        "shots": shots,
        "dribbles": dribbles,
        "duels": duels,
        "tackles": tackles,
        "cards": cards,
        "fouls": fouls
    }

    output_data["statistics"].append(stat_entry)

if player_team_id is None:
    print("❌ Não foi possível identificar o time principal do jogador com jogos > 0.")
    exit()

# Verificação de jogo hoje ou amanhã
dates = [datetime.today().strftime('%Y-%m-%d'),
         (datetime.today() + timedelta(days=1)).strftime('%Y-%m-%d')]

league_id = None
adversary_id = None
adversary_name = None
match_date = None

for date_check in dates:
    fixtures_url = "https://v3.football.api-sports.io/fixtures"
    fixtures_params = {
        "date": date_check
    }
    fixtures_response = requests.get(fixtures_url, headers=headers, params=fixtures_params)
    if fixtures_response.status_code != 200:
        continue

    fixtures_data = fixtures_response.json()
    fixtures = fixtures_data.get('response', [])

    for fixture in fixtures:
        teams = fixture.get('teams', {})
        home = teams.get('home', {})
        away = teams.get('away', {})

        if home.get('id') == player_team_id or away.get('id') == player_team_id:
            league = fixture.get('league', {})
            league_id = league.get('id')
            match_date = date_check
            if home.get('id') == player_team_id:
                adversary_id = away.get('id')
                adversary_name = away.get('name')
            else:
                adversary_id = home.get('id')
                adversary_name = home.get('name')

            output_data["match_today_tomorrow"] = {
                "date": match_date,
                "league_id": league_id,
                "player_team_id": player_team_id,
                "player_team_name": player_team_name,
                "adversary_id": adversary_id,
                "adversary_name": adversary_name
            }
            break
    if league_id is not None:
        break

if league_id is None:
    output_data["match_today_tomorrow"] = None

# Função para buscar estatísticas do adversário
def get_team_statistics(league_id, season, team_id):
    url_stats = "https://v3.football.api-sports.io/teams/statistics"
    params_stats = {
        "league": league_id,
        "season": season,
        "team": team_id
    }
    response_stats = requests.get(url_stats, headers=headers, params=params_stats)
    if response_stats.status_code != 200:
        return None

    data_stats = response_stats.json()
    stats = data_stats.get("response", {})
    return stats

if league_id is not None and adversary_id is not None:
    adversary_stats = get_team_statistics(league_id, season, adversary_id)
    if adversary_stats:
        output_data["next_opponent_stats"] = adversary_stats

# Salvar JSON no arquivo
os.makedirs("data", exist_ok=True)
with open(json_filename, 'w', encoding='utf-8') as f:
    json.dump(output_data, f, ensure_ascii=False, indent=4)

print(f"✅ Dados do jogador salvos em {json_filename}")
