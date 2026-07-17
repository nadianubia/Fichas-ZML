import streamlit as st
import pandas as pd
from fpdf import FPDF
import os

# Configuração da página para modo amplo (wide)
st.set_page_config(
    page_title="CASAL - Fichas Técnicas dos Sistemas",
    page_icon="🚰",
    layout="wide"
)

# Estilização CSS para os Cards na tela
st.markdown("""
    <style>
    .block-container { padding-top: 2rem; }
    .card {
        background-color: #f8f9fa;
        padding: 20px;
        border-radius: 10px;
        border-left: 5px solid #1F4E79;
        margin-bottom: 20px;
        box-shadow: 2px 2px 5px rgba(0,0,0,0.05);
    }
    .card-title { color: #1F4E79; font-weight: bold; margin-bottom: 10px; }
    </style>
""", unsafe_allow_html=True)

# Link da sua Planilha do Google (Substitua pelo link real da sua planilha!)
URL_PLANILHA = "https://docs.google.com/spreadsheets/d/1cUfZoPkVmiOivWXmRK4u3Vlp435f4_DeFzGvTFQOiNw/edit?gid=1077292522#gid=1077292522"

# Detecta a logo na pasta (suporta png, jpg ou jpeg)
LOGO_PATH = None
for ext in ['png', 'jpg', 'jpeg']:
    if os.path.exists(f"logo.{ext}"):
        LOGO_PATH = f"logo.{ext}"
        break

def converter_link_sheets(url):
    try:
        if "/edit" in url:
            return url.split("/edit")[0] + "/gviz/tq?tqx=out:csv&sheet="
        return url
    except:
        return url

base_url = converter_link_sheets(URL_PLANILHA)

@st.cache_data(ttl=60)
def carregar_dados():
    df_cap = pd.read_csv(base_url + "DADOS_CAPTACAO")
    df_eta = pd.read_csv(base_url + "DADOS_ETA_EEAB")
    df_poc = pd.read_csv(base_url + "DADOS_POCOS")
    try:
        df_adu = pd.read_csv(base_url + "ADUTORAS_INTERLIGACAO")
    except:
        df_adu = pd.DataFrame()
    return df_cap, df_eta, df_poc, df_adu

