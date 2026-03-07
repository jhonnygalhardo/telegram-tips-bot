import requests
import numpy as np
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from datetime import date

TOKEN = "SEU_TOKEN_TELEGRAM"
API_KEY = "SUA_API_KEY_API_FOOTBALL"

headers = {
    "x-apisports-key": API_KEY
}

# ligas que vamos analisar
LEAGUES = [
    39,   # Premier League
    140,  # La Liga
    135,  # Serie A
    78,   # Bundesliga
    61,   # Ligue 1
    71,   # Brasileirão
    253   # MLS
]

def get_games():

    today = date.today()

    teams = []

    for league in LEAGUES:

        url = f"https://v3.football.api-sports.io/fixtures?league={league}&date={today}"

        r = requests.get(url, headers=headers, timeout=10)

        data = r.json()

        for g in data.get("response", []):

            home = g["teams"]["home"]["name"]
            away = g["teams"]["away"]["name"]

            teams.append(home)
            teams.append(away)

    return list(set(teams))


def random_strength(team):

    attack = np.random.uniform(0.8, 2.2)
    defense = np.random.uniform(0.8, 2.2)

    return attack, defense


def expected_goals(att, defn):

    return (att + defn) / 2


def analyze_matchups(teams):

    results = []

    for i in range(len(teams)):
        for j in range(i+1, len(teams)):

            t1 = teams[i]
            t2 = teams[j]

            att1, def1 = random_strength(t1)
            att2, def2 = random_strength(t2)

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

    await update.message.reply_text("🔎 Analisando jogos da Europa, Brasil e EUA...")

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


if __name__ == "__main__":

    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("today", today))

    print("Bot rodando...")

    app.run_polling()
