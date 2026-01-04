import re
import streamlit as st
from google import genai
from pypdf import PdfReader

# 1) CONFIGURAÇÃO DA PÁGINA
st.set_page_config(page_title="Portal de Carreira IA", layout="wide", page_icon="🚀")

# CSS Customizado para simular o layout dos prints (Papel A4 e Timeline)
st.markdown("""
    <style>
    /* Estilo do container que simula o papel do CV */
    .cv-paper {
        background-color: white;
        padding: 40px;
        border-radius: 5px;
        border: 1px solid #d3d3d3;
        box-shadow: 2px 2px 15px rgba(0,0,0,0.1);
        color: #1a1a1a;
        font-family: 'Arial', sans-serif;
        line-height: 1.5;
    }
    /* Estilização para simular o cabeçalho e as linhas do SheetsResume */
    .cv-paper h1, .cv-paper h2, .cv-paper h3 {
        color: #000;
        margin-bottom: 5px;
    }
    .stButton>button {
        width: 100%;
        border-radius: 5px;
        height: 3em;
        background-color: #f0f2f6;
    }
    </style>
    """, unsafe_allow_html=True)

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
    job_description = st.text_area("Descrição da vaga alvo:", height=300, placeholder="Cole os requisitos da vaga aqui...")

with col2:
    st.subheader("✨ Resultado Otimizado")
    
    if "result" not in st.session_state: 
        st.session_state.result = ""

    if st.button("Gerar CV no Formato Referência"):
        if uploaded_file and job_description.strip():
            with st.spinner("Analisando e formatando currículo..."):
                try:
                    # Extração de texto
                    reader = PdfReader(uploaded_file)
                    cv_text = "".join([(p.extract_text() or "") for p in reader.pages]).strip()

                    lang = detect_language(job_description)
                    lang_rules = language_instructions(lang)

                    # 4) PROMPT REFINADO (Foco em Match Técnico + Layout JNG)
                    prompt = f"""
You are an expert resume writer specialized in the "SheetsResume/JNG" professional format.
{lang_rules}

TASK:
Rewrite the CV to maximize technical match with the job description. 
Adjust the "Work Experience" and "Projects" sections (like Oppia and Agiltec) to emphasize the specific technical keywords (e.g., MVVM, Threading, Sensors) from the job description.

STRICT FORMATTING RULES (Timeline Style):
1. NO SUMMARY: Start directly with WORK EXPERIENCE.
2. HEADER: Name in bold. One line for sub-headline. Contact info separated by '⬩'.
3. WORK EXPERIENCE LAYOUT:
   - Company Name (left) | Dates (right)
   - Title (left) | Location (right)
   - First bullet: One-sentence context of the company.
   - Following bullets: Technical achievements using action verbs.
4. MATCHING: If the JD asks for a skill you have (like Coroutines), ensure it appears prominently in the most relevant experience.

CV TEXT:
{cv_text}

JOB DESCRIPTION:
{job_description}

EXPECTED OUTPUT:
Return ONLY the [OPTIMIZED CV] in Markdown format, followed by [MATCH ANALYSIS] and [GAPS].
"""

                    # 5) CHAMADA AO MODELO
                    models_to_try = ["gemini-2.0-flash", "gemini-1.5-pro"]
                    response = None
                    for m in models_to_try:
                        try:
                            response = client.models.generate_content(model=m, contents=prompt)
                            if response.text: break
                        except: continue

                    if response:
                        st.session_state.result = response.text
                        st.success("✅ Currículo formatado com sucesso!")
                except Exception as e:
                    st.error(f"Erro: {e}")
        else:
            st.warning("⚠️ Suba o PDF e preencha a vaga.")

    # 6) EXIBIÇÃO EM "PAPEL"
    if st.session_state.result:
        # Exibe o resultado dentro de uma div com a classe 'cv-paper' definida no CSS
        st.markdown(f'<div class="cv-paper">', unsafe_allow_html=True)
        st.markdown(st.session_state.result)
        st.markdown('</div>', unsafe_allow_html=True)
        
        st.divider()
        st.download_button(
            label="📥 Baixar CV Ajustado (TXT)",
            data=st.session_state.result,
            file_name="cv_final_jng_format.txt",
            mime="text/plain",
            use_container_width=True
        )
