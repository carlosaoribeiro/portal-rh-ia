import streamlit as st
import json
import sqlite3
import re
from google import genai
from duckduckgo_search import DDGS
from datetime import datetime

# =========================
# 1) CONFIGURAÇÃO E SEGURANÇA
# =========================
st.set_page_config(page_title="Agente de Carreira AI", layout="wide", page_icon="🚀")

# Estilização customizada para os cards de vagas
st.markdown("""
    <style>
    .vaga-card {
        border: 1px solid #4a4a4a;
        padding: 15px;
        border-radius: 10px;
        margin-bottom: 10px;
    }
    </style>
""", unsafe_allow_html=True)

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
# 2) MOTOR DE BUSCA (RN-01 & RN-02)
# =========================
def agente_explorer_vagas(cargo, local):
    query = (
        f'"{cargo}" {local} '
        f'(site:[linkedin.com/jobs/view](https://linkedin.com/jobs/view) OR site:[glassdoor.com/Job](https://glassdoor.com/Job) OR site:flexjobs.com OR site:remote.co) '
        f'-intitle:"help" -intitle:"ajuda" -intitle:"support" -intitle:"check"'
    )
    
    vagas_validas = []
    logs = [f"🔍 Buscando: {query}"]
    
    try:
        with DDGS() as ddgs:
            results = ddgs.text(query, max_results=15)
            if results:
                for r in results:
                    link = r['href'].lower()
                    # RF-01: Validação estrita de URL de vaga
                    if any(p in link for p in ['/jobs/', '/job/', '/viewjob', '/remote-jobs/']):
                        vagas_validas.append(r)
                    else:
                        logs.append(f"🚫 Ignorado (Link não-vaga): {link[:40]}...")
            else:
                logs.append("⚠️ O buscador não retornou dados brutos.")
    except Exception as e:
        logs.append(f"🚨 Erro técnico: {str(e)}")
    
    return vagas_validas, logs

# =========================
# 3) INTERFACE PRINCIPAL
# =========================
st.sidebar.title("🤖 Agent Command Center")
app_mode = st.sidebar.radio("Módulo:", ["🔍 Motor de Busca", "📄 Gerador de Currículo"])

st.sidebar.divider()
st.sidebar.subheader("Sua Base de Dados")
matrix_input = st.sidebar.file_uploader("Sincronizar Matriz JSON (Perfil)", type=["json"])

if matrix_input:
    try:
        matrix_data = json.load(matrix_input)
        conn.execute("INSERT OR REPLACE INTO user_profile (id, matrix_json, last_updated) VALUES (1, ?, datetime('now'))", 
                     (json.dumps(matrix_data),))
        conn.commit()
        st.sidebar.success("✅ Perfil sincronizado!")
    except Exception as e:
        st.sidebar.error(f"Erro no JSON: {e}")

# --- MÓDULO 1: BUSCA ---
if app_mode == "🔍 Motor de Busca":
    st.header("🔍 Motor de Busca Ativa")
    st.caption(f"Status do Agente: Online | Data: {datetime.now().strftime('%d/%m/%Y')}")

    col1, col2 = st.columns(2)
    with col1:
        cargo_q = st.text_input("Cargo desejado:", value="Android Developer")
    with col2:
        local_q = st.text_input("Localidade (ex: Remote, Brazil):", value="Remote")

    if st.button("Agente, iniciar varredura", use_container_width=True):
        with st.spinner("Varrendo portais de vagas..."):
            vagas, logs_debug = agente_explorer_vagas(cargo_q, local_q)
            
            with st.expander("📝 Logs de Diagnóstico (Debug)"):
                for l in logs_debug: st.text(l)

            if vagas:
                st.success(f"Encontramos {len(vagas)} oportunidades potenciais!")
                for i, v in enumerate(vagas):
                    with st.container(border=True):
                        st.markdown(f"### {v['title']}")
                        st.caption(f"🔗 [Acessar Vaga no Portal]({v['href']})")
                        st.write(v['body'][:300] + "...")
                        
                        if st.button(f"🎯 Selecionar para Adaptação", key=f"btn_{i}"):
                            st.session_state['vaga_ativa'] = v['body']
                            st.session_state['vaga_titulo'] = v['title']
                            st.success(f"Vaga de '{v['title']}' carregada no Gerador!")
            else:
                st.warning("Nenhuma vaga listada. Tente ajustar os termos de busca.")

# --- MÓDULO 2: GERADOR ---
elif app_mode == "📄 Gerador de Currículo":
    st.header("📄 Adaptador de Perfil Profissional")
    
    # Carrega matriz do banco local
    row = conn.execute("SELECT matrix_json FROM user_profile WHERE id = 1").fetchone()
    if not row:
        st.warning("⚠️ Carregue sua Matriz JSON no menu lateral primeiro.")
        st.stop()
    
    vaga_selecionada = st.session_state.get('vaga_ativa', "")
    vaga_titulo = st.session_state.get('vaga_titulo', "Vaga não selecionada")

    if not vaga_selecionada:
        st.info("💡 Vá ao 'Motor de Busca' e selecione uma vaga primeiro.")
    else:
        st.subheader(f"Adaptando para: {vaga_titulo}")
        with st.expander("Ver descrição da vaga coletada"):
            st.write(vaga_selecionada)

        if st.button("🚀 Gerar Currículo Otimizado (Gemini 2.0)", use_container_width=True):
            with st.spinner("IA processando sua matriz e cruzando dados com a vaga..."):
                
                # Prompt Robusto para o Gemini
                prompt = f"""
                Você é um recrutador expert em ATS (Applicant Tracking Systems). 
                OBJETIVO: Adaptar a MATRIZ PROFISSIONAL do candidato para a VAGA fornecida.

                MATRIZ (JSON): {row[0]}
                DESCRIÇÃO DA VAGA: {vaga_selecionada}

                INSTRUÇÕES:
                1. Destaque as Hard Skills da matriz que coincidem com a vaga.
                2. Reescreva o resumo profissional para ser focado em resultados.
                3. Use bullet points de alto impacto nas experiências.
                4. Retorne APENAS o texto do currículo em Markdown elegante, pronto para copiar.
                5. Se houver lacunas (skills pedidas na vaga que não estão na matriz), não invente experiências, mas destaque as habilidades transferíveis.
                """
                
                try:
                    resp = client.models.generate_content(model="gemini-2.0-flash", contents=prompt)
                    st.divider()
                    st.success("✨ Currículo Adaptado com Sucesso!")
                    st.markdown(resp.text)
                    
                    st.download_button(
                        label="Baixar como TXT",
                        data=resp.text,
                        file_name=f"Curriculo_Adaptado_{datetime.now().strftime('%d%m')}.md",
                        mime="text/markdown"
                    )
                except Exception as e:
                    st.error(f"Erro na geração da IA: {e}")

# Fechar conexão ao final do script
conn.close()
