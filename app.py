import streamlit as st
import google.generativeai as genai
from PyPDF2 import PdfReader

st.set_page_config(page_title="Portal de Carreira IA", layout="wide")

if "GOOGLE_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"], transport='rest')
else:
    st.error("Erro: A etiqueta 'GOOGLE_API_KEY' não foi encontrada.")

# Alteração aqui: Usando 'gemini-1.5-flash' sem o sufixo ou testando 'gemini-1.5-pro'
model = genai.GenerativeModel('gemini-1.5-flash')

# 3. Interface do Usuário
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
            with st.spinner('Analisando e otimizando com IA...'):
                try:
                    # Extração de texto do PDF
                    reader = PdfReader(uploaded_file)
                    cv_text = ""
                    for page in reader.pages:
                        cv_text += page.extract_text()
                    
                    # Prompt para a IA
                    prompt = f"""
                    Você é um especialista em recrutamento e seleção (RH). 
                    Abaixo está o meu currículo e a descrição de uma vaga de emprego.
                    
                    CURRÍCULO:
                    {cv_text}
                    
                    VAGA:
                    {job_description}
                    
                    TAREFA: 
                    Reescreva meu currículo de forma otimizada para esta vaga específica. 
                    Destaque minhas experiências que coincidem com os requisitos, use palavras-chave da descrição da vaga 
                    e mantenha um tom profissional.
                    """
                    
                    # Chamada da IA
                    response = model.generate_content(prompt)
                    
                    # Exibição do resultado
                    st.markdown("### Resultado:")
                    st.markdown(response.text)
                    
                except Exception as e:
                    st.error(f"Ocorreu um erro ao processar: {e}")
        else:
            st.warning("Por favor, suba o PDF e cole a descrição da vaga antes de gerar.")
