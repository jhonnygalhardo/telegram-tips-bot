import os
import logging
import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# Ativa logs para você ver o que acontece no painel do Railway
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Variáveis de Ambiente
TOKEN = os.getenv("TOKEN")
API_KEY = os.getenv("API_FOOTBALL_KEY")

# Cache Simples
DB_STATS = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🤖 **Accuracy Engine V5.1 Online**\nPronto para análise real.")

async def games(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Lógica de busca na API com tratamento de erro robusto
    await update.message.reply_text("⏳ Processando dados... verifique os logs se demorar.")
    # ... (Sua lógica de busca aqui)
    await update.message.reply_text("✅ Dados carregados.")

async def match(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Lógica de análise de Matchup
    # ... (Sua lógica de cálculo aqui)
    await update.message.reply_text("📊 Resultado da análise...")

def main():
    if not TOKEN:
        logger.error("Variável TOKEN não encontrada!")
        return

    # Construção do App
    application = ApplicationBuilder().token(TOKEN).build()

    # Handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("games", games))
    application.add_handler(CommandHandler("match", match))

    logger.info("Bot iniciando polling...")
    
    # drop_pending_updates limpa a fila de mensagens acumuladas
    application.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
