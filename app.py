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

# Estilização CSS para corrigir margens e criar os Cards visuais
st.markdown("""
    <style>
    .block-container { padding-top: 1rem; }
    .logo-container {
        display: flex;
        align-items: center;
        justify-content: center;
    }
    .card {
        background-color: #f8f9fa;
        padding: 20px;
        border-radius: 10px;
        border-left: 5px solid #1F4E79;
        margin-bottom: 20px;
        box-shadow: 2px 2px 5px rgba(0,0,0,0.05);
    }
    .card-title { color: #1F4E79; font-weight: bold; margin-bottom: 10px; font-size: 1.1rem; }
    </style>
""", unsafe_allow_html=True)

# Link da sua Planilha do Google (Troque caso mude o link da planilha original)
URL_PLANILHA = "COLOQUE_O_LINK_DA_SUA_PLANILHA_AQUI"

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

# Carrega as abas oficiais do projeto tratando colunas para maiúsculo para evitar erros de digitação
@st.cache_data(ttl=60)
def carregar_dados():
    try:
        df_cap = pd.read_csv(base_url + "DADOS_CAPTACAO")
        df_cap.columns = [c.strip().upper() for c in df_cap.columns]
    except:
        df_cap = pd.DataFrame(columns=['MUNICÍPIO'])
        
    try:
        df_eta = pd.read_csv(base_url + "DADOS_ETA_EEAB")
        df_eta.columns = [c.strip().upper() for c in df_eta.columns]
    except:
        df_eta = pd.DataFrame(columns=['MUNICÍPIO'])
        
    try:
        df_poc = pd.read_csv(base_url + "DADOS_POCOS")
        df_poc.columns = [c.strip().upper() for c in df_poc.columns]
    except:
        df_poc = pd.DataFrame(columns=['MUNICÍPIO'])
        
    try:
        df_adu = pd.read_csv(base_url + "ADUTORAS_INTERLIGACAO")
        df_adu.columns = [c.strip().upper() for c in df_adu.columns]
    except:
        df_adu = pd.DataFrame()
        
    return df_cap, df_eta, df_poc, df_adu

