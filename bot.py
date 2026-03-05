import os
import math
import requests
import logging
import unicodedata
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# Configuração de Logs
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Variáveis de Ambiente
TOKEN = os.getenv("TOKEN")
API_KEY = os.getenv("API_FOOTBALL_KEY")
HOST = "v3.football.api-sports.io"

# Banco de Dados em Memória
DB_STATS = {}

# =============================
# UTILITÁRIOS
# =============================

def remover_acentos(texto):
    return "".join(c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn')

# =============================
# MOTOR DE DADOS MULTILIGA
# =============================

def buscar_dados_api(nome_time):
    headers = {"x-rapidapi-host": HOST, "x-rapidapi-key": API_KEY}
    nome_busca = remover_acentos(nome_time).strip()
    
    try:
        # 1. Busca ID do Time
        url_team = f"https://{HOST}/teams"
        resp = requests.get(url_team, headers=headers, params={"search": nome_busca}, timeout=10).json()
        
        if not resp.get('response'):
            return None

        team_id = resp['response'][0]['team']['id']
        nome_oficial = resp['response'][0]['team']['name']

        # 2. Busca Stats em múltiplas ligas (Argentina, Brasil, Inglaterra, Espanha, etc)
        # 128: Argentina, 71: Brasil, 39: Premier League, 140: La Liga
        ligas_para_testar = [128, 71, 39, 140, 2, 3] # Adicionado Copa Libertadores (13) e Champions (2)
        
        for ano in [2026, 2025]:
            for league_id in ligas_para_testar:
                url_stats = f"https://{HOST}/teams/statistics"
                params = {"league": league_id, "season": ano, "team": team_id}
                s_resp = requests.get(url_stats, headers=headers, params=params, timeout=10).json()
                
                if s_resp.get('response'):
                    stats = s_resp['response']['goals']['for']['average']
                    if stats['total'] and stats['total'] != "0":
                        g_pro = float(s_resp['response']['goals']['for']['average']['total'])
                        g_contra = float(s_resp['response']['goals']['against']['average']['total'])
                        
                        return {"nome": nome_oficial, "atk": g_pro, "def": g_contra}
        return None
    except Exception as e:
        logger.error(f"Erro na API para {nome_time}: {e}")
        return None

# =============================
# CÁLCULOS MATEMÁTICOS
# =============================

def calcular_poisson(lmbda, k):
    return (math.pow(lmbda, k) * math.exp(-lmbda)) / math.factorial(k)

def obter_probabilidades(xgA, xgB):
    winA = draw = winB = 0
    for i in range(8):
        for j in range(8):
            prob = calcular_poisson(xgA, i) * calcular_poisson(xgB, j)
            if i > j: winA += prob
            elif j > i: winB += prob
            else: draw += prob
    return winA, draw, winB

# =============================
# COMANDOS TELEGRAM
# =============================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🚀 **ACCURACY ENGINE V6**\n\nEnvie os jogos com `/games` para carregar as estatísticas da API.")

async def games(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto = update.message.text.replace("/games", "").strip()
    if not texto:
        await update.message.reply_text("Exemplo: /games\nBoca Juniors vs Lanus")
        return

    await update.message.reply_text("⏳ Puxando dados reais da API... (Ligas: ARG, BRA, EUR)")
    
    linhas = texto.split("\n")
    carregados = 0
    for linha in linhas:
        if "vs" in linha.lower():
            times = linha.lower().split("vs")
            for t in times:
                nome = t.strip()
                if nome not in DB_STATS:
                    dados = buscar_dados_api(nome)
                    if dados:
                        DB_STATS[nome] = dados
                        carregados += 1

    await update.message.reply_text(f"✅ {carregados} novos times prontos para o Match!")

async def match(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        args = " ".join(context.args).lower().split("vs")
        tA_in, tB_in = args[0].strip(), args[1].strip()

        if tA_in not in DB_STATS or tB_in not in DB_STATS:
            await update.message.reply_text("❌ Time não mapeado. Use /games primeiro.")
            return

        tA, tB = DB_STATS[tA_in], DB_STATS[tB_in]

        # xG Cruzado: Força de ataque de A contra defesa de B
        xgA = (tA['atk'] + tB['def']) / 2
        xgB = (tB['atk'] + tA['def']) / 2

        pA, pD, pB = obter_probabilidades(xgA, xgB)
        
        # Cálculo de Confiança Trader
        conf = (abs(pA - pB) * 1.5 + pD) * 100
        conf = min(max(conf, 20), 98)

        res = (
            f"📊 *ANÁLISE PROFISSIONAL*\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"🏠 *{tA['nome']}* (xG: {xgA:.2f})\n"
            f"🚀 *{tB['nome']}* (xG: {xgB:.2f})\n\n"
            f"📈 *CHANCES:*\n"
            f"Vit. {tA['nome']}: `{pA*100:.1f}%`\n"
            f"Empate: `{pD*100:.1f}%`\n"
            f"Vit. {tB['nome']}: `{pB*100:.1f}%`\n\n"
            f"🎯 *CONFIANÇA IA:* `{conf:.1f}%`"
        )
        await update.message.reply_text(res, parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text("⚠️ Use: /match TimeA vs TimeB")

# =============================
# MAIN
# =============================

if __name__ == "__main__":
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("games", games))
    app.add_handler(CommandHandler("match", match))
    
    print("🤖 IA V6 EM OPERAÇÃO")
    app.run_polling(drop_pending_updates=True)
