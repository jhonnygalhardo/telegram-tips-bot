import os
import requests
import math
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# Configurações de Log para você ver no Railway
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = os.getenv("TOKEN")
API_KEY = os.getenv("API_FOOTBALL_KEY")
HOST = "v3.football.api-sports.io"

DB_STATS = {}

async def games(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto = update.message.text.replace("/games", "").strip()
    if "vs" not in texto.lower():
        await update.message.reply_text("❌ Formato: /games Time A vs Time B")
        return

    await update.message.reply_text("📡 Varrendo TODAS as ligas disponíveis...")

    times_input = [t.strip() for t in texto.lower().split("vs")]
    headers = {"x-rapidapi-host": HOST, "x-rapidapi-key": API_KEY}

    for nome in times_input:
        try:
            # 1. Busca ID do Time
            res_t = requests.get(f"https://{HOST}/teams", headers=headers, params={"search": nome}, timeout=10).json()
            if not res_t.get('response'):
                await update.message.reply_text(f"❌ Time '{nome}' não encontrado.")
                continue

            t_id = res_t['response'][0]['team']['id']
            t_nome = res_t['response'][0]['team']['name']

            # 2. Busca as Ligas desse time (focando em 2025/2026)
            encontrou_gols = False
            for ano in [2026, 2025]:
                # Puxa todas as ligas do time naquele ano
                res_l = requests.get(f"https://{HOST}/leagues", headers=headers, params={"team": t_id, "season": ano}, timeout=10).json()
                
                if not res_l.get('response'): continue

                for item in res_l['response']:
                    league_id = item['league']['id']
                    league_name = item['league']['name']

                    # 3. Puxa estatística da liga encontrada
                    res_s = requests.get(f"https://{HOST}/teams/statistics", headers=headers, 
                                         params={"league": league_id, "season": ano, "team": t_id}, timeout=10).json()
                    
                    if res_s.get('response'):
                        st = res_s['response']['goals']
                        atk = st['for']['average']['total']
                        dfs = st['against']['average']['total']

                        # Se atk não for nulo e for maior que 0
                        if atk and float(atk) > 0:
                            DB_STATS[nome.lower()] = {"nome": t_nome, "atk": float(atk), "def": float(dfs)}
                            await update.message.reply_text(f"✅ {t_nome} mapeado!\n🏆 {league_name} ({ano})\n⚽ Atq: {atk} | Def: {dfs}")
                            encontrou_gols = True
                            break
                if encontrou_gols: break

            if not encontrou_gols:
                await update.message.reply_text(f"⚠️ {t_nome} encontrado, mas a API não tem médias de gols processadas para ele.")

        except Exception as e:
            await update.message.reply_text(f"💥 Erro em {nome}: {str(e)}")

async def match(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # (A lógica do /match continua a mesma para processar os dados salvos)
    args = " ".join(context.args).lower().split("vs")
    if len(args) < 2: return
    tA_in, tB_in = args[0].strip(), args[1].strip()
    
    if tA_in in DB_STATS and tB_in in DB_STATS:
        dA, dB = DB_STATS[tA_in], DB_STATS[tB_in]
        xgA = (dA['atk'] + dB['def']) / 2
        xgB = (dB['atk'] + dA['atk']) / 2 # Ajustado para força relativa
        await update.message.reply_text(f"🔥 **{dA['nome']}** ({xgA:.2f}) vs **{dB['nome']}** ({xgB:.2f})")
    else:
        await update.message.reply_text("❌ Use /games primeiro.")

if __name__ == "__main__":
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("games", games))
    app.add_handler(CommandHandler("match", match))
    app.run_polling(drop_pending_updates=True)
