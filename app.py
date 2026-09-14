import datetime
import os
import time
import unicodedata
import gspread
import oauth2client.service_account
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from oauth2client.service_account import ServiceAccountCredentials
from plotly.subplots import make_subplots


#
# CONFIGURAÇÃO DA PÁGINA E ESTILIZAÇÃO VISUAL
#
st.set_page_config(
    page_title="Painel de Cálculos CCOP CASAL",
    page_icon="🌊",
    layout="wide",
)


st.markdown(
    """
<style>
/* Oculta marca d'água e menus padrão do Streamlit */
div[data-testid="stStatusWidget"] { display: none !important; }
#MainMenu { visibility: hidden; }
footer { visibility: hidden; }
header { visibility: hidden; }
</style>
""",
    unsafe_allow_html=True,
)


#
# CONSTANTES GLOBAIS E REGRAS DE NEGÓCIO
#
CIDADES_PERMITIDAS = [
    "Campestre",
    "Colônia Leopoldina",
    "Ibateguara",
    "Severo",
    "Sumidouro",
    "Jacuípe",
    "Joaquim Gomes",
    "Joaq Gomes",
    "Jundiá",
    "Novo Lino",
    "Anadia",
    "Capela",
    "Mar Vermelho",
    "Maribondo",
    "Paulo Jacinto",
    "Pindoba",
    "Taquarana",
    "Japaratinga",
    "Maragogi",
    "Matriz",
    "Passo",
    "Porto de Pedras",
    "Tatuamunha",
]


CIDADES_MACRO_SAIDA = [
    "Campestre",
    "Jundiá",
    "Mar Vermelho",
    "Jacuípe",
    "Porto de Pedras",
    "Taquarana",
    "Anadia",
    "Maribondo",
]


ID_PLANILHA = "1GvwFCLdVhuwRfiVhMkhKBIYl-fpsIwuK52ycK3EuUB8"
ABA_VAZOES_NOME = "Histórico de Vazões - Telemetria"
ABA_NIVEIS_NOME = "Dados_Níveis"
ABA_CONFIG_NOME = "Config_Tetos"




def normalizar_texto(texto):
    """Remove acentos, converte para maiúsculas e remove espaços das pontas."""
    if not isinstance(texto, str):
        return ""
    return (
        "".join(
            c
            for c in unicodedata.normalize("NFD", texto)
            if unicodedata.category(c) != "Mn"
        )
        .upper()
        .strip()
    )




#
# CONEXÃO COM GOOGLE SHEETS
#
def conectar_google_sheets_completo():
    """Abre a planilha com tentativas automáticas em caso de erro de conexão API."""
    if not os.path.exists("credentials.json"):
        st.error(
            "Erro técnico: Arquivo 'credentials.json' não localizado na raiz do projeto."
        )
        return None, None, None


    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive",
    ]
    creds = ServiceAccountCredentials.from_json_keyfile_name(
        "credentials.json", scope
    )
    client = gspread.authorize(creds)
    planilha = None


    for tentativa in range(3):
        try:
            planilha = client.open_by_key(ID_PLANILHA)
            break
        except gspread.exceptions.APIError:
            if tentativa < 2:
                time.sleep(2)
                continue
            else:
                st.error(
                    " O serviço do Google Sheets está instável (Erro 503). Tente atualizar a página."
                )
                return None, None, None
        except Exception as e:
            st.error(f"Erro ao conectar ao Google Sheets: {e}")
            return None, None, None


    aba_vacoes = None
    aba_config = None
    aba_niveis = None


    if planilha:
        try:
            lista_abas = [w.title.strip() for w in planilha.worksheets()]
            if ABA_VAZOES_NOME in lista_abas:
                aba_vacoes = planilha.worksheet(ABA_VAZOES_NOME)


            if ABA_CONFIG_NOME in lista_abas:
                aba_config = planilha.worksheet(ABA_CONFIG_NOME)
            else:
                aba_config = planilha.add_worksheet(
                    title=ABA_CONFIG_NOME, rows="100", cols="2"
                )
                aba_config.append_row(["Sistema/Canal", "Teto Máximo"])


            if ABA_NIVEIS_NOME in lista_abas:
                aba_niveis = planilha.worksheet(ABA_NIVEIS_NOME)
        except Exception as e:
            st.error(f"Erro ao ler abas da planilha: {e}")


    return aba_vacoes, aba_config, aba_niveis




#
# BARRA LATERAL (SIDEBAR)
#
formatos_logo = [
    "logo.png",
    "logo.png.png",
    "logo.jpg",
    "logo.jpeg",
    "LOGO.PNG",
]


caminho_logo = next((f for f in formatos_logo if os.path.exists(f)), None)
if caminho_logo:
    st.sidebar.image(caminho_logo, use_container_width=True)


st.sidebar.markdown("---")
st.sidebar.title("Navegação")
aba_selecionada = st.sidebar.radio(
    "Escolha a tela:",
    [" Importar e Enviar Tudo", "Consultar Histórico"],
)


st.title(" Painel de Cálculos Diários")
st.markdown("### *Gestão e Telemetria Integrada de Sistemas e ETAs*")
st.write("")


