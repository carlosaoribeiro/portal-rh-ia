import streamlit as st
import requests
from io import BytesIO
from docx import Document
from datetime import datetime

st.set_page_config(page_title="Portal RH IA", layout="wide")

# --------------------
# MENU HORIZONTAL
# --------------------
abas = st.tabs(["Buscar Vagas", "Minhas Vagas", "Dashboard"])

st.markdown(f"### 📅 {datetime.today().strftime('%d/%m/%Y')}")

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


# =====================================================
# ABA 1 — BUSCAR VAGAS
# =====================================================

with abas[0]:

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

                # DATA REAL
                data_publicacao = None
                if "detected_extensions" in vaga:
                    data_publicacao = vaga["detected_extensions"].get("posted_at")

                if data_publicacao:
                    st.write(f"📅 Publicado: {data_publicacao}")

                # LINK CORRETO
                link_vaga = None
                if "apply_options" in vaga and vaga["apply_options"]:
                    link_vaga = vaga["apply_options"][0].get("link")

                if link_vaga:
                    st.markdown(f"[🔗 Ver vaga original]({link_vaga})")

                if st.button("Selecionar", key=f"vaga_{i}"):
                    st.session_state.vaga_ativa = vaga
                    st.session_state.vaga_selecionada = vaga
                    st.session_state.aba_detalhe = True


    # DETALHE DA VAGA
    if "vaga_selecionada" in st.session_state:

        vaga = st.session_state.vaga_selecionada

        st.markdown("---")
        st.header(vaga.get("title"))
        st.write(vaga.get("description", ""))

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

            if score >= 0:

                texto_adaptado = f"""Currículo Adaptado para {vaga.get("title")}

Resumo Profissional:
Profissional com experiência em {", ".join(match) if match else "tecnologias relacionadas"}.

Skills Principais:
{", ".join(match) if match else "A revisar manualmente."}
"""

                if texto_adaptado.strip():

                    arquivo_docx = gerar_docx(texto_adaptado)

                    st.download_button(
                        label="📥 Baixar CV Adaptado",
                        data=arquivo_docx,
                        file_name="CV_Adaptado.docx",
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                    )


# =====================================================
# ABA 2 — MINHAS VAGAS
# =====================================================

with abas[1]:
    st.header("Minhas Vagas Submetidas")
    if "vaga_selecionada" in st.session_state:
        st.write(st.session_state.vaga_selecionada.get("title"))
    else:
        st.info("Nenhuma vaga submetida ainda.")


# =====================================================
# ABA 3 — DASHBOARD
# =====================================================

with abas[2]:
    st.header("Dashboard")
    if "vaga_selecionada" in st.session_state:
        st.metric("Total de Vagas Avaliadas", 1)
    else:
        st.metric("Total de Vagas Avaliadas", 0)
