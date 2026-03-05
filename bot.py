import os
import requests
import logging
import asyncio
import unicodedata
import difflib
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# =============================
# CONFIGURAÇÃO
# =============================
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = os.getenv("TOKEN")
API_KEY = os.getenv("API_FOOTBALL_KEY")
HOST = "v3.football.api-sports.io"

DB_STATS = {}

# =============================
# FUNÇÕES AUXILIARES
# =============================
def normalize(text):
    """Remove acentos e coloca em lowercase"""
    text = unicodedata.normalize('NFKD', text)
    text = "".join([c for c in text if not unicodedata.combining(c)])
    return text.lower().strip()

def find_best_team(name, teams_list):
    """Usa difflib para escolher o time mais próximo"""
    names_normalized = [normalize(t['team']['name']) for t in teams_list]
    match = difflib.get_close_matches(normalize(name), names_normalized, n=1, cutoff=0.5)
    if match:
        index = names_normalized.index(match[0])
        return teams_list[index]['team']
    return None

def get_last_season_with_stats(team_id):
    """Retorna a última temporada que tem jogos do time"""
    headers = {"x-rapidapi-host": HOST, "x-rapidapi-key": API_KEY}
    for ano in [2026, 2025, 2024, 2023]:
        res_l = requests.get(
            f"https://{HOST}/leagues",
            headers=headers,
            params={"team": team_id, "season": ano},
            timeout=10
        ).json()
        if res_l.get('response'):
            for league in res_l['response']:
                # Verifica se há estatísticas
                res_s = requests.get(
                    f"https://{HOST}/teams/statistics",
                    headers=headers,
                    params={"league": league['league']['id'], "season": ano, "team": team_id},
                    timeout=10
                ).json()
                if res_s.get('response') and res_s['response'].get('fixtures', {}).get('played', {}).get('total', 0) > 0:
                    return league['league']['id'], league['league']['name'], ano
    return None, None, None

# =============================
# COMANDO /games
# =============================
async def games(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto = update.message.text.replace("/games", "").strip()
    if "vs" not in texto.lower():
        await update.message.reply_text("❌ Use: /games TimeA vs TimeB")
        return

    await update.message.reply_text("📡 Buscando estatísticas reais...")

    times_input = [t.strip() for t in texto.lower().split("vs")]
    headers = {"x-rapidapi-host": HOST, "x-rapidapi-key": API_KEY}

    for nome in times_input:
        try:
            # Busca times
            res_t = requests.get(
                f"https://{HOST}/teams",
                headers=headers,
                params={"search": nome},
                timeout=10
            ).json()

            if not res_t.get('response'):
                await update.message.reply_text(f"❌ Nenhum time encontrado para '{nome}'.")
                continue

            # Escolhe o melhor match
            best_team = find_best_team(nome, res_t['response'])
            if not best_team:
                await update.message.reply_text(f"❌ Não foi possível identificar o time '{nome}'.")
                continue

            t_id = best_team['id']
            t_nome = best_team['name']

            # Última temporada com estatísticas
            l_id, l_nome, ano = get_last_season_with_stats(t_id)
            if not l_id:
                await update.message.reply_text(f"⚠️ {t_nome} sem jogos registrados em ligas recentes.")
                continue

            # Busca estatísticas
            res_s = requests.get(
                f"https://{HOST}/teams/statistics",
                headers=headers,
                params={"league": l_id, "season": ano, "team": t_id},
                timeout=10
            ).json()

            st = res_s['response']
            played = st.get('fixtures', {}).get('played', {}).get('total', 0)
            g_for = st.get('goals', {}).get('for', {}).get('total', {}).get('total', 0)
            g_against = st.get('goals', {}).get('against', {}).get('total', {}).get('total', 0)

            if played and played > 0:
                m_atk = round(g_for / played, 2)
                m_def = round(g_against / played, 2)
                DB_STATS[normalize(nome)] = {"nome": t_nome, "atk": m_atk, "def": m_def}

                await update.message.reply_text(
                    f"✅ **{t_nome}** ({ano})\n🏆 {l_nome}\n🏟️ Jogos: {played}\n⚽ Atq: `{m_atk}` | Def: `{m_def}`"
                )
            else:
                await update.message.reply_text(f"⚠️ {t_nome} não possui jogos registrados.")

        except Exception as e:
            logger.error(f"Erro ao processar '{nome}': {e}")
            await update.message.reply_text(f"💥 Erro ao buscar {nome}.")

# =============================
# COMANDO /match
# =============================
async def match(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if not context.args:
            await update.message.reply_text("❌ Use: /match TimeA vs TimeB")
            return

        args = " ".join(context.args).lower().split("vs")
        if len(args) < 2:
            await update.message.reply_text("❌ Use: /match TimeA vs TimeB")
            return

        tA, tB = normalize(args[0].strip()), normalize(args[1].strip())

        if tA not in DB_STATS or tB not in DB_STATS:
            await update.message.reply_text("⚠️ Um dos times não possui estatísticas. Rode /games primeiro.")
            return

        dA, dB = DB_STATS[tA], DB_STATS[tB]

        # xG simplificado
        xgA = round((dA['atk'] + dB['def']) / 2, 2)
        xgB = round((dB['atk'] + dA['def']) / 2, 2)

        # Determinar resultado histórico
        if abs(xgA - xgB) < 0.5:
            resultado = "Equilibrio / Empate"
        else:
            resultado = f"Vitoria {dA['nome']}" if xgA > xgB else f"Vitoria {dB['nome']}"

        await update.message.reply_text(
            f"🔥 **{dA['nome']}** ({xgA}) vs **{dB['nome']}** ({xgB})\n\n🎯 Resultado Sugerido: `{resultado}`"
        )

    except Exception as e:
        logger.error(f"Erro no Match: {e}")
        await update.message.reply_text("❌ Erro no Match.")

# =============================
# MAIN
# =============================
if __name__ == "__main__":
    if not TOKEN or not API_KEY:
        logger.error("❌ TOKEN ou API_FOOTBALL_KEY não configurado.")
        exit(1)

    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("games", games))
    app.add_handler(CommandHandler("match", match))

    asyncio.run(app.run_polling())
