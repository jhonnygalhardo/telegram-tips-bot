import os
import requests
import random
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
)

# ==============================
# CONFIG
# ==============================

BOT_TOKEN = os.getenv("BOT_TOKEN")
API_KEY = os.getenv("API_FOOTBALL_KEY")

if not BOT_TOKEN:
    raise Exception("BOT_TOKEN não configurado no Railway!")

# ==============================
# TELEGRAM COMMANDS
# ==============================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 TIPSTER IA ONLINE!\n\n"
        "Use:\n"
        "/match Arsenal x Liverpool"
    )

# ==============================
# BUSCAR TIME (GLOBAL)
# ==============================

def buscar_id_time(nome_time):

    url = "https://v3.football.api-sports.io/teams"

    headers = {
        "x-apisports-key": API_KEY
    }

    params = {
        "search": nome_time
    }

    r = requests.get(url, headers=headers, params=params).json()

    resposta = r.get("response", [])

    if not resposta:
        return None

    return resposta[0]["team"]["id"]

# ==============================
# PROXIMO JOGO DO TIME
# ==============================

def buscar_proximo_jogo(nome_time):

    team_id = buscar_id_time(nome_time)

    if not team_id:
        return None

    url = "https://v3.football.api-sports.io/fixtures"

    headers = {
        "x-apisports-key": API_KEY
    }

    params = {
        "team": team_id,
        "next": 1
    }

    r = requests.get(url, headers=headers, params=params).json()

    jogos = r.get("response", [])

    if not jogos:
        return None

    jogo = jogos[0]

    return {
        "home": jogo["teams"]["home"]["name"],
        "away": jogo["teams"]["away"]["name"],
        "league": jogo["league"]["name"]
    }

# ==============================
# MODELO IA (PREVISÃO DE GOLS)
# ==============================

def prever_gols():

    # Modelo base (iremos evoluir depois)
    ataque = random.uniform(0.9, 2.4)
    defesa = random.uniform(0.8, 1.9)

    gols = ataque * (2 - defesa / 2)

    return round(max(0.4, gols), 2)

# ==============================
# MATCH VIRTUAL
# ==============================

async def match(update: Update, context: ContextTypes.DEFAULT_TYPE):

    texto = " ".join(context.args)

    if " x " not in texto.lower():
        await update.message.reply_text(
            "Use:\n/match Time1 x Time2"
        )
        return

    timeA, timeB = texto.split(" x ")

    timeA = timeA.strip()
    timeB = timeB.strip()

    await update.message.reply_text("🔎 IA analisando jogos reais...")

    jogoA = buscar_proximo_jogo(timeA)
    jogoB = buscar_proximo_jogo(timeB)

    if not jogoA:
        await update.message.reply_text(f"❌ Não encontrei jogo do {timeA}")
        return

    if not jogoB:
        await update.message.reply_text(f"❌ Não encontrei jogo do {timeB}")
        return

    golsA = prever_gols()
    golsB = prever_gols()

    if golsA > golsB:
        vencedor = f"🏆 {timeA}"
    elif golsB > golsA:
        vencedor = f"🏆 {timeB}"
    else:
        vencedor = "🤝 EMPATE"

    resposta = f"""
⚔️ MATCH VIRTUAL IA

🟥 {timeA}
🏟 {jogoA['home']} vs {jogoA['away']}
🏆 Liga: {jogoA['league']}
⚽ Gols previstos: {golsA}

🟦 {timeB}
🏟 {jogoB['home']} vs {jogoB['away']}
🏆 Liga: {jogoB['league']}
⚽ Gols previstos: {golsB}

━━━━━━━━━━━━━━━
RESULTADO VIRTUAL
{vencedor}
━━━━━━━━━━━━━━━
"""

    await update.message.reply_text(resposta)

# ==============================
# START BOT
# ==============================

app = ApplicationBuilder().token(BOT_TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("match", match))

print("✅ BOT ONLINE...")

app.run_polling()
