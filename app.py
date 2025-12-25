import streamlit as st
from google import genai
from PyPDF2 import PdfReader

st.set_page_config(page_title="Portal de Carreira IA", layout="wide")

# Chave (o client pega do env GEMINI_API_KEY também, mas aqui mantemos Streamlit secrets)
if "GOOGLE_API_KEY" not in st.secrets:
    st.error("Configure a chave nos Secrets!")
    st.stop()

client = genai.Client(api_key=st.secrets["GOOGLE_API_KEY"])

st.title("🚀 Gerador de CV Inteligente")

uploaded_file = st.file_uploader("Suba seu CV em PDF", type="pdf")
job_description = st.text_area("Descrição da vaga:")

if st.button("Gerar"):
    if uploaded_file and job_description:
        with st.spinner("Processando..."):
            try:
                reader = PdfReader(uploaded_file)
                cv_text = "".join([(p.extract_text() or "") for p in reader.pages]).strip()

                if not cv_text:
                    st.error("Não consegui extrair texto do PDF (parece escaneado/imagem). Tente um PDF com texto ou rode OCR.")
                    st.stop()

                prompt = f"""
Você é um especialista em ATS e recrutamento.
Tarefa: otimizar o CV para a vaga mantendo a verdade (não invente experiência).

CV:
{cv_text}

Vaga:
{job_description}

Saída:
1) Versão otimizada do CV (bem formatada)
2) Lista de mudanças aplicadas (bullet points)
3) Palavras-chave faltantes que o candidato deveria cobrir (sem mentir)
"""

                response = client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=prompt
                )
                st.markdown(response.text)

            except Exception as e:
                st.error(f"Erro: {e}")
