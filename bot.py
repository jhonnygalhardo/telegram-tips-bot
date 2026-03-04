import os
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

TOKEN = os.getenv("BOT_TOKEN")

# comando /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 Bot de Tips IA Online!\nUse /tip para receber análise."
    )

# comando /tip
async def tip(update: Update, context: ContextTypes.DEFAULT_TYPE):

    jogo = "Liverpool vs Chelsea"

    analise = f"""
⚽ TIP IA — Análise do Jogo

🏟 Jogo: {jogo}

📊 Forma recente:
Liverpool: ✅✅❌✅
Chelsea: ❌➖✅❌

🔥 Ataque mais eficiente: Liverpool
🛡 Defesa mais sólida: Liverpool

🎯 Probabilidade IA:
✅ Vitória Liverpool — 62%
🤝 Empate — 23%
✅ Vitória Chelsea — 15%

💡 Sugestão:
➡️ Liverpool ou Over 1.5 gols
"""

    await update.message.reply_text(analise)

# iniciar bot
app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("tip", tip))

print("Bot iniciado...")
app.run_polling()
