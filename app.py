import streamlit as st
import requests
from google import genai
from io import BytesIO
from docx import Document
from pypdf import PdfReader

# ==========================================
# CONFIGURAÇÃO INICIAL
# ==========================================
st.set_page_config(page_title="Portal RH IA", layout="wide")

# Verificação de Chaves
if "GOOGLE_API_KEY" not in st.secrets:
    st.error("Falta GOOGLE_API_KEY no Secrets.")
    st.stop()
if "SERPAPI_KEY" not in st.secrets:
    st.error("Falta SERPAPI_KEY no Secrets.")
    st.stop()

# Inicializa cliente Gemini
try:
    client = genai.Client(api_key=st.secrets["GOOGLE_API_KEY"])
    # O SEGREDO ESTÁ AQUI: Usar exatamente esta string
    MODEL_ID = "gemini-1.5-flash"
    
    # Teste de conexão
    client.models.generate_content(model=MODEL_ID, contents="oi")
except Exception as e:
    st.error(f"Erro Crítico de API: {str(e)}")
    st.stop()

# ==========================================
# ESTADO E FUNÇÕES
# ==========================================
if "step" not in st.session_state:
    st.session_state.step = 1

def buscar_vagas(cargo, local):
    try:
        url = "https://serpapi.com/search.json"
        params = {
            "engine": "google_jobs",
            "q": f"{cargo} {local}",
            "hl": "pt",
            "api_key": st.secrets["SERPAPI_KEY"]
        }
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        return [{"title": j.get("title"), "company": j.get("company_name"), "location": j.get("location"), "description": j.get("description")} for j in data.get("jobs_results", [])]
    except:
        return []

def extrair_texto(uploaded_file):
    if uploaded_file.type == "application/pdf":
        return "".join([p.extract_text() for p in PdfReader(uploaded_file).pages])
    return "\n".join([p.text for p in Document(uploaded_file).paragraphs])

def gerar_ats(cv, vaga):
    prompt = f"Otimize o resumo deste CV para esta vaga. CV: {cv[:3000]} Vaga: {vaga[:2000]}"
    # USANDO O MESMO MODEL_ID QUE PASSOU NO TESTE
    response = client.models.generate_content(model=MODEL_ID, contents=prompt)
    return response.text

# ==========================================
# INTERFACE SIMPLIFICADA E DIRETA
# ==========================================
if st.session_state.step == 1:
    st.header("1. Buscar Vaga")
    c1, c2 = st.columns(2)
    cargo = c1.text_input("Cargo", "Android Developer")
    local = c2.text_input("Local", "Remoto")
    if st.button("Buscar Vagas"):
        st.session_state.vagas = buscar_vagas(cargo, local)
    
    if "vagas" in st.session_state:
        for i, v in enumerate(st.session_state.vagas):
            with st.container(border=True):
                st.write(f"**{v['title']}** - {v['company']}")
                if st.button("Selecionar", key=f"v_{i}"):
                    st.session_state.vaga_ativa = v
                    st.session_state.step = 2
                    st.rerun()

elif st.session_state.step == 2:
    st.header("2. Adaptar CV")
    st.subheader(st.session_state.vaga_ativa['title'])
    file = st.file_uploader("Suba seu CV", type=["pdf", "docx"])
    
    if file:
        if st.button("Gerar Versão Otimizada"):
            texto_cv = extrair_texto(file)
            resumo = gerar_ats(texto_cv, st.session_state.vaga_ativa['description'])
            st.text_area("Resultado ATS:", resumo, height=300)
    
    if st.button("Voltar"):
        st.session_state.step = 1
        st.rerun()
