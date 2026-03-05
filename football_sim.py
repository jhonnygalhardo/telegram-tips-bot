import os
import requests
from datetime import datetime
import random
from collections import Counter
from math import exp
from typing import Optional, Dict, List

API_KEY = os.getenv("API_FOOTBALL_KEY")
if not API_KEY:
    raise ValueError("API_FOOTBALL_KEY não encontrada!")

BASE_URL = "https://v3.football.api-sports.io"
HEADERS = {"x-apisports-key": API_KEY}

def api_get(endpoint: str, params=None, timeout=12) -> list:
    try:
        url = f"{BASE_URL}/{endpoint}"
        response = requests.get(url, headers=HEADERS, params=params, timeout=timeout)
        response.raise_for_status()
        return response.json().get("response", [])
    except requests.RequestException as e:
        print(f"Erro na API {endpoint}: {e}")
        return []

def get_team_id(team_name: str) -> Optional[int]:
    data = api_get("teams", {"search": team_name})
    if data:
        team = data[0]["team"]
        print(f"Encontrado: {team['name']} (ID: {team['id']})")
        return team["id"]
    print(f"Time '{team_name}' não encontrado.")
    return None

def get_last_fixtures(team_id: int, limit=6) -> list:
    return api_get("fixtures", {"team": team_id, "last": limit, "timezone": "America/Sao_Paulo"})

def get_fixture_stats(fixture_id: int) -> Dict:
    stats = api_get(f"fixtures/statistics?fixture={fixture_id}")
    if not stats or len(stats) != 2:
        return {}
    
    team_stats = {}
    for s in stats:
        team_id = s["team"]["id"]
        stats_dict = {stat["type"]: stat["value"] for stat in s["statistics"]}
        team_stats[team_id] = {
            "Shots on Goal": stats_dict.get("Shots on Goal", 0),
            "Total Shots": stats_dict.get("Total Shots", 0),
            "Possession": stats_dict.get("% Ball Possession", "0%"),
            "xG": float(stats_dict.get("Expected Goals", 0)) if "Expected Goals" in stats_dict else None
        }
    return team_stats

def extract_recent_stats(team_id: int, fixtures: list) -> Dict:
    scored = conceded = xg_scored = xg_conceded = matches = 0
    form = []

    for fix in fixtures:
        if fix["fixture"]["status"]["short"] not in ["FT", "AET", "PEN"]:
            continue
        home_id = fix["teams"]["home"]["id"]
        away_id = fix["teams"]["away"]["id"]
        goals_home = fix["goals"]["home"] or 0
        goals_away = fix["goals"]["away"] or 0
        stats = get_fixture_stats(fix["fixture"]["id"])

        if team_id == home_id:
            scored += goals_home
            conceded += goals_away
            xg = stats.get(home_id, {}).get("xG")
            if xg is not None:
                xg_scored += xg
                xg_conceded += stats.get(away_id, {}).get("xG", 0)
            result = 'W' if goals_home > goals_away else 'D' if goals_home == goals_away else 'L'
        else:
            scored += goals_away
            conceded += goals_home
            xg = stats.get(away_id, {}).get("xG")
            if xg is not None:
                xg_scored += xg
                xg_conceded += stats.get(home_id, {}).get("xG", 0)
            result = 'W' if goals_away > goals_home else 'D' if goals_away == goals_home else 'L'

        form.append(result)
        matches += 1

    if matches == 0:
        return {"error": "Nenhum jogo concluído encontrado"}

    avg_scored = scored / matches
    avg_conceded = conceded / matches
    avg_xg_scored = xg_scored / matches if xg_scored > 0 else avg_scored
    avg_xg_conceded = xg_conceded / matches if xg_conceded > 0 else avg_conceded

    return {
        "matches": matches,
        "avg_goals_scored": round(avg_scored, 2),
        "avg_goals_conceded": round(avg_conceded, 2),
        "avg_xg_scored": round(avg_xg_scored, 2),
        "avg_xg_conceded": round(avg_xg_conceded, 2),
        "form": "".join(form[-5:])[::-1]  # últimos 5, mais recente primeiro
    }

