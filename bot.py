import os
import math
import random
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

TOKEN = os.getenv("TOKEN")

JOGOS = {}

# ==========================
# BASE ESTATÍSTICA SIMULADA
# (depois ligaremos API real)
# ==========================

def stats_time(nome):

    # simulação estatística realista
    random.seed(nome.lower())

    gols_marcados = random.uniform(1.0, 2.4)
    gols_sofridos = random.uniform(0.8, 2.0)
    forma = random.uniform(0.8, 1.2)

    return gols_marcados, gols_sofridos, forma


# ==========================
# POISSON
# ==========================

def poisson(lmbda, k):
    return (lmbda**k * math.exp(-lmbda)) / math.factorial(k)


def prob_vitoria(xgA, xgB):

    max_gols = 6

    winA = 0
    winB = 0
    draw = 0

    for i in range(max_gols):
        for j in range(max_gols):

            p = poisson(xgA, i) * poisson(xgB, j)

            if i > j:
                winA += p
            elif j > i:
                winB += p
            else:
                draw += p

    return winA, draw, winB


# ==========================
# EXPECTED GOALS ENGINE
# ==========================

def calcular_xg(timeA, advA, timeB, advB):

    liga_media = 1.35

    atkA, defA, formaA = stats_time(timeA)
    atkAdvA, defAdvA, _ = stats_time(advA)

    atkB, defB, formaB = stats_time(timeB)
    atkAdvB, defAdvB, _ = stats_time(advB)

    xgA = liga_media * (atkA / defAdvA) * formaA
    xgB = liga_media * (atkB / defAdvB) * formaB

    return round(xgA,2), round(xgB,2)


# ==========================
# START
# ==========================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text(
"""🤖 IA MATCHUP ENGINE PRO

/games -> cadastrar jogos
/match Time A vs Time B
"""
)


# ==========================
# CADASTRAR JOGOS
# ==========================

async def games(update: Update, context: ContextTypes.DEFAULT_TYPE):

    texto = update.message.text.replace("/games","").strip()

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


# ==========================
# MATCH ENGINE
# ==========================

async def match(update: Update, context: ContextTypes.DEFAULT_TYPE):

    texto = " ".join(context.args)

    if "vs" not in texto.lower():
        await update.message.reply_text("Use /match Time A vs Time B")
        return

    timeA, timeB = texto.split("vs")

    timeA = timeA.strip()
    timeB = timeB.strip()

    if timeA.lower() not in JOGOS:
        await update.message.reply_text(f"{timeA} sem jogo cadastrado.")
        return

    if timeB.lower() not in JOGOS:
        await update.message.reply_text(f"{timeB} sem jogo cadastrado.")
        return

    advA = JOGOS[timeA.lower()]
    advB = JOGOS[timeB.lower()]

    # IA ENGINE
    xgA, xgB = calcular_xg(timeA, advA, timeB, advB)

    pA, pD, pB = prob_vitoria(xgA, xgB)

    # odds implícitas
    oddA = round(1/pA,2)
    oddD = round(1/pD,2)
    oddB = round(1/pB,2)

    # confiança
    confianca = round(abs(pA-pB)*100,1)

    if max(pA,pD,pB) == pA:
        pick = f"Vitória {timeA}"
    elif max(pA,pD,pB) == pB:
        pick = f"Vitória {timeB}"
    else:
        pick = "Empate"

    resposta = f"""
⚔️ MATCHUP IA — ACCURACY ENGINE

🅰 {timeA} vs {advA}
xG previsto: {xgA}

🅱 {timeB} vs {advB}
xG previsto: {xgB}

📊 Probabilidades IA
✅ {timeA}: {pA*100:.1f}%
🤝 Empate: {pD*100:.1f}%
✅ {timeB}: {pB*100:.1f}%

💰 Odds Implícitas
{timeA}: {oddA}
Empate: {oddD}
{timeB}: {oddB}

🔥 Confiança do Modelo: {confianca}%

🎯 MELHOR PICK:
👉 {pick}
"""

    await update.message.reply_text(resposta)


# ==========================
# MAIN
# ==========================

def main():

    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("games", games))
    app.add_handler(CommandHandler("match", match))

    print("✅ IA ONLINE")

    app.run_polling()


if __name__ == "__main__":
    main()
