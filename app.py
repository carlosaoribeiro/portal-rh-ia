import re
import json
import streamlit as st
from google import genai
from pypdf import PdfReader
import streamlit.components.v1 as components
from html import escape

# =========================
# 1) CONFIGURAÇÃO DA PÁGINA
# =========================
st.set_page_config(page_title="Gerador de Currículo", layout="wide", page_icon="🚀")

CV_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;700&display=swap');

body { 
  background-color: #f4f4f4; 
  font-family: 'Roboto', sans-serif; 
}
.cv-paper { 
  background-color: #ffffff; 
  width: 850px; 
  margin: 0 auto;
  padding: 50px; 
  box-shadow: 0 0 15px rgba(0,0,0,0.1); 
  color: #000; 
  line-height: 1.4; 
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

# =========================
# 2) CONEXÃO API (GEMINI)
# =========================
if "GOOGLE_API_KEY" not in st.secrets:
    st.error("Configure a chave 'GOOGLE_API_KEY' em .streamlit/secrets.toml")
    st.stop()

client = genai.Client(api_key=st.secrets["GOOGLE_API_KEY"])

# =========================
# 3) FUNÇÕES AUXILIARES
# =========================
MISSING_RE = re.compile(r"^MISSING\s—\s.+", re.IGNORECASE)
DATE_RE = re.compile(r"\b[A-Z][a-z]{2}\s+\d{4}\s*-\s*(?:Present|[A-Z][a-z]{2}\s+\d{4})\b")

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
    text = (text or "").strip()
    if text.startswith("{") and text.endswith("}"):
        return json.loads(text)
    i = text.find("{")
    j = text.rfind("}")
    if i == -1 or j == -1 or j <= i:
        raise ValueError("Resposta não contém um objeto JSON válido.")
    return json.loads(text[i:j+1])

def achievements_to_list(achievements_raw: str) -> list[str]:
    if not achievements_raw:
        return []
    parts = [p.strip(" \n\r\t-•") for p in achievements_raw.split("/") if p.strip()]
    out, seen = [], set()
    for p in parts:
        key = p.lower()
        if key not in seen:
            out.append(p)
            seen.add(key)
    return out

def ensure_exp_ids(experiences: list[dict]) -> list[dict]:
    for i, exp in enumerate(experiences, start=1):
        exp.setdefault("exp_id", f"exp_{i:02d}")
    return experiences

def normalize_matrix(matrix: dict) -> dict:
    """
    Aceita aliases:
      - experiences (padrão)
      - experience
      - work_experience
      - jobs
    """
    matrix = matrix or {}

    # Aliases de experiências
    if "experiences" not in matrix:
        for k in ("experience", "work_experience", "jobs"):
            if k in matrix and isinstance(matrix.get(k), list):
                matrix["experiences"] = matrix.get(k) or []
                break

    # Header defaults
    if "header" not in matrix or not isinstance(matrix.get("header"), dict):
        matrix["header"] = {}

    header = matrix["header"]
    # normaliza links como lista
    links = header.get("links", [])
    if isinstance(links, str):
        links = [links]
    header["links"] = [str(x).strip() for x in (links or []) if str(x).strip()]

    # normaliza contact_line
    cl = header.get("contact_line", [])
    if isinstance(cl, str):
        cl = [cl]
    header["contact_line"] = [str(x).strip() for x in (cl or []) if str(x).strip()]

    matrix["header"] = header

    exps = ensure_exp_ids(matrix.get("experiences", []) or [])
    for exp in exps:
        if not exp.get("achievements"):
            exp["achievements"] = achievements_to_list(exp.get("achievements_raw", ""))
    matrix["experiences"] = exps
    return matrix

def validate_coverage(expected_ids: list[str], output_ids: list[str]) -> dict:
    expected_set = set(expected_ids)
    output_set = set(output_ids)
    missing = [x for x in expected_ids if x not in output_set]
    extra = [x for x in output_ids if x and x not in expected_set]
    return {"missing": missing, "extra": extra}

def join_slash(items: list[str]) -> str:
    items = [i.strip() for i in (items or []) if (i or "").strip()]
    return " / ".join(items)

def strip_missing(value: str) -> str:
    v = (value or "").strip()
    return "" if MISSING_RE.match(v) else v

def fmt_field(value: str, show_missing: bool = True) -> str:
    v = (value or "").strip()
    if not v:
        return ""
    safe = escape(v)
    if show_missing and MISSING_RE.match(v):
        return f"<span class='missing'>{safe}</span>"
    return safe

def render_cv_html(cv: dict, lang: str, show_missing: bool = True, export_clean: bool = False) -> str:
    """
    Ajuste fino:
    - Depois do Nome e Telefone, mostrar links (LinkedIn/GitHub/Portfólio) se existirem.
    - Se não existirem, passa sem validação e sem quebrar layout.
    """
    cv = cv or {}
    header = cv.get("header", {}) or {}

    name = header.get("name", "") or ""

    # NOVO: phone + links (preferencial)
    phone = header.get("phone", "") or ""
    links = header.get("links", []) or []

    # compatibilidade: contact_line pode ter phone/links
    contact_line = header.get("contact_line", []) or []
    if isinstance(contact_line, str):
        contact_line = [contact_line]

    # tenta pegar phone do contact_line se vazio
    if not phone:
        for item in contact_line:
            if re.search(r"\+\d", str(item)):
                phone = str(item).strip()
                break

    # tenta pegar links do contact_line se vazio
    if not links:
        for item in contact_line:
            for u in re.findall(r"https?://\S+", str(item)):
                u = u.strip().rstrip(").,;")
                if u not in links:
                    links.append(u)

    summary = cv.get("summary", "") or ""
    skills = cv.get("skills", []) or []
    education = cv.get("education", []) or []
    experience = cv.get("experience", []) or []

    if lang == "pt-BR":
        L_SUMMARY, L_SKILLS, L_EXPERIENCE, L_EDU = "Resumo", "Skills", "Experiência", "Educação"
    else:
        L_SUMMARY, L_SKILLS, L_EXPERIENCE, L_EDU = "Summary", "Skills", "Experience", "Education"

    def clean(v: str) -> str:
        return strip_missing(v) if export_clean else (v or "")

    def rel_key(x):
        return 0 if x.get("relevance") == "high" else 1
    experience_sorted = sorted(experience, key=rel_key)

    html = []
    html.append(f"<h1>{fmt_field(clean(name), show_missing)}</h1>")

    # Linha 1: phone
    # Linha 2: links
    contact_rows = []
    if phone:
        contact_rows.append(fmt_field(clean(phone), show_missing))

    if links:
        link_html = " | ".join([
            f"<a href='{escape(u)}' target='_blank'>{escape(u)}</a>"
            for u in links if str(u).strip()
        ])
        if link_html.strip():
            contact_rows.append(link_html)

    # fallback: se não tem phone/links mas tem contact_line
    if not contact_rows and contact_line:
        fallback = " | ".join([escape(str(x)) for x in contact_line if str(x).strip()])
        if fallback.strip():
            contact_rows.append(fallback)

    if contact_rows:
        html.append(f"<div class='contact-line'>{'<br/>'.join(contact_rows)}</div>")

    if summary:
        html.append(f"<div class='section-title'>{L_SUMMARY}</div>")
        html.append(f"<div class='experience-description'>{fmt_field(clean(summary), show_missing)}</div>")

    if skills:
        html.append(f"<div class='section-title'>{L_SKILLS}</div>")
        html.append(f"<div class='experience-description'>{fmt_field(clean(join_slash(skills)), show_missing)}</div>")

    if experience_sorted:
        html.append(f"<div class='section-title'>{L_EXPERIENCE}</div>")
        for exp in experience_sorted:
            company = clean(exp.get("company", ""))
            date_range = clean(exp.get("date_range", ""))
            title = clean(exp.get("title", ""))
            location = clean(exp.get("location", ""))
            achievements = exp.get("achievements", []) or []
            achievements = [strip_missing(a) if export_clean else a for a in achievements]

            html.append("<table class='timeline-table'>")
            html.append("<tr>")
            html.append(f"<td class='company-name'>{fmt_field(company, show_missing)}</td>")
            html.append(f"<td class='date-range'>{fmt_field(date_range, show_missing)}</td>")
            html.append("</tr>")
            html.append("</table>")

            html.append("<table class='subrow-table'>")
            html.append("<tr>")
            html.append(f"<td class='job-title'>{fmt_field(title, show_missing)}</td>")
            html.append(f"<td class='location'>{fmt_field(location, show_missing)}</td>")
            html.append("</tr>")
            html.append("</table>")

            html.append(f"<div class='experience-description'>{fmt_field(join_slash(achievements), show_missing)}</div>")

    if education:
        html.append(f"<div class='section-title'>{L_EDU}</div>")
        for edu in education:
            line = clean(edu.get("line", ""))
            details = clean(edu.get("details", ""))
            txt = (f"{line} / {details}").strip(" /")
            html.append(f"<div class='experience-description'>{fmt_field(txt, show_missing)}</div>")

    return "\n".join(html)

def parse_matrix_from_pdf(cv_text: str) -> dict:
    """
    Fallback melhorado:
    - pega nome (linha 1)
    - tenta pegar phone e URLs nas primeiras 20 linhas
    - tenta parsear experiências se tiver "Title | Company | DateRange | Location"
    - se não achar experiences, segue com raw_cv_text para o Gemini inferir (sem inventar)
    """
    lines = [ln.strip() for ln in (cv_text or "").splitlines() if ln.strip()]
    if not lines:
        return {}

    name = lines[0]
    top = lines[:20]
    links = []
    phone = ""

    for ln in top:
        found_urls = re.findall(r"https?://\S+", ln)
        for u in found_urls:
            u = u.strip().rstrip(").,;")
            if u not in links:
                links.append(u)

        if not phone and re.search(r"\+\d", ln):
            m = re.search(r"\+\d[\d\s\(\)\-\.]{7,}", ln)
            if m:
                phone = m.group(0).strip()

    header = {
        "name": name,
        "phone": phone,
        "links": links,
        "contact_line": []  # compatibilidade
    }

    experiences = []
    i = 0
    while i < len(lines):
        ln = lines[i]
        if " | " in ln and DATE_RE.search(ln):
            parts = [p.strip() for p in ln.split("|")]
            title = parts[0] if len(parts) > 0 else ""
            company = parts[1] if len(parts) > 1 else ""
            date_range = parts[2] if len(parts) > 2 else ""
            location = parts[3] if len(parts) > 3 else ""

            j = i + 1
            chunk = []
            while j < len(lines):
                nxt = lines[j]
                if " | " in nxt and DATE_RE.search(nxt):
                    break
                chunk.append(nxt)
                j += 1

            achievements_raw = " ".join(chunk)
            experiences.append({
                "company": company,
                "date_range": date_range,
                "title": title,
                "location": location,
                "achievements_raw": achievements_raw
            })
            i = j
        else:
            i += 1

    return {
        "header": header,
        "summary": "",
        "experiences": experiences,
        "education": [],
        "skills_raw": "",
        "raw_cv_text": cv_text
    }

def build_prompt(matrix: dict, job_description: str, company_description: str, lang: str) -> str:
    target_lang = "pt-BR" if lang == "pt-BR" else "en-US"

    matrix = matrix or {}
    experiences = matrix.get("experiences", []) or []
    has_matrix_exps = len(experiences) > 0
    raw_cv_text = matrix.get("raw_cv_text", "") or ""

    matrix_json = json.dumps(matrix, ensure_ascii=False)

    coverage_block = ""
    coverage_schema = ""
    if has_matrix_exps:
        coverage_block = """
- CRITICAL: Do not drop experiences.
  - The matrix contains experiences with exp_id.
  - Your output MUST include EVERY exp_id exactly once.
  - Do not merge, do not remove, do not invent new roles.
  - You may reorder experiences only by relevance, but must include all items.
"""
        coverage_schema = """
  ,
  "experience_coverage": {
    "expected_exp_ids": ["string"],
    "output_exp_ids": ["string"],
    "missing_exp_ids": ["string"]
  }
"""
    else:
        coverage_block = """
- The matrix may not contain structured experiences.
  - In that case, infer experience entries from raw_cv_text (do NOT invent new companies/dates).
  - If dates/companies are unclear, use "MISSING — ..." and add to missing_info.
"""
        coverage_schema = ""

    return f"""
Return ONLY a valid JSON object (no markdown, no backticks, no commentary).

Language rule:
- If the job description is in Portuguese, write everything in pt-BR.
- If the job description is in English, write everything in en-US.

Hard rules:
- Use the matrix as the primary source of truth. Do NOT invent companies, dates, titles, degrees, certifications, or metrics.
- If matrix/header has URLs (LinkedIn/GitHub/portfolio), put them in cv.header.links.
- If matrix/header has a phone number, put it in cv.header.phone.
{coverage_block}

Missing info rule:
- If any field is missing/unclear:
  (a) put a placeholder in the CV field exactly like: "MISSING — <what to add>"
  (b) add an entry to missing_info with field path, why it matters, and an example input.
- Keep missing_info <= 10 items (most important only).

Use simple, direct wording. Avoid buzzword stuffing.
Achievements: 3–6 per role, one line each, impact-focused, tailored to job keywords.

JSON schema:
{{
  "cv": {{
    "header": {{
      "name": "string",
      "phone": "string",
      "links": ["string"],
      "contact_line": ["string"]
    }},
    "summary": "string",
    "skills": ["string"],
    "experience": [
      {{
        "exp_id": "string",
        "company": "string",
        "date_range": "string",
        "title": "string",
        "location": "string",
        "relevance": "high|other",
        "achievements": ["string"]
      }}
    ],
    "education": [
      {{ "line": "string", "details": "string" }}
    ]
  }},
  "analysis_md": "string",
  "missing_info": [
    {{
      "field": "string (e.g., cv.experience[1].date_range)",
      "why_it_matters": "string",
      "suggested_input_example": "string"
    }}
  ]{coverage_schema}
}}

Authoritative input matrix (JSON):
{matrix_json}

raw_cv_text (if present; use only to infer structure when matrix lacks experiences):
{raw_cv_text}

Target job description:
{job_description}

Company description:
{company_description}

Write everything in: {target_lang}
""".strip()

# =========================
# 4) UI
# =========================
st.markdown("<h1 style='text-align:center;'>🚀 Gerador de Currículo Inteligente</h1>", unsafe_allow_html=True)

_, center_col, _ = st.columns([1, 2, 1])

with center_col:
    st.subheader("1) Matriz (fonte de verdade)")
    matrix_json_file = st.file_uploader("Upload da MATRIZ (JSON) — recomendado", type=["json"])
    matrix_pdf_file = st.file_uploader("OU upload do CV (PDF) como matriz (fallback)", type=["pdf"])

    st.subheader("2) Alvo")
    job_description = st.text_area("Descrição da vaga alvo:", height=220)
    company_description = st.text_area("Descrição da empresa (opcional):", height=140)

    st.subheader("3) Saída")
    show_missing = st.toggle("Mostrar 'MISSING — ...' no preview", value=True)
    export_final = st.toggle("Exportar versão FINAL (remove 'MISSING')", value=False)
    enforce_validation = st.toggle("Bloquear se a matriz estiver inválida (experiences/exp_id)", value=False)

    btn_gerar = st.button("Gerar Currículo e Análise", use_container_width=True)

if "data" not in st.session_state:
    st.session_state.data = None
if "debug" not in st.session_state:
    st.session_state.debug = {}

def load_matrix() -> dict:
    if matrix_json_file is not None:
        raw = matrix_json_file.read().decode("utf-8")
        return json.loads(raw)

    if matrix_pdf_file is not None:
        cv_text = extract_pdf_text(matrix_pdf_file)
        if len(cv_text) < 80:
            raise ValueError("Não consegui extrair texto suficiente do PDF. Se for escaneado (imagem), precisa OCR.")
        return parse_matrix_from_pdf(cv_text)

    return {}

# =========================
# 5) LÓGICA DE GERAÇÃO
# =========================
if btn_gerar:
    if not job_description.strip():
        st.warning("Cole a descrição da vaga.")
        st.stop()

    try:
        matrix = load_matrix()
        matrix = normalize_matrix(matrix)

        # Validação "aberta": não bloqueia por padrão
        has_exps = bool(matrix.get("experiences"))
        if not has_exps:
            msg = ("Sua matriz não tem experiences[]. Vou continuar SEM travar, mas não consigo garantir "
                   "que todas as experiências serão respeitadas. Recomendo enviar uma MATRIZ JSON com experiences[].")
            if enforce_validation:
                st.error(msg)
                st.stop()
            else:
                st.warning(msg)

        expected_ids = [e.get("exp_id") for e in (matrix.get("experiences") or []) if e.get("exp_id")]
        if has_exps and not expected_ids:
            msg = "Não encontrei exp_id na matriz. Vou continuar sem validação de cobertura."
            if enforce_validation:
                st.error(msg)
                st.stop()
            else:
                st.warning(msg)

        lang = detect_language(job_description)
        prompt = build_prompt(matrix, job_description, company_description or "", lang)

        with st.spinner("Gerando com Gemini..."):
            resp = client.models.generate_content(
                model="gemini-2.0-flash",
                contents=prompt
            )
        raw = get_response_text(resp).strip()
        data = extract_json_loose(raw)

        # Só valida cobertura se existir expected_ids
        cv_exps = (data.get("cv", {}) or {}).get("experience", []) or []
        output_ids = [e.get("exp_id") for e in cv_exps if e.get("exp_id")]

        if expected_ids:
            cov = validate_coverage(expected_ids, output_ids)
            if cov["missing"]:
                msg = f"⚠️ O modelo omitiu experiências da matriz: {cov['missing']}"
                if enforce_validation:
                    st.error(msg)
                    with st.expander("Debug (resposta bruta)"):
                        st.text(raw[:6000])
                    st.stop()
                else:
                    st.warning(msg)

            if cov["extra"]:
                st.warning(f"⚠️ O modelo retornou exp_id não existente na matriz: {cov['extra']}")
        else:
            st.info("Validação de cobertura ignorada (sem expected_exp_ids).")

        st.session_state.data = data
        st.session_state.debug = {
            "lang": lang,
            "has_experiences_in_matrix": has_exps,
            "expected_exp_ids": expected_ids,
            "output_exp_ids": output_ids,
            "raw_len": len(raw),
        }

    except Exception as e:
        st.session_state.data = None
        st.error(f"Erro: {e}")

# =========================
# 6) EXIBIÇÃO
# =========================
if st.session_state.data:
    data = st.session_state.data
    lang = st.session_state.debug.get("lang", "en")

    cv = data.get("cv", {}) or {}
    analysis_md = data.get("analysis_md", "") or ""
    missing_info = data.get("missing_info", []) or []

    clean_html = render_cv_html(cv, lang=lang, show_missing=show_missing, export_clean=export_final)
    full_doc = f"<html><head><meta charset='UTF-8'>{CV_CSS}</head><body><div class='cv-paper'>{clean_html}</div></body></html>"

    st.divider()
    components.html(full_doc, height=1000, scrolling=True)

    c1, c2 = st.columns(2)
    with c1:
        st.download_button(
            label="📥 Baixar Currículo (.doc) — HTML para Word",
            data=full_doc,
            file_name="Curriculo.doc",
            mime="application/msword",
            use_container_width=True
        )
    with c2:
        st.download_button(
            label="📥 Baixar Saída JSON (auditoria)",
            data=json.dumps(data, ensure_ascii=False, indent=2),
            file_name="saida_gemini.json",
            mime="application/json",
            use_container_width=True
        )

    st.divider()
    st.subheader("📊 Relatório / Preparação para Entrevista")
    st.markdown(analysis_md if analysis_md else "_(sem análise)_")

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
        if "experience_coverage" in data:
            st.json(data.get("experience_coverage", {}))
