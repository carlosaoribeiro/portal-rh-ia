import re
import json
import sqlite3
import streamlit as st
from google import genai
from pypdf import PdfReader
import streamlit.components.v1 as components
from html import escape
from duckduckgo_search import DDGS

# =========================
# 1) CONFIGURAÇÃO E BANCO DE DADOS (SQLite)
# =========================
st.set_page_config(page_title="Agente de Carreira AI", layout="wide", page_icon="🚀")

def init_db():
    # check_same_thread=False é necessário para o Streamlit
    conn = sqlite3.connect('career_agent.db', check_same_thread=False)
    c = conn.cursor()
    # Armazena sua Matriz JSON (Fonte de Verdade) 
    c.execute('''CREATE TABLE IF NOT EXISTS user_profile 
                 (id INTEGER PRIMARY KEY, matrix_json TEXT, last_updated DATETIME)''')
    # Histórico de vagas encontradas e status 
    c.execute('''CREATE TABLE IF NOT EXISTS job_log 
                 (id INTEGER PRIMARY KEY, title TEXT, company TEXT, link TEXT, status TEXT, date_found DATETIME)''')
    conn.commit()
    return conn

conn = init_db()

# Configuração da API Gemini
if "GOOGLE_API_KEY" not in st.secrets:
    st.error("Configure a chave 'GOOGLE_API_KEY' em .streamlit/secrets.toml")
    st.stop()

client = genai.Client(api_key=st.secrets["GOOGLE_API_KEY"])

# =========================
# 2) HELPERS
# =========================
def get_response_text(response) -> str:
    try:
        return response.text if hasattr(response, "text") else response.candidates[0].content.parts[0].text
    except: return ""

def extract_json_loose(text: str) -> dict:
    text = (text or "").strip()
    text = re.sub(r"```(?:json)?", "", text, flags=re.IGNORECASE).strip("` \n\r\t")
    i = text.find("{")
    if i == -1: raise ValueError("Resposta sem JSON")
    return json.JSONDecoder().raw_decode(text[i:])[0]

# =========================
# 3) INTERFACE LATERAL (MENU)
# =========================
st.sidebar.title("🤖 Agent Command Center")
app_mode = st.sidebar.radio("Selecione o Módulo:", ["🔍 Motor de Busca", "📄 Gerador de Currículo"])

st.sidebar.divider()
st.sidebar.subheader("⚙️ Configurações Base")
matrix_input = st.sidebar.file_uploader("Atualizar Matriz JSON", type=["json"])

if matrix_input:
    matrix_data = json.load(matrix_input)
    conn.execute("INSERT OR REPLACE INTO user_profile (id, matrix_json, last_updated) VALUES (1, ?, datetime('now'))", 
                 (json.dumps(matrix_data),))
    conn.commit()
    st.sidebar.success("✅ Matriz salva no SQLite!")

# =========================
# 4) MÓDULO: MOTOR DE BUSCA (POWER SEARCH)
# =========================
if app_mode == "🔍 Motor de Busca":
    st.title("🔍 Motor de Busca de Vagas Remotas")
    st.info("O agente busca em portais especializados (WeWorkRemotely, Wellfound, RemoteOK, etc.)")
    
    col1, col2 = st.columns(2)
    with col1:
        cargo = st.text_input("Cargo (ex: Product Manager):", value="Product Manager")
    with col2:
        # Foco em Houston ou Worldwide para PMs [cite: 1]
        local = st.text_input("Localização/Filtro:", value="Remote")
    
    if st.button("Agente, iniciar varredura profunda", use_container_width=True):
        with st.spinner("Varrendo portais de tecnologia e startups..."):
            # Lista baseada na sua tabela de sites 
            sites_remotos = [
                "weworkremotely.com", "wellfound.com", "remotive.io", 
                "remoteok.com", "workingnomads.com", "justremote.co",
                "flexjobs.com", "remote.co", "remotecircle.com", "jsremotely.com"
            ]
            
            site_query = " OR ".join([f"site:{s}" for s in sites_remotos])
            full_query = f'"{cargo}" {local} ({site_query}) after:2026-01-01'
            
            try:
                with DDGS() as ddgs:
                    results = [r for r in ddgs.text(full_query, max_results=12)]
                
                if results:
                    for i, res in enumerate(results):
                        with st.container(border=True):
                            # Identifica a fonte
                            origem = next((s for s in sites_remotos if s in res['href']), "Outro")
                            st.markdown(f"### {res['title']}")
                            st.caption(f"📍 Fonte: {origem} | [Ver Vaga Original]({res['href']})")
                            st.write(res['body'])
                            
                            if st.button(f"Selecionar Vaga #{i+1}", key=f"sel_{i}"):
                                st.session_state['vaga_ativa'] = res['body']
                                # Salva log no DB 
                                conn.execute("INSERT INTO job_log (title, company, link, status, date_found) VALUES (?, ?, ?, ?, datetime('now'))", 
                                             (res['title'], origem, res['href'], 'Selecionada'))
                                conn.commit()
                                st.success("✅ Vaga carregada! Vá para 'Gerador de Currículo'.")
                else:
                    st.warning("Nenhuma vaga recente encontrada. Tente simplificar o cargo.")
            except Exception as e:
                st.error(f"Erro na busca: {e}")

# =========================
# 5) MÓDULO: GERADOR DE CURRÍCULO
# =========================
elif app_mode == "📄 Gerador de Currículo":
    st.title("📄 Adaptador de Perfil para ATS")
    
    # Busca matriz salva 
    row = conn.execute("SELECT matrix_json FROM user_profile WHERE id = 1").fetchone()
    if not row:
        st.warning("⚠️ Faça o upload da sua Matriz no menu lateral primeiro.")
        st.stop()
    
    saved_matrix = json.loads(row[0])
    vaga_auto = st.session_state.get('vaga_ativa', "")

    st.subheader("Vaga Alvo")
    job_desc = st.text_area("Descrição (Preenchida via Motor de Busca):", value=vaga_auto, height=250)
    
    if st.button("Gerar Currículo Otimizado", use_container_width=True):
        with st.spinner("IA processando sua matriz e adaptando keywords..."):
            # Prompt de PM focado em resultados [cite: 1]
            prompt = f"""
            Como um Tech Recruiter, adapte o currículo da matriz abaixo para a vaga fornecida.
            Foque em métricas de produto e keywords de ATS.
            MATRIZ: {json.dumps(saved_matrix)}
            VAGA: {job_desc}
            Retorne JSON seguindo o esquema padrão do sistema.
            """
            resp = client.models.generate_content(model="gemini-2.0-flash", contents=prompt)
            raw_text = get_response_text(resp)
            
            try:
                data = extract_json_loose(raw_text)
                st.session_state['curriculo_final'] = data
                st.success("Currículo Gerado!")
            except:
                st.error("Erro ao processar JSON da IA.")

    # Exibição do PDF/HTML se houver dados
    if 'curriculo_final' in st.session_state:
        # (Aqui você mantém suas funções de renderização HTML/ATS originais)
        st.json(st.session_state['curriculo_final']) # Placeholder da exibição
