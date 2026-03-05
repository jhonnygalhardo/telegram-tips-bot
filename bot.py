import os
import math
import requests
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# Logs para o Railway
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = os.getenv("TOKEN")
API_KEY = os.getenv("API_FOOTBALL_KEY")
HOST = "v3.football.api-sports.io"

# Cache de estatísticas para evitar excesso de chamadas à API
DB_STATS = {}

# =============================
# FUNÇÕES DE APOIO
# =============================

def buscar_stats(nome_time):
    headers = {"x-rapidapi-host": HOST, "x-rapidapi-key": API_KEY}
    try:
        # Busca o ID do time
        r = requests.get(f"https://{HOST}/teams", headers=headers, params={"search": nome_time}, timeout=10).json()
        if not r.get('response'): return None
        
        t_id = r['response'][0]['team']['id']
        t_nome = r['response'][0]['team']['name']

        # Busca estatísticas (Tentando 2026, depois 2025)
        for ano in [2026, 2025]:
            # Nota: ID 71 (Brasil), 39 (EPL), 140 (Espanha). 
            # Para ser pro, tentamos buscar a liga principal do time.
            s = requests.get(f"https://{HOST}/teams/statistics", headers=headers, 
                             params={"team": t_id, "season": ano, "league": 71}, timeout=10).json()
            
            if s.get('response') and s['response']['goals']['for']['average']['total']:
                atk = float(s['response']['goals']['for']['average']['total'])
                defe = float(s['response']['goals']['against']['average']['total'])
                return {"nome": t_nome, "atk": atk, "def": defe}
        return None
    except:
        return None

def calcular_probabilidades(xgA, xgB):
    winA = draw = winB = 0
    for i in range(8):
        for j in range(8):
            prob = ((math.pow(xgA, i) * math.exp(-xgA)) / math.factorial(i)) * \
                   ((math.pow(xgB, j) * math.exp(-xgB)) / math.factorial(j))
            if i > j: winA += prob
            elif j > i: winB += prob
            else: draw += prob
    return winA, draw, winB

# =============================
# COMANDOS DO BOT
# =============================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🚀 **ACCURACY ENGINE V6**\nUse /games para carregar e /match para analisar.")

async def games(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto = update.message.text.replace("/games", "").strip()
    if not texto:
        await update.message.reply_text("Informe os jogos. Ex: Flamengo vs Vasco")
        return

    await update.message.reply_text("⏳ Puxando dados reais da API...")
    
    linhas = texto.split("\n")
    for linha in linhas:
        if "vs" in linha.lower():
            times = linha.lower().split("vs")
            for t in times:
                nome = t.strip()
                res = buscar_stats(nome)
                if res: DB_STATS[nome] = res

    await update.message.reply_text(f"✅ Dados de {len(DB_STATS)} times prontos.")

async def match(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = " ".join(context.args).lower().split("vs")
    if len(args) < 2:
        await update.message.reply_text("Use: /match TimeA vs TimeB")
        return

    tA_in, tB_in = args[0].strip(), args[1].strip()

    if tA_in not in DB_STATS or tB_in not in DB_STATS:
        await update.message.reply_text("❌ Times não encontrados no /games.")
        return

    tA = DB_STATS[tA_in]
    tB = DB_STATS[tB_input]

    # Lógica de Cruzamento: Ataque de A vs Defesa de B
    xgA = round((tA['atk'] + tB['def']) / 2, 2)
    xgB = round((tB['atk'] + tA['def']) / 2, 2)

    pA, pD, pB = calcular_probabilidades(xgA, xgB)
    
    conf = min(max((abs(pA - pB) + pD) * 100, 20), 98)

    resposta = (
        f"📊 *ANÁLISE PROFISSIONAL*\n\n"
        f"🏠 *{tA['nome']}* (xG: {xgA})\n"
        f"🚀 *{tB['nome']}* (xG: {xgB})\n\n"
        f"📈 Probabilidades:\n"
        f"Win {tA['nome']}: `{pA*100:.1f}%` (Odd: `{1/pA:.2f}`)\n"
        f"Empate: `{pD*100:.1f}%` (Odd: `{1/pD:.2f}`)\n"
        f"Win {tB['nome']}: `{pB*100:.1f}%` (Odd: `{1/pB:.2f}`)\n\n"
        f"🛡️ *CONFIANÇA:* `{conf:.1f}%`"
    )
    await update.message.reply_text(resposta, parse_mode="Markdown")

# =============================
# MAIN
# =============================

if __name__ == "__main__":
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("games", games))
    app.add_handler(CommandHandler("match", match))
    app.run_polling(drop_pending_updates=True)
