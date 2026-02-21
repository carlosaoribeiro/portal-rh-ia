import streamlit as st
import requests
from google import genai
from io import BytesIO
from docx import Document
from pypdf import PdfReader

# Configuração de página
st.set_page_config(page_title="Portal RH IA", layout="wide")

# Inicialização da API com tratamento de erro direto
try:
    # O .strip() remove espaços ou quebras de linha que vimos no seu print
    api_key = st.secrets["GOOGLE_API_KEY"].strip()
    client = genai.Client(api_key=api_key)
    
    # Nome de modelo oficial e estável para evitar o 404
    MODEL_ID = "gemini-1.5-flash"
    
    # Teste de validação silencioso
    client.models.generate_content(model=MODEL_ID, contents="teste")
except Exception as e:
    st.error(f"ERRO DE CONFIGURAÇÃO: {e}")
    st.info("Dica: Verifique se sua chave no Secrets não tem aspas duplas dentro de aspas duplas.")
    st.stop()

# Controle de Navegação
if "step" not in st.session_state:
    st.session_state.step = 1

# Funções de Suporte
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
    st.header("1. Pesquisar Oportunidades")
    col1, col2 = st.columns(2)
    cargo = col1.text_input("Cargo desejado:", "Android Developer")
    local = col2.text_input("Localização:", "Remoto")
    
    if st.button("Buscar Vagas"):
        with st.spinner("Consultando Google Jobs..."):
            st.session_state.vagas = buscar_vagas(cargo, local)
    
    if "vagas" in st.session_state:
        for i, v in enumerate(st.session_state.vagas):
            with st.container(border=True):
                st.subheader(v.get('title'))
                st.write(f"**Empresa:** {v.get('company_name')} | **Local:** {v.get('location')}")
                if st.button("Trabalhar nesta vaga", key=f"btn_{i}"):
                    st.session_state.vaga_ativa = v
                    st.session_state.step = 2
                    st.rerun()

elif st.session_state.step == 2:
    vaga = st.session_state.vaga_ativa
    st.header("2. Otimização de Currículo")
    st.write(f"Vaga selecionada: **{vaga.get('title')}**")
    
    upload = st.file_uploader("Suba seu CV (PDF ou DOCX)", type=["pdf", "docx"])
    
    if upload:
        if st.button("GERAR RESUMO OTIMIZADO"):
            with st.spinner("IA processando..."):
                texto_cv = extrair_texto(upload)
                desc_vaga = vaga.get('description', '')
                
                prompt = (
                    f"Atue como um especialista em RH. Realeje o resumo profissional do currículo abaixo "
                    f"para dar match com a descrição da vaga. Mantenha a verdade, mas use palavras-chave da vaga.\n\n"
                    f"DESCRIÇÃO DA VAGA:\n{desc_vaga[:2000]}\n\n"
                    f"CURRÍCULO ATUAL:\n{texto_cv[:3000]}"
                )
                
                try:
                    res = client.models.generate_content(model=MODEL_ID, contents=prompt)
                    st.success("Resumo Otimizado com Sucesso!")
                    st.markdown("---")
                    st.write(res.text)
                except Exception as e:
                    st.error(f"Erro na IA: {e}")
    
    if st.button("Voltar para busca"):
        st.session_state.step = 1
        st.rerun()
