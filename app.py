import streamlit as st
import json
import sqlite3
import requests
from google import genai
from datetime import datetime
from io import BytesIO
from docx import Document
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import letter
from pypdf import PdfReader  # ✅ CORRETO

# ==========================================
# CONFIGURAÇÃO
# ==========================================
st.set_page_config(page_title="Agente de Carreira AI", layout="wide", page_icon="🚀")

# ==========================================
# VALIDAÇÃO DE CHAVES
# ==========================================
if "GOOGLE_API_KEY" not in st.secrets:
    st.error("🚨 Configure GOOGLE_API_KEY no Streamlit Secrets.")
    st.stop()

if "SERPAPI_KEY" not in st.secrets:
    st.error("🚨 Configure SERPAPI_KEY no Streamlit Secrets.")
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
# EXTRAIR TEXTO DE PDF/DOCX
# ==========================================
import docx

def extrair_texto_arquivo(uploaded_file):

    if uploaded_file.type == "application/pdf":
        reader = PdfReader(uploaded_file)  # ✅ USANDO pypdf
        texto = ""
        for page in reader.pages:
            texto += page.extract_text() or ""
        return texto

    elif uploaded_file.type in [
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/msword"
    ]:
        doc = docx.Document(uploaded_file)
        return "\n".join([p.text for p in doc.paragraphs])

    return None

# ==========================================
# GERAR WORD
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
# GERAR PDF
# ==========================================
def gerar_pdf(texto):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    elements = []

    for linha in texto.split("\n"):
        elements.append(Paragraph(linha, styles["Normal"]))
        elements.append(Spacer(1, 8))

    doc.build(elements)
    buffer.seek(0)
    return buffer

# ==========================================
# MOTOR DE BUSCA – GOOGLE JOBS
# ==========================================
def agente_explorer_vagas(cargo, local):
    url = "https://serpapi.com/search.json"
    logs = []
    vagas = []

    params = {
        "engine": "google_jobs",
        "q": f"{cargo} {local}",
        "hl": "en",
        "api_key": st.secrets["SERPAPI_KEY"]
    }

    try:
        response = requests.get(url, params=params)
        data = response.json()

        jobs = data.get("jobs_results", [])
        logs.append(f"🔍 {len(jobs)} vagas encontradas na API.")

        for job in jobs:
            link = None

            if job.get("related_links"):
                link = job["related_links"][0].get("link")

            if not link and job.get("apply_options"):
                link = job["apply_options"][0].get("link")

            vagas.append({
                "title": job.get("title"),
                "company": job.get("company_name"),
                "location": job.get("location"),
                "description": job.get("description"),
                "link": link,
                "apply_options": job.get("apply_options", [])
            })

        return vagas, logs

    except Exception as e:
        logs.append(f"🚨 Erro: {str(e)}")
        return [], logs

# ==========================================
# SIDEBAR
# ==========================================
st.sidebar.title("🤖 Agent Command Center")

modo = st.sidebar.radio(
    "Módulo:",
    ["🔍 Buscar Vagas", "📄 Adaptar Currículo"]
)

st.sidebar.divider()
st.sidebar.subheader("Sincronizar Perfil")

uploaded_file = st.sidebar.file_uploader(
    "Enviar Arquivo (JSON, PDF, DOC, DOCX)",
    type=["json", "pdf", "doc", "docx"]
)

if uploaded_file:

    if uploaded_file.type == "application/json":
        matrix_data = json.load(uploaded_file)
        conn.execute(
            "INSERT OR REPLACE INTO user_profile (id, matrix_json, last_updated) VALUES (1, ?, datetime('now'))",
            (json.dumps(matrix_data),)
        )
        conn.commit()
        st.session_state["cv_text"] = None
        st.sidebar.success("✅ Matriz JSON salva!")

    else:
        texto_cv = extrair_texto_arquivo(uploaded_file)
        st.session_state["cv_text"] = texto_cv
        st.sidebar.success("📄 Currículo carregado!")

# ==========================================
# BUSCAR VAGAS
# ==========================================
if modo == "🔍 Buscar Vagas":

    st.header("🔍 Google Jobs – Busca Inteligente")
    st.caption(f"Data: {datetime.now().strftime('%d/%m/%Y')}")

    col1, col2 = st.columns(2)

    with col1:
        cargo = st.text_input("Cargo:", value="Android Developer")

    with col2:
        local = st.text_input("Localização:", value="Remote United States")

    if st.button("🚀 Iniciar Busca", use_container_width=True):

        vagas, logs = agente_explorer_vagas(cargo, local)

        if vagas:
            st.success(f"🎯 {len(vagas)} vagas listadas!")

            for i, v in enumerate(vagas):
                with st.container(border=True):

                    st.markdown(f"### {v['title']}")
                    st.markdown(f"**Empresa:** {v['company']}")
                    st.markdown(f"📍 {v['location']}")

                    if v["link"]:
                        st.markdown(f"[Abrir Vaga Principal]({v['link']})")

                    if st.button(f"Selecionar Vaga #{i+1}", key=f"vaga_{i}"):
                        st.session_state["vaga_ativa"] = v
                        st.success("Vaga selecionada!")

        else:
            st.warning("Nenhuma vaga encontrada.")

# ==========================================
# ADAPTAR CURRÍCULO
# ==========================================
elif modo == "📄 Adaptar Currículo":

    st.header("📄 Adaptador Inteligente")

    vaga = st.session_state.get("vaga_ativa")

    if not vaga:
        st.warning("⚠️ Selecione uma vaga primeiro.")
        st.stop()

    perfil_base = st.session_state.get("cv_text")

    if not perfil_base:
        st.warning("⚠️ Envie seu currículo primeiro.")
        st.stop()

    if st.button("🧠 Gerar Currículo ATS", use_container_width=True):

        with st.spinner("IA adaptando estrategicamente..."):

            prompt = f"""
Rewrite ONLY the SUMMARY section to better align with the job description.

Do NOT invent experience.
Do NOT modify employment history.
Keep ATS-friendly plain text format.

ORIGINAL CV:
{perfil_base}

JOB DESCRIPTION:
{vaga['description']}
"""

            resp = client.models.generate_content(
                model="gemini-2.0-flash",
                contents=prompt
            )

            texto_final = resp.text

            st.text_area("Resultado ATS:", texto_final, height=500)

            # DOWNLOAD WORD
            st.download_button(
                "⬇️ Baixar em Word (.docx)",
                gerar_docx(texto_final),
                "Carlos_Ribeiro_ATS.docx"
            )

            # DOWNLOAD PDF
            st.download_button(
                "⬇️ Baixar em PDF",
                gerar_pdf(texto_final),
                "Carlos_Ribeiro_ATS.pdf"
            )
