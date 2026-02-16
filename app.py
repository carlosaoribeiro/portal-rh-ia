import streamlit as st
import json
import sqlite3
import requests
from google import genai
from datetime import datetime

# =========================
# 1) SEGURANÇA E BANCO DE DADOS
# =========================
st.set_page_config(page_title="Agente de Carreira AI", layout="wide", page_icon="🚀")

# Verificação de chaves nos Secrets
if "SERPER_API_KEY" not in st.secrets or "GOOGLE_API_KEY" not in st.secrets:
    st.error("🚨 Configure SERPER_API_KEY e GOOGLE_API_KEY nos Secrets do Streamlit!")
    st.stop()

# Cliente Gemini 2.0 Flash
client = genai.Client(api_key=st.secrets["GOOGLE_API_KEY"])

def init_db():
    conn = sqlite3.connect('career_agent.db', check_same_thread=False)
    # Tabela para Perfil (Matriz)
    conn.execute('''CREATE TABLE IF NOT EXISTS user_profile 
                 (id INTEGER PRIMARY KEY, matrix_json TEXT, last_updated DATETIME)''')
    # Tabela para Histórico de Candidaturas
    conn.execute('''CREATE TABLE IF NOT EXISTS job_applications 
                 (id INTEGER PRIMARY KEY, title TEXT, link TEXT, date_applied DATETIME)''')
    conn.commit()
    return conn

conn = init_db()

# =========================
# 2) MOTOR DE BUSCA PROFISSIONAL (SERPER API)
# =========================
def motor_de_busca_profissional(cargo, local):
    """
    Executa busca via Serper API para evitar bloqueios de Scraping.
    Implementa filtros para remover resultados de 'Ajuda' e 'Suporte'.
    """
    url = "https://google.serper.dev/search"
    # Query otimizada para portais de vagas reais
    query = (
        f'"{cargo}" "{local}" '
        f'(site:linkedin.com/jobs/view OR site:glassdoor.com/Job OR site:flexjobs.com OR site:remote.co) '
        f'-intitle:"help" -intitle:"ajuda" -intitle:"support"'
    )
    
    payload = json.dumps({
        "q": query,
        "gl": "us",      # Foco nos EUA (Houston/Remote)
        "hl": "pt",      # Interface em Português
        "autocorrect": True
    })
    
    headers = {
        'X-API-KEY': st.secrets["SERPER_API_KEY"],
        'Content-Type': 'application/json'
    }
    
    try:
        response = requests.request("POST", url, headers=headers, data=payload)
        return response.json().get('organic', [])
    except Exception as e:
        st.error(f"Erro na conexão com o motor de busca: {e}")
        return []

# =========================
# 3) INTERFACE (UI/UX)
# =========================
st.sidebar.title("🤖 Agent Command Center")
app_mode = st.sidebar.radio("Selecione o Módulo:", ["🔍 Motor de Busca Ativa", "📄 Gerador de Currículo"])

st.sidebar.divider()
st.sidebar.subheader("⚙️ Configurações Base")
matrix_input = st.sidebar.file_uploader("Sincronizar Matriz JSON", type=["json"])

if matrix_input:
    matrix_data = json.load(matrix_input)
    conn.execute("INSERT OR REPLACE INTO user_profile (id, matrix_json, last_updated) VALUES (1, ?, datetime('now'))", 
                 (json.dumps(matrix_data),))
    conn.commit()
    st.sidebar.success("✅ Matriz salva com sucesso!")

# --- MÓDULO: BUSCA ---
if app_mode == "🔍 Motor de Busca Ativa":
    st.header("🔍 Agente Explorador Profissional")
    st.caption(f"Data de referência: {datetime.now().strftime('%d/%m/%Y')}")

    col1, col2 = st.columns(2)
    with col1:
        cargo_q = st.text_input("Cargo ou Tecnologia:", value="Android Developer")
    with col2:
        local_q = st.text_input("Localidade (Houston ou Remote):", value="Remote")

    if st.button("Agente, iniciar varredura profissional", use_container_width=True):
        with st.spinner("Acessando bases de dados premium via Serper..."):
            vagas = motor_de_busca_profissional(cargo_q, local_q)
            
            if vagas:
                st.success(f"Encontramos {len(vagas)} oportunidades reais!")
                for i, v in enumerate(vagas):
                    with st.container(border=True):
                        st.markdown(f"### {v.get('title')}")
                        st.caption(f"🔗 [Link da Vaga]({v.get('link')})")
                        st.write(v.get('snippet'))
                        
                        if st.button(f"Selecionar Vaga #{i+1}", key=f"sel_{i}"):
                            st.session_state['vaga_ativa'] = v.get('snippet')
                            st.session_state['url_vaga'] = v.get('link')
                            st.success("Vaga enviada para o módulo 'Gerador'!")
            else:
                st.warning("Nenhuma vaga listada. Tente simplificar os termos de busca.")

# --- MÓDULO: GERADOR ---
elif app_mode == "📄 Gerador de Currículo":
    st.header("📄 Adaptador de Currículo Inteligente")
    
    # Busca matriz no banco local
    row = conn.execute("SELECT matrix_json FROM user_profile WHERE id = 1").fetchone()
    if not row:
        st.warning("⚠️ Carregue sua Matriz JSON no menu lateral primeiro.")
        st.stop()
    
    vaga_selecionada = st.session_state.get('vaga_ativa', "")
    st.text_area("Descrição da vaga (enviada pelo Agente):", value=vaga_selecionada, height=200)
    
    if st.button("Gerar Currículo Otimizado", use_container_width=True):
        with st.spinner("IA processando sua matriz e a descrição da vaga..."):
            prompt = f"Como Tech Recruiter, adapte o currículo da matriz {row[0]} para a vaga: {vaga_selecionada}. Retorne apenas o JSON estruturado."
            resp = client.models.generate_content(model="gemini-2.0-flash", contents=prompt)
            st.success("Currículo Gerado!")
            st.markdown(resp.text)
