import re
import streamlit as st
from google import genai
from pypdf import PdfReader

# 1) CONFIGURAÇÃO DA PÁGINA
st.set_page_config(page_title="Gerador de CV Inteligente", layout="wide", page_icon="🚀")

# CSS para simular o layout SheetsResume/JNG e organizar a visualização vertical
st.markdown("""
    <style>
    .cv-paper {
        background-color: white;
        padding: 40px 50px;
        border-radius: 2px;
        border: 1px solid #ddd;
        box-shadow: 5px 5px 15px rgba(0,0,0,0.1);
        color: #000;
        font-family: 'Times New Roman', serif;
        width: 100%;
        margin-top: 20px;
        line-height: 1.4;
    }
    .timeline-row {
        display: flex;
        justify-content: space-between;
        align-items: baseline;
        font-weight: bold;
        margin-top: 12px;
        font-size: 1.1em;
    }
    .timeline-subrow {
        display: flex;
        justify-content: space-between;
        align-items: baseline;
        font-style: italic;
        margin-bottom: 5px;
    }
    .section-title {
        border-bottom: 1.5px solid #000;
        text-transform: uppercase;
        font-weight: bold;
        margin-top: 20px;
        margin-bottom: 5px;
        font-size: 1em;
    }
    ul { margin-top: 5px; padding-left: 20px; }
    li { margin-bottom: 3px; }
    </style>
    """, unsafe_allow_html=True)

# 2) CONEXÃO API
if "GOOGLE_API_KEY" not in st.secrets:
    st.error("Configure GOOGLE_API_KEY nos Secrets!")
    st.stop()

client = genai.Client(api_key=st.secrets["GOOGLE_API_KEY"])

# ---------- Helpers ----------
def detect_language(text):
    text = (text or "").lower()
    pt_hits = len(re.findall(r"\b(de|da|o|a|com|vaga|requisitos|experiência)\b", text))
    en_hits = len(re.findall(r"\b(the|and|with|role|requirements|experience)\b", text))
    return "pt-BR" if pt_hits > en_hits else "en"

# 3) INTERFACE
st.title("🚀 Gerador de CV Inteligente")
st.caption("Ajuste seu currículo para o formato profissional **SheetsResume/JNG**.")

st.subheader("📁 Dados de Entrada")
uploaded_file = st.file_uploader("Suba seu currículo atual (PDF)", type="pdf")
job_description = st.text_area("Descrição da vaga alvo:", height=200, placeholder="Cole os requisitos da vaga aqui...")

# Container para o resultado (permite limpar e sobrescrever)
result_container = st.empty()

if "result" not in st.session_state:
    st.session_state.result = ""

# Botão de Ação
if st.button("Gerar CV no Formato Referência", use_container_width=True):
    if uploaded_file and job_description.strip():
        # Limpa o resultado anterior da tela antes de começar
        st.session_state.result = ""
        result_container.empty()
        
        with st.spinner("Analisando requisitos e formatando..."):
            try:
                reader = PdfReader(uploaded_file)
                cv_text = "".join([page.extract_text() for page in reader.pages if page.extract_text()])
                lang = detect_language(job_description)

                # PROMPT REFINADO: Instrução explícita para evitar blocos de código Markdown
                prompt = f"""
                You are a senior tech recruiter. Output the optimized resume in RAW HTML format.
                IMPORTANT: Do NOT use markdown code blocks like ```html. Start directly with the HTML tags.
                
                STRUCTURAL RULES (SheetsResume/JNG style):
                1. Header: Name in <h1><b>Name</b></h1>. Contact line separated by ' ⬩ '.
                2. NO SUMMARY. Start with 'WORK EXPERIENCE'.
                3. Sections: Use <div class="section-title">TITLE</div>.
                4. Job Headers:
                   <div class="timeline-row"><span>Company</span><span>Dates</span></div>
                   <div class="timeline-subrow"><span>Title</span><span>Location</span></div>
                5. Points: Use <ul> and <li>.
                
                Language: {lang}.
                Original CV: {cv_text}
                Job: {job_description}
                """
                
                response = client.models.generate_content(model="gemini-2.0-flash", contents=prompt)
                
                # Limpeza final de qualquer tag indesejada que a IA possa ter enviado
                clean_html = response.text.replace("```html", "").replace("```", "").strip()
                st.session_state.result = clean_html
                
            except Exception as e:
                st.error(f"Erro: {e}")
    else:
        st.warning("Preencha os campos.")

# 4) EXIBIÇÃO DO RESULTADO
if st.session_state.result:
    with result_container.container():
        st.divider()
        st.subheader("✨ Resultado Otimizado")
        st.markdown(f'<div class="cv-paper">{st.session_state.result}</div>', unsafe_allow_html=True)
        
        st.download_button(
            label="📥 Baixar CV Ajustado (HTML)",
            data=st.session_state.result,
            file_name="cv_otimizado.html",
            mime="text/html",
            use_container_width=True
        )
