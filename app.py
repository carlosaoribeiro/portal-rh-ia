import streamlit as st
import google.generativeai as genai
from PyPDF2 import PdfReader

# 1. Configuração da Página
st.set_page_config(page_title="Portal de Carreira IA", layout="wide")

# 2. Configuração da API
if "GOOGLE_API_KEY" in st.secrets:
    # transport='rest' é essencial para evitar bugs de versão de protocolo
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"], transport='rest')
else:
    st.error("Chave API não configurada nos Secrets!")
    st.stop()

# 3. Inicialização do Modelo (Usando o modelo estável)
model = genai.GenerativeModel('gemini-1.5-flash')

st.title("🚀 Portal de Carreira: Gerador de CV Inteligente")

uploaded_file = st.file_uploader("Suba seu CV em PDF", type="pdf")
job_description = st.text_area("Descrição da vaga alvo:", height=250)

if st.button("Gerar Currículo Otimizado"):
    if uploaded_file and job_description:
        with st.spinner('Aguarde, conectando ao servidor estável do Google...'):
            try:
                # Extração do PDF
                reader = PdfReader(uploaded_file)
                cv_text = "".join([p.extract_text() for p in reader.pages])
                
                prompt = f"Otimize este currículo para esta vaga:\n\nCV:\n{cv_text}\n\nVAGA:\n{job_description}"
                
                # Chamada de conteúdo
                # Se a biblioteca estiver atualizada, ela usará a rota /v1/ automaticamente
                response = model.generate_content(prompt)
                
                st.subheader("✨ Prévia do seu novo currículo:")
                st.markdown(response.text)
                
                st.download_button("📥 Baixar como Texto", response.text, "cv_otimizado.txt")
                
            except Exception as e:
                # Se o erro 404 persistir, vamos mostrar uma mensagem mais clara
                if "404" in str(e):
                    st.error("O servidor ainda está tentando usar a rota antiga (v1beta).")
                    st.info("Por favor, vá em 'Settings' -> 'Advanced' -> 'Clear Cache' no painel do Streamlit Cloud e reinicie o app.")
                else:
                    st.error(f"Erro: {e}")
    else:
        st.warning("Preencha todos os campos.")
