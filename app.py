import streamlit as st
import pandas as pd
import requests
import io
import re
import base64

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

# Estilização CSS customizada para os cards e botão
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
    .sirius-container {
        display: flex;
        align-items: center;
        gap: 12px;
        background-color: #ffffff;
        border: 1px solid #007bff;
        padding: 8px 16px;
        border-radius: 8px;
        margin-bottom: 10px;
        width: fit-content;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
    }
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# FUNÇÕES UTILITÁRIAS E LEITURA DA PLANILHA (SISTEMA ORIGINAL)
# ==============================================================================

@st.cache_data(ttl=600)
def carregar_dados_planilha(caminho_arquivo="dados.xlsx"):
    """Carrega as abas da planilha original do projeto."""
    try:
        excel = pd.ExcelFile(caminho_arquivo)
        df_cap = pd.read_excel(excel, 'CAPTAÇÃO') if 'CAPTAÇÃO' in excel.sheet_names else pd.DataFrame()
        df_eta = pd.read_excel(excel, 'ETA') if 'ETA' in excel.sheet_names else pd.DataFrame()
        df_poc = pd.read_excel(excel, 'POÇOS') if 'POÇOS' in excel.sheet_names else pd.DataFrame()
        df_geo = pd.read_excel(excel, 'GEO') if 'GEO' in excel.sheet_names else pd.DataFrame()
        df_adu = pd.read_excel(excel, 'ADUTORAS') if 'ADUTORAS' in excel.sheet_names else pd.DataFrame()
        return df_cap, df_eta, df_poc, df_geo, df_adu
    except Exception as e:
        st.error(f"Erro ao carregar a planilha local/Google: {e}")
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

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

def get_image_base64(path_imagem):
    """Converte a imagem da logo para Base64 para exibição no HTML do botão."""
    try:
        with open(path_imagem, "rb") as image_file:
            encoded = base64.b64encode(image_file.read()).decode()
            return f"data:image/png;base64,{encoded}"
    except:
        return ""

# ==============================================================================
# CARREGAMENTO INICIAL
# ==============================================================================

df_cap, df_eta, df_poc, df_geo, df_adutoras = carregar_dados_planilha()

# Consolidação dos municípios disponíveis na planilha
municipios = set()
for df in [df_cap, df_eta, df_poc]:
    if not df.empty:
        col_mun = next((c for c in ['Município', 'MUNICÍPIO', 'Municipio', 'Cidade'] if c in df.columns), None)
        if col_mun:
            municipios.update(df[col_mun].dropna().astype(str).str.strip().str.upper().unique())

lista_municipios = sorted(list(municipios))

st.title("💧 Painel de Monitoramento Operacional")

