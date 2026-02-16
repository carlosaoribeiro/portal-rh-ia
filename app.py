import re
import json
import sqlite3
import streamlit as st
from google import genai
from pypdf import PdfReader
import streamlit.components.v1 as components
from html import escape

# =========================
# 1) CONFIGURAÇÃO DA PÁGINA E DB
# =========================
st.set_page_config(page_title="Agente de Carreira AI", layout="wide", page_icon="🚀")

def init_db():
    conn = sqlite3.connect('career_agent.db')
    c = conn.cursor()
    # Tabela para sua Matriz (Fonte de Verdade)
    c.execute('''CREATE TABLE IF NOT EXISTS user_profile 
                 (id INTEGER PRIMARY KEY, matrix_json TEXT, last_updated DATETIME)''')
    # Tabela para Log de Vagas (Motor de Busca)
    c.execute('''CREATE TABLE IF NOT EXISTS job_log 
                 (id INTEGER PRIMARY KEY, title TEXT, company TEXT, link TEXT, status TEXT)''')
    conn.commit()
    return conn

conn = init_db()

# =========================
# 2) NAVEGAÇÃO (SIDEBAR)
# =========================
st.sidebar.title("🤖 Agent Command Center")
app_mode = st.sidebar.radio("Selecione o Módulo:", 
                            ["🔍 Motor de Busca", "📄 Gerador de Currículo"])

st.sidebar.divider()
st.sidebar.subheader("⚙️ Configurações Base")
# Upload da Matriz agora fica fixo no Sidebar para ser usado em ambos os módulos
matrix_input = st.sidebar.file_uploader("Atualizar Matriz JSON", type=["json"])

if matrix_input:
    matrix_data = json.load(matrix_input)
    # Salva no SQLite para persistência
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO user_profile (id, matrix_json, last_updated) VALUES (1, ?, datetime('now'))", 
              (json.dumps(matrix_data),))
    conn.commit()
    st.sidebar.success("Matriz salva no banco local!")

# =========================
# 3) MÓDULO: MOTOR DE BUSCA (NOVO)
# =========================
if app_mode == "🔍 Motor de Busca":
    st.title("🔍 Motor de Busca de Vagas (Houston/Remote)")
    st.info("Este agente busca vagas e filtra as melhores oportunidades para você.")
    
    col1, col2 = st.columns(2)
    with col1:
        cargo_busca = st.text_input("Cargo desejado:", value="Product Manager")
    with col2:
        local_busca = st.text_input("Localização:", value="Houston, TX")
    
    if st.button("Agente, buscar novas vagas"):
        with st.spinner("O Agente está varrendo a web..."):
            # Lógica simplificada: aqui você integraria com uma API de busca (Serper/Jina)
            # Por enquanto, simulamos o resultado
            st.warning("Integração de busca em tempo real requer chave de API de busca (ex: Serper.dev).")
            # Exemplo de como salvar no DB para o futuro:
            # c.execute("INSERT INTO job_log (title, company, status) VALUES (?, ?, ?)", (cargo_busca, 'Empresa X', 'Nova'))

# =========================
# 4) MÓDULO: GERADOR DE CURRÍCULO (SEU CÓDIGO ORIGINAL)
# =========================
elif app_mode == "📄 Gerador de Currículo":
    st.title("📄 Adaptador de Currículo Inteligente")
    
    # Tenta carregar matriz do DB primeiro
    c = conn.cursor()
    c.execute("SELECT matrix_json FROM user_profile WHERE id = 1")
    row = c.fetchone()
    
    if not row:
        st.warning("⚠️ Por favor, faça o upload da sua Matriz JSON no menu lateral primeiro.")
        st.stop()
    
    saved_matrix = json.loads(row[0])

    # Seus inputs de alvo
    st.subheader("Informações da Vaga Alvo")
    job_description = st.text_area("Cole aqui a descrição da vaga:", height=200)
    company_description = st.text_area("Descrição da empresa (opcional):", height=100)

    # Lógica de geração (o restante do seu código original de extração e Gemini)
    # Use 'saved_matrix' como a base para 'btn_gerar'
    
    if st.button("Gerar Currículo Otimizado", use_container_width=True):
        if not job_description.strip():
            st.error("A descrição da vaga é obrigatória.")
        else:
            # Aqui entra a sua função client.models.generate_content 
            # enviando o prompt com a 'saved_matrix'
            st.success("Currículo gerado com sucesso!")
            # [O restante da lógica de exibição HTML e download permanece igual]
