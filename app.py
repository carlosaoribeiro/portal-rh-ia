import streamlit as st
import requests
from google import genai
from io import BytesIO
from docx import Document
from pypdf import PdfReader

st.set_page_config(page_title="Portal RH IA", layout="wide")

# Inicialização Segura
try:
    client = genai.Client(api_key=st.secrets["GOOGLE_API_KEY"])
    MODEL_ID = "gemini-1.5-flash"
except Exception as e:
    st.error(f"Erro nas chaves: {e}")
    st.stop()

if "step" not in st.session_state: st.session_state.step = 1

# Funções Principais
def buscar_vagas(cargo, local):
    url = "https://serpapi.com/search.json"
    params = {
        "engine": "google_jobs",
        "q": f"{cargo} {local}",
        "api_key": st.secrets["SERPAPI_KEY"]
    }
    return requests.get(url, params=params).json().get("jobs_results", [])

def extrair_texto(file):
    if file.type == "application/pdf":
        return "".join([p.extract_text() for p in PdfReader(file).pages])
    return "\n".join([p.text for p in Document(file).paragraphs])

# Interface
if st.session_state.step == 1:
    st.header("1. Busca de Vagas")
    cargo = st.text_input("Cargo", "Developer")
    local = st.text_input("Local", "Remoto")
    if st.button("Pesquisar"):
        st.session_state.vagas = buscar_vagas(cargo, local)
    
    if "vagas" in st.session_state:
        for i, v in enumerate(st.session_state.vagas):
            with st.container(border=True):
                st.write(f"**{v.get('title')}** - {v.get('company_name')}")
                if st.button("Escolher esta", key=f"v_{i}"):
                    st.session_state.vaga = v
                    st.session_state.step = 2
                    st.rerun()

elif st.session_state.step == 2:
    st.header("2. Otimizar CV")
    file = st.file_uploader("Suba seu currículo (PDF ou DOCX)", type=["pdf", "docx"])
    if file and st.button("Gerar Resumo ATS"):
        texto_cv = extrair_texto(file)
        vaga_desc = st.session_state.vaga.get('description', '')
        prompt = f"Otimize o resumo do CV para esta vaga: {vaga_desc}. CV original: {texto_cv[:3000]}"
        
        res = client.models.generate_content(model=MODEL_ID, contents=prompt)
        st.subheader("Sugestão de Resumo:")
        st.write(res.text)
    
    if st.button("Voltar"):
        st.session_state.step = 1
        st.rerun()
