import streamlit as st
import requests
from google import genai
from io import BytesIO
from docx import Document
from pypdf import PdfReader

st.set_page_config(page_title="Portal RH IA", layout="wide")

# Inicialização com correção de rota
try:
    # O SDK google-genai espera a chave sem espaços
    api_key = st.secrets["GOOGLE_API_KEY"].strip()
    client = genai.Client(api_key=api_key)
    
    # MUDANÇA CRUCIAL: Algumas versões do SDK v1beta exigem o nome curto ou específico
    MODEL_ID = "gemini-1.5-flash" 
    
    # Teste de validação
    client.models.generate_content(model=MODEL_ID, contents="ping")
except Exception as e:
    st.error(f"Erro de Conexão: {e}")
    st.stop()

if "step" not in st.session_state: 
    st.session_state.step = 1

# Funções
def buscar_vagas(cargo, local):
    try:
        url = "https://serpapi.com/search.json"
        params = {
            "engine": "google_jobs",
            "q": f"{cargo} {local}",
            "api_key": st.secrets["SERPAPI_KEY"].strip()
        }
        return requests.get(url, params=params).json().get("jobs_results", [])
    except:
        return []

def extrair_texto(file):
    if file.type == "application/pdf":
        return "".join([p.extract_text() for p in PdfReader(file).pages])
    return "\n".join([p.text for p in Document(file).paragraphs])

# Interface
if st.session_state.step == 1:
    st.header("1. Buscar Vagas")
    cargo = st.text_input("Cargo", "Android Developer")
    local = st.text_input("Localização", "Remoto")
    if st.button("Buscar"):
        st.session_state.vagas = buscar_vagas(cargo, local)
    
    if "vagas" in st.session_state:
        for i, v in enumerate(st.session_state.vagas):
            with st.container(border=True):
                st.write(f"**{v.get('title')}** - {v.get('company_name')}")
                if st.button("Selecionar", key=f"v_{i}"):
                    st.session_state.vaga = v
                    st.session_state.step = 2
                    st.rerun()

elif st.session_state.step == 2:
    st.header("2. Otimizar Currículo")
    file = st.file_uploader("Upload CV", type=["pdf", "docx"])
    
    if file and st.button("Gerar Otimização"):
        texto_cv = extrair_texto(file)
        vaga_desc = st.session_state.vaga.get('description', '')
        prompt = f"Otimize o resumo do CV para esta vaga: {vaga_desc}. CV: {texto_cv[:3000]}"
        
        try:
            # Chamada final
            res = client.models.generate_content(model=MODEL_ID, contents=prompt)
            st.write(res.text)
        except Exception as e:
            st.error(f"Erro na IA: {e}")
            
    if st.button("Voltar"):
        st.session_state.step = 1
        st.rerun()
