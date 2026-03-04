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

async def match(update: Update, context: ContextTypes.DEFAULT_TYPE):

    texto = " ".join(context.args)

    if "vs" not in texto.lower() and "x" not in texto.lower():
        await update.message.reply_text(
            "Use assim:\n/match Liverpool vs Chelsea"
        )
        return

    times = re.split(r"vs|x", texto, flags=re.IGNORECASE)

    time_a = times[0].strip()
    time_b = times[1].strip()

    prompt = f"""
Você é um analista profissional de MATCHUP VIRTUAL de futebol.

REGRA PRINCIPAL:
Cada time joga sua partida real separadamente.
O vencedor é quem tem MAIOR PROBABILIDADE DE MARCAR MAIS GOLS.

Analise:

Time A: {time_a}
Time B: {time_b}

Considere:
- poder ofensivo
- média recente de gols
- forma atual
- nível da liga
- qualidade ofensiva do elenco

Responda OBRIGATORIAMENTE:

⚔️ MATCHUP VIRTUAL
{time_a} 🆚 {time_b}

📊 Gols esperados:
{time_a}: X.X gols
{time_b}: X.X gols

🏆 Vencedor provável: TIME

📈 Confiança: XX%

💡 Justificativa curta profissional.
"""

    resposta = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}]
    )

    resultado = resposta.choices[0].message.content

    await update.message.reply_text(resultado)


