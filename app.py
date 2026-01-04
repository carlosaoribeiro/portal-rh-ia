import re
import streamlit as st
from google import genai
from pypdf import PdfReader
import streamlit.components.v1 as components

# 1) CONFIGURAÇÃO DA PÁGINA
st.set_page_config(page_title="Gerador de CV Inteligente", layout="wide", page_icon="🚀")

# CSS DO MODELO JNG (Injetado no componente HTML)
CV_CSS = """
<style>
    body { background-color: #ffffff; margin: 0; padding: 20px; font-family: 'Times New Roman', serif; color: #000; }
    .cv-paper { max-width: 850px; margin: auto; line-height: 1.4; }
    h1 { font-size: 26px; margin-bottom: 5px; text-transform: none; }
    .contact-line { font-size: 0.95em; margin-bottom: 20px; border-bottom: 1px solid #eee; padding-bottom: 10px; }
    .section-title { border-bottom: 1.5px solid #000; text-transform: uppercase; font-weight: bold; margin-top: 25px; margin-bottom: 8px; font-size: 1.05em; }
    .timeline-row { display: flex; justify-content: space-between; font-weight: bold; margin-top: 15px; font-size: 1.1em; }
    .timeline-subrow { display: flex; justify-content: space-between; font-style: italic; margin-bottom: 5px; font-size: 1em; }
    ul { margin-top: 5px; padding-left: 25px; }
    li { margin-bottom: 4px; }
</style>
"""

# 2) CONEXÃO API
if "GOOGLE_API_KEY" not in st.secrets:
    st.error("Configure GOOGLE_API_KEY nos Secrets!")
    st.stop()
client = genai.Client(api_key=st.secrets["GOOGLE_API_KEY"])

# ---------- Helpers ----------
def detect_language(text):
    text = (text or "").lower()
    pt_hits = len(re.findall(r"\b(de|da|o|a|com|vaga|requisitos|experiência)\b", text))
    return "pt-BR" if pt_hits > 3 else "en"

def clean_ai_output(text):
    """Remove blocos de código markdown e espaços extras."""
    text = text.replace("```html", "").replace("```", "").strip()
    return text

# 3) INTERFACE
st.title("🚀 Gerador de CV Inteligente")
st.caption("Formato Profissional **SheetsResume/JNG**")

# Inputs sequenciais
uploaded_file = st.file_uploader("Suba seu currículo (PDF)", type="pdf")
job_description = st.text_area("Descrição da vaga alvo:", height=200, placeholder="Insira a vaga aqui...")

# Gerenciamento de estado
if "cv_result" not in st.session_state:
    st.session_state.cv_result = ""

if st.button("Gerar CV no Formato Referência", use_container_width=True):
    if uploaded_file and job_description.strip():
        # Limpa o estado anterior
        st.session_state.cv_result = ""
        
        with st.spinner("Otimizando conteúdo e traduzindo se necessário..."):
            try:
                reader = PdfReader(uploaded_file)
                cv_text = "".join([p.extract_text() for p in reader.pages if p.extract_text()])
                lang = detect_language(job_description)
                
                # Prompt rigoroso com o idioma
                target_lang_instruction = "TODO O CURRÍCULO DEVE SER EM PORTUGUÊS." if lang == "pt-BR" else "THE ENTIRE RESUME MUST BE IN ENGLISH."
                
                prompt = f"""
                You are a professional resume writer. Return ONLY raw HTML code.
                {target_lang_instruction}
                
                RULES:
                1. No markdown blocks. No text before or after HTML.
                2. Header: <h1><b>Name</b></h1> followed by <div class="contact-line">Contacts with ⬩</div>.
                3. Sections: <div class="section-title">SECTION</div>.
                4. Jobs: <div class="timeline-row"><span>Company</span><span>Dates</span></div>
                          <div class="timeline-subrow"><span>Title</span><span>Location</span></div>
                5. Content: Match technical keywords from the job description.
                
                CV: {cv_text}
                Job Description: {job_description}
                """
                
                response = client.models.generate_content(model="gemini-2.0-flash", contents=prompt)
                st.session_state.cv_result = clean_ai_output(response.text)
                st.rerun() 
            except Exception as e:
                st.error(f"Erro: {e}")

# 4) EXIBIÇÃO DO RESULTADO
if st.session_state.cv_result:
    st.divider()
    st.subheader("✨ Resultado Otimizado")
    
    # Injeção segura no IFrame
    full_display_html = f"<html><head>{CV_CSS}</head><body><div class='cv-paper'>{st.session_state.cv_result}</div></body></html>"
    
    components.html(full_display_html, height=1000, scrolling=True)
    
    st.download_button(
        label="📥 Baixar CV em HTML (Pronto para imprimir)",
        data=full_display_html,
        file_name="curriculo_otimizado.html",
        mime="text/html",
        use_container_width=True
    )