# --- FUNÇÃO PARA GERAR O PDF COM A LOGO ---
def gerar_pdf_ficha(municipio, df_c, df_e, df_p, df_a):
    pdf = FPDF()
    pdf.add_page()
    
    # Se a logo existir, insere ela no topo esquerdo do PDF
    if LOGO_PATH:
        # Insere a imagem (x=10, y=10, largura=35mm)
        pdf.image(LOGO_PATH, x=10, y=10, w=35)
        pdf.set_y(15)
        # Empurra o texto para o lado para não sobrepor a imagem
        pdf.set_x(50)
        pdf.set_font("Arial", "B", 14)
        pdf.cell(0, 8, "CASAL - COMPANHIA DE SANEAMENTO DE ALAGOAS", ln=True)
        pdf.set_x(50)
        pdf.set_font("Arial", "B", 12)
        pdf.cell(0, 8, f"FICHA TÉCNICA OPERACIONAL: {municipio}", ln=True)
    else:
        pdf.set_font("Arial", "B", 16)
        pdf.cell(0, 10, "CASAL - COMPANHIA DE SANEAMENTO DE ALAGOAS", ln=True, align="C")
        pdf.set_font("Arial", "B", 14)
        pdf.cell(0, 10, f"FICHA TÉCNICA OPERACIONAL: {municipio}", ln=True, align="C")
        
    pdf.ln(10)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(5)
    
    # Seção Captação
    if not df_c.empty:
        pdf.set_font("Arial", "B", 12)
        pdf.cell(0, 8, "1. DADOS DA CAPTAÇÃO SUPERFICIAL", ln=True)
        pdf.set_font("Arial", "", 10)
        for _, row in df_c.iterrows():
            pdf.cell(0, 6, f"Localidade/Sistema: {row.get('Localidade', '—')}", ln=True)
            pdf.cell(0, 6, f"Tipo de Captação: {row.get('Captação - Tipo', '—')} | Possui Crivo: {row.get('Captação - Possui Crivo', '—')}", ln=True)
            pdf.cell(0, 6, f"Adutora AB até EEAB: Diâmetro {row.get('Adutora AB até EEAB - Diâmetro (mm)', '—')}mm | Comp: {row.get('Adutora AB até EEAB - Comprimento (m)', '—')}m", ln=True)
            pdf.ln(2)
        pdf.ln(4)

    # Seção ETA / EEAB
    if not df_e.empty:
        pdf.set_font("Arial", "B", 12)
        pdf.cell(0, 8, "2. ESTAÇÃO DE TRATAMENTO DE ÁGUA (ETA / EEAB)", ln=True)
        pdf.set_font("Arial", "", 10)
        for _, row in df_e.iterrows():
            pdf.cell(0, 6, f"Localidade da ETA: {row.get('Localidade', '—')} | CC Equatorial: {row.get('CC Equatorial ETA', '—')}", ln=True)
            pdf.cell(0, 6, f"Bomba Principal: {row.get('EEAB - Tipo da Bomba Principal', '—')} | Potência: {row.get('EEAB - Potência Principal (cv)', '—')} cv", ln=True)
            pdf.cell(0, 6, f"Vazão: {row.get('EEAB - Vazão Principal (m³/h)', '—')} m³/h | Altura Manométrica: {row.get('EEAB - Altura Manométrica Principal (mca)', '—')} mca", ln=True)
            pdf.ln(2)
        pdf.ln(4)

    # Seção Adutoras Interligadas
    if not df_a.empty:
        dados_adu = df_a[(df_a['Município Origem'] == municipio) | (df_a['Município Destino'] == municipio)]
        if not dados_adu.empty:
            pdf.set_font("Arial", "B", 12)
            pdf.cell(0, 8, "3. SISTEMAS INTERLIGADOS / ADUTORAS DE EXPORTAÇÃO", ln=True)
            pdf.set_font("Arial", "", 10)
            for _, row in dados_adu.iterrows():
                pdf.cell(0, 6, f"Interligação: Origem {row['Município Origem']} -> Destino {row['Município Destino']}", ln=True)
                pdf.cell(0, 6, f"Nome: {row['Nome do Sistema Interligado']} | Diâmetro: {row['Diâmetro da Adutora (mm)']}mm", ln=True)
                pdf.ln(2)
            pdf.ln(4)

    # Seção Poços
    if not df_p.empty:
        pdf.set_font("Arial", "B", 12)
        pdf.cell(0, 8, "4. SISTEMA DE POÇOS ARTESIANOS", ln=True)
        for _, row in df_p.iterrows():
            pdf.set_font("Arial", "B", 10)
            pdf.cell(0, 6, f"• Poço: {row['Identificação do Poço']} ({row.get('Localidade/Região', '—')})", ln=True)
            pdf.set_font("Arial", "", 10)
            pdf.cell(0, 5, f"  Potência: {row.get('Potência da Bomba (cv)', '—')} cv | Altura: {row.get('Altura da Bomba (mca)', '—')} mca | Vazão: {row.get('Vazão (m³/h)', '—')} m³/h", ln=True)
            if 'Observações' in row and pd.notna(row['Observações']) and str(row['Observações']).strip() != "":
                pdf.cell(0, 5, f"  Obs: {row['Observações']}", ln=True)
            pdf.ln(1)
            
    return pdf.output()

