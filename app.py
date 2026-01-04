import re
import streamlit as st
from google import genai
from pypdf import PdfReader

# 1) CONFIGURAÇÃO DA PÁGINA
st.set_page_config(page_title="Gerador de CV Inteligente", layout="wide", page_icon="🚀")

# CSS para simular o layout SheetsResume/JNG fielmente
st.markdown("""
    <style>
    /* Estilo do Papel A4 */
    .cv-paper {
        background-color: white;
        padding: 40px 50px;
        border-radius: 2px;
        border: 1px solid #ddd;
        box-shadow: 5px 5px 15px rgba(0,0,0,0.1);
        color: #000;
        font-family: 'Times New Roman', serif;
        width: 100%;
        margin: auto;
    }
    /* Timeline: Empresa à esquerda, Data à direita */
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
    /* Seções com borda inferior */
    .section-title {
        border-bottom: 1.5px solid #000;
        text-transform: uppercase;
        font-weight: bold;
        margin-top: 20px;
        margin-bottom: 5px;
        font-size: 1em;
    }
    .contact-line { text-align: center; margin-bottom: 20px; font-size: 0.9em; }
    .bullet-point { margin-left: 20px; text-indent: -20px; margin-bottom: 3px; }
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
    pt_hits = len(re.findall(r"\b(de|da|o|a|com|vaga|requisitos)\b", text))
    en_hits = len(re.findall(r"\b(the|and|with|role|requirements)\b", text))
    return "pt-BR" if pt_hits > en_hits else "en"

# 3) INTERFACE (Layout 2 Colunas conforme print)
st.title("🚀 Gerador de CV Inteligente")
st.caption("Ajuste seu currículo para o formato profissional **SheetsResume/JNG**.")

col1, col2 = st.columns([1, 1.3])

with col1:
    st.subheader("📁 Dados de Entrada")
    uploaded_file = st.file_uploader("Suba seu currículo atual (PDF)", type="pdf")
    job_description = st.text_area("Descrição da vaga alvo:", height=300)

with col2:
    st.subheader("✨ Resultado Otimizado")
    if "result" not in st.session_state: st.session_state.result = ""

    if st.button("Gerar CV no Formato Referência", use_container_width=True):
        if uploaded_file and job_description:
            with st.spinner("Formatando linha do tempo..."):
                reader = PdfReader(uploaded_file)
                cv_text = "".join([p.extract_text() for p in reader.pages])
                lang = detect_language(job_description)

                # PROMPT: Forçando a saída em HTML para manter o alinhamento do print
                prompt = f"""
                You are an expert resume writer for the "SheetsResume/JNG" style.
                Output the resume using HTML tags ONLY for structure.
                
                STRUCTURAL RULES:
                1. Use <div class="timeline-row"><span>Company</span><span>Date</span></div> for all experience headers.
                2. Use <div class="timeline-subrow"><span>Title</span><span>Location</span></div> for titles.
                3. Use <div class="section-title">SECTION NAME</div> for headers.
                4. No Summary. Start with WORK EXPERIENCE.
                5. Bullet points should be concise and tech-heavy (MVVM, Kotlin, etc).
                
                Language: {lang}.
                CV: {cv_text}
                Job: {job_description}
                """
                
                response = client.models.generate_content(model="gemini-2.0-flash", contents=prompt)
                st.session_state.result = response.text

    if st.session_state.result:
        # Exibição dentro do estilo de "Papel" do print
        st.markdown(f'<div class="cv-paper">{st.session_state.result}</div>', unsafe_allow_html=True)
        st.download_button("📥 Baixar CV Ajustado", st.session_state.result, "cv.html", use_container_width=True)
