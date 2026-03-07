import os
import requests
from datetime import date

from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

BOT_TOKEN = os.getenv("BOT_TOKEN")
API_KEY = os.getenv("API_KEY")

headers = {
    "x-apisports-key": API_KEY
}

SEASON = 2024

# média de gols por time
LEAGUE_AVG = 1.35


def get_games():

    today = date.today()

    url = f"https://v3.football.api-sports.io/fixtures?date={today}"

    r = requests.get(url, headers=headers, timeout=10)

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

    r = requests.get(url, headers=headers, timeout=10)

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


def analyze_matchups(games):

    results = []

    for g in games:

        home_stats = get_team_stats(g["home_id"], g["league"])
        away_stats = get_team_stats(g["away_id"], g["league"])

        if not home_stats or not away_stats:
            continue

        att1, def1 = home_stats
        att2, def2 = away_stats

        xg1, xg2 = expected_goals(att1, def1, att2, def2)

        diff = abs(xg1 - xg2)

        results.append({
            "home": g["home"],
            "away": g["away"],
            "xg1": xg1,
            "xg2": xg2,
            "balance": diff
        })

    results.sort(key=lambda x: x["balance"])

    return results[:10]


async def today(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text("📊 Analisando jogos reais do dia...")

    games = get_games()

    if not games:
        await update.message.reply_text("❌ Nenhum jogo encontrado.")
        return

    matchups = analyze_matchups(games)

    msg = "🏆 MELHORES MATCHUPS (dados reais)\n\n"

    for m in matchups:

        msg += (
            f"{m['home']} vs {m['away']}\n"
            f"xG: {m['xg1']:.2f} - {m['xg2']:.2f}\n\n"
        )

    await update.message.reply_text(msg)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text(
        "🤖 Bot de análise de futebol\n\nUse /today para analisar jogos do dia."
    )


def main():

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("today", today))

    print("Bot rodando...")

    app.run_polling()


if __name__ == "__main__":
    main()
