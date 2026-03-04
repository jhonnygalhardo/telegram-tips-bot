import os
import requests
from difflib import get_close_matches
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

TOKEN = os.getenv("TOKEN")

API_KEY = "SUA_API_KEY_API_FOOTBALL"
BASE_URL = "https://v3.football.api-sports.io"

HEADERS = {
    "x-apisports-key": API_KEY
}

# =============================
# BUSCAR TIME (FUZZY SEARCH)
# =============================
def buscar_time(nome):
    url = f"{BASE_URL}/teams"
    params = {"search": nome}

    r = requests.get(url, headers=HEADERS, params=params)
    data = r.json()

    if data["results"] == 0:
        return None

    return data["response"][0]["team"]["id"], data["response"][0]["team"]["name"]


# =============================
# PEGAR PRÓXIMO JOGO
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

    return home, away


# =============================
# GERAR GOLS ESTIMADOS (IA BASE)
# =============================
def estimar_gols(nome_time):
    # modelo inicial (vamos evoluir depois)
    import random
    return round(random.uniform(0.8, 2.5), 2)


# =============================
# COMANDO START
# =============================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 BOT IA DE MATCHUP VIRTUAL ONLINE\n\n"
        "Use:\n"
        "/match Time A vs Time B"
    )


# =============================
# MATCHUP VIRTUAL
# =============================
async def match(update: Update, context: ContextTypes.DEFAULT_TYPE):

    texto = " ".join(context.args)

    if "vs" not in texto.lower():
        await update.message.reply_text("Use:\n/match Arsenal vs Liverpool")
        return

    timeA_nome, timeB_nome = texto.split("vs")

    timeA_nome = timeA_nome.strip()
    timeB_nome = timeB_nome.strip()

    await update.message.reply_text("🔎 Analisando jogos mundiais...")

    # buscar times
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

    if not jogoA:
        await update.message.reply_text(f"Sem jogos próximos para {nomeA}")
        return

    if not jogoB:
        await update.message.reply_text(f"Sem jogos próximos para {nomeB}")
        return

    golsA = estimar_gols(nomeA)
    golsB = estimar_gols(nomeB)

    # resultado virtual
    if golsA > golsB:
        vencedor = nomeA
    elif golsB > golsA:
        vencedor = nomeB
    else:
        vencedor = "EMPATE"

    resposta = f"""
⚔️ MATCHUP VIRTUAL IA

🅰 {nomeA}
Jogo real: {jogoA[0]} vs {jogoA[1]}
Gols estimados: {golsA}

🅱 {nomeB}
Jogo real: {jogoB[0]} vs {jogoB[1]}
Gols estimados: {golsB}

🏆 Resultado Virtual:
👉 {vencedor}
"""

    await update.message.reply_text(resposta)


# =============================
# MAIN
# =============================
def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("match", match))

    print("BOT ONLINE")

    app.run_polling()


if __name__ == "__main__":
    main()
