import os
import requests
from difflib import SequenceMatcher
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

TOKEN = os.getenv("TOKEN")
API_KEY = os.getenv("API_KEY")

BASE_URL = "https://v3.football.api-sports.io"
HEADERS = {"x-apisports-key": API_KEY}

# =========================
# CACHE GLOBAL
# =========================
TEAMS = []

# ligas principais mundiais
LEAGUES = [
    39,   # Premier League
    140,  # La Liga
    135,  # Serie A
    78,   # Bundesliga
    61,   # Ligue 1
    71,   # Brasileirão
    128,  # Argentina
    253,  # MLS
    2,    # Champions League
]

SEASON = 2024


# =========================
# CARREGAR TIMES DO MUNDO
# =========================
def carregar_times_global():

    global TEAMS

    print("🌍 Carregando base GLOBAL...")

    for league in LEAGUES:

        url = f"{BASE_URL}/teams"
        params = {"league": league, "season": SEASON}

        r = requests.get(url, headers=HEADERS, params=params)

        if r.status_code != 200:
            continue

        data = r.json()

        for t in data["response"]:
            TEAMS.append({
                "id": t["team"]["id"],
                "name": t["team"]["name"]
            })

    print(f"✅ {len(TEAMS)} times carregados.")


# =========================
# SIMILARIDADE
# =========================
def similar(a, b):
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


# =========================
# BUSCA GLOBAL
# =========================
def buscar_time(nome):

    melhor = None
    score_max = 0

    for team in TEAMS:
        score = similar(nome, team["name"])

        if score > score_max:
            score_max = score
            melhor = team

    if score_max < 0.35:
        return None

    return melhor["id"], melhor["name"]


# =========================
# PRÓXIMO JOGO
# =========================
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


# =========================
# MODELO IA (BASE)
# =========================
def estimar_gols(nome):

    import random

    base = random.uniform(0.9, 2.4)

    # leve bônus para gigantes (simulação IA)
    gigantes = ["real", "city", "bayern", "barcelona", "liverpool"]

    if any(g in nome.lower() for g in gigantes):
        base += 0.3

    return round(base, 2)


# =========================
# START
# =========================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text(
        "🌍 BOT IA GLOBAL ONLINE\n\n"
        "Use:\n"
        "/match Time A vs Time B"
    )


# =========================
# MATCHUP GLOBAL
# =========================
async def match(update: Update, context: ContextTypes.DEFAULT_TYPE):

    texto = " ".join(context.args)

    if "vs" not in texto.lower():
        await update.message.reply_text("Use:\n/match Arsenal vs Flamengo")
        return

    timeA_nome, timeB_nome = texto.lower().split("vs")

    timeA_nome = timeA_nome.strip()
    timeB_nome = timeB_nome.strip()

    await update.message.reply_text("🔎 Escaneando futebol mundial...")

    timeA = buscar_time(timeA_nome)
    timeB = buscar_time(timeB_nome)

    if not timeA:
        await update.message.reply_text(f"❌ Time não encontrado: {timeA_nome}")
        return

    if not timeB:
        await update.message.reply_text(f"❌ Time não encontrado: {timeB_nome}")
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
⚔️ MATCHUP VIRTUAL GLOBAL

🅰 {nomeA}
📅 {jogoA}
⚽ Gols IA: {golsA}

🅱 {nomeB}
📅 {jogoB}
⚽ Gols IA: {golsB}

🏆 Vencedor Virtual:
👉 {vencedor}
"""

    await update.message.reply_text(resposta)


# =========================
# MAIN
# =========================
def main():

    carregar_times_global()

    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("match", match))

    print("🤖 BOT GLOBAL ONLINE")

    app.run_polling()


if __name__ == "__main__":
    main()
