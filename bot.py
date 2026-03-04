import os
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes
)

TOKEN = os.getenv("TOKEN")


# ===============================
# BANCO DE FORÇA DOS TIMES (BASE)
# depois vamos puxar API real
# ===============================

teams_stats = {
    "liverpool": {"ataque": 1.90, "defesa": 1.10},
    "chelsea": {"ataque": 1.35, "defesa": 1.45},
    "arsenal": {"ataque": 1.80, "defesa": 1.20},
    "manchester city": {"ataque": 2.20, "defesa": 0.95},
    "real madrid": {"ataque": 2.00, "defesa": 1.10},
    "barcelona": {"ataque": 1.85, "defesa": 1.25},
    "psg": {"ataque": 2.10, "defesa": 1.30},
    "bayern": {"ataque": 2.30, "defesa": 1.05},
}

MEDIA_LIGA = 1.35


# ===============================
# MODELO ESTATÍSTICO (PRO)
# ===============================

def gols_esperados(ataque, defesa_oponente):
    return round((ataque * defesa_oponente) / MEDIA_LIGA, 2)


def calcular_probabilidade(gols_a, gols_b):
    total = gols_a + gols_b

    prob_a = round((gols_a / total) * 100)
    prob_b = round((gols_b / total) * 100)
    empate = 100 - (prob_a + prob_b)

    return prob_a, empate, prob_b


# ===============================
# COMANDOS TELEGRAM
# ===============================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 TIPSTER IA ONLINE\n\n"
        "Use:\n"
        "/match TimeA x TimeB\n\n"
        "Exemplo:\n"
        "/match Liverpool x Chelsea"
    )


async def match(update: Update, context: ContextTypes.DEFAULT_TYPE):

    try:
        texto = " ".join(context.args).lower()

        if " x " not in texto:
            await update.message.reply_text(
                "Formato correto:\n/match Liverpool x Chelsea"
            )
            return

        time_a, time_b = texto.split(" x ")

        stats_a = teams_stats.get(time_a, {"ataque": 1.4, "defesa": 1.4})
        stats_b = teams_stats.get(time_b, {"ataque": 1.4, "defesa": 1.4})

        # cálculo estatístico real
        gols_a = gols_esperados(stats_a["ataque"], stats_b["defesa"])
        gols_b = gols_esperados(stats_b["ataque"], stats_a["defesa"])

        prob_a, empate, prob_b = calcular_probabilidade(gols_a, gols_b)

        # decisão
        if gols_a > gols_b:
            vencedor = time_a.title()
        elif gols_b > gols_a:
            vencedor = time_b.title()
        else:
            vencedor = "Empate técnico"

        resposta = f"""
⚽ ANÁLISE ESTATÍSTICA IA

🏟 Confronto Virtual:
{time_a.title()} 🆚 {time_b.title()}

📊 Gols Esperados (xG):
{time_a.title()}: {gols_a}
{time_b.title()}: {gols_b}

📈 Probabilidades:
✅ {time_a.title()} — {prob_a}%
🤝 Empate — {empate}%
✅ {time_b.title()} — {prob_b}%

🎯 Time com maior chance de fazer MAIS gols:
🔥 {vencedor}
"""

        await update.message.reply_text(resposta)

    except Exception as e:
        await update.message.reply_text(f"Erro: {e}")


# ===============================
# INICIAR BOT
# ===============================

app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("match", match))

print("BOT ONLINE...")
app.run_polling()
