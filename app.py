import streamlit as st
import google.generativeai as genai
from PyPDF2 import PdfReader

# CONFIGURAÇÃO CORRETA: O código busca o NOME da etiqueta, não o valor da chave
if "GOOGLE_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
else:
    st.error("Erro: A etiqueta 'GOOGLE_API_KEY' não foi encontrada nos Secrets do Streamlit.")
    
model = genai.GenerativeModel('gemini-1.5-flash-latest')

st.set_page_config(page_title="Portal de Carreira IA", layout="wide")
st.title("🚀 Portal de Carreira: Gerador de CV Inteligente")

col1, col2 = st.columns(2)

with col1:
    st.subheader("📁 1. Seu Currículo Mestre")
    uploaded_file = st.file_uploader("Suba seu CV original em PDF", type="pdf")
    job_description = st.text_area("Cole aqui a descrição da vaga alvo:", height=300)

with col2:
    st.subheader("✨ 3. Currículo Otimizado")
    if st.button("Gerar CV para esta Vaga"):
        if uploaded_file and job_description:
            with st.spinner('Analisando...'):
                reader = PdfReader(uploaded_file)
                cv_text = "".join([page.extract_text() for page in reader.pages])
                prompt = f"Otimize este CV: {cv_text} para esta vaga: {job_description}"
                response = model.generate_content(prompt)
                st.markdown(response.text)
        else:
            st.warning("Suba o PDF e cole a vaga.")
