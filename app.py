import re
import streamlit as st
from google import genai
from pypdf import PdfReader

# 1) CONFIGURAÇÃO DA PÁGINA
st.set_page_config(page_title="Portal de Carreira IA", layout="wide", page_icon="🚀")

# 2) CONEXÃO COM A API
if "GOOGLE_API_KEY" not in st.secrets:
    st.error("Erro: Configure a chave 'GOOGLE_API_KEY' nos Secrets do Streamlit!")
    st.stop()

client = genai.Client(api_key=st.secrets["GOOGLE_API_KEY"])

# ---------- Helpers ----------
def detect_language(job_text: str) -> str:
    """
    Retorna 'pt-BR' ou 'en' baseado em heurística.
    - Se encontrar sinais fortes de PT (acentos, stopwords PT), retorna pt-BR.
    - Caso contrário, tenta EN (stopwords EN) e retorna en.
    - Se der empate/indefinido, usa en como fallback (mais comum em JDs globais).
    """
    text = (job_text or "").strip().lower()
    if not text:
        return "pt-BR"

    # Sinais fortes de português
    has_pt_chars = bool(re.search(r"[àáâãçéêíóôõúü]", text))
    pt_hits = len(re.findall(r"\b(o|a|os|as|de|da|do|das|dos|para|com|sem|que|não|uma|um|em|no|na|nos|nas|por|seu|sua)\b", text))

    # Sinais de inglês
    en_hits = len(re.findall(r"\b(the|and|or|with|without|to|for|you|we|our|role|requirements|experience|skills|responsibilities)\b", text))

    if has_pt_chars or pt_hits >= 4:
        return "pt-BR"
    if en_hits >= 4 and pt_hits == 0:
        return "en"

    # fallback: se tiver mais "cara" de pt que en, pt; senão en
    return "pt-BR" if pt_hits > en_hits else "en"


def language_instructions(lang: str) -> str:
    if lang == "pt-BR":
        return (
            "IDIOMA OBRIGATÓRIO: Português (Brasil).\n"
            "- Escreva TODO o currículo e as seções em PT-BR.\n"
            "- Não misture inglês (exceto nomes próprios de tecnologias, produtos e empresas).\n"
            "- Use termos naturais de recrutamento no Brasil (Resumo, Experiência, Projetos, Educação, Habilidades).\n"
        )
    return (
        "REQUIRED LANGUAGE: English.\n"
        "- Write the ENTIRE resume and section headings in English.\n"
        "- Do not mix Portuguese (except proper nouns: company/product names).\n"
        "- Use standard US resume sections (Summary, Experience, Projects, Education, Skills).\n"
    )


# 3) INTERFACE
st.title("🚀 Gerador de CV Inteligente")
st.markdown("Ajuste seu currículo para dar match com os requisitos técnicos da vaga desejada.")

col1, col2 = st.columns([1, 1.2])

with col1:
    st.subheader("📁 Dados de Entrada")
    uploaded_file = st.file_uploader("Suba seu currículo atual (PDF)", type="pdf")

    job_description = st.text_area(
        "Descrição da vaga alvo (Requisitos Técnicos):",
        height=300,
        placeholder="Cole aqui a descrição da vaga..."
    )

with col2:
    st.subheader("✨ Resultado Otimizado")

    if "result" not in st.session_state:
        st.session_state.result = ""
    if "result_lang" not in st.session_state:
        st.session_state.result_lang = "pt-BR"

    if st.button("Gerar CV com Match Técnico", use_container_width=True):
        if uploaded_file and job_description.strip():
            with st.spinner("Analisando requisitos e alinhando experiências..."):
                try:
                    # Extração do texto do PDF
                    reader = PdfReader(uploaded_file)
                    cv_text = "".join([(p.extract_text() or "") for p in reader.pages]).strip()

                    if not cv_text:
                        st.error("Não foi possível extrair texto do PDF. Verifique se o arquivo não é uma imagem.")
                        st.stop()

                    # Detecta idioma da vaga
                    lang = detect_language(job_description)
                    st.session_state.result_lang = lang

                    # Instruções de idioma para o prompt
                    lang_rules = language_instructions(lang)

                    # 4) PROMPT
                    prompt = f"""
You are a senior Android engineer and a tech recruiter.

{lang_rules}

GOLDEN RULE (do not violate):
- Do NOT invent experience, tools, projects, companies, achievements, or metrics.
- If a requirement is not clearly supported by the CV text, mark it as a GAP and suggest how to address it in an interview honestly.

TASK:
Rewrite the CV below to maximize technical match with the job description, without mentioning "career transition".

ADJUSTMENT GUIDELINES:
1. IMMEDIATE TECH FOCUS: In the Summary, highlight Android development strengths (Kotlin, Java, MVVM, Clean Architecture) as primary skills.
2. EXPERIENCE ALIGNMENT:
   - Rewrite development experience bullets to mirror the job description keywords and technologies where truthful.
   - For leadership/PO roles, keep the history but emphasize technical collaboration, architecture, engineering decisions, delivery, and measurable outcomes.
3. JOB TERMINOLOGY:
   - Identify key technical terms in the job description and integrate them naturally ONLY where the CV supports it.
4. FORMAT:
   - Clean, professional, ATS-friendly, in Markdown, ready to copy.

CV TEXT:
{cv_text}

JOB DESCRIPTION:
{job_description}

EXPECTED OUTPUT:
1) [OPTIMIZED CV] - Final version ready to send.
2) [MATCH ANALYSIS] - Short explanation of how the experience maps to the requirements.
3) [GAPS & INTERVIEW TALKING POINTS] - Very specific requirements that need honest clarification + suggested interview framing.
"""

                    # 5) CHAMADA AO GEMINI (com fallback simples de modelo)
                    models_to_try = ["gemini-2.5-flash", "gemini-2.0-flash"]
                    last_err = None
                    response = None

                    for m in models_to_try:
                        try:
                            response = client.models.generate_content(model=m, contents=prompt)
                            if getattr(response, "text", None):
                                break
                        except Exception as e:
                            last_err = e
                            response = None

                    if not response or not getattr(response, "text", None):
                        st.error(f"Falha ao gerar conteúdo. {last_err if last_err else ''}")
                        st.stop()

                    st.session_state.result = response.text
                    st.success("✅ Currículo ajustado com sucesso!")

                except Exception as e:
                    st.error(f"Erro ao processar: {e}")
        else:
            st.warning("⚠️ Por favor, suba o PDF e cole a descrição da vaga.")

    # Renderiza resultado persistido
    if st.session_state.result:
        st.markdown(st.session_state.result)

        suffix = "en" if st.session_state.result_lang == "en" else "ptbr"
        st.download_button(
            label="📥 Baixar CV Ajustado (TXT)",
            data=st.session_state.result,
            file_name=f"cv_ajustado_match_{suffix}.txt",
            mime="text/plain",
            use_container_width=True
        )

# RODAPÉ
st.markdown("---")
st.caption("Ajustado para match técnico via IA. Revise os dados antes de enviar.")
