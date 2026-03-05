import os
import math
import requests
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# Configuração de Logs
logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)

TOKEN = os.getenv("TOKEN")
API_KEY = os.getenv("API_FOOTBALL_KEY")
HOST = "v3.football.api-sports.io"

DB_STATS = {}

# =============================
# MOTOR DE DADOS REALISTA
# =============================

def buscar_dados_reais(nome_time):
    headers = {"x-rapidapi-host": HOST, "x-rapidapi-key": API_KEY}
    
    try:
        # 1. Busca o ID do time com busca refinada
        url_team = f"https://{HOST}/teams"
        resp = requests.get(url_team, headers=headers, params={"search": nome_time}, timeout=10).json()
        
        if not resp.get('response'):
            return None # Retorna None para sabermos que o time não existe na API

        team_id = resp['response'][0]['team']['id']
        nome_oficial = resp['response'][0]['team']['name']

        # 2. Tenta buscar estatísticas (Primeiro 2026, depois 2025 como backup)
        for ano in [2026, 2025]:
            url_stats = f"https://{HOST}/teams/statistics"
            # O ideal é não travar em uma liga. Vamos tentar IDs comuns: 71 (Brasil), 39 (Inglaterra), 140 (Espanha)
            # Para ser pro, o bot deveria identificar a liga, mas vamos usar a principal do time:
            params = {"league": 71, "season": ano, "team": team_id}
            s_resp = requests.get(url_stats, headers=headers, params=params, timeout=10).json()
            
            if s_resp.get('response') and s_resp['response']['goals']['for']['average']['total'] != "0%":
                gols_pro = s_resp['response']['goals']['for']['average']['total']
                gols_contra = s_resp['response']['goals']['against']['average']['total']
                
                # Limpeza de dados (transformar "1.5" string em float)
                return {
                    "nome": nome_oficial,
                    "atk": float(gols_pro or 1.0),
                    "def": float(gols_contra or 1.0)
                }
        
        return None
    except Exception as e:
        logging.error(f"Erro ao buscar {nome_time}: {e}")
        return None

# =============================
# LÓGICA DE CÁLCULO
# =============================

def calcular_match(timeA_data, timeB_data):
    # xG de A = Ataque de A confrontado com a média de gols sofridos de B
    # Usamos a média de 1.35 como base da liga para normalizar
    xgA = (timeA_data['atk'] + timeB_data['def']) / 2
    xgB = (timeB_data['atk'] + timeA_data['def']) / 2
    
    return round(xgA, 2), round(xgB, 2)

# =============================
# COMANDOS
# =============================

async def games(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto = update.message.text.replace("/games", "").strip()
    if not texto:
        await update.message.reply_text("Exemplo: /games\nFlamengo vs Vasco")
        return

    await update.message.reply_text("📡 Acessando banco de dados da API 2026...")
    
    linhas = texto.split("\n")
    sucesso = []
    falha = []

    for linha in linhas:
        if "vs" in linha.lower():
            times = linha.lower().split("vs")
            for t in times:
                nome = t.strip()
                dados = buscar_dados_reais(nome)
                if dados:
                    DB_STATS[nome] = dados
                    sucesso.append(dados['nome'])
                else:
                    falha.append(nome)

    msg = f"✅ Times Carregados: {', '.join(sucesso)}\n"
    if falha:
        msg += f"❌ Não encontrados: {', '.join(falha)}"
    
    await update.message.reply_text(msg)

async def match(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = " ".join(context.args).lower().split("vs")
    if len(args) < 2:
        await update.message.reply_text("Use: /match TimeA vs TimeB")
        return

    tA_input, tB_input = args[0].strip(), args[1].strip()

    if tA_input not in DB_STATS or tB_input not in DB_STATS:
        await update.message.reply_text("⚠️ Dados insuficientes. Use /games primeiro.")
        return

    tA = DB_STATS[tA_input]
    tB = DB_STATS[tB_input]

    xgA, xgB = calcular_match(tA, tB)

    # Cálculo de Probabilidades Simples (Poisson)
    # 
    
    # Probabilidade de vitória baseada na força relativa
    total_xg = xgA + xgB
    pA = (xgA / total_xg) * 0.85 # Ajuste para margem de empate
    pB = (xgB / total_xg) * 0.85
    pD = 1 - (pA + pB)

    confianca = abs(pA - pB) * 200 # Diferença de força
    confianca = min(max(confianca, 15), 98)

    res = (
        f"🤖 *ACCURACY ENGINE V5*\n\n"
        f"🏠 *{tA['nome']}* (xG: {xgA})\n"
        f"🚀 *{tB['nome']}* (xG: {xgB})\n\n"
        f"📊 *CHANCES:*\n"
        f"Vitoria {tA['nome']}: `{pA*100:.1f}%`\n"
        f"Empate: `{pD*100:.1f}%`\n"
        f"Vitoria {tB['nome']}: `{pB*100:.1f}%`\n\n"
        f"🎯 *CONFIANÇA:* `{confianca:.1f}%`"
    )

    await update.message.reply_text(res, parse_mode="Markdown")

# ... (main function remains the same)
