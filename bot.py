import os
import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

TOKEN = os.getenv("TOKEN")
API_KEY = os.getenv("API_KEY")

HEADERS = {
    "x-apisports-key": API_KEY
}

MEDIA_LIGA = 1.35


# ===============================
# BUSCAR TIME NA API
# ===============================
def buscar_time(nome):
    url = f"https://v3.football.api-sports.io/teams?search={nome}"
    r = requests.get(url, headers=HEADERS).json()

    if r["results"] == 0:
        return None

    return r["response"][0]["team"]["id"]


# ===============================
# PEGAR ESTATÍSTICAS
# ===============================
def pegar_stats(team_id):

    # temporada atual padrão
    url = f"https://v3.football.api-sports.io/teams/statistics?league=39&season=2023&team={team_id}"

    r = requests.get(url, headers=HEADERS).json()

    if "response" not in r:
        return None

    dados = r["response"]

    gols_marcados = dados["goals"]["for"]["average"]["total"]
    gols_sofridos = dados["goals"]["against"]["average"]["total"]

    ataque = float(gols_marcados)
    defesa = float(gols_sofridos)

    return ataque, defesa


# ===============================
# MODELO MATEMÁTICO
# ===============================
def gols_esperados(ataque, defesa_oponente):
    return round((ataque * defesa_oponente) / MEDIA_LIGA, 2)


def probabilidades(g1, g2):
    total = g1 + g2
    p1 = round((g1 / total) * 100)
    p2 = round((g2 / total) * 100)
    empate = 100 - (p1 + p2)
    return p1, empate, p2


# ===============================
# COMANDOS
# ===============================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🌍 TIPSTER IA GLOBAL ONLINE\n\n"
        "Use:\n"
        "/match TimeA x TimeB"
    )


async def match(update: Update, context: ContextTypes.DEFAULT_TYPE):

    texto = " ".join(context.args)

    if " x " not in texto.lower():
        await update.message.reply_text("Use: /match TimeA x TimeB")
        return

    time_a, time_b = texto.split(" x ")

    await update.message.reply_text("🔎 Analisando dados globais...")

    id_a = buscar_time(time_a)
    id_b = buscar_time(time_b)

    if not id_a or not id_b:
        await update.message.reply_text("❌ Não encontrei um dos times.")
        return

    stats_a = pegar_stats(id_a)
    stats_b = pegar_stats(id_b)

    if not stats_a or not stats_b:
        await update.message.reply_text("❌ Estatísticas indisponíveis.")
        return

    ataque_a, defesa_a = stats_a
    ataque_b, defesa_b = stats_b

    gols_a = gols_esperados(ataque_a, defesa_b)
    gols_b = gols_esperados(ataque_b, defesa_a)

    p_a, empate, p_b = probabilidades(gols_a, gols_b)

    vencedor = time_a if gols_a > gols_b else time_b

    resposta = f"""
🌍 ANÁLISE GLOBAL IA

⚔️ {time_a} vs {time_b}

📊 Gols Esperados:
{time_a}: {gols_a}
{time_b}: {gols_b}

📈 Probabilidades:
{time_a}: {p_a}%
Empate: {empate}%
{time_b}: {p_b}%

🔥 Maior chance de fazer MAIS gols:
✅ {vencedor}
"""

    await update.message.reply_text(resposta)


# ===============================
# START BOT
# ===============================
app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("match", match))

print("BOT GLOBAL ONLINE")
app.run_polling()
