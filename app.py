import re
import json
import streamlit as st
from google import genai
from pypdf import PdfReader
import streamlit.components.v1 as components
from html import escape

# 1) CONFIGURAÇÃO DA PÁGINA
st.set_page_config(page_title="Gerador de Currículo", layout="wide", page_icon="🚀")

CV_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;700&display=swap');
body { background-color: #f4f4f4; font-family: 'Roboto', sans-serif; }
.cv-paper {
    background-color: #ffffff; width: 850px; margin: 0 auto; padding: 50px;
    box-shadow: 0 0 15px rgba(0,0,0,0.1); color: #000; line-height: 1.4;
}
h1 { font-size: 26px; margin-bottom: 5px; font-weight: 700; text-align: center; font-family: 'Roboto', sans-serif; }
.contact-line { font-size: 0.95em; margin-bottom: 20px; border-bottom: 1px solid #eee; padding-bottom: 10px; text-align: center; }
.section-title { border-bottom: 1.5px solid #000; text-transform: uppercase; font-weight: 700; margin-top: 25px; margin-bottom: 10px; font-size: 1.1em; }

.timeline-table { width: 100%; border-collapse: collapse; margin-top: 15px; }
.company-name { text-align: left; font-weight: 700; font-size: 1.1em; }
.date-range { text-align: right; font-weight: 700; font-size: 1.1em; }

.subrow-table { width: 100%; border-collapse: collapse; margin-bottom: 8px; }
.job-title { text-align: left; font-style: italic; color: #333; }
.location { text-align: right; font-style: italic; color: #333; }

.experience-description { text-align: justify; font-size: 10.5pt; margin-bottom: 15px; line-height: 1.5; white-space: pre-line; }
ul { margin-top: 6px; }
</style>
"""

# 2) CONEXÃO API
if "GOOGLE_API_KEY" not in st.secrets:
    st.error("Configure a chave 'GOOGLE_API_KEY' nos Secrets!")
    st.stop()

client = genai.Client(api_key=st.secrets["GOOGLE_API_KEY"])

def detect_language(text: str) -> str:
    text = (text or "").lower()
    pt_hits = len(re.findall(r"\b(vaga|requisitos|experi[eê]ncia|responsabilidades|conhecimento)\b", text))
    return "pt-BR" if pt_hits >= 2 else "en"

def extract_pdf_text(uploaded_file) -> str:
    reader = PdfReader(uploaded_file)
    parts = []
    for p in reader.pages:
        t = p.extract_text() or ""
        if t.strip():
            parts.append(t)
    return "\n".join(parts).strip()

def get_response_text(response) -> str:
    if hasattr(response, "text") and response.text:
        return response.text
    try:
        return response.candidates[0].content.parts[0].text
    except Exception:
        return ""

def extract_json_loose(text: str) -> dict:
    """
    Tenta pegar JSON mesmo se o modelo colocar texto extra.
    Pega do primeiro "{" ao último "}".
    """
    text = text.strip()
    # caso já seja json puro
    if text.startswith("{") and text.endswith("}"):
        return json.loads(text)

    # fallback: recorta
    i = text.find("{")
    j = text.rfind("}")
    if i == -1 or j == -1 or j <= i:
        raise ValueError("Resposta não contém um objeto JSON válido.")
    candidate = text[i:j+1]
    return json.loads(candidate)

def join_slash(items):
    items = [i.strip() for i in (items or []) if (i or "").strip()]
    return " / ".join(items)

def render_cv_html(cv: dict) -> str:
    # Helpers de escape para evitar HTML quebrado/injeção
    def e(x): return escape(str(x or "").strip())

    header = cv.get("header", {})
    name = e(header.get("name"))
    contact = header.get("contact_line", [])
    contact_line = " | ".join([e(x) for x in contact if str(x).strip()])

    summary = cv.get("summary", "")
    skills = cv.get("skills", [])
    education = cv.get("education", [])
    experience = cv.get("experience", [])

    html = []
    html.append(f"<h1>{name}</h1>")
    if contact_line:
        html.append(f"<div class='contact-line'>{contact_line}</div>")

    if summary:
        html.append("<div class='section-title'>Resumo</div>")
        html.append(f"<div class='experience-description'>{e(summary)}</div>")

    if skills:
        html.append("<div class='section-title'>Skills</div>")
        html.append("<div class='experience-description'>")
        html.append(e(join_slash(skills)))
        html.append("</div>")

    if experience:
        html.append("<div class='section-title'>Experiência</div>")
        for exp in experience:
            company = e(exp.get("company"))
            date_range = e(exp.get("date_range"))
            title = e(exp.get("title"))
            location = e(exp.get("location"))
            achievements = exp.get("achievements", [])

            html.append("<table class='timeline-table'>")
            html.append("<tr>")
            html.append(f"<td class='company-name'>{company}</td>")
            html.append(f"<td class='date-range'>{date_range}</td>")
            html.append("</tr>")
            html.append("</table>")

            html.append("<table class='subrow-table'>")
            html.append("<tr>")
            html.append(f"<td class='job-title'>{title}</td>")
            html.append(f"<td class='location'>{location}</td>")
            html.append("</tr>")
            html.append("</table>")

            # bloco corrido com "/"
            html.append(f"<div class='experience-description'>{e(join_slash(achievements))}</div>")

    if education:
        html.append("<div class='section-title'>Educação</div>")
        for edu in education:
            line = edu.get("line") or ""
            details = edu.get("details") or ""
            text = f"{line} / {details}".strip(" /")
            html.append(f"<div class='experience-description'>{e(text)}</div>")

    return "\n".join(html)

def build_prompt(cv_text: str, job_description: str, lang: str) -> str:
    target_lang = "pt-BR" if lang == "pt-BR" else "en-US"
    # Regras claras: só JSON, campos obrigatórios, sem inventar datas/empresas
    return f"""
Return ONLY a valid JSON object (no markdown, no backticks, no commentary).

Schema:
{{
  "cv": {{
    "header": {{
      "name": "string",
      "contact_line": ["string", "string", "string"]
    }},
    "summary": "string",
    "skills": ["string", "..."],
    "experience": [
      {{
        "company": "string",
        "date_range": "string",
        "title": "string",
        "location": "string",
        "achievements": ["string", "string", "string"]
      }}
    ],
    "education": [
      {{
        "line": "string",
        "details": "string"
      }}
    ]
  }},
  "analysis_md": "string (markdown)"
}}

Rules:
- Language for ALL text: {target_lang}
- Do NOT output HTML. Only JSON.
- Do NOT invent companies, titles, or dates; if missing, use empty string "".
- achievements must be short, impact-focused, and tailored to the job; avoid buzzword spam.
- skills: include hard skills relevant to the job, deduplicated.
- analysis_md: include (1) Match summary, (2) Key gaps, (3) Interview prep Q&A, (4) Suggested edits.

Input CV text:
{cv_text}

Target job description:
{job_description}
""".strip()

# 3) INTERFACE
st.markdown("<h1 style='text-align: center;'>🚀 Gerador de Currículo Inteligente</h1>", unsafe_allow_html=True)

_, center_col, _ = st.columns([1, 2, 1])

with center_col:
    uploaded_file = st.file_uploader("Suba seu currículo atual (PDF)", type="pdf")
    job_description = st.text_area("Descrição da vaga alvo:", height=200)
    btn_gerar = st.button("Gerar Currículo e Análise", use_container_width=True)

if "result" not in st.session_state:
    st.session_state.result = None
if "debug" not in st.session_state:
    st.session_state.debug = {}

# LÓGICA
if btn_gerar:
    if not uploaded_file:
        st.warning("Envie um PDF do currículo.")
    elif not job_description.strip():
        st.warning("Cole a descrição da vaga.")
    else:
        with st.spinner("Processando..."):
            try:
                cv_text = extract_pdf_text(uploaded_file)
                if len(cv_text) < 80:
                    st.error("Não consegui extrair texto suficiente do PDF. Se for PDF escaneado (imagem), precisa de OCR.")
                    st.stop()

                lang = detect_language(job_description)
                prompt = build_prompt(cv_text, job_description, lang)

                response = client.models.generate_content(
                    model="gemini-2.0-flash",
                    contents=prompt
                )
                raw = get_response_text(response).strip()

                data = extract_json_loose(raw)

                st.session_state.result = data
                st.session_state.debug = {
                    "cv_text_len": len(cv_text),
                    "raw_len": len(raw),
                    "lang": lang,
                }
            except Exception as e:
                st.session_state.result = None
                st.error(f"Erro: {e}")

# 4) EXIBIÇÃO
if st.session_state.result:
    data = st.session_state.result
    cv = data.get("cv", {})
    analysis_md = data.get("analysis_md", "")

    # Render HTML estável
    clean_html = render_cv_html(cv)
    full_doc = f"<html><head><meta charset='UTF-8'>{CV_CSS}</head><body><div class='cv-paper'>{clean_html}</div></body></html>"

    st.divider()
    components.html(full_doc, height=1000, scrolling=True)

    _, btn_exp_col, _ = st.columns([1, 2, 1])
    with btn_exp_col:
        st.download_button(
            label="📥 Baixar Currículo em Roboto (.doc)",
            data=full_doc,
            file_name="Curriculo_Roboto.doc",
            mime="application/msword",
            use_container_width=True
        )

    st.divider()
    st.subheader("📊 Preparação para Entrevista")
    st.markdown(analysis_md or "_(sem análise)_")

    with st.expander("🔎 Debug"):
        st.write(st.session_state.debug)
        st.json(data)