def get_h2h(team1_id: int, team2_id: int, limit=6) -> List[str]:
    fixtures = api_get("fixtures/headtohead", {"team1": team1_id, "team2": team2_id})
    h2h = []
    for fix in fixtures[:limit]:
        if fix["fixture"]["status"]["short"] not in ["FT", "AET", "PEN"]:
            continue
        home = fix["teams"]["home"]["name"]
        away = fix["teams"]["away"]["name"]
        score = f"{fix['goals']['home'] or 0}-{fix['goals']['away'] or 0}"
        date = fix["fixture"]["date"][:10]
        h2h.append(f"{home} {score} {away} ({date})")
    return h2h

def poisson_sim(lambda_home: float, lambda_away: float, n=20000) -> Dict:
    home_goals = [random.poisson(lambda_home) for _ in range(n)]
    away_goals = [random.poisson(lambda_away) for _ in range(n)]
    most_common = Counter(zip(home_goals, away_goals)).most_common(1)[0][0]
    home_w = sum(h > a for h, a in zip(home_goals, away_goals)) / n
    draw = sum(h == a for h, a in zip(home_goals, away_goals)) / n
    away_w = 1 - home_w - draw
    return {
        "most_probable": f"{most_common[0]}-{most_common[1]}",
        "home_win": round(home_w * 100, 1),
        "draw": round(draw * 100, 1),
        "away_win": round(away_w * 100, 1)
    }

def simulate_match(home_name: str, away_name: str) -> str:
    lines = [f"⚽ Simulação: **{home_name} (casa)** vs **{away_name} (fora)**\n"]

    home_id = get_team_id(home_name)
    away_id = get_team_id(away_name)
    if not home_id or not away_id:
        return "Não foi possível encontrar um ou ambos os times. Verifique os nomes."

    fixtures_home = get_last_fixtures(home_id)
    fixtures_away = get_last_fixtures(away_id)

    stats_home = extract_recent_stats(home_id, fixtures_home)
    stats_away = extract_recent_stats(away_id, fixtures_away)

    if "error" in stats_home:
        return f"Erro ao obter estatísticas do {home_name}: {stats_home['error']}"
    if "error" in stats_away:
        return f"Erro ao obter estatísticas do {away_name}: {stats_away['error']}"

    lines.append(f"Forma recente (últimos 5):")
    lines.append(f"  {home_name}: {stats_home['form']}  |  {stats_home['avg_goals_scored']} / {stats_home['avg_goals_conceded']} gols (xG {stats_home['avg_xg_scored']}/{stats_home['avg_xg_conceded']})")
    lines.append(f"  {away_name}: {stats_away['form']}  |  {stats_away['avg_goals_scored']} / {stats_away['avg_goals_conceded']} gols (xG {stats_away['avg_xg_scored']}/{stats_away['avg_xg_conceded']})\n")

    lambda_home = (stats_home["avg_xg_scored"] + stats_away["avg_xg_conceded"]) / 2 + 0.3
    lambda_away = (stats_away["avg_xg_scored"] + stats_home["avg_xg_conceded"]) / 2 - 0.3

    lines.append(f"Lambda estimado (xG + vantagem casa):")
    lines.append(f"  {home_name}: {lambda_home:.2f}")
    lines.append(f"  {away_name}: {lambda_away:.2f}\n")

    sim = poisson_sim(lambda_home, lambda_away)

    lines.append("**Probabilidades (Poisson 20.000 simulações)**")
    lines.append(f"  Placar mais provável: **{sim['most_probable']}**")
    lines.append(f"  {home_name} vence: **{sim['home_win']}%**")
    lines.append(f"  Empate: **{sim['draw']}%**")
    lines.append(f"  {away_name} vence: **{sim['away_win']}%**\n")

    h2h = get_h2h(home_id, away_id)
    if h2h:
        lines.append("**Últimos confrontos diretos**")
        for match in h2h:
            lines.append(f"  - {match}")
    else:
        lines.append("Nenhum confronto direto recente encontrado.")

    return "\n".join(lines)