#
# TELA 1: IMPORTAR E ENVIAR TUDO
#
if aba_selecionada == " Importar e Enviar Tudo":
    st.subheader("Carregar Planilhas de Telemetria para a Nuvem")
    up_col1, up_col2 = st.columns(2)


    with up_col1:
        st.markdown("#### Macromedição")
        uploaded_file = st.file_uploader(
            "Arraste aqui o arquivo CSV de Vazões/Totalizadores",
            type=["csv"],
            key="macro_file",
        )


    with up_col2:
        st.markdown("#### Níveis dos Reservatórios")
        uploaded_niveis_lista = st.file_uploader(
            "Arraste aqui os arquivos CSV de Níveis (Multi-polos permitidos)",
            type=["csv"],
            accept_multiple_files=True,
            key="nivel_file",
        )


    df_macro_pronto = None
    df_nivel_pronto = None
    colunas_vazao = []


    if uploaded_file is not None:
        try:
            df_macro_pronto = pd.read_csv(
                uploaded_file, sep=";", decimal=",", encoding="latin1"
            )
            df_macro_pronto.columns = df_macro_pronto.columns.str.strip()
            df_macro_pronto = df_macro_pronto.loc[
                :, ~df_macro_pronto.columns.str.contains("^Unnamed")
            ]


            df_macro_pronto["Data e Hora"] = (
                pd.to_datetime(
                    df_macro_pronto["Data e Hora"],
                    format="%Y-%m-%d %H:%M:%S",
                    errors="coerce",
                )
                .fillna(
                    pd.to_datetime(
                        df_macro_pronto["Data e Hora"],
                        format="%d/%m/%Y %H:%M:%S",
                        errors="coerce",
                    )
                )
                .fillna(
                    pd.to_datetime(
                        df_macro_pronto["Data e Hora"],
                        format="%Y/%m/%d %H:%M:%S",
                        errors="coerce",
                    )
                )
            )


            df_macro_pronto = df_macro_pronto.dropna(subset=["Data e Hora"])


            colunas_vazao = [
                col
                for col in df_macro_pronto.columns
                if "VAZAO" in normalizar_texto(col)
            ]


            if colunas_vazao:
                st.success(
                    f" Macromedição: Identificados {len(colunas_vazao)} sistemas de vazão prontos para envio!"
                )
            else:
                st.warning(
                    "! Arquivo carregado, mas nenhuma coluna contendo 'VAZÃO' foi identificada."
                )
        except Exception as e:
            st.error(f"Erro ao ler arquivo de macromedição: {e}")


    if uploaded_niveis_lista:
        dfs_polos = []
        for arquivo_nivel in uploaded_niveis_lista:
            try:
                df_n_bruto = pd.read_csv(
                    arquivo_nivel, sep=";", encoding="latin1"
                )
                df_n_bruto.columns = df_n_bruto.columns.str.strip()


                if "Data e Hora" in df_n_bruto.columns:
                    df_n_bruto["Data e Hora"] = pd.to_datetime(
                        df_n_bruto["Data e Hora"],
                        format="%d/%m/%Y %H:%M:%S",
                        errors="coerce",
                    ).fillna(
                        pd.to_datetime(
                            df_n_bruto["Data e Hora"],
                            dayfirst=True,
                            errors="coerce",
                        )
                    )
                    df_n_bruto = df_n_bruto.dropna(subset=["Data e Hora"])


                    colunas_validas = ["Data e Hora"] + [
                        col
                        for col in df_n_bruto.columns
                        if col != "Data e Hora"
                        and not col.startswith("Unnamed")
                    ]


                    df_filtrado_tempo = df_n_bruto[colunas_validas].copy()
                    for col in df_filtrado_tempo.columns:
                        if col != "Data e Hora":
                            df_filtrado_tempo[col] = pd.to_numeric(
                                df_filtrado_tempo[col]
                                .astype(str)
                                .str.replace(",", "."),
                                errors="coerce",
                            )


                    df_filtrado_tempo = df_filtrado_tempo.set_index("Data e Hora")
                    df_agrupado_10min = (
                        df_filtrado_tempo.resample("10min")
                        .mean()
                        .reset_index()
                    )
                    dfs_polos.append(df_agrupado_10min)
            except Exception as e:
                st.error(
                    f"Erro ao processar o arquivo de nível {arquivo_nivel.name}: {e}"
                )


        if dfs_polos:
            try:
                df_nivel_pronto = dfs_polos[0]
                for df_proximo in dfs_polos[1:]:
                    df_nivel_pronto = pd.merge(
                        df_nivel_pronto,
                        df_proximo,
                        on="Data e Hora",
                        how="outer",
                    )
                df_nivel_pronto = df_nivel_pronto.sort_values(
                    by="Data e Hora"
                ).reset_index(drop=True)


                st.success(
                    f" Níveis: {len(uploaded_niveis_lista)} arquivo(s) de polos integrados temporariamente!"
                )
            except Exception as e:
                st.error(f"Erro ao unificar as planilhas de níveis: {e}")


    if df_macro_pronto is not None or df_nivel_pronto is not None:
        st.write("")
        if st.button(
            "Salvar Dados Carregados no Google Sheets",
            type="primary",
            use_container_width=True,
        ):
            scope = [
                "https://spreadsheets.google.com/feeds",
                "https://www.googleapis.com/auth/drive",
            ]
            if os.path.exists("credentials.json"):
                creds = ServiceAccountCredentials.from_json_keyfile_name(
                    "credentials.json", scope
                )
                client = gspread.authorize(creds)
                try:
                    planilha_mae = client.open_by_key(ID_PLANILHA)
                except Exception as e:
                    st.error(
                        f"Não foi possível abrir a planilha mãe para gravação: {e}"
                    )
                    st.stop()


                if df_macro_pronto is not None and colunas_vazao:
                    with st.spinner(
                        "Enviando dados de Macromedição (Formato Americano)..."
                    ):
                        try:
                            aba_macro = planilha_mae.worksheet(ABA_VAZOES_NOME)
                            dados_atuais = aba_macro.get_all_values()


                            if not dados_atuais:
                                aba_macro.append_row(
                                    [
                                        "Data e Hora",
                                        "Sistema/Canal",
                                        "Vazão (m³/h)",
                                        "Totalizador (m³)",
                                    ]
                                )


                            novas_linhas_macro = []
                            for col_vazao in colunas_vazao:
                                col_totalizador_esperada = (
                                    col_vazao.replace("VAZÃO", "TOTALIZADOR")
                                    .replace("VAZAO", "TOTALIZADOR")
                                    .replace("(m³/h)", "(m³)")
                                    .replace("(M³/H)", "(M³)")
                                )


                                col_totalizador = (
                                    col_totalizador_esperada
                                    if col_totalizador_esperada
                                    in df_macro_pronto.columns
                                    else None
                                )


                                nome_canal_final = col_vazao.strip()


                                for _, row in df_macro_pronto.iterrows():
                                    dt_formatada_us = row[
                                        "Data e Hora"
                                    ].strftime("%Y-%m-%d %H:%M:%S")


                                    v_vazao = row[col_vazao]
                                    v_tot = (
                                        row[col_totalizador]
                                        if col_totalizador
                                        else ""
                                    )


                                    try:
                                        vazao_final = (
                                            float(v_vazao)
                                            if not pd.isna(v_vazao)
                                            and str(v_vazao)
                                            .strip()
                                            .lower()
                                            not in ["null", "nan", ""]
                                            else ""
                                        )
                                    except Exception:
                                        vazao_final = ""


                                    try:
                                        tot_final = (
                                            float(v_tot)
                                            if v_tot != ""
                                            and not pd.isna(v_tot)
                                            and str(v_tot)
                                            .strip()
                                            .lower()
                                            not in ["null", "nan", ""]
                                            else ""
                                        )
                                    except Exception:
                                        tot_final = ""


                                    novas_linhas_macro.append(
                                        [
                                            dt_formatada_us,
                                            nome_canal_final,
                                            vazao_final,
                                            tot_final,
                                        ]
                                    )


                            if novas_linhas_macro:
                                aba_macro.append_rows(novas_linhas_macro)
                                st.success(
                                    f"✅ Macromedição salva com sucesso na aba '{ABA_VAZOES_NOME}'!"
                                )
                        except Exception as e:
                            st.error(
                                f"Erro ao salvar macromedição no Sheets: {e}"
                            )


                if df_nivel_pronto is not None:
                    with st.spinner(
                        "Enviando e alinhando dados de Níveis nos Polos..."
                    ):
                        try:
                            lista_abas_existentes = [
                                w.title.strip()
                                for w in planilha_mae.worksheets()
                            ]


                            if ABA_NIVEIS_NOME in lista_abas_existentes:
                                aba_niveis = planilha_mae.worksheet(
                                    ABA_NIVEIS_NOME
                                )
                            else:
                                aba_niveis = planilha_mae.add_worksheet(
                                    title=ABA_NIVEIS_NOME,
                                    rows="5000",
                                    cols="100",
                                )
                                aba_niveis.append_row(
                                    df_nivel_pronto.columns.tolist()
                                )


                            dados_existentes = aba_niveis.get_all_values()
                            if dados_existentes:
                                cabecalho_real_nuvem = [
                                    c.strip() for c in dados_existentes[0]
                                ]
                                df_nivel_pronto["Data e Hora"] = df_nivel_pronto[
                                    "Data e Hora"
                                ].dt.strftime("%d/%m/%Y %H:%M:%S")


                                df_nivel_alinhado = df_nivel_pronto.reindex(
                                    columns=cabecalho_real_nuvem
                                ).fillna("")


                                linhas_niveis_envio = (
                                    df_nivel_alinhado.values.tolist()
                                )
                            else:
                                aba_niveis.append_row(
                                    df_nivel_pronto.columns.tolist()
                                )
                                df_nivel_pronto["Data e Hora"] = df_nivel_pronto[
                                    "Data e Hora"
                                ].dt.strftime("%d/%m/%Y %H:%M:%S")


                                df_nivel_pronto = df_nivel_pronto.fillna("")
                                linhas_niveis_envio = (
                                    df_nivel_pronto.values.tolist()
                                )


                            if linhas_niveis_envio:
                                aba_niveis.append_rows(linhas_niveis_envio)
                                st.success(
                                    f" Níveis dos polos sincronizados e salvos com sucesso em '{ABA_NIVEIS_NOME}'!"
                                )
                        except Exception as e:
                            st.error(f"Erro ao salvar níveis no Sheets: {e}")


                st.balloons()
                st.info("Processamento finalizado. A página será atualizada.")
                st.rerun()


