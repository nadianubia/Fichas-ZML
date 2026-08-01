import streamlit as st
import pandas as pd
import requests
import io
import re

# Importações do ReportLab para geração do PDF
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, KeepTogether, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.pdfgen import canvas

# ==============================================================================
# CONFIGURAÇÃO DA PÁGINA STREAMLIT
# ==============================================================================
st.set_page_config(
    page_title="Dashboard Operacional de Saneamento",
    page_icon="💧",
    layout="wide"
)

# Estilização CSS customizada para os cards da interface
st.markdown("""
<style>
    .card {
        background-color: #f8f9fa;
        border-radius: 8px;
        padding: 15px;
        margin-bottom: 15px;
        border-left: 5px solid #007bff;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    .card-title {
        font-weight: bold;
        font-size: 1.1rem;
        color: #007bff;
        margin-bottom: 10px;
    }
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# FUNÇÃO DE SUPORTE E LEITURA DA API DA TI
# ==============================================================================

# Link fornecido pela TI
URL_API_TI = "https://unserrana.com.br/sirius/v1/wp-json/app/v1/data?tipo=app_get_dados_de_cidades"

@st.cache_data(ttl=300)  # Recarrega os dados a cada 5 minutos
def carregar_dados_sistema(url_api):
    """
    Puxa os dados em tempo real da API da TI.
    Se a API responder com um dicionário contendo abas (como o Excel) ou com uma lista simples,
    a função converte diretamente em DataFrames do Pandas.
    """
    try:
        response = requests.get(url_api, timeout=15)
        response.raise_for_status()
        dados_json = response.json()
        
        # Estruturas padrão para retorno
        dfs = {
            'cap': pd.DataFrame(),
            'eta': pd.DataFrame(),
            'poc': pd.DataFrame(),
            'geo': pd.DataFrame(),
            'adu': pd.DataFrame()
        }
        
        # Se o JSON retornado tiver as chaves/abas separadas
        if isinstance(dados_json, dict):
            for chave in dados_json:
                chave_norm = str(chave).lower()
                df_temp = pd.DataFrame(dados_json[chave])
                if 'cap' in chave_norm: dfs['cap'] = df_temp
                elif 'eta' in chave_norm: dfs['eta'] = df_temp
                elif 'poc' in chave_norm or 'poço' in chave_norm: dfs['poc'] = df_temp
                elif 'geo' in chave_norm: dfs['geo'] = df_temp
                elif 'adu' in chave_norm: dfs['adu'] = df_temp
                
            # Se não encontrou abas específicas, usa a chave principal se existir
            if all(v.empty for v in dfs.values()):
                df_geral = pd.DataFrame(dados_json)
                return df_geral, df_geral, df_geral, df_geral, df_geral

            return dfs['cap'], dfs['eta'], dfs['poc'], dfs['geo'], dfs['adu']
        
        elif isinstance(dados_json, list):
            df_geral = pd.DataFrame(dados_json)
            return df_geral, df_geral, df_geral, df_geral, df_geral
            
    except Exception as e:
        st.error(f"⚠️ Não foi possível conectar ao link da TI: {e}")
        st.info("Tentando carregar a planilha local como backup...")
        # Backup automático para planilha local se o link falhar
        try:
            excel = pd.ExcelFile("dados.xlsx")
            return (
                pd.read_excel(excel, 'CAPTAÇÃO') if 'CAPTAÇÃO' in excel.sheet_names else pd.DataFrame(),
                pd.read_excel(excel, 'ETA') if 'ETA' in excel.sheet_names else pd.DataFrame(),
                pd.read_excel(excel, 'POÇOS') if 'POÇOS' in excel.sheet_names else pd.DataFrame(),
                pd.read_excel(excel, 'GEO') if 'GEO' in excel.sheet_names else pd.DataFrame(),
                pd.read_excel(excel, 'ADUTORAS') if 'ADUTORAS' in excel.sheet_names else pd.DataFrame(),
            )
        except Exception as err_backup:
            st.error(f"Erro ao carregar backup local: {err_backup}")
            return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

# Helper Functions
def buscar_campo_mult(row, lista_campos):
    for campo in lista_campos:
        if campo in row.index and pd.notna(row[campo]) and str(row[campo]).strip() != "":
            return str(row[campo]).strip()
    return None

def dado_valido(val):
    return val is not None and str(val).strip() != "" and str(val).strip() != "—"

def formatar_valor(val):
    if not dado_valido(val): return "—"
    try:
        val_float = float(str(val).replace(',', '.'))
        return f"{val_float:g}".replace('.', ',')
    except:
        return str(val)

def converter_coordenada(val):
    if not dado_valido(val): return None
    try:
        val_str = str(val).replace(',', '.').strip()
        return float(val_str)
    except:
        return None

def extrair_lista_fotos(row, prefixo):
    fotos = []
    for col in row.index:
        if str(col).lower().startswith(prefixo) and 'foto' in str(col).lower():
            val = row[col]
            if dado_valido(val):
                fotos.append(str(val).strip())
    return fotos

def exibir_galeria_fotos(lista_fotos, legenda_base=""):
    if lista_fotos:
        cols = st.columns(min(len(lista_fotos), 3))
        for idx, url_foto in enumerate(lista_fotos):
            with cols[idx % 3]:
                st.image(url_foto, caption=f"{legenda_base} - Foto {idx+1}", use_column_width=True)

# ==============================================================================
# EXECUÇÃO DO APLICATIVO
# ==============================================================================

# Carregando dados da API da TI
df_cap, df_eta, df_poc, df_geo, df_adutoras = carregar_dados_sistema(URL_API_TI)

# Consolidação dos municípios disponíveis
municipios = set()
for df in [df_cap, df_eta, df_poc]:
    if not df.empty:
        col_mun = next((c for c in ['Município', 'MUNICÍPIO', 'Municipio', 'Cidade'] if c in df.columns), None)
        if col_mun:
            municipios.update(df[col_mun].dropna().astype(str).str.strip().str.upper().unique())

lista_municipios = sorted(list(municipios))

st.title("💧 Painel de Monitoramento Operacional")

if not lista_municipios:
    st.warning("Nenhum município localizado nos dados da API.")
else:
    municipio_selecionado = st.sidebar.selectbox("Selecione o Município:", lista_municipios)
    
    # Filtragem dos DataFrames pelo município selecionado
    def filtrar_df(df):
        if df.empty: return pd.DataFrame()
        col_m = next((c for c in ['Município', 'MUNICÍPIO', 'Municipio', 'Cidade'] if c in df.columns), None)
        if col_m:
            return df[df[col_m].astype(str).str.strip().str.upper() == municipio_selecionado]
        return pd.DataFrame()

    dados_cap = filtrar_df(df_cap)
    dados_eta = filtrar_df(df_eta)
    dados_poc = filtrar_df(df_poc)
    dados_geo = filtrar_df(df_geo)

    st.header(f"📍 Município: {municipio_selecionado}")

    # Layout de Colunas para Captação e ETA
    col_cap, col_eta = st.columns(2)

    # 1. CARD CAPTAÇÃO / EEAB
    with col_cap:
        if not dados_cap.empty:
            st.markdown("<div class='card'><div class='card-title'>🚰 CAPTAÇÃO / EEAB</div>", unsafe_allow_html=True)
            for _, row in dados_cap.iterrows():
                cc_eeab = formatar_valor(buscar_campo_mult(row, ['CC Equatorial EEAB', 'CC EEAB']))
                if dado_valido(cc_eeab): st.write(f"**⚡ CC Equatorial EEAB:** {cc_eeab}")
                
                tipo_cap = buscar_campo_mult(row, ['Captação - Tipo', 'Tipo de Captação'])
                if dado_valido(tipo_cap): st.write(f"**Tipo de Captação:** {tipo_cap}")

                vaz_cap = formatar_valor(buscar_campo_mult(row, ['EEAB - Vazão Principal (m³/h)', 'Vazão Principal']))
                if dado_valido(vaz_cap): st.write(f"**Vazão Principal:** {vaz_cap} m³/h")

                bomba_cap = buscar_campo_mult(row, ['EEAB - Tipo da Bomba Principal', 'Tipo da Bomba Principal'])
                pot_cap = formatar_valor(buscar_campo_mult(row, ['EEAB - Potência Principal (cv)', 'Potência Principal']))
                alt_cap = formatar_valor(buscar_campo_mult(row, ['EEAB - Altura Manométrica Principal (mca)']))
                
                if dado_valido(bomba_cap) or dado_valido(pot_cap) or dado_valido(alt_cap):
                    txt_b = "**Bomba Principal (EEAB):**"
                    if dado_valido(bomba_cap): txt_b += f" {bomba_cap}"
                    if dado_valido(pot_cap): txt_b += f" | Potência: {pot_cap} cv"
                    if dado_valido(alt_cap): txt_b += f" | Altura: {alt_cap} mca"
                    st.write(txt_b)

                obs_c = buscar_campo_mult(row, ['OBSERVAÇÕES', 'Observações', 'Obs'])
                if dado_valido(obs_c): st.info(f"**Obs:** {obs_c}")

                fotos_cap = extrair_lista_fotos(row, "cap")
                exibir_galeria_fotos(fotos_cap, legenda_base="Captação/EEAB")

                st.markdown("---")
            st.markdown("</div>", unsafe_allow_html=True)

    # 2. CARD ETA
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

                obs_e = buscar_campo_mult(row, ['OBSERVAÇÕES', 'Observações', 'Obs'])
                if dado_valido(obs_e): st.info(f"**Obs:** {obs_e}")

                fotos_eta = extrair_lista_fotos(row, "eta")
                exibir_galeria_fotos(fotos_eta, legenda_base="ETA")

                st.markdown("---")
            st.markdown("</div>", unsafe_allow_html=True)

    # 3. SEÇÃO POÇOS ARTESIANOS
    if not dados_poc.empty:
        st.header("🕳️ Sistema de Poços Artesianos")
        cols_pocos = st.columns(3)
        idx = 0
        for _, row in dados_poc.iterrows():
            col_atual = cols_pocos[idx % 3]
            with col_atual:
                id_pocio = buscar_campo_mult(row, ['Identificação do Poço', 'Poço']) or '—'
                st.markdown(f"<div class='card'><div class='card-title'>📍 {id_pocio}</div>", unsafe_allow_html=True)
                
                loc_p = buscar_campo_mult(row, ['Localidade/Região', 'Localidade'])
                if dado_valido(loc_p): st.write(f"**Região/Localidade:** {loc_p}")

                cc_poco = formatar_valor(buscar_campo_mult(row, ['CC Equatorial', 'CC Poço']))
                if dado_valido(cc_poco): st.write(f"**⚡ CC Equatorial:** {cc_poco}")

                pot_b = formatar_valor(buscar_campo_mult(row, ['Potência da Bomba (cv)']))
                if dado_valido(pot_b): st.write(f"**Potência:** {pot_b} cv")

                obs_p = buscar_campo_mult(row, ['OBSERVAÇÕES', 'Observações'])
                if dado_valido(obs_p): st.info(f"**Obs:** {obs_p}")

                fotos_poc = extrair_lista_fotos(row, "poc")
                exibir_galeria_fotos(fotos_poc, legenda_base="Poço")
                
                st.markdown("</div>", unsafe_allow_html=True)
            idx += 1

    # 4. GEOLOCALIZAÇÃO
    if not dados_geo.empty:
        pontos_mapa = []
        for _, r_g in dados_geo.iterrows():
            lat_f = converter_coordenada(buscar_campo_mult(r_g, ['Latitude', 'LATITUDE', 'Lat']))
            lon_f = converter_coordenada(buscar_campo_mult(r_g, ['Longitude', 'LONGITUDE', 'Long']))
            
            if lat_f is not None and lon_f is not None:
                nome_est = buscar_campo_mult(r_g, ['Unidade', 'UNIDADE', 'Descrição', 'Nome']) or 'Unidade Operacional'
                pontos_mapa.append({
                    'Unidade / Estrutura': str(nome_est),
                    'Latitude': lat_f,
                    'Longitude': lon_f,
                    'Google Maps': f"https://www.google.com/maps/search/?api=1&query={lat_f},{lon_f}"
                })

        if pontos_mapa:
            st.markdown("---")
            st.header("📍 Geolocalização das Unidades Operacionais")
            df_mapa = pd.DataFrame(pontos_mapa)
            
            col_mapa, col_lista = st.columns([1.2, 1])
            with col_mapa:
                st.map(df_mapa, latitude='Latitude', longitude='Longitude', zoom=11, use_container_width=True)
            with col_lista:
                st.dataframe(
                    df_mapa[['Unidade / Estrutura', 'Google Maps']],
                    column_config={
                        "Google Maps": st.column_config.LinkColumn("Rota GPS", display_text="🗺️ Abrir no Maps")
                    },
                    hide_index=True, use_container_width=True, height=380
                )
