import os
import requests
import math
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# Configurações do Railway
TOKEN = os.getenv("TOKEN")
API_KEY = os.getenv("API_FOOTBALL_KEY")
HOST = "v3.football.api-sports.io"

DB_STATS = {}

async def games(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto = update.message.text.replace("/games", "").strip()
    if "vs" not in texto.lower():
        await update.message.reply_text("❌ Formato inválido! Use: /games Time A vs Time B")
        return

    await update.message.reply_text("📡 Varrendo banco de dados da API (Temporada 2025/26)...")

    times_input = [t.strip() for t in texto.lower().split("vs")]
    headers = {"x-rapidapi-host": HOST, "x-rapidapi-key": API_KEY}

    for nome in times_input:
        try:
            # 1. Busca o ID do Time
            url_t = f"https://{HOST}/teams"
            res_t = requests.get(url_t, headers=headers, params={"search": nome}, timeout=10).json()

            if not res_t.get('response'):
                await update.message.reply_text(f"❌ Time '{nome}' não encontrado.")
                continue

            t_id = res_t['response'][0]['team']['id']
            t_nome = res_t['response'][0]['team']['name']

            # 2. Busca TODAS as estatísticas do time na temporada atual (2025) 
            # Nota: A API-Football usa o ano de início da temporada (2025 para 25/26)
            url_s = f"https://{HOST}/teams/statistics"
            
            # Buscamos primeiro as ligas que o time participa para não dar erro
            url_l = f"https://{HOST}/leagues"
            res_l = requests.get(url_l, headers=headers, params={"team": t_id, "current": "true"}, timeout=10).json()
            
            if not res_l.get('response'):
                await update.message.reply_text(f"⚠️ Não encontrei ligas ativas para {t_nome}.")
                continue

            # Tenta extrair dados da liga principal (onde ele tem mais jogos)
            found_data = False
            for league_info in res_l['response']:
                l_id = league_info['league']['id']
                # Tenta 2025 (início da temporada europeia) e 2026 (brasileira)
                for ano in [2025, 2026]:
                    res_s = requests.get(url_s, headers=headers, params={"league": l_id, "season": ano, "team": t_id}, timeout=10).json()
                    
                    if res_s.get('response') and res_s['response']['goals']['for']['average']['total']:
                        stats = res_s['response']['goals']
                        atk = stats['for']['average']['total']
                        dfs = stats['against']['average']['total']
                        
                        # Salva no banco de dados
                        DB_STATS[nome.lower()] = {"nome": t_nome, "atk": float(atk), "def": float(dfs)}
                        await update.message.reply_text(f"✅ {t_nome} OK!\n📊 Atq: {atk} | Def: {dfs} (Liga: {l_id})")
                        found_data = True
                        break
                if found_data: break

            if not found_data:
                await update.message.reply_text(f"⚠️ {t_nome} achado, mas sem médias de gols em 2025/26.")

        except Exception as e:
            await update.message.reply_text(f"💥 Erro em {nome}: {str(e)}")

async def match(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = " ".join(context.args).lower().split("vs")
    if len(args) < 2:
        await update.message.reply_text("❌ Use: /match TimeA vs TimeB")
        return

    tA_in, tB_in = args[0].strip(), args[1].strip()

    if tA_in in DB_STATS and tB_in in DB_STATS:
        dataA, dataB = DB_STATS[tA_in], DB_STATS[tB_in]
        
        # xG Cruzado
        xgA = (dataA['atk'] + dataB['def']) / 2
        xgB = (dataB['atk'] + dataA['def']) / 2
        
        # Probabilidades simples
        total = xgA + xgB
        pA = (xgA / total) * 0.82
        pB = (xgB / total) * 0.82
        pD = 1 - (pA + pB)

        res = (
            f"🔥 **ANÁLISE V11**\n"
            f"🏟️ {dataA['nome']} vs {dataB['nome']}\n\n"
            f"🏠 Vit. Casa: `{pA*100:.1f}%`\n"
            f"🤝 Empate: `{pD*100:.1f}%`\n"
            f"🚀 Vit. Fora: `{pB*100:.1f}%`\n\n"
            f"⚽ xG Esperado: `{xgA:.2f}` - `{xgB:.2f}`"
        )
        await update.message.reply_text(res, parse_mode="Markdown")
    else:
        await update.message.reply_text("❌ Times não carregados. Use /games primeiro.")

if __name__ == "__main__":
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("games", games))
    app.add_handler(CommandHandler("match", match))
    app.run_polling()
