import re
import streamlit as st
from google import genai
from pypdf import PdfReader
import streamlit.components.v1 as components

# 1) CONFIGURAÇÃO DA PÁGINA
st.set_page_config(page_title="Gerador de Currículo", layout="wide", page_icon="🚀")

# CSS COM ALINHAMENTO CENTRALIZADO
CV_CSS = """
<style>
    body { 
        background-color: #f4f4f4; 
        display: flex; 
        justify-content: center; 
        padding: 40px 0;
        font-family: 'Arial', sans-serif;
    }
    .cv-paper { 
        background-color: #ffffff;
        width: 850px; 
        padding: 50px;
        box-shadow: 0 0 15px rgba(0,0,0,0.1);
        color: #000;
        line-height: 1.4;
        text-align: left; /* Conteúdo interno à esquerda, mas a folha centralizada */
    }
    h1 { font-size: 26px; margin-bottom: 5px; font-weight: bold; text-align: center; }
    .contact-line { font-size: 0.95em; margin-bottom: 20px; border-bottom: 1px solid #eee; padding-bottom: 10px; text-align: center; }
    .section-title { border-bottom: 1.5px solid #000; text-transform: uppercase; font-weight: bold; margin-top: 25px; margin-bottom: 10px; font-size: 1.1em; }
    .timeline-row { display: flex; justify-content: space-between; font-weight: bold; font-size: 1.1em; margin-top: 15px; }
    .timeline-subrow { display: flex; justify-content: space-between; font-style: italic; margin-bottom: 8px; font-size: 1em; color: #333; }
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

# Layout de colunas centralizado
_, center_col, _ = st.columns([1, 2, 1])

with center_col:
    uploaded_file = st.file_uploader("Suba seu currículo atual (PDF)", type="pdf")
    job_description = st.text_area("Descrição da vaga alvo:", height=200)

if "content" not in st.session_state:
    st.session_state.content = ""

if st.button("Gerar Currículo e Análise", use_container_width=True):
    if uploaded_file and job_description.strip():
        st.session_state.content = ""
        with st.spinner("Processando..."):
            try:
                reader = PdfReader(uploaded_file)
                cv_text = "".join([p.extract_text() for p in reader.pages if p.extract_text()])
                lang = detect_language(job_description)
                target_lang = "PORTUGUÊS" if lang == "pt-BR" else "ENGLISH"

                prompt = f"""
                Gere um currículo e uma análise em {target_lang}.
                REGRAS:
                1. Use [CV_START] e [CV_END] para o HTML.
                2. Use [ANALYSIS_START] e [ANALYSIS_END] para a análise.
                3. No HTML:
                   - Empresa e data na mesma linha (<div class="timeline-row">). [cite: 16]
                   - Cargo e localização abaixo (<div class="timeline-subrow">). [cite: 16]
                   - Descrição como texto corrido, separando itens por "/", sem listas de bolinhas. [cite: 19]
                4. Na análise: inclua seções "O que está melhor", "O que melhorar" e "Perguntas de entrevista". [cite: 26, 27, 32, 62]
                
                DADOS: {cv_text}
                VAGA: {job_description}
                """
                response = client.models.generate_content(model="gemini-2.0-flash", contents=prompt)
                st.session_state.content = response.text
                st.rerun()
            except Exception as e:
                st.error(f"Erro: {e}")

# 4) EXIBIÇÃO CENTRALIZADA
if st.session_state.content:
    cv_match = re.search(r"\[CV_START\](.*?)\[CV_END\]", st.session_state.content, re.DOTALL)
    analysis_match = re.search(r"\[ANALYSIS_START\](.*?)\[ANALYSIS_END\]", st.session_state.content, re.DOTALL)
    
    if cv_match:
        st.divider()
        clean_html = cv_match.group(1).replace("```html", "").replace("```", "").strip()
        full_display = f"<html><head>{CV_CSS}</head><body><div class='cv-paper'>{clean_html}</div></body></html>"
        components.html(full_display, height=1000, scrolling=True)

        if st.button("📝 Exportar para Google Docs", use_container_width=True):
            st.info("Esta funcionalidade exportará o conteúdo para o seu Drive assim que as credenciais forem configuradas. ")

    if analysis_match:
        _, a_col, _ = st.columns([1, 2, 1])
        with a_col:
            st.divider()
            st.subheader("📊 Preparação para Entrevista")
            st.markdown(analysis_match.group(1).strip())
