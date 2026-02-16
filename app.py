import streamlit as st
import json
import sqlite3
import requests
from google import genai
from datetime import datetime

# =========================
# CONFIGURAÇÃO INICIAL
# =========================
st.set_page_config(page_title="Agente de Carreira AI", layout="wide", page_icon="🚀")

# =========================
# VERIFICAÇÃO DE CHAVES
# =========================
if "GOOGLE_API_KEY" not in st.secrets:
    st.error("🚨 Configure GOOGLE_API_KEY no Streamlit Secrets.")
    st.stop()

if "SERPAPI_KEY" not in st.secrets:
    st.error("🚨 Configure SERPAPI_KEY no Streamlit Secrets.")
    st.stop()

client = genai.Client(api_key=st.secrets["GOOGLE_API_KEY"])

# =========================
# BANCO DE DADOS
# =========================
def init_db():
    conn = sqlite3.connect('career_agent.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS user_profile 
                 (id INTEGER PRIMARY KEY, matrix_json TEXT, last_updated DATETIME)''')
    conn.commit()
    return conn

conn = init_db()

# =========================
# MOTOR DE BUSCA – GOOGLE JOBS
# =========================
def agente_explorer_vagas(cargo, local):
    url = "https://serpapi.com/search.json"

    params = {
        "engine": "google_jobs",
        "q": f"{cargo} {local}",
        "hl": "en",
        "api_key": st.secrets["SERPAPI_KEY"]
    }

    logs = [f"🔍 Buscando: {cargo} - {local}"]

    try:
        response = requests.get(url, params=params)
        data = response.json()

        vagas = []

        for job in data.get("jobs_results", []):
            vagas.append({
                "title": job.get("title"),
                "company": job.get("company_name"),
                "location": job.get("location"),
                "description": job.get("description"),
                "via": job.get("via"),
                "link": job.get("related_links", [{}])[0].get("link")
            })

        if not vagas:
            logs.append("⚠️ Nenhuma vaga encontrada.")

        return vagas, logs

    except Exception as e:
        logs.append(f"🚨 Erro: {str(e)}")
        return [], logs

# =========================
# SIDEBAR
# =========================
st.sidebar.title("🤖 Agent Command Center")

app_mode = st.sidebar.radio(
    "Módulo:",
    ["🔍 Buscar Vagas", "📄 Adaptar Currículo"]
)

st.sidebar.divider()
st.sidebar.subheader("Sincronizar Perfil")

matrix_input = st.sidebar.file_uploader("Enviar Matriz JSON", type=["json"])

if matrix_input:
    matrix_data = json.load(matrix_input)
    conn.execute(
        "INSERT OR REPLACE INTO user_profile (id, matrix_json, last_updated) VALUES (1, ?, datetime('now'))",
        (json.dumps(matrix_data),)
    )
    conn.commit()
    st.sidebar.success("✅ Perfil salvo!")

# =========================
# MÓDULO BUSCA
# =========================
if app_mode == "🔍 Buscar Vagas":
    st.header("🔍 Google Jobs – Busca Inteligente")
    st.caption(f"Data: {datetime.now().strftime('%d/%m/%Y')}")

    col1, col2 = st.columns(2)

    with col1:
        cargo_q = st.text_input("Cargo:", value="Android Developer")

    with col2:
        local_q = st.text_input("Localização:", value="Remote United States")

    if st.button("🚀 Iniciar Busca", use_container_width=True):
        vagas, logs_debug = agente_explorer_vagas(cargo_q, local_q)

        with st.expander("📝 Logs Técnicos"):
            for l in logs_debug:
                st.text(l)

        if vagas:
            st.success(f"🎯 Encontramos {len(vagas)} vagas!")

            for i, v in enumerate(vagas):
                with st.container(border=True):
                    st.markdown(f"### {v['title']}")
                    st.markdown(f"**Empresa:** {v['company']}")
                    st.markdown(f"📍 {v['location']}")
                    st.markdown(f"🔗 [Ver Vaga]({v['link']})")
                    st.write(v['description'][:600] + "...")

                    if st.button(f"Selecionar Vaga #{i+1}", key=f"vaga_{i}"):
                        st.session_state["vaga_ativa"] = v
                        st.success("Vaga selecionada!")
        else:
            st.warning("Nenhuma vaga encontrada.")

# =========================
# MÓDULO CURRÍCULO
# =========================
elif app_mode == "📄 Adaptar Currículo":

    st.header("📄 Adaptador Inteligente")

    row = conn.execute("SELECT matrix_json FROM user_profile WHERE id = 1").fetchone()

    if not row:
        st.warning("⚠️ Envie sua Matriz JSON primeiro.")
        st.stop()

    vaga = st.session_state.get("vaga_ativa", None)

    if not vaga:
        st.warning("⚠️ Selecione uma vaga no módulo de busca.")
        st.stop()

    st.subheader("📌 Vaga Selecionada")
    st.write(f"**{vaga['title']} – {vaga['company']}**")
    st.write(vaga["description"][:800] + "...")

    if st.button("🧠 Gerar Currículo Otimizado", use_container_width=True):
        with st.spinner("IA adaptando seu perfil..."):

            prompt = f"""
Adapte o perfil abaixo para esta vaga.

PERFIL:
{row[0]}

VAGA:
{vaga['description']}

Retorne em Markdown profissional otimizado para ATS.
"""

            resp = client.models.generate_content(
                model="gemini-2.0-flash",
                contents=prompt
            )

            st.success("✅ Currículo gerado!")
            st.markdown(resp.text)
