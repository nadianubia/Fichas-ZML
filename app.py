import streamlit as st
import pandas as pd
from fpdf import FPDF
import os
import re
import requests
from io import BytesIO
from PIL import Image

# Configuração da página para modo amplo (wide)
st.set_page_config(
    page_title="CASAL - Fichas Técnicas dos Sistemas ZML",
    page_icon="💧",
    layout="wide"
)

# Estilização CSS Ajustada
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
.card-title { 
    color: #1F4E79; 
    font-weight: bold; 
    margin-bottom: 12px;
    font-size: 1.15rem; 
}
/* Link discreto e pequeno para o Google Maps */
.link-maps-discreto {
    display: inline-block;
    color: #006699 !important;
    font-size: 0.85rem;
    font-weight: 500;
    text-decoration: underline !important;
    margin-top: 6px;
    margin-bottom: 8px;
}
.link-maps-discreto:hover {
    color: #1F4E79 !important;
}
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
    if not texto: 
        return ""
    import unicodedata
    texto_str = str(texto).strip()
    
    # Mapeamento de caracteres incompatíveis com a fonte Helvetica do FPDF
    substituicoes = {
        '–': '-',  # EN Dash (causador do erro em Maragogi)
        '—': '-',  # EM Dash
        '“': '"',
        '”': '"',
        '‘': "'",
        '’': "'",
        '…': '...',
        '¹': '1',
        '²': '2',
        '³': '3',
        'º': 'o',
        'ª': 'a',
        'µ': 'u',
        '®': '(R)',
        '©': '(C)'
    }
    for orig, dest in substituicoes.items():
        texto_str = texto_str.replace(orig, dest)
        
    return "".join(c for c in unicodedata.normalize('NFD', texto_str) if unicodedata.category(c) != 'Mn')

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
        opcoes = ["Foto Poco", "Foto Poço", "Foto"]
 
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

def baixar_imagem_para_pdf(url):
    """Baixa a imagem da URL e converte para BytesIO compatível com FPDF"""
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            img = Image.open(BytesIO(response.content))
            if img.mode != 'RGB':
                img = img.convert('RGB')
            img_byte_arr = BytesIO()
            img.save(img_byte_arr, format='JPEG')
            img_byte_arr.seek(0)
            return img_byte_arr
    except Exception:
        pass 
    return None

def exibir_galeria_fotos(fotos, legenda_base="Foto"):
    """Exibe fotos em colunas lado a lado no card"""
    if not fotos:
        return
    st.markdown("<div style='margin-top: 15px;'><b>Registros Fotográficos:</b></div>", unsafe_allow_html=True)
    cols = st.columns(len(fotos))
    for idx, (col, url_foto) in enumerate(zip(cols, fotos)):
        with col:
            try:
                st.image(url_foto, caption=f"{legenda_base} ({idx+1})", use_container_width=True)
            except Exception:
                st.markdown(f"[{legenda_base} ({idx+1})]({url_foto})")

def converter_coordenada(val):
    if not dado_valido(val):
        return None
    try:
        texto = str(val).strip().replace(',', '.')
        match = re.search(r'[+-]?\d*\.\d+|\d+', texto)
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

def obter_link_gmaps(row, df_geo=None, tipo_busca=None):
    """Busca o link limpo do Maps priorizando a aba GEOLOCALIZACAO ou extraindo URLs limpas"""
    def extrair_url_pura(val):
        if not dado_valido(val):
            return None
        texto = str(val).strip()
        match = re.search(r'https?://[^\s\'"]+', texto)
        if match:
            return match.group(0)
        return None

    # 1. Identificador da estrutura nesta linha
    id_nome = buscar_campo_mult(row, ['Identificação do Poço', 'Poço', 'Unidade', 'Localidade', 'Sistema', 'Captação Tipo'])
    id_norm = limpar_acentos(id_nome).upper().strip() if id_nome else ""

    # 2. Busca na aba GEOLOCALIZACAO
    if df_geo is not None and not df_geo.empty:
        for _, r_g in df_geo.iterrows():
            unid_geo = buscar_campo_mult(r_g, ['Unidade', 'UNIDADE', 'Descrição', 'Descricao'])
            unid_geo_norm = limpar_acentos(unid_geo).upper().strip() if unid_geo else ""
            if id_norm and (id_norm in unid_geo_norm or unid_geo_norm in id_norm):
                lat_g = converter_coordenada(buscar_campo_mult(r_g, ['Latitude', 'LATITUDE', 'Lat']))
                lon_g = converter_coordenada(buscar_campo_mult(r_g, ['Longitude', 'LONGITUDE', 'Long', 'Lon']))
                if lat_g is not None and lon_g is not None:
                    return f"https://www.google.com/maps/search/?api=1&query={lat_g},{lon_g}"

    # 3. Lat/Lon da própria linha
    lat = buscar_campo_mult(row, ['Latitude', 'LATITUDE', 'Lat'])
    lon = buscar_campo_mult(row, ['Longitude', 'LONGITUDE', 'Long', 'Lon'])
    lat_f = converter_coordenada(lat)
    lon_f = converter_coordenada(lon)
    if lat_f is not None and lon_f is not None:
        return f"https://www.google.com/maps/search/?api=1&query={lat_f},{lon_f}"

    # 4. Extrair URL direta
    link_direto = buscar_campo_mult(row, ['Geolocalização', 'Geolocalizacao', 'Link Maps', 'Google Maps', 'Maps', 'Localização'])
    url_pura = extrair_url_pura(link_direto)
    if url_pura:
        return url_pura
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

