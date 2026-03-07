import os
import requests
import numpy as np
from datetime import date

from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

from scipy.stats import poisson

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
        "France",
        "Portugal",
        "Netherlands"
    ]

    for g in data.get("response", []):

        country = g["league"]["country"]

        if country not in allowed:
            continue

        games.append({
            "home": g["teams"]["home"]["name"],
            "away": g["teams"]["away"]["name"],
            "home_id": g["teams"]["home"]["id"],
            "away_id": g["teams"]["away"]["id"],
            "league": g["league"]["id"]
        })

    return games


def get_team_stats(team_id, league):

    url = f"https://v3.football.api-sports.io/teams/statistics?team={team_id}&league={league}&season={SEASON}"

    r = requests.get(url, headers=HEADERS, timeout=10)

    data = r.json()

    if "response" not in data:
        return None

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


def poisson_probs(xg_home, xg_away):

    max_goals = 5

    probs = {}

    home_win = 0
    draw = 0
    away_win = 0

    over25 = 0

    for i in range(max_goals):
        for j in range(max_goals):

            p = poisson.pmf(i, xg_home) * poisson.pmf(j, xg_away)

            probs[(i, j)] = p

            if i > j:
                home_win += p
            elif i == j:
                draw += p
            else:
                away_win += p

            if i + j > 2:
                over25 += p

    return home_win, draw, away_win, over25, probs


def analyze_games(games):

    results = []

    for g in games:

        home_stats = get_team_stats(g["home_id"], g["league"])
        away_stats = get_team_stats(g["away_id"], g["league"])

        if not home_stats or not away_stats:
            continue

        att1, def1 = home_stats
        att2, def2 = away_stats

        xg1, xg2 = expected_goals(att1, def1, att2, def2)

        home_win, draw, away_win, over25, probs = poisson_probs(xg1, xg2)

        most_likely = max(probs, key=probs.get)

        results.append({
            "home": g["home"],
            "away": g["away"],
            "xg1": xg1,
            "xg2": xg2,
            "home_win": home_win,
            "draw": draw,
            "away_win": away_win,
            "over25": over25,
            "score": most_likely
        })

    results.sort(key=lambda x: abs(x["xg1"] - x["xg2"]))

    return results[:10]


async def today(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text("📊 Analisando jogos com modelo PRO...")

    games = get_games()

    if not games:
        await update.message.reply_text("❌ Nenhum jogo encontrado.")
        return

    analysis = analyze_games(games)

    msg = "🏆 TOP MATCHUPS DO DIA\n\n"

    for g in analysis:

        msg += (
            f"{g['home']} vs {g['away']}\n"
            f"xG: {g['xg1']:.2f} - {g['xg2']:.2f}\n"
            f"Casa: {g['home_win']*100:.1f}%\n"
            f"Empate: {g['draw']*100:.1f}%\n"
            f"Fora: {g['away_win']*100:.1f}%\n"
            f"Over2.5: {g['over25']*100:.1f}%\n"
            f"Placar provável: {g['score'][0]}-{g['score'][1]}\n\n"
        )

    await update.message.reply_text(msg)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text(
        "🤖 Bot PRO de análise de futebol\n\nUse /today"
    )


def main():

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("today", today))

    print("Bot PRO rodando...")

    app.run_polling()


if __name__ == "__main__":
    main()
