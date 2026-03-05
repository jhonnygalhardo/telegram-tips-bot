import os
import math
import requests
import logging
import unicodedata
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# Configuração de Logs para o Railway
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = os.getenv("TOKEN")
API_KEY = os.getenv("API_FOOTBALL_KEY")
HOST = "v3.football.api-sports.io"

DB_STATS = {}

def remover_acentos(texto):
    return "".join(c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn')

# =============================
# MOTOR DE BUSCA SNIPER
# =============================

def buscar_dados_api(nome_time):
    headers = {"x-rapidapi-host": HOST, "x-rapidapi-key": API_KEY}
    nome_busca = remover_acentos(nome_time).strip()
    
    try:
        # 1. Busca ID do Time (Busca Global)
        url_team = f"https://{HOST}/teams"
        resp = requests.get(url_team, headers=headers, params={"search": nome_busca}, timeout=10).json()
        
        if not resp.get('response'):
            # Segunda tentativa: busca apenas a primeira palavra
            primeira_palavra = nome_busca.split()[0]
            resp = requests.get(url_team, headers=headers, params={"search": primeira_palavra}, timeout=10).json()

        if not resp.get('response'):
            return None

        # Pega o resultado mais relevante
        team_id = resp['response'][0]['team']['id']
        nome_oficial = resp['response'][0]['team']['name']

        # 2. Busca TODAS as ligas que esse time participa em 2025/2026
        # Em vez de fixar IDs, perguntamos à API onde esse time joga
        url_leagues = f"https://{HOST}/leagues"
        l_resp = requests.get(url_leagues, headers=headers, params={"team": team_id, "current": "true"}, timeout=10).json()
        
        ligas_encontradas = [item['league']['id'] for item in l_resp.get('response', [])]

        # 3. Varre as ligas até achar estatísticas de gols
        for ano in [2026, 2025]:
            for league_id in ligas_encontradas:
                url_stats = f"https://{HOST}/teams/statistics"
                params = {"league": league_id, "season": ano, "team": team_id}
                s_resp = requests.get(url_stats, headers=headers, params=params, timeout=10).json()
                
                if s_resp.get('response'):
                    data = s_resp['response']['goals']['for']['average']
                    if data.get('total') and data['total'] != "0":
                        g_pro = float(s_resp['response']['goals']['for']['average']['total'])
                        g_contra = float(s_resp['response']['goals']['against']['average']['total'])
                        
                        logger.info(f"✅ {nome_oficial} encontrado na Liga {league_id} ({ano})")
                        return {"nome": nome_oficial, "atk": g_pro, "def": g_contra}
        
        return None
    except Exception as e:
        logger.error(f"Erro na API para {nome_time}: {e}")
        return None

# =============================
# COMANDOS (LÓGICA REFINADA)
# =============================

async def games(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto = update.message.text.replace("/games", "").strip()
    if not texto:
        await update.message.reply_text("❌ Envie os jogos. Ex: Boca vs Lanus")
        return

    await update.message.reply_text("🔍 Buscando times no Banco de Dados Global...")
    
    linhas = texto.split("\n")
    sucesso = []
    for linha in linhas:
        if "vs" in linha.lower():
            times = linha.lower().split("vs")
            for t in times:
                nome = t.strip()
                if nome not in DB_STATS:
                    dados = buscar_dados_api(nome)
                    if dados:
                        DB_STATS[nome] = dados
                        sucesso.append(dados['nome'])

    if sucesso:
        await update.message.reply_text(f"✅ Sucesso: {', '.join(sucesso)}")
    else:
        await update.message.reply_text("❌ Nenhum time encontrado. Tente nomes mais simples.")

async def match(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        args = " ".join(context.args).lower().split("vs")
        tA_in, tB_in = args[0].strip(), args[1].strip()

        if tA_in not in DB_STATS or tB_in not in DB_STATS:
            await update.message.reply_text("❌ Use /games primeiro para carregar esses times.")
            return

        tA, tB = DB_STATS[tA_in], DB_STATS[tB_in]

        # xG Cruzado
        xgA = (tA['atk'] + tB['def']) / 2
        xgB = (tB['atk'] + tA['def']) / 2

        # Lógica de Probabilidades
        total_xg = xgA + xgB
        pA = (xgA / total_xg) * 0.82
        pB = (xgB / total_xg) * 0.82
        pD = 1 - (pA + pB)

        res = (
            f"🎯 *MATCHUP VIRTUAL*\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"👕 *{tA['nome']}* (xG: {xgA:.2f})\n"
            f"👕 *{tB['nome']}* (xG: {xgB:.2f})\n\n"
            f"📊 *PROBABILIDADES:*\n"
            f"Vitoria {tA['nome']}: `{pA*100:.1f}%`\n"
            f"Empate: `{pD*100:.1f}%`\n"
            f"Vitoria {tB['nome']}: `{pB*100:.1f}%`"
        )
        await update.message.reply_text(res, parse_mode="Markdown")
    except:
        await update.message.reply_text("Use: /match TimeA vs TimeB")

# =============================
# START E MAIN
# =============================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🚀 Accuracy Engine V7 Online!")

if __name__ == "__main__":
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("games", games))
    app.add_handler(CommandHandler("match", match))
    app.run_polling(drop_pending_updates=True)