#
# TELA 2: CONSULTAR HISTÓRICO
#
elif aba_selecionada == "Consultar Histórico":
    st.subheader("Filtro e Análise de Período Retroativo")


    tipo_analise = st.radio(
        "Selecione o tipo de dado para visualizar:",
        [" Vazão e Produção", " Níveis de Reservatórios"],
        horizontal=True,
    )


    aba_google, aba_config, aba_niveis_sheet = conectar_google_sheets_completo()


    todas_linhas_vazoes = (
        aba_google.get_all_values() if aba_google else []
    )
    linhas_config = aba_config.get_all_records() if aba_config else []


    dados_niveis_nuvem = []
    if aba_niveis_sheet is not None:
        try:
            dados_niveis_nuvem = aba_niveis_sheet.get_all_records()
        except Exception:
            dados_niveis_nuvem = []


    tetos_salvos = {
        str(r.get("Sistema/Canal", "")).strip(): float(
            r.get("Teto Máximo", 99999.0)
        )
        for r in linhas_config
        if r.get("Sistema/Canal")
    }


    # SUB-TELA: VAZÃO E PRODUÇÃO
    if tipo_analise == " Vazão e Produção":
        if len(todas_linhas_vazoes) > 1:
            dados_corpos = todas_linhas_vazoes[1:]
            df_nuvem = pd.DataFrame(
                dados_corpos,
                columns=[
                    "Data e Hora",
                    "Sistema/Canal",
                    "Vazão (m³/h)",
                    "Totalizador (m³)",
                ],
            )


            df_nuvem["Data e Hora"] = (
                pd.to_datetime(
                    df_nuvem["Data e Hora"],
                    format="%Y-%m-%d %H:%M:%S",
                    errors="coerce",
                )
                .fillna(
                    pd.to_datetime(
                        df_nuvem["Data e Hora"],
                        format="%d/%m/%Y %H:%M:%S",
                        errors="coerce",
                    )
                )
                .fillna(
                    pd.to_datetime(
                        df_nuvem["Data e Hora"],
                        format="%Y/%m/%d %H:%M:%S",
                        errors="coerce",
                    )
                )
            )


            df_nuvem = df_nuvem.dropna(subset=["Data e Hora"]).sort_values(
                by="Data e Hora"
            )
            df_nuvem["Data"] = df_nuvem["Data e Hora"].dt.date


            sistemas_disponiveis = sorted(
                df_nuvem["Sistema/Canal"].dropna().unique()
            )


            st.sidebar.markdown("---")
            st.sidebar.subheader(" Filtro de Picos (Teto Máximo)")


            tetos_sistemas = {}
            for sistema in sistemas_disponiveis:
                if not sistema.strip():
                    continue
                valor_padrao = tetos_salvos.get(sistema, 99999.0)
                tetos_sistemas[sistema] = st.sidebar.number_input(
                    f"Teto para {sistema}:",
                    min_value=0.0,
                    value=valor_padrao,
                    step=50.0,
                    key=f"teto_{sistema}",
                )


            if st.sidebar.button(" Salvar Tetos Permanentemente", type="primary"):
                if aba_config:
                    with st.spinner("Gravando limites..."):
                        aba_config.clear()
                        aba_config.append_row(["Sistema/Canal", "Teto Máximo"])
                        novas_configs = [
                            [sis, teto]
                            for sis, teto in tetos_sistemas.items()
                        ]
                        aba_config.append_rows(novas_configs)
                        st.sidebar.success(" Limites atualizados na nuvem!")


            if sistemas_disponiveis:
                sistema_filtro = st.selectbox(
                    "Selecione qual ETA/Sistema deseja analisar:",
                    sistemas_disponiveis,
                )


                col1, col2 = st.columns(2)
                data_maxima = (
                    df_nuvem["Data"].max()
                    if not df_nuvem.empty
                    else datetime.date.today()
                )
                data_inicio_padrao = data_maxima - datetime.timedelta(days=3)


                data_inicio = col1.date_input(
                    "Data Inicial:",
                    value=data_inicio_padrao,
                    format="DD/MM/YYYY",
                    key="vazao_dt_ini",
                )


                data_fim = col2.date_input(
                    "Data Final:",
                    value=data_maxima,
                    format="DD/MM/YYYY",
                    key="vazao_dt_fim",
                )


                df_nuvem["Vazão (m³/h)"] = pd.to_numeric(
                    df_nuvem["Vazão (m³/h)"]
                    .astype(str)
                    .str.replace(",", "."),
                    errors="coerce",
                )


                df_nuvem["Totalizador (m³)"] = pd.to_numeric(
                    df_nuvem["Totalizador (m³)"]
                    .astype(str)
                    .str.replace(",", "."),
                    errors="coerce",
                )


                df_sistema_completo = df_nuvem[
                    df_nuvem["Sistema/Canal"] == sistema_filtro
                ].copy()
                df_sistema_completo = df_sistema_completo.sort_values(
                    by="Data e Hora"
                )


                df_filtrado = df_sistema_completo[
                    (df_sistema_completo["Data"] >= data_inicio)
                    & (df_sistema_completo["Data"] <= data_fim)
                ].copy()


                if not df_filtrado.empty:
                    resumo_dias = []
                    datas_unicas = sorted(df_filtrado["Data"].unique())
                    teto_atual = tetos_sistemas.get(
                        sistema_filtro, 99999.0
                    )


                    tot_periodo = df_filtrado[
                        df_filtrado["Totalizador (m³)"] > 0
                    ]["Totalizador (m³)"].dropna()


                    if len(tot_periodo) >= 2:
                        total_volume_physical = float(
                            tot_periodo.iloc[-1]
                        ) - float(tot_periodo.iloc[0])
                        if total_volume_physical < 0:
                            total_volume_physical = abs(total_volume_physical)
                    else:
                        total_volume_physical = 0.0


                    tot_ultimo_dia_anterior = None


                    for data in datas_unicas:
                        dt_str = data.strftime("%d/%m/%Y")
                        df_dia = (
                            df_filtrado[df_filtrado["Data"] == data]
                            .drop_duplicates(subset=["Data e Hora"])
                            .sort_values("Data e Hora")
                        )


                        df_vazao_valida = df_dia[
                            df_dia["Vazão (m³/h)"].notna()
                        ].copy()


                        if df_vazao_valida.empty:
                            continue


                        df_vazao_valida["intervalo_horas"] = (
                            df_vazao_valida["Data e Hora"]
                            .diff()
                            .dt.total_seconds()
                            / 3600.0
                        ).fillna(10.0 / 60.0)


                        df_vazao_valida["intervalo_horas"] = df_vazao_valida[
                            "intervalo_horas"
                        ].clip(upper=1.0)


                        df_fora_do_ar = df_vazao_valida[
                            (df_vazao_valida["Vazão (m³/h)"] < 0)
                            | (df_vazao_valida["Vazão (m³/h)"] > teto_atual)
                        ]


                        df_ativas = df_vazao_valida[
                            (df_vazao_valida["Vazão (m³/h)"] >= 0)
                            & (df_vazao_valida["Vazão (m³/h)"] <= teto_atual)
                        ]


                        horas_fora_do_ar = min(
                            24.0,
                            float(df_fora_do_ar["intervalo_horas"].sum()),
                        )
                        horas_funcionamento = min(
                            24.0, float(df_ativas["intervalo_horas"].sum())
                        )


                        media_vazao = (
                            df_ativas["Vazão (m³/h)"].mean()
                            if not df_ativas.empty
                            else 0.0
                        )


                        volume_calculado_vazao = (
                            media_vazao * horas_funcionamento
                        )


                        tot_validos_dia = df_dia[
                            df_dia["Totalizador (m³)"] > 0
                        ]["Totalizador (m³)"].dropna()


                        if not tot_validos_dia.empty:
                            ultimo_dia = float(tot_validos_dia.iloc[-1])
                            primeiro_dia = float(tot_validos_dia.iloc[0])


                            if tot_ultimo_dia_anterior is not None:
                                volume_diario_totalizador = (
                                    ultimo_dia - tot_ultimo_dia_anterior
                                )
                            else:
                                volume_diario_totalizador = (
                                    ultimo_dia - primeiro_dia
                                )


                            if volume_diario_totalizador < 0:
                                volume_diario_totalizador = 0.0


                            tot_ultimo_dia_anterior = ultimo_dia
                        else:
                            volume_diario_totalizador = 0.0


                        resumo_dias.append(
                            {
                                "Data": dt_str,
                                "Vazão Média (m³/h)": round(media_vazao, 2),
                                "Horas Ativas Reais": round(
                                    horas_funcionamento, 1
                                ),
                                "Tempo Fora do Ar (h)": round(
                                    horas_fora_do_ar, 1
                                ),
                                "Vol. Diário Totalizador (m³)": round(
                                    volume_diario_totalizador, 2
                                ),
                                "Vol. Calculado Vazão (m³)": round(
                                    volume_calculado_vazao, 2
                                ),
                            }
                        )


                    if resumo_dias:
                        df_resumo = pd.DataFrame(resumo_dias)
                    else:
                        df_resumo = pd.DataFrame(
                            columns=[
                                "Data",
                                "Vazão Média (m³/h)",
                                "Horas Ativas Reais",
                                "Tempo Fora do Ar (h)",
                                "Vol. Diário Totalizador (m³)",
                                "Vol. Calculado Vazão (m³)",
                            ]
                        )


                    total_volume_calculated = (
                        df_resumo["Vol. Calculado Vazão (m³)"].sum()
                        if not df_resumo.empty
                        else 0.0
                    )
                    total_horas_ativas = (
                        df_resumo["Horas Ativas Reais"].sum()
                        if not df_resumo.empty
                        else 0.0
                    )
                    total_horas_fora = (
                        df_resumo["Tempo Fora do Ar (h)"].sum()
                        if not df_resumo.empty
                        else 0.0
                    )


                    linha_total = pd.DataFrame(
                        [
                            {
                                "Data": "TOTAL DO PERÍODO",
                                "Vazão Média (m³/h)": "",
                                "Horas Ativas Reais": round(
                                    total_horas_ativas, 1
                                ),
                                "Tempo Fora do Ar (h)": round(
                                    total_horas_fora, 1
                                ),
                                "Vol. Diário Totalizador (m³)": round(
                                    total_volume_physical, 2
                                ),
                                "Vol. Calculado Vazão (m³)": round(
                                    total_volume_calculated, 2
                                ),
                            }
                        ]
                    )


                    df_resumo_com_total = pd.concat(
                        [df_resumo, linha_total], ignore_index=True
                    )


                    st.write("")
                    st.subheader(
                        f"📊 Relatório Consolidado do Período: {sistema_filtro}"
                    )


                    c_card1, c_card2 = st.columns(2)
                    v_phy_str = (
                        f"{total_volume_physical:,.2f}"
                        .replace(",", "X")
                        .replace(".", ",")
                        .replace("X", ".")
                    )
                    v_calc_str = (
                        f"{total_volume_calculated:,.2f}"
                        .replace(",", "X")
                        .replace(".", ",")
                        .replace("X", ".")
                    )


                    c_card1.metric(
                        label="📦 SOMA Totalizador do Período Selecionado",
                        value=f"{v_phy_str} m³",
                    )
                    c_card2.metric(
                        label="⚡ SOMA Calculada por Vazão no Período",
                        value=f"{v_calc_str} m³",
                    )


                    st.dataframe(
                        df_resumo_com_total,
                        use_container_width=True,
                        hide_index=True,
                    )


                    df_grafico = df_filtrado[
                        (df_filtrado["Vazão (m³/h)"] >= 0)
                        & (df_filtrado["Vazão (m³/h)"] <= teto_atual)
                    ]


                    if not df_grafico.empty:
                        fig_vazao = px.line(
                            df_grafico,
                            x="Data e Hora",
                            y="Vazão (m³/h)",
                            title=f"Comportamento Contínuo da Vazão ({sistema_filtro})",
                        )
                        fig_vazao.update_traces(line_color="#1f77b4")
                        st.plotly_chart(
                            fig_vazao, use_container_width=True
                        )


                    if not df_resumo.empty:
                        fig_volume = px.bar(
                            df_resumo,
                            x="Data",
                            y="Vol. Diário Totalizador (m³)",
                            title="Volume Líquido Diário Produzido (m³)",
                            text_auto=".2f",
                        )
                        st.plotly_chart(
                            fig_volume, use_container_width=True
                        )
                else:
                    st.warning(
                        "Nenhum dado encontrado para os filtros selecionados."
                    )
        else:
            st.warning("Não há canais de macromedição registrados.")


    # SUB-TELA: NÍVEIS DE RESERVATÓRIOS
    elif tipo_analise == " Níveis de Reservatórios":
        if dados_niveis_nuvem:
            df_n_nuvem = pd.DataFrame(dados_niveis_nuvem)


            if "Data e Hora" in df_n_nuvem.columns:
                df_n_nuvem["Data e Hora"] = pd.to_datetime(
                    df_n_nuvem["Data e Hora"],
                    format="%d/%m/%Y %H:%M:%S",
                    errors="coerce",
                ).fillna(
                    pd.to_datetime(
                        df_n_nuvem["Data e Hora"],
                        format="%Y-%m-%d %H:%M:%S",
                        errors="coerce",
                    )
                )


                df_n_nuvem = df_n_nuvem.dropna(subset=["Data e Hora"]).sort_values(
                    by="Data e Hora"
                )
                df_n_nuvem["Data"] = df_n_nuvem["Data e Hora"].dt.date


                sensores_disponiveis = sorted(
                    [
                        c
                        for c in df_n_nuvem.columns
                        if c not in ["Data e Hora", "Data"]
                    ]
                )


                locais_limpos = sorted(
                    list(
                        set(
                            [
                                s.replace("(m)", "")
                                .replace("(%)", "")
                                .replace("Nível", "")
                                .replace("Nivel", "")
                                .strip()
                                for s in sensores_disponiveis
                            ]
                        )
                    )
                )


                if locais_limpos:
                    locais_selecionados = st.multiselect(
                        "Selecione qual(is) Local(is)/Reservatório(s) deseja analisar e comparar:",
                        options=locais_limpos,
                        default=[locais_limpos[0]] if locais_limpos else None,
                    )


                    canais_vazao_disponiveis = []
                    if len(todas_linhas_vazoes) > 1:
                        df_v_aux = pd.DataFrame(
                            todas_linhas_vazoes[1:],
                            columns=[
                                "Data e Hora",
                                "Sistema/Canal",
                                "Vazão (m³/h)",
                                "Totalizador (m³)",
                            ],
                        )
                        canais_vazao_disponiveis = sorted(
                            df_v_aux["Sistema/Canal"]
                            .dropna()
                            .unique()
                            .tolist()
                        )


                    vazao_selecionada = st.selectbox(
                        "Deseja incluir a Vazão de algum sistema neste mesmo gráfico? (Opcional)",
                        options=["[Não incluir vazão]"] + canais_vazao_disponiveis,
                    )


                    cn1, cn2 = st.columns(2)
                    d_n_max = (
                        df_n_nuvem["Data"].max()
                        if not df_n_nuvem.empty
                        else datetime.date.today()
                    )
                    d_n_ini_padrao = d_n_max - datetime.timedelta(days=3)


                    d_n_ini = cn1.date_input(
                        "Data Inicial do Nível:",
                        value=d_n_ini_padrao,
                        format="DD/MM/YYYY",
                        key="nivel_dt_ini",
                    )


                    d_n_fim = cn2.date_input(
                        "Data Final do Nível:",
                        value=d_n_max,
                        format="DD/MM/YYYY",
                        key="nivel_dt_fim",
                    )


                    if locais_selecionados:
                        df_n_filtrado = df_n_nuvem[
                            (df_n_nuvem["Data"] >= d_n_ini)
                            & (df_n_nuvem["Data"] <= d_n_fim)
                        ].copy()


                        if not df_n_filtrado.empty:
                            st.subheader(
                                "✓ Monitoramento Integrado e Comparativo de Níveis"
                            )


                            fig_m = make_subplots(
                                specs=[[{"secondary_y": True}]]
                            )
                            dados_m_plotados = False


                            for local in locais_selecionados:
                                col_encontrada = None
                                for col_bruta in sensores_disponiveis:
                                    if local in col_bruta and "(%)" not in col_bruta:
                                        col_encontrada = col_bruta
                                        break


                                if col_encontrada and col_encontrada in df_n_filtrado.columns:
                                    df_n_filtrado[col_encontrada] = pd.to_numeric(
                                        df_n_filtrado[col_encontrada]
                                        .astype(str)
                                        .str.replace(",", "."),
                                        errors="coerce",
                                    )


                                    fig_m.add_trace(
                                        go.Scatter(
                                            x=df_n_filtrado["Data e Hora"],
                                            y=df_n_filtrado[col_encontrada],
                                            name=f"Nível {local} (m)",
                                            mode="lines",
                                        ),
                                        secondary_y=False,
                                    )
                                    dados_m_plotados = True


                            df_v_plot = pd.DataFrame()
                            if (
                                vazao_selecionada != "[Não incluir vazão]"
                                and len(todas_linhas_vazoes) > 1
                            ):
                                df_v_plot = pd.DataFrame(
                                    todas_linhas_vazoes[1:],
                                    columns=[
                                        "Data e Hora",
                                        "Sistema/Canal",
                                        "Vazão (m³/h)",
                                        "Totalizador (m³)",
                                    ],
                                )


                                df_v_plot["Data e Hora"] = pd.to_datetime(
                                    df_v_plot["Data e Hora"],
                                    errors="coerce",
                                )


                                df_v_plot = df_v_plot[
                                    (df_v_plot["Sistema/Canal"] == vazao_selecionada)
                                    & (df_v_plot["Data e Hora"].dt.date >= d_n_ini)
                                    & (df_v_plot["Data e Hora"].dt.date <= d_n_fim)
                                ].copy()


                                df_v_plot["Vazão (m³/h)"] = pd.to_numeric(
                                    df_v_plot["Vazão (m³/h)"]
                                    .astype(str)
                                    .str.replace(",", "."),
                                    errors="coerce",
                                )


                                df_v_plot = df_v_plot[
                                    df_v_plot["Vazão (m³/h)"] >= 0
                                ].sort_values(by="Data e Hora")


                                if not df_v_plot.empty:
                                    fig_m.add_trace(
                                        go.Scatter(
                                            x=df_v_plot["Data e Hora"],
                                            y=df_v_plot["Vazão (m³/h)"],
                                            name=f"Vazão: ({vazao_selecionada})",
                                            mode="lines",
                                            line=dict(
                                                dash="dash",
                                                color="red",
                                                width=2.5,
                                            ),
                                        ),
                                        secondary_y=True,
                                    )


                            fig_m.update_layout(
                                title_text="Nível Contínuo em Metros (m) vs Comportamento de Vazão",
                                hovermode="x unified",
                                legend=dict(
                                    orientation="h",
                                    yanchor="bottom",
                                    y=-0.2,
                                    xanchor="right",
                                    x=1,
                                ),
                            )


                            fig_m.update_xaxes(title_text="Data e Hora")
                            fig_m.update_yaxes(
                                title_text="<b>Nível (m)</b>",
                                secondary_y=False,
                            )
                            fig_m.update_yaxes(
                                title_text="<b>Vazão (m³/h)</b>",
                                secondary_y=True,
                                overlaying="y",
                                side="right",
                            )


                            if dados_m_plotados:
                                st.plotly_chart(
                                    fig_m, use_container_width=True
                                )


                            #
                            # DETECÇÃO DE LAVAGENS E TRANSBORDOS
                            #
                            if vazao_selecionada != "[Não incluir vazão]" and not df_v_plot.empty:
                                st.markdown("---")
                                teto_limite = tetos_salvos.get(vazao_selecionada, 99999.0)


                                # ------------------------------------------
                                # 1. TABELA DE DETECÇÃO DAS LAVAGENS DE FILTRO
                                # ------------------------------------------
                                st.subheader("🧹 Tabela de Lavagens de Filtro Detectadas")


                                df_lavagem = df_v_plot.sort_values("Data e Hora").copy()
                                # Considera em lavagem se a vazão cair para menos de 10 m³/h
                                df_lavagem["em_lavagem"] = df_lavagem["Vazão (m³/h)"] < 10.0
                                df_lavagem["grupo"] = (df_lavagem["em_lavagem"] != df_lavagem["em_lavagem"].shift()).cumsum()


                                eventos_lavagem = []
                                for _, grupo in df_lavagem[df_lavagem["em_lavagem"]].groupby("grupo"):
                                    dt_inicio = grupo["Data e Hora"].min()
                                    dt_fim = grupo["Data e Hora"].max()
                                    duracao_seg = (dt_fim - dt_inicio).total_seconds()
                                    duracao_horas = duracao_seg / 3600.0


                                    # Eventos entre 3 minutos e 3 horas
                                    if 180 <= duracao_seg <= 10800:
                                        dia_evento = dt_inicio.date()
                                        vazoes_do_dia = df_v_plot[
                                            (df_v_plot["Data e Hora"].dt.date == dia_evento) &
                                            (df_v_plot["Vazão (m³/h)"] >= 10.0)
                                        ]["Vazão (m³/h)"]


                                        vazao_media_dia = vazoes_do_dia.mean() if not vazoes_do_dia.empty else 0.0
                                        vol_gasto = vazao_media_dia * duracao_horas


                                        eventos_lavagem.append({
                                            "Início da Lavagem": dt_inicio.strftime("%d/%m/%Y %H:%M:%S"),
                                            "Fim da Lavagem": dt_fim.strftime("%d/%m/%Y %H:%M:%S"),
                                            "Duração": f"{int(duracao_seg // 60)} min",
                                            "Vazão Média do Dia (m³/h)": round(vazao_media_dia, 2),
                                            "Vol. Gasto Estimado (m³)": round(vol_gasto, 2)
                                        })


                                if eventos_lavagem:
                                    df_tb_lavagens = pd.DataFrame(eventos_lavagem)
                                    total_vol_lavagens = df_tb_lavagens["Vol. Gasto Estimado (m³)"].sum()
                                    total_eventos_lav = len(df_tb_lavagens)


                                    m_col1, m_col2 = st.columns(2)
                                    m_col1.metric("Total de Lavagens no Período", f"{total_eventos_lav} eventos")
                                    m_col2.metric("Volume Total Estimado Gasto", f"{total_vol_lavagens:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") + " m³")


                                    linha_total_lav = pd.DataFrame([{
                                        "Início da Lavagem": "TOTAL DO PERÍODO",
                                        "Fim da Lavagem": "-",
                                        "Duração": "-",
                                        "Vazão Média do Dia (m³/h)": "",
                                        "Vol. Gasto Estimado (m³)": round(total_vol_lavagens, 2)
                                    }])


                                    df_exibir_lav = pd.concat([df_tb_lavagens, linha_total_lav], ignore_index=True)
                                    st.dataframe(df_exibir_lav, use_container_width=True, hide_index=True)
                                else:
                                    st.info("Nenhum evento característico de lavagem de filtro foi identificado no período.")


                                st.markdown("---")


