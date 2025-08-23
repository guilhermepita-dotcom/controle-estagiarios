import os

from datetime import date

from contextlib import contextmanager

from typing import Optional, Dict, Any



import pandas as pd

import sqlite3

import streamlit as st

from dateutil.relativedelta import relativedelta

from PIL import Image

from streamlit_option_menu import option_menu



# ==========================

# Configurações e Constantes

# ==========================

DB_FILE = "estagiarios.db"

LOGO_FILE = "logo.png"

DEFAULT_PROXIMOS_DIAS = 30

DEFAULT_DURATION_OTHERS = 6

DEFAULT_REGRAS = [("UERJ", 24), ("UNIRIO", 24), ("MACKENZIE", 24)]



universidades_padrao = [

    "Anhanguera - Instituição de Ensino Anhanguera",

    "CBPF – Centro Brasileiro de Pesquisas Físicas",

    "CEFET/RJ – Centro Federal de Educação Tecnológica Celso Suckow da Fonseca",

    "Celso Lisboa – Centro Universitário Celso Lisboa",

    "ENCE – Escola Nacional de Ciências Estatísticas",

    "Estácio - Universidade Estácio de Sá",

    "FACHA – Faculdades Integradas Hélio Alonso",

    "FAETERJ – Faculdade de Educação Tecnológica do Estado do RJ",

    "FGV-RJ – Fundação Getulio Vargas",

    "IBMEC-RJ – Instituto Brasileiro de Mercado de Capitais",

    "IBMR – Instituto Brasileiro de Medicina de Reabilitação",

    "IFRJ – Instituto Federal do Rio de Janeiro",

    "IME – Instituto Militar de Engenharia",

    "IMPA – Instituto de Matemática Pura e Aplicada",

    "ISERJ – Instituto Superior de Educação do Rio de Janeiro",

    "Mackenzie Rio – Universidade Presbiteriana Mackenzie",

    "PUC-Rio – Pontifícia Universidade Católica do Rio de Janeiro",

    "Santa Úrsula – Associação Universitária Santa Úrsula",

    "UCAM – Universidade Cândido Mendes",

    "UCB – Universidade Castelo Branco",

    "UERJ – Universidade do Estado do Rio de Janeiro",

    "UFF – Universidade Federal Fluminense",

    "UFRJ – Universidade Federal do Rio de Janeiro",

    "UFRRJ – Universidade Federal Rural do Rio de Janeiro",

    "UNESA – Universidade Estácio de Sá",

    "UNIABEU – Centro Universitário ABEU",

    "UNICARIOCA – Centro Universitário Carioca",

    "UNIFESO – Centro Universitário Serra dos Órgãos",

    "UNIG – Universidade Iguaçu",

    "UNIGRANRIO – Universidade do Grande Rio",

    "UNILASALLE-RJ – Centro Universitário La Salle do Rio de Janeiro",

    "UNIRIO – Universidade Federal do Estado do Rio de Janeiro",

    "UNISÃOJOSÉ – Centro Universitário São José",

    "UNISIGNORELLI - Centro Universitário Internacional Signorelli",

    "UNISUAM – Centro Universitário Augusto Motta",

    "UNIVERSO – Universidade Salgado de Oliveira",

    "USS – Universidade de Vassouras (antiga Severino Sombra)",

    "UVA – Universidade Veiga de Almeida",

    "Outra (cadastrar manualmente)"

]



# ==========================

# Inicialização Streamlit

# ==========================

st.set_page_config(page_title="Controle de Estagiários", layout="wide", page_icon="📋")



# ==========================

# Estilo (CSS) Profissional

# ==========================

