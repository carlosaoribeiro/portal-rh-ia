import re
import json
import sqlite3
import streamlit as st
from datetime import datetime, timedelta
from google import genai
from pypdf import PdfReader
import streamlit.components.v1 as components
from html import escape
from duckduckgo_search import DDGS

# =========================
# 1) CONFIGURAÇÃO E BANCO DE DADOS
# =========================
st.set_page_config(page_title="Agente de Carreira AI", layout="wide", page_icon="🚀")

def init_db():
    conn = sqlite3.connect('career_agent.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS user_profile 
                 (id INTEGER PRIMARY KEY, matrix_json TEXT, last_updated DATETIME)''')
    c.execute('''CREATE TABLE IF NOT EXISTS job_log 
                 (id INTEGER PRIMARY KEY, title TEXT, company TEXT, link TEXT, status TEXT, date_found DATETIME)''')
    conn.commit()
    return conn

conn = init_db()

if "GOOGLE_API_KEY" not in st.secrets:
    st.error("Configure a chave 'GOOGLE_API_KEY' em .streamlit/secrets.toml")
    st.stop()

client = genai.Client(api_key=st.secrets["GOOGLE_API_KEY"])

# =========================
# 2) HELPERS
# =========================
def get_response_text(response) -> str:
    try: return response.text if hasattr(response, "text") else response.candidates[0].content.parts[0].text
    except: return ""

def extract_json_loose(text: str) -> dict:
    text = (text or "").strip().replace("```json", "").replace("```", "").strip()
    i = text.find("{")
    return json.JSONDecoder().raw_decode(text[i:])[0]

def render_ats_html(cv: dict) -> str:
    h = cv.get("header", {})
    html = [f"<h1 style='text-align:center;'>{escape(h.get('name',''))}</h1>"]
    contact = [h.get("phone")] + h.get("links", [])
    html.append(f"<div style='text-align:center; margin-bottom:20px;'>{' • '.join([escape(str(x)) for x in contact if x])}</div>")
    
    sections = [("RESUMO", cv.get("summary")), ("EXPERIÊNCIA", cv.get("experience")), 
                ("EDUCAÇÃO", cv.get("education")), ("COMPETÊNCIAS", cv.get("skills"))]
    
    for title, content in sections:
        if not content: continue
        html.append(f"<div style='border-bottom: 1px solid #000; font-weight:bold; margin-top:20px;'>{title}</div>")
        if title == "EXPERIÊNCIA":
            for e in content:
                html.append(f"<div style='display:flex; justify-content:space-between; font-weight:bold; margin-top:10px;'><span>{escape(e.get('company',''))}</span><span>{escape(e.get('date_range',''))}</span></div>")
                html.append(f"<div style='font-style:italic;'>{escape(e.get('title',''))}</div>")
                html.append("<ul>" + "".join([f"<li>{escape(a)}</li>" for a in e.get("achievements", [])]) + "</ul>")
        elif isinstance(content, list):
            html.append("<p>" + ", ".join([escape(str(x)) for x in content]) + "</p>")
        else:
            html.append(f"<p>{escape(content)}</p>")
    return "\n".join(html)

# =========================
# 3) INTERFACE LATERAL
# =========================
st.sidebar.title("🤖 Agent Command Center")
app_mode = st.sidebar.radio("Selecione o Módulo:", ["🔍 Motor de Busca", "📄 Gerador de Currículo"])

st.sidebar.divider()
matrix_input = st.sidebar.file_uploader("Atualizar Matriz JSON", type=["json"])

if matrix_input:
    matrix_data = json.load(matrix_input)
    conn.execute("INSERT OR REPLACE INTO user_profile (id, matrix_json, last_updated) VALUES (1, ?, datetime('now'))", 
                 (json.dumps(matrix_data),))
    conn.commit()
    st.sidebar.success("✅ Matriz sincronizada!")

# =========================
# 4) MÓDULO: MOTOR DE BUSCA (LINKS DIRECIONADOS)
# =========================
if app_mode == "🔍 Motor de Busca":
    st.title("🔍 Busca em Portais Selecionados")
    
    hoje = datetime.now()
    data_7_dias = hoje - timedelta(days=7)
    st.info(f"Buscando no LinkedIn, FlexJobs, Glassdoor e Remote.co desde {data_7_dias.strftime('%d/%m/%Y')}.")

    col1, col2 = st.columns(2)
    with col1: cargo = st.text_input("Cargo:", value="Product Manager")
    with col2: local = st.text_input("Local:", value="Remote")

    if st.button("Agente, buscar vagas recentes", use_container_width=True):
        with st.spinner("Consultando bases de dados..."):
            # Query focada nos seus 4 portais específicos
            sites = ["linkedin.com/jobs", "flexjobs.com", "glassdoor.com/Job", "remote.co"]
            site_query = " OR ".join([f"site:{s}" for s in sites])
            full_query = f'"{cargo}" {local} ({site_query})'
            
            try:
                with DDGS() as ddgs:
                    results = [r for r in ddgs.text(full_query, max_results=15)]

                if results:
                    st.success(f"Encontramos {len(results)} vagas!")
                    for i, res in enumerate(results):
                        with st.container(border=True):
                            st.markdown(f"### {res['title']}")
                            st.caption(f"📍 [Abrir vaga no portal]({res['href']})")
                            st.write(res['body'])
                            if st.button(f"Selecionar Vaga #{i+1}", key=f"sel_{i}"):
                                st.session_state['vaga_ativa'] = res['body']
                                st.session_state['titulo_vaga_ativa'] = res['title']
                                st.success("Vaga carregada!")
                else:
                    st.warning("Nenhuma vaga encontrada nesses sites. Tente remover o filtro de local.")
            except Exception as e:
                st.error(f"Erro na busca: {e}")

# =========================
# 5) MÓDULO: GERADOR DE CURRÍCULO
# =========================
elif app_mode == "📄 Gerador de Currículo":
    st.title("📄 Gerador de CV Adaptado")
    row = conn.execute("SELECT matrix_json FROM user_profile WHERE id = 1").fetchone()
    if not row:
        st.warning("⚠️ Carregue sua Matriz no menu lateral.")
        st.stop()
    
    saved_matrix = json.loads(row[0])
    vaga_auto = st.session_state.get('vaga_ativa', "")
    
    job_desc = st.text_area("Descrição da vaga:", value=vaga_auto, height=250)
    
    if st.button("Gerar Currículo Otimizado", use_container_width=True):
        with st.spinner("IA adaptando keywords..."):
            prompt = f"Como Tech Recruiter, use a matriz {json.dumps(saved_matrix)} e adapte para a vaga: {job_desc}. Retorne APENAS o JSON estruturado."
            resp = client.models.generate_content(model="gemini-2.0-flash", contents=prompt)
            try:
                data = extract_json_loose(get_response_text(resp))
                st.session_state['cv_gerado'] = data
                st.success("Gerado!")
            except Exception as e:
                st.error(f"Erro no JSON da IA: {e}")

    if 'cv_gerado' in st.session_state:
        cv_data = st.session_state['cv_gerado'].get("cv", {})
        html_content = f"<html><body><div style='background:white; padding:30px; color:black;'>{render_ats_html(cv_data)}</div></body></html>"
        components.html(html_content, height=800, scrolling=True)
        st.download_button("📥 Baixar CV", data=html_content, file_name="Curriculo.doc", mime="application/msword")
