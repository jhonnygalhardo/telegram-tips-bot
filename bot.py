import os
import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

TOKEN = os.getenv("BOT_TOKEN")

API_KEY = os.getenv("API_FOOTBALL_KEY")
BASE_URL = "https://v3.football.api-sports.io"

HEADERS = {
    "x-apisports-key": API_KEY
}


# ==============================
# BUSCAR TIME PELO NOME
# ==============================
def find_team(team_name):
    url = f"{BASE_URL}/teams"
    params = {"search": team_name}

    r = requests.get(url, headers=HEADERS, params=params).json()

    if r["results"] == 0:
        return None

    return r["response"][0]["team"]["id"]


# ==============================
# BUSCAR PRÓXIMO JOGO DO TIME
# ==============================
def next_fixture(team_id):
    url = f"{BASE_URL}/fixtures"
    params = {
        "team": team_id,
        "next": 1
    }

    r = requests.get(url, headers=HEADERS, params=params).json()

    if r["results"] == 0:
        return None

    return r["response"][0]


# ==============================
# ANALISE PROFUNDA (PREVISÃO GOLS)
# ==============================
def predict_goals(team_id):

    url = f"{BASE_URL}/fixtures"
    params = {
        "team": team_id,
        "last": 5
    }

    r = requests.get(url, headers=HEADERS, params=params).json()

    goals = []

    for game in r["response"]:
        home = game["teams"]["home"]["id"]
        score_home = game["goals"]["home"]
        score_away = game["goals"]["away"]

        if home == team_id:
            goals.append(score_home)
        else:
            goals.append(score_away)

    if len(goals) == 0:
        return 1.0

    avg = sum(goals) / len(goals)

    # ajuste estatístico simples
    return round(avg * 1.15, 2)


# ==============================
# COMANDO /start
# ==============================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "⚽ Bot de Matchup Virtual ONLINE!\n\nUse:\n/match Arsenal x Liverpool"
    )


# ==============================
# COMANDO /match
# ==============================
async def match(update: Update, context: ContextTypes.DEFAULT_TYPE):

    try:
        text = " ".join(context.args)

        if "x" not in text.lower():
            await update.message.reply_text("Use: /match TimeA x TimeB")
            return

        teamA_name, teamB_name = text.split("x")

        teamA_name = teamA_name.strip()
        teamB_name = teamB_name.strip()

        await update.message.reply_text("🔎 Analisando matchup virtual...")

        teamA_id = find_team(teamA_name)
        teamB_id = find_team(teamB_name)

        if not teamA_id or not teamB_id:
            await update.message.reply_text("❌ Time não encontrado.")
            return

        fixtureA = next_fixture(teamA_id)
        fixtureB = next_fixture(teamB_id)

        if not fixtureA or not fixtureB:
            await update.message.reply_text("❌ Jogos não encontrados.")
            return

        goalsA = predict_goals(teamA_id)
        goalsB = predict_goals(teamB_id)

        # RESULTADO
        if goalsA > goalsB:
            winner = teamA_name
        elif goalsB > goalsA:
            winner = teamB_name
        else:
            winner = "EMPATE"

        msg = f"""
⚔️ MATCHUP VIRTUAL

🔴 {teamA_name} → previsão gols: {goalsA}
🔵 {teamB_name} → previsão gols: {goalsB}

🏆 Resultado provável: {winner}
"""

        await update.message.reply_text(msg)

    except Exception as e:
        await update.message.reply_text(f"Erro: {e}")


# ==============================
# START BOT
# ==============================
app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("match", match))

print("BOT ONLINE...")
app.run_polling()
