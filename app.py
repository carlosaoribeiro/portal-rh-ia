import streamlit as st
import requests
import google.generativeai as palmlib  # Usando a lib estável
from io import BytesIO
from docx import Document
from pypdf import PdfReader

st.set_page_config(page_title="Portal RH IA", layout="wide")

# Configuração da API Estável
try:
    api_key = st.secrets["GOOGLE_API_KEY"].strip().replace('"', '')
    palmlib.configure(api_key=api_key)
    
    # Tenta o flash, se não existir na sua região/chave, ele avisa
    model = palmlib.GenerativeModel('gemini-1.5-flash')
except Exception as e:
    st.error(f"Erro ao configurar API: {e}")
    st.stop()

if "step" not in st.session_state:
    st.session_state.step = 1

# Funções de Suporte
def buscar_vagas(cargo, local):
    try:
        url = "https://serpapi.com/search.json"
        params = {
            "engine": "google_jobs",
            "q": f"{cargo} {local}",
            "api_key": st.secrets["SERPAPI_KEY"].strip().replace('"', '')
        }
        r = requests.get(url, params=params, timeout=10)
        return r.json().get("jobs_results", [])
    except:
        return []

def extrair_texto(file):
    try:
        if file.type == "application/pdf":
            return "".join([p.extract_text() for p in PdfReader(file).pages])
        return "\n".join([p.text for p in Document(file).paragraphs])
    except:
        return ""

# --- INTERFACE ---
if st.session_state.step == 1:
    st.header("1. Buscar Vagas")
    c1, c2 = st.columns(2)
    cargo = c1.text_input("Cargo:", "Android Developer")
    local = c2.text_input("Local:", "Remoto")
    
    if st.button("Buscar"):
        st.session_state.vagas = buscar_vagas(cargo, local)
    
    if "vagas" in st.session_state:
        for i, v in enumerate(st.session_state.vagas):
            with st.container(border=True):
                st.write(f"**{v.get('title')}** - {v.get('company_name')}")
                if st.button("Selecionar", key=f"v_{i}"):
                    st.session_state.vaga_ativa = v
                    st.session_state.step = 2
                    st.rerun()

elif st.session_state.step == 2:
    vaga = st.session_state.vaga_ativa
    st.header("2. Otimizar CV")
    st.write(f"Vaga: {vaga.get('title')}")
    
    upload = st.file_uploader("Suba seu CV", type=["pdf", "docx"])
    
    if upload and st.button("GERAR RESUMO"):
        with st.spinner("IA processando..."):
            texto_cv = extrair_texto(upload)
            prompt = f"Otimize o resumo deste CV para esta vaga. CV: {texto_cv[:2500]} Vaga: {vaga.get('description', '')[:1500]}"
            
            try:
                # Método de geração da lib estável
                response = model.generate_content(prompt)
                st.subheader("Resultado:")
                st.write(response.text)
            except Exception as e:
                st.error(f"Erro na IA: {e}")
    
    if st.button("Voltar"):
        st.session_state.step = 1
        st.rerun()
