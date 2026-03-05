async def games(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto = update.message.text.replace("/games", "").strip()
    if "vs" not in texto.lower():
        await update.message.reply_text("❌ Formato: /games Time A vs Time B")
        return

    await update.message.reply_text("📡 Calculando médias reais (Total Gols / Total Jogos)...")

    times_input = [t.strip() for t in texto.lower().split("vs")]
    headers = {"x-rapidapi-host": HOST, "x-rapidapi-key": API_KEY}

    for nome in times_input:
        try:
            # 1. Busca ID do Time
            res_t = requests.get(f"https://{HOST}/teams", headers=headers, params={"search": nome}, timeout=10).json()
            if not res_t.get('response'):
                await update.message.reply_text(f"❌ Time '{nome}' não encontrado.")
                continue

            t_id = res_t['response'][0]['team']['id']
            t_nome = res_t['response'][0]['team']['name']

            # 2. Busca Ligas e Stats (Temporada 2025/26)
            encontrou_dados = False
            # Tentamos 2025 (Europa) e 2026 (Brasil/Américas)
            for ano in [2026, 2025]:
                # Buscamos as ligas para ter o ID correto
                res_l = requests.get(f"https://{HOST}/leagues", headers=headers, params={"team": t_id, "season": ano}, timeout=10).json()
                if not res_l.get('response'): continue

                for item in res_l['response']:
                    l_id = item['league']['id']
                    l_nome = item['league']['name']

                    # 3. Puxa Stats Brutas
                    res_s = requests.get(f"https://{HOST}/teams/statistics", headers=headers, 
                                         params={"league": l_id, "season": ano, "team": t_id}, timeout=10).json()
                    
                    if res_s.get('response'):
                        st = res_s['response']
                        
                        # PEGANDO TOTAIS EM VEZ DE MÉDIAS
                        jogos = st['fixtures']['played']['total']
                        gols_feitos = st['goals']['for']['total']['total']
                        gols_sofridos = st['goals']['against']['total']['total']

                        # Se o time jogou pelo menos 3 partidas na liga
                        if jogos and jogos >= 3:
                            m_atk = round(gols_feitos / jogos, 2)
                            m_def = round(gols_sofridos / jogos, 2)
                            
                            DB_STATS[nome.lower()] = {"nome": t_nome, "atk": m_atk, "def": m_def}
                            await update.message.reply_text(
                                f"✅ **{t_nome} MAPEADO!**\n"
                                f"🏆 Liga: {l_nome} ({ano})\n"
                                f"🏟️ Jogos: {jogos}\n"
                                f"⚽ Média Atq: `{m_atk}`\n"
                                f"🛡️ Média Def: `{m_def}`"
                            )
                            encontrou_dados = True
                            break
                if encontrou_dados: break

            if not encontrou_dados:
                await update.message.reply_text(f"⚠️ {t_nome} encontrado, mas sem jogos suficientes registrados em 2025/26.")

        except Exception as e:
            await update.message.reply_text(f"💥 Erro em {nome}: {str(e)}")
