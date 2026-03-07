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


# -------------------------
# PEGAR JOGOS DO DIA
# -------------------------
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

        if g["league"]["country"] not in allowed:
            continue

        games.append({
            "home": g["teams"]["home"]["name"],
            "away": g["teams"]["away"]["name"],
            "home_id": g["teams"]["home"]["id"],
            "away_id": g["teams"]["away"]["id"],
            "league": g["league"]["id"]
        })

    return games


# -------------------------
# ESTATÍSTICAS DO TIME
# -------------------------
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


# -------------------------
# CALCULAR XG
# -------------------------
def expected_goals(att1, def1, att2, def2):

    home_xg = LEAGUE_AVG * (att1 / def2)
    away_xg = LEAGUE_AVG * (att2 / def1)

    return home_xg, away_xg


# -------------------------
# PROBABILIDADES POISSON
# -------------------------
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


# -------------------------
# ANALISAR JOGOS
# -------------------------
def analyze_games(games):

    opportunities = []

    for g in games:

        home_stats = get_team_stats(g["home_id"], g["league"])
        away_stats = get_team_stats(g["away_id"], g["league"])

        if not home_stats or not away_stats:
            continue

        att1, def1 = home_stats
        att2, def2 = away_stats

        xg1, xg2 = expected_goals(att1, def1, att2, def2)

        p_home, p_draw, p_away = match_probs(xg1, xg2)

        best_prob = max(p_home, p_draw, p_away)

        opportunities.append({
            "home": g["home"],
            "away": g["away"],
            "prob": best_prob,
            "xg1": xg1,
            "xg2": xg2
        })

    opportunities.sort(key=lambda x: x["prob"], reverse=True)

    return opportunities[:5]


# -------------------------
# COMANDO /SCAN
# -------------------------
async def scan(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text("🔎 Escaneando jogos do dia...")

    games = get_games()

    if not games:
        await update.message.reply_text("❌ Nenhum jogo encontrado hoje.")
        return

    best = analyze_games(games)

    if not best:
        await update.message.reply_text("❌ Não foi possível analisar os jogos.")
        return

    msg = "🔥 TOP 5 JOGOS MAIS PREVISÍVEIS\n\n"

    for g in best:

        msg += (
            f"{g['home']} vs {g['away']}\n"
            f"xG: {g['xg1']:.2f}-{g['xg2']:.2f}\n"
            f"Confiança: {g['prob']*100:.1f}%\n\n"
        )

    await update.message.reply_text(msg)


# -------------------------
# START
# -------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text(
        "🤖 Bot Scanner de Futebol\n\n"
        "Use /scan para encontrar oportunidades do dia."
    )


# -------------------------
# MAIN
# -------------------------
def main():

    if not BOT_TOKEN:
        raise ValueError("BOT_TOKEN não definido")

    if not API_KEY:
        raise ValueError("API_KEY não definida")

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("scan", scan))

    print("Bot scanner rodando...")

    app.run_polling()


if __name__ == "__main__":
    main()
