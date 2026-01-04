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
    text = (job_text or "").strip().lower()
    if not text: return "pt-BR"
    has_pt_chars = bool(re.search(r"[àáâãçéêíóôõúü]", text))
    pt_hits = len(re.findall(r"\b(o|a|os|as|de|da|do|das|dos|para|com|sem|que|não|uma|um|em|no|na|nos|nas|por|seu|sua)\b", text))
    en_hits = len(re.findall(r"\b(the|and|or|with|without|to|for|you|we|our|role|requirements|experience|skills|responsibilities)\b", text))
    if has_pt_chars or pt_hits >= 4: return "pt-BR"
    return "en" if en_hits >= 4 else "pt-BR"

def language_instructions(lang: str) -> str:
    if lang == "pt-BR":
        return "IDIOMA: Português (Brasil). Use títulos: EXPERIÊNCIA PROFISSIONAL, FORMAÇÃO ACADÊMICA, CERTIFICAÇÕES E HABILIDADES."
    return "LANGUAGE: English. Use headings: WORK EXPERIENCE, EDUCATION, CERTIFICATIONS, SKILLS & INTERESTS."

# 3) INTERFACE
st.title("🚀 Gerador de CV Inteligente")
st.markdown("Ajuste seu currículo para o formato profissional **SheetsResume/JNG**.")

col1, col2 = st.columns([1, 1.2])

with col1:
    st.subheader("📁 Dados de Entrada")
    uploaded_file = st.file_uploader("Suba seu currículo atual (PDF)", type="pdf")
    job_description = st.text_area("Descrição da vaga alvo:", height=300)

with col2:
    st.subheader("✨ Resultado Otimizado")
    if "result" not in st.session_state: st.session_state.result = ""

    if st.button("Gerar CV no Formato Referência", use_container_width=True):
        if uploaded_file and job_description.strip():
            with st.spinner("Formatando currículo..."):
                try:
                    reader = PdfReader(uploaded_file)
                    cv_text = "".join([(p.extract_text() or "") for p in reader.pages]).strip()

                    lang = detect_language(job_description)
                    lang_rules = language_instructions(lang)

                    # 4) PROMPT AJUSTADO PARA O FORMATO DA IMAGEM
                    prompt = f"""
You are an expert resume writer specialized in the "SheetsResume/JNG" professional format.

{lang_rules}

TASK:
Rewrite the user's CV to match the EXACT structural style of the reference provided, optimized for the job description.

STRICT FORMATTING RULES (Based on reference):
1. HEADER: Name in bold, followed by a one-line sub-headline (Job Title + Key Value). Contact info on one line separated by symbols (⬩).
2. WORK EXPERIENCE:
   - Company Name on the left, Dates (e.g., Oct. 2020 – Present) on the far right.
   - Job Title on the left, Location/Remote on the far right.
   - First bullet: A brief 1-sentence description of what the company does.
   - Sub-bullets: Achievement-oriented, starting with strong action verbs. Highlight technical match (Kotlin, MVVM, etc.).
3. EDUCATION: University Name (left), Graduation Date (right). Degree/Major (left), City (right).
4. SKILLS & INTERESTS: Grouped at the bottom. Format as "Skills: Skill 1; Skill 2; Skill 3".

GOLDEN RULES:
- DO NOT use a "Summary" section (as per reference style). Start with Work Experience.
- DO NOT mention career transition.
- Integrate keywords from the Job Description into the bullet points.

CV TEXT:
{cv_text}

JOB DESCRIPTION:
{job_description}

EXPECTED OUTPUT:
Return ONLY the [OPTIMIZED CV] in Markdown, followed by a brief [MATCH ANALYSIS] and [GAPS].
"""

                    models_to_try = ["gemini-2.0-flash", "gemini-1.5-pro"]
                    response = None
                    for m in models_to_try:
                        try:
                            response = client.models.generate_content(model=m, contents=prompt)
                            if response.text: break
                        except: continue

                    if response:
                        st.session_state.result = response.text
                        st.success("✅ Currículo formatado!")
                except Exception as e:
                    st.error(f"Erro: {e}")

    if st.session_state.result:
        st.markdown(st.session_state.result)
        st.download_button("📥 Baixar CV Ajustado", st.session_state.result, "cv_formatado.txt", use_container_width=True)
