import os
import requests
import math
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# Log de erro para o Railway
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = os.getenv("TOKEN")
API_KEY = os.getenv("API_FOOTBALL_KEY")
HOST = "v3.football.api-sports.io"

DB_STATS = {}

async def games(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto = update.message.text.replace("/games", "").strip()
    if "vs" not in texto.lower():
        await update.message.reply_text("❌ Use: /games Time A vs Time B")
        return

    await update.message.reply_text("📡 Calculando médias brutas (Blindagem V14)...")

    times_input = [t.strip() for t in texto.lower().split("vs")]
    headers = {"x-rapidapi-host": HOST, "x-rapidapi-key": API_KEY}

    for nome in times_input:
        try:
            # 1. Busca ID do Time
            res_t = requests.get(f"https://{HOST}/teams", headers=headers, params={"search": nome}, timeout=10).json()
            if not res_t.get('response'):
                await update.message.reply_text(f"❌ '{nome}' não encontrado.")
                continue

            t_id = res_t['response'][0]['team']['id']
            t_nome = res_t['response'][0]['team']['name']

            # 2. Busca Ligas Ativas
            encontrou = False
            for ano in [2026, 2025]:
                res_l = requests.get(f"https://{HOST}/leagues", headers=headers, params={"team": t_id, "season": ano}, timeout=10).json()
                if not res_l.get('response'): continue

                for item in res_l['response']:
                    l_id = item['league']['id']
                    l_nome = item['league']['name']

                    # 3. Puxa Stats
                    res_s = requests.get(f"https://{HOST}/teams/statistics", headers=headers, 
                                         params={"league": l_id, "season": ano, "team": t_id}, timeout=10).json()
                    
                    if res_s.get('response'):
                        st = res_s['response']
                        
                        # PROTEÇÃO CONTRA CRASH: Verificação de existência de campos
                        try:
                            played = st.get('fixtures', {}).get('played', {}).get('total', 0)
                            g_for = st.get('goals', {}).get('for', {}).get('total', {}).get('total', 0)
                            g_against = st.get('goals', {}).get('against', {}).get('total', {}).get('total', 0)

                            # Só calcula se tiver jogado pelo menos 1 vez para evitar divisão por zero
                            if played and played > 0:
                                m_atk = round(float(g_for) / played, 2)
                                m_def = round(float(g_against) / played, 2)
                                
                                DB_STATS[nome.lower()] = {"nome": t_nome, "atk": m_atk, "def": m_def}
                                await update.message.reply_text(
                                    f"✅ **{t_nome}**\n🏆 {l_nome}\n🏟️ Jogos: {played}\n⚽ Atq: `{m_atk}` | Def: `{m_def}`"
                                )
                                encontrou = True
                                break
                        except Exception as e:
                            logger.error(f"Erro no cálculo interno: {e}")
                            continue
                if encontrou: break

            if not encontrou:
                await update.message.reply_text(f"⚠️ {t_nome} sem jogos registrados.")

        except Exception as e:
            logger.error(f"Erro na requisição para {nome}: {e}")
            await update.message.reply_text(f"💥 Erro ao buscar {nome}.")

async def match(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        args = " ".join(context.args).lower().split("vs")
        if len(args) < 2: return
        tA, tB = args[0].strip(), args[1].strip()
        
        if tA in DB_STATS and tB in DB_STATS:
            dA, dB = DB_STATS[tA], DB_STATS[tB]
            xgA = round((dA['atk'] + dB['def']) / 2, 2)
            xgB = round((dB['atk'] + dA['def']) / 2, 2)
            
            await update.message.reply_text(
                f"🔥 **{dA['nome']}** ({xgA}) vs **{dB['nome']}** ({xgB})\n\n"
                f"🎯 Resultado Sugerido: `{'Vitoria ' + dA['nome'] if xgA > xgB + 0.5 else 'Equilibrio / Empate'}`"
            )
    except Exception as e:
        await update.message.reply_text("❌ Erro no Match.")

if __name__ == "__main__":
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("games", games))
    app.add_handler(CommandHandler("match", match))
    app.run_polling(drop_pending_updates=True)
