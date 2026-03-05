import os
import requests
from datetime import datetime
import random
from collections import Counter
from math import exp

API_KEY = os.getenv("API_FOOTBALL_KEY")
if not API_KEY:
    raise ValueError("API_FOOTBALL_KEY não encontrada!")

BASE_URL = "https://v3.football.api-sports.io"
HEADERS = {"x-apisports-key": API_KEY}

def api_get(endpoint, params=None):
    try:
        url = f"{BASE_URL}/{endpoint}"
        response = requests.get(url, headers=HEADERS, params=params)
        response.raise_for_status()
        return response.json().get("response", [])
    except requests.RequestException as e:
        print(f"Erro na API {endpoint}: {e}")
        return []

def get_team_id(team_name: str):
    data = api_get("teams", {"search": team_name})
    if data:
        team = data[0]["team"]
        print(f"Encontrado: {team['name']} (ID: {team['id']})")
        return team["id"]
    print(f"Time {team_name} não encontrado.")
    return None

def get_last_fixtures(team_id: int, limit=6):
    return api_get("fixtures", {"team": team_id, "last": limit, "timezone": "America/Sao_Paulo"})

def get_fixture_stats(fixture_id: int):
    """Pega estatísticas do jogo (inclui shots, posses, etc. – xG se disponível)"""
    stats = api_get(f"fixtures/statistics?fixture={fixture_id}")
    if not stats:
        return {}
    # stats é lista de 2 times
    team_stats = {}
    for s in stats:
        team_id = s["team"]["id"]
        team_stats[team_id] = {
            "Shots on Goal": s["statistics"].get("Shots on Goal", 0),
            "Total Shots": s["statistics"].get("Total Shots", 0),
            "Possession": s["statistics"].get("% Ball Possession", "0%"),
            # xG não é padrão em todos; se sua chave tiver, aparece como "Expected Goals"
            "xG": float(s["statistics"].get("Expected Goals", 0)) if "Expected Goals" in s["statistics"] else None
        }
    return team_stats

def extract_recent_stats(team_id: int, fixtures: list):
    scored, conceded, xg_scored, xg_conceded, matches = 0, 0, 0, 0, 0
    form = []  # 'W', 'D', 'L'

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

    avg_scored = scored / matches if matches else 0
    avg_conceded = conceded / matches if matches else 0
    avg_xg_scored = xg_scored / matches if xg_scored and matches else avg_scored  # fallback
    avg_xg_conceded = xg_conceded / matches if xg_conceded and matches else avg_conceded

    return {
        "matches": matches,
        "avg_goals_scored": round(avg_scored, 2),
        "avg_goals_conceded": round(avg_conceded, 2),
        "avg_xg_scored": round(avg_xg_scored, 2),
        "avg_xg_conceded": round(avg_xg_conceded, 2),
        "form": "".join(form[-5:])[::-1]  # últimos 5, mais recente à esquerda
    }

def get_h2h(team1_id: int, team2_id: int, limit=8):
    fixtures = api_get("fixtures/headtohead", {"team1": team1_id, "team2": team2_id})
    h2h = []
    for fix in fixtures[:limit]:
        if fix["fixture"]["status"]["short"] not in ["FT", "AET", "PEN"]:
            continue
        home = fix["teams"]["home"]["name"]
        away = fix["teams"]["away"]["name"]
        score = f"{fix['goals']['home']}-{fix['goals']['away']}"
        h2h.append(f"{home} {score} {away} ({fix['fixture']['date'][:10]})")
    return h2h

def get_recent_odds(team1_name: str, team2_name: str):
    # Odds para jogos futuros; aqui pegamos genéricas ou de league recente
    # Para precisão, use /odds?fixture=ID quando tiver fixture futuro
    # Exemplo aproximado via busca (ajuste league/season)
    # Por simplicidade, mostramos odds médias típicas ou placeholder
    # Ideal: encontre fixture_id futuro via /fixtures?teams=ID1-ID2&season=...
    print("Buscando odds recentes ou médias para confronto similar...")
    # Placeholder realista (substitua por chamada real quando possível)
    return {
        "1": 2.45, "X": 3.30, "2": 2.90,  # casa - empate - fora
        "bookmaker": "Exemplo (Bet365/Pinnacle média)"
    }

def poisson_sim(lambda_home: float, lambda_away: float, n=20000):
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

def simulate_match(home_name: str, away_name: str):
    home_id = get_team_id(home_name)
    away_id = get_team_id(away_name)
    if not home_id or not away_id:
        return

    print("\n=== Forma recente e stats (últimos 5-6 jogos) ===")
    fixtures_home = get_last_fixtures(home_id)
    fixtures_away = get_last_fixtures(away_id)

    stats_home = extract_recent_stats(home_id, fixtures_home)
    stats_away = extract_recent_stats(away_id, fixtures_away)

    print(f"{home_name} (casa): {stats_home['form']} | Jogos: {stats_home['matches']}")
    print(f"   Média gols: {stats_home['avg_goals_scored']} marcados / {stats_home['avg_goals_conceded']} sofridos")
    print(f"   Média xG : {stats_home['avg_xg_scored']} / {stats_home['avg_xg_conceded']}\n")

    print(f"{away_name} (fora): {stats_away['form']} | Jogos: {stats_away['matches']}")
    print(f"   Média gols: {stats_away['avg_goals_scored']} marcados / {stats_away['avg_goals_conceded']} sofridos")
    print(f"   Média xG : {stats_away['avg_xg_scored']} / {stats_away['avg_xg_conceded']}\n")

    # Lambda ajustado com xG (ataque próprio vs defesa adversária)
    lambda_home = (stats_home["avg_xg_scored"] + stats_away["avg_xg_conceded"]) / 2
    lambda_away = (stats_away["avg_xg_scored"] + stats_home["avg_xg_conceded"]) / 2

    # +0.3/-0.3 vantagem casa aproximada
    lambda_home += 0.3
    lambda_away -= 0.3

    print(f"→ Lambda (xG ajustado) {home_name}: {lambda_home:.2f}")
    print(f"→ Lambda (xG ajustado) {away_name}: {lambda_away:.2f}\n")

    sim = poisson_sim(lambda_home, lambda_away)

    odds = get_recent_odds(home_name, away_name)

    print("═" * 60)
    print(f"     SIMULAÇÃO: {home_name} (casa) vs {away_name} (fora)")
    print("═" * 60)
    print(f"Placar mais provável: {sim['most_probable']}")
    print(f"Probabilidades (Poisson xG):")
    print(f"  {home_name} vence: {sim['home_win']}%")
    print(f"  Empate:          {sim['draw']}%")
    print(f"  {away_name} vence: {sim['away_win']}%")
    print(f"\nOdds aproximadas (1X2): Casa {odds['1']:.2f} | Empate {odds['X']:.2f} | Fora {odds['2']:.2f} ({odds['bookmaker']})")
    print("═" * 60)

    # Confrontos diretos
    print("\nConfrontos diretos recentes:")
    h2h_list = get_h2h(home_id, away_id)
    for match in h2h_list:
        print(f" - {match}")
    if not h2h_list:
        print("Nenhum confronto direto recente encontrado.")

# Exemplo
if __name__ == "__main__":
    simulate_match("Tottenham", "Arsenal")
