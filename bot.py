import os
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

TOKEN = os.getenv("TOKEN")

# =====================
# BANCO EM MEMÓRIA
# =====================
JOGOS = {}

# =====================
# MODELO IA (simulação)
# =====================
def estimar_gols(time, adversario):

    import random

    base = random.uniform(0.8, 2.2)

    gigantes = [
        "palmeiras","flamengo","arsenal","city",
        "real","barcelona","bayern","liverpool"
    ]

    if any(g in time.lower() for g in gigantes):
        base += 0.4

    return round(base,2)


# =====================
# START
# =====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text(
"""🤖 BOT MATCHUP VIRTUAL

1️⃣ Cadastre jogos:

/games
Palmeiras vs Novorizontino
Arsenal vs Chelsea

2️⃣ Crie duelo virtual:

/match Palmeiras vs Chelsea
"""
)


# =====================
# CADASTRAR JOGOS
# =====================
async def games(update: Update, context: ContextTypes.DEFAULT_TYPE):

    texto = update.message.text.replace("/games","").strip()

    if not texto:
        await update.message.reply_text("Envie os jogos abaixo do comando.")
        return

    linhas = texto.split("\n")

    adicionados = []

    for linha in linhas:

        if "vs" not in linha.lower():
            continue

        casa, fora = linha.split("vs")

        casa = casa.strip()
        fora = fora.strip()

        JOGOS[casa.lower()] = fora
        JOGOS[fora.lower()] = casa

        adicionados.append(f"{casa} vs {fora}")

    await update.message.reply_text(
        "✅ Jogos cadastrados:\n\n" + "\n".join(adicionados)
    )


# =====================
# MATCHUP
# =====================
async def match(update: Update, context: ContextTypes.DEFAULT_TYPE):

    texto = " ".join(context.args)

    if "vs" not in texto.lower():
        await update.message.reply_text("Use:\n/match Time A vs Time B")
        return

    timeA_nome, timeB_nome = texto.split("vs")

    timeA_nome = timeA_nome.strip()
    timeB_nome = timeB_nome.strip()

    if timeA_nome.lower() not in JOGOS:
        await update.message.reply_text(f"❌ {timeA_nome} não possui jogo cadastrado.")
        return

    if timeB_nome.lower() not in JOGOS:
        await update.message.reply_text(f"❌ {timeB_nome} não possui jogo cadastrado.")
        return

    advA = JOGOS[timeA_nome.lower()]
    advB = JOGOS[timeB_nome.lower()]

    golsA = estimar_gols(timeA_nome, advA)
    golsB = estimar_gols(timeB_nome, advB)

    if golsA > golsB:
        vencedor = timeA_nome
    elif golsB > golsA:
        vencedor = timeB_nome
    else:
        vencedor = "EMPATE"

    resposta = f"""
⚔️ MATCHUP VIRTUAL

🅰 {timeA_nome}
vs {advA}
⚽ Gols previstos: {golsA}

🅱 {timeB_nome}
vs {advB}
⚽ Gols previstos: {golsB}

🏆 Vencedor Virtual:
👉 {vencedor}
"""

    await update.message.reply_text(resposta)


# =====================
# MAIN
# =====================
def main():

    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("games", games))
    app.add_handler(CommandHandler("match", match))

    print("✅ BOT ONLINE")

    app.run_polling()


if __name__ == "__main__":
    main()
