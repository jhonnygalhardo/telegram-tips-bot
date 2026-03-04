import os
import requests
from difflib import SequenceMatcher
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

TOKEN = os.getenv("TOKEN")

API_KEY = "SUA_API_KEY_API_FOOTBALL"
BASE_URL = "https://v3.football.api-sports.io"

HEADERS = {"x-apisports-key": API_KEY}

# =============================
# CACHE GLOBAL DE TIMES
# =============================
TEAMS_CACHE = []


# =============================
# CARREGAR TIMES (UMA VEZ)
# =============================
def carregar_times():
    global TEAMS_CACHE

    print("Carregando base mundial de times...")

    url = f"{BASE_URL}/teams"
    params = {"league": 39, "season": 2023}  # Premier League base

    r = requests.get(url, headers=HEADERS, params=params)
    data = r.json()

    TEAMS_CACHE = []

    for t in data["response"]:
        TEAMS_CACHE.append({
            "id": t["team"]["id"],
            "name": t["team"]["name"]
        })

    print("Times carregados:", len(TEAMS_CACHE))


# =============================
# SIMILARIDADE DE TEXTO
# =============================
def similar(a, b):
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


# =============================
# BUSCA INTELIGENTE
# =============================
def buscar_time(nome_usuario):

    melhor = None
    melhor_score = 0

    for team in TEAMS_CACHE:
        score = similar(nome_usuario, team["name"])

        if score > melhor_score:
            melhor_score = score
            melhor = team

    if melhor_score < 0.4:
        return None

    return melhor["id"], melhor["name"]


# =============================
# PRÓXIMO JOGO
# =============================
def proximo_jogo(team_id):

    url = f"{BASE_URL}/fixtures"
    params = {
        "team": team_id,
        "next": 1
    }

    r = requests.get(url, headers=HEADERS, params=params)
    data = r.json()

    if data["results"] == 0:
        return None

    jogo = data["response"][0]

    home = jogo["teams"]["home"]["name"]
    away = jogo["teams"]["away"]["name"]

    return f"{home} vs {away}"


# =============================
# MODELO IA (base)
# =============================
def estimar_gols(nome):
    import random
    return round(random.uniform(0.9, 2.6), 2)


# =============================
# /start
# =============================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 IA MATCHUP VIRTUAL ONLINE\n\n"
        "Use:\n"
        "/match Palmeiras vs Blooming"
    )


# =============================
# /match
# =============================
async def match(update: Update, context: ContextTypes.DEFAULT_TYPE):

    texto = " ".join(context.args)

    if "vs" not in texto.lower():
        await update.message.reply_text("Use:\n/match Time A vs Time B")
        return

    timeA_nome, timeB_nome = texto.lower().split("vs")

    timeA_nome = timeA_nome.strip()
    timeB_nome = timeB_nome.strip()

    await update.message.reply_text("🔎 Buscando jogos mundiais...")

    timeA = buscar_time(timeA_nome)
    timeB = buscar_time(timeB_nome)

    if not timeA:
        await update.message.reply_text(f"❌ Não encontrei {timeA_nome}")
        return

    if not timeB:
        await update.message.reply_text(f"❌ Não encontrei {timeB_nome}")
        return

    idA, nomeA = timeA
    idB, nomeB = timeB

    jogoA = proximo_jogo(idA)
    jogoB = proximo_jogo(idB)

    if not jogoA or not jogoB:
        await update.message.reply_text("❌ Não achei jogos futuros.")
        return

    golsA = estimar_gols(nomeA)
    golsB = estimar_gols(nomeB)

    if golsA > golsB:
        vencedor = nomeA
    elif golsB > golsA:
        vencedor = nomeB
    else:
        vencedor = "EMPATE"

    resposta = f"""
⚔️ MATCHUP VIRTUAL IA

🅰 {nomeA}
📅 {jogoA}
⚽ Gols estimados: {golsA}

🅱 {nomeB}
📅 {jogoB}
⚽ Gols estimados: {golsB}

🏆 Resultado:
👉 {vencedor}
"""

    await update.message.reply_text(resposta)


# =============================
# MAIN
# =============================
def main():

    carregar_times()

    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("match", match))

    print("BOT ONLINE")

    app.run_polling()


if __name__ == "__main__":
    main()
