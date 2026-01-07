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
# 3) REGEX / CONSTANTES
# =========================
MISSING_RE = re.compile(r"^MISSING\s—\s.+", re.IGNORECASE)

DATE_RE = re.compile(
    r"\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{4}\s*-\s*"
    r"(?:Present|(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{4})\b"
)

SECTION_START_RE = re.compile(r"^(work experience|experience|professional experience)$", re.IGNORECASE)
SECTION_END_RE = re.compile(r"^(education|skills|certifications|projects|languages|interests)$", re.IGNORECASE)

CERT_SECTION_RE = re.compile(r"^certifications,\s*skills\s*&\s*interests$", re.IGNORECASE)

# =========================
# 4) HELPERS
# =========================
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
    Extrai o PRIMEIRO objeto JSON válido da resposta.
    Corrige o erro "Extra data" quando o modelo devolve 2 JSONs ou JSON + texto.
    """
    text = (text or "").strip()
    text = re.sub(r"```(?:json)?", "", text, flags=re.IGNORECASE).strip("` \n\r\t")

    i = text.find("{")
    if i == -1:
        raise ValueError("Resposta não contém um objeto JSON (não achei '{').")

    decoder = json.JSONDecoder()
    obj, _end = decoder.raw_decode(text[i:])  # pega só o 1º JSON e ignora o resto
    return obj

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

def normalize_links(urls: list[str]) -> list[str]:
    out, seen = [], set()
    for u in (urls or []):
        u = (u or "").strip()
        if not u:
            continue
        u = u.rstrip(").,;]}>\"'")

        if u.startswith("www."):
            u = "https://" + u
        if u.startswith("linkedin.com") or u.startswith("github.com"):
            u = "https://" + u

        if not (u.startswith("http://") or u.startswith("https://")):
            continue

        key = u.lower()
        if key not in seen:
            out.append(u)
            seen.add(key)
    return out

def extract_links_from_text(text: str) -> list[str]:
    if not text:
        return []
    t = text.replace("https ://", "https://").replace("http ://", "http://")
    t = re.sub(r"(https?://)\s+", r"\1", t)
    t = t.replace("\n", " ")
    t = re.sub(r"\s+", " ", t)

    urls = []
    urls += re.findall(r"https?://[^\s]+", t)
    urls += re.findall(r"\b(?:www\.[^\s]+|linkedin\.com/[^\s]+|github\.com/[^\s]+)\b", t, flags=re.IGNORECASE)
    return normalize_links(urls)

def extract_phone_from_text(text: str) -> str:
    if not text:
        return ""
    t = text.replace("\n", " ")
    m = re.search(r"\+\d[\d\s\(\)\-\.]{7,}", t)
    return m.group(0).strip() if m else ""

def extract_cert_skills_interests(lines: list[str]) -> dict:
    if not lines:
        return {}

    start = None
    for i, ln in enumerate(lines):
        if CERT_SECTION_RE.match(ln.strip()):
            start = i + 1
            break
    if start is None:
        return {}

    chunk = []
    for j in range(start, len(lines)):
        ln = lines[j].strip()
        if not ln:
            continue

        if len(ln) <= 40 and ln.isupper() and j > start + 1:
            break

        chunk.append(ln)

    if not chunk:
        return {}

    text = " ".join(chunk)
    text = re.sub(r"\s+", " ", text)

    def grab(label: str) -> str:
        m = re.search(
            rf"{label}\s*:\s*(.*?)(?=(Certifications|Skills|Interests)\s*:|$)",
            text, re.IGNORECASE
        )
        return m.group(1).strip() if m else ""

    certs = grab("Certifications")
    skills = grab("Skills")
    interests = grab("Interests")

    cert_list = []
    if certs:
        for part in re.split(r"[;•]", certs):
            p = part.strip(" ;,-")
            if p:
                cert_list.append(p)

    interest_list = []
    if interests:
        for part in re.split(r"[;•,]", interests):
            p = part.strip(" ;,-")
            if p:
                interest_list.append(p)

    return {
        "certifications": cert_list,
        "skills_raw": skills,
        "interests": interest_list
    }

def normalize_matrix(matrix: dict) -> dict:
    matrix = matrix or {}

    if "experiences" not in matrix:
        for k in ("experience", "work_experience", "jobs"):
            if k in matrix and isinstance(matrix.get(k), list):
                matrix["experiences"] = matrix.get(k) or []
                break

    if "header" not in matrix or not isinstance(matrix.get("header"), dict):
        matrix["header"] = {}
    header = matrix["header"]

    cl = header.get("contact_line", [])
    if isinstance(cl, str):
        cl = [cl]
    header["contact_line"] = [str(x).strip() for x in (cl or []) if str(x).strip()]

    links = header.get("links", [])
    if isinstance(links, str):
        links = [links]
    header["links"] = normalize_links([str(x).strip() for x in (links or [])])

    header["phone"] = str(header.get("phone", "") or "").strip()
    matrix["header"] = header

    certs = matrix.get("certifications", [])
    if isinstance(certs, str):
        certs = [certs]
    matrix["certifications"] = [str(x).strip() for x in (certs or []) if str(x).strip()]

    interests = matrix.get("interests", [])
    if isinstance(interests, str):
        interests = [interests]
    matrix["interests"] = [str(x).strip() for x in (interests or []) if str(x).strip()]

    matrix["skills_raw"] = str(matrix.get("skills_raw", "") or "").strip()

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

def slice_experience_section(lines: list[str]) -> list[str]:
    if not lines:
        return lines

    start = None
    for i, ln in enumerate(lines):
        if SECTION_START_RE.match(ln.strip()):
            start = i + 1
            break
    if start is None:
        return lines

    end = None
    for j in range(start, len(lines)):
        if SECTION_END_RE.match(lines[j].strip()):
            end = j
            break

    return lines[start:end] if end else lines[start:]

def parse_experiences_from_lines(lines: list[str]) -> list[dict]:
    exps = []
    i = 0
    while i < len(lines):
        ln = lines[i]

        if DATE_RE.search(ln):
            date_range = DATE_RE.search(ln).group(0).strip()

            j = i + 1
            chunk = []
            while j < len(lines) and not DATE_RE.search(lines[j]):
                chunk.append(lines[j])
                j += 1

            title = company = location = ""
            if "|" in ln:
                parts = [p.strip() for p in ln.split("|") if p.strip()]
                parts_no_date = [p for p in parts if date_range not in p]
                if len(parts_no_date) >= 1:
                    title = parts_no_date[0]
                if len(parts_no_date) >= 2:
                    company = parts_no_date[1]
                if len(parts_no_date) >= 3:
                    location = parts_no_date[2]

            achievements_raw = " ".join([c for c in chunk if c.strip()])
            exps.append({
                "company": company,
                "date_range": date_range,
                "title": title,
                "location": location,
                "achievements_raw": achievements_raw
            })
            i = j
        else:
            i += 1
    return exps

def parse_matrix_from_pdf(cv_text: str) -> dict:
    lines = [ln.strip() for ln in (cv_text or "").splitlines() if ln.strip()]
    if not lines:
        return {}

    name = lines[0]
    links = extract_links_from_text(cv_text)
    phone = extract_phone_from_text(cv_text)

    extras = extract_cert_skills_interests(lines)

    header = {
        "name": name,
        "phone": phone,
        "links": links,
        "contact_line": []
    }

    exp_lines = slice_experience_section(lines)
    experiences = parse_experiences_from_lines(exp_lines)

    return {
        "header": header,
        "summary": "",
        "experiences": experiences,
        "education": [],
        "skills_raw": extras.get("skills_raw", ""),
        "certifications": extras.get("certifications", []),
        "interests": extras.get("interests", []),
        "raw_cv_text": cv_text
    }

def analysis_sections(lang: str) -> str:
    if lang == "pt-BR":
        return """
