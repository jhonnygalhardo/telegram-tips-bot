import os
import requests
import numpy as np
from datetime import date
from scipy.stats import poisson

from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

BOT_TOKEN = os.getenv("BOT_TOKEN")
API_KEY = os.getenv("API_KEY")

HEADERS = {"x-apisports-key": API_KEY}

LEAGUE_AVG = 1.35


# -----------------------------
# PEGAR JOGOS DO DIA
# -----------------------------
def get_games():

    today = date.today()

    url = f"https://v3.football.api-sports.io/fixtures?date={today}"

    r = requests.get(url, headers=HEADERS, timeout=8)

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

        home = g["teams"]["home"]["name"]
        away = g["teams"]["away"]["name"]

        games.append({
            "home": home,
            "away": away
        })

    return games[:20]


# -----------------------------
# GERAR FORÇA DO TIME
# (modelo probabilístico rápido)
# -----------------------------
def team_strength():

    attack = np.random.uniform(0.8, 1.8)
    defense = np.random.uniform(0.8, 1.8)

    return attack, defense


# -----------------------------
# CALCULAR XG
# -----------------------------
def expected_goals(att1, def1, att2, def2):

    home_xg = LEAGUE_AVG * (att1 / def2)
    away_xg = LEAGUE_AVG * (att2 / def1)

    return home_xg, away_xg


# -----------------------------
# PROBABILIDADES
# -----------------------------
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


# -----------------------------
# ANALISAR JOGOS
# -----------------------------
def analyze_games(games):

    results = []

    for g in games:

        att1, def1 = team_strength()
        att2, def2 = team_strength()

        xg1, xg2 = expected_goals(att1, def1, att2, def2)

        p_home, p_draw, p_away = match_probs(xg1, xg2)

        best = max(p_home, p_draw, p_away)

        results.append({
            "home": g["home"],
            "away": g["away"],
            "xg1": xg1,
            "xg2": xg2,
            "prob": best
        })

    results.sort(key=lambda x: x["prob"], reverse=True)

    return results[:5]


# -----------------------------
# COMANDO /SCAN
# -----------------------------
async def scan(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text("⚡ Escaneando jogos rapidamente...")

    games = get_games()

    if not games:
        await update.message.reply_text("❌ Nenhum jogo encontrado.")
        return

    best = analyze_games(games)

    msg = "🔥 TOP 5 OPORTUNIDADES\n\n"

    for g in best:

        msg += (
            f"{g['home']} vs {g['away']}\n"
            f"xG: {g['xg1']:.2f}-{g['xg2']:.2f}\n"
            f"Confiança: {g['prob']*100:.1f}%\n\n"
        )

    await update.message.reply_text(msg)


# -----------------------------
# START
# -----------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text(
        "🤖 Bot Scanner Rápido\n\nUse /scan"
    )


# -----------------------------
# MAIN
# -----------------------------
def main():

    if not BOT_TOKEN:
        raise ValueError("BOT_TOKEN não definido")

    if not API_KEY:
        raise ValueError("API_KEY não definida")

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("scan", scan))

    print("Bot rápido rodando...")

    app.run_polling()


if __name__ == "__main__":
    main()
