import os
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
)
from football_sim import simulate_match

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
if not TELEGRAM_TOKEN:
    raise ValueError("TELEGRAM_TOKEN não encontrado! Defina a variável de ambiente.")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Olá! Eu sou um bot de simulação de partidas de futebol.\n\n"
        "Use o comando:\n"
        "/simular NomeDoTimeCasa NomeDoTimeFora\n\n"
        "Exemplos:\n"
        "/simular Flamengo Palmeiras\n"
        "/simular Manchester City Liverpool"
    )

async def simular(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Uso: /simular TimeCasa TimeFora\nEx: /simular Tottenham Arsenal")
        return

    msg = await update.message.reply_text("🔍 Buscando times e estatísticas...")

    # Junta os argumentos considerando que o nome do time pode ter espaços
    full_text = " ".join(context.args)
    parts = full_text.split(" vs ", 1)  # permite "Time A vs Time B"
    if len(parts) == 2:
        home, away = parts
    else:
        # Tenta dividir no meio (heurística simples)
        words = full_text.split()
        split_idx = len(words) // 2
        home = " ".join(words[:split_idx])
        away = " ".join(words[split_idx:])

    try:
        result = simulate_match(home.strip(), away.strip())
        await msg.edit_text(result, parse_mode="Markdown")
    except Exception as e:
        await msg.edit_text(f"Erro durante a simulação: {str(e)}")

def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("simular", simular))

    print("Bot iniciado. Pressione Ctrl+C para parar.")
    app.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)

if __name__ == "__main__":
    main()
