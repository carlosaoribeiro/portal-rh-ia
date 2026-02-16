import streamlit as st
import json
import sqlite3
from google import genai
from duckduckgo_search import DDGS
from datetime import datetime

# =========================
# 1) SEGURANÇA E BANCO DE DADOS
# =========================
st.set_page_config(page_title="Agente de Carreira AI", layout="wide", page_icon="🚀")

if "GOOGLE_API_KEY" not in st.secrets:
    st.error("🚨 ERRO: Configure a GOOGLE_API_KEY nos Secrets do Streamlit!")
    st.stop()

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
# 2) MOTOR DE BUSCA (RESTAURADO DO ORIGINAL)
# =========================
def agente_explorer_vagas(cargo, local):
    # Voltando EXATAMENTE para a sua query original que funcionava
    query = (
        f'"{cargo}" {local} '
        f'(site:linkedin.com/jobs/view OR site:glassdoor.com/Job OR site:flexjobs.com OR site:remote.co) '
        f'-intitle:"help" -intitle:"ajuda" -intitle:"support" -intitle:"check"'
    )
    
    vagas_validas = []
    logs = [f"🔍 Buscando: {query}"]
    
    try:
        with DDGS() as ddgs:
            # Pegando os resultados brutos como no seu primeiro código
            results = ddgs.text(query, max_results=20)
            if results:
                for r in results:
                    link = r['href'].lower()
                    # RF-01: Sua validação original
                    if any(p in link for p in ['/jobs/', '/job/', '/viewjob', '/remote-jobs/']):
                        vagas_validas.append(r)
                    else:
                        logs.append(f"🚫 Ignorado: {link[:50]}...")
            else:
                logs.append("⚠️ O buscador não retornou dados brutos.")
    except Exception as e:
        logs.append(f"🚨 Erro técnico: {str(e)}")
    
    return vagas_validas, logs

# =========================
# 3) INTERFACE (UI/UX)
# =========================
st.sidebar.title("🤖 Agent Command Center")
app_mode = st.sidebar.radio("Módulo:", ["🔍 Motor de Busca", "📄 Gerador de Currículo"])

st.sidebar.divider()
st.sidebar.subheader("Sua Base de Dados")
matrix_input = st.sidebar.file_uploader("Sincronizar Matriz JSON", type=["json"])

if matrix_input:
    matrix_data = json.load(matrix_input)
    conn.execute("INSERT OR REPLACE INTO user_profile (id, matrix_json, last_updated) VALUES (1, ?, datetime('now'))", 
                 (json.dumps(matrix_data),))
    conn.commit()
    st.sidebar.success("✅ Perfil salvo no SQLite!")

# --- MÓDULO BUSCA ---
if app_mode == "🔍 Motor de Busca":
    st.header("🔍 Motor de Busca Ativa (7 dias)")
    st.caption(f"Data de referência: {datetime.now().strftime('%d/%m/%Y')}")

    col1, col2 = st.columns(2)
    with col1:
        cargo_q = st.text_input("Cargo:", value="Android Developer")
    with col2:
        local_q = st.text_input("Localidade:", value="Remote")

    if st.button("Agente, iniciar varredura", use_container_width=True):
        vagas, logs_debug = agente_explorer_vagas(cargo_q, local_q)
        
        with st.expander("📝 Logs de Diagnóstico", expanded=True):
            for l in logs_debug: st.text(l)

        if vagas:
            st.success(f"Encontramos {len(vagas)} vagas reais!")
            for i, v in enumerate(vagas):
                with st.container(border=True):
                    st.markdown(f"### {v['title']}")
                    st.caption(f"🌍 [Ver Vaga no Portal]({v['href']})")
                    st.write(v['body'])
                    # Botão para levar a vaga para o gerador
                    if st.button(f"Selecionar Vaga #{i+1}", key=f"btn_{i}"):
                        st.session_state['vaga_ativa'] = v['body']
                        st.success("Vaga carregada para o Gerador!")
        else:
            st.warning("Nenhuma vaga listada. Verifique os logs de diagnóstico.")

# --- MÓDULO GERADOR ---
elif app_mode == "📄 Gerador de Currículo":
    st.header("📄 Adaptador de Perfil Profissional")
    
    row = conn.execute("SELECT matrix_json FROM user_profile WHERE id = 1").fetchone()
    if not row:
        st.warning("⚠️ Carregue sua Matriz no menu lateral primeiro.")
        st.stop()
    
    vaga_selecionada = st.session_state.get('vaga_ativa', "")
    desc_vaga = st.text_area("Descrição enviada pelo Agente:", value=vaga_selecionada, height=200)
    
    if st.button("Gerar Currículo Otimizado"):
        with st.spinner("IA processando sua matriz..."):
            prompt = f"Adapte o perfil {row[0]} para esta vaga: {desc_vaga}. Retorne em Markdown bem formatado."
            try:
                resp = client.models.generate_content(model="gemini-2.0-flash", contents=prompt)
                st.success("Currículo Adaptado com Sucesso!")
                st.markdown(resp.text)
            except Exception as e:
                st.error(f"Erro na IA: {e}")

conn.close()
