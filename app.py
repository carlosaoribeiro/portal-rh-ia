import streamlit as st
import requests
from google import genai
from io import BytesIO
from docx import Document
from pypdf import PdfReader

st.set_page_config(page_title="Portal RH IA", layout="wide")

# Inicialização Segura e Teste de Conexão
try:
    # Garante que a chave não tenha espaços invisíveis
    api_key = st.secrets["GOOGLE_API_KEY"].strip()
    client = genai.Client(api_key=api_key)
    MODEL_ID = "gemini-1.5-flash"
    
    # Teste rápido: Se falhar aqui, o erro aparece antes de você tentar usar o app
    client.models.generate_content(model=MODEL_ID, contents="teste")
except Exception as e:
    st.error(f"Erro de Autenticação na API Gemini: Verifique se sua chave é válida e se não foi exposta. Detalhe: {e}")
    st.stop()

if "step" not in st.session_state: 
    st.session_state.step = 1

# Funções Principais
def buscar_vagas(cargo, local):
    try:
        url = "https://serpapi.com/search.json"
        params = {
            "engine": "google_jobs",
            "q": f"{cargo} {local}",
            "api_key": st.secrets["SERPAPI_KEY"].strip()
        }
        r = requests.get(url, params=params, timeout=10)
        return r.json().get("jobs_results", [])
    except Exception as e:
        st.error(f"Erro ao buscar vagas: {e}")
        return []

def extrair_texto(file):
    try:
        if file.type == "application/pdf":
            return "".join([p.extract_text() for p in PdfReader(file).pages])
        return "\n".join([p.text for p in Document(file).paragraphs])
    except Exception as e:
        st.error(f"Erro ao ler arquivo: {e}")
        return ""

# Interface
if st.session_state.step == 1:
    st.header("1. Busca de Vagas")
    cargo = st.text_input("Cargo", "Android Developer")
    local = st.text_input("Local", "Remoto")
    
    if st.button("Pesquisar Vagas"):
        with st.spinner("Buscando..."):
            st.session_state.vagas = buscar_vagas(cargo, local)
    
    if "vagas" in st.session_state:
        for i, v in enumerate(st.session_state.vagas):
            with st.container(border=True):
                st.write(f"**{v.get('title')}** - {v.get('company_name')}")
                st.write(f"Local: {v.get('location')}")
                if st.button("Escolher esta", key=f"v_{i}"):
                    st.session_state.vaga = v
                    st.session_state.step = 2
                    st.rerun()

elif st.session_state.step == 2:
    st.header("2. Otimizar Currículo")
    vaga = st.session_state.vaga
    st.info(f"Vaga Selecionada: {vaga.get('title')} em {vaga.get('company_name')}")
    
    file = st.file_uploader("Suba seu currículo (PDF ou DOCX)", type=["pdf", "docx"])
    
    if file:
        if st.button("Gerar Versão ATS"):
            with st.spinner("A IA está trabalhando..."):
                texto_cv = extrair_texto(file)
                if texto_cv:
                    vaga_desc = vaga.get('description', 'Descrição não disponível')
                    prompt = f"Otimize apenas o resumo deste currículo para a vaga abaixo. CV: {texto_cv[:3000]}. Vaga: {vaga_desc[:2000]}"
                    
                    try:
                        res = client.models.generate_content(model=MODEL_ID, contents=prompt)
                        st.subheader("Sugestão de Resumo Otimizado:")
                        st.success("Pronto!")
                        st.write(res.text)
                    except Exception as e:
                        st.error(f"Falha na IA: {e}")
    
    if st.button("Voltar para busca"):
        st.session_state.step = 1
        st.rerun()