# --- FUNÇÃO PARA GERAR O PDF DINÂMICO ---
def gerar_pdf_ficha(municipio, df_c, df_e, df_p, df_a):
    pdf = FPDF()
    pdf.add_page()
    
    if LOGO_PATH:
        pdf.image(LOGO_PATH, x=10, y=10, w=30)
        pdf.set_y(12)
        pdf.set_x(45)
        pdf.set_font("Arial", "B", 13)
        pdf.cell(0, 7, "CASAL - COMPANHIA DE SANEAMENTO DE ALAGOAS", ln=True)
        pdf.set_x(45)
        pdf.set_font("Arial", "B", 11)
        pdf.cell(0, 7, f"FICHA TÉCNICA OPERACIONAL: {municipio.upper()}", ln=True)
    else:
        pdf.set_font("Arial", "B", 14)
        pdf.cell(0, 10, "CASAL - COMPANHIA DE SANEAMENTO DE ALAGOAS", ln=True, align="C")
        pdf.cell(0, 10, f"FICHA TÉCNICA OPERACIONAL: {municipio.upper()}", ln=True, align="C")
        
    pdf.ln(12)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(5)
    
    if not df_c.empty:
        pdf.set_font("Arial", "B", 11)
        pdf.cell(0, 7, "1. DADOS DA CAPTAÇÃO SUPERFICIAL", ln=True)
        pdf.set_font("Arial", "", 10)
        for _, row in df_c.iterrows():
            pdf.cell(0, 5.5, f"Localidade/Sistema: {row.get('LOCALIDADE', '—')}", ln=True)
            pdf.cell(0, 5.5, f"Tipo de Captação: {row.get('CAPTAÇÃO - TIPO', '—')} | Possui Crivo: {row.get('CAPTAÇÃO - POSSUI CRIVO', '—')}", ln=True)
            pdf.cell(0, 5.5, f"Adutora AB até EEAB: Diâmetro {row.get('ADUTORA AB ATÉ EEAB - DIÂMETRO (MM)', '—')}mm | Comprimento: {row.get('ADUTORA AB ATÉ EEAB - COMPRIMENTO (M)', '—')}m", ln=True)
            pdf.ln(1.5)
        pdf.ln(3)

    if not df_e.empty:
        pdf.set_font("Arial", "B", 11)
        pdf.cell(0, 7, "2. ESTAÇÃO DE TRATAMENTO DE ÁGUA (ETA / EEAB)", ln=True)
        pdf.set_font("Arial", "", 10)
        for _, row in df_e.iterrows():
            pdf.cell(0, 5.5, f"Localidade da ETA: {row.get('LOCALIDADE', '—')} | CC Equatorial: {row.get('CC EQUATORIAL ETA', '—')}", ln=True)
            pdf.cell(0, 5.5, f"Bomba Principal: {row.get('EEAB - TIPO DA BOMBA PRINCIPAL', '—')} | Potência: {row.get('EEAB - POTÊNCIA PRINCIPAL (CV)', '—')} cv", ln=True)
            pdf.cell(0, 5.5, f"Vazão: {row.get('EEAB - VAZÃO PRINCIPAL (M³/H)', '—')} m³/h | Altura Manométrica: {row.get('EEAB - ALTURA MANOMÉTRICA PRINCIPAL (MCA)', '—')} mca", ln=True)
            pdf.ln(1.5)
        pdf.ln(3)

    if not df_a.empty:
        col_origem = 'MUNICÍPIO ORIGEM' if 'MUNICÍPIO ORIGEM' in df_a.columns else 'MUNICIPIO ORIGEM'
        col_destino = 'MUNICÍPIO DESTINO' if 'MUNICÍPIO DESTINO' in df_a.columns else 'MUNICIPIO DESTINO'
        if col_origem in df_a.columns and col_destino in df_a.columns:
            dados_adu = df_a[(df_a[col_origem].astype(str).str.strip().str.upper() == municipio.upper()) | 
                             (df_a[col_destino].astype(str).str.strip().str.upper() == municipio.upper())]
            if not dados_adu.empty:
                pdf.set_font("Arial", "B", 11)
                pdf.cell(0, 7, "3. SISTEMAS INTERLIGADOS / ADUTORAS DE EXPORTAÇÃO", ln=True)
                pdf.set_font("Arial", "", 10)
                for _, row in dados_adu.iterrows():
                    pdf.cell(0, 5.5, f"Interligação: Origem {row.get(col_origem, '—')} -> Destino {row.get(col_destino, '—')}", ln=True)
                    pdf.cell(0, 5.5, f"Nome: {row.get('NOME DO SISTEMA INTERLIGADO', '—')} | Diâmetro: {row.get('DIÂMETRO DA ADUTORA (MM)', '—')}mm", ln=True)
                    pdf.ln(1.5)
                pdf.ln(3)

    if not df_p.empty:
        pdf.set_font("Arial", "B", 11)
        pdf.cell(0, 7, "4. SISTEMA DE POÇOS ARTESIANOS (SUBTERRÂNEO)", ln=True)
        for _, row in df_p.iterrows():
            id_p = row.get('IDENTIFICAÇÃO DO POÇO', row.get('IDENTIFICACAO DO POCO', '—'))
            loc_p = row.get('LOCALIDADE/REGIÃO', row.get('LOCALIDADE/REGIAO', '—'))
            pot_p = row.get('POTÊNCIA DA BOMBA (CV)', row.get('POTENCIA DA BOMBA (CV)', '—'))
            alt_p = row.get('ALTURA DA BOMBA (MCA)', row.get('ALTURA DA BOMBA (MCA)', '—'))
            vaz_p = row.get('VAZÃO (M³/H)', row.get('VAZAO (M³/H)', '—'))
            
            pdf.set_font("Arial", "B", 10)
            pdf.cell(0, 5.5, f"• Poço: {id_p} ({loc_p})", ln=True)
            pdf.set_font("Arial", "", 10)
            pdf.cell(0, 5, f"  Potência: {pot_p} cv | Altura Manométrica: {alt_p} mca | Vazão: {vaz_p} m³/h", ln=True)
            if 'OBSERVAÇÕES' in row and pd.notna(row['OBSERVAÇÕES']) and str(row['OBSERVAÇÕES']).strip() != "":
                pdf.cell(0, 5, f"  Obs: {row['OBSERVAÇÕES']}", ln=True)
            pdf.ln(1)
            
    return pdf.output()

