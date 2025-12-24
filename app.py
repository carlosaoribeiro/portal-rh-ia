import streamlit as st
import google.generativeai as genai
from PyPDF2 import PdfReader

# 1. Configuração da Página
st.set_page_config(page_title="Portal de Carreira IA", layout="wide")

# 2. Configuração da API
if "GOOGLE_API_KEY" in st.secrets:
    # transport='rest' evita erros de rede/gRPC
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"], transport='rest')
else:
    st.error("Erro: A chave GOOGLE_API_KEY não foi encontrada nos Secrets.")
    st.stop()

# 3. Inicialização do Modelo
# Usar 'gemini-1.5-flash-latest' ajuda a evitar o erro 404 da versão v1beta
model = genai.GenerativeModel('gemini-1.5-flash-latest')

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
                    
                    if not cv_text.strip():
                        st.error("Não conseguimos ler o texto do PDF. O arquivo pode estar protegido ou vazio.")
                        st.stop()
                    
                    # Prompt estruturado
                    prompt = f"Atue como um especialista em RH. Otimize meu currículo para esta vaga.\n\nCURRÍCULO:\n{cv_text}\n\nVAGA:\n{job_description}"
                    
                    # Chamada da API - Aqui é onde o erro 404 acontecia
                    response = model.generate_content(prompt)
                    
                    # Exibição do resultado
                    if response.text:
                        st.markdown(response.text)
                    else:
                        st.error("A IA não retornou texto. Verifique se o conteúdo infringe as políticas de segurança.")
                        
                except Exception as e:
                    # Caso o 1.5-flash-latest ainda dê erro, tentamos o 1.0-pro como última alternativa
                    st.info("Tentando rota alternativa de conexão...")
                    try:
                        fallback_model = genai.GenerativeModel('gemini-1.0-pro')
                        response = fallback_model.generate_content(prompt)
                        st.markdown(response.text)
                    except Exception as fatal_e:
                        st.error(f"Erro ao processar com todos os modelos: {fatal_e}")
        else:
            st.warning("Por favor, preencha todos os campos (PDF e Descrição).")
