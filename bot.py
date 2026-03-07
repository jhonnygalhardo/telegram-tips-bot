import os
import requests
from datetime import date
from scipy.stats import poisson

from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

BOT_TOKEN = os.getenv("BOT_TOKEN")
API_KEY = os.getenv("API_KEY")

HEADERS = {"x-apisports-key": API_KEY}

SEASON = 2024
LEAGUE_AVG = 1.35


def get_games():

    today = date.today()

    url = f"https://v3.football.api-sports.io/fixtures?date={today}"

    r = requests.get(url, headers=HEADERS, timeout=10)

    data = r.json()

    games = []

    allowed = [
        "Brazil",
        "USA",
        "England",
        "Spain",
        "Italy",
        "Germany",
        "France"
    ]

    for g in data.get("response", []):

        if g["league"]["country"] not in allowed:
            continue

        games.append({
            "fixture_id": g["fixture"]["id"],
            "home": g["teams"]["home"]["name"],
            "away": g["teams"]["away"]["name"],
            "home_id": g["teams"]["home"]["id"],
            "away_id": g["teams"]["away"]["id"],
            "league": g["league"]["id"]
        })

    return games


def get_team_stats(team_id, league):

    url = f"https://v3.football.api-sports.io/teams/statistics?team={team_id}&league={league}&season={SEASON}"

    r = requests.get(url, headers=HEADERS)

    data = r.json()

    stats = data["response"]

    played = stats["fixtures"]["played"]["total"]

    if played == 0:
        return None

    goals_for = stats["goals"]["for"]["total"]["total"]
    goals_against = stats["goals"]["against"]["total"]["total"]

    attack = goals_for / played
    defense = goals_against / played

    return attack, defense


def expected_goals(att1, def1, att2, def2):

    home_xg = LEAGUE_AVG * (att1 / def2)
    away_xg = LEAGUE_AVG * (att2 / def1)

    return home_xg, away_xg


def match_probs(xg1, xg2):

    max_goals = 5

    home = draw = away = 0

    for i in range(max_goals):
        for j in range(max_goals):

            p = poisson.pmf(i, xg1) * poisson.pmf(j, xg2)

            if i > j:
                home += p
            elif i == j:
                draw += p
            else:
                away += p

    return home, draw, away


def get_odds(fixture):

    url = f"https://v3.football.api-sports.io/odds?fixture={fixture}"

    r = requests.get(url, headers=HEADERS)

    data = r.json()

    try:

        bets = data["response"][0]["bookmakers"][0]["bets"]

        for b in bets:

            if b["name"] == "Match Winner":

                odds = {v["value"]: float(v["odd"]) for v in b["values"]}

                return odds["Home"], odds["Draw"], odds["Away"]

    except:

        return None


def analyze_games(games):

    opportunities = []

    for g in games:

        home_stats = get_team_stats(g["home_id"], g["league"])
        away_stats = get_team_stats(g["away_id"], g["league"])

        if not home_stats or not away_stats:
            continue

        xg1, xg2 = expected_goals(*home_stats, *away_stats)

        p_home, p_draw, p_away = match_probs(xg1, xg2)

        odds = get_odds(g["fixture_id"])

        if not odds:
            continue

        o_home, o_draw, o_away = odds

        fair_home = 1 / p_home
        fair_draw = 1 / p_draw
        fair_away = 1 / p_away

        value_home = o_home - fair_home
        value_draw = o_draw - fair_draw
        value_away = o_away - fair_away

        best = max(value_home, value_draw, value_away)

        opportunities.append({
            "home": g["home"],
            "away": g["away"],
            "value": best,
            "odds": odds
        })

    opportunities.sort(key=lambda x: x["value"], reverse=True)

    return opportunities[:5]


async def value(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text("🔎 Procurando oportunidades...")

    games = get_games()

    best = analyze_games(games)

    if not best:
        await update.message.reply_text("❌ Nenhuma oportunidade encontrada")
        return

    msg = "💰 TOP 5 VALUE BETS DO DIA\n\n"

    for g in best:

        msg += f"{g['home']} vs {g['away']}\n"
        msg += f"Value: {g['value']:.2f}\n\n"

    await update.message.reply_text(msg)


def main():

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("value", value))

    print("Scanner rodando...")

    app.run_polling()


if __name__ == "__main__":
    main()
