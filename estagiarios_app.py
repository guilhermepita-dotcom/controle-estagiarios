import os
from datetime import date, datetime
from contextlib import contextmanager
from typing import Optional, Dict, Any

import pandas as pd
import sqlite3
import streamlit as st
from dateutil.relativedelta import relativedelta
from PIL import Image
from streamlit_option_menu import option_menu
import pytz # <-- LINHA CORRIGIDA

# ==========================
# Configurações e Constantes
# ==========================
DB_FILE = "estagiarios.db"
LOGO_FILE = "logo.png"
DEFAULT_PROXIMOS_DIAS = 30
DEFAULT_DURATION_OTHERS = 6
DEFAULT_REGRAS = [("UERJ", 24), ("UNIRIO", 24), ("MACKENZIE", 24)]
TIMEZONE = pytz.timezone("America/Sao_Paulo")

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
    c.execute("""
        CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            action TEXT NOT NULL,
            details TEXT
        )
    """)
    
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
def log_action(action: str, details: str = ""):
    conn = get_db_connection()
    timestamp = datetime.now(TIMEZONE).strftime("%Y-%m-%d %H:%M:%S")
    conn.execute("INSERT INTO logs (timestamp, action, details) VALUES (?, ?, ?)", (timestamp, action, details))
    conn.commit()

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
    log_action("NOVO ESTAGIÁRIO", f"Nome: {nome}, Universidade: {universidade}")

def update_estagiario(est_id: int, nome: str, universidade: str, data_adm: date, data_renov: Optional[date], obs: str, data_venc: Optional[date]):
    conn = get_db_connection()
    conn.execute("UPDATE estagiarios SET nome=?, universidade=?, data_admissao=?, data_ult_renovacao=?, obs=?, data_vencimento=? WHERE id=?", (nome, universidade, str(data_adm), str(data_renov) if data_renov else None, obs, str(data_venc) if data_venc else None, est_id))
    conn.commit()
    log_action("ESTAGIÁRIO ATUALIZADO", f"ID: {est_id}, Nome: {nome}")

def delete_estagiario(est_id: int, nome: str):
    conn = get_db_connection()
    conn.execute("DELETE FROM estagiarios WHERE id=?", (int(est_id),))
    conn.commit()
    log_action("ESTAGIÁRIO EXCLUÍDO", f"ID: {est_id}, Nome: {nome}")

def add_regra(keyword: str, meses: int):
    conn = get_db_connection()
    conn.execute("INSERT OR REPLACE INTO regras(keyword, meses) VALUES (?, ?)", (keyword.upper().strip(), meses))
    conn.commit()
    log_action("REGRA ADICIONADA/EDITADA", f"Universidade: {keyword}, Meses: {meses}")

def delete_regra(regra_id: int, keyword: str):
    conn = get_db_connection()
    conn.execute("DELETE FROM regras WHERE id=?", (int(regra_id),))
    conn.commit()
    log_action("REGRA EXCLUÍDA", f"ID: {regra_id}, Universidade: {keyword}")

def list_logs_df(start_date: Optional[date] = None, end_date: Optional[date] = None) -> pd.DataFrame:
    conn = get_db_connection()
    query = "SELECT timestamp, action, details FROM logs"
    params = {}
    if start_date and end_date:
        query += " WHERE date(timestamp) BETWEEN :start_date AND :end_date"
        params['start_date'] = start_date.strftime('%Y-%m-%d')
        params['end_date'] = end_date.strftime('%Y-%m-%d')
    query += " ORDER BY id DESC LIMIT 50"
    df = pd.read_sql_query(query, conn, params=params if params else None)
    return df

