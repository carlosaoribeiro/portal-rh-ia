import re
import streamlit as st
from google import genai
from pypdf import PdfReader

# 1) CONFIGURAÇÃO DA PÁGINA
st.set_page_config(page_title="Gerador de CV Inteligente", layout="wide", page_icon="🚀")

# CSS para simular o layout SheetsResume/JNG e organizar a visualização vertical
st.markdown("""
    <style>
    /* Estilo do Papel A4 para o resultado */
    .cv-paper {
        background-color: white;
        padding: 40px 50px;
        border-radius: 2px;
        border: 1px solid #ddd;
        box-shadow: 5px 5px 15px rgba(0,0,0,0.1);
        color: #000;
        font-family: 'Times New Roman', serif;
        width: 100%;
        margin-top: 20px;
        line-height: 1.4;
    }
    /* Timeline: Empresa à esquerda, Data à direita */
    .timeline-row {
        display: flex;
        justify-content: space-between;
        align-items: baseline;
        font-weight: bold;
        margin-top: 12px;
        font-size: 1.1em;
    }
    .timeline-subrow {
        display: flex;
        justify-content: space-between;
        align-items: baseline;
        font-style: italic;
        margin-bottom: 5px;
    }
    /* Seções com borda inferior */
    .section-title {
        border-bottom: 1.5px solid #000;
        text-transform: uppercase;
        font-weight: bold;
        margin-top: 20px;
        margin-bottom: 5px;
        font-size: 1em;
    }
    /* Estilização para garantir que os inputs ocupem a largura total */
    .stTextArea textarea { font-size: 16px; }
    </style>
    """, unsafe_allow_html=True)

# 2) CONEXÃO API
if "GOOGLE_API_KEY" not in st.secrets:
    st.error("Erro: Configure a chave 'GOOGLE_API_KEY' nos Secrets do Streamlit!")
    st.stop()

client = genai.Client(api_key=st.secrets["GOOGLE_API_KEY"])

# ---------- Helpers ----------
def detect_language(text):
    text = (text or "").lower()
    pt_hits = len(re.findall(r"\b(de|da|o|a|com|vaga|requisitos|experiência|desenvolvimento)\b", text))
    en_hits = len(re.findall(r"\b(the|and|with|role|requirements|experience|development)\b", text))
    return "pt-BR" if pt_hits > en_hits else "en"

# 3) INTERFACE EM FLUXO VERTICAL (Resultado abaixo da Entrada)
st.title("🚀 Gerador de CV Inteligente")
st.caption("Ajuste seu currículo para o formato profissional **SheetsResume/JNG**.")

# Bloco de Entrada de Dados (Ocupando a largura total conforme solicitado)
st.subheader("📁 Dados de Entrada")
uploaded_file = st.file_uploader("Suba seu currículo atual (PDF)", type="pdf")
job_description = st.text_area("Descrição da vaga alvo:", height=250, placeholder="Cole os requisitos da vaga aqui (ex: MVVM, Kotlin, Coroutines)...")

# Inicializa o estado do resultado para persistência na tela
if "result" not in st.session_state:
    st.session_state.result = ""

# Botão de Ação (Largura total abaixo dos inputs)
if st.button("Gerar CV no Formato Referência", use_container_width=True):
    if uploaded_file and job_description.strip():
        with st.spinner("Analisando requisitos e formatando linha do tempo..."):
            try:
                # Extração segura de texto do PDF
                reader = PdfReader(uploaded_file)
                cv_text = ""
                for page in reader.pages:
                    content = page.extract_text()
                    if content:
                        cv_text += content
                
                if not cv_text.strip():
                    st.error("Não foi possível extrair texto do PDF. O arquivo pode ser uma imagem ou estar protegido.")
                    st.stop()

                lang = detect_language(job_description)

                # 4) PROMPT REFINADO PARA O LAYOUT JNG (Sem transição, foco em match técnico)
                prompt = f"""
                You are a senior tech recruiter and resume expert for the "SheetsResume/JNG" style.
                Output the optimized resume using HTML tags ONLY for structural alignment to ensure the dates stay on the right.
                
                STRICT RULES:
                1. HEADER: Name in Bold. Contact line with symbols '⬩'.
                2. NO SUMMARY: Start directly with the section 'WORK EXPERIENCE'.
                3. TIMELINE FORMAT (Mandatory HTML):
                   - For every company: <div class="timeline-row"><span>Company Name</span><span>Dates</span></div>
                   - For every title: <div class="timeline-subrow"><span>Job Title</span><span>Location</span></div>
                4. SECTION TITLES: Use <div class="section-title">SECTION NAME</div>.
                5. CONTENT MATCH: Focus on technical keywords from the job description (e.g., MVVM, Threading, Sensors). 
                   Maintain previous roles but describe them through the lens of technical delivery and architectural collaboration.
                
                Language of the output: {lang}.
                Original CV: {cv_text}
                Job Description Requirements: {job_description}
                """
                
                # Chamada ao motor Gemini 2.0 Flash
                response = client.models.generate_content(model="gemini-2.0-flash", contents=prompt)
                st.session_state.result = response.text
                st.success("✅ Currículo otimizado com sucesso!")
                
            except Exception as e:
                st.error(f"Erro no processamento: {e}")
    else:
        st.warning("⚠️ Certifique-se de subir o PDF e inserir a descrição da vaga.")

# 5) EXIBIÇÃO DO RESULTADO (Sempre posicionado abaixo dos controles)
if st.session_state.result:
    st.divider()
    st.subheader("✨ Resultado Otimizado")
    
    # Renderização do currículo no estilo "papel" com as classes de timeline
    st.markdown(f'<div class="cv-paper">{st.session_state.result}</div>', unsafe_allow_html=True)
    
    # Opção de Download para preservar a formatação
    st.download_button(
        label="📥 Baixar CV Ajustado (HTML/Texto)",
        data=st.session_state.result,
        file_name="cv_jng_otimizado.html",
        mime="text/html",
        use_container_width=True
    )

st.markdown("---")
st.caption("Ajustado para match técnico via IA. Revise os dados antes de enviar.")
