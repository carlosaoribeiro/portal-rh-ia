import streamlit as st
import requests
from google import genai
from io import BytesIO
from docx import Document
from pypdf import PdfReader

# ==========================================
# CONFIGURAÇÃO INICIAL
# ==========================================
st.set_page_config(page_title="Portal RH IA", layout="wide")

if "GOOGLE_API_KEY" not in st.secrets:
    st.error("GOOGLE_API_KEY não configurada no Secrets.")
    st.stop()

if "SERPAPI_KEY" not in st.secrets:
    st.error("SERPAPI_KEY não configurada no Secrets.")
    st.stop()

# Inicializa cliente Gemini (Versão Novo SDK google-genai)
try:
    client = genai.Client(api_key=st.secrets["GOOGLE_API_KEY"])
    # Teste rápido para validar chave - Corrigido para o formato do novo SDK
    client.models.generate_content(
        model="gemini-3.0-flash",
        contents="Ping"
    )
except Exception as e:
    st.error(f"Erro ao inicializar Gemini API: {str(e)}")
    st.stop()

# ==========================================
# ESTADO
# ==========================================
if "step" not in st.session_state:
    st.session_state.step = 1

# ==========================================
# FUNÇÕES
# ==========================================
def buscar_vagas(cargo, local):
    try:
        url = "https://serpapi.com/search.json"
        params = {
            "engine": "google_jobs",
            "q": f"{cargo} {local}",
            "hl": "pt",
            "api_key": st.secrets["SERPAPI_KEY"]
        }

        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        jobs = data.get("jobs_results", [])
        vagas = []

        for job in jobs:
            vagas.append({
                "title": job.get("title", "N/A"),
                "company": job.get("company_name", "N/A"),
                "location": job.get("location", "N/A"),
                "description": job.get("description", "")
            })

        return vagas

    except Exception as e:
        st.error(f"Erro ao buscar vagas: {str(e)}")
        return []


def extrair_texto(uploaded_file):
    try:
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
    except Exception as e:
        st.error(f"Erro ao ler arquivo: {str(e)}")
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
    try:
        cv_words = set(cv.lower().split())
        vaga_words = set(vaga.lower().split())

        if not vaga_words:
            return 0

        score = int((len(cv_words.intersection(vaga_words)) / len(vaga_words)) * 100)
        return min(score, 100)
    except:
        return 0


def gerar_ats(cv_texto, vaga_desc):
    cv_limitado = cv_texto[:4000]
    vaga_limitada = vaga_desc[:2000]

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

    # Chamada corrigida para o SDK google-genai
    response = client.models.generate_content(
        model="gemini-1.5-flash",
        contents=prompt
    )

    return response.text


# ==========================================
# TELA 1 – BUSCAR VAGAS
# ==========================================
if st.session_state.step == 1:

    st.header("Buscar Vagas")

    cargo = st.text_input("Cargo", "Android Developer")
    local = st.text_input("Localização", "Remote")

    if st.button("Buscar"):
        st.session_state.vagas = buscar_vagas(cargo, local)

    if "vagas" in st.session_state:
        for i, v in enumerate(st.session_state.vagas):
            with st.container(border=True):
                st.subheader(v["title"])
                st.write(f"Empresa: {v['company']}")
                st.write(f"Local: {v['location']}")

                if st.button("Selecionar Vaga", key=f"vaga_{i}"):
                    st.session_state.vaga_ativa = v
                    st.session_state.step = 2
                    st.rerun()

# ==========================================
# TELA 2 – DETALHES
# ==========================================
elif st.session_state.step == 2:

    vaga = st.session_state.vaga_ativa

    st.header("Detalhes da Vaga")
    st.subheader(vaga["title"])
    st.write(f"**Empresa:** {vaga['company']}")
    st.write(f"**Local:** {vaga['location']}")
    st.write("---")
    st.write(vaga["description"])

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Continuar para adaptar currículo", use_container_width=True):
            st.session_state.step = 3
            st.rerun()
    with col2:
        if st.button("Voltar", use_container_width=True):
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
        if texto_cv:
            st.session_state.cv_texto = texto_cv
            st.success("Currículo carregado!")

    if "cv_texto" in st.session_state:

        score = calcular_match(st.session_state.cv_texto, vaga["description"])
        st.metric("Compatibilidade estimada", f"{score}%")

        if st.button("Gerar Versão ATS"):
            try:
                with st.spinner("IA otimizando seu resumo..."):
                    texto_final = gerar_ats(st.session_state.cv_texto, vaga["description"])

                    if not texto_final:
                        st.error("Resposta vazia da API.")
                    else:
                        st.text_area("Versão ATS Gerada", texto_final, height=500)

                        st.download_button(
                            "Baixar Word (.docx)",
                            gerar_docx(texto_final),
                            "CV_ATS_Otimizado.docx",
                            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                        )

            except Exception as e:
                st.error(f"Erro ao gerar conteúdo: {str(e)}")

    if st.button("Voltar para busca"):
        st.session_state.step = 1
        st.rerun()