def exportar_logs_bytes(start_date: Optional[date] = None, end_date: Optional[date] = None) -> bytes:
    conn = get_db_connection()
    query = "SELECT timestamp, action, details FROM logs"
    params = {}
    if start_date and end_date:
        query += " WHERE date(timestamp) BETWEEN :start_date AND :end_date"
        params['start_date'] = start_date.strftime('%Y-%m-%d')
        params['end_date'] = end_date.strftime('%Y-%m-%d')
    query += " ORDER BY id ASC"
    df = pd.read_sql_query(query, conn, params=params if params else None)
    log_string = df.to_string(index=False)
    return log_string.encode('utf-8')

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

    c1, c2 = st.columns([1, 5], vertical_alignment="center")
    with c1:
        if os.path.exists(LOGO_FILE):
            st.image(LOGO_FILE, width=150)
    with c2:
        st.markdown("<h1 style='margin-bottom: -15px;'>Controle de Contratos de Estagiários</h1>", unsafe_allow_html=True)
        st.caption("Cadastro, Renovação e Acompanhamento de Vencimentos")
    
    selected = option_menu(
        menu_title=None,
        options=["Dashboard", "Base", "Cadastro", "Regras", "Import/Export", "Área Administrativa"],
        icons=['bar-chart-line-fill', 'database-fill', 'pencil-square', 'gear-fill', 'cloud-upload-fill', 'key-fill'],
        menu_icon="cast", 
        default_index=0,
        orientation="horizontal",
        styles={
            "container": {"padding": "0!important", "background-color": "transparent", "border-bottom": "1px solid #333"},
            "icon": {"color": "var(--text-color-muted)", "font-size": "20px"},
            "nav-link": {
                "font-size": "16px", "text-align": "center", "margin": "0px",
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
    
    if 'main_selection' not in st.session_state: st.session_state.main_selection = "Dashboard"
    if selected != st.session_state.main_selection:
        st.session_state.main_selection = selected
        for key in ['sub_menu_cad', 'cadastro_universidade', 'est_selecionado_id', 'confirm_delete', 'confirm_delete_rule', 'filtro_status_dash', 'filtro_nome_dash']:
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
        
        st.subheader("Consulta Rápida:")
        if 'filtro_status_dash' not in st.session_state: st.session_state.filtro_status_dash = []
        if 'filtro_nome_dash' not in st.session_state: st.session_state.filtro_nome_dash = ""
        
        filtros_c1, filtros_c2 = st.columns(2)
        st.session_state.filtro_status_dash = filtros_c1.multiselect("Filtrar por status", options=["OK", "Venc.Proximo", "Vencido"], default=st.session_state.filtro_status_dash)
        st.session_state.filtro_nome_dash = filtros_c2.text_input("🔎 Buscar por Nome do Estagiário", value=st.session_state.filtro_nome_dash)

        if not st.session_state.filtro_status_dash and not st.session_state.filtro_nome_dash.strip():
            st.info("Aplique um filtro para visualizar os resultados.")
        else:
            df_view = df.copy()
            if st.session_state.filtro_status_dash: df_view = df_view[df_view["status"].isin(st.session_state.filtro_status_dash)]
            if st.session_state.filtro_nome_dash.strip(): df_view = df_view[df_view["nome"].str.contains(st.session_state.filtro_nome_dash.strip(), case=False, na=False)]
            if df_view.empty:
                st.warning("Nenhum registro encontrado para os filtros selecionados.")
            else:
                df_view["proxima_renovacao"] = df_view.apply(calcular_proxima_renovacao, axis=1)
                df_display = df_view.rename(columns={'id': 'ID', 'nome': 'Nome', 'universidade': 'Universidade','data_admissao': 'Data Admissão', 'data_ult_renovacao': 'Renovado em:','status': 'Status', 'ultimo_ano': 'Ultimo Ano?','proxima_renovacao': 'Proxima Renovação', 'data_vencimento': 'Termino de Contrato','obs': 'Observação'})
                colunas_ordenadas = ['ID', 'Nome', 'Universidade', 'Data Admissão', 'Renovado em:', 'Status', 'Ultimo Ano?', 'Proxima Renovação', 'Termino de Contrato', 'Observação']
                df_display = df_display.reindex(columns=colunas_ordenadas)
                st.dataframe(df_display, use_container_width=True, hide_index=True)
                st.download_button("📥 Exportar Resultado", exportar_para_excel_bytes(df_view), "estagiarios_filtrados.xlsx", key="download_dashboard")

    if selected == "Base":
        st.subheader("🗃️ Base Completa de Estagiários")
        df_base = list_estagiarios_df()
        
        if df_base.empty:
            st.info("Nenhum estagiário cadastrado.")
        else:
            df_base["status"] = df_base["data_vencimento"].apply(lambda d: classificar_status(d, int(get_config("proximos_dias"))))
            filtro_status_base = st.multiselect("Filtrar por status", options=["OK", "Venc.Proximo", "Vencido"], default=[])
            
            df_view_base = df_base.copy()
            if filtro_status_base:
                df_view_base = df_view_base[df_view_base["status"].isin(filtro_status_base)]
            
            df_view_base["proxima_renovacao"] = df_view_base.apply(calcular_proxima_renovacao, axis=1)
            df_display_base = df_view_base.rename(columns={'id': 'ID', 'nome': 'Nome', 'universidade': 'Universidade','data_admissao': 'Data Admissão', 'data_ult_renovacao': 'Renovado em:','status': 'Status', 'ultimo_ano': 'Ultimo Ano?','proxima_renovacao': 'Proxima Renovação', 'data_vencimento': 'Termino de Contrato','obs': 'Observação'})
            colunas_ordenadas_base = ['ID', 'Nome', 'Universidade', 'Data Admissão', 'Renovado em:', 'Status', 'Ultimo Ano?', 'Proxima Renovação', 'Termino de Contrato', 'Observação']
            df_display_base = df_display_base.reindex(columns=colunas_ordenadas_base)
            st.dataframe(df_display_base, use_container_width=True, hide_index=True)

    if selected == "Cadastro":
        # (O código da aba Cadastro permanece o mesmo)
        ...

    if selected == "Regras":
        # (O código da aba Regras permanece o mesmo)
        ...

    if selected == "Import/Export":
        # (O código da aba Import/Export permanece o mesmo)
        ...
        
    if selected == "Área Administrativa":
        # (O código da aba Área Administrativa permanece o mesmo)
        ...

if __name__ == "__main__":
    main()
