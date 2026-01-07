import re
import streamlit as st
from google import genai
from pypdf import PdfReader
import streamlit.components.v1 as components

# --- NOTA PARA O FUTURO: DESCOMENTE AS LINHAS ABAIXO PARA ATIVAR GOOGLE DRIVE ---
# from google_auth_oauthlib.flow import Flow
# from googleapiclient.discovery import build
# from google.oauth2.credentials import Credentials
# ------------------------------------------------------------------------------

# 1) CONFIGURAÇÃO DA PÁGINA
st.set_page_config(page_title="Gerador de CV Inteligente", layout="wide", page_icon="🚀")

# CSS ESTILO JNG (Baseado nos prints enviados)
CV_CSS = """
<style>
    body { background-color: #ffffff; font-family: 'Arial', sans-serif; color: #333; }
    .cv-paper { max-width: 800px; margin: auto; padding: 40px; border: 1px solid #eee; box-shadow: 0 0 10px rgba(0,0,0,0.05); }
    h1 { color: #1a73e8; font-size: 26px; margin-bottom: 5px; }
    .contact-line { font-size: 0.95em; color: #555; margin-bottom: 20px; border-bottom: 1px solid #eee; padding-bottom: 10px; }
    .section-title { border-bottom: 2px solid #1a73e8; font-weight: bold; margin-top: 25px; padding-bottom: 5px; color: #1a73e8; text-transform: uppercase; font-size: 1.1em; }
    .timeline-row { display: flex; justify-content: space-between; font-weight: bold; margin-top: 15px; font-size: 1.1em; }
    .timeline-subrow { display: flex; justify-content: space-between; font-style: italic; color: #444; margin-bottom: 8px; }
    ul { padding-left: 20px; margin-top: 5px; }
    li { margin-bottom: 5px; font-size: 10.5pt; line-height: 1.5; }
</style>
"""

# 2) CONEXÃO API GEMINI
if "GOOGLE_API_KEY" not in st.secrets:
    st.error("Configure GOOGLE_API_KEY nos Secrets!")
    st.stop()
client = genai.Client(api_key=st.secrets["GOOGLE_API_KEY"])

# ---------- Helpers ----------
def detect_language(text):
    text = (text or "").lower()
    pt_hits = len(re.findall(r"\b(vaga|requisitos|experiência|responsabilidades|conhecimento)\b", text))
    return "pt-BR" if pt_hits > 2 else "en"

# 3) INTERFACE PRINCIPAL
st.title("🚀 Gerador de CV Inteligente")
st.caption("Ajuste seu currículo para o formato profissional **SheetsResume/JNG**.")

col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("📁 Dados de Entrada")
    uploaded_file = st.file_uploader("Suba seu currículo atual (PDF)", type="pdf")
    job_description = st.text_area("Descrição da vaga alvo:", height=250, placeholder="Cole os requisitos da vaga aqui...")

# Estado para armazenar a resposta da IA
if "full_response" not in st.session_state:
    st.session_state.full_response = ""

# Botão de Geração
if st.button("Gerar CV no Formato Referência", use_container_width=True):
    if uploaded_file and job_description.strip():
        st.session_state.full_response = "" # Limpa antes de gerar
        with st.spinner("Analisando requisitos e formatando currículo..."):
            try:
                reader = PdfReader(uploaded_file)
                cv_text = "".join([p.extract_text() for p in reader.pages if p.extract_text()])
                lang = detect_language(job_description)
                
                target_lang = "PORTUGUÊS (Brasil)" if lang == "pt-BR" else "ENGLISH (US)"
                
                prompt = f"""
                You are a senior tech recruiter and CV expert. 
                Generate a response in {target_lang} containing two parts:
                1. An optimized ATS-Friendly CV in RAW HTML (no markdown code blocks).
                2. A detailed Career Analysis exactly like the #jobnagringa style.

                LAYOUT RULES FOR CV:
                - Name in <h1>. Contact line with ⬩ separator.
                - Sections: WORK EXPERIENCE, EDUCATION, SKILLS, CERTIFICATIONS.
                - Use <div class="timeline-row"> and <div class="timeline-subrow">.
                - Focus on metrics and keywords from the job: {job_description}.

                ANALYSIS SECTIONS:
                - "O que está melhor neste currículo?"
                - "O que você precisará melhorar manualmente?"
                - "Quais são seus pontos fortes para essa entrevista?"
                - "Quais perguntas podem cair numa entrevista como essa?"

                FORMAT:
                [CV_START]
                (HTML content)
                [CV_END]
                [ANALYSIS_START]
                (Markdown content)
                [ANALYSIS_END]

                CV DATA: {cv_text}
                """
                
                response = client.models.generate_content(model="gemini-2.0-flash", contents=prompt)
                st.session_state.full_response = response.text
                st.rerun()
            except Exception as e:
                st.error(f"Erro na geração: {e}")

# 4) EXIBIÇÃO DO RESULTADO
if st.session_state.full_response:
    res = st.session_state.full_response
    cv_html = re.search(r"\[CV_START\](.*?)\[CV_END\]", res, re.DOTALL)
    analysis_text = re.search(r"\[ANALYSIS_START\](.*?)\[ANALYSIS_END\]", res, re.DOTALL)
    
    if cv_html:
        st.divider()
        st.subheader("✨ Resultado Otimizado")
        clean_html = cv_html.group(1).replace("```html", "").replace("```", "").strip()
        full_display = f"<html><head>{CV_CSS}</head><body><div class='cv-paper'>{clean_html}</div></body></html>"
        
        components.html(full_display, height=800, scrolling=True)

        # --- FUNCIONALIDADE GOOGLE DOCS (COMENTADA PARA USO FUTURO) ---
        # if st.button("📝 Edite no Google Docs", use_container_width=True):
        #     st.info("Para ativar esta função, configure as credenciais do Google Cloud Console.")
        #     # O fluxo futuro seria:
        #     # 1. Verificar autenticação
        #     # 2. Chamar a API googleapiclient para criar o Doc
        #     # 3. Retornar o link st.link_button("Abrir Documento", url)
        # -------------------------------------------------------------
        
        st.download_button(
            label="📥 Baixar CV Ajustado (HTML)",
            data=full_display,
            file_name="cv_jng_otimizado.html",
            mime="text/html",
            use_container_width=True
        )

    if analysis_text:
        st.divider()
        st.subheader("📊 Prepare-se para a Entrevista")
        st.markdown(analysis_text.group(1).strip())

st.caption("Não é permitida a reprodução sem autorização prévia do #jobnagringa")
