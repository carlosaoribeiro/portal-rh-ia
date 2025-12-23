import streamlit as st
import google.generativeai as genai
from PyPDF2 import PdfReader

# 1. Configuração de Segurança (Lê a chave que você colocou nos Secrets do Streamlit)
if "GOOGLE_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["AIzaSyCe_He20qNGuvXrBsaDnlhxiRqBbooMQkc"])
else:
    st.error("Erro: A chave GOOGLE_API_KEY não foi encontrada nos Secrets do Streamlit.")

# 2. Configuração do Modelo (Gemini 1.5 Flash - o mesmo do seu AI Studio)
model = genai.GenerativeModel('gemini-1.5-flash')

# 3. Layout do Site
st.set_page_config(page_title="Portal de Carreira IA", layout="wide")

st.title("🚀 Portal de Carreira: Gerador de CV Inteligente")
st.markdown("---")

# --- BARRA LATERAL (Dashboard Simples) ---
with st.sidebar:
    st.header("📊 Dashboard")
    st.info("O Dashboard completo com Google Sheets será configurado no próximo passo.")
    st.write("Status do Sistema: **Online**")

# --- ÁREA DE INPUT ---
col1, col2 = st.columns(2)

with col1:
    st.subheader("📁 1. Seu Currículo Mestre")
    uploaded_file = st.file_uploader("Suba seu CV original em PDF", type="pdf")
    
    st.subheader("📝 2. Detalhes da Vaga")
    job_description = st.text_area("Cole aqui a descrição da vaga alvo:", height=300)

# --- LÓGICA DE PROCESSAMENTO ---
with col2:
    st.subheader("✨ 3. Currículo Otimizado")
    
    if st.button("Gerar CV para esta Vaga"):
        if uploaded_file and job_description:
            with st.spinner('A IA está analisando seu perfil e adaptando para a vaga...'):
                try:
                    # Extração de texto do PDF
                    reader = PdfReader(uploaded_file)
                    cv_text = ""
                    for page in reader.pages:
                        cv_text += page.extract_text()
                    
                    # Prompt Estruturado para a IA
                    prompt = f"""
                    Você é um especialista em RH e ATS (Sistemas de Rastreamento de Candidatos). 
                    Com base no meu Currículo Mestre abaixo, crie uma versão otimizada para a vaga descrita.
                    
                    REGRAS:
                    1. Mantenha a verdade dos fatos, não invente experiências.
                    2. Destaque as palavras-chave encontradas na descrição da vaga.
                    3. Use um tom profissional e direto.
                    4. No final, forneça um 'Score de Compatibilidade' de 0 a 100%.

                    CURRÍCULO MESTRE:
                    {cv_text}

                    DESCRIÇÃO DA VAGA:
                    {job_description}
                    """
                    
                    # Chamada para o Gemini
                    response = model.generate_content(prompt)
                    
                    # Exibição do Resultado
                    st.success("Currículo Gerado com Sucesso!")
                    st.markdown(response.text)
                    
                except Exception as e:
                    st.error(f"Ocorreu um erro no processamento: {e}")
        else:
            st.warning("Atenção: Você precisa subir o PDF e colar a descrição da vaga.")

st.markdown("---")
st.caption("Desenvolvido por Carlos Ribeiro | Powered by Gemini 1.5 Flash")
