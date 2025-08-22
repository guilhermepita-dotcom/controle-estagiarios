import os
from datetime import date
from contextlib import contextmanager
from typing import Optional, Dict, Any

import pandas as pd
import sqlite3
import streamlit as st
from dateutil.relativedelta import relativedelta
from PIL import Image

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
st.set_page_config(page_title="Controle de Estagiários", layout="wide")

# ==========================
# Banco de Dados (sqlite3 padrão)
# ==========================
@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.commit()
        conn.close()

def init_db():
    with get_conn() as conn:
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
        for kw, meses in DEFAULT_REGRAS:
            c.execute("INSERT OR IGNORE INTO regras(keyword, meses) VALUES (?, ?)", (kw.upper(), meses))
        c.execute("INSERT OR IGNORE INTO config(key, value) VALUES(?, ?)", ('proximos_dias', str(DEFAULT_PROXIMOS_DIAS)))
        c.execute("INSERT OR IGNORE INTO config(key, value) VALUES(?, ?)", ('admin_password', '123456'))


def get_config(key: str, default: Optional[str] = None) -> str:
    with get_conn() as conn:
        c = conn.cursor()
        row = c.execute("SELECT value FROM config WHERE key=?", (key,)).fetchone()
        return row['value'] if row else (default if default is not None else "")

