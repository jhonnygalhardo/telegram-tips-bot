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