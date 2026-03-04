import os
import math
import random
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

TOKEN = os.getenv("TOKEN")

JOGOS = {}

# =============================
# ELO GLOBAL (base inicial)
# =============================

def elo_time(nome):
    random.seed(nome.lower())
    return random.randint(1500, 1950)


# =============================
# FORÇA DA LIGA
# =============================

def league_factor(nome):

    nome = nome.lower()

    elite = ["city","real madrid","barcelona","liverpool","arsenal","bayern"]
    forte = ["palmeiras","flamengo","chelsea","inter","milan"]

    if any(t in nome for t in elite):
        return 1.15
    if any(t in nome for t in forte):
        return 1.05

    return 1.0


# =============================
# ESTATÍSTICAS BASE
# =============================

def stats(nome):

    random.seed(nome.lower())

    ataque = random.uniform(1.1,2.5)
    defesa = random.uniform(0.9,2.0)
    forma = random.uniform(0.85,1.15)

    return ataque, defesa, forma


# =============================
# POISSON
# =============================

def poisson(lmbda, k):
    return (lmbda**k * math.exp(-lmbda)) / math.factorial(k)


def resultado_prob(xgA, xgB):

    winA = draw = winB = 0

    for i in range(6):
        for j in range(6):

            p = poisson(xgA,i)*poisson(xgB,j)

            if i>j:
                winA+=p
            elif j>i:
                winB+=p
            else:
                draw+=p

    return winA, draw, winB


# =============================
# EXPECTED GOALS V2
# =============================

def calcular_xg(time, adversario):

    atk, defe, forma = stats(time)
    atkO, defO, _ = stats(adversario)

    elo = elo_time(time)
    eloO = elo_time(adversario)

    elo_factor = 1 + ((elo-eloO)/4000)

    liga = league_factor(time)

    liga_media = 1.35

    xg = liga_media * (atk/defO) * forma * elo_factor * liga

    return max(0.2, round(xg,2))


# =============================
# CONFIDENCE ENGINE
# =============================

def confianca_modelo(pA,pD,pB,xgA,xgB):

    edge = abs(pA-pB)
    estabilidade = 1 - abs(xgA-xgB)/5

    conf = (edge*0.7 + estabilidade*0.3)*100

    return round(min(conf,95),1)


# =============================
# START
# =============================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text(
"""🤖 ACCURACY ENGINE V2 ONLINE

1️⃣ Cadastre jogos:
/games
Palmeiras vs Novorizontino
Arsenal vs Chelsea

2️⃣ Analise:
/match Palmeiras vs Chelsea
"""
)


# =============================
# CADASTRAR JOGOS
# =============================

async def games(update: Update, context: ContextTypes.DEFAULT_TYPE):

    texto = update.message.text.replace("/games","").strip()
    linhas = texto.split("\n")

    adicionados=[]

    for l in linhas:

        if "vs" not in l.lower():
            continue

        a,b=l.split("vs")

        a=a.strip()
        b=b.strip()

        JOGOS[a.lower()]=b
        JOGOS[b.lower()]=a

        adicionados.append(f"{a} vs {b}")

    await update.message.reply_text(
        "✅ Jogos registrados:\n\n"+"\n".join(adicionados)
    )


# =============================
# MATCH ENGINE V2
# =============================

async def match(update: Update, context: ContextTypes.DEFAULT_TYPE):

    texto=" ".join(context.args)

    if "vs" not in texto.lower():
        await update.message.reply_text("Use /match Time A vs Time B")
        return

    A,B=texto.split("vs")

    A=A.strip()
    B=B.strip()

    if A.lower() not in JOGOS:
        await update.message.reply_text(f"{A} sem jogo cadastrado.")
        return

    if B.lower() not in JOGOS:
        await update.message.reply_text(f"{B} sem jogo cadastrado.")
        return

    advA=JOGOS[A.lower()]
    advB=JOGOS[B.lower()]

    xgA=calcular_xg(A,advA)
    xgB=calcular_xg(B,advB)

    pA,pD,pB=resultado_prob(xgA,xgB)

    oddA=round(1/pA,2)
    oddD=round(1/pD,2)
    oddB=round(1/pB,2)

    conf=confianca_modelo(pA,pD,pB,xgA,xgB)

    pick=max([(pA,A),(pD,"Empate"),(pB,B)])[1]

    resposta=f"""
⚔️ MATCHUP IA — ACCURACY ENGINE V2

🅰 {A} vs {advA}
xG: {xgA}

🅱 {B} vs {advB}
xG: {xgB}

📊 Probabilidades
{A}: {pA*100:.1f}%
Empate: {pD*100:.1f}%
{B}: {pB*100:.1f}%

💰 Odds Implícitas
{A}: {oddA}
Empate: {oddD}
{B}: {oddB}

🧠 Confiança IA: {conf}%

🎯 PICK IA:
👉 {pick}
"""

    await update.message.reply_text(resposta)


# =============================
# MAIN
# =============================

def main():

    app=ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start",start))
    app.add_handler(CommandHandler("games",games))
    app.add_handler(CommandHandler("match",match))

    print("IA V2 ONLINE")

    app.run_polling()


if __name__=="__main__":
    main()
