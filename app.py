import streamlit as st
import requests
import google.generativeai as genai
from docx import Document
from pypdf import PdfReader

st.set_page_config(page_title="Portal RH IA", layout="wide")

# ------------------------
# CONFIG IA (sem travar boot)
# ------------------------
model = None
api_key = st.secrets.get("GOOGLE_API_KEY")

if api_key:
    try:
        genai.configure(api_key=api_key.strip())
        model = genai.GenerativeModel("gemini-1.5-flash")
    except Exception as e:
        st.warning("Erro ao configurar IA. Rewrite ficará desativado.")

# ------------------------
# SESSION CONTROL
# ------------------------
if "step" not in st.session_state:
    st.session_state.step = 1

# ------------------------
# FUNÇÕES
# ------------------------

def buscar_vagas(cargo, local):
    try:
        serp_key = st.secrets.get("SERPAPI_KEY")
        if not serp_key:
            return []

        url = "https://serpapi.com/search.json"
        params = {
            "engine": "google_jobs",
            "q": f"{cargo} {local}",
            "api_key": serp_key.strip()
        }

        r = requests.get(url, params=params, timeout=10)
        return r.json().get("jobs_results", [])
    except:
        return []


def extrair_texto(file):
    try:
        if file.type == "application/pdf":
            reader = PdfReader(file)
            return "".join(page.extract_text() or "" for page in reader.pages)
        else:
            doc = Document(file)
            return "\n".join(p.text for p in doc.paragraphs)
    except:
        return ""


def extrair_skills(texto):
    tech_stack = [
        "kotlin", "java", "compose", "firebase", "mvvm",
        "hilt", "retrofit", "android", "sql", "git",
        "clean architecture", "rest api"
    ]
    texto = texto.lower()
    return [skill for skill in tech_stack if skill in texto]


def calcular_score(skills_vaga, skills_cv):
    if not skills_vaga:
        return 0

    match = set(skills_vaga).intersection(set(skills_cv))
    score = (len(match) / len(skills_vaga)) * 100
    return round(score, 2), list(match), list(set(skills_vaga) - set(skills_cv))


# ------------------------
# TELA 1 — BUSCA
# ------------------------

if st.session_state.step == 1:

    st.header("🔍 Buscar Vagas")

    c1, c2 = st.columns(2)
    cargo = c1.text_input("Cargo", "Android Developer")
    local = c2.text_input("Localidade", "Brasil")

    if st.button("Buscar"):
        with st.spinner("Buscando vagas..."):
            st.session_state.vagas = buscar_vagas(cargo, local)

    if "vagas" in st.session_state:

        if not st.session_state.vagas:
            st.warning("Nenhuma vaga encontrada.")
        else:
            for i, vaga in enumerate(st.session_state.vagas):
                with st.container(border=True):
                    st.subheader(vaga.get("title"))
                    st.write(
                        f"**Empresa:** {vaga.get('company_name')} | "
                        f"**Local:** {vaga.get('location')}"
                    )

                    if st.button("Ver Detalhes", key=f"vaga_{i}"):
                        st.session_state.vaga_ativa = vaga
                        st.session_state.step = 2
                        st.rerun()


# ------------------------
# TELA 2 — DETALHE + SCORE
# ------------------------

elif st.session_state.step == 2:

    vaga = st.session_state.vaga_ativa

    st.header("📄 Detalhes da Vaga")
    st.subheader(vaga.get("title"))
    st.write(vaga.get("description", "Descrição não disponível."))

    st.markdown("---")

    upload = st.file_uploader("Upload do CV matriz (PDF ou DOCX)", type=["pdf", "docx"])

    if upload:

        texto_cv = extrair_texto(upload)
        desc_vaga = vaga.get("description", "")

        skills_vaga = extrair_skills(desc_vaga)
        skills_cv = extrair_skills(texto_cv)

        score, match, faltantes = calcular_score(skills_vaga, skills_cv)

        st.markdown("## 📊 Compatibilidade")

        st.metric("Match (%)", f"{score}%")

        st.write("### ✅ Skills encontradas")
        st.write(match if match else "Nenhuma encontrada")

        st.write("### ❌ Skills faltantes")
        st.write(faltantes if faltantes else "Nenhuma")

        st.markdown("---")

        if score >= 60 and model:
            if st.button("Gerar CV Otimizado com IA"):
                with st.spinner("Gerando versão otimizada..."):
                    prompt = f"""
                    Reescreva o resumo profissional abaixo para alinhar com a vaga.
                    Não invente experiências.

                    VAGA:
                    {desc_vaga[:3000]}

                    CURRÍCULO:
                    {texto_cv[:4000]}
                    """

                    try:
                        response = model.generate_content(prompt)
                        st.success("Versão otimizada:")
                        st.write(response.text)
                    except:
                        st.error("Erro ao gerar conteúdo com IA.")

        elif score < 60:
            st.warning("Compatibilidade baixa. Avalie antes de otimizar.")

    if st.button("Voltar"):
        st.session_state.step = 1
        st.rerun()
