import os
from datetime import date
from contextlib import contextmanager
from typing import Optional

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
# Banco de Dados
# ==========================
@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
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
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL,
                universidade TEXT NOT NULL,
                data_admissao TEXT NOT NULL,
                data_ult_renovacao TEXT,
                ultimo_ano INTEGER DEFAULT 0,
                obs TEXT,
                data_vencimento TEXT NOT NULL
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS regras (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                keyword TEXT UNIQUE NOT NULL,
                meses INTEGER NOT NULL
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS config (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)
        for kw, meses in DEFAULT_REGRAS:
            c.execute("INSERT OR IGNORE INTO regras(keyword, meses) VALUES (?, ?)", (kw.upper(), meses))
        c.execute("INSERT OR IGNORE INTO config(key, value) VALUES('proximos_dias', ?)", (str(DEFAULT_PROXIMOS_DIAS),))


def get_config(key: str, default: Optional[str] = None) -> str:
    with get_conn() as conn:
        c = conn.cursor()
        row = c.execute("SELECT value FROM config WHERE key=?", (key,)).fetchone()
        return row[0] if row else (default if default is not None else "")


def set_config(key: str, value: str):
    with get_conn() as conn:
        c = conn.cursor()
        c.execute(
            "INSERT INTO config(key, value) VALUES(?, ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, value),
        )

# ==========================
# Funções Estagiários
# ==========================
def list_estagiarios_df() -> pd.DataFrame:
    with get_conn() as conn:
        df = pd.read_sql_query(
            "SELECT id, nome, universidade, data_admissao, data_ult_renovacao, ultimo_ano, obs, data_vencimento FROM estagiarios ORDER BY date(data_vencimento) ASC",
            conn
        )
        for col in ["data_admissao", "data_ult_renovacao", "data_vencimento"]:
            df[col] = pd.to_datetime(df[col], errors='coerce').dt.date
        df["ultimo_ano"] = df["data_admissao"].apply(lambda d: "SIM" if d and date.today().year == d.year + 2 else "NÃO")
        for col in ["data_admissao", "data_ult_renovacao", "data_vencimento"]:
            df[col] = df[col].apply(lambda x: x.strftime("%d.%m.%Y") if pd.notnull(x) else "")
    return df


def insert_estagiario(nome, universidade, data_adm, data_renov, ultimo_ano, obs, data_venc):
    with get_conn() as conn:
        c = conn.cursor()
        c.execute("""
            INSERT INTO estagiarios(nome, universidade, data_admissao, data_ult_renovacao, ultimo_ano, obs, data_vencimento)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (nome.strip(), universidade.strip(), str(data_adm), str(data_renov) if data_renov else None, 1 if ultimo_ano else 0, obs.strip() if obs else "", str(data_venc)))


def update_estagiario(est_id, nome, universidade, data_adm, data_renov, ultimo_ano, obs, data_venc):
    with get_conn() as conn:
        c = conn.cursor()
        c.execute("""
            UPDATE estagiarios
            SET nome=?, universidade=?, data_admissao=?, data_ult_renovacao=?, ultimo_ano=?, obs=?, data_vencimento=?
            WHERE id=?
        """, (nome.strip(), universidade.strip(), str(data_adm), str(data_renov) if data_renov else None, 1 if ultimo_ano else 0, obs.strip() if obs else "", str(data_venc), est_id))


def delete_estagiario(est_id):
    with get_conn() as conn:
        c = conn.cursor()
        c.execute("DELETE FROM estagiarios WHERE id=?", (int(est_id),))


# ==========================
# Funções Regras / Status
# ==========================
def list_regras():
    with get_conn() as conn:
        return pd.read_sql_query("SELECT id, keyword, meses FROM regras ORDER BY keyword", conn)


def add_regra(keyword, meses):
    with get_conn() as conn:
        c = conn.cursor()
        c.execute("INSERT OR REPLACE INTO regras(keyword, meses) VALUES (?, ?)", (keyword.upper(), int(meses)))


def meses_por_universidade(universidade):
    if not universidade:
        return DEFAULT_DURATION_OTHERS
    uni_up = universidade.upper()
    df = list_regras()
    meses = DEFAULT_DURATION_OTHERS
    for _, row in df.iterrows():
        if row["keyword"] in uni_up:
            meses = max(meses, int(row["meses"]))
    return meses


def calcular_vencimento(universidade, data_adm, data_renov):
    base = data_renov if data_renov else data_adm
    meses = meses_por_universidade(universidade)
    return base + relativedelta(months=meses)


def classificar_status(data_venc, proximos_dias):
    if not data_venc:
        return "SEM DATA"
    delta = (data_venc - date.today()).days
    if delta < 0:
        return "Vencido"
    if delta <= proximos_dias:
        return "Venc.Proximo"
    return "OK"


def exportar_para_excel_bytes(df):
    df_export = df.copy()
    df_export.sort_values("data_vencimento", inplace=True)
    path_temp = "temp.xlsx"
    with pd.ExcelWriter(path_temp, engine="openpyxl") as writer:
        df_export.to_excel(writer, index=False, sheet_name="Estagiarios")
    with open(path_temp, "rb") as f:
        data_bytes = f.read()
    os.remove(path_temp)
    return data_bytes


def highlight_ultimo_ano(row):
    styles = [''] * len(row)
    if 'ultimo_ano' in row.index and row['ultimo_ano'] == "SIM":
        idx = list(row.index).index('ultimo_ano')
        styles[idx] = "background-color: rgba(255, 0, 0, 0.2);"
    return styles

# ==========================
# Main App
# ==========================
def main():
    init_db()

    # --------------------------
    # Logo pequena no canto esquerdo
    # --------------------------
    if os.path.exists(LOGO_FILE):
        logo = Image.open(LOGO_FILE)
        logo.thumbnail((120, 120))
        st.image(logo, use_column_width=False)

    st.markdown(
        "<h2 style='text-align: center;'>📋 Controle de Contratos de Estagiários</h2>"
        "<p style='text-align: center; font-size:18px;'>Cadastro, Renovação e Acompanhamento de Vencimentos</p>",
        unsafe_allow_html=True
    )

    proximos_dias = int(get_config("proximos_dias", str(DEFAULT_PROXIMOS_DIAS)))
    proximos_dias = st.sidebar.number_input("Janela 'Venc.Proximo' (dias)", min_value=1, max_value=120, value=proximos_dias, step=1)
    set_config("proximos_dias", str(proximos_dias))

    # Tabs
    tab_dash, tab_cad, tab_regras, tab_io = st.tabs(["📊 Dashboard", "📝 Cadastro/Editar", "🧠 Regras", "📥 Import/Export"])

    # ==========================
    # Dashboard
    # ==========================
    with tab_dash:
        df = list_estagiarios_df()
        if df.empty:
            st.info("Sem dados ainda.")
        else:
            df["status"] = df["data_vencimento"].apply(lambda d: classificar_status(pd.to_datetime(d, dayfirst=True).date(), proximos_dias))
            total = len(df)
            ok = (df["status"] == "OK").sum()
            prox = (df["status"] == "Venc.Proximo").sum()
            venc = (df["status"] == "Vencido").sum()

            c1, c2, c3, c4 = st.columns(4)
            for col, titulo, valor in zip([c1, c2, c3, c4],
                                          ["👥Total de Estagiários", "✅Contratos OK", "⚠️Vencimentos Próximos", "⛔Contratos Vencidos"],
                                          [total, ok, prox, venc]):
                col.metric(titulo, valor)

            st.divider()
            st.subheader("Consulta rápida")
            filtro_status = st.multiselect("Filtrar status", ["OK", "Venc.Proximo", "Vencido"], default=[])
            filtro_nome = st.text_input("Buscar por Nome do Estagiário")

            df_view = df.copy()
            if filtro_status:
                df_view = df_view[df_view["status"].isin(filtro_status)]
            if filtro_nome.strip():
                df_view = df_view[df_view["nome"].str.contains(filtro_nome.strip(), case=False, na=False)]

            st.dataframe(df_view.style.apply(highlight_ultimo_ano, axis=1), use_container_width=True)

            st.download_button("📥 Exportar Excel", exportar_para_excel_bytes(df_view), file_name="estagiarios_export.xlsx")

# ==========================
# Executar
# ==========================
if __name__ == "__main__":
    main()
