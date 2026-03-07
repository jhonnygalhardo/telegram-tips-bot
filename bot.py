import os
import math
import requests
import itertools
from datetime import date

from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

BOT_TOKEN = os.getenv("BOT_TOKEN")
API_KEY = os.getenv("FOOTBALL_API")

headers = {
    "x-apisports-key": API_KEY
}

# -----------------------------
# POISSON
# -----------------------------

def poisson(lam, k):
    return (math.exp(-lam) * lam**k) / math.factorial(k)

def distribution(lam):

    probs = []

    for i in range(5):
        probs.append(poisson(lam,i))

    probs.append(1 - sum(probs))

    return probs

# -----------------------------
# EXPECTED GOALS
# -----------------------------

def expected_goals(scored, conceded):

    attack = scored / 10
    defense = conceded / 10

    return (attack + defense) / 2

# -----------------------------
# GET GAMES TODAY
# -----------------------------

def get_games():

    today = date.today()

    url = f"https://v3.football.api-sports.io/fixtures?date={today}"

    r = requests.get(url, headers=headers)

    data = r.json()

    games = []

    for g in data["response"]:

        home = g["teams"]["home"]["name"]
        away = g["teams"]["away"]["name"]

        games.append(home)
        games.append(away)

    return games

# -----------------------------
# SIMULATE MATCHUP
# -----------------------------

def matchup(lamA, lamB):

    distA = distribution(lamA)
    distB = distribution(lamB)

    winA = 0
    winB = 0
    draw = 0

    for i in range(6):
        for j in range(6):

            p = distA[i] * distB[j]

            if i > j:
                winA += p
            elif j > i:
                winB += p
            else:
                draw += p

    return winA, draw, winB

# -----------------------------
# FIND BEST MATCHUPS
# -----------------------------

def best_matchups():

    teams = get_games()

    results = []

    for a,b in itertools.combinations(teams,2):

        lamA = 1.5
        lamB = 1.2

        winA,draw,winB = matchup(lamA,lamB)

        edge = winA - winB

        results.append((a,b,winA,draw,winB,edge))

    results.sort(key=lambda x:x[5],reverse=True)

    return results[:10]

# -----------------------------
# TELEGRAM COMMAND
# -----------------------------

async def today(update: Update, context: ContextTypes.DEFAULT_TYPE):

    matches = best_matchups()

    text = "🔥 TOP MATCHUPS DO DIA\n\n"

    for m in matches:

        text += (
            f"{m[0]} vs {m[1]}\n"
            f"A vence: {m[2]:.2%}\n"
            f"Empate: {m[3]:.2%}\n"
            f"B vence: {m[4]:.2%}\n\n"
        )

    await update.message.reply_text(text)

# -----------------------------
# RUN BOT
# -----------------------------

app = ApplicationBuilder().token(BOT_TOKEN).build()

app.add_handler(CommandHandler("today", today))

print("Bot rodando...")

app.run_polling()
