import json
import streamlit as st
import streamlit.components.v1 as components
from google import genai

from src.matrix import (
    extract_pdf_text,
    normalize_matrix,
    detect_language,
    validate_coverage,
)
from src.prompt import build_prompt
from src.gemini_client import get_response_text, extract_json_loose
from src.renderer import render_cv_html

# ===== Page =====
st.set_page_config(page_title="Gerador de Currículo (Matriz → Gemini)", layout="wide", page_icon="🚀")

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
.missing { color: #666; font-style: italic; text-decoration: underline; }
</style>
"""

# ===== Secrets / Client =====
if "GOOGLE_API_KEY" not in st.secrets:
    st.error("Configure a chave 'GOOGLE_API_KEY' em .streamlit/secrets.toml")
    st.stop()

client = genai.Client(api_key=st.secrets["GOOGLE_API_KEY"])

# ===== UI =====
st.markdown("<h1 style='text-align:center;'>🚀 CV Generator (Matriz → Gemini)</h1>", unsafe_allow_html=True)

left, mid, right = st.columns([1, 2, 1])
with mid:
    st.subheader("1) Fonte (Matriz)")
    matrix_json_file = st.file_uploader("Upload da MATRIZ (JSON) — recomendado", type=["json"])
    matrix_pdf_file = st.file_uploader("Ou use PDF (fallback)", type=["pdf"])

    st.subheader("2) Alvo")
    job_description = st.text_area("Job Description", height=220)
    company_description = st.text_area("Company Description (opcional)", height=140)

    st.subheader("3) Saída")
    show_missing = st.toggle("Mostrar 'MISSING — ...' no preview", value=True)
    export_final = st.toggle("Exportar versão FINAL (remove 'MISSING')", value=False)

    btn = st.button("Gerar CV + Análise", use_container_width=True)

# ===== State =====
if "data" not in st.session_state:
    st.session_state.data = None
if "debug" not in st.session_state:
    st.session_state.debug = {}

# ===== Load matrix =====
def load_matrix() -> dict:
    if matrix_json_file is not None:
        raw = matrix_json_file.read().decode("utf-8")
        return json.loads(raw)

    if matrix_pdf_file is not None:
        # fallback: só usa texto bruto como base (você pode evoluir para parser completo)
        pdf_text = extract_pdf_text(matrix_pdf_file)
        # matriz mínima: você pode editar/expandir depois
        return {
            "header": {"name": "", "contact_line": []},
            "summary": pdf_text[:1500],
            "experiences": [],
            "education": [],
            "skills_raw": ""
        }

    return {}

# ===== Run =====
if btn:
    if not job_description.strip():
        st.warning("Cole a Job Description.")
        st.stop()

    matrix = load_matrix()
    matrix = normalize_matrix(matrix)

    # valida matriz mínima
    if not matrix.get("experiences"):
        st.warning("Sua matriz não tem experiences[]. Para garantir 'não omitir experiências', envie a MATRIZ em JSON com experiences e exp_id.")
        st.stop()

    expected_ids = [e.get("exp_id") for e in matrix["experiences"] if e.get("exp_id")]
    if not expected_ids:
        st.warning("Sua matriz não tem exp_id. Gere exp_id para cada experiência.")
        st.stop()

    lang = detect_language(job_description)
    prompt = build_prompt(matrix, job_description, company_description or "", lang)

    with st.spinner("Gerando com Gemini..."):
        resp = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt
        )
        raw = get_response_text(resp).strip()

    try:
        data = extract_json_loose(raw)
    except Exception as e:
        st.error(f"Falha ao interpretar JSON do modelo: {e}")
        with st.expander("Resposta bruta do modelo"):
            st.text(raw)
        st.stop()

    # ===== Coverage validation (hard gate) =====
    cv_exps = (data.get("cv", {}) or {}).get("experience", []) or []
    output_ids = [e.get("exp_id") for e in cv_exps if e.get("exp_id")]

    cov = validate_coverage(expected_ids, output_ids)
    if cov["missing"]:
        st.error(f"Modelo omitiu experiências da matriz: {cov['missing']}")
        with st.expander("Debug"):
            st.json({"expected_exp_ids": expected_ids, "output_exp_ids": output_ids, "raw_model": raw[:2000]})
        st.stop()

    if cov["extra"]:
        st.warning(f"Modelo retornou exp_id não existente na matriz: {cov['extra']}")

    st.session_state.data = data
    st.session_state.debug = {
        "lang": lang,
        "expected_exp_ids": expected_ids,
        "output_exp_ids": output_ids,
        "raw_len": len(raw),
    }

# ===== Display =====
if st.session_state.data:
    data = st.session_state.data
    cv = data.get("cv", {}) or {}
    analysis_md = data.get("analysis_md", "") or ""
    missing_info = data.get("missing_info", []) or []

    # HTML render
    clean_html = render_cv_html(cv, show_missing=show_missing, export_clean=export_final)
    full_doc = f"<html><head><meta charset='UTF-8'>{CV_CSS}</head><body><div class='cv-paper'>{clean_html}</div></body></html>"

    st.divider()
    components.html(full_doc, height=1000, scrolling=True)

    c1, c2 = st.columns(2)
    with c1:
        st.download_button(
            "📥 Baixar CV (.doc) — HTML para Word",
            data=full_doc,
            file_name="Curriculo.doc",
            mime="application/msword",
            use_container_width=True
        )
    with c2:
        st.download_button(
            "📥 Baixar Saída JSON (debug/auditoria)",
            data=json.dumps(data, ensure_ascii=False, indent=2),
            file_name="saida_gemini.json",
            mime="application/json",
            use_container_width=True
        )

    st.divider()
    st.subheader("📊 Relatório / Preparação para Entrevista")
    st.markdown(analysis_md)

    if missing_info:
        st.subheader("⚠️ Informações faltando (complete antes de enviar)")
        for item in missing_info:
            field = item.get("field", "")
            why = item.get("why_it_matters", "")
            ex = item.get("suggested_input_example", "")
            st.write(f"- **{field}**: {why}")
            if ex:
                st.caption(f"Exemplo: {ex}")

    with st.expander("🔎 Debug"):
        st.json(st.session_state.debug)
        st.json(data.get("experience_coverage", {}))
