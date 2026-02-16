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
# 2) MOTOR DE BUSCA (ESTRATÉGIA RESILIENTE)
# =========================
def agente_explorer_vagas(cargo, local):
    # Tentativa 1: Query estruturada (Sua regra original)
    query_bruta = f'"{cargo}" {local} jobs (linkedin OR glassdoor OR remote.co)'
    
    vagas_validas = []
    logs = [f"🔍 Iniciando varredura para: {cargo} em {local}"]
    
    try:
        with DDGS() as ddgs:
            # Busca simplificada para evitar bloqueio de bot
            results = list(ddgs.text(query_bruta, max_results=15))
            
            if not results:
                logs.append("⚠️ Tentando busca secundária sem filtros de site...")
                results = list(ddgs.text(f"vagas de {cargo} {local}", max_results=10))

            if results:
                for r in results:
                    link = r.get('href', '').lower()
                    # Filtro de relevância mínimo
                    if any(p in link for p in ['job', 'vaga', 'career', 'view', 'apply']):
                        vagas_validas.append(r)
                logs.append(f"✅ Sucesso: {len(vagas_validas)} resultados processados.")
            else:
                logs.append("❌ Erro: O provedor de busca não retornou nenhum dado.")
                
    except Exception as e:
        logs.append(f"🚨 Erro técnico na busca: {str(e)}")
    
    return vagas_validas, logs

# =========================
# 3) INTERFACE PRINCIPAL
# =========================
st.sidebar.title("🤖 Agent Command Center")
app_mode = st.sidebar.radio("Módulo:", ["🔍 Motor de Busca", "📄 Gerador de Currículo"])

# Upload da Matriz
matrix_input = st.sidebar.file_uploader("Sincronizar Matriz JSON", type=["json"])
if matrix_input:
    matrix_data = json.load(matrix_input)
    conn.execute("INSERT OR REPLACE INTO user_profile (id, matrix_json, last_updated) VALUES (1, ?, datetime('now'))", 
                 (json.dumps(matrix_data),))
    conn.commit()
    st.sidebar.success("✅ Matriz Sincronizada!")

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
            st.success(f"Encontramos {len(vagas)} oportunidades!")
            for i, v in enumerate(vagas):
                with st.container(border=True):
                    st.subheader(v.get('title', 'Título não disponível'))
                    st.write(v.get('body', 'Descrição indisponível.'))
                    st.caption(f"🔗 [Link Direto]({v.get('href')})")
                    
                    if st.button(f"Selecionar Vaga #{i+1}", key=f"v_{i}"):
                        st.session_state['vaga_ativa'] = v.get('body')
                        st.session_state['vaga_nome'] = v.get('title')
                        st.toast("Vaga selecionada!")
        else:
            st.warning("Nenhum resultado. Tente mudar o termo de busca (ex: tire as aspas).")

# --- MÓDULO GERADOR ---
elif app_mode == "📄 Gerador de Currículo":
    st.header("📄 Adaptador de Perfil")
    
    row = conn.execute("SELECT matrix_json FROM user_profile WHERE id = 1").fetchone()
    if not row:
        st.warning("⚠️ Carregue sua Matriz no menu lateral primeiro.")
        st.stop()
    
    vaga_data = st.session_state.get('vaga_ativa', "")
    vaga_titulo = st.session_state.get('vaga_nome', "Nenhuma vaga selecionada")
    
    st.info(f"Vaga atual: **{vaga_titulo}**")
    area_texto = st.text_area("Conteúdo da Vaga:", value=vaga_data, height=200)
    
    if st.button("Gerar Currículo Otimizado"):
        if not area_texto:
            st.error("Cole a descrição da vaga ou selecione uma no buscador.")
        else:
            with st.spinner("Gemini gerando currículo..."):
                prompt = f"Use este perfil (JSON): {row[0]}. Adapte-o para esta vaga: {area_texto}. Retorne em Markdown."
                try:
                    resp = client.models.generate_content(model="gemini-2.0-flash", contents=prompt)
                    st.markdown("---")
                    st.markdown(resp.text)
                except Exception as e:
                    st.error(f"Erro na IA: {e}")

conn.close()
