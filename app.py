import os
import json
from flask import Flask, render_template, abort
from datetime import datetime

app = Flask(__name__)

DATA_DIR = 'data'  # pasta onde estão os JSONs

@app.template_filter('format_date')
def format_date_filter(date_str):
    if not date_str:
        return "N/A"
    try:
        date_obj = datetime.strptime(date_str, '%Y-%m-%d')
        return date_obj.strftime('%d-%m-%Y')
    except (ValueError, TypeError):
        return date_str

def load_players():
    players = {}
    for filename in os.listdir(DATA_DIR):
        if filename.startswith('player_') and filename.endswith('.json'):
            path = os.path.join(DATA_DIR, filename)
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                player_id = filename.split('_')[1].replace('.json', '')
                player_name = data['player']['name']
                players[player_id] = player_name
    return players

def process_player_data(player_data):
    """Processa os dados do jogador mantendo os existentes"""
    # Formata a data de nascimento
    birth_date_str = player_data['player']['birth'].get('date')
    player_data['player']['birth']['formatted_date'] = format_date_filter(birth_date_str)
    
    # Mantém os dados existentes de partidas
    player_data.setdefault('match_today_tomorrow', None)
    player_data.setdefault('next_opponent_stats', None)
    
    return player_data

@app.route('/')
def home():
    players = load_players()
    return render_template('index.html', players=players)

@app.route('/player/<player_id>')
def player_detail(player_id):
    json_path = os.path.join(DATA_DIR, f'player_{player_id}.json')
    if not os.path.exists(json_path):
        abort(404, description="Player data not found.")
    
    with open(json_path, 'r', encoding='utf-8') as f:
        player_data = json.load(f)
    
    player_data = process_player_data(player_data)
    
    return render_template('player.html', player=player_data)

from flask import send_from_directory

@app.route('/logo.png')
def serve_logo():
    return send_from_directory('templates', 'logo.png')

@app.route('/bg.png')
def serve_bg():
    return send_from_directory('templates', 'bg.png')

if __name__ == '__main__':
    app.run(debug=True)