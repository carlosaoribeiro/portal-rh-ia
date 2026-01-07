import re
import streamlit as st
from google import genai
from pypdf import PdfReader
import streamlit.components.v1 as components

# 1) CONFIGURAÇÃO DA PÁGINA
st.set_page_config(page_title="Gerador de CV Inteligente", layout="wide", page_icon="🚀")

# ---------- CSS ESTILO JNG (ALINHADO COM A SUA IMAGEM) ----------
CV_CSS = """
<style>
    body { background-color: #ffffff; font-family: 'Arial', sans-serif; color: #000; margin: 0; padding: 20px; }
    .cv-paper { max-width: 850px; margin: auto; line-height: 1.4; }
    
    h1 { font-size: 26px; margin-bottom: 5px; font-weight: bold; }
    .contact-line { font-size: 0.95em; margin-bottom: 20px; border-bottom: 1px solid #eee; padding-bottom: 10px; }

    .section-title { 
        border-bottom: 1.5px solid #000; 
        text-transform: uppercase; 
        font-weight: bold; 
        margin-top: 25px; 
        margin-bottom: 10px; 
        font-size: 1.1em; 
    }

    .timeline-row { 
        display: flex; 
        justify-content: space-between; 
        font-weight: bold; 
        font-size: 1.1em; 
        margin-top: 15px;
    }

    .timeline-subrow { 
        display: flex; 
        justify-content: space-between; 
        font-style: italic; 
        margin-bottom: 8px; 
        font-size: 1em;
        color: #333;
    }

    .experience-description {
        text-align: justify;
        font-size: 10.5pt;
        margin-bottom: 15px;
        line-height: 1.5;
        white-space: pre-line;
    }
</style>
"""

# 2) CONEXÃO API GEMINI
if "GOOGLE_API_KEY" not in st.secrets:
    st.error("Erro: Configure a chave 'GOOGLE_API_KEY' nos Secrets do Streamlit!")
    st.stop()

client = genai.Client(api_key=st.secrets["GOOGLE_API_KEY"])

# ---------- HELPERS ----------
def detect_language(text):
    text = (text or "").lower()
    pt_hits = len(re.findall(r"\b(de|da|o|a|com|vaga|requisitos|experiência|desenvolvimento)\b", text))
    return "pt-BR" if pt_hits > 3 else "en"

# 3) INTERFACE PRINCIPAL
st.title("🚀 Gerador de CV Inteligente")
st.caption("Ajuste seu currículo para o formato profissional **SheetsResume/JNG**.")

col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("📁 Dados de Entrada")
    uploaded_file = st.file_uploader("Suba seu currículo atual (PDF)", type="pdf")
    job_description = st.text_area("Descrição da vaga alvo:", height=250, placeholder="Cole os requisitos da vaga aqui...")

if "full_response" not in st.session_state:
    st.session_state.full_response = ""

# Botão de Ação
if st.button("Gerar CV e Análise no Formato Referência", use_container_width=True):
    if uploaded_file and job_description.strip():
        st.session_state.full_response = "" # Limpeza inicial
        
        with st.spinner("Analisando e formatando currículo..."):
            try:
                # Extração de Texto do PDF
                reader = PdfReader(uploaded_file)
                cv_text = "".join([p.extract_text() for p in reader.pages if p.extract_text()])
                lang = detect_language(job_description)
                target_lang = "PORTUGUÊS (Brasil)" if lang == "pt-BR" else "ENGLISH (US)"

                # PROMPT RIGOROSO PARA ALINHAMENTO VISUAL
                prompt = f"""
                You are a senior tech recruiter. Generate a response in {target_lang}.
                
                STRUCTURE RULES:
                1. Return exactly two blocks: [CV_START] (HTML) [CV_END] and [ANALYSIS_START] (Markdown) [ANALYSIS_END].
                2. In the CV (HTML):
                   - Use <h1><b>Name</b></h1>.
                   - Use <div class="section-title">SECTION TITLE</div>.
                   - For each job:
                     <div class="timeline-row"><span>Company Name</span><span>Date (e.g., Sep 2024 – Present)</span></div>
                     <div class="timeline-subrow"><span>Job Title</span><span>Location (e.g., Texas, USA (Remote))</span></div>
                     <div class="experience-description">A single paragraph of text. Separate achievements with "/" instead of bullets.</div>
                3. In the Analysis (Markdown):
                   - Include "O que está melhor", "O que melhorar", "Pontos fortes" and "Perguntas de entrevista".
                
                JOB DESCRIPTION: {job_description}
                CV DATA: {cv_text}
                """
                
                response = client.models.generate_content(model="gemini-2.0-flash", contents=prompt)
                st.session_state.full_response = response.text
                st.rerun()
                
            except Exception as e:
                st.error(f"Erro ao processar: {e}")

# 4) EXIBIÇÃO DOS RESULTADOS
if st.session_state.full_response:
    res = st.session_state.full_response
    
    # Extração via Regex
    cv_match = re.search(r"\[CV_START\](.*?)\[CV_END\]", res, re.DOTALL)
    analysis_match = re.search(r"\[ANALYSIS_START\](.*?)\[ANALYSIS_END\]", res, re.DOTALL)
