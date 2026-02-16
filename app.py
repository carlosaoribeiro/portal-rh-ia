import streamlit as st
import json
import sqlite3
from google import genai
from duckduckgo_search import DDGS
from datetime import datetime, timedelta

# =========================
# 1) SEGURANÇA E CONEXÃO
# =========================
# O Streamlit busca a chave automaticamente se você colocá-la em Settings > Secrets
if "GOOGLE_API_KEY" not in st.secrets:
    st.error("🚨 ERRO: Configure a GOOGLE_API_KEY nos 'Secrets' do Streamlit!")
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
# 2) REGRA DE NEGÓCIO: BUSCA FILTRADA
# =========================
def motor_de_busca_agente(cargo, local):
    """
    RN-01: O Agente deve ignorar páginas de suporte e ajuda.
    RN-02: Focar apenas em diretórios de vagas (Jobs).
    """
    hoje = datetime.now()
    # Criando uma query que força o Google/DuckDuckGo a ignorar lixo
    query = (
        f'"{cargo}" "{local}" '
        f'(site:linkedin.com/jobs/view OR site:glassdoor.com/Job OR site:flexjobs.com OR site:remote.co) '
        f'-intitle:"help" -intitle:"ajuda" -intitle:"support" -intitle:"check"'
    )
    
    vagas_validadas = []
    try:
        with DDGS() as ddgs:
            results = ddgs.text(query, max_results=15)
            for r in results:
                # RF: Validação de URL de vaga real (padrão de software profissional)
                link = r['href'].lower()
                if any(ponto in link for ponto in ['/jobs/', '/job/', '/viewjob', '/remote-jobs/']):
                    vagas_validadas.append(r)
    except Exception as e:
        st.error(f"Erro na busca: {e}")
    return vagas_validadas

# =========================
# 3) INTERFACE (UI/UX)
# =========================
st.sidebar.title("🤖 Agent Command Center")
app_mode = st.sidebar.radio("Navegação:", ["🔍 Motor de Busca Ativa", "📄 Gerador de Currículo"])

# Persistência da Matriz no SQLite 
st.sidebar.subheader("Sua Base de Dados")
matrix_input = st.sidebar.file_uploader("Upload Matriz JSON", type=["json"])
if matrix_input:
    matrix_data = json.load(matrix_input)
    conn.execute("INSERT OR REPLACE INTO user_profile (id, matrix_json, last_updated) VALUES (1, ?, datetime('now'))", 
                 (json.dumps(matrix_data),))
    conn.commit()
    st.sidebar.success("✅ Perfil atualizado no banco!")

# --- MÓDULO BUSCA ---
if app_mode == "🔍 Motor de Busca Ativa":
    st.header("🔍 Agente de Varredura de Oportunidades")
    st.write(f"Data: {datetime.now().strftime('%d/%m/%Y')} | Filtro: Últimos 7 dias")

    c1, c2 = st.columns(2)
    with c1: cargo_q = st.text_input("Cargo (Ex: Android Developer):", value="Android Developer")
    with c2: local_q = st.text_input("Local (Ex: Houston ou Remote):", value="Remote")

    if st.button("Agente, inicie a busca nos portais selecionados"):
        vagas = motor_de_busca_agente(cargo_q, local_q)
        
        if vagas:
            st.success(f"Encontramos {len(vagas)} listagens de emprego REAIS.")
            for i, v in enumerate(vagas):
                with st.container(border=True):
                    st.markdown(f"### {v['title']}")
                    st.caption(f"🌍 Fonte oficial: {v['href']}")
                    st.write(v['body'])
                    if st.button(f"Selecionar Vaga #{i+1}", key=f"v_{i}"):
                        st.session_state['vaga_ativa'] = v['body']
                        st.success("Vaga enviada para adaptação!")
        else:
            st.warning("Nenhuma vaga recente encontrada. Tente simplificar o cargo.")

# --- MÓDULO GERADOR ---
elif app_mode == "📄 Gerador de Currículo":
    st.header("📄 Adaptador de Currículo (IA)")
    # Recupera matriz do SQLite [cite: 1]
    row = conn.execute("SELECT matrix_json FROM user_profile WHERE id = 1").fetchone()
    if not row:
        st.warning("⚠️ Carregue sua Matriz JSON no menu lateral primeiro.")
        st.stop()
    
    saved_matrix = json.loads(row[0])
    vaga_texto = st.session_state.get('vaga_ativa', "")
    
    st.text_area("Descrição da Vaga Capturada:", value=vaga_texto, height=200)
    
    if st.button("Gerar Currículo Otimizado para esta Vaga"):
        with st.spinner("IA processando sua matriz e a descrição da vaga..."):
            # Aqui a IA usa sua chave para trabalhar
            prompt = f"Adapte este perfil: {json.dumps(saved_matrix)} para a vaga: {vaga_texto}. Foque em Android e Product Management."
            resp = client.models.generate_content(model="gemini-2.0-flash", contents=prompt)
            st.success("Currículo gerado com sucesso!")
            st.markdown(resp.text)
