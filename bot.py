import requests
import pandas as pd
import numpy as np
from scipy.stats import poisson
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# ===== CONFIGURAÇÕES =====
TELEGRAM_TOKEN = "SEU_TELEGRAM_BOT_TOKEN"
FOOTBALL_API_KEY = "SUA_FOOTBALL_API_KEY"
API_URL = "https://api.football-data.org/v4/matches"
HEADERS = {"X-Auth-Token": FOOTBALL_API_KEY}
NUM_JOGOS = 5  # últimos jogos para análise
MAX_GOALS = 10  # limite para Poisson

# ===== FUNÇÃO PARA PEGAR PARTIDAS E ODDS =====
def get_recent_matches(team_name):
    response = requests.get(API_URL, headers=HEADERS)
    data = response.json()
    matches = []
    for match in data.get("matches", []):
        if team_name in [match["homeTeam"]["name"], match["awayTeam"]["name"]]:
            matches.append({
                "home": match["homeTeam"]["name"],
                "away": match["awayTeam"]["name"],
                "home_score": match["score"]["fullTime"]["home"],
                "away_score": match["score"]["fullTime"]["away"],
                "home_odds": match.get("odds", {}).get("homeWin", 2.0),
                "draw_odds": match.get("odds", {}).get("draw", 3.0),
                "away_odds": match.get("odds", {}).get("awayWin", 2.5)
            })
    return pd.DataFrame(matches).tail(NUM_JOGOS)

# ===== FUNÇÃO POISSON PARA MÉDIA DE GOLS =====
def poisson_expected_goals(team, opponent, team_matches, is_home=True):
    if team_matches.empty:
        return 1
    goals_for = []
    goals_against = []
    for _, row in team_matches.iterrows():
        if row["home"] == team:
            goals_for.append(row["home_score"])
            goals_against.append(row["away_score"])
        else:
            goals_for.append(row["away_score"])
            goals_against.append(row["home_score"])
    
    avg_for = np.mean(goals_for)
    avg_against = np.mean(goals_against)
    
    # Vantagem casa/fora
    if is_home:
        avg_for *= 1.1
        avg_against *= 0.9
    else:
        avg_for *= 0.9
        avg_against *= 1.1
    
    expected_goals = (avg_for + avg_against) / 2
    return expected_goals

# ===== FUNÇÃO PARA CALCULAR PROBABILIDADES E EV =====
def analyze_matchup(team1, team2):
    df1 = get_recent_matches(team1)
    df2 = get_recent_matches(team2)
    
    if df1.empty or df2.empty:
        return "Não há dados suficientes para os times selecionados."
    
    team1_goals = poisson_expected_goals(team1, team2, df1, is_home=True)
    team2_goals = poisson_expected_goals(team2, team1, df2, is_home=False)
    
    # Matriz Poisson
    prob_matrix = np.zeros((MAX_GOALS+1, MAX_GOALS+1))
    for i in range(MAX_GOALS+1):
        for j in range(MAX_GOALS+1):
            prob_matrix[i,j] = poisson.pmf(i, team1_goals) * poisson.pmf(j, team2_goals)
    
    # Probabilidades de cada resultado
    win_team1 = np.sum(np.tril(prob_matrix, -1))
    win_team2 = np.sum(np.triu(prob_matrix, 1))
    draw = np.sum(np.diag(prob_matrix))
    
    # Odds médias
    home_odds = np.mean(df1["home_odds"].dropna()) if not df1.empty else 2.0
    draw_odds = np.mean(df1["draw_odds"].dropna()) if not df1.empty else 3.0
    away_odds = np.mean(df2["away_odds"].dropna()) if not df2.empty else 2.5
    
    # EV (Expected Value) = Probabilidade * Odds - 1
    ev_team1 = win_team1 * home_odds - 1
    ev_team2 = win_team2 * away_odds - 1
    ev_draw = draw * draw_odds - 1
    
    # Resultado esperado
    expected_score1 = round(team1_goals)
    expected_score2 = round(team2_goals)
    
    # Índice de confiança
    confidence = max(win_team1, win_team2, draw)
    
    result_text = f"{team1} {expected_score1} x {expected_score2} {team2}\nConfiança: {confidence:.2%}\n\n"
    result_text += f"Probabilidades:\n{team1} vitória: {win_team1:.2%} | EV: {ev_team1:.2f}\n"
    result_text += f"{team2} vitória: {win_team2:.2%} | EV: {ev_team2:.2f}\n"
    result_text += f"Empate: {draw:.2%} | EV: {ev_draw:.2f}\n\n"
    
    # Sugestão de aposta
    best_ev = max(ev_team1, ev_team2, ev_draw)
    if best_ev == ev_team1:
        result_text += f"💡 Sugestão: Apostar em {team1} (maior EV)"
    elif best_ev == ev_team2:
        result_text += f"💡 Sugestão: Apostar em {team2} (maior EV)"
    else:
        result_text += f"💡 Sugestão: Apostar no Empate (maior EV)"
    
    return result_text

# ===== COMANDOS TELEGRAM =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Olá! Envie /matchup time1 time2 para análise profissional com Poisson + Odds + EV + Confiança.")

async def matchup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) != 2:
        await update.message.reply_text("Uso correto: /matchup Brasil França")
        return
    team1, team2 = context.args
    result = analyze_matchup(team1, team2)
    await update.message.reply_text(result)

# ===== EXECUÇÃO DO BOT =====
app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("matchup", matchup))

print("Bot de análise esportiva avançado iniciado...")
app.run_polling()
