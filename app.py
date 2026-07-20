import streamlit as st
import pandas as pd
from fpdf import FPDF
import os

# Configuração da página para modo amplo (wide)
st.set_page_config(
    page_title="CASAL - Fichas Técnicas dos Sistemas ZML",
    page_icon="🚰",
    layout="wide"
)

# Estilização CSS para corrigir margens, cores institucionais e criar os Cards visuais
st.markdown("""
    <style>
    .block-container { padding-top: 4rem; }
    
    .header-text-container {
        display: flex;
        flex-direction: column;
        justify-content: center;
        height: 100%;
        padding-left: 10px;
    }
    
    .titulo-principal {
        color: #1F4E79;
        font-size: 2.3rem;
        font-weight: bold;
        margin: 0;
        padding: 0;
        line-height: 1.2;
    }
    .subtitulo-principal {
        color: #006699; 
        font-size: 1.3rem;
        font-weight: bold;
        margin-top: 8px;
        padding: 0;
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

URL_PLANILHA = "https://docs.google.com/spreadsheets/d/1cUfZoPkVmiOivWXmRK4u3Vlp435f4_DeFzGvTFQOiNw/edit?gid=1107305555#gid=1107305555"

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

def dado_valido(valor):
    if pd.isna(valor) or str(valor).strip() == "" or str(valor).strip().lower() == "nan" or str(valor).strip() == "—":
        return False
    return True

def formatar_valor(valor):
    if not dado_valido(valor):
        return ""
    texto = str(valor).strip()
    if texto.endswith('.0'):
        return texto[:-2]
    return texto

def limpar_acentos(texto):
    if not texto: return ""
    import unicodedata
    return "".join(c for c in unicodedata.normalize('NFD', str(texto)) if unicodedata.category(c) != 'Mn')

def buscar_campo_mult(row, lista_colunas):
    for nome_col in lista_colunas:
        nome_norm = limpar_acentos(nome_col).upper().strip()
        for col in row.index:
            if limpar_acentos(col).upper().strip() == nome_norm:
                val = row.get(col)
                if dado_valido(val):
                    return val
    return None

@st.cache_data(ttl=60)
def carregar_dados():
    try:
        df_cap = pd.read_csv(base_url + "DADOS_CAPTACAO")
    except:
        df_cap = pd.DataFrame()
        
    try:
        df_eta = pd.read_csv(base_url + "DADOS_ETA_EEAB")
    except:
        df_eta = pd.DataFrame()
        
    try:
        df_poc = pd.read_csv(base_url + "DADOS_POCOS")
    except:
        df_poc = pd.DataFrame()
        
    try:
        df_adu = pd.read_csv(base_url + "ADUTORAS_INTERLIGACAO")
    except:
        df_adu = pd.DataFrame()
        
    return df_cap, df_eta, df_poc, df_adu

# --- GERADOR DE PDF ---
def gerar_pdf_ficha(municipio, df_c, df_e, df_p, df_a):
    pdf = FPDF()
    pdf.add_page()
    
    mun_limpo = limpar_acentos(municipio).upper()
    
    if LOGO_PATH:
        pdf.image(LOGO_PATH, x=10, y=10, w=30)
        pdf.set_y(12)
        pdf.set_x(45)
        pdf.set_font("Helvetica", "B", 13)
        pdf.cell(0, 7, "CASAL - COMPANHIA DE SANEAMENTO DE ALAGOAS", ln=True)
        pdf.set_x(45)
        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(0, 7, f"FICHA TECNICA DOS SISTEMAS ZML: {mun_limpo}", ln=True)
    else:
        pdf.set_font("Helvetica", "B", 14)
        pdf.cell(0, 10, "CASAL - COMPANHIA DE SANEAMENTO DE ALAGOAS", ln=True, align="C")
        pdf.cell(0, 10, f"FICHA TECNICA DOS SISTEMAS ZML: {mun_limpo}", ln=True, align="C")
        
    pdf.ln(12)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(5)
    
    if not df_c.empty:
        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(0, 7, "1. DADOS DA CAPTACAO SUPERFICIAL E ADUTORAS/EEAB", ln=True)
        pdf.set_font("Helvetica", "", 10)
        for _, row in df_c.iterrows():
            loc = buscar_campo_mult(row, ['Localidade'])
            tipo = buscar_campo_mult(row, ['Captação - Tipo', 'Tipo de Captação'])
            vaz = formatar_valor(buscar_campo_mult(row, ['EEAB - Vazão Principal (m³/h)', 'Vazão']))
            pot = formatar_valor(buscar_campo_mult(row, ['EEAB - Potência Principal (cv)']))
            alt = formatar_valor(buscar_campo_mult(row, ['EEAB - Altura Manométrica Principal (mca)']))
            
            if dado_valido(loc): pdf.cell(0, 5.5, f"Localidade/Sistema: {limpar_acentos(loc)}", ln=True)
            if dado_valido(tipo): pdf.cell(0, 5.5, f"Tipo de Captacao: {limpar_acentos(tipo)}", ln=True)
            if dado_valido(vaz): pdf.cell(0, 5.5, f"Vazao EEAB: {vaz} m3/h", ln=True)
            if dado_valido(pot) or dado_valido(alt): pdf.cell(0, 5.5, f"Potencia / Altura: {pot} cv | {alt} mca", ln=True)
            pdf.ln(1.5)
        pdf.ln(3)

    if not df_e.empty:
        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(0, 7, "2. ESTACAO DE TRATAMENTO DE AGUA (ETA)", ln=True)
        pdf.set_font("Helvetica", "", 10)
        for _, row in df_e.iterrows():
            loc_eta = buscar_campo_mult(row, ['Localidade'])
            cc_eta = formatar_valor(buscar_campo_mult(row, ['CC Equatorial ETA']))
            cc_eeab = formatar_valor(buscar_campo_mult(row, ['CC Equatorial EEAB']))
            obs_eta = buscar_campo_mult(row, ['OBSERVAÇÕES', 'Observações'])
            
            if dado_valido(loc_eta): pdf.cell(0, 5.5, f"Localidade da ETA: {limpar_acentos(loc_eta)}", ln=True)
            if dado_valido(cc_eeab): pdf.cell(0, 5.5, f"CC Equatorial EEAB: {cc_eeab}", ln=True)
            if dado_valido(cc_eta): pdf.cell(0, 5.5, f"CC Equatorial ETA: {cc_eta}", ln=True)
            if dado_valido(obs_eta): pdf.multi_cell(0, 5.5, f"Obs: {limpar_acentos(obs_eta)}")
            pdf.ln(1.5)
        pdf.ln(3)

    if not df_p.empty:
        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(0, 7, "3. SISTEMA DE POCOS ARTESIANOS (SUBTERRANEO)", ln=True)
        for _, row in df_p.iterrows():
            id_p = buscar_campo_mult(row, ['Identificação do Poço']) or 'Poco'
            pdf.set_font("Helvetica", "B", 10)
            pdf.cell(0, 5.5, f"Poco: {limpar_acentos(id_p)}", ln=True)
            pdf.set_font("Helvetica", "", 10)
            
            pot_b = formatar_valor(buscar_campo_mult(row, ['Potência da Bomba (cv)']))
            alt_b = formatar_valor(buscar_campo_mult(row, ['Altura da Bomba (mca)']))
            vaz_b = formatar_valor(buscar_campo_mult(row, ['Vazão (m³/h)']))
            
            detalhes = []
            if dado_valido(pot_b): detalhes.append(f"Potencia: {pot_b} cv")
            if dado_valido(alt_b): detalhes.append(f"Altura: {alt_b} mca")
            if dado_valido(vaz_b): detalhes.append(f"Vazao: {vaz_b} m3/h")
            if detalhes: pdf.cell(0, 5, "  " + " | ".join(detalhes), ln=True)
            pdf.ln(1)
            
    return pdf.output()

try:
    df_captacao, df_eta_eeab, df_pocos, df_adutoras = carregar_dados()
    
    def obter_municipios(df):
        if df.empty: return []
        for col in df.columns:
            if limpar_acentos(col).upper().strip() in ['MUNICIPIO', 'MUNICPIO ORIGEM', 'MUNICÍPIO']:
                return df[col].dropna().astype(str).str.strip().str.upper().unique().tolist()
        return []

    todos_muns = obter_municipios(df_captacao) + obter_municipios(df_eta_eeab) + obter_municipios(df_pocos)
    todos_municipios = sorted(list(set(todos_muns)))

    if not todos_municipios:
        st.warning("Nenhum município localizado nas tabelas da planilha. Verifique o preenchimento.")
        st.stop()

    # --- CABEÇALHO ---
    margem_esq, col_logo, col_texto, margem_dir = st.columns([1, 1.3, 5, 1])
    with col_logo:
        if LOGO_PATH: st.image(LOGO_PATH, width=140)
            
    with col_texto:
        st.markdown("""
            <div class='header-text-container'>
                <div class='titulo-principal'>FICHAS TÉCNICAS DOS SISTEMAS ZML</div>
                <div class='subtitulo-principal'>CASAL - Companhia de Saneamento de Alagoas</div>
            </div>
        """, unsafe_allow_html=True)

    st.markdown("---")

    col_sel, col_btn = st.columns([3, 1])
    with col_sel:
        municipio_selecionado = st.selectbox("🔍 Escolha o Município para visualizar os dados técnicos:", todos_municipios)
    
    def filtrar_por_municipio(df):
        if df.empty: return pd.DataFrame()
        col_real = None
        for c in df.columns:
            if limpar_acentos(c).upper().strip() in ['MUNICIPIO', 'MUNICÍPIO']:
                col_real = c
                break
        if col_real:
            return df[df[col_real].astype(str).str.strip().str.upper() == municipio_selecionado]
        return pd.DataFrame()

    dados_cap = filtrar_por_municipio(df_captacao)
    dados_eta = filtrar_por_municipio(df_eta_eeab)
    dados_poc = filtrar_por_municipio(df_pocos)
    
    with col_btn:
        st.write("") 
        st.write("") 
        try:
            pdf_out = gerar_pdf_ficha(municipio_selecionado, dados_cap, dados_eta, dados_poc, df_adutoras)
            pdf_bytes = bytes(pdf_out) if isinstance(pdf_out, (bytearray, bytes)) else pdf_out.encode('latin1', errors='ignore') if hasattr(pdf_out, 'encode') else b""
            
            st.download_button(
                label="📥 Salvar Ficha em PDF",
                data=pdf_bytes,
                file_name=f"Ficha_Tecnica_{municipio_selecionado.replace(' ', '_')}.pdf",
                mime="application/pdf",
                use_container_width=True
            )
        except Exception as pdf_err:
            st.error("Erro ao gerar PDF")

    st.write(f"Exibindo dados operacionais atuais para: **{municipio_selecionado}**")
    st.markdown("---")

    # --- EXIBIÇÃO NA TELA ---
    if not dados_cap.empty or not dados_eta.empty:
        st.header("🏢 Infraestrutura de Tratamento e Distribuição Superficial")
        col_cap, col_eta = st.columns(2)
        
        with col_cap:
            if not dados_cap.empty:
                st.markdown("<div class='card'><div class='card-title'>🪵 DADOS DA CAPTAÇÃO E ADUTORAS/EEAB</div>", unsafe_allow_html=True)
                for _, row in dados_cap.iterrows():
                    loc_c = buscar_campo_mult(row, ['Localidade'])
                    if dado_valido(loc_c): st.write(f"**Localidade/Sistema:** {loc_c}")
                    
                    tipo_cap = buscar_campo_mult(row, ['Captação - Tipo', 'Tipo de Captação'])
                    if dado_valido(tipo_cap): st.write(f"**Tipo de Captação:** {tipo_cap}")

                    vaz_cap = formatar_valor(buscar_campo_mult(row, ['EEAB - Vazão Principal (m³/h)', 'Vazão', 'Vazão da Captação']))
                    if dado_valido(vaz_cap): st.write(f"**Vazão:** {vaz_cap} m³/h")

                    bomba_cap = buscar_campo_mult(row, ['EEAB - Tipo da Bomba Principal', 'Tipo da Bomba'])
                    pot_cap = formatar_valor(buscar_campo_mult(row, ['EEAB - Potência Principal (cv)', 'Potência (cv)']))
                    if dado_valido(bomba_cap) or dado_valido(pot_cap):
                        txt_b = "**Bomba Elevatória (EEAB):**"
                        if dado_valido(bomba_cap): txt_b += f" {bomba_cap}"
                        if dado_valido(pot_cap): txt_b += f" | Potência: {pot_cap} cv"
                        st.write(txt_b)

                    alt_cap = formatar_valor(buscar_campo_mult(row, ['EEAB - Altura Manométrica Principal (mca)', 'Altura (mca)']))
                    if dado_valido(alt_cap): st.write(f"**Altura Manométrica:** {alt_cap} mca")
                    
                    crivo = buscar_campo_mult(row, ['Captação - Possui Crivo'])
                    mat_crivo = buscar_campo_mult(row, ['Captação - Material Crivo'])
                    diam_crivo = formatar_valor(buscar_campo_mult(row, ['Captação - Diâmetro Crivo (mm)']))
                    if dado_valido(crivo):
                        txt_c = f"**Possui Crivo:** {crivo}"
                        if dado_valido(diam_crivo): txt_c += f" ({diam_crivo} mm)"
                        if dado_valido(mat_crivo): txt_c += f" - {mat_crivo}"
                        st.write(txt_c)
                    
                    diam = formatar_valor(buscar_campo_mult(row, ['Adutora EEAB até ETA - Diâmetro (mm)', 'Adutora AB até EEAB - Diâmetro (mm)']))
                    comp = formatar_valor(buscar_campo_mult(row, ['Adutora EEAB até ETA - Comprimento (m)', 'Adutora AB até EEAB - Comprimento (m)']))
                    mat_adu = buscar_campo_mult(row, ['Adutora EEAB até ETA - Material', 'Adutora AB até EEAB - Material'])
                    if dado_valido(diam) or dado_valido(comp):
                        txt_adu = "**Adutora EEAB ➔ ETA:**"
                        if dado_valido(diam): txt_adu += f" Diâmetro {diam} mm"
                        if dado_valido(mat_adu): txt_adu += f" ({mat_adu})"
                        if dado_valido(comp): txt_adu += f" | Comprimento: {comp} m"
                        st.write(txt_adu)

                    obs_c = buscar_campo_mult(row, ['OBSERVAÇÕES', 'Observações', 'Obs'])
                    if dado_valido(obs_c): st.info(f"**Obs:** {obs_c}")

                    st.markdown("---")
                st.markdown("</div>", unsafe_allow_html=True)

        with col_eta:
            if not dados_eta.empty:
                st.markdown("<div class='card'><div class='card-title'>⚡ ESTAÇÃO DE TRATAMENTO DE ÁGUA (ETA)</div>", unsafe_allow_html=True)
                for _, row in dados_eta.iterrows():
                    loc_e = buscar_campo_mult(row, ['Localidade'])
                    if dado_valido(loc_e): st.write(f"**Localidade da ETA:** {loc_e}")
                    
                    cc_eeab = formatar_valor(buscar_campo_mult(row, ['CC Equatorial EEAB', 'CC EEAB']))
                    if dado_valido(cc_eeab): st.write(f"**⚡ CC Equatorial EEAB:** {cc_eeab}")

                    cc_eta = formatar_valor(buscar_campo_mult(row, ['CC Equatorial ETA', 'CC ETA']))
                    if dado_valido(cc_eta): st.write(f"**⚡ CC Equatorial ETA:** {cc_eta}")
                    
                    eta_tipo = buscar_campo_mult(row, ['ETA - Tipo'])
                    if dado_valido(eta_tipo): st.write(f"**Tipo da ETA:** {eta_tipo}")

                    mat_est = buscar_campo_mult(row, ['ETA - Material Estrutura'])
                    if dado_valido(mat_est): st.write(f"**Material da Estrutura:** {mat_est}")
                    
                    obs_e = buscar_campo_mult(row, ['OBSERVAÇÕES', 'Observações', 'Obs'])
                    if dado_valido(obs_e): st.info(f"**Obs:** {obs_e}")

                    st.markdown("---")
                st.markdown("</div>", unsafe_allow_html=True)

    # 2. Seção de Adutoras Interligadas
    if not df_adutoras.empty:
        c_origem = 'Município Origem'
        c_destino = 'Município Destino'
        dados_adu = df_adutoras[(df_adutoras[c_origem].astype(str).str.strip().str.upper() == municipio_selecionado) | 
                                (df_adutoras[c_destino].astype(str).str.strip().str.upper() == municipio_selecionado)] if c_origem in df_adutoras.columns else pd.DataFrame()
        if not dados_adu.empty:
            st.header("🔗 Sistemas Interligados / Adutoras de Exportação")
            for _, row in dados_adu.iterrows():
                diam_adu = formatar_valor(buscar_campo_mult(row, ['Diâmetro da Adutora (mm)']) or '—')
                st.warning(f"🚨 **Atenção:** Sistema Interligado! Origem: {row[c_origem]} ➔ Destino: {row[c_destino]} | Diâmetro: {diam_adu}mm")

    # 3. Seção de Poços Artesianos
    if not dados_poc.empty:
        st.header("🕳️ Sistema de Poços Artesianos (Captação Subterrânea)")
        cols_pocos = st.columns(3)
        
        idx = 0
        for _, row in dados_poc.iterrows():
            col_atual = cols_pocos[idx % 3]
            with col_atual:
                id_pocio = buscar_campo_mult(row, ['Identificação do Poço', 'Poço']) or '—'
                st.markdown(f"<div class='card'><div class='card-title'>📍 {id_pocio}</div>", unsafe_allow_html=True)
                
                loc_p = buscar_campo_mult(row, ['Localidade/Região', 'Localidade'])
                if dado_valido(loc_p): st.write(f"**Região/Localidade:** {loc_p}")
                
                pot_b = formatar_valor(buscar_campo_mult(row, ['Potência da Bomba (cv)', 'Potência (cv)']))
                alt_b = formatar_valor(buscar_campo_mult(row, ['Altura da Bomba (mca)', 'Altura (mca)']))
                vaz_b = formatar_valor(buscar_campo_mult(row, ['Vazão (m³/h)', 'Vazão']))
                
                if dado_valido(pot_b): st.write(f"**Potência da Bomba:** {pot_b} cv")
                if dado_valido(alt_b): st.write(f"**Altura da Bomba:** {alt_b} mca")
                if dado_valido(vaz_b): st.write(f"**Vazão Cadastrada:** {vaz_b} m³/h")
                
                st.markdown("</div>", unsafe_allow_html=True)
            idx += 1

    if dados_cap.empty and dados_eta.empty and dados_poc.empty:
        st.info("Nenhuma estrutura localizada para este município nos registros da planilha.")

except Exception as e:
    st.error(f"Erro na leitura dos dados: {e}")
