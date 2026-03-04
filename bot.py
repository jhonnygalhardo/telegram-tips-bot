import re
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from openai import OpenAI

TOKEN = os.getenv("BOT_TOKEN")
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 IA de Apostas Online!\nEnvie /tip para análise."
    )

async def tip(update: Update, context: ContextTypes.DEFAULT_TYPE):

    jogo = "Liverpool vs Chelsea"

    prompt = f"""
Você é um analista profissional de apostas esportivas.

Analise o jogo {jogo} considerando:

- forma recente
- força ofensiva e defensiva
- probabilidade de gols
- cenário provável
- sugestão de aposta segura

Responda como tipster profissional usando emojis.
"""

    resposta = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}]
    )

    analise = resposta.choices[0].message.content

    await update.message.reply_text(analise)

app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("tip", tip))

print("Bot IA iniciado...")
app.run_polling()

