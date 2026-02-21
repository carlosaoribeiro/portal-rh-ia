import streamlit as st
import requests
import google.generativeai as genai
from io import BytesIO
from docx import Document
from pypdf import PdfReader

# Configuração da Página
st.set_page_config(page_title="Portal RH IA", layout="wide")

# Inicialização da IA (Biblioteca Estável)
try:
    # Limpa a chave de aspas ou espaços acidentais
    api_key = st.secrets["GOOGLE_API_KEY"].strip().replace('"', '').replace("'", "")
    genai.configure(api_key=api_key)
    
    # Define o modelo estável
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    # Teste rápido de conexão
    model.generate_content("oi")
except Exception as e:
    st.error(f"Erro de Conexão: {e}")
    st.info("Verifique se sua GOOGLE_API_KEY no Secrets está correta.")
    st.stop()

# Controle de Navegação
if "step" not in st.session_state:
    st.session_state.step = 1

# --- FUNÇÕES ---
def buscar_vagas(cargo, local):
    try:
        api_serp = st.secrets["SERPAPI_KEY"].strip().replace('"', '').replace("'", "")
        url = "https://serpapi.com/search.json"
        params = {
            "engine": "google_jobs",
            "q": f"{cargo} {local}",
            "api_key": api_serp
        }
        r = requests.get(url, params=params, timeout=10)
        return r.json().get("jobs_results", [])
    except:
        return []

def extrair_texto(file):
    try:
        if file.type == "application/pdf":
            reader = PdfReader(file)
            return "".join([page.extract_text() for page in reader.pages])
        doc = Document(file)
        return "\n".join([p.text for p in doc.paragraphs])
    except:
        return ""

# --- INTERFACE ---
if st.session_state.step == 1:
    st.header("🔍 1. Buscar Vagas")
    c1, c2 = st.columns(2)
    cargo = c1.text_input("Cargo:", "Android Developer")
    local = c2.text_input("Localização:", "Brasil")
    
    if st.button("Pesquisar Oportunidades"):
        with st.spinner("Buscando no Google Jobs..."):
            st.session_state.vagas = buscar_vagas(cargo, local)
    
    if "vagas" in st.session_state:
        for i, v in enumerate(st.session_state.vagas):
            with st.container(border=True):
                st.subheader(v.get('title'))
                st.write(f"**Empresa:** {v.get('company_name')} | **Local:** {v.get('location')}")
                if st.button("Selecionar Vaga", key=f"btn_{i}"):
                    st.session_state.vaga_ativa = v
                    st.session_state.step = 2
                    st.rerun()

elif st.session_state.step == 2:
    vaga = st.session_state.vaga_ativa
    st.header("📄 2. Adaptar Currículo")
    st.info(f"Vaga: {vaga.get('title')} na {vaga.get('company_name')}")
    
    upload = st.file_uploader("Suba seu CV (PDF ou DOCX)", type=["pdf", "docx"])
    
    if upload:
        if st.button("GERAR CURRÍCULO OTIMIZADO"):
            with st.spinner("IA criando seu novo resumo..."):
                texto_cv = extrair_texto(upload)
                desc_vaga = vaga.get('description', '')
                
                prompt = (
                    f"Atue como especialista em RH. Reescreva o resumo profissional do currículo "
                    f"para alinhar perfeitamente com a descrição da vaga abaixo. "
                    f"Use as palavras-chave da vaga, mas não invente experiências.\n\n"
                    f"VAGA:\n{desc_vaga[:2000]}\n\n"
                    f"CURRÍCULO:\n{texto_cv[:3000]}"
                )
                
                try:
                    response = model.generate_content(prompt)
                    st.success("Otimização Concluída!")
                    st.markdown("---")
                    st.write(response.text)
                except Exception as e:
                    st.error(f"Erro na IA: {e}")
    
    if st.button("Voltar para a busca"):
        st.session_state.step = 1
        st.rerun()
