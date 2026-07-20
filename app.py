import streamlit as st
import pandas as pd
from fpdf import FPDF
import os
import re

# Configuração da página para modo amplo (wide)
st.set_page_config(
    page_title="CASAL - Fichas Técnicas dos Sistemas ZML",
    page_icon="🚰",
    layout="wide"
)

# Estilização CSS
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
    .card-title { color: #1F4E79; font-weight: bold; margin-bottom: 12px; font-size: 1.15rem; }
    </style>
""", unsafe_allow_html=True)

# URL Base Única da Planilha Fichas-ZML
base_url = "https://docs.google.com/spreadsheets/d/1cUfZoPkVmiOivWXmRK4u3Vlp435f4_DeFzGvTFQOiNw/gviz/tq?tqx=out:csv&sheet="

LOGO_PATH = None
for ext in ['png', 'jpg', 'jpeg']:
    if os.path.exists(f"logo.{ext}"):
        LOGO_PATH = f"logo.{ext}"
        break

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

def formatar_link_drive(url):
    """Converte links do Google Drive para visualização direta de imagem"""
    if not dado_valido(url):
        return None
    url_str = str(url).strip()
    match = re.search(r'(?:file/d/|id=)([\w-]+)', url_str)
    if match:
        file_id = match.group(1)
        return f"https://lh3.googleusercontent.com/d/{file_id}"
    return url_str

def extrair_lista_fotos(row, tipo_aba):
    """Busca dinâmica por colunas de foto (01, 02, 03) independente da aba"""
    fotos = []
    
    opcoes = []
    if tipo_aba == "cap":
        opcoes = ["Foto Captação", "Foto Captacao", "Foto"]
    elif tipo_aba == "eta":
        opcoes = ["Foto ETA", "Foto"]
    elif tipo_aba == "poc":
        opcoes = ["Foto Poço", "Foto Poco", "Foto"]

    sufixos = ['', ' 01', ' 1', ' 02', ' 2', ' 03', ' 3']

    for pref in opcoes:
        for suf in sufixos:
            nome_col = f"{pref}{suf}"
            val = buscar_campo_mult(row, [nome_col])
            if val:
                link_fmt = formatar_link_drive(val)
                if link_fmt and link_fmt not in fotos:
                    fotos.append(link_fmt)

    return fotos

def exibir_galeria_fotos(fotos, legenda_base="Foto"):
    """Exibe fotos em colunas lado a lado no card"""
    if not fotos:
        return
    st.markdown("<div style='margin-top: 15px;'><b>📷 Registros Fotográficos:</b></div>", unsafe_allow_html=True)
    cols = st.columns(len(fotos))
    for idx, (col, url_foto) in enumerate(zip(cols, fotos)):
        with col:
            try:
                st.image(url_foto, caption=f"{legenda_base} - {idx+1}", use_container_width=True)
            except Exception:
                st.markdown(f"[🔗 Abrir {legenda_base} {idx+1}]({url_foto})")

def converter_coordenada(val):
    if not dado_valido(val):
        return None
    try:
        texto = str(val).strip().replace(',', '.')
        match = re.search(r'[-+]?\d*\.\d+|\d+', texto)
        if match:
            num = float(match.group())
            if "S" in texto.upper() or "W" in texto.upper() or "O" in texto.upper():
                num = -abs(num)
            elif num > 0 and num < 40:
                num = -num
            return num
    except:
        return None
    return None

@st.cache_data(ttl=60)
def carregar_dados():
    try: df_cap = pd.read_csv(base_url + "DADOS_CAPTACAO")
    except: df_cap = pd.DataFrame()
        
    try: df_eta = pd.read_csv(base_url + "DADOS_ETA_EEAB")
    except: df_eta = pd.DataFrame()
        
    try: df_poc = pd.read_csv(base_url + "DADOS_POCOS")
    except: df_poc = pd.DataFrame()
        
    try: df_adu = pd.read_csv(base_url + "ADUTORAS_INTERLIGACAO")
    except: df_adu = pd.DataFrame()

    try: df_geo = pd.read_csv(base_url + "GEOLOCALIZACAO")
    except: df_geo = pd.DataFrame()
        
    return df_cap, df_eta, df_poc, df_adu, df_geo

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
    
    if not df_c.empty or not df_e.empty:
        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(0, 7, "1. DADOS DA CAPTACAO SUPERFICIAL E ADUTORAS/EEAB", ln=True)
        pdf.set_font("Helvetica", "", 10)
        
        cc_eeab_val = ""
        if not df_e.empty:
            for _, r_e in df_e.iterrows():
                cc_eeab_val = formatar_valor(buscar_campo_mult(r_e, ['CC Equatorial EEAB', 'CC EEAB']))
                if cc_eeab_val: break

        for _, row in df_c.iterrows():
            loc = buscar_campo_mult(row, ['Localidade'])
            tipo = buscar_campo_mult(row, ['Captação - Tipo', 'Tipo de Captação'])
            vaz = formatar_valor(buscar_campo_mult(row, ['EEAB - Vazão Principal (m³/h)', 'EEAB - Vazão Principal (m3/h)', 'Vazão Principal', 'Vazão']))
            pot = formatar_valor(buscar_campo_mult(row, ['EEAB - Potência Principal (cv)', 'EEAB - Potencia Principal (cv)', 'Potência Principal']))
            alt = formatar_valor(buscar_campo_mult(row, ['EEAB - Altura Manométrica Principal (mca)', 'EEAB - Altura Manometrica Principal (mca)']))
            
            bomba_res = buscar_campo_mult(row, ['EEAB - Possui Bomba Reserva', 'EAB - Possui Bomba Reserva', 'Possui Bomba Reserva'])
            tipo_res = buscar_campo_mult(row, ['EEAB - Tipo da Bomba Reserva', 'EAB - Tipo da Bomba Reserva', 'Tipo da Bomba Reserva'])
            pot_res = formatar_valor(buscar_campo_mult(row, ['EEAB - Potência Reserva (cv)', 'EEAB - Potencia Reserva (cv)', 'EAB - Potência Reserva (cv)', 'Potência Reserva']))
            vaz_res = formatar_valor(buscar_campo_mult(row, ['EEAB - Vazão Reserva (m³/h)', 'EEAB - Vazao Reserva (m3/h)', 'EAB - Vazão Reserva (m³/h)', 'Vazão Reserva']))
            alt_res = formatar_valor(buscar_campo_mult(row, ['EEAB - Altura Manométrica Reserva (mca)', 'EEAB - Altura Manometrica Reserva (mca)', 'EAB - Altura Manométrica Reserva (mca)']))
            
            if dado_valido(loc): pdf.cell(0, 5.5, f"Localidade/Sistema: {limpar_acentos(loc)}", ln=True)
            if dado_valido(cc_eeab_val): pdf.cell(0, 5.5, f"CC Equatorial EEAB: {cc_eeab_val}", ln=True)
            if dado_valido(tipo): pdf.cell(0, 5.5, f"Tipo de Captacao: {limpar_acentos(tipo)}", ln=True)
            if dado_valido(vaz): pdf.cell(0, 5.5, f"Vazao Principal EEAB: {vaz} m3/h", ln=True)
            if dado_valido(pot) or dado_valido(alt): pdf.cell(0, 5.5, f"Bomba Principal: Potencia: {pot} cv | Altura: {alt} mca", ln=True)
            
            if dado_valido(bomba_res):
                txt_r = f"Bomba Reserva: {limpar_acentos(bomba_res)}"
                if dado_valido(tipo_res): txt_r += f" ({limpar_acentos(tipo_res)})"
                if dado_valido(pot_res): txt_r += f" | Potencia: {pot_res} cv"
                if dado_valido(vaz_res): txt_r += f" | Vazao: {vaz_res} m3/h"
                if dado_valido(alt_res): txt_r += f" | Altura: {alt_res} mca"
                pdf.cell(0, 5.5, txt_r, ln=True)
                
            pdf.ln(1.5)
        pdf.ln(3)

    if not df_e.empty:
        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(0, 7, "2. ESTACAO DE TRATAMENTO DE AGUA (ETA)", ln=True)
        pdf.set_font("Helvetica", "", 10)
        for _, row in df_e.iterrows():
            loc_eta = buscar_campo_mult(row, ['Localidade'])
            cc_eta = formatar_valor(buscar_campo_mult(row, ['CC Equatorial ETA', 'CC ETA']))
            eta_tipo = buscar_campo_mult(row, ['ETA - Tipo'])
            filtros_qtd = formatar_valor(buscar_campo_mult(row, ['Filtros - Quantidade']))
            prod_chem = buscar_campo_mult(row, ['Produto Químico Principal'])
            obs_eta = buscar_campo_mult(row, ['OBSERVAÇÕES', 'Observações'])
            
            if dado_valido(loc_eta): pdf.cell(0, 5.5, f"Localidade da ETA: {limpar_acentos(loc_eta)}", ln=True)
            if dado_valido(cc_eta): pdf.cell(0, 5.5, f"CC Equatorial ETA: {cc_eta}", ln=True)
            if dado_valido(eta_tipo): pdf.cell(0, 5.5, f"Tipo da ETA: {limpar_acentos(eta_tipo)}", ln=True)
            if dado_valido(filtros_qtd): pdf.cell(0, 5.5, f"Filtros: {filtros_qtd} unidade(s)", ln=True)
            if dado_valido(prod_chem): pdf.cell(0, 5.5, f"Produtos Quimicos: {limpar_acentos(prod_chem)}", ln=True)
            if dado_valido(obs_eta): pdf.multi_cell(0, 5.5, f"Obs: {limpar_acentos(obs_eta)}")
            pdf.ln(1.5)
        pdf.ln(3)

    if not df_p.empty:
        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(0, 7, "3. SISTEMA DE POCOS ARTESIANOS (SUBTERRANEO)", ln=True)
        for _, row in df_p.iterrows():
            id_p = buscar_campo_mult(row, ['Identificação do Poço']) or 'Poco'
            cc_p = formatar_valor(buscar_campo_mult(row, ['CC Equatorial', 'CC Equatorial Poço', 'CC Poço', 'CC', 'Código do Cliente']))
            pdf.set_font("Helvetica", "B", 10)
            txt_head_p = f"Poco: {limpar_acentos(id_p)}"
            if dado_valido(cc_p): txt_head_p += f" (CC: {cc_p})"
            pdf.cell(0, 5.5, txt_head_p, ln=True)
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
    df_captacao, df_eta_eeab, df_pocos, df_adutoras, df_geolocalizacao = carregar_dados()
    
    def obter_municipios(df):
        if df.empty: return []
        for col in df.columns:
            if limpar_acentos(col).upper().strip() in ['MUNICIPIO', 'MUNICPIO ORIGEM', 'MUNICÍPIO']:
                return df[col].dropna().astype(str).str.strip().str.upper().unique().tolist()
        return []

    todos_muns = obter_municipios(df_captacao) + obter_municipios(df_eta_eeab) + obter_municipios(df_pocos) + obter_municipios(df_geolocalizacao)
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
    dados_geo = filtrar_por_municipio(df_geolocalizacao)
    
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

    cc_eeab_da_eta = None
    if not dados_eta.empty:
        for _, r_e in dados_eta.iterrows():
            val = formatar_valor(buscar_campo_mult(r_e, ['CC Equatorial EEAB', 'CC EEAB']))
            if val:
                cc_eeab_da_eta = val
                break

    # --- EXIBIÇÃO DA INFRAESTRUTURA NA TELA ---
    if not dados_cap.empty or not dados_eta.empty:
        st.header("🏢 Infraestrutura de Tratamento e Distribuição Superficial")
        col_cap, col_eta = st.columns(2)
        
        # --- CARD CAPTAÇÃO E EEAB ---
        with col_cap:
            if not dados_cap.empty:
                st.markdown("<div class='card'><div class='card-title'>🪵 DADOS DA CAPTAÇÃO E ADUTORAS/EEAB</div>", unsafe_allow_html=True)
                for _, row in dados_cap.iterrows():
                    loc_c = buscar_campo_mult(row, ['Localidade'])
                    if dado_valido(loc_c): st.write(f"**Localidade/Sistema:** {loc_c}")

                    if dado_valido(cc_eeab_da_eta):
                        st.write(f"**⚡ CC Equatorial EEAB:** {cc_eeab_da_eta}")
                    
                    tipo_cap = buscar_campo_mult(row, ['Captação - Tipo', 'Tipo de Captação'])
                    if dado_valido(tipo_cap): st.write(f"**Tipo de Captação:** {tipo_cap}")

                    vaz_cap = formatar_valor(buscar_campo_mult(row, ['EEAB - Vazão Principal (m³/h)', 'EEAB - Vazão Principal (m3/h)', 'Vazão Principal', 'Vazão']))
                    if dado_valido(vaz_cap): st.write(f"**Vazão Principal:** {vaz_cap} m³/h")

                    bomba_cap = buscar_campo_mult(row, ['EEAB - Tipo da Bomba Principal', 'Tipo da Bomba Principal', 'EEAB - Tipo Bomba Principal'])
                    pot_cap = formatar_valor(buscar_campo_mult(row, ['EEAB - Potência Principal (cv)', 'EEAB - Potencia Principal (cv)', 'Potência Principal']))
                    alt_cap = formatar_valor(buscar_campo_mult(row, ['EEAB - Altura Manométrica Principal (mca)', 'EEAB - Altura Manometrica Principal (mca)']))
                    
                    if dado_valido(bomba_cap) or dado_valido(pot_cap) or dado_valido(alt_cap):
                        txt_b = "**Bomba Principal (EEAB):**"
                        if dado_valido(bomba_cap): txt_b += f" {bomba_cap}"
                        if dado_valido(pot_cap): txt_b += f" | Potência: {pot_cap} cv"
                        if dado_valido(alt_cap): txt_b += f" | Altura: {alt_cap} mca"
                        st.write(txt_b)

                    possui_reserva = buscar_campo_mult(row, ['EEAB - Possui Bomba Reserva', 'EAB - Possui Bomba Reserva', 'Possui Bomba Reserva', 'Bomba Reserva'])
                    tipo_reserva = buscar_campo_mult(row, ['EEAB - Tipo da Bomba Reserva', 'EAB - Tipo da Bomba Reserva', 'Tipo da Bomba Reserva', 'EEAB - Tipo Bomba Reserva'])
                    pot_reserva = formatar_valor(buscar_campo_mult(row, ['EEAB - Potência Reserva (cv)', 'EEAB - Potencia Reserva (cv)', 'EAB - Potência Reserva (cv)', 'EAB - Potencia Reserva (cv)', 'Potência Reserva']))
                    vaz_reserva = formatar_valor(buscar_campo_mult(row, ['EEAB - Vazão Reserva (m³/h)', 'EEAB - Vazao Reserva (m3/h)', 'EAB - Vazão Reserva (m³/h)', 'EAB - Vazao Reserva (m3/h)', 'Vazão Reserva']))
                    alt_reserva = formatar_valor(buscar_campo_mult(row, ['EEAB - Altura Manométrica Reserva (mca)', 'EEAB - Altura Manometrica Reserva (mca)', 'EAB - Altura Manométrica Reserva (mca)', 'Altura Manométrica Reserva']))

                    if dado_valido(possui_reserva):
                        txt_res = f"**Bomba Reserva:** {possui_reserva}"
                        if dado_valido(tipo_reserva): txt_res += f" ({tipo_reserva})"
                        if dado_valido(pot_reserva): txt_res += f" | Potência: {pot_reserva} cv"
                        if dado_valido(vaz_reserva): txt_res += f" | Vazão: {vaz_reserva} m³/h"
                        if dado_valido(alt_reserva): txt_res += f" | Altura: {alt_reserva} mca"
                        st.write(txt_res)

                    crivo = buscar_campo_mult(row, ['Captação - Possui Crivo', 'Possui Crivo'])
                    mat_crivo = buscar_campo_mult(row, ['Captação - Material Crivo', 'Material Crivo'])
                    diam_crivo = formatar_valor(buscar_campo_mult(row, ['Captação - Diâmetro Crivo (mm)', 'Captação - Diametro Crivo (mm)']))
                    if dado_valido(crivo):
                        txt_c = f"**Possui Crivo:** {crivo}"
                        if dado_valido(diam_crivo): txt_c += f" ({diam_crivo} mm)"
                        if dado_valido(mat_crivo): txt_c += f" - {mat_crivo}"
                        st.write(txt_c)

                    diam = formatar_valor(buscar_campo_mult(row, ['Adutora EEAB até ETA - Diâmetro (mm)', 'Adutora EEAB ate ETA - Diametro (mm)']))
                    comp = formatar_valor(buscar_campo_mult(row, ['Adutora EEAB até ETA - Comprimento (m)', 'Adutora EEAB ate ETA - Comprimento (m)']))
                    mat_adu = buscar_campo_mult(row, ['Adutora EEAB até ETA - Material', 'Adutora EEAB ate ETA - Material'])
                    if dado_valido(diam) or dado_valido(comp):
                        txt_adu = "**Adutora EEAB ➔ ETA:**"
                        if dado_valido(diam): txt_adu += f" Diâmetro {diam} mm"
                        if dado_valido(mat_adu): txt_adu += f" ({mat_adu})"
                        if dado_valido(comp): txt_adu += f" | Comprimento: {comp} m"
                        st.write(txt_adu)

                    obs_c = buscar_campo_mult(row, ['OBSERVAÇÕES', 'Observações', 'Obs'])
                    if dado_valido(obs_c): st.info(f"**Obs:** {obs_c}")

                    # --- GALERIA DE FOTOS CAPTAÇÃO ---
                    fotos_cap = extrair_lista_fotos(row, "cap")
                    exibir_galeria_fotos(fotos_cap, legenda_base="Captação/EEAB")

                    st.markdown("---")
                st.markdown("</div>", unsafe_allow_html=True)

        # --- CARD ESTAÇÃO DE TRATAMENTO DE ÁGUA (ETA) ---
        with col_eta:
            if not dados_eta.empty:
                st.markdown("<div class='card'><div class='card-title'>⚡ ESTAÇÃO DE TRATAMENTO DE ÁGUA (ETA)</div>", unsafe_allow_html=True)
                for _, row in dados_eta.iterrows():
                    loc_e = buscar_campo_mult(row, ['Localidade'])
                    if dado_valido(loc_e): st.write(f"**Localidade da ETA:** {loc_e}")

                    cc_eta = formatar_valor(buscar_campo_mult(row, ['CC Equatorial ETA', 'CC ETA']))
                    if dado_valido(cc_eta): st.write(f"**⚡ CC Equatorial ETA:** {cc_eta}")
                    
                    eta_tipo = buscar_campo_mult(row, ['ETA - Tipo'])
                    if dado_valido(eta_tipo): st.write(f"**Tipo da ETA:** {eta_tipo}")

                    mat_est = buscar_campo_mult(row, ['ETA - Material Estrutura'])
                    if dado_valido(mat_est): st.write(f"**Material da Estrutura:** {mat_est}")

                    f_qtd = formatar_valor(buscar_campo_mult(row, ['Filtros - Quantidade']))
                    f_alt = formatar_valor(buscar_campo_mult(row, ['Filtros - Altura (m)']))
                    f_vol = formatar_valor(buscar_campo_mult(row, ['Filtros - Volume (m³)', 'Filtros - Volume (m3)']))
                    if dado_valido(f_qtd) or dado_valido(f_vol):
                        txt_f = "**Filtros:**"
                        if dado_valido(f_qtd): txt_f += f" {f_qtd} unidade(s)"
                        if dado_valido(f_alt): txt_f += f" | Altura: {f_alt} m"
                        if dado_valido(f_vol): txt_f += f" | Volume Total: {f_vol} m³"
                        st.write(txt_f)

                    d_alt = formatar_valor(buscar_campo_mult(row, ['Decantador - Altura (m)']))
                    d_vol = formatar_valor(buscar_campo_mult(row, ['Decantador - Volume (m³)', 'Decantador - Volume (m3)']))
                    if dado_valido(d_alt) or dado_valido(d_vol):
                        txt_d = "**Decantador:**"
                        if dado_valido(d_alt): txt_d += f" Altura: {d_alt} m"
                        if dado_valido(d_vol): txt_d += f" | Volume: {d_vol} m³"
                        st.write(txt_d)

                    rl_alt = formatar_valor(buscar_campo_mult(row, ['Reservatório Lavagem - Altura (m)', 'Reservatorio Lavagem - Altura (m)']))
                    rl_vol = formatar_valor(buscar_campo_mult(row, ['Reservatório Lavagem - Volume (m³)', 'Reservatorio Lavagem - Volume (m3)']))
                    if dado_valido(rl_alt) or dado_valido(rl_vol):
                        txt_rl = "**Reservatório de Lavagem:**"
                        if dado_valido(rl_alt): txt_rl += f" Altura: {rl_alt} m"
                        if dado_valido(rl_vol): txt_rl += f" | Volume: {rl_vol} m³"
                        st.write(txt_rl)

                    cc_alt = formatar_valor(buscar_campo_mult(row, ['Câmara de Carga - Altura (m)', 'Camara de Carga - Altura (m)']))
                    cc_vol = formatar_valor(buscar_campo_mult(row, ['Câmara de Carga - Volume (m³)', 'Camara de Carga - Volume (m3)']))
                    if dado_valido(cc_alt) or dado_valido(cc_vol):
                        txt_cc = "**Câmara de Carga:**"
                        if dado_valido(cc_alt): txt_cc += f" Altura: {cc_alt} m"
                        if dado_valido(cc_vol): txt_cc += f" | Volume: {cc_vol} m³"
                        st.write(txt_cc)

                    pre_clor = buscar_campo_mult(row, ['Possui Pré-cloração', 'Possui Pre-cloracao'])
                    if dado_valido(pre_clor): st.write(f"**Possui Pré-cloração:** {pre_clor}")

                    prod_chem = buscar_campo_mult(row, ['Produto Químico Principal', 'Produto Quimico Principal'])
                    if dado_valido(prod_chem): st.write(f"**Produtos Químicos:** {prod_chem}")

                    obs_e = buscar_campo_mult(row, ['OBSERVAÇÕES', 'Observações', 'Obs'])
                    if dado_valido(obs_e): st.info(f"**Obs:** {obs_e}")

                    # --- GALERIA DE FOTOS ETA ---
                    fotos_eta = extrair_lista_fotos(row, "eta")
                    exibir_galeria_fotos(fotos_eta, legenda_base="ETA")

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

                # --- EXIBIÇÃO DA CC EQUATORIAL DO POÇO ---
                cc_poco = formatar_valor(buscar_campo_mult(row, ['CC Equatorial', 'CC Equatorial Poço', 'CC Poço', 'CC', 'Código do Cliente', 'CC Equatorial (Poço)']))
                if dado_valido(cc_poco): st.write(f"**⚡ CC Equatorial:** {cc_poco}")
                
                pot_b = formatar_valor(buscar_campo_mult(row, ['Potência da Bomba (cv)', 'Potência (cv)']))
                alt_b = formatar_valor(buscar_campo_mult(row, ['Altura da Bomba (mca)', 'Altura (mca)']))
                vaz_b = formatar_valor(buscar_campo_mult(row, ['Vazão (m³/h)', 'Vazão']))
                
                if dado_valido(pot_b): st.write(f"**Potência da Bomba:** {pot_b} cv")
                if dado_valido(alt_b): st.write(f"**Altura da Bomba:** {alt_b} mca")
                if dado_valido(vaz_b): st.write(f"**Vazão Cadastrada:** {vaz_b} m³/h")

                # --- GALERIA DE FOTOS POÇO ---
                fotos_poc = extrair_lista_fotos(row, "poc")
                exibir_galeria_fotos(fotos_poc, legenda_base="Poço")
                
                st.markdown("</div>", unsafe_allow_html=True)
            idx += 1

    if dados_cap.empty and dados_eta.empty and dados_poc.empty:
        st.info("Nenhuma estrutura localizada para este município nos registros da planilha.")

    # --- SEÇÃO DE GEOLOCALIZAÇÃO OTIMIZADA ---
    if not dados_geo.empty:
        pontos_mapa = []
        for _, r_g in dados_geo.iterrows():
            lat_col = buscar_campo_mult(r_g, ['Latitude', 'LATITUDE', 'Lat'])
            lon_col = buscar_campo_mult(r_g, ['Longitude', 'LONGITUDE', 'Long', 'Lon'])
            
            lat_f = converter_coordenada(lat_col)
            lon_f = converter_coordenada(lon_col)
            
            if lat_f is not None and lon_f is not None:
                nome_est = buscar_campo_mult(r_g, ['Unidade', 'UNIDADE', 'Descrição', 'Descricao', 'Estrutura', 'Nome']) or 'Unidade Operacional'
                
                # Link direto para Google Maps
                link_gmaps = f"https://www.google.com/maps/search/?api=1&query={lat_f},{lon_f}"
                
                pontos_mapa.append({
                    'Unidade / Estrutura': str(nome_est),
                    'Latitude': lat_f,
                    'Longitude': lon_f,
                    'Google Maps': link_gmaps
                })

        if pontos_mapa:
            st.markdown("---")
            st.header("📍 Geolocalização das Unidades Operacionais")
            
            df_mapa = pd.DataFrame(pontos_mapa)

            # Dividindo a tela de forma proporcional
            col_mapa, col_lista = st.columns([1.2, 1])
            
            with col_mapa:
                st.map(
                    df_mapa, 
                    latitude='Latitude', 
                    longitude='Longitude', 
                    zoom=11, 
                    use_container_width=True
                )
                
            with col_lista:
                st.markdown("##### 📌 Unidades Mapeadas")
                
                st.dataframe(
                    df_mapa[['Unidade / Estrutura', 'Google Maps']],
                    column_config={
                        "Unidade / Estrutura": st.column_config.TextColumn("Unidade Operacional", help="Nome da unidade"),
                        "Google Maps": st.column_config.LinkColumn(
                            "Rota GPS", 
                            display_text="🗺️ Abrir no Maps",
                            help="Clique para abrir as coordenadas no Google Maps"
                        )
                    },
                    hide_index=True,
                    use_container_width=True,
                    height=380
                )

except Exception as e:
    st.error(f"Erro na leitura dos dados: {e}")