if not lista_municipios:
    st.warning("Nenhum município localizado na planilha.")
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

    # --- CABEÇALHO DO MUNICÍPIO E BOTÃO DO SIRIUS INTEGRADO ---
    st.header(f"📍 Município: {municipio_selecionado}")

    img_sirius_b64 = get_image_base64("logo_sirius.png")
    
    col_btn_custom, col_espaco = st.columns([1.5, 2])
    with col_btn_custom:
        # Exibe a logo do Sirius
        if img_sirius_b64:
            st.markdown(f"""
            <div class="sirius-container">
                <img src="{img_sirius_b64}" style="height: 32px; width: auto;" alt="Sirius Integrado">
                <span style="font-weight: bold; color: #1e3a8a; font-size: 0.95rem;">Sirius Integrado</span>
            </div>
            """, unsafe_allow_html=True)
        
        # Botão interativo para puxar o histórico da TI
        if st.button(f"📜 Consultar Histórico no Sirius ({municipio_selecionado})", key="btn_sirius"):
            with st.spinner("Conectando ao Sirius Integrado e buscando histórico..."):
                try:
                    url_api = "https://unserrana.com.br/sirius/v1/wp-json/app/v1/data?tipo=app_get_dados_de_cidades"
                    res = requests.get(url_api, timeout=12)
                    
                    if res.status_code == 200:
                        dados_historico = res.json()
                        df_hist = pd.DataFrame(dados_historico)
                        
                        # Filtra pelo município atual se existir a coluna correspondente
                        col_m = next((c for c in ['Município', 'MUNICÍPIO', 'Municipio', 'Cidade', 'cidade'] if c in df_hist.columns), None)
                        if col_m:
                            df_hist = df_hist[df_hist[col_m].astype(str).str.strip().str.upper() == municipio_selecionado]
                        
                        st.success("Histórico recuperado com sucesso!")
                        with st.expander(f"📊 Registros Históricos de {municipio_selecionado}", expanded=True):
                            st.dataframe(df_hist, use_container_width=True)
                    else:
                        st.error(f"Erro na resposta do Sirius: Código {res.status_code}")
                except Exception as err:
                    st.error(f"Falha ao conectar com o link do Sirius Integrado: {err}")

    st.markdown("---")

    # ==============================================================================
    # EXIBIÇÃO DOS CARDS (CAPTAÇÃO / ETA / POÇOS)
    # ==============================================================================
    col_cap, col_eta = st.columns(2)

    # 1. CARD CAPTAÇÃO / EEAB
    with col_cap:
        if not dados_cap.empty:
            st.markdown("<div class='card'><div class='card-title'>🚰 CAPTAÇÃO / EEAB</div>", unsafe_allow_html=True)
            for _, row in dados_cap.iterrows():
                cc_eeab_da_eta = formatar_valor(buscar_campo_mult(row, ['CC Equatorial EEAB', 'CC EEAB']))
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
                tipo_reserva = buscar_campo_mult(row, ['EEAB - Tipo da Bomba Reserva', 'EAB - Tipo da Bomba Reserva', 'Tipo da Bomba Reserva'])
                pot_reserva = formatar_valor(buscar_campo_mult(row, ['EEAB - Potência Reserva (cv)', 'Potência Reserva']))
                vaz_reserva = formatar_valor(buscar_campo_mult(row, ['EEAB - Vazão Reserva (m³/h)', 'Vazão Reserva']))
                alt_reserva = formatar_valor(buscar_campo_mult(row, ['EEAB - Altura Manométrica Reserva (mca)', 'Altura Manométrica Reserva']))

                if dado_valido(possui_reserva):
                    txt_res = f"**Bomba Reserva:** {possui_reserva}"
                    if dado_valido(tipo_reserva): txt_res += f" ({tipo_reserva})"
                    if dado_valido(pot_reserva): txt_res += f" | Potência: {pot_reserva} cv"
                    if dado_valido(vaz_reserva): txt_res += f" | Vazão: {vaz_reserva} m³/h"
                    if dado_valido(alt_reserva): txt_res += f" | Altura: {alt_reserva} mca"
                    st.write(txt_res)

                crivo = buscar_campo_mult(row, ['Captação - Possui Crivo', 'Possui Crivo'])
                mat_crivo = buscar_campo_mult(row, ['Captação - Material Crivo', 'Material Crivo'])
                diam_crivo = formatar_valor(buscar_campo_mult(row, ['Captação - Diâmetro Crivo (mm)']))
                if dado_valido(crivo):
                    txt_c = f"**Possui Crivo:** {crivo}"
                    if dado_valido(diam_crivo): txt_c += f" ({diam_crivo} mm)"
                    if dado_valido(mat_crivo): txt_c += f" - {mat_crivo}"
                    st.write(txt_c)

                diam = formatar_valor(buscar_campo_mult(row, ['Adutora EEAB até ETA - Diâmetro (mm)']))
                comp = formatar_valor(buscar_campo_mult(row, ['Adutora EEAB até ETA - Comprimento (m)']))
                mat_adu = buscar_campo_mult(row, ['Adutora EEAB até ETA - Material'])
                if dado_valido(diam) or dado_valido(comp):
                    txt_adu = "**Adutora EEAB ➔ ETA:**"
                    if dado_valido(diam): txt_adu += f" Diâmetro {diam} mm"
                    if dado_valido(mat_adu): txt_adu += f" ({mat_adu})"
                    if dado_valido(comp): txt_adu += f" | Comprimento: {comp} m"
                    st.write(txt_adu)

                obs_c = buscar_campo_mult(row, ['OBSERVAÇÕES', 'Observações', 'Obs', 'OBS', 'OBSERVAÇÃO', 'Observacao'])
                if dado_valido(obs_c): st.info(f"**Obs:** {obs_c}")

                fotos_cap = extrair_lista_fotos(row, "cap")
                exibir_galeria_fotos(fotos_cap, legenda_base="Captação/EEAB")

                st.markdown("---")
            st.markdown("</div>", unsafe_allow_html=True)

    # 2. CARD ESTAÇÃO DE TRATAMENTO DE ÁGUA (ETA)
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

                # Bombas de Saturação
                sat1_tipo = buscar_campo_mult(row, ['Bomba de saturação 01 - Tipo', 'Bomba de saturacao 01 - Tipo'])
                sat1_alt = formatar_valor(buscar_campo_mult(row, ['Bomba de saturação 01 - Altura Manométrica 01 (mca)']))
                sat1_pot = formatar_valor(buscar_campo_mult(row, ['Bomba de saturação 01 - Potência 01 (cv)']))
                sat1_vaz = formatar_valor(buscar_campo_mult(row, ['Bomba de saturação 01 - Vazão 01 (m³/h)']))

                if dado_valido(sat1_tipo) or dado_valido(sat1_pot) or dado_valido(sat1_vaz) or dado_valido(sat1_alt):
                    txt_sat1 = "**Bomba de Saturação 01:**"
                    if dado_valido(sat1_tipo): txt_sat1 += f" {sat1_tipo}"
                    if dado_valido(sat1_pot): txt_sat1 += f" | Potência: {sat1_pot} cv"
                    if dado_valido(sat1_vaz): txt_sat1 += f" | Vazão: {sat1_vaz} m³/h"
                    if dado_valido(sat1_alt): txt_sat1 += f" | Altura: {sat1_alt} mca"
                    st.write(txt_sat1)

                # Bombas de Lavagem
                b1_tipo = buscar_campo_mult(row, ['Bomba de lavagem 01 - Tipo'])
                b1_alt = formatar_valor(buscar_campo_mult(row, ['Bomba de lavagem 01 - Altura Manométrica 01 (mca)']))
                b1_pot = formatar_valor(buscar_campo_mult(row, ['Bomba de lavagem 01 - Potência 01 (cv)']))
                b1_vaz = formatar_valor(buscar_campo_mult(row, ['Bomba de lavagem 01 - Vazão 01 (m³/h)']))

                if dado_valido(b1_tipo) or dado_valido(b1_pot) or dado_valido(b1_vaz) or dado_valido(b1_alt):
                    txt_b1 = "**Bomba de Lavagem 01:**"
                    if dado_valido(b1_tipo): txt_b1 += f" {b1_tipo}"
                    if dado_valido(b1_pot): txt_b1 += f" | Potência: {b1_pot} cv"
                    if dado_valido(b1_vaz): txt_b1 += f" | Vazão: {b1_vaz} m³/h"
                    if dado_valido(b1_alt): txt_b1 += f" | Altura: {b1_alt} mca"
                    st.write(txt_b1)

                pre_clor = buscar_campo_mult(row, ['Possui Pré-cloração', 'Possui Pre-cloracao'])
                if dado_valido(pre_clor): st.write(f"**Possui Pré-cloração:** {pre_clor}")

                prod_chem = buscar_campo_mult(row, ['Produto Químico Principal', 'Produto Quimico Principal'])
                if dado_valido(prod_chem): st.write(f"**Produtos Químicos:** {prod_chem}")

                obs_e = buscar_campo_mult(row, ['OBSERVAÇÕES', 'Observações', 'Obs', 'OBS', 'OBSERVAÇÃO', 'Observacao'])
                if dado_valido(obs_e): st.info(f"**Obs:** {obs_e}")

                fotos_eta = extrair_lista_fotos(row, "eta")
                exibir_galeria_fotos(fotos_eta, legenda_base="ETA")

                st.markdown("---")
            st.markdown("</div>", unsafe_allow_html=True)

    # 3. SEÇÃO DE ADUTORAS INTERLIGADAS
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

    # 4. SEÇÃO POÇOS ARTESIANOS
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

                loc_poco = buscar_campo_mult(row, ['Localização do Poço', 'Localizacao do Poco', 'Localização'])
                if dado_valido(loc_poco): st.write(f"**Localização:** {loc_poco}")

                cc_poco = formatar_valor(buscar_campo_mult(row, ['CC Equatorial', 'CC Poço', 'Código do Cliente']))
                if dado_valido(cc_poco): st.write(f"**⚡ CC Equatorial:** {cc_poco}")

                pot_b = formatar_valor(buscar_campo_mult(row, ['Potência da Bomba (cv)', 'Potência (cv)']))
                alt_b = formatar_valor(buscar_campo_mult(row, ['Altura da Bomba (mca)', 'Altura (mca)']))
                vaz_b = formatar_valor(buscar_campo_mult(row, ['Vazão (m³/h)', 'Vazão']))
                
                if dado_valido(pot_b): st.write(f"**Potência da Bomba:** {pot_b} cv")
                if dado_valido(alt_b): st.write(f"**Altura da Bomba:** {alt_b} mca")
                if dado_valido(vaz_b): st.write(f"**Vazão Cadastrada:** {vaz_b} m³/h")

                obs_p = buscar_campo_mult(row, ['OBSERVAÇÕES', 'Observações', 'Obs'])
                if dado_valido(obs_p): st.info(f"**Obs:** {obs_p}")

                fotos_poc = extrair_lista_fotos(row, "poc")
                exibir_galeria_fotos(fotos_poc, legenda_base="Poço")
                
                st.markdown("</div>", unsafe_allow_html=True)
            idx += 1

    if dados_cap.empty and dados_eta.empty and dados_poc.empty:
        st.info("Nenhuma estrutura localizada para este município nos registros da planilha.")

    # 5. SEÇÃO DE GEOLOCALIZAÇÃO
    if not dados_geo.empty:
        pontos_mapa = []
        for _, r_g in dados_geo.iterrows():
            lat_f = converter_coordenada(buscar_campo_mult(r_g, ['Latitude', 'LATITUDE', 'Lat']))
            lon_f = converter_coordenada(buscar_campo_mult(r_g, ['Longitude', 'LONGITUDE', 'Long', 'Lon']))
            
            if lat_f is not None and lon_f is not None:
                nome_est = buscar_campo_mult(r_g, ['Unidade', 'UNIDADE', 'Descrição', 'Estrutura', 'Nome']) or 'Unidade Operacional'
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
                st.markdown("##### 📌 Unidades Mapeadas")
                st.dataframe(
                    df_mapa[['Unidade / Estrutura', 'Google Maps']],
                    column_config={
                        "Unidade / Estrutura": st.column_config.TextColumn("Unidade Operacional", help="Nome da unidade"),
                        "Google Maps": st.column_config.LinkColumn("Rota GPS", display_text="🗺️ Abrir no Maps")
                    },
                    hide_index=True,
                    use_container_width=True,
                    height=380
                )
