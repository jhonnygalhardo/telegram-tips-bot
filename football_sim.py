import os
import requests
import random
from collections import Counter
import unicodedata
from typing import Optional, Dict, List

API_KEY = os.getenv("API_FOOTBALL_KEY")
if not API_KEY:
    raise ValueError("API_FOOTBALL_KEY não encontrada!")

BASE_URL = "https://v3.football.api-sports.io"
HEADERS = {"x-apisports-key": API_KEY}

def api_get(endpoint: str, params=None, timeout=15) -> list:
    try:
        url = f"{BASE_URL}/{endpoint}"
        response = requests.get(url, headers=HEADERS, params=params, timeout=timeout)
        response.raise_for_status()
        return response.json().get("response", [])
    except requests.RequestException as e:
        print(f"Erro na API {endpoint}: {e}")
        return []

def normalize_name(name: str) -> str:
    """Remove acentos, converte para minúsculo e remove espaços extras para comparação"""
    name = name.lower().strip()
    return ''.join(c for c in unicodedata.normalize('NFD', name)
                   if unicodedata.category(c) != 'Mn')

def get_team_id(team_name: str) -> Optional[int]:
    original_name = team_name.strip()
    search_name = original_name
    
    # Dicionário expandido com variações comuns
    common_variations = {
        # Premier League
        "man city": "Manchester City",
        "mci": "Manchester City",
        "city": "Manchester City",
        "man united": "Manchester United",
        "man utd": "Manchester United",
        "united": "Manchester United",
        "mun": "Manchester United",
        "arsenal": "Arsenal",
        "liverpool": "Liverpool",
        "chelsea": "Chelsea",
        "tottenham": "Tottenham Hotspur",
        "spurs": "Tottenham Hotspur",
        # ... (mantenha todo o dicionário que você já tem, eu não repeti tudo aqui para encurtar)
        # Adicione o resto do seu dicionário aqui (Brasileirão, Bundesliga, La Liga)
        # Exemplo final:
        "barcelona": "FC Barcelona",
        "barça": "FC Barcelona",
        "real madrid": "Real Madrid",
        # etc.
    }
    
    norm_input = normalize_name(original_name)
    
    if norm_input in common_variations:
        search_name = common_variations[norm_input]
        print(f"Variação aplicada: '{original_name}' → '{search_name}'")
    
    attempts = [
        search_name,
        original_name,
        normalize_name(search_name),
    ]
    
    found = None
    candidates = []
    
    for attempt in set(attempts):
        if len(attempt) < 3:
            continue
        data = api_get("teams", {"search": attempt})
        if not data:
            continue
        
        for item in data:
            team = item["team"]
            team_norm = normalize_name(team["name"])
            attempt_norm = normalize_name(attempt)
            
            candidates.append((team["name"], team["id"], team_norm))
            
            if team_norm == attempt_norm or team_norm.replace(" ", "") == attempt_norm.replace(" ", ""):
                found = team["id"]
                print(f"Match exato: {team['name']} (ID: {team['id']}) via '{attempt}'")
                break
        
        if found:
            break
    
    if found:
        return found
    
    if candidates:
        print(f"Candidatos para '{original_name}':")
        for name, tid, _ in sorted(candidates, key=lambda x: len(x[0]))[:5]:
            print(f" - {name} (ID: {tid})")
        
        fallback = candidates[0]
        print(f"Usando fallback: {fallback[0]} (ID: {fallback[1]})")
        return fallback[1]
    
    print(f"Time '{original_name}' não encontrado.")
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
        stats_dict = {stat["type"]: stat["value"] for stat in s.get("statistics", [])}
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
        return {"error": "Nenhum jogo concluído recente"}

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
        "form": "".join(form[-5:])[::-1]
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

    lines.append("Forma recente (últimos 5):")
    lines.append(f"  {home_name}: {stats_home['form']}  |  {stats_home['avg_goals_scored']} / {stats_home['avg_goals_conceded']} gols (xG {stats_home['avg_xg_scored']}/{stats_home['avg_xg_conceded']})")
    lines.append(f"  {away_name}: {stats_away['form']}  |  {stats_away['avg_goals_scored']} / {stats_away['avg_goals_conceded']} gols (xG {stats_away['avg_xg_scored']}/{stats_away['avg_xg_conceded']})\n")

    lambda_home = (stats_home["avg_xg_scored"] + stats_away["avg_xg_conceded"]) / 2 + 0.3
    lambda_away = (stats_away["avg_xg_scored"] + stats_home["avg_xg_conceded"]) / 2 - 0.3

    lines.append("Lambda estimado (xG + vantagem casa):")
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
