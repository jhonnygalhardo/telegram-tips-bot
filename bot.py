import os
import math
import requests
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# Logs para o Railway
logging.basicConfig(level=logging.INFO)

TOKEN = os.getenv("TOKEN")
API_KEY = os.getenv("API_FOOTBALL_KEY")
HOST = "v3.football.api-sports.io"

DB_STATS = {}

# =============================
# MOTOR DE BUSCA ULTRA-AGRESSIVO
# =============================

def buscar_dados_api(nome_time):
    headers = {"x-rapidapi-host": HOST, "x-rapidapi-key": API_KEY}
    
    # 1. Tenta busca exata, se falhar, tenta apenas a primeira palavra
    termos_busca = [nome_time.strip(), nome_time.split()[0]]
    
    for termo in termos_busca:
        try:
            url_team = f"https://{HOST}/teams"
            resp = requests.get(url_team, headers=headers, params={"search": termo}, timeout=10).json()
            
            if not resp.get('response'):
                continue

            # Pega o primeiro time que aparecer no resultado
            team_id = resp['response'][0]['team']['id']
            nome_oficial = resp['response'][0]['team']['name']

            # 2. Busca TODAS as ligas onde o time está presente
            url_leagues = f"https://{HOST}/leagues"
            l_resp = requests.get(url_leagues, headers=headers, params={"team": team_id}, timeout=10).json()
            
            if not l_resp.get('response'):
                continue

            # Pega as últimas 3 ligas (geralmente as mais recentes/ativas)
            ligas = [item['league']['id'] for item in l_resp['response']][-3:]

            # 3. Varre estatísticas (2025 é mais seguro se 2026 acabou de começar)
            for ano in [2026, 2025]:
                for league_id in ligas:
                    url_stats = f"https://{HOST}/teams/statistics"
                    params = {"league": league_id, "season": ano, "team": team_id}
                    s_resp = requests.get(url_stats, headers=headers, params=params, timeout=10).json()
                    
                    if s_resp.get('response'):
                        res = s_resp['response']
                        # Se tiver média de gols, capturamos
                        g_pro = res['goals']['for']['average']['total']
                        g_contra = res['goals']['against']['average']['total']
                        
                        if g_pro and g_pro != "0%":
                            return {
                                "nome": nome_oficial,
                                "atk": float(g_pro),
                                "def": float(g_contra)
                            }
        except Exception as e:
            print(f"Erro na busca: {e}")
            continue
            
    return None

# =============================
# COMANDOS
# =============================

async def games(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto = update.message.text.replace("/games", "").strip()
    if not texto:
        await update.message.reply_text("💡 Envie os jogos (ex: Lanus vs Boca)")
        return

    await update.message.reply_text("🛰️ Conectando à API Global...")
    
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
        msg = "✅ **Times Mapeados:**\n" + "\n".join([f"• {s}" for s in sucesso])
        await update.message.reply_text(msg, parse_mode="Markdown")
    else:
        await update.message.reply_text("❌ Nenhum dado encontrado. Verifique sua API_KEY no Railway.")

async def match(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Lógica de cálculo (mesma do anterior)
    # ...
    pass

# =============================
# MAIN
# =============================

if __name__ == "__main__":
    if not TOKEN or not API_KEY:
        print("❌ Chaves ausentes nas variáveis de ambiente!")
    else:
        app = ApplicationBuilder().token(TOKEN).build()
        app.add_handler(CommandHandler("games", games))
        app.run_polling(drop_pending_updates=True)
