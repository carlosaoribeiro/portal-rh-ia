import re
import streamlit as st
from google import genai
from pypdf import PdfReader
import streamlit.components.v1 as components
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# 1) CONFIGURAÇÃO DA PÁGINA
st.set_page_config(page_title="Gerador de CV Inteligente", layout="wide", page_icon="🚀")

# CSS ESTILO JNG (Conforme Documento Enviado)
CV_CSS = """
<style>
    body { background-color: #ffffff; font-family: 'Arial', sans-serif; color: #333; }
    .cv-paper { max-width: 800px; margin: auto; padding: 40px; border: 1px solid #eee; }
    h1 { color: #1a73e8; font-size: 24px; margin-bottom: 10px; }
    .section-title { border-bottom: 2px solid #1a73e8; font-weight: bold; margin-top: 20px; padding-bottom: 5px; color: #1a73e8; text-transform: uppercase; }
    .timeline-row { display: flex; justify-content: space-between; font-weight: bold; margin-top: 10px; }
    .contact-line { font-size: 0.9em; color: #666; margin-bottom: 20px; }
    ul { padding-left: 20px; }
</style>
"""

# 2) CONFIGURAÇÃO OAUTH GOOGLE
# Nota: Você deve baixar o 'client_secrets.json' do Google Cloud Console
CLIENT_SECRETS_FILE = "client_secrets.json"
SCOPES = ['https://www.googleapis.com/auth/documents', 'https://www.googleapis.com/auth/drive.file']

def get_google_auth_flow():
    return Flow.from_client_secrets_file(
        CLIENT_SECRETS_FILE,
        scopes=SCOPES,
        redirect_uri="http://localhost:8501" # Ajuste para sua URL de produção
    )

# 3) CONEXÃO API GEMINI
client = genai.Client(api_key=st.secrets["GOOGLE_API_KEY"])

# ---------- Helpers ----------
def detect_language(text):
    text = (text or "").lower()
    pt_hits = len(re.findall(r"\b(vaga|requisitos|experiência|vagas|blog)\b", text))
    return "pt-BR" if pt_hits > 2 else "en"

def create_google_doc(token, cv_content):
    try:
        from google.oauth2.credentials import Credentials
        creds = Credentials(token=token)
        service = build('docs', 'v1', credentials=creds)
        
        # Cria documento vazio
        doc = service.documents().create(body={'title': 'Meu Novo CV - JNG'}).execute()
        doc_id = doc.get('documentId')
        
        # Insere o conteúdo (Texto Simples para o Docs)
        requests = [{'insertText': {'location': {'index': 1}, 'text': cv_content}}]
        service.documents().batchUpdate(documentId=doc_id, body={'requests': requests}).execute()
        
        return f"https://docs.google.com/document/d/{doc_id}/edit"
    except HttpError as err:
        return f"Erro: {err}"

# 4) INTERFACE PRINCIPAL
st.title("🚀 Gerador de CV Inteligente")
st.caption("Baseado no padrão **#jobnagringa** [cite: 2, 7]")

uploaded_file = st.file_uploader("Suba seu currículo atual (PDF)", type="pdf")
job_description = st.text_area("Descrição da vaga alvo:", height=150)

if "full_content" not in st.session_state:
    st.session_state.full_content = ""
if "auth_token" not in st.session_state:
    st.session_state.auth_token = None

# Fluxo de Geração
if st.button("Gerar CV e Análise", use_container_width=True):
    if uploaded_file and job_description:
        with st.spinner("Analisando e formatando..."):
            reader = PdfReader(uploaded_file)
            cv_text = "".join([p.extract_text() for p in reader.pages])
            lang = detect_language(job_description)
            
            prompt = f"""
            Task: Generate a JNG Resume [cite: 8] and Interview Analysis[cite: 26].
            Language: {lang}.
            Format: [CV_START] (HTML CV) [CV_END] [ANALYSIS_START] (Markdown Analysis) [ANALYSIS_END]
            
            Include:
            - ATS Friendly format [cite: 10]
            - Professional Summary [cite: 13, 30]
            - Work Experience with metrics [cite: 15, 58]
            - Skills and keywords for ATS [cite: 31]
            - Interview prep sections: "O que está melhor", "O que melhorar", "Perguntas de entrevista" 
            
            CV Data: {cv_text}
            Job: {job_description}
            """
            response = client.models.generate_content(model="gemini-2.0-flash", contents=prompt)
            st.session_state.full_content = response.text
            st.rerun()

# 5) EXIBIÇÃO E BOTÃO GOOGLE DOCS
if st.session_state.full_content:
    cv_match = re.search(r"\[CV_START\](.*?)\[CV_END\]", st.session_state.full_content, re.DOTALL)
    analysis_match = re.search(r"\[ANALYSIS_START\](.*?)\[ANALYSIS_END\]", st.session_state.full_content, re.DOTALL)
    
    if cv_match:
        st.subheader("📄 Currículo Otimizado")
        display_html = f"<html><head>{CV_CSS}</head><body><div class='cv-paper'>{cv_match.group(1)}</div></body></html>"
        components.html(display_html, height=600, scrolling=True)

        # CENÁRIO GOOGLE DOCS
        if not st.session_state.auth_token:
            if st.button("🔗 Login no Google para Editar Documento", use_container_width=True):
                flow = get_google_auth_flow()
                auth_url, _ = flow.authorization_url(prompt='consent')
                st.markdown(f"**[Clique aqui para autorizar o acesso ao seu Google Drive]({auth_url})**")
                # Em produção, o redirecionamento capturaria o código via URL params
        else:
            if st.button("📝 Enviar para o Google Docs", use_container_width=True):
                doc_url = create_google_doc(st.session_state.auth_token, cv_match.group(1))
                st.success(f"Documento criado! [Clique aqui para abrir]({doc_url})")

    if analysis_match:
        st.divider()
        st.subheader("💡 Preparação para Entrevista [cite: 26]")
        st.markdown(analysis_match.group(1))

st.caption("Não é permitida a reprodução sem autorização prévia do #jobnagringa [cite: 84]")