def load_custom_css():

    st.markdown("""

        <style>

            @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;600;700&display=swap');

            

            :root {

                --primary-color: #E2A144;

                --background-color: #0F0F0F;

                --secondary-background-color: #212121;

                --text-color: #EAEAEA;

                --text-color-muted: #888;

                --font-family: 'Poppins', sans-serif;

            }



            html, body, [class*="st-"], .st-emotion-cache-10trblm {

                font-family: var(--font-family);

                color: var(--text-color);

            }

            

            .main > div { background-color: var(--background-color); }

            

            h1, h2, h3 { color: var(--text-color) !important; font-weight: 600 !important;}

            h1 { color: var(--primary-color) !important; }



            .stButton > button {

                background-color: transparent;

                color: var(--primary-color);

                border-radius: 8px;

                border: 2px solid var(--primary-color);

                font-weight: 600;

                transition: all 0.2s ease-in-out;

                padding: 8px 16px;

            }

            .stButton > button:hover {

                background-color: var(--primary-color);

                color: #FFFFFF;

            }

            .stButton > button:focus {

                box-shadow: 0 0 0 2px var(--secondary-background-color), 0 0 0 4px var(--primary-color) !important;

            }

            /* Botão de confirmação agora usa a cor primária */

            .stButton > button[kind="primary"] {

                background-color: var(--primary-color);

                border-color: var(--primary-color);

                color: #FFFFFF;

            }

            .stButton > button[kind="primary"]:hover {

                background-color: transparent;

                color: var(--primary-color);

            }



            [data-testid="stMetric"] {

                background-color: var(--secondary-background-color);

                border-radius: 10px;

                padding: 20px;

                border-left: 5px solid var(--primary-color);

                box-shadow: 0 4px 8px 0 rgba(0,0,0,0.2);

            }



            form {

                background-color: var(--secondary-background-color);

                border-radius: 10px;

                padding: 25px;

                border: 1px solid #333;

            }

            [data-testid="stExpander"] {

                background-color: var(--secondary-background-color);

                border-radius: 8px;

                border: 1px solid #333;

            }

            

            li[data-testid="stMenuIIsHorizontal"] > a:hover {

                color: var(--primary-color) !important;

            }



            div[data-testid="stDataFrame"] table td:nth-child(1), /* ID */

            div[data-testid="stDataFrame"] table td:nth-child(4), /* Data Admissão */

            div[data-testid="stDataFrame"] table td:nth-child(5), /* Renovado em */

            div[data-testid="stDataFrame"] table td:nth-child(8), /* Próxima Renovação */

            div[data-testid="stDataFrame"] table td:nth-child(9) { /* Termino de Contrato */

                text-align: center;

            }

        </style>

    """, unsafe_allow_html=True)



# ==========================

# Banco de Dados

# ==========================

@st.cache_resource

def get_db_connection():

    conn = sqlite3.connect(DB_FILE, check_same_thread=False)

    conn.row_factory = sqlite3.Row

    return conn



def init_db():

    conn = get_db_connection()

    c = conn.cursor()

    c.execute("""

        CREATE TABLE IF NOT EXISTS estagiarios (

            id INTEGER PRIMARY KEY, nome TEXT NOT NULL, universidade TEXT NOT NULL,

            data_admissao TEXT NOT NULL, data_ult_renovacao TEXT,

            obs TEXT, data_vencimento TEXT

        )

    """)

    c.execute("CREATE TABLE IF NOT EXISTS regras (id INTEGER PRIMARY KEY, keyword TEXT UNIQUE NOT NULL, meses INTEGER NOT NULL)")

    c.execute("CREATE TABLE IF NOT EXISTS config (key TEXT PRIMARY KEY, value TEXT)")

    

    c.execute("SELECT value FROM config WHERE key='regras_iniciadas'")

    regras_iniciadas = c.fetchone()

    if not regras_iniciadas:

        for kw, meses in DEFAULT_REGRAS:

            c.execute("INSERT OR IGNORE INTO regras(keyword, meses) VALUES (?, ?)", (kw.upper(), meses))

        c.execute("INSERT OR REPLACE INTO config(key, value) VALUES(?, ?)", ('regras_iniciadas', 'true'))



    c.execute("INSERT OR IGNORE INTO config(key, value) VALUES(?, ?)", ('proximos_dias', str(DEFAULT_PROXIMOS_DIAS)))

    c.execute("INSERT OR IGNORE INTO config(key, value) VALUES(?, ?)", ('admin_password', '123456'))

    conn.commit()



def get_config(key: str, default: Optional[str] = None) -> str:

    conn = get_db_connection()

    c = conn.cursor()

    row = c.execute("SELECT value FROM config WHERE key=?", (key,)).fetchone()

    return row['value'] if row else (default if default is not None else "")



