import os
import math
import requests
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# Configuração de Logs para monitorar no Railway
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# --- VARIÁVEIS DE AMBIENTE (Configure no painel do Railway) ---
TOKEN = os.getenv("TOKEN")
API_KEY = os.getenv("API_FOOTBALL_KEY")
HOST = "v3.football.api-sports.io"

# Banco de dados temporário em memória
DB_JOGOS = {}
DB_STATS = {}

# =============================
# MOTOR DE DADOS (API FOOTBALL)
# =============================

def buscar_dados_time(nome_time):
    """Busca média de gols marcados/sofridos na API"""
    headers = {"x-rapidapi-host": HOST, "x-rapidapi-key": API_KEY}
    
    # 1. Busca ID do Time
    try:
        url_team = f"https://{HOST}/teams"
        resp = requests.get(url_team, headers=headers, params={"search": nome_time}, timeout=10).json()
        
        if not resp.get('response'):
            return 1.4, 1.2 # Fallback (médias neutras)
            
        team_id = resp['response'][0]['team']['id']
        
        # 2. Busca Stats da Temporada Atual (Ex: ID 71 = Brasileirão)
        # Nota: Você pode ajustar o league_id conforme o campeonato
        url_stats = f"https://{HOST}/teams/statistics"
        params = {"league": 71, "season": 2026, "team": team_id}
        s_resp = requests.get(url_stats, headers=headers, params=params, timeout=10).json()
        
        gols_pro = s_resp['response']['goals']['for']['average']['total']
        gols_contra = s_resp['response']['goals']['against']['average']['total']
        
        return float(gols_pro), float(gols_contra)
    except Exception as e:
        logging.error(f"Erro na API para {nome_time}: {e}")
        return 1.4, 1.2

# =============================
# LÓGICA MATEMÁTICA (TRADER)
# =============================

def calcular_poisson(lmbda, k):
    return (math.pow(lmbda, k) * math.exp(-lmbda)) / math.factorial(k)

def processar_match(xgA, xgB):
    winA = draw = winB = 0
    # Matriz 7x7 para precisão de trader
    for i in range(7):
        for j in range(7):
            prob = calcular_poisson(xgA, i) * calcular_poisson(xgB, j)
            if i > j: winA += prob
            elif j > i: winB += prob
            else: draw += prob
    return winA, draw, winB

# =============================
# COMANDOS DO BOT
# =============================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🚀 **ACCURACY ENGINE V4 ONLINE**\n\n1. Use `/games` para cadastrar a rodada.\n2. Use `/match` para analisar o duelo virtual.")

async def games(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto = update.message.text.replace("/games", "").strip()
    if not texto:
        await update.message.reply_text("⚠️ Exemplo:\n/games\nFlamengo vs Vasco\nPalmeiras vs Santos")
        return

    await update.message.reply_text("⏳ Puxando dados reais da API... (Isso pode levar alguns segundos)")
    
    linhas = texto.split("\n")
    for linha in linhas:
        if "vs" in linha.lower():
            t1, t2 = linha.lower().split("vs")
            t1, t2 = t1.strip(), t2.strip()
            
            DB_JOGOS[t1] = t2
            DB_JOGOS[t2] = t1
            
            # Busca e armazena stats
            DB_STATS[t1] = buscar_dados_time(t1)
            DB_STATS[t2] = buscar_dados_time(t2)

    await update.message.reply_text(f"✅ Rodada mapeada! {len(DB_STATS)} times prontos para análise.")

async def match(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto = " ".join(context.args).lower()
    if "vs" not in texto:
        await update.message.reply_text("❌ Use: `/match Flamengo vs Santos`")
        return

    tA_nome, tB_nome = texto.split("vs")
    tA_nome, tB_nome = tA_nome.strip(), tB_nome.strip()

    if tA_nome not in DB_STATS or tB_nome not in DB_STATS:
        await update.message.reply_text("❌ Times não encontrados. Cadastre-os primeiro com `/games`.")
        return

    # Dados reais coletados
    atkA, defA = DB_STATS[tA_nome]
    atkB, defB = DB_STATS[tB_nome]

    # xG Cruzado (Ataque de um vs Defesa do outro)
    xgA = round(atkA * (defB / 1.3), 2)
    xgB = round(atkB * (defA / 1.3), 2)

    pA, pD, pB = processar_match(xgA, xgB)

    # Confiança baseada na margem de probabilidade
    conf = (abs(pA - pB) + pD) * 100
    conf_final = min(max(conf, 10), 96.5)

    res = (
        f"📊 *ANÁLISE DE MATCHUP VIRTUAL*\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🏠 *{tA_nome.upper()}* (xG: {xgA})\n"
        f"🚀 *{tB_nome.upper()}* (xG: {xgB})\n\n"
        f"📈 *PROBABILIDADES:*\n"
        f"Win {tA_nome.upper()}: `{pA*100:.1f}%` (Odd: `{1/pA:.2f}`)\n"
        f"Empate: `{pD*100:.1f}%` (Odd: `{1/pD:.2f}`)\n"
        f"Win {tB_nome.upper()}: `{pB*100:.1f}%` (Odd: `{1/pB:.2f}`)\n\n"
        f"🛡️ *CONFIANÇA IA:* `{conf_final:.1f}%`"
    )

    await update.message.reply_text(res, parse_mode="Markdown")

# =============================
# INICIALIZAÇÃO
# =============================

if __name__ == "__main__":
    app = ApplicationBuilder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("games", games))
    app.add_handler(CommandHandler("match", match))
    
    print("🤖 ENGINE V4 RODANDO NO RAILWAY...")
    app.run_polling()
