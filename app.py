import streamlit as st
import google.generativeai as genai
from PyPDF2 import PdfReader

# 1. Configuração da Página
st.set_page_config(page_title="Portal de Carreira IA", layout="wide")

# 2. Configuração da API (Forçando o protocolo estável)
if "GOOGLE_API_KEY" in st.secrets:
    # O transport='rest' é vital para rodar no Streamlit Cloud
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"], transport='rest')
else:
    st.error("Erro: A chave GOOGLE_API_KEY não foi encontrada nos Secrets.")
    st.stop()

# 3. Inicialização do Modelo (Usando o nome estável mais recente)
# Se o 1.5-flash falhar, ele tentará o 1.5-pro automaticamente
try:
    model = genai.GenerativeModel('gemini-1.5-flash')
except:
    model = genai.GenerativeModel('gemini-1.5-pro')

st.title("🚀 Portal de Carreira: Gerador de CV Inteligente")

col1, col2 = st.columns(2)

with col1:
    st.subheader("📁 1. Seu Currículo Mestre")
    uploaded_file = st.file_uploader("Suba seu CV em PDF", type="pdf")
    job_description = st.text_area("Descrição da vaga alvo:", height=250)

with col2:
    st.subheader("✨ 3. Currículo Otimizado")
    if st.button("Gerar Currículo Otimizado"):
        if uploaded_file and job_description:
            with st.spinner('A IA está analisando seu currículo...'):
                try:
                    # Extraindo texto do PDF
                    reader = PdfReader(uploaded_file)
                    cv_text = ""
                    for page in reader.pages:
                        text = page.extract_text()
                        if text:
                            cv_text += text
                    
                    # Prompt estruturado
                    prompt = f"Atue como um especialista em RH. Otimize meu currículo para esta vaga.\n\nCURRÍCULO:\n{cv_text}\n\nVAGA:\n{job_description}"
                    
                    # Chamada da API
                    response = model.generate_content(prompt)
                    
                    if response.text:
                        st.markdown(response.text)
                    else:
                        st.error("A IA não retornou texto. Tente novamente.")
                        
                except Exception as e:
                    # Exibe o erro de forma clara para sabermos o que é
                    st.error(f"Erro detalhado: {e}")
        else:
            st.warning("Por favor, preencha todos os campos (PDF e Descrição).")
