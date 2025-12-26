import streamlit as st
from google import genai
from pypdf import PdfReader

# 1. CONFIGURAÇÃO DA PÁGINA
st.set_page_config(page_title="Portal de Carreira IA", layout="wide", page_icon="🚀")

# 2. CONEXÃO COM A API
# O cliente busca a chave nos Secrets do Streamlit
if "GOOGLE_API_KEY" not in st.secrets:
    st.error("Erro: Configure a chave 'GOOGLE_API_KEY' nos Secrets do Streamlit!")
    st.stop()

client = genai.Client(api_key=st.secrets["GOOGLE_API_KEY"])

# 3. INTERFACE DO USUÁRIO
st.title("🚀 Gerador de CV Inteligente")
st.markdown("Ajuste seu currículo para dar match com os requisitos técnicos da vaga desejada.")

col1, col2 = st.columns([1, 1.2])

with col1:
    st.subheader("📁 Dados de Entrada")
    uploaded_file = st.file_uploader("Suba seu currículo atual (PDF)", type="pdf")
    
    job_description = st.text_area(
        "Descrição da vaga alvo (Requisitos Técnicos):", 
        height=300, 
        placeholder="Cole aqui a descrição da vaga..."
    )

with col2:
    st.subheader("✨ Resultado Otimizado")
    
    if st.button("Gerar CV com Match Técnico", use_container_width=True):
        if uploaded_file and job_description:
            with st.spinner("Analisando requisitos e alinhando experiências..."):
                try:
                    # Extração do texto do PDF
                    reader = PdfReader(uploaded_file)
                    cv_text = "".join([(p.extract_text() or "") for p in reader.pages]).strip()

                    if not cv_text:
                        st.error("Não foi possível extrair texto do PDF. Verifique se o arquivo não é uma imagem.")
                        st.stop()

                    # 4. PROMPT EVOLUÍDO (Match Técnico sem foco em Transição)
                    prompt = f"""
Você é um Tech Recruiter e Engenheiro Android Sênior.
Sua tarefa é ajustar o CV abaixo para que ele dê um "match" perfeito com os requisitos da vaga, sem mencionar "transição de carreira".

DIRETRIZES DE AJUSTE:
1. FOCO TÉCNICO IMEDIATO: No resumo (Summary), destaque as competências de Android Developer (Kotlin, Java, MVVM, Clean Architecture) como suas habilidades principais.
2. ALINHAMENTO DE EXPERIÊNCIA: 
   - Ajuste as descrições das experiências de desenvolvimento (como Oppia e Agiltec) para usar exatamente as mesmas palavras-chave e tecnologias mencionadas na vaga (ex: Threading, sensores, APIs específicas).
   - Nas experiências de gestão (Smiles, Brasilprev, etc.), mantenha o histórico, mas dê ênfase total à colaboração técnica, arquitetura de sistemas mobile e entrega de software, usando linguagem de engenharia.
3. TERMINOLOGIA DA VAGA: Identifique termos técnicos específicos na descrição da vaga e integre-os naturalmente nas suas responsabilidades anteriores onde houve contato com essas tecnologias.
4. ESTRUTURA: Mantenha o currículo profissional, limpo e formatado em Markdown pronto para ser copiado.

CV ORIGINAL:
{cv_text}

VAGA ALVO:
{job_description}

SAÍDA ESPERADA:
1) [CV AJUSTADO] - Versão pronta para envio com as experiências alinhadas tecnicamente.
2) [ANÁLISE DE MATCH] - Breve explicação de como as experiências foram conectadas aos requisitos da vaga.
3) [PONTOS DE ATENÇÃO] - Quais requisitos da vaga são muito específicos e podem exigir uma explicação mais detalhada na entrevista.
"""

                    # 5. CHAMADA AO MOTOR GEMINI
                    response = client.models.generate_content(
                        model="gemini-2.0-flash",
                        contents=prompt
                    )
                    
                    if response.text:
                        st.success("✅ Currículo ajustado com sucesso!")
                        
                        # Exibição do Markdown
                        st.markdown(response.text)
                        
                        # Botão de Download
                        st.download_button(
                            label="📥 Baixar CV Ajustado (TXT)",
                            data=response.text,
                            file_name="cv_ajustado_match.txt",
                            mime="text/plain",
                            use_container_width=True
                        )
                    
                except Exception as e:
                    st.error(f"Erro ao processar: {e}")
        else:
            st.warning("⚠️ Por favor, suba o PDF e cole a descrição da vaga.")

# RODAPÉ
st.markdown("---")
st.caption("Ajustado para match técnico via IA. Revise os dados antes de enviar.")
