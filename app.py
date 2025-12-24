import streamlit as st
import google.generativeai as genai
from PyPDF2 import PdfReader

# 1. Configuração Inicial (Sempre no topo)
st.set_page_config(page_title="Portal de Carreira IA", layout="wide")

# 2. Configuração da API
if "GOOGLE_API_KEY" in st.secrets:
    # Usamos o transport='rest' para evitar erros de rede
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"], transport='rest')
else:
    st.error("Erro: A etiqueta 'GOOGLE_API_KEY' não foi encontrada.")

# 3. Definição do Modelo (Ajustado para evitar o erro 404)
# O nome 'gemini-1.5-flash' é o padrão estável. 
# Se ele falhar, o código tentará o 'gemini-1.5-pro'
try:
    model = genai.GenerativeModel(model_name='gemini-1.5-flash')
except:
    model = genai.GenerativeModel(model_name='gemini-1.5-pro')

# --- Restante da Interface ---
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
                try:
                    reader = PdfReader(uploaded_file)
                    cv_text = "".join([page.extract_text() for page in reader.pages])
                    
                    # Chamada simplificada para testar estabilidade
                    response = model.generate_content(
                        f"Otimize este currículo para esta vaga. CV: {cv_text} Vaga: {job_description}"
                    )
                    
                    st.markdown(response.text)
                except Exception as e:
                    st.error(f"Erro na geração: {e}")
        else:
            st.warning("Suba o PDF e cole a vaga.")
