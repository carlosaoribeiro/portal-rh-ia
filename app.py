import re
import streamlit as st
from google import genai
from pypdf import PdfReader
import streamlit.components.v1 as components

# 1) CONFIGURAÇÃO DA PÁGINA
st.set_page_config(page_title="Gerador de Currículo", layout="wide", page_icon="🚀")

# CSS COM FONTE ROBOTO E ALINHAMENTO DA IMAGEM 2
CV_CSS = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;700&display=swap');
    
    body { 
        background-color: #f4f4f4; 
        font-family: 'Roboto', sans-serif; 
    }
    .cv-paper { 
        background-color: #ffffff; 
        width: 850px; 
        margin: 0 auto;
        padding: 50px; 
        box-shadow: 0 0 15px rgba(0,0,0,0.1); 
        color: #000; 
        line-height: 1.4; 
    }
    h1 { font-size: 26px; margin-bottom: 5px; font-weight: 700; text-align: center; font-family: 'Roboto', sans-serif; }
    .contact-line { font-size: 0.95em; margin-bottom: 20px; border-bottom: 1px solid #eee; padding-bottom: 10px; text-align: center; }
    .section-title { border-bottom: 1.5px solid #000; text-transform: uppercase; font-weight: 700; margin-top: 25px; margin-bottom: 10px; font-size: 1.1em; }
    
    /* Tabelas para alinhamento Empresa/Data (Imagem 2) */
    .timeline-table { width: 100%; border-collapse: collapse; margin-top: 15px; }
    .company-name { text-align: left; font-weight: 700; font-size: 1.1em; }
    .date-range { text-align: right; font-weight: 700; font-size: 1.1em; }
    
    .subrow-table { width: 100%; border-collapse: collapse; margin-bottom: 8px; }
    .job-title { text-align: left; font-style: italic; color: #333; }
    .location { text-align: right; font-style: italic; color: #333; }
    
    .experience-description { text-align: justify; font-size: 10.5pt; margin-bottom: 15px; line-height: 1.5; white-space: pre-line; }
</style>
"""

# 2) CONEXÃO API
if "GOOGLE_API_KEY" not in st.secrets:
    st.error("Configure a chave 'GOOGLE_API_KEY' nos Secrets!")
    st.stop()
client = genai.Client(api_key=st.secrets["GOOGLE_API_KEY"])

def detect_language(text):
    text = (text or "").lower()
    pt_hits = len(re.findall(r"\b(vaga|requisitos|experiência|responsabilidades|conhecimento)\b", text))
    return "pt-BR" if pt_hits > 2 else "en"

# 3) INTERFACE
st.markdown("<h1 style='text-align: center;'>🚀 Gerador de Currículo Inteligente</h1>", unsafe_allow_html=True)

_, center_col, _ = st.columns([1, 2, 1])

with center_col:
    uploaded_file = st.file_uploader("Suba seu currículo atual (PDF)", type="pdf")
    job_description = st.text_area("Descrição da vaga alvo:", height=200)
    # Botão centralizado e controlado
    btn_gerar = st.button("Gerar Currículo e Análise", use_container_width=True)

if "content" not in st.session_state:
    st.session_state.content = ""

# LÓGICA DE GERAÇÃO
if btn_gerar:
    if uploaded_file and job_description.strip():
        with st.spinner("Processando..."):
            try:
                reader = PdfReader(uploaded_file)
                cv_text = "".join([p.extract_text() for p in reader.pages if p.extract_text()])
                lang = detect_language(job_description)
                target_lang = "PORTUGUÊS" if lang == "pt-BR" else "ENGLISH"

                prompt = f"""
                Gere um currículo e uma análise em {target_lang}.
                FONTE OBRIGATÓRIA: Roboto.
                ESTRUTURA IGUAL À IMAGEM 2:
                1. No [CV_START]:
                   - Cabeçalho centralizado.
                   - Experiências usando <table> (Empresa/Data na linha 1, Cargo/Local na linha 2).
                   - Descrição em bloco corrido com "/".
                2. No [ANALYSIS_START]: análise completa.
                DADOS: {cv_text}
                VAGA: {job_description}
                """
                response = client.models.generate_content(model="gemini-2.0-flash", contents=prompt)
                st.session_state.content = response.text
            except Exception as e:
                st.error(f"Erro: {e}")

# 4) EXIBIÇÃO DOS RESULTADOS
if st.session_state.content:
    cv_match = re.search(r"\[CV_START\](.*?)\[CV_END\]", st.session_state.content, re.DOTALL)
    analysis_match = re.search(r"\[ANALYSIS_START\](.*?)\[ANALYSIS_END\]", st.session_state.content, re.DOTALL)
    
    if cv_match:
        st.divider()
        clean_html = cv_match.group(1).replace("```html", "").replace("```", "").strip()
        full_doc = f"<html><head><meta charset='UTF-8'>{CV_CSS}</head><body><div class='cv-paper'>{clean_html}</div></body></html>"
        
        components.html(full_doc, height=1000, scrolling=True)

        _, btn_exp_col, _ = st.columns([1, 2, 1])
        with btn_exp_col:
            st.download_button(
                label="📥 Baixar Currículo em Roboto (.doc)",
                data=full_doc,
                file_name="Curriculo_Roboto.doc",
                mime="application/msword",
                use_container_width=True
            )

    if analysis_match:
        _, a_col, _ = st.columns([1, 2, 1])
        with a_col:
            st.divider()
            st.subheader("📊 Preparação para Entrevista")
            st.markdown(analysis_match.group(1).strip())