# ------------------------------------------
# 2. TABELA DE DETECÇÃO DE TRANSBORDOS
# ------------------------------------------
st.subheader("🚨 Tabela de Transbordos Detectados")

# Limites por cidade (em metros)
LIMITES_TRANSBORDO = {
    "Colônia Leopoldina": 3.30,
    "Capela": 4.09,
    "Novo Lino": 4.30,
}

# Teto máximo físico plausível (qualquer valor > 5m é ruído da telemetria)
LIMITE_MAXIMO_FISICO = 5.0 

df_base = df_n_filtrado.copy() if "df_n_filtrado" in locals() and not df_n_filtrado.empty else None
cidade_atual = None

# 1. Identificação precisa do local selecionado
if df_base is not None:
    # Varre os valores e nomes de colunas do DF ativo buscando a palavra-chave da cidade
    conteudo_texto = " ".join(df_base.columns.astype(str)).lower()
    for col in df_base.select_dtypes(include=["object", "string"]).columns:
        conteudo_texto += " " + " ".join(df_base[col].dropna().astype(str).unique()).lower()

    for cidade in LIMITES_TRANSBORDO.keys():
        if cidade.lower() in conteudo_texto:
            cidade_atual = cidade
            break

# 2. Processamento do Transbordo
if cidade_atual and df_base is not None:
    teto_limite = LIMITES_TRANSBORDO[cidade_atual]

    # Identifica a coluna numérica do NÍVEL
    colunas_numericas = df_base.select_dtypes(include=["number"]).columns.tolist()
    col_nivel = None
    for col in colunas_numericas:
        if any(termo in col.lower() for termo in ["nível", "nivel", "cota"]):
            col_nivel = col
            break
    if not col_nivel and colunas_numericas:
        col_nivel = colunas_numericas[0]

    if col_nivel:
        df_transbordo = df_base.sort_values("Data e Hora").copy()
        df_transbordo[col_nivel] = pd.to_numeric(df_transbordo[col_nivel], errors="coerce")

        # CONDICIONAL: Transbordo real entre o limite (ex: 4.09m) e o teto máximo (5.00m)
        df_transbordo["em_transbordo"] = (
            (df_transbordo[col_nivel] > teto_limite) & 
            (df_transbordo[col_nivel] <= LIMITE_MAXIMO_FISICO)
        )

        df_transbordo["grupo"] = (
            df_transbordo["em_transbordo"] != df_transbordo["em_transbordo"].shift()
        ).cumsum()

        eventos_transbordo = []
        for _, grupo in df_transbordo[df_transbordo["em_transbordo"]].groupby("grupo"):
            dt_inicio = grupo["Data e Hora"].min()
            dt_fim = grupo["Data e Hora"].max()
            duracao_seg = (dt_fim - dt_inicio).total_seconds()
            duracao_horas = duracao_seg / 3600.0

            if duracao_seg >= 60:
                dia_evento = dt_inicio.date()
                
                vazao_media_dia = 0.0
                if "df_v_plot" in locals() and not df_v_plot.empty and "Vazão (m³/h)" in df_v_plot.columns:
                    vazoes_do_dia = df_v_plot[
                        (df_v_plot["Data e Hora"].dt.date == dia_evento)
                    ]["Vazão (m³/h)"]
                    vazao_media_dia = vazoes_do_dia.mean() if not vazoes_do_dia.empty else 0.0

                vol_transbordado = vazao_media_dia * duracao_horas

                eventos_transbordo.append({
                    "Início do Transbordo": dt_inicio.strftime("%d/%m/%Y %H:%M:%S"),
                    "Fim do Transbordo": dt_fim.strftime("%d/%m/%Y %H:%M:%S"),
                    "Duração": f"{int(duracao_seg // 60)} min",
                    "Nível Máximo (m)": round(grupo[col_nivel].max(), 2),
                    "Vazão Média do Dia (m³/h)": round(vazao_media_dia, 2),
                    "Vol. Transbordado (m³)": round(vol_transbordado, 2),
                })

        if eventos_transbordo:
            df_tb_transbordo = pd.DataFrame(eventos_transbordo)
            total_vol_transbordo = df_tb_transbordo["Vol. Transbordado (m³)"].sum()
            total_eventos_trans = len(df_tb_transbordo)

            t_col1, t_col2 = st.columns(2)
            t_col1.metric("Total de Ocorrências de Transbordo", f"{total_eventos_trans} eventos")
            t_col2.metric(
                "Volume Total Transbordado",
                f"{total_vol_transbordo:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") + " m³"
            )

            linha_total_trans = pd.DataFrame([{
                "Início do Transbordo": "TOTAL DO PERÍODO",
                "Fim do Transbordo": "-",
                "Duração": "-",
                "Nível Máximo (m)": "-",
                "Vazão Média do Dia (m³/h)": "",
                "Vol. Transbordado (m³)": round(total_vol_transbordo, 2),
            }])

            df_exibir_trans = pd.concat([df_tb_transbordo, linha_total_trans], ignore_index=True)
            st.dataframe(df_exibir_trans, use_container_width=True, hide_index=True)
        else:
            st.info(f"Nenhum evento de transbordo válido (entre {teto_limite:.2f}m e {LIMITE_MAXIMO_FISICO:.2f}m) foi identificado para {cidade_atual} no período.")
