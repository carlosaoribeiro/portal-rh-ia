import streamlit as st
import google.generativeai as genai
from PyPDF2 import PdfReader

st.set_page_config(page_title="Portal de Carreira IA", layout="wide")

# Configuração com transport 'rest' para evitar erros de conexão gRPC
if "GOOGLE_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"], transport='rest')
else:
    st.error("Chave API não configurada nos Secrets.")

# Criando o modelo - usando o nome estável
model = genai.GenerativeModel('gemini-1.5-flash')

st.title("🚀 Portal de Carreira: Gerador de CV Inteligente")

uploaded_file = st.file_uploader("Suba seu CV (PDF)", type="pdf")
job_description = st.text_area("Descrição da vaga:")

if st.button("Gerar CV"):
    if uploaded_file and job_description:
        with st.spinner('Processando...'):
            try:
                reader = PdfReader(uploaded_file)
                cv_text = "".join([page.extract_text() for page in reader.pages])
                
                # Chamada direta
                response = model.generate_content(
                    f"Otimize este CV: {cv_text} para esta vaga: {job_description}"
                )
                st.markdown(response.text)
                
            except Exception as e:
                # Se ainda der 404, o erro aparecerá aqui detalhado
                st.error(f"Erro detalhado: {e}")
