import streamlit as st
import google.generativeai as genai
from PyPDF2 import PdfReader

# 1. CONFIGURAÇÃO DA PÁGINA (Deve ser o primeiro comando)
st.set_page_config(page_title="Portal de Carreira IA", layout="wide", page_icon="🚀")

# 2. CONFIGURAÇÃO DA API
if "GOOGLE_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"], transport='rest')
else:
    st.error("Erro: A chave 'GOOGLE_API_KEY' não foi configurada nos Secrets do Streamlit.")
    st.stop()

# Inicializamos o modelo (Flash para velocidade, com fallback para Pro)
try:
    model = genai.GenerativeModel('gemini-1.5-flash-latest')
except:
    model = genai.GenerativeModel('gemini-1.5-pro')

# 3. INTERFACE
st.title("🚀 Portal de Carreira: Gerador de CV Inteligente")
st.markdown("---")

col1, col2 = st.columns([1, 1.2]) # Coluna da direita levemente maior para a prévia

with col1:
    st.subheader("📁 1. Seus Dados")
    uploaded_file = st.file_uploader("Suba seu currículo atual (PDF)", type="pdf")
    
    st.subheader("🎯 2. Vaga Alvo")
    job_description = st.text_area("Cole aqui a descrição da vaga ou requisitos:", height=300, placeholder="Ex: Requisitos: Experiência com Python, Gestão de Equipes...")

with col2:
    st.subheader("✨ 3. Resultado & Prévia")
    
    # Botão de ação
    if st.button("Gerar Currículo Otimizado", use_container_width=True):
        if uploaded_file and job_description:
            with st.spinner('A IA está analisando e otimizando seu perfil...'):
                try:
                    # Extração do texto do PDF
                    reader = PdfReader(uploaded_file)
                    cv_text = ""
                    for page in reader.pages:
                        text = page.extract_text()
                        if text:
                            cv_text += text
                    
                    if not cv_text.strip():
                        st.error("Não conseguimos ler o texto deste PDF. Tente um arquivo diferente.")
                        st.stop()

                    # Instrução para a IA (Prompt)
                    prompt = f"""
                    Você é um Especialista em Recrutamento e Seleção. 
                    Sua tarefa é reescrever o currículo abaixo para que ele seja mais atraente para a vaga descrita.
                    
                    Destaque as habilidades técnicas e experiências que batem exatamente com o que a vaga pede.
                    Mantenha um tom profissional e use palavras-chave do setor.
                    
                    CURRÍCULO ORIGINAL:
                    {cv_text}
                    
                    DESCRIÇÃO DA VAGA:
                    {job_description}
                    
                    REGRAS:
                    1. Use cabeçalhos claros (Experiência, Resumo, Habilidades).
                    2. Use listas (bullet points) para as atividades.
                    3. Retorne o texto pronto para ser copiado.
                    """

                    # Chamada para o Google Gemini
                    response = model.generate_content(prompt)
                    
                    if response.text:
                        st.success("✅ Currículo gerado com sucesso!")
                        
                        # --- ÁREA DA PRÉVIA ---
                        with st.container(border=True):
                            st.markdown(response.text)
                        
                        # --- BOTÃO DE DOWNLOAD ---
                        st.download_button(
                            label="📥 Baixar Currículo como Texto (.txt)",
                            data=response.text,
                            file_name="meu_curriculo_otimizado.txt",
                            mime="text/plain",
                            use_container_width=True
                        )
                        st.info("💡 Dica: Você pode copiar o texto acima e colar direto no Word para finalizar o layout.")
                    
                except Exception as e:
                    # Caso ocorra o erro 404 de novo, tentamos a última rota de fuga
                    st.warning("Houve uma oscilação na conexão. Tentando rota alternativa...")
                    try:
                        fallback = genai.GenerativeModel('gemini-1.0-pro')
                        response = fallback.generate_content(prompt)
                        st.markdown(response.text)
                    except:
                        st.error(f"Erro persistente: {e}. Verifique se sua chave API está ativa.")
        else:
            st.warning("⚠️ Por favor, suba o PDF e cole a descrição da vaga.")

# Rodapé
st.markdown("---")
st.caption("Desenvolvido com IA para otimização de carreira.")