try:
    df_captacao, df_eta_eeab, df_pocos, df_adutoras = carregar_dados()
    
    todos_municipios = sorted(list(set(
        df_captacao['Município'].dropna().unique().tolist() + 
        df_eta_eeab['Município'].dropna().unique().tolist() + 
        df_pocos['Município'].dropna().unique().tolist()
    )))

    # --- TOPONA DA TELA COM LOGO ---
    col_logo, col_titulo = st.columns([1, 4])
    
    with col_logo:
        if LOGO_PATH:
            st.image(LOGO_PATH, width=120)
            
    with col_titulo:
        st.title("FICHA TÉCNICA DOS SISTEMAS")
        st.subheader("CASAL - Companhia de Saneamento de Alagoas")

    st.markdown("---")

    # Filtros e Botão de PDF
    col_sel, col_btn = st.columns([3, 1])
    
    with col_sel:
        municipio_selecionado = st.selectbox(
            "🔍 Escolha o Município para visualizar os dados técnicos:", 
            todos_municipios
        )
    
    dados_cap = df_captacao[df_captacao['Município'] == municipio_selecionado]
    dados_eta = df_eta_eeab[df_eta_eeab['Município'] == municipio_selecionado]
    dados_poc = df_pocos[df_pocos['Município'] == municipio_selecionado]
    
    with col_btn:
        st.write("") 
        st.write("") 
        pdf_data = gerar_pdf_ficha(municipio_selecionado, dados_cap, dados_eta, dados_poc, df_adutoras)
        st.download_button(
            label="📥 Salvar Ficha em PDF",
            data=bytes(pdf_data),
            file_name=f"Ficha_Tecnica_{municipio_selecionado}.pdf",
            mime="application/pdf",
            use_container_width=True
        )

    st.write(f"Exibindo dados operacionais atuais para: **{municipio_selecionado}**")
    st.markdown("---")

    # --- INTERFACE ADAPTATIVA DO LAYOUT ---
    if not dados_cap.empty or not dados_eta.empty:
        st.header("🏢 Infraestrutura de Tratamento e Distribuição Superficial")
        col_cap, col_eta = st.columns(2)
        
        with col_cap:
            if not dados_cap.empty:
                st.markdown("<div class='card'><div class='card-title'>🪵 DADOS DA CAPTAÇÃO</div>", unsafe_allowed_color_html=True)
                for _, row in dados_cap.iterrows():
                    st.write(f"**Localidade/Sistema:** {row.get('Localidade', '—')}")
                    st.write(f"**Tipo de Captação:** {row.get('Captação - Tipo', '—')}")
                    st.write(f"**Possui Crivo:** {row.get('Captação - Possui Crivo', '—')} ({row.get('Captação - Material Crivo', '—')})")
                    st.write(f"**Adutora AB até EEAB:** Diâmetro {row.get('Adutora AB até EEAB - Diâmetro (mm)', '—')}mm | Comp: {row.get('Adutora AB até EEAB - Comprimento (m)', '—')}m")
                    st.markdown("---")
                st.markdown("</div>", unsafe_allowed_color_html=True)

        with col_eta:
            if not dados_eta.empty:
                st.markdown("<div class='card'><div class='card-title'>⚡ ESTAÇÃO DE TRATAMENTO DE ÁGUA (ETA / EEAB)</div>", unsafe_allowed_color_html=True)
                for _, row in dados_eta.iterrows():
                    st.write(f"**Localidade da ETA:** {row.get('Localidade', '—')}")
                    st.write(f"**CC Equatorial ETA:** {row.get('CC Equatorial ETA', '—')}")
                    st.write(f"**Bomba Principal:** {row.get('EEAB - Tipo da Bomba Principal', '—')} | Potência: {row.get('EEAB - Potência Principal (cv)', '—')} cv")
                    st.write(f"**Vazão e Altura:** {row.get('EEAB - Vazão Principal (m³/h)', '—')} m³/h | {row.get('EEAB - Altura Manométrica Principal (mca)', '—')} mca")
                    st.markdown("---")
                st.markdown("</div>", unsafe_allowed_color_html=True)

    if not df_adutoras.empty:
        dados_adu = df_adutoras[(df_adutoras['Município Origem'] == municipio_selecionado) | (df_adutoras['Município Destino'] == municipio_selecionado)]
        if not dados_adu.empty:
            st.header("🔗 Sistemas Interligados / Adutoras de Exportação")
            for _, row in dados_adu.iterrows():
                st.warning(f"🚨 **Atenção:** Sistema Interligado! Origem: {row['Município Origem']} ➔ Destino: {row['Município Destino']} | Diâmetro: {row['Diâmetro da Adutora (mm)']}mm")

    if not dados_poc.empty:
        st.header("🕳️ Sistema de Poços Artesianos (Captação Subterrânea)")
        cols_pocos = st.columns(3)
        for idx, (_, row) in enumerate(dados_poc.iterrows()):
            col_atual = cols_pocos[idx % 3]
            with col_atual:
                st.markdown(f"<div class='card'><div class='card-title'>📍 {row['Identificação do Poço']}</div>", unsafe_allowed_color_html=True)
                st.write(f"**Potência da Bomba:** {row.get('Potência da Bomba (cv)', '—')} cv")
                st.write(f"**Altura da Bomba:** {row.get('Altura da Bomba (mca)', '—')} mca")
                st.write(f"**Vazão Cadastrada:** {row.get('Vazão (m³/h)', '—')} m³/h")
                
                link_curva = row.get('Link/Arquivo Curva da Bomba', '')
                if pd.notna(link_curva) and str(link_curva).strip() != "" and str(link_curva).strip() != "—":
                    st.link_button("📊 Ver Curva da Bomba", str(link_curva))
                
                if 'Observações' in row and pd.notna(row['Observações']) and str(row['Observações']).strip() != "":
                    st.info(f"**Obs:** {row['Observações']}")
                st.markdown("</div>", unsafe_allowed_color_html=True)

except Exception as e:
    st.warning("Aguardando configuração da planilha de dados no código.")