def set_config(key: str, value: str):
    with get_conn() as conn:
        c = conn.cursor()
        c.execute("INSERT INTO config(key, value) VALUES(?, ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key, value))

# ==========================
# Funções de Lógica e Auxiliares
# ==========================

def list_regras() -> pd.DataFrame:
    with get_conn() as conn:
        return pd.read_sql_query("SELECT id, keyword, meses FROM regras ORDER BY keyword", conn)

def meses_por_universidade(universidade: str) -> int:
    if not universidade: return DEFAULT_DURATION_OTHERS
    uni_up = universidade.upper()
    df_regras = list_regras()
    meses_encontrados = [DEFAULT_DURATION_OTHERS]
    for _, row in df_regras.iterrows():
        if row["keyword"] in uni_up:
            meses_encontrados.append(int(row["meses"]))
    return max(meses_encontrados)

def list_estagiarios_df() -> pd.DataFrame:
    with get_conn() as conn:
        try:
            df = pd.read_sql_query("SELECT * FROM estagiarios", conn, index_col="id")
        except (pd.io.sql.DatabaseError, ValueError): # Trata o caso de banco de dados vazio
             return pd.DataFrame()

    if df.empty:
        return pd.DataFrame(columns=['id', 'nome', 'universidade', 'data_admissao', 'data_ult_renovacao', 'obs', 'data_vencimento'])

    df.reset_index(inplace=True)
    
    df['data_vencimento_obj'] = pd.to_datetime(df['data_vencimento'], errors='coerce')
    df = df.sort_values(by='data_vencimento_obj', ascending=True).drop(columns=['data_vencimento_obj'])
    
    df_dates = df.copy()
    for col in ["data_admissao", "data_vencimento"]:
        df_dates[col] = pd.to_datetime(df_dates[col], errors='coerce').dt.date

    df["ultimo_ano"] = df_dates["data_vencimento"].apply(lambda d: "SIM" if pd.notna(d) and d.year == date.today().year else "NÃO")
    
    regras_df = list_regras()
    regras_24m_keywords = [row['keyword'] for index, row in regras_df.iterrows() if row['meses'] >= 24]
    if regras_24m_keywords:
        mask = (df['universidade'].str.upper().str.contains('|'.join(regras_24m_keywords), na=False)) & (df['data_ult_renovacao'].isnull() | df['data_ult_renovacao'].eq(''))
        df.loc[mask, 'data_ult_renovacao'] = "Contrato Único"
        
    return df

def insert_estagiario(nome: str, universidade: str, data_adm: date, data_renov: Optional[date], obs: str, data_venc: Optional[date]):
    with get_conn() as conn:
        c = conn.cursor()
        c.execute(
            "INSERT INTO estagiarios(nome, universidade, data_admissao, data_ult_renovacao, obs, data_vencimento) VALUES (?, ?, ?, ?, ?, ?)",
            (nome, universidade, str(data_adm), str(data_renov) if data_renov else None, obs, str(data_venc) if data_venc else None)
        )

def update_estagiario(est_id: int, nome: str, universidade: str, data_adm: date, data_renov: Optional[date], obs: str, data_venc: Optional[date]):
    with get_conn() as conn:
        c = conn.cursor()
        c.execute(
            "UPDATE estagiarios SET nome=?, universidade=?, data_admissao=?, data_ult_renovacao=?, obs=?, data_vencimento=? WHERE id=?",
            (nome, universidade, str(data_adm), str(data_renov) if data_renov else None, obs, str(data_venc) if data_venc else None, est_id)
        )

def delete_estagiario(est_id: int):
    with get_conn() as conn:
        c = conn.cursor()
        c.execute("DELETE FROM estagiarios WHERE id=?", (est_id,))

def add_regra(keyword: str, meses: int):
    with get_conn() as conn:
        c = conn.cursor()
        c.execute("INSERT OR IGNORE INTO regras(keyword, meses) VALUES (?, ?)", (keyword.upper().strip(), meses))

def update_regra(regra_id: int, keyword: str, meses: int):
    with get_conn() as conn:
        c = conn.cursor()
        c.execute("UPDATE regras SET keyword=?, meses=? WHERE id=?", (keyword.upper().strip(), meses, regra_id))

def calcular_vencimento_final(data_adm: Optional[date]) -> Optional[date]:
    if not data_adm: return None
    return data_adm + relativedelta(months=24)

def classificar_status(data_venc: Optional[str], proximos_dias: int) -> str:
    if not data_venc or pd.isna(data_venc): return "SEM DATA"
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
    data_adm = pd.to_datetime(row['data_admissao'], dayfirst=True, errors='coerce').date()
    data_ult_renov = pd.to_datetime(row['data_ult_renovacao'], dayfirst=True, errors='coerce').date()
    
    if pd.isna(data_adm): return ""
    
    termo_meses = meses_por_universidade(row['universidade'])
    if termo_meses >= 24: return ""

    limite_2_anos = data_adm + relativedelta(months=24)
    if limite_2_anos < hoje: return ""

    base_date = data_ult_renov if pd.notna(data_ult_renov) else data_adm
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

def highlight_status_and_year(row):
    styles = [''] * len(row)
    if 'status' in row.index:
        status_idx = list(row.index).index('status')
        if row['status'] == "Vencido": styles[status_idx] = "background-color: rgba(255, 0, 0, 0.3);"
        elif row['status'] == "Venc.Proximo": styles[status_idx] = "background-color: rgba(255, 255, 0, 0.4);"
    if 'ultimo_ano' in row.index and row['ultimo_ano'] == "SIM":
        ano_idx = list(row.index).index('ultimo_ano')
        styles[ano_idx] = "background-color: rgba(255, 165, 0, 0.3);"
    return styles

def show_message(message: Dict[str, Any]):
    if message['type'] == 'success': st.success(message['text'])
    elif message['type'] == 'warning': st.warning(message['text'])
    elif message['type'] == 'error': st.error(message['text'])
    else: st.info(message['text'])

# ==========================
# Main App
# ==========================
def main():
    init_db()

    col1, col2 = st.columns([1, 4], vertical_alignment="center")
    with col1:
        if os.path.exists(LOGO_FILE):
            logo = Image.open(LOGO_FILE)
            st.image(logo, width=200)
    with col2:
        st.markdown("<h1 style='text-align: left;'>Controle de Contratos de Estagiários</h1>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: left; font-size:18px;'>Cadastro, Renovação e Acompanhamento de Vencimentos</p>", unsafe_allow_html=True)
    
    st.divider()

    proximos_dias_input = st.sidebar.number_input("Janela 'Venc.Proximo' (dias)", min_value=1, max_value=120, value=int(get_config("proximos_dias", DEFAULT_PROXIMOS_DIAS)), step=1)
    set_config("proximos_dias", str(proximos_dias_input))

    st.sidebar.title("Área Administrativa")
    if 'admin_logged_in' not in st.session_state: st.session_state.admin_logged_in = False
    
    admin_password = get_config("admin_password")
    if not