def set_config(key: str, value: str):

    conn = get_db_connection()

    c = conn.cursor()

    c.execute("INSERT INTO config(key, value) VALUES(?, ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key, value))

    conn.commit()



# ==========================

# Funções de Lógica e CRUD

# ==========================

def list_regras() -> pd.DataFrame:

    df = pd.read_sql_query("SELECT id, keyword, meses FROM regras ORDER BY keyword", get_db_connection())

    return df



def meses_por_universidade(universidade: str) -> int:

    if not universidade: return DEFAULT_DURATION_OTHERS

    uni_up = universidade.upper()

    df_regras = list_regras()

    for _, row in df_regras.iterrows():

        if row["keyword"] == uni_up:

            return int(row["meses"])

    return DEFAULT_DURATION_OTHERS



def list_estagiarios_df() -> pd.DataFrame:

    try:

        df = pd.read_sql_query("SELECT * FROM estagiarios", get_db_connection(), index_col="id")

    except (pd.io.sql.DatabaseError, ValueError):

        return pd.DataFrame()

    if df.empty:

        return pd.DataFrame(columns=['id', 'nome', 'universidade', 'data_admissao', 'data_ult_renovacao', 'obs', 'data_vencimento'])

    df.reset_index(inplace=True)

    df['data_vencimento_obj'] = pd.to_datetime(df['data_vencimento'], errors='coerce')

    df = df.sort_values(by='data_vencimento_obj', ascending=True).drop(columns=['data_vencimento_obj'])

    df["ultimo_ano"] = pd.to_datetime(df["data_vencimento"], errors='coerce').dt.year.apply(lambda y: "SIM" if pd.notna(y) and y == date.today().year else "NÃO")

    regras_df = list_regras()

    regras_24m_keywords = [row['keyword'] for index, row in regras_df.iterrows() if row['meses'] >= 24]

    if regras_24m_keywords:

        mask = (df['universidade'].str.upper().isin(regras_24m_keywords)) & (df['data_ult_renovacao'].isnull() | df['data_ult_renovacao'].eq(''))

        df.loc[mask, 'data_ult_renovacao'] = "Contrato Único"

    return df



def insert_estagiario(nome: str, universidade: str, data_adm: date, data_renov: Optional[date], obs: str, data_venc: Optional[date]):

    conn = get_db_connection()

    conn.execute("INSERT INTO estagiarios(nome, universidade, data_admissao, data_ult_renovacao, obs, data_vencimento) VALUES (?, ?, ?, ?, ?, ?)", (nome, universidade, str(data_adm), str(data_renov) if data_renov else None, obs, str(data_venc) if data_venc else None))

    conn.commit()



def update_estagiario(est_id: int, nome: str, universidade: str, data_adm: date, data_renov: Optional[date], obs: str, data_venc: Optional[date]):

    conn = get_db_connection()

    conn.execute("UPDATE estagiarios SET nome=?, universidade=?, data_admissao=?, data_ult_renovacao=?, obs=?, data_vencimento=? WHERE id=?", (nome, universidade, str(data_adm), str(data_renov) if data_renov else None, obs, str(data_venc) if data_venc else None, est_id))

    conn.commit()



def delete_estagiario(est_id: int):

    conn = get_db_connection()

    conn.execute("DELETE FROM estagiarios WHERE id=?", (int(est_id),))

    conn.commit()



def add_regra(keyword: str, meses: int):

    conn = get_db_connection()

    conn.execute("INSERT OR REPLACE INTO regras(keyword, meses) VALUES (?, ?)", (keyword.upper().strip(), meses))

    conn.commit()



def update_regra(regra_id: int, keyword: str, meses: int):

    conn = get_db_connection()

    conn.execute("UPDATE regras SET keyword=?, meses=? WHERE id=?", (keyword.upper().strip(), meses, int(regra_id)))

    conn.commit()



def delete_regra(regra_id: int):

    conn = get_db_connection()

    conn.execute("DELETE FROM regras WHERE id=?", (int(regra_id),))

    conn.commit()



def calcular_vencimento_final(data_adm: Optional[date]) -> Optional[date]:

    if not data_adm: return None

    return data_adm + relativedelta(months=24)



def classificar_status(data_venc: Optional[str], proximos_dias: int) -> str:

    if not data_venc or pd.isna(data_venc) or data_venc == '': return "SEM DATA"

    try:

        data_venc_obj = pd.to_datetime(data_venc).date()

    except:

        return "DATA INVÁLIDA"

    delta = (data_venc_obj - date.today()).days

    if delta < 0: return "Vencido"

    if delta <= proximos_dias: return "Venc.Proximo"

    return "OK"



def calcular_proxima_renovacao(row: pd.Series) -> str:

    hoje = date.today()

    data_adm = pd.to_datetime(row['data_admissao'], dayfirst=False, errors='coerce').date()

    data_ult_renov_str = row.get('data_ult_renovacao', '')

    data_ult_renov = None

    if isinstance(data_ult_renov_str, str) and "Contrato" not in data_ult_renov_str and data_ult_renov_str != '':

        data_ult_renov = pd.to_datetime(data_ult_renov_str, dayfirst=False, errors='coerce').date()

    if pd.isna(data_adm): return ""

    termo_meses = meses_por_universidade(row['universidade'])

    if termo_meses >= 24: return ""

    limite_2_anos = data_adm + relativedelta(months=24)

    if limite_2_anos < hoje: return "Contrato Encerrado"

    base_date = data_ult_renov if pd.notna(data_ult_renov) else data_adm

    if pd.isna(base_date): return ""

    ciclo_renovacao = 6

    proxima_data_renovacao = base_date + relativedelta(months=ciclo_renovacao)

    if proxima_data_renovacao > limite_2_anos: return "Término do Contrato"

    if proxima_data_renovacao < hoje: return "Renovação Pendente"

    return proxima_data_renovacao.strftime("%d.%m.%Y")



def exportar_para_excel_bytes(df: pd.DataFrame) -> bytes:

    df_export = df.copy()

    path_temp = "temp.xlsx"

    with pd.ExcelWriter(path_temp, engine="openpyxl") as writer:

        df_export.to_excel(writer, index=False, sheet_name="Estagiarios")

    with open(path_temp, "rb") as f: data_bytes = f.read()

    os.remove(path_temp)

    return data_bytes



def show_message(message: Dict[str, Any]):

    msg_type = message.get('type', 'info')

    text = message.get('text', 'Ação concluída.')

    icon_map = {'success': '✅', 'warning': '⚠️', 'error': '❌', 'info': 'ℹ️'}

    st.toast(text, icon=icon_map[msg_type])



# ==========================

# Main App

# ==========================

def main():

    load_custom_css()

    init_db()



    # --- CABEÇALHO COM LOGO E MENU LADO A LADO ---

    c1, c2 = st.columns([1, 4], vertical_alignment="center")

    with c1:

        if os.path.exists(LOGO_FILE):

            st.image(LOGO_FILE, width=150)

    with c2:

        selected = option_menu(

            menu_title=None,

            options=["Dashboard", "Cadastro", "Regras", "Import/Export", "Área Administrativa"],

            icons=['bar-chart-line-fill', 'pencil-square', 'gear-fill', 'cloud-upload-fill', 'key-fill'],

            menu_icon="cast", 

            default_index=0,

            orientation="horizontal",

            styles={

                "container": {"padding": "0!important", "background-color": "transparent"},

                "icon": {"color": "var(--text-color-muted)", "font-size": "20px"},

                "nav-link": {

                    "font-size": "16px", "text-align": "center", "margin": "0px 10px",

                    "padding-bottom": "10px", "color": "var(--text-color-muted)",

                    "border-bottom": "3px solid transparent", "transition": "color 0.3s, border-bottom 0.3s",

                },

                "nav-link-selected": {

                    "background-color": "transparent",

                    "color": "var(--primary-color)",

                    "border-bottom": "3px solid var(--primary-color)",

                    "font-weight": "600",

                },

            }

        )

    st.divider()

    

    # Lógica de Reset de Página

    if 'main_selection' not in st.session_state: st.session_state.main_selection = "Dashboard"

    if selected != st.session_state.main_selection:

        st.session_state.main_selection = selected

        for key in ['sub_menu_cad', 'cadastro_universidade', 'est_selecionado_id', 'confirm_delete', 'confirm_delete_rule']:

            if key in st.session_state:

                st.session_state[key] = None

        st.rerun()

    

    if selected == "Dashboard":

        c_dash1, c_dash2 = st.columns([3, 1])

        with c_dash1:

            st.subheader("Visão Geral")

        with c_dash2:

            proximos_dias_input = st.number_input("'Venc. Próximo' (dias)", min_value=1, max_value=120, value=int(get_config("proximos_dias", DEFAULT_PROXIMOS_DIAS)), step=1)

            set_config("proximos_dias", str(proximos_dias_input))

        

        df = list_estagiarios_df()

        if df.empty:

            st.info("Nenhum estagiário cadastrado para exibir métricas.")

        else:

            df["status"] = df["data_vencimento"].apply(lambda d: classificar_status(d, proximos_dias_input))

            total, ok, prox, venc = len(df), (df["status"] == "OK").sum(), (df["status"] == "Venc.Proximo").sum(), (df["status"] == "Vencido").sum()

            c1, c2, c3, c4 = st.columns(4)

            c1.metric("👥 Total de Estagiários", total)

            c2.metric("✅ Contratos OK", ok)

            c3.metric("⚠️ Vencimentos Próximos", prox)

            c4.metric("⛔ Contratos Vencidos", venc)

        

        st.subheader("Consulta de Estagiários")

        if df.empty:

            st.info("Nenhum estagiário cadastrado ainda.")

        else:

            filtros_c1, filtros_c2 = st.columns(2)

            with filtros_c1:

                filtro_status = st.multiselect("Filtrar por status", options=["OK", "Venc.Proximo", "Vencido"], default=[])

            with filtros_c2:

                filtro_nome = st.text_input("🔎 Buscar por Nome do Estagiário")



            df_view = df.copy()

            if filtro_status: df_view = df_view[df_view["status"].isin(filtro_status)]

            if filtro_nome.strip(): df_view = df_view[df_view["nome"].str.contains(filtro_nome.strip(), case=False, na=False)]

            if df_view.empty:

                st.warning("Nenhum registro encontrado para os filtros selecionados.")

            else:

                df_view["proxima_renovacao"] = df_view.apply(calcular_proxima_renovacao, axis=1)

                

                df_display = df_view.rename(columns={

                    'id': 'ID', 'nome': 'Nome', 'universidade': 'Universidade',

                    'data_admissao': 'Data Admissão', 'data_ult_renovacao': 'Renovado em:',

                    'status': 'Status', 'ultimo_ano': 'Ultimo Ano?',

                    'proxima_renovacao': 'Proxima Renovação', 'data_vencimento': 'Termino de Contrato',

                    'obs': 'Observação'

                })

                

                colunas_ordenadas = ['ID', 'Nome', 'Universidade', 'Data Admissão', 'Renovado em:', 'Status', 'Ultimo Ano?', 'Proxima Renovação', 'Termino de Contrato', 'Observação']

                df_display = df_display.reindex(columns=colunas_ordenadas)

                st.dataframe(df_display, use_container_width=True, hide_index=True)

                st.download_button("📥 Exportar Resultado", exportar_para_excel_bytes(df_view), "estagiarios_filtrados.xlsx", key="download_dashboard")



    if selected == "Cadastro":

        st.subheader("Gerenciar Cadastro de Estagiário")

        

        if 'sub_menu_cad' not in st.session_state: st.session_state.sub_menu_cad = None

        if 'message' not in st.session_state: st.session_state.message = None

        

        if st.session_state.message:

            show_message(st.session_state.message)

            st.session_state.message = None



        cols = st.columns(2)

        if cols[0].button("➕ Novo Estagiário"):

            if st.session_state.sub_menu_cad != "Novo":

                st.session_state.sub_menu_cad = "Novo"

                st.rerun()

        if cols[1].button("🔎 Consultar / Editar"):

            if st.session_state.sub_menu_cad != "Editar":

                st.session_state.sub_menu_cad = "Editar"

                st.rerun()

        st.divider()



        if st.session_state.sub_menu_cad == "Novo":

            if 'cadastro_universidade' not in st.session_state: st.session_state.cadastro_universidade = None



            if not st.session_state.cadastro_universidade:

                st.subheader("Passo 1: Selecione a Universidade")

                uni_selecionada = st.selectbox("Universidade*", options=universidades_padrao, index=None, placeholder="Selecione uma universidade...")

                

                col1_passo1, _ = st.columns([1, 5])

                with col1_passo1:

                    if st.button("Cancelar"):

                        st.session_state.sub_menu_cad = None

                        st.session_state.cadastro_universidade = None

                        st.rerun()



                if uni_selecionada == "Outra (cadastrar manualmente)":

                    uni_outra = st.text_input("Digite o nome da Universidade*")

                    if st.button("Continuar"):

                        if uni_outra.strip():

                            st.session_state.cadastro_universidade = uni_outra.strip().upper()

                            st.rerun()

                        else:

                            st.warning("Por favor, digite o nome da universidade.")

                elif uni_selecionada:

                    st.session_state.cadastro_universidade = uni_selecionada

                    st.rerun()

            else:

                with st.form("form_new_cadastro"):

                    st.subheader(f"Passo 2: Detalhes do Estagiário ({st.session_state.cadastro_universidade})")

                    nome = st.text_input("Nome*")

                    termo_meses = meses_por_universidade(st.session_state.cadastro_universidade)

                    c1, c2 = st.columns(2)

                    data_adm = c1.date_input("Data de Admissão*")

                    data_renov = c2.date_input("Data da Última Renovação", disabled=(termo_meses >= 24))

                    if termo_meses >= 24:

                        c2.info("Contrato único. Não requer renovação.")

                    obs = st.text_area("Observações", height=100)

                    st.markdown("---")

                    c_submit, c_cancel = st.columns(2)

                    if c_submit.form_submit_button("💾 Salvar Novo Estagiário"):

                        if not nome.strip() or not data_adm:

                            st.session_state.message = {'text': "Preencha todos os campos obrigatórios (*).", 'type': 'warning'}

                        else:

                            nome_upper, uni_upper, obs_upper = nome.strip().upper(), st.session_state.cadastro_universidade, obs.strip().upper()

                            data_venc = calcular_vencimento_final(data_adm)

                            insert_estagiario(nome_upper, uni_upper, data_adm, data_renov, obs_upper, data_venc)

                            st.session_state.message = {'text': f"Estagiário {nome_upper} cadastrado!", 'type': 'success'}

                            st.session_state.cadastro_universidade = None

                            st.session_state.sub_menu_cad = None

                        st.rerun()

                    if c_cancel.form_submit_button("🧹 Cancelar"):

                        st.session_state.cadastro_universidade = None

                        st.session_state.sub_menu_cad = None

                        st.rerun()



        if st.session_state.sub_menu_cad == "Editar":

            if 'est_selecionado_id' not in st.session_state: st.session_state.est_selecionado_id = None

            if 'confirm_delete' not in st.session_state: st.session_state.confirm_delete = None



            if st.session_state.confirm_delete:

                st.warning(f"Tem certeza que deseja excluir o estagiário **{st.session_state.confirm_delete['name']}**?")

                c1_conf, c2_conf, _ = st.columns([1,1,4])

                if c1_conf.button("SIM, EXCLUIR"):

                    delete_estagiario(st.session_state.confirm_delete['id'], st.session_state.confirm_delete['name'])

                    st.session_state.message = {'text': f"Estagiário {st.session_state.confirm_delete['name']} excluído!", 'type': 'success'}

                    st.session_state.confirm_delete, st.session_state.est_selecionado_id = None, None

                    st.rerun()

                if c2_conf.button("NÃO, CANCELAR"):

                    st.session_state.confirm_delete = None

                    st.rerun()



            df_estagiarios = list_estagiarios_df()

            nomes_estagiarios = [""] + df_estagiarios["nome"].tolist() if not df_estagiarios.empty else [""]

            nome_atual = ""

            if st.session_state.est_selecionado_id and not df_estagiarios.empty:

                nome_filtrado = df_estagiarios[df_estagiarios['id'] == st.session_state.est_selecionado_id]

                if not nome_filtrado.empty: nome_atual = nome_filtrado.iloc[0]['nome']



            nome_selecionado = st.selectbox("Selecione um estagiário para editar", options=nomes_estagiarios, index=nomes_estagiarios.index(nome_atual) if nome_atual in nomes_estagiarios else 0, disabled=bool(st.session_state.confirm_delete))

            st.divider()



            if nome_selecionado and not st.session_state.confirm_delete:

                id_selecionado = df_estagiarios[df_estagiarios["nome"] == nome_selecionado].iloc[0]['id']

                est_selecionado_dict = df_estagiarios[df_estagiarios['id'] == id_selecionado].iloc[0].to_dict()

                

                with st.form("form_edit_cadastro"):

                    st.subheader(f"Editando: {est_selecionado_dict['nome']}")

                    nome_default = est_selecionado_dict["nome"]

                    uni_default = est_selecionado_dict.get("universidade")

                    uni_index = universidades_padrao.index(uni_default) if uni_default in universidades_padrao else 0

                    

                    nome = st.text_input("Nome*", value=nome_default)

                    universidade_selecionada = st.selectbox("Universidade*", options=universidades_padrao, index=uni_index)

                    universidade_final = universidade_selecionada

                    if universidade_selecionada == "Outra (cadastrar manualmente)":

                        universidade_final = st.text_input("Digite o nome da Universidade*", value=uni_default if uni_default not in universidades_padrao else "")

                    

                    termo_meses = meses_por_universidade(universidade_final)

                    data_adm_default = pd.to_datetime(est_selecionado_dict.get("data_admissao"), dayfirst=True, errors='coerce').date()

                    data_renov_default = pd.to_datetime(est_selecionado_dict.get("data_ult_renovacao"), dayfirst=True, errors='coerce').date() if "Contrato" not in str(est_selecionado_dict.get("data_ult_renovacao")) else None

                    obs_default = est_selecionado_dict.get("obs", "")



                    c1, c2 = st.columns(2)

                    data_adm = c1.date_input("Data de Admissão*", value=data_adm_default)

                    data_renov = c2.date_input("Data da Última Renovação", value=data_renov_default, disabled=(termo_meses >= 24))

                    if termo_meses >= 24:

                        c2.info("Contrato único. Não requer renovação.")



                    obs = st.text_area("Observações", value=obs_default, height=100)

                    st.markdown("---")

                    

                    c_submit, c_delete, c_cancel = st.columns([1,1,2])

                    if c_submit.form_submit_button("💾 Salvar Alterações"):

                        if not nome.strip() or not universidade_final.strip() or not data_adm:

                            st.session_state.message = {'text': "Preencha todos os campos obrigatórios (*).", 'type': 'warning'}

                        else:

                            nome_upper, uni_upper, obs_upper = nome.strip().upper(), universidade_final.strip().upper(), obs.strip().upper()

                            data_venc = calcular_vencimento_final(data_adm)

                            update_estagiario(id_selecionado, nome_upper, uni_upper, data_adm, data_renov, obs_upper, data_venc)

                            st.session_state.message = {'text': f"Estagiário {nome_upper} atualizado!", 'type': 'success'}

                            st.session_state.est_selecionado_id = None

                        st.rerun()

                    if c_delete.form_submit_button("🗑️ Excluir"):

                        st.session_state.confirm_delete = {'id': id_selecionado, 'name': nome}

                        st.rerun()

                    if c_cancel.form_submit_button("🧹 Cancelar Edição"):

                        st.session_state.est_selecionado_id = None

                        st.rerun()



    if selected == "Regras":

        st.subheader("Gerenciar Regras de Contrato")

        st.info("Defina o tempo máximo de contrato para cada universidade (não pode exceder 24 meses).")



        if 'message_rule' not in st.session_state: st.session_state.message_rule = None

        if 'confirm_delete_rule' not in st.session_state: st.session_state.confirm_delete_rule = None



        if st.session_state.message_rule:

            show_message(st.session_state.message_rule)

            st.session_state.message_rule = None



        if st.session_state.confirm_delete_rule:

            st.warning(f"Tem certeza que deseja excluir a regra **{st.session_state.confirm_delete_rule['keyword']}**?")

            col1_conf, col2_conf, _ = st.columns([1,1,4])

            if col1_conf.button("SIM, EXCLUIR REGRA"):

                delete_regra(int(st.session_state.confirm_delete_rule['id']), st.session_state.confirm_delete_rule['keyword'])

                st.session_state.message_rule = {'text': f"Regra {st.session_state.confirm_delete_rule['keyword']} excluída com sucesso!", 'type': 'success'}

                st.session_state.confirm_delete_rule = None

                st.rerun()

            if col2_conf.button("NÃO, CANCELAR EXCLUSÃO"):

                st.session_state.confirm_delete_rule = None

                st.rerun()

        

        else:

            df_regras = list_regras()

            if df_regras.empty:

                st.info("Nenhuma regra cadastrada. Universidades sem regra específica usarão o padrão de 6 meses.")

            else:

                st.table(df_regras.rename(columns={"keyword": "Universidade", "meses": "Meses"}))

            st.divider()



            c1, c2 = st.columns(2)

            with c1:

                with st.form("form_add_edit_regra"):

                    st.subheader("Adicionar / Editar Regra")

                    universidade_selecionada = st.selectbox("Universidade", options=universidades_padrao, index=None, placeholder="Selecione para adicionar ou editar...")

                    keyword_final = ""

                    if universidade_selecionada == "Outra (cadastrar manualmente)":

                        keyword_final = st.text_input("Digite o Nome ou Palavra-chave").upper()

                    elif universidade_selecionada:

                        keyword_final = universidade_selecionada.upper()

                    meses = st.number_input("Meses de contrato", min_value=1, max_value=24, value=6, step=1)

                    add_button = st.form_submit_button("Salvar Regra")

                    if add_button and keyword_final.strip():

                        add_regra(keyword_final, meses)

                        st.session_state.message_rule = {'text': f"Regra para '{keyword_final}' salva!", 'type': 'success'}

                        st.rerun()

            

            with c2:

                with st.form("form_delete_regra"):

                    st.subheader("Excluir Regra")

                    if not df_regras.empty:

                        opcoes = {f"{r['id']} - {r['keyword']}": r for _, r in df_regras.iterrows()}

                        regra_para_deletar_str = st.selectbox("Selecione a regra para excluir", options=opcoes.keys())

                        delete_button = st.form_submit_button("🗑️ Excluir")

                        if delete_button and regra_para_deletar_str:

                            regra_selecionada = opcoes[regra_para_deletar_str]

                            st.session_state.confirm_delete_rule = {'id': regra_selecionada['id'], 'keyword': regra_selecionada['keyword']}

                            st.rerun()

                    else: 

                        st.info("Nenhuma regra para excluir.")

                        st.form_submit_button("🗑️ Excluir", disabled=True)



    if selected == "Import/Export":

        st.subheader("Importar / Exportar Dados")

        st.info("O arquivo Excel deve conter as colunas: 'nome', 'universidade', 'data_admissao', 'data_ult_renovacao' (opcional), 'obs' (opcional).")

        arquivo = st.file_uploader("Importar de um arquivo Excel (.xlsx)", type=["xlsx"])

        if arquivo:

            df_import = pd.read_excel(arquivo)

            count = 0

            with st.spinner("Importando dados..."):

                for _, row in df_import.iterrows():

                    try:

                        nome = str(row.get("nome","")).strip().upper()

                        universidade = str(row.get("universidade","")).strip().upper()

                        data_adm = pd.to_datetime(row.get("data_admissao")).date()

                        data_renov = pd.to_datetime(row.get("data_ult_renovacao")).date() if pd.notna(row.get("data_ult_renovacao")) else None

                        obs = str(row.get("obs","")).strip().upper()

                        if nome and universidade and data_adm:

                            data_venc = calcular_vencimento_final(data_adm)

                            insert_estagiario(nome, universidade, data_adm, data_renov, obs, data_venc)

                            count += 1

                    except Exception as e: st.warning(f"Erro ao importar a linha com nome '{nome}': {e}")

            show_message({'text': f"{count} estagiários importados com sucesso!", 'type': 'success'})

        st.divider()

        df_export = list_estagiarios_df()

        st.download_button("📥 Exportar Todos os Dados para Excel", exportar_para_excel_bytes(df_export), "estagiarios_export_completo.xlsx")

        

    if selected == "Área Administrativa":

        st.subheader("🔑 Área Administrativa")

        

        if 'admin_logged_in' not in st.session_state: st.session_state.admin_logged_in = False

        admin_password = get_config("admin_password")

        

        if not st.session_state.admin_logged_in:

            with st.form("admin_login_form"):

                st.text_input("Senha", type="password", key="admin_pw_input_main", label_visibility="collapsed", placeholder="Senha de Administrador")

                if st.form_submit_button("Entrar"):

                    if st.session_state.admin_pw_input_main == admin_password:

                        st.session_state.admin_logged_in = True

                        st.rerun()

                    else:

                        st.error("Senha incorreta.")

        

        if st.session_state.admin_logged_in:

            st.success("Acesso liberado!")

            

            c1, c2 = st.columns(2)

            with c1:

                st.subheader("Backup do Banco de Dados")

                if os.path.exists(DB_FILE):

                    with open(DB_FILE, "rb") as f:

                        db_bytes = f.read()

                    st.download_button(label="📥 Baixar Backup", data=db_bytes, file_name="backup_estagiarios.db", mime="application/octet-stream")



            with c2:

                st.subheader("Logs do Sistema")

                filter_date = st.date_input("Filtrar logs por data:", value=None)

                logs_df = list_logs_df(filter_date=filter_date)

                

                if logs_df.empty:

                    st.info("Nenhum log encontrado para a data selecionada.")

                else:

                    st.dataframe(logs_df, use_container_width=True, hide_index=True)

                

                log_bytes = exportar_logs_bytes()

                st.download_button(label="📥 Baixar Log Completo", data=log_bytes, file_name="log_completo.txt", mime="text/plain")



            if st.button("Sair da Área Admin"):

                st.session_state.admin_logged_in = False

                st.rerun()



if __name__ == "__main__":

    main()
