import os
import requests

API_KEY = os.getenv("API_FOOTBALL_KEY")
BASE_URL = "https://v3.football.api-sports.io"

# Busca o ID do time pelo nome
def get_team_id(team_name):
    url = f"{BASE_URL}/teams?search={team_name}"
    headers = {"Authorization": f"Bearer {API_KEY}"}
    data = requests.get(url, headers=headers).json()
    teams = data.get("response", [])
    if not teams:
        return None
    return teams[0]["team"]["id"]

# Pega últimos jogos do time
def get_last_fixtures(team_id, limit=5):
    url = f"{BASE_URL}/fixtures?team={team_id}&last={limit}"
    headers = {"Authorization": f"Bearer {API_KEY}"}
    data = requests.get(url, headers=headers).json()
    return data.get("response", [])

# Exemplo de uso
team_name = "Tottenham"
team_id = get_team_id(team_name)
fixtures = get_last_fixtures(team_id, 5)
print(fixtures)  # Lista dos últimos 5 jogos

