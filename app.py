import streamlit as st
import google.generativeai as genai
from PyPDF2 import PdfReader
from google.generativeai.types import RequestOptions

# 1. Configuração inicial
st.set_page_config(page_title="Portal de Carreira IA", layout="wide")

# 2. Conexão com a API (Usando a chave dos Secrets)
if "GOOGLE_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"], transport='rest')
else:
    st.error("Erro: Configure a GOOGLE_API_KEY nos Secrets do Streamlit.")
    st.stop()

# 3. Definição do Modelo
model = genai.GenerativeModel('gemini-1.5-flash')

st.title("🚀 Portal de Carreira: Gerador de CV Inteligente")

# Interface
uploaded_file = st.file_uploader("Suba seu CV em PDF", type="pdf")
job_description = st.text_area("Descrição da vaga alvo:", height=250)

if st.button("Gerar Currículo Otimizado"):
    if uploaded_file and job_description:
        with st.spinner('Analisando...'):
            try:
                # Extração do PDF
                reader = PdfReader(uploaded_file)
                cv_text = "".join([p.extract_text() for p in reader.pages])
                
                # Prompt
                prompt = f"Otimize este currículo para esta vaga:\n\nCV:\n{cv_text}\n\nVAGA:\n{job_description}"
                
                # O SEGREDO: Forçar a api_version='v1' para evitar o erro 404
                response = model.generate_content(
                    prompt, 
                    request_options=RequestOptions(api_version='v1')
                )
                
                st.subheader("✨ Prévia do seu novo currículo:")
                st.markdown(response.text)
                
                st.download_button("📥 Baixar como Texto", response.text, "cv_otimizado.txt")
                
            except Exception as e:
                st.error(f"Erro ao processar: {e}")
    else:
        st.warning("Preencha o PDF e a descrição da vaga.")
