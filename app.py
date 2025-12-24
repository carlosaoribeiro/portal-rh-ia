import streamlit as st
import google.generativeai as genai
from PyPDF2 import PdfReader

st.set_page_config(page_title="Portal de Carreira IA", layout="wide")

# Conexão simples
if "GOOGLE_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
else:
    st.error("Configure a chave nos Secrets!")
    st.stop()

# Usando o modelo Pro que é o mais aceito em todas as regiões
model = genai.GenerativeModel('gemini-1.0-pro')

st.title("🚀 Gerador de CV Inteligente")

uploaded_file = st.file_uploader("Suba seu CV em PDF", type="pdf")
job_description = st.text_area("Descrição da vaga:")

if st.button("Gerar"):
    if uploaded_file and job_description:
        with st.spinner('Processando...'):
            try:
                reader = PdfReader(uploaded_file)
                cv_text = "".join([p.extract_text() for p in reader.pages])
                
                # Chamada direta
                response = model.generate_content(f"Otimize este CV: {cv_text} para esta vaga: {job_description}")
                st.markdown(response.text)
            except Exception as e:
                st.error(f"Erro: {e}")