# GERADOR DE PDF
def gerar_pdf_ficha(municipio, df_c, df_e, df_p, df_a):
    pdf = FPDF()
    pdf.add_page()
    mun_limpo = limpar_acentos(municipio).upper()
    
    if LOGO_PATH:
        pdf.image(LOGO_PATH, x=10, y=10, w=30)
        pdf.set_y(12)
        pdf.set_x(45)
        pdf.set_font("Helvetica", "B", 13)
        pdf.cell(0, 7, "CASAL COMPANHIA DE SANEAMENTO DE ALAGOAS", ln=True)
        pdf.set_x(45)
        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(0, 7, f"FICHA TECNICA DOS SISTEMAS ZML: {mun_limpo}", ln=True)
    else:
        pdf.set_font("Helvetica", "B", 14)
        pdf.cell(0, 10, "CASAL COMPANHIA DE SANEAMENTO DE ALAGOAS", ln=True, align="C")
        pdf.cell(0, 10, f"FICHA TECNICA DOS SISTEMAS ZML: {mun_limpo}", ln=True, align="C")
        
    pdf.ln(12)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(5)

    # 1. CAPTAÇÃO E EEAB
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
            tipo = buscar_campo_mult(row, ['Captação Tipo', 'Tipo de Captação'])
            vaz = formatar_valor(buscar_campo_mult(row, ['EEAB Principal (m3/h)', 'EEAB Vazão Principal (m3/h)', 'Vazão Principal', 'Vazão']))
            pot = formatar_valor(buscar_campo_mult(row, ['EEAB Potência Principal (cv)', 'EEAB Potencia Principal (cv)', 'Potência Principal']))
            alt = formatar_valor(buscar_campo_mult(row, ['EEAB Altura Manométrica Principal (mca)', 'EEAB Altura Manometrica Principal (mca)']))
            
            bomba_res = buscar_campo_mult(row, ['EEAB Possui Bomba Reserva', 'Possui Bomba Reserva', 'EAB Possui Bomba Reserva'])
            tipo_res = buscar_campo_mult(row, ['EEAB Tipo da Bomba Reserva', 'Tipo da Bomba Reserva'])
            pot_res = formatar_valor(buscar_campo_mult(row, ['EEAB Potência Reserva (cv)', 'EEAB Potencia Reserva (cv)', 'EAB Potência Reserva (cv)', 'Potência Reserva']))
            vaz_res = formatar_valor(buscar_campo_mult(row, ['EEAB Vazão Reserva (m3/h)', 'EEAB Vazao Reserva (m3/h)', 'EAB Vazão Reserva (m3/h)', 'Vazão Reserva']))
            alt_res = formatar_valor(buscar_campo_mult(row, ['EEAB - Altura Manométrica Reserva (mca)', 'EEAB - Altura Manometrica Reserva (mca)', 'EAB - Altura Manométrica Reserva (mca)']))
            
            crivo = buscar_campo_mult(row, ['Captação - Possui Crivo', 'Possui Crivo'])
            mat_crivo = buscar_campo_mult(row, ['Captação - Material Crivo', 'Material Crivo'])
            diam_crivo = formatar_valor(buscar_campo_mult(row, ['Captação - Diâmetro Crivo (mm)', 'Captação - Diametro Crivo (mm)']))
            diam_adu = formatar_valor(buscar_campo_mult(row, ['Adutora EEAB até ETA - Diâmetro (mm)', 'Adutora EEAB ate ETA - Diametro (mm)']))
            comp_adu = formatar_valor(buscar_campo_mult(row, ['Adutora EEAB até ETA - Comprimento (m)', 'Adutora EEAB ate ETA - Comprimento (m)']))
            mat_adu = buscar_campo_mult(row, ['Adutora EEAB até ETA - Material', 'Adutora EEAB ate ETA - Material'])
            obs_cap = buscar_campo_mult(row, ['OBSERVAÇÕES', 'Observações', 'Obs', 'OBS'])

            if dado_valido(loc): pdf.cell(0, 5.5, f"Localidade/Sistema: {limpar_acentos(loc)}", ln=True)
            if dado_valido(cc_eeab_val): pdf.cell(0, 5.5, f"CC Equatorial EEAB: {limpar_acentos(cc_eeab_val)}", ln=True)
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

            if dado_valido(crivo):
                txt_c = f"Possui Crivo: {limpar_acentos(crivo)}"
                if dado_valido(diam_crivo): txt_c += f" ({diam_crivo} mm)"
                if dado_valido(mat_crivo): txt_c += f" ({limpar_acentos(mat_crivo)})"
                pdf.cell(0, 5.5, txt_c, ln=True)

            if dado_valido(diam_adu) or dado_valido(comp_adu):
                txt_a = "Adutora EEAB -> ETA:"
                if dado_valido(diam_adu): txt_a += f" Diametro {diam_adu} mm"
                if dado_valido(mat_adu): txt_a += f" ({limpar_acentos(mat_adu)})"
                if dado_valido(comp_adu): txt_a += f" | Comprimento: {comp_adu} m"
                pdf.cell(0, 5.5, txt_a, ln=True)

            if dado_valido(obs_cap):
                pdf.multi_cell(0, 5.5, f"Obs: {limpar_acentos(obs_cap)}")

            fotos_cap = extrair_lista_fotos(row, "cap")
            if fotos_cap:
                pdf.ln(2)
                x_start = pdf.get_x()
                y_pos = pdf.get_y()
                if y_pos > 220:
                    pdf.add_page()
                    y_pos = pdf.get_y()
                offset_x = 0
                for idx_f, url_f in enumerate(fotos_cap[:3]):
                    img_bytes = baixar_imagem_para_pdf(url_f)
                    if img_bytes:
                        pdf.image(img_bytes, x=x_start + offset_x, y=y_pos, w=50, h=35)
                        offset_x += 55
                if offset_x > 0:
                    pdf.set_y(y_pos + 38)
            pdf.ln(3)

    # 2. ETA
    if not df_e.empty:
        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(0, 7, "2. ESTACAO DE TRATAMENTO DE AGUA (ETA)", ln=True)
        pdf.set_font("Helvetica", "", 10)
        
        for _, row in df_e.iterrows():
            loc_eta = buscar_campo_mult(row, ['Localidade'])
            cc_eta = formatar_valor(buscar_campo_mult(row, ['CC Equatorial ETA', 'CC ETA']))
            eta_tipo = buscar_campo_mult(row, ['ETA Tipo'])
            filtros_qtd = formatar_valor(buscar_campo_mult(row, ['Filtros Quantidade']))
            prod_chem = buscar_campo_mult(row, ['Produto Quimico Principal', 'Produto Químico Principal'])
            obs_eta = buscar_campo_mult(row, ['OBSERVAÇÕES', 'Observações', 'Obs', 'OBS'])

            if dado_valido(loc_eta): pdf.cell(0, 5.5, f"Localidade da ETA: {limpar_acentos(loc_eta)}", ln=True)
            if dado_valido(cc_eta): pdf.cell(0, 5.5, f"CC Equatorial ETA: {limpar_acentos(cc_eta)}", ln=True)
            if dado_valido(eta_tipo): pdf.cell(0, 5.5, f"Tipo da ETA: {limpar_acentos(eta_tipo)}", ln=True)
            if dado_valido(filtros_qtd): pdf.cell(0, 5.5, f"Filtros: {filtros_qtd} unidade(s)", ln=True)
            if dado_valido(prod_chem): pdf.cell(0, 5.5, f"Produtos Quimicos: {limpar_acentos(prod_chem)}", ln=True)
            if dado_valido(obs_eta): pdf.multi_cell(0, 5.5, f"Obs: {limpar_acentos(obs_eta)}")

            fotos_eta = extrair_lista_fotos(row, "eta")
            if fotos_eta:
                pdf.ln(2)
                x_start = pdf.get_x()
                y_pos = pdf.get_y()
                if y_pos > 220:
                    pdf.add_page()
                    y_pos = pdf.get_y()
                offset_x = 0
                for idx_f, url_f in enumerate(fotos_eta[:3]):
                    img_bytes = baixar_imagem_para_pdf(url_f)
                    if img_bytes:
                        pdf.image(img_bytes, x=x_start + offset_x, y=y_pos, w=50, h=35)
                        offset_x += 55
                if offset_x > 0:
                    pdf.set_y(y_pos + 38)
            pdf.ln(3)

    # 3. ADUTORAS DE INTERLIGAÇÃO
    if not df_a.empty:
        c_origem, c_destino = 'Municipio Origem', 'Municipio Destino'
        if c_origem in df_a.columns and c_destino in df_a.columns:
            dados_adu_pdf = df_a[
                (df_a[c_origem].astype(str).str.strip().str.upper() == mun_limpo) |
                (df_a[c_destino].astype(str).str.strip().str.upper() == mun_limpo)
            ]
        else:
            dados_adu_pdf = pd.DataFrame()

        if not dados_adu_pdf.empty:
            pdf.set_font("Helvetica", "B", 11)
            pdf.cell(0, 7, "3. SISTEMAS INTERLIGADOS / ADUTORAS DE EXPORTACAO", ln=True)
            pdf.set_font("Helvetica", "", 10)
            
            for _, r_a in dados_adu_pdf.iterrows():
                origem = limpar_acentos(r_a.get(c_origem, ''))
                destino = limpar_acentos(r_a.get(c_destino, ''))
                diam = formatar_valor(buscar_campo_mult(r_a, ['Diâmetro da Adutora (mm)']) or '-')
                pdf.cell(0, 5.5, f"Origem: {origem} -> Destino: {destino} | Diametro: {diam} mm", ln=True)
            pdf.ln(3)

    # 4. POÇOS
    if not df_p.empty:
        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(0, 7, "4. SISTEMA DE POCOS ARTESIANOS (SUBTERRANEO)", ln=True)
        pdf.set_font("Helvetica", "", 10)
        
        for _, row in df_p.iterrows():
            if pdf.get_y() > 230:
                pdf.add_page()
            
            p_id = buscar_campo_mult(row, ['Identificação do Poço', 'Poço', 'Identificacao do Poco'])
            p_loc = buscar_campo_mult(row, ['Localidade', 'Sistema'])
            p_vaz = formatar_valor(buscar_campo_mult(row, ['Vazão (m³/h)', 'Vazao (m3/h)', 'Vazão']))
            p_obs = buscar_campo_mult(row, ['OBSERVAÇÕES', 'Observações', 'Obs', 'OBS'])

            if dado_valido(p_id): pdf.cell(0, 5.5, f"Poco: {limpar_acentos(p_id)}", ln=True)
            if dado_valido(p_loc): pdf.cell(0, 5.5, f"Localidade: {limpar_acentos(p_loc)}", ln=True)
            if dado_valido(p_vaz): pdf.cell(0, 5.5, f"Vazao: {p_vaz} m3/h", ln=True)
            if dado_valido(p_obs): pdf.multi_cell(0, 5.5, f"Obs: {limpar_acentos(p_obs)}")

            fotos_poc = extrair_lista_fotos(row, "poc")
            if fotos_poc:
                pdf.ln(2)
                x_start = pdf.get_x()
                y_pos = pdf.get_y()
                if y_pos > 220:
                    pdf.add_page()
                    y_pos = pdf.get_y()
                offset_x = 0
                for idx_f, url_f in enumerate(fotos_poc[:3]):
                    img_bytes = baixar_imagem_para_pdf(url_f)
                    if img_bytes:
                        pdf.image(img_bytes, x=x_start + offset_x, y=y_pos, w=50, h=35)
                        offset_x += 55
                if offset_x > 0:
                    pdf.set_y(y_pos + 38)
            pdf.ln(2)

    return pdf.output(dest='S').encode('latin-1')
