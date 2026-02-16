import re
import json
import sqlite3
import streamlit as st
from google import genai
from pypdf import PdfReader
import streamlit.components.v1 as components
from html import escape
from duckduckgo_search import DDGS

# =========================
# 1) CONFIGURAÇÃO DA PÁGINA E DB
# =========================
st.set_page_config(page_title="Agente de Carreira AI", layout="wide", page_icon="🚀")

# CSS para o PDF/ATS
CV_CSS_ATS = """
<style>
.cv-paper { font-family: Arial, sans-serif; color: #000; background: #fff; width: 850px; margin: 0 auto; padding: 48px; line-height: 1.45; }
h1 { font-size: 28px; margin-bottom: 6px; font-weight: 700; }
.contact { font-size: 11pt; margin-bottom: 18px; }
.section-title { font-size: 12pt; font-weight: 700; margin-top: 22px; margin-bottom: 8px; letter-spacing: 0.04em; }
.job-header { font-weight: 700; margin-top: 10px; }
.job-title { font-style: italic; margin-bottom: 4px; }
ul { margin-top: 4px; padding-left: 18px; }
li { margin-bottom: 6px; }
</style>
"""

def init_db():
    conn = sqlite3.connect('career_agent.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS user_profile 
                 (id INTEGER PRIMARY KEY, matrix_json TEXT, last_updated DATETIME)''')
    c.execute('''CREATE TABLE IF NOT EXISTS job_log 
                 (id INTEGER PRIMARY KEY, title TEXT, company TEXT, link TEXT, status TEXT)''')
    conn.commit()
    return conn

conn = init_db()

if "GOOGLE_API_KEY" not in st.secrets:
    st.error("Configure a chave 'GOOGLE_API_KEY' em .streamlit/secrets.toml")
    st.stop()

client = genai.Client(api_key=st.secrets["GOOGLE_API_KEY"])

# =========================
# 2) HELPERS & LOGIC
# =========================
def get_response_text(response) -> str:
    try:
        return response.text if hasattr(response, "text") else response.candidates[0].content.parts[0].text
    except: return ""

def extract_json_loose(text: str) -> dict:
    text = (text or "").strip()
    text = re.sub(r"```(?:json)?", "", text, flags=re.IGNORECASE).strip("` \n\r\t")
    i = text.find("{")
    if i == -1: raise ValueError("JSON não encontrado")
    return json.JSONDecoder().raw_decode(text[i:])[0]

def render_ats_html(cv: dict) -> str:
    h = cv.get("header", {})
    html = [f"<h1>{h.get('name','')}</h1>"]
    contact = [h.get("phone")] + h.get("links", [])
    html.append(f"<div class='contact'>{' • '.join([str(x) for x in contact if x])}</div>")
    
    sections = [("SUMMARY", cv.get("summary")), ("WORK EXPERIENCE", cv.get("experience")), 
                ("EDUCATION", cv.get("education")), ("SKILLS", cv.get("skills"))]
    
    for title, content in sections:
        if not content: continue
        html.append(f"<div class='section-title'>{title}</div>")
        if title == "WORK EXPERIENCE":
            for e in content:
                html.append(f"<div class='job-header'>{e.get('company')} — {e.get('date_range')}</div>")
                html.append(f"<div class='job-title'>{e.get('title')}</div>")
                html.append("<ul>" + "".join([f"<li>▪ {a}</li>" for a in e.get("achievements", [])]) + "</ul>")
        elif isinstance(content, list):
            html.append("<p>" + ", ".join([str(x) for x in content]) + "</p>")
        else:
            html.append(f"<p>{content}</p>")
    return "\n".join(html)

# =========================
# 3) SIDEBAR (CONFIGURAÇÃO)
# =========================
st.sidebar.title("🤖 Agent Command Center")
app_mode = st.sidebar.radio("Módulo:", ["🔍 Motor de Busca", "📄 Gerador de Currículo"])

st.sidebar.divider()
matrix_input = st.sidebar.file_uploader("Upload Matriz JSON", type=["json"])

if matrix_input:
    matrix_data = json.load(matrix_input)
    conn.execute("INSERT OR REPLACE INTO user_profile (id, matrix_json, last_updated) VALUES (1, ?, datetime('now'))", 
                 (json.dumps(matrix_data),))
    conn.commit()
    st.sidebar.success("Matriz atualizada!")

# =========================
# 4) MÓDULO: MOTOR DE BUSCA
# =========================
if app_mode == "🔍 Motor de Busca":
    st.title("🔍 Motor de Busca de Vagas")
    col1, col2 = st.columns(2)
    with col1: cargo = st.text_input("Cargo:", value="Product Manager")
    with col2: local = st.text_input("Localização:", value="Houston, TX")

    if st.button("Agente, buscar novas vagas", use_container_width=True):
        with st.spinner("Varrendo LinkedIn e Indeed..."):
            query = f"{cargo} jobs in {local} site:[linkedin.com/jobs/view](https://linkedin.com/jobs/view) OR site:[indeed.com/viewjob](https://indeed.com/viewjob)"
            with DDGS() as ddgs:
                results = [r for r in ddgs.text(query, max_results=5)]
            
            if results:
                for i, res in enumerate(results):
                    with st.container(border=True):
                        st.write(f"### {res['title']}")
                        st.write(f"**Link:** {res['href']}")
                        st.write(res['body'])
                        if st.button(f"Enviar para Gerador #{i+1}", key=f"btn_{i}"):
                            st.session_state['vaga_ativa'] = res['body']
                            st.success("✅ Vaga carregada! Vá para 'Gerador de Currículo'.")
            else: st.warning("Nenhuma vaga encontrada.")

# =========================
# 5) MÓDULO: GERADOR DE CURRÍCULO
# =========================
elif app_mode == "📄 Gerador de Currículo":
    st.title("📄 Gerador de CV Adaptado")
    
    row = conn.execute("SELECT matrix_json FROM user_profile WHERE id = 1").fetchone()
    if not row:
        st.warning("⚠️ Faça upload da sua Matriz no menu lateral.")
        st.stop()
    
    saved_matrix = json.loads(row[0])
    vaga_previa = st.session_state.get('vaga_ativa', "")

    job_desc = st.text_area("Descrição da vaga:", value=vaga_previa, height=250)
    
    if st.button("Gerar Currículo com Gemini 2.0 Flash", use_container_width=True):
        with st.spinner("IA adaptando seu perfil..."):
            # Prompt simplificado para o exemplo (use o seu original completo aqui)
            prompt = f"Crie um currículo em JSON baseado nesta matriz: {json.dumps(saved_matrix)} para esta vaga: {job_desc}"
            resp = client.models.generate_content(model="gemini-2.0-flash", contents=prompt)
            try:
                data = extract_json_loose(get_response_text(resp))
                st.session_state['curriculo_gerado'] = data
            except Exception as e: st.error(f"Erro no processamento da IA: {e}")

    if 'curriculo_gerado' in st.session_state:
        cv_data = st.session_state['curriculo_gerado'].get("cv", {})
        full_html = f"<html><head>{CV_CSS_ATS}</head><body><div class='cv-paper'>{render_ats_html(cv_data)}</div></body></html>"
        components.html(full_html, height=800, scrolling=True)
        st.download_button("📥 Baixar CV (.doc)", data=full_html, file_name="CV_Adaptado.doc", mime="application/msword")
