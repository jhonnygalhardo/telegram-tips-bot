import os
import requests
import numpy as np
from datetime import date

from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

BOT_TOKEN = os.getenv("BOT_TOKEN")
API_KEY = os.getenv("API_KEY")

headers = {
    "x-apisports-key": API_KEY
}


def get_games():

    today = date.today()

    url = f"https://v3.football.api-sports.io/fixtures?date={today}"

    r = requests.get(url, headers=headers, timeout=10)

    data = r.json()

    teams = []

    allowed_countries = [
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

        if country not in allowed_countries:
            continue

        home = g["teams"]["home"]["name"]
        away = g["teams"]["away"]["name"]

        teams.append(home)
        teams.append(away)

    return list(set(teams))


def random_strength():

    attack = np.random.uniform(0.8, 2.2)
    defense = np.random.uniform(0.8, 2.2)

    return attack, defense


def expected_goals(att, defn):

    return (att + defn) / 2


def analyze_matchups(teams):

    results = []

    for i in range(len(teams)):
        for j in range(i + 1, len(teams)):

            t1 = teams[i]
            t2 = teams[j]

            att1, def1 = random_strength()
            att2, def2 = random_strength()

            g1 = expected_goals(att1, def2)
            g2 = expected_goals(att2, def1)

            diff = abs(g1 - g2)

            results.append({
                "team1": t1,
                "team2": t2,
                "g1": g1,
                "g2": g2,
                "balance": diff
            })

    results.sort(key=lambda x: x["balance"])

    return results[:10]


async def today(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text(
        "🔎 Analisando jogos da Europa, Brasil e EUA..."
    )

    teams = get_games()

    if len(teams) < 2:
        await update.message.reply_text("❌ Nenhum jogo encontrado hoje.")
        return

    matchups = analyze_matchups(teams)

    msg = "🏆 MELHORES MATCHUPS VIRTUAIS\n\n"

    for m in matchups:

        msg += (
            f"{m['team1']} vs {m['team2']}\n"
            f"⚽ xG: {m['g1']:.2f} - {m['g2']:.2f}\n\n"
        )

    await update.message.reply_text(msg)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text(
        "🤖 Bot de Matchups\n\nUse /today para analisar jogos do dia."
    )


def main():

    if not BOT_TOKEN:
        raise ValueError("BOT_TOKEN não definido")

    if not API_KEY:
        raise ValueError("API_KEY não definida")

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("today", today))

    print("Bot rodando...")

    app.run_polling()


if __name__ == "__main__":
    main()
