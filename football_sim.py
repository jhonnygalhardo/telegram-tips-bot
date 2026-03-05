import unicodedata
from typing import Optional

def normalize_name(name: str) -> str:
    """Remove acentos, converte para minúsculo e remove espaços extras para comparação"""
    name = name.lower().strip()
    return ''.join(c for c in unicodedata.normalize('NFD', name)
                   if unicodedata.category(c) != 'Mn')

def get_team_id(team_name: str) -> Optional[int]:
    original_name = team_name.strip()
    search_name = original_name
    
    # Dicionário expandido com variações comuns (apelidos, abreviações, nomes alternativos)
    common_variations = {
        # Premier League (Inglaterra)
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
        "newcastle": "Newcastle United",
        "aston villa": "Aston Villa",
        "west ham": "West Ham United",
        "fulham": "Fulham",
        "brighton": "Brighton & Hove Albion",
        "crystal palace": "Crystal Palace",
        "everton": "Everton",
        "wolves": "Wolverhampton Wanderers",
        "nottingham forest": "Nottingham Forest",
        "brentford": "Brentford",
        "bournemouth": "AFC Bournemouth",
        "sunderland": "Sunderland",
        "burnley": "Burnley",
        "leeds": "Leeds United",

        # Brasileirão Série A (Brasil)
        "flamengo": "Flamengo",
        "fla": "Flamengo",
        "mengão": "Flamengo",
        "palmeiras": "Palmeiras",
        "verdão": "Palmeiras",
        "cruzeiro": "Cruzeiro",
        "raposa": "Cruzeiro",
        "corinthians": "Corinthians",
        "timão": "Corinthians",
        "são paulo": "São Paulo",
        "tricolor": "São Paulo",
        "bahia": "Bahia",
        "ec bahia": "Bahia",
        "botafogo": "Botafogo",
        "fogão": "Botafogo",
        "atlético mg": "Atlético Mineiro",
        "galo": "Atlético Mineiro",
        "fortaleza": "Fortaleza",
        "leão": "Fortaleza",
        "internacional": "Internacional",
        "colorado": "Internacional",
        "grêmio": "Grêmio",
        "imortal": "Grêmio",
        "fluminense": "Fluminense",
        "tricolor carioca": "Fluminense",
        "vasco": "Vasco da Gama",
        "vasco da gama": "Vasco da Gama",
        "cr vasco": "Vasco da Gama",
        "mirassol": "Mirassol",
        "red bull bragantino": "Red Bull Bragantino",
        "bragantino": "Red Bull Bragantino",
        "santos": "Santos",
        "peixe": "Santos",
        "ceará": "Ceará",
        "juventude": "Juventude",
        "sport": "Sport",
        "vitória": "Vitória",
        "ec vitória": "Vitória",

        # Bundesliga (Alemanha)
        "bayern": "Bayern Munich",
        "bayern munich": "Bayern Munich",
        "fcb": "Bayern Munich",
        "borussia dortmund": "Borussia Dortmund",
        "dortmund": "Borussia Dortmund",
        "bvb": "Borussia Dortmund",
        "hoffenheim": "TSG Hoffenheim",
        "1899 hoffenheim": "TSG Hoffenheim",
        "tsg": "TSG Hoffenheim",
        "stuttgart": "VfB Stuttgart",
        "vfb stuttgart": "VfB Stuttgart",
        "rb leipzig": "RB Leipzig",
        "leipzig": "RB Leipzig",
        "rbl": "RB Leipzig",
        "leverkusen": "Bayer Leverkusen",
        "bayer leverkusen": "Bayer Leverkusen",
        "b04": "Bayer Leverkusen",
        "frankfurt": "Eintracht Frankfurt",
        "freiburg": "SC Freiburg",
        "augsburg": "FC Augsburg",
        "union berlin": "1. FC Union Berlin",
        "union": "1. FC Union Berlin",
        "gladbach": "Borussia Mönchengladbach",
        "mönchengladbach": "Borussia Mönchengladbach",
        "werder bremen": "Werder Bremen",
        "mainz": "1. FSV Mainz 05",
        "mainz 05": "1. FSV Mainz 05",
        "heidenheim": "FC Heidenheim",
        "1. fc heidenheim": "FC Heidenheim",
        "wolfsburg": "VfL Wolfsburg",
        "köln": "1. FC Köln",
        "cologne": "1. FC Köln",

        # La Liga (Espanha)
        "barcelona": "FC Barcelona",
        "barça": "FC Barcelona",
        "real madrid": "Real Madrid",
        "madrid": "Real Madrid",
        "rma": "Real Madrid",
        "atlético madrid": "Atlético Madrid",
        "atleti": "Atlético Madrid",
        "atm": "Atlético Madrid",
        "villarreal": "Villarreal CF",
        "real betis": "Real Betis",
        "betis": "Real Betis",
        "celta": "Celta de Vigo",
        "celta vigo": "Celta de Vigo",
        "osasuna": "CA Osasuna",
        "alavés": "Deportivo Alavés",
        "espanyol": "RCD Espanyol",
        "getafe": "Getafe CF",
        "mallorca": "Mallorca",
        "valencia": "Valencia CF",
        "girona": "Girona FC",
        "sevilla": "Sevilla FC",
        "real sociedad": "Real Sociedad",
        "rayo vallecano": "Rayo Vallecano",
        "athletic club": "Athletic Club",
        "athletic bilbao": "Athletic Club",
        # Adicione mais se precisar (ex: promovidos como Elche, Oviedo, Levante etc.)
    }
    
    norm_input = normalize_name(original_name)
    
    # Se o nome normalizado estiver no dicionário, usa a variação oficial
    if norm_input in common_variations:
        search_name = common_variations[norm_input]
        print(f"Variação aplicada: '{original_name}' → busca por '{search_name}'")
    
    attempts = [
        search_name,                  # nome ajustado ou original
        original_name,                # como o usuário digitou
        normalize_name(search_name),  # sem acentos
    ]
    
    found = None
    candidates = []
    
    for attempt in set(attempts):  # evita duplicatas
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
            
            # Match exato (ignorando case/acentos/espaços extras)
            if team_norm == attempt_norm or team_norm.replace(" ", "") == attempt_norm.replace(" ", ""):
                found = team["id"]
                print(f"Match exato: {team['name']} (ID: {team['id']}) via '{attempt}'")
                break
        
        if found:
            break
    
    if found:
        return found
    
    # Se não achou exato, mas tem candidatos → usa o primeiro (com log)
    if candidates:
        print(f"Candidatos para '{original_name}':")
        for name, tid, _ in sorted(candidates, key=lambda x: len(x[0]))[:5]:  # menores nomes primeiro (mais prováveis)
            print(f" - {name} (ID: {tid})")
        
        fallback = candidates[0]
        print(f"Usando fallback: {fallback[0]} (ID: {fallback[1]})")
        return fallback[1]
    
    print(f"Time '{original_name}' não encontrado após tentativas.")
    return None
