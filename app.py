import streamlit as st
import json
import sqlite3
import re
from google import genai
from duckduckgo_search import DDGS
from datetime import datetime, timedelta

# =========================
# 1) SEGURANÇA E BANCO DE DADOS
# =========================
st.set_page_config(page_title="Agente de Carreira AI", layout="wide", page_icon="🚀")

# A chave deve estar no painel do Streamlit Cloud (Settings > Secrets)
if "GOOGLE_API_KEY" not in st.secrets:
    st.error("🚨 ERRO: Configure a GOOGLE_API_KEY nos Secrets do Streamlit!")
    st.stop()

# Cliente Gemini 2.0 Flash
client = genai.Client(api_key=st.secrets["GOOGLE_API_KEY"])

def init_db():
    conn = sqlite3.connect('career_agent.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS user_profile 
                 (id INTEGER PRIMARY KEY, matrix_json TEXT, last_updated DATETIME)''')
    c.execute('''CREATE TABLE IF NOT EXISTS job_log 
                 (id INTEGER PRIMARY KEY, title TEXT, company TEXT, link TEXT, status TEXT)''')
    conn.commit()
    return conn

conn = init_db()

# =========================
# 2) MOTOR DE BUSCA COM REGRA DE NEGÓCIO (RN)
# =========================
def agente_explorer_vagas(cargo, local):
    """
    RN-01: O Agente ignora links de suporte/ajuda.
    RN-02: Foca em LinkedIn, Glassdoor, FlexJobs e Remote.co.
    """
    # Query otimizada para evitar páginas de suporte
    query = (
        f'"{cargo}" {local} '
        f'(site:linkedin.com/jobs/view OR site:glassdoor.com/Job OR site:flexjobs.com OR site:remote.co) '
        f'-intitle:"help" -intitle:"ajuda" -intitle:"support" -intitle:"check"'
    )
    
    vagas_validas = []
    logs = [f"🔍 Buscando: {query}"]
    
    try:
        with DDGS() as ddgs:
            # max_results=20 para ter margem de filtragem
            results = ddgs.text(query, max_results=20)
            if results:
                for r in results:
                    link = r['href'].lower()
                    # RF-01: Validação estrita de URL de vaga
                    if any(p in link for p in ['/jobs/', '/job/', '/viewjob', '/remote-jobs/']):
                        vagas_validas.append(r)
                    else:
                        logs.append(f"🚫 Ignorado (Não é vaga): {link[:50]}...")
            else:
                logs.append("⚠️ O buscador não retornou dados brutos.")
    except Exception as e:
        logs.append(f"🚨 Erro técnico: {str(e)}")
    
    return vagas_validas, logs

# =========================
#
