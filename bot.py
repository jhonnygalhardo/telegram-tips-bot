import math
import itertools
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# --------- POISSON ---------

def poisson_prob(lam, k):
    return (math.exp(-lam) * lam**k) / math.factorial(k)

def goal_distribution(lam):
    probs = {}
    for i in range(5):
        probs[i] = poisson_prob(lam, i)
    probs["4+"] = 1 - sum(probs.values())
    return probs

# --------- EXPECTED GOALS ---------

def expected_goals(attack, opp_defense, odd):

    base = (attack + opp_defense) / 2

    if odd <= 1.70:
        base *= 1.07
    elif odd <= 2.10:
        base *= 1.03
    elif odd <= 2.80:
        base *= 0.95
    else:
        base *= 0.90

    return base

# --------- MATCHUP ---------

def matchup_prob(lamA, lamB):

    distA = [poisson_prob(lamA, i) for i in range(5)]
    distB = [poisson_prob(lamB, i) for i in range(5)]

    winA = 0
    draw = 0
    winB = 0

    for i in range(5):
        for j in range(5):

            p = distA[i] * distB[j]

            if i > j:
                winA += p
            elif i == j:
                draw += p
            else:
                winB += p

    return winA, draw, winB

# --------- DATA EXAMPLE ---------

teams = [
    {"name":"RB Leipzig","attack":2.2,"opp_def":1.6,"odd":1.36},
    {"name":"Atlético Madrid","attack":1.4,"opp_def":1.2,"odd":1.70},
    {"name":"Atalanta","attack":2.0,"opp_def":1.5,"odd":1.70},
    {"name":"Borussia Dortmund","attack":2.1,"opp_def":1.4,"odd":1.80},
]

# --------- FIND BEST MATCHUPS ---------

def best_matchups():

    results = []

    for a,b in itertools.combinations(teams,2):

        lamA = expected_goals(a["attack"],a["opp_def"],a["odd"])
        lamB = expected_goals(b["attack"],b["opp_def"],b["odd"])

        winA,draw,winB = matchup_prob(lamA,lamB)

        score = winA - winB

        results.append({
            "A":a["name"],
            "B":b["name"],
            "winA":winA,
            "draw":draw,
            "winB":winB,
            "score":score
        })

    results.sort(key=lambda x:x["score"],reverse=True)

    return results[:5]

# --------- TELEGRAM ---------

async def matchups(update: Update, context: ContextTypes.DEFAULT_TYPE):

    top = best_matchups()

    text = "TOP MATCHUPS DO DIA\n\n"

    for m in top:

        text += (
            f"{m['A']} vs {m['B']}\n"
            f"A vence: {m['winA']:.2%}\n"
            f"Empate: {m['draw']:.2%}\n"
            f"B vence: {m['winB']:.2%}\n\n"
        )

    await update.message.reply_text(text)

# --------- RUN BOT ---------

app = ApplicationBuilder().token("SEU_TOKEN_TELEGRAM").build()

app.add_handler(CommandHandler("matchups", matchups))

app.run_polling()
