import datetime
import os
import time
import unicodedata
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from google.cloud import bigquery
from google.oauth2 import service_account
from plotly.subplots import make_subplots

#
# CONFIGURAÇÃO DA PÁGINA E ESTILIZAÇÃO VISUAL
#
st.set_page_config(
    page_title="Painel de Cálculos CCOP CASAL",
    page_icon="🌊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Estilização via CSS na barra lateral
with st.sidebar:
    st.markdown("### Filtros")
    st.markdown(
        """
<style>
[data-testid="stSidebar"] { display: block !important; visibility: visible !important; }
[data-testid="collapsedControl"] { display: block !important; visibility: visible !important; }
#MainMenu { visibility: hidden; }
footer { visibility: hidden; }
div[data-testid="stStatusWidget"] { display: none !important; }
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

PROJECT_ID = "ccop-zml"
DATASET_ID = f"{PROJECT_ID}.telemetria"


def normalizar_texto(texto):
    if not isinstance(texto, str):
        return ""
    return "".join(
        c
        for c in unicodedata.normalize("NFD", texto)
        if unicodedata.category(c) != "Mn"
    ).upper().strip()


def filtrar_colunas_indesejadas(df):
    """
    Descarta colunas fantasma (Unnamed), Esgoto (EEE/ETE) e
    cidades/sistemas descontinuados.
    """
    if df is None or df.empty:
        return df

    # 1. Remover colunas vazias ou fantasma (Unnamed)
    df = df.loc[:, ~df.columns.str.contains("^Unnamed", na=False)]

    # 2. Termos e locais que não devem ir para o BigQuery
    termos_descarte = [
        "EEE",
        "ETE",
        "ESGOTO",
        "E.E.E.",
        "E.T.E.",
        "BRANQUINHA",
        "PORTO CALVO",
        "CHA PRETA",
        "TAQUARI",
        "SAO LUIZ DO QUITUNDE",
        "SAO MIGUEL DOS MILAGRES",
        "UNIÃO DOS PALMARES",
    ]

    colunas_para_remover = [
        col
        for col in df.columns
        if any(termo in normalizar_texto(col) for termo in termos_descarte)
    ]

    if colunas_para_remover:
        df = df.drop(columns=colunas_para_remover, errors="ignore")

    return df


#
# CONEXÃO COM O GOOGLE BIGQUERY
#
@st.cache_resource
def conectar_bigquery():
    if not os.path.exists("credentials.json"):
        st.error(
            "Erro técnico: Arquivo 'credentials.json' não localizado na raiz do projeto."
        )
        return None
    try:
        creds = service_account.Credentials.from_service_account_file(
            "credentials.json"
        )
        client = bigquery.Client(credentials=creds, project=PROJECT_ID)
        return client
    except Exception as e:
        st.error(f"Erro ao conectar ao BigQuery: {e}")
        return None


client = conectar_bigquery()

#
# BARRA LATERAL (SIDEBAR)
#
formatos_logo = ["logo.png", "logo.png.png", "logo.jpg", "logo.jpeg", "LOGO.PNG"]
caminho_logo = next((f for f in formatos_logo if os.path.exists(f)), None)

if caminho_logo:
    st.sidebar.image(caminho_logo, use_container_width=True)

st.sidebar.markdown("---")
st.sidebar.title("Navegação")
aba_selecionada = st.sidebar.radio(
    "Escolha a tela:", ["Importar e Enviar Tudo", "Consultar Histórico"]
)

st.title("Painel de Cálculos Diários")
st.markdown("### *Gestão e Telemetria Integrada de Sistemas e ETAS*")
st.write("")

#
# TELA 1: IMPORTAR E ENVIAR TUDO
#
if aba_selecionada == "Importar e Enviar Tudo":
    st.subheader("Carregar Planilhas de Telemetria para a Nuvem (BigQuery)")
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
            df_macro_pronto = filtrar_colunas_indesejadas(df_macro_pronto)

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
                    f"Macromedição: Identificados {len(colunas_vazao)} sistemas de vazão prontos para envio!"
                )
            else:
                st.warning(
                    "Arquivo carregado, mas nenhuma coluna válida contendo 'VAZÃO' foi identificada."
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
                df_n_bruto = filtrar_colunas_indesejadas(df_n_bruto)

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

                    df_filtrado_tempo = df_filtrado_tempo.set_index(
                        "Data e Hora"
                    )
                    df_agrupado_10min = (
                        df_filtrado_tempo.resample("10min")
                        .mean()
                        .reset_index()
                    )
                    dfs_polos.append(df_agrupado_10min)
            except Exception as e:
                st.error(
                    f"Erro ao processar o arquivo de nível ({arquivo_nivel.name}): {e}"
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
                    f"Níveis: {len(uploaded_niveis_lista)} arquivo(s) de polos integrados temporariamente!"
                )
            except Exception as e:
                st.error(f"Erro ao unificar as planilhas de níveis: {e}")

    if df_macro_pronto is not None or df_nivel_pronto is not None:
        st.write("")
        if st.button(
            "Salvar Dados Carregados no BigQuery",
            type="primary",
            use_container_width=True,
        ):
            if not client:
                st.error("Conexão com o BigQuery indisponível.")
                st.stop()

            # Envio de Macromedição
            if df_macro_pronto is not None and colunas_vazao:
                with st.spinner(
                    "Enviando dados de Macromedição para o BigQuery..."
                ):
                    try:
                        novas_linhas_macro = []
                        for col_vazao in colunas_vazao:
                            col_totalizador_esperada = (
                                col_vazao.replace("VAZÃO", "TOTALIZADOR")
                                .replace("VAZAO", "TOTALIZADOR")
                                .replace("(m³/h)", "(m³)")
                                .replace("(M³/H)", "(M³)")
                            )
                            col_tot = (
                                col_totalizador_esperada
                                if col_totalizador_esperada
                                in df_macro_pronto.columns
                                else None
                            )
                            nome_canal = col_vazao.strip()

                            for _, row in df_macro_pronto.iterrows():
                                v_vazao = pd.to_numeric(
                                    row[col_vazao], errors="coerce"
                                )
                                v_tot = (
                                    pd.to_numeric(row[col_tot], errors="coerce")
                                    if col_tot
                                    else None
                                )

                                novas_linhas_macro.append(
                                    {
                                        "data_hora": row["Data e Hora"],
                                        "sistema_canal": nome_canal,
                                        "vazao_m3h": (
                                            float(v_vazao)
                                            if pd.notna(v_vazao)
                                            else None
                                        ),
                                        "totalizador_m3": (
                                            float(v_tot)
                                            if pd.notna(v_tot)
                                            else None
                                        ),
                                    }
                                )

                        df_bq_vazao = pd.DataFrame(novas_linhas_macro)
                        table_vazao_id = f"{DATASET_ID}.tb_vazao"
                        job = client.load_table_from_dataframe(
                            df_bq_vazao, table_vazao_id
                        )
                        job.result()
                        st.success(
                            "Macromedição salva com sucesso no BigQuery!"
                        )
                    except Exception as e:
                        st.error(
                            f"Erro ao salvar macromedição no BigQuery: {e}"
                        )

            # Envio de Níveis
            if df_nivel_pronto is not None:
                with st.spinner(
                    "Enviando dados de Níveis para o BigQuery..."
                ):
                    try:
                        df_niveis_longo = df_nivel_pronto.melt(
                            id_vars=["Data e Hora"],
                            var_name="local_reservatorio",
                            value_name="nivel_m",
                        ).rename(columns={"Data e Hora": "data_hora"})

                        df_niveis_longo["nivel_m"] = pd.to_numeric(
                            df_niveis_longo["nivel_m"], errors="coerce"
                        )
                        df_niveis_longo = df_niveis_longo.dropna(
                            subset=["nivel_m"]
                        )

                        # Ajuste/Filtro de consistência de nível (-0.1 a 10m)
                        df_niveis_longo = df_niveis_longo[
                            (df_niveis_longo["nivel_m"] >= -0.1)
                            & (df_niveis_longo["nivel_m"] <= 10.0)
                        ]

                        table_niveis_id = f"{DATASET_ID}.tb_niveis"
                        job_n = client.load_table_from_dataframe(
                            df_niveis_longo, table_niveis_id
                        )
                        job_n.result()
                        st.success(
                            "Níveis dos reservatórios salvos com sucesso no BigQuery!"
                        )
                    except Exception as e:
                        st.error(f"Erro ao salvar níveis no BigQuery: {e}")

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
        ["Vazão e Produção", "Níveis de Reservatórios"],
        horizontal=True,
    )

    if not client:
        st.error("Sem conexão com o BigQuery.")
        st.stop()

    # Leitura dos tetos salvos
    try:
        query_tetos = f"SELECT sistema_canal, teto_maximo FROM `{DATASET_ID}.tb_config_tetos`"
        df_tetos = client.query(query_tetos).to_dataframe()
        tetos_salvos = dict(
            zip(df_tetos["sistema_canal"], df_tetos["teto_maximo"])
        )
    except Exception:
        tetos_salvos = {}

    # SUB-TELA: VAZÃO E PRODUÇÃO
    if tipo_analise == "Vazão e Produção":
        query_sistemas = f"SELECT DISTINCT sistema_canal FROM `{DATASET_ID}.tb_vazao` WHERE sistema_canal IS NOT NULL ORDER BY sistema_canal"
        sistemas_disponiveis = [
            r["sistema_canal"] for r in client.query(query_sistemas).result()
        ]

        st.sidebar.markdown("---")
        st.sidebar.subheader("Filtro de Picos (Teto Máximo)")

        tetos_sistemas = {}
        for sistema in sistemas_disponiveis:
            if not sistema.strip():
                continue
            valor_padrao = float(tetos_salvos.get(sistema, 99999.0))
            tetos_sistemas[sistema] = st.sidebar.number_input(
                f"Teto para {sistema}:",
                min_value=0.0,
                value=valor_padrao,
                step=50.0,
                key=f"teto_{sistema}",
            )

        if st.sidebar.button("Salvar Tetos Permanentemente", type="primary"):
            try:
                client.query(
                    f"DELETE FROM `{DATASET_ID}.tb_config_tetos` WHERE TRUE"
                ).result()
                df_novos_tetos = pd.DataFrame(
                    [
                        {
                            "sistema_canal": sis,
                            "teto_maximo": float(teto),
                        }
                        for sis, teto in tetos_sistemas.items()
                    ]
                )
                client.load_table_from_dataframe(
                    df_novos_tetos, f"{DATASET_ID}.tb_config_tetos"
                ).result()
                st.sidebar.success("Limites atualizados no BigQuery!")
            except Exception as e:
                st.sidebar.error(f"Erro ao salvar tetos: {e}")

        if sistemas_disponiveis:
            sistema_filtro = st.selectbox(
                "Selecione qual ETA/Sistema deseja analisar:",
                sistemas_disponiveis,
            )

            col1, col2 = st.columns(2)
            data_inicio = col1.date_input(
                "Data Inicial:",
                datetime.date.today() - datetime.timedelta(days=3),
                format="DD/MM/YYYY",
                key="vazao_dt_ini",
            )
            data_fim = col2.date_input(
                "Data Final:",
                datetime.date.today(),
                format="DD/MM/YYYY",
                key="vazao_dt_fim",
            )

            query_dados = f"""
            SELECT data_hora, sistema_canal, vazao_m3h, totalizador_m3
            FROM `{DATASET_ID}.tb_vazao`
            WHERE sistema_canal = @sistema
            AND DATE(data_hora) BETWEEN @data_ini AND @data_fim
            ORDER BY data_hora ASC
            """
            job_config = bigquery.QueryJobConfig(
                query_parameters=[
                    bigquery.ScalarQueryParameter(
                        "sistema", "STRING", sistema_filtro
                    ),
                    bigquery.ScalarQueryParameter(
                        "data_ini", "DATE", data_inicio
                    ),
                    bigquery.ScalarQueryParameter(
                        "data_fim", "DATE", data_fim
                    ),
                ]
            )
            df_filtrado = client.query(
                query_dados, job_config=job_config
            ).to_dataframe()

            if not df_filtrado.empty:
                df_filtrado["Data e Hora"] = pd.to_datetime(
                    df_filtrado["data_hora"]
                )
                df_filtrado["Data"] = df_filtrado["Data e Hora"].dt.date
                df_filtrado["Vazão (m³/h)"] = pd.to_numeric(
                    df_filtrado["vazao_m3h"], errors="coerce"
                )
                df_filtrado["Totalizador (m³)"] = pd.to_numeric(
                    df_filtrado["totalizador_m3"], errors="coerce"
                )

                teto_atual = tetos_sistemas.get(sistema_filtro, 99999.0)
                resumo_dias = []
                datas_unicas = sorted(df_filtrado["Data"].unique())

                tot_periodo = df_filtrado[df_filtrado["Totalizador (m³)"] > 0][
                    "Totalizador (m³)"
                ].dropna()
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
                        .fillna(10.0 / 60.0)
                        .clip(upper=1.0)
                    )

                    df_fora_do_ar = df_vazao_valida[
                        (df_vazao_valida["Vazão (m³/h)"] < 0)
                        | (df_vazao_valida["Vazão (m³/h)"] > teto_atual)
                    ]
                    df_ativas = df_vazao_valida[
                        (df_vazao_valida["Vazão (m³/h)"] >= 0)
                        & (df_vazao_valida["Vazão (m³/h)"] <= teto_atual)
                    ]

                    horas_fora_do_ar = min(
                        24.0, float(df_fora_do_ar["intervalo_horas"].sum())
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
                        horas_funcionamento * media_vazao
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
                            "Tempo Fora do Ar (h)": round(horas_fora_do_ar, 1),
                            "Vol. Diário Totalizador (m³)": round(
                                volume_diario_totalizador, 2
                            ),
                            "Vol. Calculado Vazão (m³)": round(
                                volume_calculado_vazao, 2
                            ),
                        }
                    )

                df_resumo = (
                    pd.DataFrame(resumo_dias)
                    if resumo_dias
                    else pd.DataFrame(
                        columns=[
                            "Data",
                            "Vazão Média (m³/h)",
                            "Horas Ativas Reais",
                            "Tempo Fora do Ar (h)",
                            "Vol. Diário Totalizador (m³)",
                            "Vol. Calculado Vazão (m³)",
                        ]
                    )
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
                            "Vazão Média (m³/h)": "-",
                            "Horas Ativas Reais": round(total_horas_ativas, 1),
                            "Tempo Fora do Ar (h)": round(total_horas_fora, 1),
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
                    f"Relatório Consolidado do Período: {sistema_filtro}"
                )

                card1, card2 = st.columns(2)
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

                card1.metric(
                    label="SOMA Totalizador do Período Selecionado",
                    value=f"{v_phy_str} m³",
                )
                card2.metric(
                    label="SOMA Calculada por Vazão no Período",
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
                    st.plotly_chart(fig_vazao, use_container_width=True)

                if not df_resumo.empty:
                    fig_volume = px.bar(
                        df_resumo,
                        x="Data",
                        y="Vol. Diário Totalizador (m³)",
                        title="Volume Líquido Diário Produzido (m³)",
                        text_auto=".2f",
                    )
                    st.plotly_chart(fig_volume, use_container_width=True)
            else:
                st.warning(
                    "Nenhum dado encontrado para os filtros selecionados."
                )
        else:
            st.warning("Não há canais de macromedição registrados.")

    # SUB-TELA: NÍVEIS DE RESERVATÓRIOS
    elif tipo_analise == "Níveis de Reservatórios":
        query_locais = f"SELECT DISTINCT local_reservatorio FROM `{DATASET_ID}.tb_niveis` ORDER BY local_reservatorio"
        locais_disponiveis = [
            r["local_reservatorio"]
            for r in client.query(query_locais).result()
        ]

        query_vazao_canais = f"SELECT DISTINCT sistema_canal FROM `{DATASET_ID}.tb_vazao` WHERE sistema_canal IS NOT NULL ORDER BY sistema_canal"
        canais_vazao_disponiveis = [
            r["sistema_canal"] for r in client.query(query_vazao_canais).result()
        ]

        locais_limpos = sorted(
            list(
                set(
                    [
                        s.replace("(m)", "")
                        .replace("(%)", "")
                        .replace("Nivel", "")
                        .replace("Nível", "")
                        .strip()
                        for s in locais_disponiveis
                    ]
                )
            )
        )

        if locais_limpos:
            locais_selecionados = st.multiselect(
                "Selecione qual(is) Local(is)/Reservatório(s) deseja analisar e comparar:",
                options=locais_limpos,
                default=[locais_limpos[0]] if locais_limpos else [],
            )

            vazao_selecionada = st.selectbox(
                "Deseja incluir a Vazão de algum sistema neste mesmo gráfico? (Opcional)",
                options=["[Não incluir vazão]"] + canais_vazao_disponiveis,
            )

            cn1, cn2 = st.columns(2)
            d_n_ini = cn1.date_input(
                "Data Inicial do Nível:",
                value=datetime.date.today() - datetime.timedelta(days=3),
                format="DD/MM/YYYY",
                key="nivel_dt_ini",
            )
            d_n_fim = cn2.date_input(
                "Data Final do Nível:",
                value=datetime.date.today(),
                format="DD/MM/YYYY",
                key="nivel_dt_fim",
            )

            if locais_selecionados:
                query_niveis = f"""
                SELECT data_hora, local_reservatorio, nivel_m
                FROM `{DATASET_ID}.tb_niveis`
                WHERE DATE(data_hora) BETWEEN @data_ini AND @data_fim
                ORDER BY data_hora ASC
                """
                job_config_niv = bigquery.QueryJobConfig(
                    query_parameters=[
                        bigquery.ScalarQueryParameter(
                            "data_ini", "DATE", d_n_ini
                        ),
                        bigquery.ScalarQueryParameter(
                            "data_fim", "DATE", d_n_fim
                        ),
                    ]
                )
                df_n_filtrado = client.query(
                    query_niveis, job_config_niv
                ).to_dataframe()

                if not df_n_filtrado.empty:
                    df_n_filtrado["nivel_m"] = pd.to_numeric(
                        df_n_filtrado["nivel_m"], errors="coerce"
                    )
                    df_n_filtrado = df_n_filtrado[
                        (df_n_filtrado["nivel_m"] >= -0.1)
                        & (df_n_filtrado["nivel_m"] <= 10.0)
                    ]

                    if not df_n_filtrado.empty:
                        df_n_filtrado["Data e Hora"] = pd.to_datetime(
                            df_n_filtrado["data_hora"]
                        )

                        st.subheader(
                            "Monitoramento Integrado e Comparativo de Níveis"
                        )
                        fig_m = make_subplots(
                            specs=[[{"secondary_y": True}]]
                        )
                        dados_m_plotados = False
                        max_nivel_encontrado = 0.0

                        for local in locais_selecionados:
                            df_loc = df_n_filtrado[
                                df_n_filtrado[
                                    "local_reservatorio"
                                ].str.contains(local, case=False, na=False)
                            ].copy()

                            if not df_loc.empty:
                                df_loc["val_valido"] = df_loc["nivel_m"].apply(
                                    lambda x: x if x >= 0 else np.nan
                                )
                                max_val = df_loc["val_valido"].max()

                                if (
                                    pd.notna(max_val)
                                    and max_val > max_nivel_encontrado
                                ):
                                    max_nivel_encontrado = max_val

                                # 1. Linha contínua cinza bem clarinha conectando o trecho fora do ar
                                df_loc_interp = df_loc.dropna(
                                    subset=["val_valido"]
                                )
                                fig_m.add_trace(
                                    go.Scatter(
                                        x=df_loc_interp["Data e Hora"],
                                        y=df_loc_interp["val_valido"],
                                        name=f"Fora do Ar (Nível {local})",
                                        mode="lines",
                                        line=dict(
                                            color="rgba(210, 210, 210, 0.6)",
                                            width=1.5,
                                        ),
                                        hoverinfo="skip",
                                        showlegend=True,
                                    ),
                                    secondary_y=False,
                                )

                                # 2. Linha azul escuro (blue) sólida para dados válidos de nível
                                fig_m.add_trace(
                                    go.Scatter(
                                        x=df_loc["Data e Hora"],
                                        y=df_loc["val_valido"],
                                        name=f"Nível {local} (m)",
                                        mode="lines",
                                        line=dict(
                                            color="#0000FF",
                                            width=2.5,
                                        ),
                                        connectgaps=False,
                                        hovertemplate="<b>Nível:</b> %{y:.2f} m<br>%{x}<extra></extra>",
                                    ),
                                    secondary_y=False,
                                )
                                dados_m_plotados = True

                        df_v_plot = pd.DataFrame()
                        if vazao_selecionada != "[Não incluir vazão]":
                            query_vazao_plot = f"""
                            SELECT data_hora, vazao_m3h
                            FROM `{DATASET_ID}.tb_vazao`
                            WHERE sistema_canal = @sistema
                            AND DATE(data_hora) BETWEEN @data_ini AND @data_fim
                            ORDER BY data_hora ASC
                            """
                            job_config_vaz = bigquery.QueryJobConfig(
                                query_parameters=[
                                    bigquery.ScalarQueryParameter(
                                        "sistema", "STRING", vazao_selecionada
                                    ),
                                    bigquery.ScalarQueryParameter(
                                        "data_ini", "DATE", d_n_ini
                                    ),
                                    bigquery.ScalarQueryParameter(
                                        "data_fim", "DATE", d_n_fim
                                    ),
                                ]
                            )
                            df_v_plot = client.query(
                                query_vazao_plot, job_config=job_config_vaz
                            ).to_dataframe()

                            if not df_v_plot.empty:
                                df_v_plot["Data e Hora"] = pd.to_datetime(
                                    df_v_plot["data_hora"]
                                )
                                df_v_plot["Vazão (m³/h)"] = pd.to_numeric(
                                    df_v_plot["vazao_m3h"], errors="coerce"
                                )
                                df_v_plot = df_v_plot.sort_values("Data e Hora")
                                df_v_plot["val_valido"] = df_v_plot[
                                    "Vazão (m³/h)"
                                ].apply(lambda x: x if x >= 0 else np.nan)

                                # 1. Linha contínua cinza bem clarinha conectando falhas da vazão
                                df_v_interp = df_v_plot.dropna(
                                    subset=["val_valido"]
                                )
                                fig_m.add_trace(
                                    go.Scatter(
                                        x=df_v_interp["Data e Hora"],
                                        y=df_v_interp["val_valido"],
                                        name="Fora do Ar (Vazão)",
                                        mode="lines",
                                        line=dict(
                                            color="rgba(210, 210, 210, 0.6)",
                                            width=1.5,
                                        ),
                                        hoverinfo="skip",
                                        showlegend=True,
                                    ),
                                    secondary_y=True,
                                )

                                # 2. Linha vermelha sólida para dados válidos de vazão
                                fig_m.add_trace(
                                    go.Scatter(
                                        x=df_v_plot["Data e Hora"],
                                        y=df_v_plot["val_valido"],
                                        name=f"Vazão: {vazao_selecionada}",
                                        mode="lines",
                                        line=dict(
                                            color="#FF6666",
                                            width=2.5,
                                        ),
                                        connectgaps=False,
                                        hovertemplate="<b>Vazão:</b> %{y:.2f} m³/h<br>%{x}<extra></extra>",
                                    ),
                                    secondary_y=True,
                                )

                        # Ajuste de teto para posicionar o Nível um pouco abaixo da Vazão
                        teto_y1 = (
                            max(max_nivel_encontrado * 1.7, 5.0)
                            if max_nivel_encontrado > 0
                            else 10.0
                        )

                        fig_m.update_layout(
                            title_text="Nível Contínuo em Metros (m) vs Comportamento de Vazão",
                            hovermode="x unified",
                            legend=dict(
                                orientation="h",
                                yanchor="bottom",
                                y=-0.25,
                                xanchor="right",
                                x=1,
                            ),
                        )
                        fig_m.update_xaxes(title_text="Data e Hora")
                        fig_m.update_yaxes(
                            title_text="<b>Nível (m)</b>",
                            range=[0, teto_y1],
                            exponentformat="none",
                            secondary_y=False,
                        )
                        fig_m.update_yaxes(
                            title_text="<b>Vazão (m³/h)</b>",
                            exponentformat="none",
                            showgrid=False,
                            secondary_y=True,
                        )

                        if dados_m_plotados:
                            st.plotly_chart(fig_m, use_container_width=True)

                        # ------------------------------------------
                        # DETECÇÃO DE LAVAGENS (REGRAS DE COLÔNIA)
                        # ------------------------------------------

                        # 1. CAPTURA E NORMALIZAÇÃO DA SELEÇÃO DA TELA
                        selecao_usuario = ""
                        for var_nome in [
                            "sel_res",
                            "locais_selecionados",
                            "reservatorios_selecionados",
                            "vazao_selecionada",
                        ]:
                            if var_nome in globals():
                                selecao_usuario += " " + str(
                                    globals()[var_nome]
                                )

                        selecao_usuario_norm = (
                            unicodedata.normalize("NFKD", selecao_usuario)
                            .encode("ASCII", "ignore")
                            .decode("utf-8")
                            .lower()
                        )

                        e_colonia = "colonia" in selecao_usuario_norm

                        # ==========================================
                        # 3. TABELA DE DETECÇÃO DAS LAVAGENS DE FILTRO
                        # ==========================================
                        if (
                            e_colonia
                            and "vazao_selecionada" in globals()
                            and vazao_selecionada != "[Não incluir vazão]"
                            and not df_v_plot.empty
                        ):
                            st.markdown("---")
                            st.subheader(
                                "🧹 Tabela de Lavagens de Filtro Detectadas (Colônia Leopoldina)"
                            )

                            df_lavagem = df_v_plot.sort_values(
                                "Data e Hora"
                            ).copy()

                            # REGRA COLÔNIA: Faixa de queda/lavagem (0 a 5 m³/h) ou fita Fora do Ar
                            df_lavagem["em_baixa_ou_fora"] = (
                                df_lavagem["Vazão (m³/h)"].isna()
                            ) | (df_lavagem["Vazão (m³/h)"] <= 5.0)

                            df_lavagem["grupo"] = (
                                df_lavagem["em_baixa_ou_fora"]
                                != df_lavagem["em_baixa_ou_fora"].shift()
                            ).cumsum()

                            eventos_lavagem = []
                            grupos_lavagem = df_lavagem[
                                df_lavagem["em_baixa_ou_fora"]
                            ].groupby("grupo")

                            # Teto de operação normal considerado: >= 80 m³/h (Ref: 120 m³/h)
                            LIMITE_OPERACAO_NORMAL = 80.0

                            for id_grupo, grupo in grupos_lavagem:
                                dt_inicio = grupo["Data e Hora"].min()
                                dt_fim = grupo["Data e Hora"].max()
                                duracao_seg = (
                                    dt_fim - dt_inicio
                                ).total_seconds()
                                duracao_horas = duracao_seg / 3600.0

                                # Duração entre 40min (2400s) e 3h (10800s)
                                if 2400 <= duracao_seg <= 10800:
                                    idx_inicio = grupo.index[0]
                                    idx_fim = grupo.index[-1]

                                    vazao_antes = (
                                        df_lavagem.loc[
                                            idx_inicio - 1, "Vazão (m³/h)"
                                        ]
                                        if idx_inicio > 0
                                        else np.nan
                                    )
                                    vazao_depois = (
                                        df_lavagem.loc[
                                            idx_fim + 1, "Vazão (m³/h)"
                                        ]
                                        if idx_fim + 1 < len(df_lavagem)
                                        else np.nan
                                    )

                                    # Checa transição abrupta comparada ao regime em ~120 m³/h (>= 80 m³/h)
                                    veio_de_vazao_normal = (
                                        pd.notna(vazao_antes)
                                        and vazao_antes >= LIMITE_OPERACAO_NORMAL
                                    )
                                    voltou_para_vazao_normal = (
                                        pd.notna(vazao_depois)
                                        and vazao_depois >= LIMITE_OPERACAO_NORMAL
                                    )

                                    if (
                                        veio_de_vazao_normal
                                        or voltou_para_vazao_normal
                                    ):
                                        dia_evento = dt_inicio.date()
                                        vazoes_do_dia = df_v_plot[
                                            (
                                                df_v_plot[
                                                    "Data e Hora"
                                                ].dt.date
                                                == dia_evento
                                            )
                                            & (
                                                df_v_plot["Vazão (m³/h)"]
                                                >= LIMITE_OPERACAO_NORMAL
                                            )
                                        ]["Vazão (m³/h)"]

                                        vazao_media_dia = (
                                            vazoes_do_dia.mean()
                                            if not vazoes_do_dia.empty
                                            else 120.0
                                        )
                                        vol_gasto = (
                                            vazao_media_dia * duracao_horas
                                        )

                                        eventos_lavagem.append(
                                            {
                                                "Início da Lavagem": dt_inicio.strftime(
                                                    "%d/%m/%Y %H:%M:%S"
                                                ),
                                                "Fim da Lavagem": dt_fim.strftime(
                                                    "%d/%m/%Y %H:%M:%S"
                                                ),
                                                "Duração": f"{int(duracao_seg // 60)} min",
                                                "Vazão Média do Dia (m³/h)": round(
                                                    vazao_media_dia, 2
                                                ),
                                                "Vol. Gasto Estimado (m³)": round(
                                                    vol_gasto, 2
                                                ),
                                            }
                                        )

                            if eventos_lavagem:
                                df_tb_lavagens = pd.DataFrame(eventos_lavagem)
                                total_vol_lavagens = df_tb_lavagens[
                                    "Vol. Gasto Estimado (m³)"
                                ].sum()
                                total_eventos_lav = len(df_tb_lavagens)

                                m_col1, m_col2 = st.columns(2)
                                m_col1.metric(
                                    "Total de Lavagens no Período",
                                    f"{total_eventos_lav} eventos",
                                )
                                m_col2.metric(
                                    "Volume Total Estimado Gasto",
                                    f"{total_vol_lavagens:,.2f}".replace(
                                        ",", "X"
                                    )
                                    .replace(".", ",")
                                    .replace("X", ".")
                                    + " m³",
                                )

                                linha_total_lav = pd.DataFrame(
                                    [
                                        {
                                            "Início da Lavagem": "TOTAL DO PERÍODO",
                                            "Fim da Lavagem": "-",
                                            "Duração": "-",
                                            "Vazão Média do Dia (m³/h)": "",
                                            "Vol. Gasto Estimado (m³)": round(
                                                total_vol_lavagens, 2
                                            ),
                                        }
                                    ]
                                )

                                df_exibir_lav = pd.concat(
                                    [df_tb_lavagens, linha_total_lav],
                                    ignore_index=True,
                                )
                                st.dataframe(
                                    df_exibir_lav,
                                    use_container_width=True,
                                    hide_index=True,
                                )
                            else:
                                st.info(
                                    "Nenhum evento característico de lavagem de filtro foi identificado no período."
                                )
