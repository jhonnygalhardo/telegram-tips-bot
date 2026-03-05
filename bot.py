import os
import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# --- CONFIGURAÇÃO ---
TOKEN = os.getenv("TOKEN")
API_KEY = os.getenv("API_FOOTBALL_KEY") # Verifique se no Railway está IGUAL
HOST = "v3.football.api-sports.io"

DB_STATS = {}

async def games(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto = update.message.text.replace("/games", "").strip()
    if not texto or "vs" not in texto.lower():
        await update.message.reply_text("Use: /games TimeA vs TimeB")
        return

    await update.message.reply_text("📡 Tentando conexão direta com a API...")

    times_input = [t.strip() for t in texto.lower().split("vs")]
    headers = {"x-rapidapi-host": HOST, "x-rapidapi-key": API_KEY}

    for nome in times_input:
        # 1. Busca Simples
        url = f"https://{HOST}/teams"
        try:
            response = requests.get(url, headers=headers, params={"search": nome}, timeout=10)
            data = response.json()

            # DEBUG: O bot vai te dizer o que a API respondeu se não achar
            if not data.get('response'):
                await update.message.reply_text(f"❌ API não encontrou '{nome}'. Resposta: {data.get('errors')}")
                continue

            team = data['response'][0]['team']
            team_id = team['id']
            nome_oficial = team['name']

            # 2. Busca Stats (Tenta apenas 2025 que é garantido ter dados)
            stats_url = f"https://{HOST}/teams/statistics"
            # Vamos tentar a liga 128 (Argentina) se for Lanus/Boca ou 71 se for Brasil
            # Mas para testar, vamos varrer os IDs de ligas principais
            found = False
            for lid in [128, 71, 262, 39]: 
                s_res = requests.get(stats_url, headers=headers, params={"league": lid, "season": 2025, "team": team_id}).json()
                if s_res.get('response') and s_res['response']['goals']['for']['average']['total']:
                    atk = s_res['response']['goals']['for']['average']['total']
                    dfs = s_res['response']['goals']['against']['average']['total']
                    DB_STATS[nome] = {"nome": nome_oficial, "atk": float(atk), "def": float(dfs)}
                    await update.message.reply_text(f"✅ {nome_oficial} mapeado com sucesso!")
                    found = True
                    break
            
            if not found:
                await update.message.reply_text(f"⚠️ Achei o ID do {nome_oficial}, mas ele não tem gols registrados nas ligas principais.")

        except Exception as e:
            await update.message.reply_text(f"💥 Erro técnico: {e}")

async def match(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Lógica simples de cruzamento
    args = " ".join(context.args).lower().split("vs")
    tA, tB = args[0].strip(), args[1].strip()
    
    if tA in DB_STATS and tB in DB_STATS:
        resA, resB = DB_STATS[tA], DB_STATS[tB]
        xgA = (resA['atk'] + resB['def']) / 2
        xgB = (resB['atk'] + resA['def']) / 2
        await update.message.reply_text(f"🔥 Match: {resA['nome']} ({xgA}) vs {resB['nome']} ({xgB})")
    else:
        await update.message.reply_text("Times não carregados.")

if __name__ == "__main__":
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("games", games))
    app.add_handler(CommandHandler("match", match))
    app.run_polling()