try:
    df_captacao, df_eta_eeab, df_pocos, df_adutoras = carregar_dados()
    
    # Padronização de nomes das colunas de Município para evitar problemas de acentuação
    for df in [df_captacao, df_eta_eeab, df_pocos]:
        if 'MUNICIPIO' in df.columns and 'MUNICÍPIO' not in df.columns:
            df.rename(columns={'MUNICIPIO': 'MUNICÍPIO'}, inplace=True)
            
    # Junta e monta a lista de cidades únicas da sua planilha
    todos_muns = []
    for df in [df_captacao, df_eta_eeab, df_pocos]:
        if 'MUNICÍPIO' in df.columns:
            todos_muns.extend(df['MUNICÍPIO'].dropna().astype(str).str.strip().str.upper().unique().tolist())
            
    todos_municipios = sorted(list(set(todos_muns)))

    if not todos_municipios:
        st.warning("Nenhum município localizado nas tabelas da planilha. Verifique o preenchimento.")
        st.stop()

    # --- RENDERIZAÇÃO DO CABEÇALHO (LOGO ALINHADA) ---
    st.write("")
    col_logo, col_titulo = st.columns([1, 4])
    
    with col_logo:
        if LOGO_PATH:
            # st.image aplicada em container limpo para evitar cortes laterais
            st.markdown("<div class='logo-container'>", unsafe_allow_html=True)
            st.image(LOGO_PATH, width=130)
            st.markdown("</div>", unsafe_allow_html=True)
            
    with col_titulo:
        st.title("FICHA TÉCNICA DOS SISTEMAS")
        st.subheader("CASAL - Companhia de Saneamento de Alagoas")

    st.markdown("---")

    # --- BARRA DE FILTRO E BOTÃO DE IMPRESSÃO ---
    col_sel, col_btn = st.columns([3, 1])
    
    with col_sel:
        municipio_selecionado = st.selectbox(
            "🔍 Escolha o Município para visualizar os dados técnicos:", 
            todos_municipios
        )
    
    # Filtragem robusta ignorando espaços vazios e diferenças de caixa alta/baixa
    dados_cap = df_captacao[df_captacao['MUNICÍPIO'].astype(str).str.strip().str.upper() == municipio_selecionado] if 'MUNICÍPIO' in df_captacao.columns else pd.DataFrame()
    dados_eta = df_eta_eeab[df_eta_eeab['MUNICÍPIO'].astype(str).str.strip().str.upper() == municipio_selecionado] if 'MUNICÍPIO' in df_eta_eeab.columns else pd.DataFrame()
    dados_poc = df_pocos[df_pocos['MUNICÍPIO'].astype(str).str.strip().str.upper() == municipio_selecionado] if 'MUNICÍPIO' in df_pocos.columns else pd.DataFrame()
    
    with col_btn:
        st.write("") 
        st.write("") 
        # Geração do PDF sob demanda baseado no filtro selecionado
        pdf_data = gerar_pdf_ficha(municipio_selecionado, dados_cap, dados_eta, dados_poc, df_adutoras)
        st.download_button(
            label="📥 Salvar Ficha em PDF",
            data=bytes(pdf_data),
            file_name=f"Ficha_Tecnica_{municipio_selecionado.replace(' ', '_')}.pdf",
            mime="application/pdf",
            use_container_width=True
        )

    st.write(f"Exibindo dados operacionais atuais para: **{municipio_selecionado}**")
    st.markdown("---")

    # --- INTERFACE ADAPTATIVA DO PAINEL (Layout Dinâmico) ---
    
    # 1. Seção Superficial (Captação e ETA)
    if not dados_cap.empty or not dados_eta.empty:
        st.header("🏢 Infraestrutura de Tratamento e Distribuição Superficial")
        col_cap, col_eta = st.columns(2)
        
        with col_cap:
            if not dados_cap.empty:
                st.markdown("<div class='card'><div class='card-title'>🪵 DADOS DA CAPTAÇÃO</div>", unsafe_allow_html=True)
                for _, row in dados_cap.iterrows():
                    st.write(f"**Localidade/Sistema:** {row.get('LOCALIDADE', '—')}")
                    st.write(f"**Tipo de Captação:** {row.get('CAPTAÇÃO - TIPO', row.get('CAPTACAO - TIPO', '—'))}")
                    st.write(f"**Possui Crivo:** {row.get('CAPTAÇÃO - POSSUI CRIVO', row.get('CAPTACAO - POSSUI CRIVO', '—'))} ({row.get('CAPTAÇÃO - MATERIAL CRIVO', row.get('CAPTACAO - MATERIAL CRIVO', '—'))})")
                    st.write(f"**Adutora AB até EEAB:** Diâmetro {row.get('ADUTORA AB ATÉ EEAB - DIÂMETRO (MM)', row.get('ADUTORA AB ATE EEAB - DIAMETRO (MM)', '—'))} mm | Comprimento: {row.get('ADUTORA AB ATÉ EEAB - COMPRIMENTO (M)', row.get('ADUTORA AB ATE EEAB - COMPRIMENTO (M)', '—'))} m")
                    st.markdown("---")
                st.markdown("</div>", unsafe_allowed_color_html=True)

        with col_eta:
            if not dados_eta.empty:
                st.markdown("<div class='card'><div class='card-title'>⚡ ESTAÇÃO DE TRATAMENTO DE ÁGUA (ETA / EEAB)</div>", unsafe_allow_html=True)
                for _, row in dados_eta.iterrows():
                    st.write(f"**Localidade da ETA:** {row.get('LOCALIDADE', '—')}")
                    st.write(f"**CC Equatorial ETA:** {row.get('CC EQUATORIAL ETA', '—')}")
                    st.write(f"**Bomba Principal:** {row.get('EEAB - TIPO DA BOMBA PRINCIPAL', row.get('EEAB - TIPO DA BOMBA PRINCIPAL', '—'))} | Potência: {row.get('EEAB - POTÊNCIA PRINCIPAL (CV)', row.get('EEAB - POTENCIA PRINCIPAL (CV)', '—'))} cv")
                    st.write(f"**Vazão e Altura:** {row.get('EEAB - VAZÃO PRINCIPAL (M³/H)', row.get('EEAB - VAZAO PRINCIPAL (M³/H)', '—'))} m³/h | {row.get('EEAB - ALTURA MANOMÉTRICA PRINCIPAL (MCA)', row.get('EEAB - ALTURA MANOMETRICA PRINCIPAL (MCA)', '—'))} mca")
                    st.markdown("---")
                st.markdown("</div>", unsafe_allowed_color_html=True)

    # 2. Seção de Adutoras Interligadas Especiais
    if not df_adutoras.empty:
        c_origem = 'MUNICÍPIO ORIGEM' if 'MUNICÍPIO ORIGEM' in df_adutoras.columns else 'MUNICIPIO ORIGEM'
        c_destino = 'MUNICÍPIO DESTINO' if 'MUNICÍPIO DESTINO' in df_adutoras.columns else 'MUNICIPIO DESTINO'
        if c_origem in df_adutoras.columns and c_destino in df_adutoras.columns:
            dados_adu = df_adutoras[(df_adutoras[c_origem].astype(str).str.strip().str.upper() == municipio_selecionado) | 
                                 (df_adutoras[c_destino].astype(str).str.strip().str.upper() == municipio_selecionado)]
            if not dados_adu.empty:
                st.header("🔗 Sistemas Interligados / Adutoras de Exportação")
                for _, row in dados_adu.iterrows():
                    st.warning(f"🚨 **Atenção:** Sistema Interligado! Origem: {row[c_origem]} ➔ Destino: {row[c_destino]} | Diâmetro: {row.get('DIÂMETRO DA ADUTORA (MM)', row.get('DIAMETRO DA ADUTORA (MM)', '—'))}mm")

    # 3. Seção de Poços Artesianos
    if not dados_poc.empty:
        st.header("🕳️ Sistema de Poços Artesianos (Captação Subterrânea)")
        cols_pocos = st.columns(3)
        for idx, (_, row) in enumerate(dados_poc.iterrows():
            col_atual = cols_pocos[idx % 3]
            with col_atual:
                id_pocio = row.get('IDENTIFICAÇÃO DO POÇO', row.get('IDENTIFICACAO DO POCO', '—'))
                st.markdown(f"<div class='card'><div class='card-title'>📍 {id_pocio}</div>", unsafe_allow_html=True)
                st.write(f"**Região/Localidade:** {row.get('LOCALIDADE/REGIÃO', row.get('LOCALIDADE/REGIAO', '—'))}")
                st.write(f"**Potência da Bomba:** {row.get('POTÊNCIA DA BOMBA (CV)', row.get('POTENCIA DA BOMBA (CV)', '—'))} cv")
                st.write(f"**Altura da Bomba:** {row.get('ALTURA DA BOMBA (MCA)', row.get('ALTURA DA BOMBA (MCA)', '—'))} mca")
                st.write(f"**Vazão Cadastrada:** {row.get('VAZÃO (M³/H)', row.get('VAZAO (M³/H)', '—'))} m³/h")
                
                link_curva = row.get('LINK/ARQUIVO CURVA DA BOMBA', row.get('LINK/ARQUIVO CURVA DA BOMBA', ''))
                if pd.notna(link_curva) and str(link_curva).strip() != "" and str(link_curva).strip() != "—":
                    st.link_button("📊 Ver Curva da Bomba", str(link_curva))
                
                if 'OBSERVAÇÕES' in row and pd.notna(row['OBSERVAÇÕES']) and str(row['OBSERVAÇÕES']).strip() != "":
                    st.info(f"**Obs:** {row['OBSERVAÇÕES']}")
                st.markdown("</div>", unsafe_allow_html=True)

    if dados_cap.empty and dados_eta.empty and dados_poc.empty:
        st.info("Nenhuma estrutura localizada para este município nos registros da planilha.")

except Exception as e:
    st.error(f"Erro na leitura dos dados: {e}")
    st.warning("Verifique se o link da planilha foi configurado corretamente e se as abas contêm as colunas 'MUNICÍPIO'.")
