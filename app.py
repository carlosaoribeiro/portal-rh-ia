import streamlit as st
import requests
from google import genai
from io import BytesIO
from docx import Document
from pypdf import PdfReader

# ==========================================
# CONFIG
# ==========================================
st.set_page_config(page_title="Portal RH IA", layout="wide")

if "GOOGLE_API_KEY" not in st.secrets:
    st.error("Configure GOOGLE_API_KEY.")
    st.stop()

if "SERPAPI_KEY" not in st.secrets:
    st.error("Configure SERPAPI_KEY.")
    st.stop()

client = genai.Client(api_key=st.secrets["GOOGLE_API_KEY"])

# ==========================================
# CONTROLE DE NAVEGAÇÃO
# ==========================================
if "step" not in st.session_state:
    st.session_state.step = 1

# ==========================================
# FUNÇÕES
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


def gerar_docx(texto):
    doc = Document()
    for linha in texto.split("\n"):
        doc.add_paragraph(linha)
    buffer = BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer


def calcular_match(cv, vaga):
    cv_words = set(cv.lower().split())
    vaga_words = set(vaga.lower().split())

    if len(vaga_words) == 0:
        return 0

    score = int((len(cv_words.intersection(vaga_words)) / len(vaga_words)) * 100)
    return min(score, 100)

# ==========================================
# TELA 1 – BUSCAR VAGAS
# ==========================================
if st.session_state.step == 1:

    st.header("Buscar Vagas")

    cargo = st.text_input("Cargo", "Android Developer")
    local = st.text_input("Localização", "Remote")

    if st.button("Buscar"):

        vagas = buscar_vagas(cargo, local)
        st.session_state.vagas = vagas

    if "vagas" in st.session_state:

        for i, v in enumerate(st.session_state.vagas):

            with st.container(border=True):
                st.subheader(v["title"])
                st.write(v["company"])
                st.write(v["location"])

                if st.button(f"Selecionar Vaga {i}", key=i):
                    st.session_state.vaga_ativa = v
                    st.session_state.step = 2
                    st.rerun()

# ==========================================
# TELA 2 – DETALHES DA VAGA
# ==========================================
elif st.session_state.step == 2:

    vaga = st.session_state.vaga_ativa

    st.header("Detalhes da Vaga")

    st.subheader(vaga["title"])
    st.write(vaga["company"])
    st.write(vaga["location"])
    st.write(vaga["description"])

    if st.button("Continuar para adaptar currículo"):
        st.session_state.step = 3
        st.rerun()

    if st.button("Voltar"):
        st.session_state.step = 1
        st.rerun()

# ==========================================
# TELA 3 – ADAPTAR CURRÍCULO
# ==========================================
elif st.session_state.step == 3:

    vaga = st.session_state.vaga_ativa

    st.header("Adaptar Currículo")

    uploaded_file = st.file_uploader("Enviar CV (PDF ou Word)", type=["pdf", "doc", "docx"])

    if uploaded_file:
        texto_cv = extrair_texto(uploaded_file)
        st.session_state.cv_texto = texto_cv
        st.success("Currículo carregado!")

    if "cv_texto" in st.session_state:

        score = calcular_match(st.session_state.cv_texto, vaga["description"])
        st.metric("Compatibilidade estimada", f"{score}%")

        if st.button("Gerar Versão ATS"):

            cv_limitado = st.session_state.cv_texto[:4000]
            vaga_limitada = vaga["description"][:2000]

            prompt = f"""
Rewrite ONLY the SUMMARY section to better align with the job description.

Do NOT invent experience.
Do NOT change dates or companies.
Keep ATS friendly plain text.

RESUME:
{cv_limitado}

JOB:
{vaga_limitada}
"""

            try:
                response = client.models.generate_content(
                    model="gemini-1.5-flash",
                    contents=[
                        {
                            "role": "user",
                            "parts": [{"text": prompt}]
                        }
                    ]
                )

                texto_final = response.candidates[0].content.parts[0].text

                st.text_area("Versão ATS", texto_final, height=500)

                st.download_button(
                    "Baixar Word",
                    gerar_docx(texto_final),
                    "CV_ATS.docx"
                )

            except Exception:
                st.error("Erro ao gerar conteúdo. Verifique limite ou chave API.")

    if st.button("Voltar para vagas"):
        st.session_state.step = 1
        st.rerun()
