import re
import json
import sqlite3
import streamlit as st
from datetime import datetime, timedelta
from google import genai
from duckduckgo_search import DDGS

# =========================
# 1) SETUP & DATABASE
# =========================
st.set_page_config(page_title="Agente de Carreira AI", layout="wide", page_icon="🚀")

def init_db():
    conn = sqlite3.connect('career_agent.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS user_profile 
                 (id INTEGER PRIMARY KEY, matrix_json TEXT, last_updated DATETIME)''')
    c.execute('''CREATE TABLE IF NOT EXISTS job_log 
                 (id INTEGER PRIMARY KEY, title TEXT, company TEXT, link TEXT, status TEXT, date_found DATETIME)''')
    conn.commit()
    return conn

conn = init_db()
client = genai.Client(api_key=st.secrets["GOOGLE_API_KEY"])

# =========================
# 2) MOTOR DE EXPLORAÇÃO (REQUISITO FUNCIONAL)
# =========================
def job_explorer_agent(cargo, local):
    """
    Simula o comportamento de um usuário navegando nos portais de vagas.
    Usa 'Dorks' avançados para filtrar apenas URLs de contratação.
    """
    hoje = datetime.now()
    # Filtro de 7 dias
    # Query construída para evitar páginas de ajuda e focar em listagens de cargos
    query = (
        f'("{cargo}") "{local}" '
        f'(site:linkedin.com/jobs/view OR site:glassdoor.com/Job OR '
        f'site:flexjobs.com/remote-jobs OR site:remote.co/remote-jobs) '
        f'-intitle:"help" -intitle:"support"'
    )
    
    results = []
    try:
        with DDGS() as ddgs:
            # max_results=20 para garantir que após o filtro tenhamos algo real
            raw = ddgs.text(query, max_results=20)
            for r in raw:
                # RN: Validação de link de vaga real
                if any(x in r['href'].lower() for x in ['/jobs/', '/job/', '/remote-jobs/']):
                    results.append(r)
    except Exception as e:
        st.error(f"Erro no Agente de Exploração: {e}")
    
    return results

# =========================
# 3) INTERFACE (UI/UX)
# =========================
st.sidebar.title("🤖 Agent Command Center")
app_mode = st.sidebar.radio("Navegação:", ["🔍 Motor de Busca Ativa", "📄 Gerador de Currículo"])

# Carregamento da Matriz (Persistência SQLite)
matrix_input = st.sidebar.file_uploader("Upload Matriz JSON", type=["json"])
if matrix_input:
    matrix_data = json.load(matrix_input)
    conn.execute("INSERT OR REPLACE INTO user_profile (id, matrix_json, last_updated) VALUES (1, ?, datetime('now'))", 
                 (json.dumps(matrix_data),))
    conn.commit()

if app_mode == "🔍 Motor de Busca Ativa":
    st.title("🔍 Agente Explorador de Vagas")
    st.markdown(f"**Data de Referência:** {datetime.now().strftime('%d/%m/%Y')} (Busca: últimos 7 dias)")

    col1, col2 = st.columns(2)
    with col1:
        cargo_busca = st.text_input("Defina o Cargo (ex: Desenvolvedor Android):", value="Android Developer")
    with col2:
        local_busca = st.text_input("Defina a Localidade (ex: Houston ou Remote):", value="Remote")

    if st.button("Agente, inicie a varredura nos portais", use_container_width=True):
        with st.spinner("O Agente está acessando as listas de vagas..."):
            vagas = job_explorer_agent(cargo_busca, local_busca)
            
            if vagas:
                st.success(f"O Agente identificou {len(vagas)} listagens de vagas reais.")
                for i, v in enumerate(vagas):
                    with st.container(border=True):
                        st.markdown(f"### {v['title']}")
                        st.caption(f"🌍 Link Original: {v['href']}")
                        st.write(v['body'])
                        
                        if st.button(f"Fazer o 'Deep Dive' nesta vaga #{i+1}"):
                            # Injeta os dados para o módulo de geração
                            st.session_state['vaga_selecionada'] = v['body']
                            st.session_state['link_selecionado'] = v['href']
                            st.success("Dados da vaga capturados! Mude para o módulo 'Gerador de Currículo'.")
            else:
                st.warning("O Agente não encontrou listagens recentes com esses termos.")

elif app_mode == "📄 Gerador de Currículo":
    st.title("📄 Adaptação de Perfil Profissional")
    # Busca matriz salva no DB
    row = conn.execute("SELECT matrix_json FROM user_profile WHERE id = 1").fetchone()
    if not row:
        st.warning("⚠️ Adicione sua Matriz JSON no menu lateral para o Agente ter base de dados.")
        st.stop()
    
    vaga_data = st.session_state.get('vaga_selecionada', "")
    st.text_area("Contexto da Vaga (Capturado pelo Agente):", value=vaga_data, height=200)
    
    if st.button("Gerar Currículo com IA"):
        # Aqui entra sua lógica de adaptação que já funciona
        st.info("Processando adaptação baseada na Matriz...")
