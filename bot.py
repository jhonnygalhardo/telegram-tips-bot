import os
import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# ==============================
# CONFIG
# ==============================

BOT_TOKEN = os.getenv("TOKEN")  # variável do Railway
API_KEY = "SUA_API_KEY_AQUI"    # https://www.api-football.com/

BASE_URL = "https://v3.football.api-sports.io"

HEADERS = {
    "x-apisports-key": API_KEY
}

# ==============================
# FUNÇÕES API
# ==============================

def buscar_time(nome_time):
    url = f"{BASE_URL}/teams"
    params = {"search": nome_time}

    r = requests.get(url, headers=HEADERS, params=params)
    data = r.json()

    if data["results"] == 0:
        return None

    return data["response"][0]["team"]["id"]


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

    return {
        "home": home,
        "away": away,
        "fixture_id": jogo["fixture"]["id"]
    }


def previsao_gols(fixture_id):
    url = f"{BASE_URL}/predictions"
    params = {"fixture": fixture_id}

    r = requests.get(url, headers=HEADERS, params=params)
    data = r.json()

    if data["results"] == 0:
        return None

    gols_home = float(data["response"][0]["predictions"]["goals"]["home"])
    gols_away = float(data["response"][0]["predictions"]["goals"]["away"])

    return gols_home, gols_away


# ==============================
# COMANDOS TELEGRAM
# ==============================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "✅ Bot ONLINE!\n\nUse:\n/match Time A vs Time B"
    )


async def match(update: Update, context: ContextTypes.DEFAULT_TYPE):

    try:
        texto = " ".join(context.args)

        if " vs " not in texto.lower():
            await update.message.reply_text(
                "Formato correto:\n/match Palmeiras vs Flamengo"
            )
            return

        partes = texto.lower().split(" vs ")

        time_a_nome = partes[0].strip()
        time_b_nome = partes[1].strip()

        await update.message.reply_text("🔎 Buscando jogos reais...")

        # Buscar IDs
        time_a_id = buscar_time(time_a_nome)
        if not time_a_id:
            await update.message.reply_text(f"❌ Não encontrei o time {time_a_nome}")
            return

        time_b_id = buscar_time(time_b_nome)
        if not time_b_id:
            await update.message.reply_text(f"❌ Não encontrei o time {time_b_nome}")
            return

        # Próximos jogos
        jogo_a = proximo_jogo(time_a_id)
        jogo_b = proximo_jogo(time_b_id)

        if not jogo_a:
            await update.message.reply_text(f"❌ {time_a_nome} sem jogos futuros.")
            return

        if not jogo_b:
            await update.message.reply_text(f"❌ {time_b_nome} sem jogos futuros.")
            return

        # Previsões
        gols_a = previsao_gols(jogo_a["fixture_id"])
        gols_b = previsao_gols(jogo_b["fixture_id"])

        if not gols_a or not gols_b:
            await update.message.reply_text("❌ Não consegui prever os gols.")
            return

        gols_time_a = gols_a[0] if jogo_a["home"].lower() == time_a_nome else gols_a[1]
        gols_time_b = gols_b[0] if jogo_b["home"].lower() == time_b_nome else gols_b[1]

        # Resultado virtual
        if gols_time_a > gols_time_b:
            vencedor = f"🏆 {time_a_nome.upper()} VENCE O MATCHUP"
        elif gols_time_b > gols_time_a:
            vencedor = f"🏆 {time_b_nome.upper()} VENCE O MATCHUP"
        else:
            vencedor = "🤝 EMPATE NO MATCHUP"

        resposta = f"""
⚔️ MATCHUP VIRTUAL

{time_a_nome.title()}
Jogo real: {jogo_a['home']} vs {jogo_a['away']}
Gols previstos: {gols_time_a:.2f}

🆚

{time_b_nome.title()}
Jogo real: {jogo_b['home']} vs {jogo_b['away']}
Gols previstos: {gols_time_b:.2f}

====================
{vencedor}
"""

        await update.message.reply_text(resposta)

    except Exception as e:
        await update.message.reply_text(f"Erro interno:\n{e}")


# ==============================
# MAIN
# ==============================

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("match", match))

    print("BOT ONLINE...")
    app.run_polling()


if __name__ == "__main__":
    main()