analysis_md must be Markdown and MUST include these sections with bullet points:

## Resumo de Aderência (3 bullets)
## Principais Forças (5 bullets)
## Lacunas / Informações Faltantes (bullets; referencie missing_info)
## Preparação para Entrevista (10 bullets: pergunta + resposta sugerida)
## Cobertura de Palavras-chave (10 keywords da vaga + onde aparecem no CV)
""".strip()
    return """
analysis_md must be Markdown and MUST include these sections with bullet points:

## Fit Summary (3 bullets)
## Key Strengths (5 bullets)
## Gaps / Missing Info (bullets; reference missing_info)
## Interview Prep (10 bullets: question + suggested answer)
## Keyword Coverage (10 keywords from the job description + where they appear)
""".strip()

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
- analysis_md must be written in the SAME language.

Hard rules:
- Use the matrix as the primary source of truth. Do NOT invent companies, dates, titles, degrees, certifications, or metrics.
- If matrix.header has URLs, put them in cv.header.links.
- If matrix.header has a phone number, put it in cv.header.phone.
- If matrix.certifications exists, include them in cv.certifications (do not drop).
- If matrix.interests exists, include them in cv.interests (do not drop).
- If matrix.skills_raw exists, convert it into cv.skills (split into items).
{coverage_block}

Missing info rule:
- If any field is missing/unclear:
  (a) put a placeholder in the CV field exactly like: "MISSING — <what to add>"
  (b) add an entry to missing_info with field path, why it matters, and an example input.
- Keep missing_info <= 10 items.

Style:
- Use simple, direct wording.
- Avoid buzzword stuffing.
- Achievements: 3–6 per role, one line each, impact-focused, tailored to job keywords.

{analysis_sections(lang)}

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
    "certifications": ["string"],
    "interests": ["string"],
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
      "field": "string",
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

def render_cv_html(cv: dict, lang: str, show_missing: bool = True, export_clean: bool = False) -> str:
    cv = cv or {}
    header = cv.get("header", {}) or {}

    name = header.get("name", "") or ""
    phone = header.get("phone", "") or ""
    links = header.get("links", []) or []
    contact_line = header.get("contact_line", []) or []

    if isinstance(contact_line, str):
        contact_line = [contact_line]

    if not phone:
        phone = extract_phone_from_text(" ".join([str(x) for x in contact_line]))
    if not links:
        links = extract_links_from_text(" ".join([str(x) for x in contact_line]))

    summary = cv.get("summary", "") or ""
    skills = cv.get("skills", []) or []
    certifications = cv.get("certifications", []) or []
    interests = cv.get("interests", []) or []
    education = cv.get("education", []) or []
    experience = cv.get("experience", []) or []

    if lang == "pt-BR":
        L_SUMMARY, L_SKILLS, L_EXPERIENCE, L_EDU = "Resumo", "Skills", "Experiência", "Educação"
        L_CERTS, L_INTERESTS = "Certificações", "Interesses"
    else:
        L_SUMMARY, L_SKILLS, L_EXPERIENCE, L_EDU = "Summary", "Skills", "Experience", "Education"
        L_CERTS, L_INTERESTS = "Certifications", "Interests"

    def clean(v: str) -> str:
        return strip_missing(v) if export_clean else (v or "")

    def rel_key(x):
        return 0 if x.get("relevance") == "high" else 1
    experience_sorted = sorted(experience, key=rel_key)

    html = []
    html.append(f"<h1>{fmt_field(clean(name), show_missing)}</h1>")

    contact_rows = []
    if phone:
        contact_rows.append(fmt_field(clean(phone), show_missing))

    links = normalize_links(links)
    if links:
        link_html = " | ".join([
            f"<a href='{escape(u)}' target='_blank'>{escape(u)}</a>"
            for u in links if str(u).strip()
        ])
        if link_html.strip():
            contact_rows.append(link_html)

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

    if certifications:
        certs_join = " / ".join([c for c in certifications if str(c).strip()])
        if certs_join.strip():
            html.append(f"<div class='section-title'>{L_CERTS}</div>")
            html.append(f"<div class='experience-description'>{fmt_field(clean(certs_join), show_missing)}</div>")

    if interests:
        interests_join = " / ".join([i for i in interests if str(i).strip()])
        if interests_join.strip():
            html.append(f"<div class='section-title'>{L_INTERESTS}</div>")
            html.append(f"<div class='experience-description'>{fmt_field(clean(interests_join), show_missing)}</div>")

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

# =========================
# 5) UI
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
    show_debug = st.toggle("Mostrar Debug", value=False)

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
# 6) GERAÇÃO
# =========================
if btn_gerar:
    if not job_description.strip():
        st.warning("Cole a descrição da vaga.")
        st.stop()

    try:
        matrix = load_matrix()
        matrix = normalize_matrix(matrix)

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

        with st.spinner("Processando suas informações..."):
            resp = client.models.generate_content(
                model="gemini-2.0-flash",
                contents=prompt
            )

        raw = get_response_text(resp).strip()

        try:
            data = extract_json_loose(raw)
        except Exception as e:
            st.error(f"Erro ao interpretar JSON do modelo: {e}")
            with st.expander("🔎 Resposta bruta do modelo (diagnóstico)"):
                st.text(raw[:9000])
            st.stop()

        cv_exps = (data.get("cv", {}) or {}).get("experience", []) or []
        output_ids = [e.get("exp_id") for e in cv_exps if e.get("exp_id")]

        if expected_ids:
            cov = validate_coverage(expected_ids, output_ids)
            if cov["missing"]:
                msg = f"⚠️ O modelo omitiu experiências da matriz: {cov['missing']}"
                if enforce_validation:
                    st.error(msg)
                    if show_debug:
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
            "matrix_header_links": (matrix.get("header", {}) or {}).get("links", []),
            "matrix_header_phone": (matrix.get("header", {}) or {}).get("phone", ""),
            "matrix_certifications": matrix.get("certifications", []),
            "matrix_skills_raw_len": len(matrix.get("skills_raw", "") or ""),
            "matrix_interests": matrix.get("interests", []),
        }

    except Exception as e:
        st.session_state.data = None
        st.error(f"Erro: {e}")

# =========================
# 7) EXIBIÇÃO
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

    if show_debug:
        with st.expander("🔎 Debug"):
            st.json(st.session_state.debug)
            if "experience_coverage" in data:
                st.json(data.get("experience_coverage", {}))
