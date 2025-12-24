import streamlit as st
import google.generativeai as genai
from PyPDF2 import PdfReader

# 1. CONFIGURAÇÃO DA PÁGINA
st.set_page_config(page_title="Portal de Carreira IA", layout="wide", page_icon="🚀")

# 2. CONEXÃO COM A API
# Certifique-se de que o nome nos Secrets seja exatamente GOOGLE_API_KEY
if "GOOGLE_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
else:
    st.error("Erro: A chave 'GOOGLE_API_KEY' não foi encontrada nos Secrets do Streamlit.")
    st.stop()

# 3. DEFINIÇÃO DO MODELO (Versão 1.0 Pro para máxima compatibilidade)
try:
    model = genai.GenerativeModel('gemini-1.0-pro')
except Exception as e:
    st.error(f"Erro ao inicializar o modelo: {e}")
    st.stop()

# 4. INTERFACE DO USUÁRIO
st.title("🚀 Portal de Carreira: Gerador de CV Inteligente")
st.markdown("Otimize seu currículo para qualquer vaga em segundos utilizando Inteligência Artificial.")
st.markdown("---")

col1, col2 = st.columns([1, 1.2])

with col1:
    st.subheader("📁 1. Seus Dados")
    uploaded_file = st.file_uploader("Suba seu currículo atual (PDF)", type="pdf")
    
    st.subheader("🎯 2. Vaga Alvo")
    job_description = st.text_area(
        "Cole aqui a descrição da vaga (requisitos e responsabilidades):", 
        height=300, 
        placeholder="Ex: Procuramos desenvolvedor com experiência em Python e Streamlit..."
    )

with col2:
    st.subheader("✨ 3. Resultado & Prévia")
    
    if st.button("Gerar Currículo Otimizado", use_container_width=True):
        if uploaded_file and job_description:
            with st.spinner('A IA está analisando seu perfil e adaptando para a vaga...'):
                try:
                    # Extração do texto do PDF
                    reader = PdfReader(uploaded_file)
                    cv_text = ""
                    for page in reader.pages:
                        text = page.extract_text()
                        if text:
                            cv_text += text
                    
                    if not cv_text.strip():
                        st.error("Não conseguimos ler o texto deste PDF. Verifique se o arquivo não é apenas uma imagem.")
                        st.stop()

                    # Prompt estruturado para o RH
                    prompt = f"""
                    Atue como um Especialista em RH e Recrutamento Técnico.
                    Otimize o currículo abaixo para que ele seja altamente relevante para a vaga descrita.
                    
                    DIRETRIZES:
                    1. Reorganize as experiências focando no que a vaga pede.
                    2. Use palavras-chave da descrição da vaga.
                    3. Mantenha um tom profissional e direto.
                    4. Formate com títulos claros e listas (bullet points).

                    CURRÍCULO ORIGINAL:
                    {cv_text}
                    
                    DESCRIÇÃO DA VAGA:
                    {job_description}
                    """

                    # Chamada para o Google Gemini
                    response = model.generate_content(prompt)
                    
                    if response.text:
                        st.success("✅ Currículo otimizado com sucesso!")
                        
                        # Container de prévia
                        with st.container(border=True):
                            st.markdown(response.text)
                        
                        # Botão para baixar o resultado
                        st.download_button(
                            label="📥 Baixar Currículo Otimizado (TXT)",
                            data=response.text,
                            file_name="curriculo_otimizado.txt",
                            mime="text/plain",
                            use_container_width=True
                        )
                        st.info("💡 Dica: Copie o texto acima e cole no seu modelo favorito do Word ou Google Docs.")
                    
                except Exception as e:
                    st.error(f"Ocorreu um erro ao processar: {e}")
                    st.info("Dica: Verifique se sua nova chave de API está correta nos Secrets.")
        else:
            st.warning("⚠️ Por favor, faça o upload do PDF e cole a descrição da vaga.")

# RODAPÉ
st.markdown("---")
st.caption("Ferramenta de auxílio profissional. Revise sempre os dados gerados pela IA.")
