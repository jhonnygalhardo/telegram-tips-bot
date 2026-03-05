import os
import math
import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# --- CONFIGURAÇÃO ---
API_KEY = "SUA_CHAVE_AQUI"
TOKEN = os.getenv("TOKEN")

# Cache para armazenar os dados da API e não gastar créditos à toa
DB_JOGOS = {} 
DB_STATS = {}

# =============================
# BUSCA DE DADOS NA API
# =============================

def buscar_stats_api(nome_time):
    """Busca média de gols reais na API-Football"""
    url = "https://v3.football.api-sports.io/teams"
    headers = {"x-rapidapi-key": API_KEY, "x-rapidapi-host": "v3.football.api-sports.io"}
    
    # 1. Acha o ID do time
    resp = requests.get(url, headers=headers, params={"search": nome_time}).json()
    if not resp['response']: return 1.0, 1.0
    
    team_id = resp['response'][0]['team']['id']
    
    # 2. Busca estatísticas da temporada (Ex: ID 71 é Brasileirão)
    stats_url = "https://v3.football.api-sports.io/teams/statistics"
    params = {"league": 71, "season": 2025, "team": team_id}
    s_resp = requests.get(stats_url, headers=headers, params=params).json()
    
    try:
        # Média de gols marcados (Ataque) e sofridos (Defesa)
        ataque = s_resp['response']['goals']['for']['average']['total']
        defesa = s_resp['response']['goals']['against']['average']['total']
        return float(ataque), float(defesa)
    except:
        return 1.3, 1.1 # Média padrão caso falhe

# =============================
# COMANDOS
# =============================

async def games(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto = update.message.text.replace("/games", "").strip()
    linhas = texto.split("\n")
    
    await update.message.reply_text("⏳ Puxando estatísticas reais da API... Aguarde.")

    for l in linhas:
        if "vs" in l.lower():
            t1, t2 = l.lower().split("vs")
            t1, t2 = t1.strip(), t2.strip()
            
            # Salva quem enfrenta quem
            DB_JOGOS[t1] = t2
            DB_JOGOS[t2] = t1
            
            # Puxa e guarda as stats de cada um
            DB_STATS[t1] = buscar_stats_api(t1)
            DB_STATS[t2] = buscar_stats_api(t2)

    await update.message.reply_text(f"✅ {len(DB_JOGOS)//2} Jogos e Stats carregados com sucesso!")

async def match(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = " ".join(context.args).lower().split("vs")
    tA, tB = args[0].strip(), args[1].strip()

    if tA not in DB_STATS or tB not in DB_STATS:
        await update.message.reply_text("❌ Time não encontrado no /games.")
        return

    # Lógica de Cruzamento: Ataque de A vs Defesa do adversário real de A
    # Para o Matchup: Usamos a força relativa
    atkA, defA = DB_STATS[tA]
    atkB, defB = DB_STATS[tB]

    # xG Final calculado para o Duelo
    xgA = round(atkA * (defB / 1.2), 2)
    xgB = round(atkB * (defA / 1.2), 2)

    # Calculo de Probabilidades (Poisson simplificado para o exemplo)
    # 
    probA = (xgA / (xgA + xgB)) * 0.8  # Exemplo de lógica rápida
    probB = (xgB / (xgA + xgB)) * 0.8
    probD = 1 - (probA + probB)

    # Nível de Confiança (Baseado na discrepância de xG e estabilidade)
    confianca = (abs(xgA - xgB) / max(xgA, xgB)) * 100
    confianca = min(max(confianca + 40, 20), 98)

    res = (
        f"🤖 *ACCURACY ENGINE PRO*\n\n"
        f"⚔️ *{tA.upper()}* vs *{tB.upper()}*\n"
        f"📊 xG: `{xgA}` vs `{xgB}`\n\n"
        f"🏠 Vit. {tA}: `{probA*100:.1f}%`\n"
        f"🤝 Empate: `{probD*100:.1f}%`\n"
        f"🚀 Vit. {tB}: `{probB*100:.1f}%`\n\n"
        f"🎯 *CONFIANÇA:* `{confianca:.1f}%`"
    )

    await update.message.reply_text(res, parse_mode="Markdown")
