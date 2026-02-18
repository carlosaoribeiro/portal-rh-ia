import streamlit as st
import json
import sqlite3
import requests
from google import genai
from datetime import datetime
from io import BytesIO
from docx import Document
from pypdf import PdfReader

# ==========================================
# CONFIGURAÇÃO
# ==========================================
st.set_page_config(page_title="Agente de Carreira AI", layout="wide", page_icon="🚀")

# ==========================================
# VALIDAÇÃO DE CHAVES
# ==========================================
if "GOOGLE_API_KEY" not in st.secrets:
    st.error("Configure GOOGLE_API_KEY no Streamlit Secrets.")
    st.stop()

if "SERPAPI_KEY" not in st.secrets:
    st.error("Configure SERPAPI_KEY no Streamlit Secrets.")
    st.stop()

client = genai.Client(api_key=st.secrets["GOOGLE_API_KEY"])

# ==========================================
# BANCO
# ==========================================
def init_db():
    conn = sqlite3.connect("career_agent.db", check_same_thread=False)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS user_profile (
            id INTEGER PRIMARY KEY,
            matrix_json TEXT,
            last_updated DATETIME
        )
    """)
    conn.commit()
    return conn

conn = init_db()

# ==========================================
# EXTRAIR TEXTO
# ==========================================
def extrair_texto(uploaded_file):

    if uploaded_file.type == "application/pdf":
        reader = PdfReader(uploaded_file)
        texto = ""
        for page in reader.pages:
            texto += page.extract_text() or ""
        return texto

    elif uploaded_file.type in [
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/msword"
    ]:
        doc = Document(uploaded_file)
        return "\n".join([p.text for p in doc.paragraphs])

    return None

# ==========================================
# GERAR DOCX
# ==========================================
def gerar_docx(texto):
    doc = Document()
    for linha in texto.split("\n"):
        doc.add_paragraph(linha)
    buffer = BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer

# ==========================================
# MATCH SIMPLES
# ==========================================
def calcular_match(cv_texto, vaga_texto):
    cv_words = set(cv_texto.lower().split())
    vaga_words = set(vaga_texto.lower().split())
    intersecao = cv_words.intersection(vaga_words)

    if len(vaga_words) == 0:
        return 0, []

    score = int((len(intersecao) / len(vaga_words)) * 100)
    return min(score, 100), list(intersecao)[:20]

# ==========================================
# BUSCA VAGAS
# ==========================================
def buscar_vagas(cargo, local):

    url = "https://serpapi.com/search.json"

    params = {
        "engine": "google_jobs",
        "q": f"{cargo} {local}",
        "hl": "en",
        "api_key": st.secrets["SERPAPI_KEY"]
    }

    response = requests.get(url, params=params)
    data = response.json()

    jobs = data.get("jobs_results", [])
    vagas = []

    for job in jobs:
        vagas.append({
            "title": job.get("title"),
            "company": job.get("company_name"),
            "location": job.get("location"),
            "description": job.get("description")
        })

    return vagas

# ==========================================
# SIDEBAR
# ==========================================
st.sidebar.title("Agent Command Center")

modo = st.sidebar.radio(
    "Módulo:",
    ["Buscar Vagas", "Adaptar Currículo"]
)

st.sidebar.divider()
st.sidebar.subheader("Enviar Currículo")

uploaded_file = st.sidebar.file_uploader(
    "PDF ou Word",
    type=["pdf", "doc", "docx"]
)

if uploaded_file:
    texto_cv = extrair_texto(uploaded_file)
    st.session_state["cv_text"] = texto_cv
    st.sidebar.success("Currículo carregado!")

# ==========================================
# BUSCAR VAGAS
# ==========================================
if modo == "Buscar Vagas":

    st.header("Buscar Vagas")

    cargo = st.text_input("Cargo", "Android Developer")
    local = st.text_input("Localização", "Remote")

    if st.button("Buscar"):

        vagas = buscar_vagas(cargo, local)

        if vagas:
            for i, v in enumerate(vagas):
                with st.container(border=True):
                    st.subheader(v["title"])
                    st.write(v["company"])
                    st.write(v["location"])

                    if st.button(f"Selecionar Vaga {i}", key=i):
                        st.session_state["vaga_ativa"] = v
                        st.success("Vaga selecionada!")
        else:
            st.warning("Nenhuma vaga encontrada.")

# ==========================================
# ADAPTAR CURRÍCULO
# ==========================================
elif modo == "Adaptar Currículo":

    st.header("Adaptador Inteligente")

    vaga = st.session_state.get("vaga_ativa")
    cv_texto = st.session_state.get("cv_text")

    if not vaga:
        st.warning("Selecione uma vaga primeiro.")
        st.stop()

    if not cv_texto:
        st.warning("Envie seu currículo primeiro.")
        st.stop()

    # MATCH
    score, palavras = calcular_match(cv_texto, vaga["description"])

    st.subheader("Match com a vaga")
    st.metric("Compatibilidade estimada", f"{score}%")
    st.write("Palavras em comum:", ", ".join(palavras))

    if st.button("Gerar Versão ATS"):

        prompt = f"""
Rewrite ONLY the SUMMARY section of the resume to better align with the job description.

Do NOT:
- Invent experience
- Modify employment history
- Add new technologies

Keep it ATS friendly.
Return plain text.

RESUME:
{cv_texto}

JOB:
{vaga["description"]}
"""

        resp = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt
        )

        texto_final = resp.text

        st.text_area("Currículo ATS", texto_final, height=500)

        st.download_button(
            "Baixar em Word",
            gerar_docx(texto_final),
            "Carlos_Ribeiro_ATS.docx"
        )
