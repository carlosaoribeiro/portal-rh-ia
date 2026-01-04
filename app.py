import re
import streamlit as st
from google import genai
from pypdf import PdfReader
import streamlit.components.v1 as components

# 1) CONFIGURAÇÃO DA PÁGINA
st.set_page_config(page_title="Gerador de CV Inteligente", layout="wide", page_icon="🚀")

# 2) CONEXÃO API
if "GOOGLE_API_KEY" not in st.secrets:
    st.error("Erro: Configure a chave 'GOOGLE_API_KEY' nos Secrets!")
    st.stop()

client = genai.Client(api_key=st.secrets["GOOGLE_API_KEY"])

# ---------- CSS DO MODELO JNG ----------
# Definimos o CSS separadamente para injetar no componente de visualização
CV_CSS = """
<style>
    body { background-color: #f0f2f6; padding: 20px; font-family: 'Times New Roman', serif; }
    .cv-paper {
        background-color: white;
        padding: 40px 50px;
        border: 1px solid #ddd;
        box-shadow: 5px 5px 15px rgba(0,0,0,0.1);
        color: #000;
        max-width: 900px;
        margin: auto;
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
    h1 { text-align: left; margin-bottom: 5px; font-size: 28px; }
    .contact-line { text-align: left; margin-bottom: 20px; font-size: 0.9em; }
</style>
"""

# ---------- Helpers ----------
def detect_language(text):
    text = (text or "").lower()
    pt_hits = len(re.findall(r"\b(de|da|o|a|com|vaga|requisitos|experiência)\b", text))
    en_hits = len(re.findall(r"\b(the|and|with|role|requirements|experience)\b", text))
    return "pt-BR" if pt_hits > en_hits else "en"

# 3) INTERFACE
st.title("🚀 Gerador de CV Inteligente")
st.caption("Ajuste seu currículo para o formato profissional **SheetsResume/JNG**.")

# Inputs
st.subheader("📁 Dados de Entrada")
uploaded_file = st.file_uploader("Suba seu currículo atual (PDF)", type="pdf")
job_description = st.text_area("Descrição da vaga alvo:", height=200)

# Estado do resultado
if "result" not in st.session_state:
    st.session_state.result = ""

# Botão de Ação
if st.button("Gerar CV no Formato Referência", use_container_width=True):
    if uploaded_file and job_description.strip():
        # LIMPEZA: Reseta o resultado antes da nova geração
        st.session_state.result = ""
        
        with st.spinner("Gerando currículo..."):
            try:
                reader = PdfReader(uploaded_file)
                cv_text = "".join([page.extract_text() for page in reader.pages if page.extract_text()])
                lang = detect_language(job_description)

                prompt = f"""
                You are a senior recruiter. Output a resume in RAW HTML format. 
                DO NOT use ```html blocks.
                
                LAYOUT RULES:
                - Use <div class="timeline-row"><span>Company</span><span>Date</span></div>
                - Use <div class="timeline-subrow"><span>Title</span><span>Location</span></div>
                - Section headers: <div class="section-title">TITLE</div>
                - Header: <h1><b>Name</b></h1>
                - Contacts: <p class="contact-line">email ⬩ phone ⬩ location ⬩ links</p>
                - NO SUMMARY SECTION.
                
                Language: {lang}.
                CV: {cv_text}
                Target Job: {job_description}
                """
                
                response = client.models.generate_content(model="gemini-2.0-flash", contents=prompt)
                
                # Limpa qualquer resquício de markdown que a IA possa ter enviado
                st.session_state.result = response.text.replace("```html", "").replace("```", "").strip()
                st.rerun() # Força a atualização da tela para garantir a limpeza
                
            except Exception as e:
                st.error(f"Erro: {e}")

# 4) EXIBIÇÃO DO RESULTADO (Renderização Real de HTML)
if st.session_state.result:
    st.divider()
    st.subheader("✨ Resultado Otimizado")
    
    # Montamos o HTML final injetando o CSS
    full_html = f"<html><head>{CV_CSS}</head><body><div class='cv-paper'>{st.session_state.result}</div></body></html>"
    
    # Renderiza o HTML como um componente real (resolve o problema de ver as tags)
    components.html(full_html, height=1200, scrolling=True)
    
    st.download_button(
        label="📥 Baixar CV Ajustado (HTML)",
        data=full_html,
        file_name="curriculo_jng.html",
        mime="text/html",
        use_container_width=True
    )
