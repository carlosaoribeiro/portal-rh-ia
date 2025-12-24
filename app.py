import streamlit as st
import google.generativeai as genai
from PyPDF2 import PdfReader

# 1. Configuração da Página
st.set_page_config(page_title="Portal de Carreira IA", layout="wide")

# 2. Conexão com a API (Usando a chave dos Secrets)
if "GOOGLE_API_KEY" in st.secrets:
    # O segredo está aqui: transport='rest' ajuda na estabilidade
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"], transport='rest')
else:
    st.error("Erro: Configure a GOOGLE_API_KEY nos Secrets do Streamlit.")
    st.stop()

# 3. Definição do Modelo usando a Rota Estável (v1)
# Em vez de apenas nomear, vamos garantir a configuração
generation_config = {
  "temperature": 0.7,
  "top_p": 0.95,
  "top_k": 64,
  "max_output_tokens": 8192,
}

# Tentaremos o 1.5-flash com a configuração de versão estável
model = genai.GenerativeModel(
    model_name="gemini-1.5-flash",
    generation_config=generation_config,
)

st.title("🚀 Portal de Carreira: Gerador de CV Inteligente")

# --- Interface ---
uploaded_file = st.file_uploader("Suba seu CV em PDF", type="pdf")
job_description = st.text_area("Descrição da vaga alvo:", height=250)

if st.button("Gerar Currículo Otimizado"):
    if uploaded_file and job_description:
        with st.spinner('Analisando...'):
            try:
                # Extração do PDF
                reader = PdfReader(uploaded_file)
                cv_text = "".join([p.extract_text() for p in reader.pages])
                
                prompt = f"Otimize este currículo para esta vaga:\n\nCV:\n{cv_text}\n\nVAGA:\n{job_description}"
                
                # Chamada de conteúdo
                # Se o erro 404 persistir aqui, é porque a biblioteca precisa de um "reboot" no servidor
                response = model.generate_content(prompt)
                
                st.subheader("✨ Prévia do seu novo currículo:")
                st.markdown(response.text)
                
                st.download_button("📥 Baixar como Texto", response.text, "cv_otimizado.txt")
                
            except Exception as e:
                st.error(f"Erro ao processar: {e}")
                st.info("Dica: Se o erro for 404, tente limpar o cache do Streamlit Cloud em 'Advanced Settings'.")
    else:
        st.warning("Preencha o PDF e a descrição da vaga.")
