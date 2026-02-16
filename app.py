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
    conn.commit()
    return conn

conn = init_db()

# =========================
# 2) MOTOR DE BUSCA (REVISADO)
# =========================
def agente_explorer_vagas(cargo, local):
    # Simplificação da query para evitar bloqueio e aumentar resultados
    query = f'"{cargo}" {local} (site:linkedin.com OR site:glassdoor.com OR site:remote.co) jobs'
    
    vagas_validas = []
    logs = [f"🔍 Buscando por: {query}"]
    
    try:
        with DDGS() as ddgs:
            # Reduzi para 10 para ser mais rápido e evitar timeout
            results = list(ddgs.text(query, max_results=10))
            
            if results:
                for r in results:
                    # Filtro básico de link
                    link = r.get('href', '').lower()
                    if any(x in link for x in ['job', 'view', 'vacancy', 'career']):
                        vagas_validas.append(r)
                    else:
                        logs.append(f"🚫 Link descartado: {link[:40]}...")
            else:
                logs.append("⚠️ DuckDuckGo não retornou resultados. Tente termos mais genéricos.")
    except Exception as e:
        logs.append(f"🚨 Erro na busca: {str(e)}")
    
    return vagas_validas, logs

# =========================
# 3) INTERFACE
# =========================
st.sidebar.title("🤖 Agent Command Center")
app_mode = st.sidebar.radio("Módulo:", ["🔍 Motor de Busca", "📄 Gerador de Currículo"])

# Persistência da Matriz
matrix_input = st.sidebar.file_uploader("Sincronizar Matriz JSON", type=["json"])
if matrix_input:
    matrix_data = json.load(matrix_input)
    conn.execute("INSERT OR REPLACE INTO user_profile (id, matrix_json, last_updated) VALUES (1, ?, datetime('now'))", 
                 (json.dumps(matrix_data),))
    conn.commit()
    st.sidebar.success("✅ Perfil sincronizado!")

# --- MÓDULO BUSCA ---
if app_mode == "🔍 Motor de Busca":
    st.header("🔍 Motor de Busca Ativa")
    
    col1, col2 = st.columns(2)
    with col1:
        cargo_q = st.text_input("Cargo:", value="Android Developer")
    with col2:
        local_q = st.text_input("Localidade:", value="Remote")

    if st.button("Agente, iniciar varredura", use_container_width=True):
        vagas, logs_debug = agente_explorer_vagas(cargo_q, local_q)
        
        with st.expander("📝 Logs de Diagnóstico"):
            for l in logs_debug: st.text(l)

        if vagas:
            st.success(f"Sucesso! {len(vagas)} vagas encontradas.")
            for i, v in enumerate(vagas):
                with st.container(border=True):
                    st.subheader(v.get('title', 'Vaga sem título'))
                    st.write(v.get('body', 'Sem descrição disponível.'))
                    st.caption(f"🔗 [Link da Vaga]({v.get('href')})")
                    
                    if st.button(f"Selecionar Vaga #{i+1}", key=f"sel_{i}"):
                        st.session_state['vaga_ativa'] = v.get('body')
                        st.success("Vaga enviada para o Gerador!")
        else:
            st.error("Nenhuma vaga encontrada. O buscador retornou vazio.")

# --- MÓDULO GERADOR ---
elif app_mode == "📄 Gerador de Currículo":
    st.header("📄 Adaptador Profissional")
    
    row = conn.execute("SELECT matrix_json FROM user_profile WHERE id = 1").fetchone()
    if not row:
        st.warning("⚠️ Carregue sua Matriz JSON lateralmente.")
        st.stop()
    
    vaga_txt = st.session_state.get('vaga_ativa', "")
    desc_vaga = st.text_area("Descrição da Vaga selecionada:", value=vaga_txt, height=200)
    
    if st.button("Gerar Currículo Otimizado"):
        with st.spinner("Gemini trabalhando..."):
            prompt = f"Com base neste perfil: {row[0]}, adapte um currículo para esta vaga: {desc_vaga}. Retorne em Markdown."
            try:
                resp = client.models.generate_content(model="gemini-2.0-flash", contents=prompt)
                st.markdown(resp.text)
            except Exception as e:
                st.error(f"Erro IA: {e}")

conn.close()
