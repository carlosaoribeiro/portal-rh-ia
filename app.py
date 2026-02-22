import streamlit as st
import requests
from io import BytesIO
from docx import Document

st.set_page_config(page_title="Portal RH IA", layout="wide")

# --------------------
# SESSION
# --------------------
if "step" not in st.session_state:
    st.session_state.step = 1

# --------------------
# FUNÇÕES
# --------------------

def buscar_vagas(cargo, local):
    serp_key = st.secrets.get("SERPAPI_KEY")
    if not serp_key:
        return []

    try:
        url = "https://serpapi.com/search.json"
        params = {
            "engine": "google_jobs",
            "q": f"{cargo} {local}",
            "api_key": serp_key
        }
        r = requests.get(url, params=params, timeout=10)
        return r.json().get("jobs_results", [])
    except:
        return []


def extrair_texto(file):
    try:
        if file.type == "application/pdf":
            from pypdf import PdfReader
            reader = PdfReader(file)
            return "".join(page.extract_text() or "" for page in reader.pages)
        else:
            doc = Document(file)
            return "\n".join(p.text for p in doc.paragraphs)
    except:
        return ""


def extrair_skills(texto):
    tech_stack = [
        "kotlin", "java", "compose", "firebase",
        "mvvm", "hilt", "retrofit", "android"
    ]
    texto = texto.lower()
    return [skill for skill in tech_stack if skill in texto]


def calcular_score(skills_vaga, skills_cv):
    if not skills_vaga:
        return 0, [], []

    match = set(skills_vaga).intersection(set(skills_cv))
    faltantes = set(skills_vaga) - set(skills_cv)

    score = (len(match) / len(skills_vaga)) * 100
    return round(score, 2), list(match), list(faltantes)


def gerar_docx(texto):
    doc = Document()
    for linha in texto.split("\n"):
        doc.add_paragraph(linha)

    buffer = BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer


# --------------------
# TELA 1
# --------------------

if st.session_state.step == 1:

    st.title("Portal RH IA")
    st.header("🔍 Buscar Vagas")

    cargo = st.text_input("Cargo", "Android Developer")
    local = st.text_input("Localidade", "Brasil")

    if st.button("Buscar"):
        with st.spinner("Buscando..."):
            st.session_state.vagas = buscar_vagas(cargo, local)

    if "vagas" in st.session_state:
        for i, vaga in enumerate(st.session_state.vagas):
            with st.container(border=True):
                st.subheader(vaga.get("title"))
                st.write(vaga.get("company_name"))

                if st.button("Selecionar", key=i):
                    st.session_state.vaga_ativa = vaga
                    st.session_state.step = 2
                    st.rerun()


# --------------------
# TELA 2
# --------------------

elif st.session_state.step == 2:

    vaga = st.session_state.vaga_ativa

    st.header(vaga.get("title"))
    st.write(vaga.get("description", ""))

    st.markdown("---")

    upload = st.file_uploader("Upload CV", type=["pdf", "docx"])

    if upload:

        texto_cv = extrair_texto(upload)
        desc_vaga = vaga.get("description", "")

        skills_vaga = extrair_skills(desc_vaga)
        skills_cv = extrair_skills(texto_cv)

        score, match, faltantes = calcular_score(skills_vaga, skills_cv)

        st.metric("Compatibilidade", f"{score}%")

        st.write("### Skills encontradas")
        st.write(match)

        st.write("### Skills faltantes")
        st.write(faltantes)

        # -------- NOVA PARTE --------

        if score > 0:
            texto_adaptado = f"""
Currículo Adaptado para a vaga de {vaga.get("title")}

Resumo Profissional:
Profissional com experiência em {", ".join(match)}.
Perfil alinhado com os requisitos da vaga.

Skills Principais:
{", ".join(match)}

"""

            arquivo_docx = gerar_docx(texto_adaptado)

            st.download_button(
                label="📥 Baixar CV Adaptado",
                data=arquivo_docx,
                file_name="CV_Adaptado.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            )

    if st.button("Voltar"):
        st.session_state.step = 1
        st.rerun()
