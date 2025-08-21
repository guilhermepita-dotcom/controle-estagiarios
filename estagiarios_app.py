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
        # Tabela estagiários
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
        # Tabela regras
        c.execute("""
            CREATE TABLE IF NOT EXISTS regras (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                keyword TEXT UNIQUE NOT NULL,
                meses INTEGER NOT NULL
            )
        """)
        # Configuração
        c.execute("""
            CREATE TABLE IF NOT EXISTS config (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)
        # Inserir regras padrão
        for kw, meses in DEFAULT_REGRAS:
            c.execute("INSERT OR IGNORE INTO regras(keyword, meses) VALUES (?, ?)", (kw.upper(), meses))
        # Inserir configuração padrão
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


def delete_regra(regra_id):
    with get_conn() as conn:
        c = conn.cursor()
        c.execute("DELETE FROM regras WHERE id=?", (regra_id,))


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
# Funções UI principais
# ==========================
def exibir_logo():
    if os.path.exists(LOGO_FILE):
        logo = Image.open(LOGO_FILE)
        wpercent = (400 / float(logo.size[0]))
        hsize = int((float(logo.size[1]) * float(wpercent)))
        logo = logo.resize((200, hsize), Image.Resampling.LANCZOS)
        st.image(logo, use_container_width=False)


def exibir_cabecalho():
    st.markdown(
        "<h2 style='text-align: center;'>📋 Controle de Contratos de Estagiários</h2>"
        "<p style='text-align: center; font-size:18px;'>Cadastro, Renovação e Acompanhamento de Vencimentos</p>",
        unsafe_allow_html=True
    )


# ==========================
# Main App
# ==========================
def main():
    init_db()
    exibir_logo()
    exibir_cabecalho()

    proximos_dias = int(get_config("proximos_dias", str(DEFAULT_PROXIMOS_DIAS)))
    proximos_dias = st.sidebar.number_input(
        "Janela 'Venc.Proximo' (dias)", min_value=1, max_value=120, value=proximos_dias, step=1
    )
    set_config("proximos_dias", str(proximos_dias))

    tab_dash, tab_cad, tab_regras, tab_io = st.tabs(
        ["📊 Dashboard", "📝 Cadastro/Editar", "🧠 Regras", "📥 Import/Export"]
    )

    # ==========================
    # Dashboard
    # ==========================
    with tab_dash:
        df = list_estagiarios_df()
        if df.empty:
            st.info("Sem dados ainda.")
        else:
            df["status"] = df["data_vencimento"].apply(
                lambda d: classificar_status(pd.to_datetime(d, dayfirst=True).date(), proximos_dias)
            )
            total = len(df)
            ok = (df["status"] == "OK").sum()
            prox = (df["status"] == "Venc.Proximo").sum()
            venc = (df["status"] == "Vencido").sum()

            c1, c2, c3, c4 = st.columns(4)
            for col, titulo, valor in zip(
                [c1, c2, c3, c4],
                ["👥Total de Estagiários", "✅Contratos OK", "⚠️Vencimentos Próximos", "⛔Contratos Vencidos"],
                [total, ok, prox, venc]
            ):
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

            st.download_button(
    label="📥 Exportar Excel",
    data=exportar_para_excel_bytes(df_view),
    file_name="estagiarios_export.xlsx",
    key="download_dashboard"
)

    # ==========================
    # Cadastro/Editar
    # ==========================
    with tab_cad:
        st.subheader("Cadastro/Editar Estagiário")
        df_estagiarios = list_estagiarios_df()
        nomes_estagiarios = df_estagiarios["nome"].tolist()
        busca = st.text_input("Buscar Estagiário pelo nome")
        est_selecionado = None
        if busca.strip():
            resultados = [nome for nome in nomes_estagiarios if busca.strip().lower() in nome.lower()]
            if resultados:
                est_nome_selecionado = st.selectbox("Selecionar Estagiário", resultados)
                est_selecionado = df_estagiarios[df_estagiarios["nome"] == est_nome_selecionado].iloc[0]
            else:
                st.info("Nenhum estagiário encontrado")

        nome_default = est_selecionado["nome"] if est_selecionado is not None else ""
        universidade_default = est_selecionado["universidade"] if est_selecionado is not None else universidades_padrao[0]
        data_adm_default = pd.to_datetime(est_selecionado["data_admissao"], dayfirst=True).date() if est_selecionado is not None else date.today()
        data_renov_default = pd.to_datetime(est_selecionado["data_ult_renovacao"], dayfirst=True).date() if est_selecionado is not None else date.today()
        obs_default = est_selecionado["obs"] if est_selecionado is not None else ""

        with st.form("form_cadastro"):
            nome = st.text_input("Nome do Estagiário", value=nome_default)
            universidade = st.selectbox(
                "Universidade",
                universidades_padrao,
                index=universidades_padrao.index(universidade_default) if universidade_default in universidades_padrao else 0
            )
            if universidade == "Outra (cadastrar manualmente)":
                universidade = st.text_input(
                    "Digite a Universidade",
                    value=universidade_default if universidade_default not in universidades_padrao else ""
                )

            data_adm = st.date_input("Data de Admissão", value=data_adm_default)
            data_renov = st.date_input("Data Últ. Renovação", value=data_renov_default)
            obs = st.text_area("Observações", value=obs_default, height=100)

            col1, col2, col3 = st.columns([1,1,1])
            submit = col1.form_submit_button("💾 Salvar")
            delete = col2.form_submit_button("🗑️ Excluir")
            novo = col3.form_submit_button("➕ Novo")

            if submit:
                if not nome.strip() or not universidade.strip() or not data_adm:
                    st.warning("Preencha todos os campos obrigatórios.")
                else:
                    data_venc = calcular_vencimento(universidade, data_adm, data_renov)
                    ultimo_ano = date.today().year == data_adm.year + 2
                    if est_selecionado is None:
                        insert_estagiario(nome, universidade, data_adm, data_renov, ultimo_ano, obs, data_venc)
                        st.success(f"Estagiário {nome} cadastrado com sucesso!")
                    else:
                        update_estagiario(est_selecionado["id"], nome, universidade, data_adm, data_renov, ultimo_ano, obs, data_venc)
                        st.success(f"Estagiário {nome} atualizado com sucesso!")

            if delete:
                if est_selecionado is None:
                    st.warning("Selecione um estagiário para excluir.")
                else:
                    confirm = st.checkbox(f"Confirme exclusão do estagiário {est_selecionado['nome']}")
                    if confirm:
                        delete_estagiario(est_selecionado["id"])
                        st.success(f"🗑️ Estagiário {est_selecionado['nome']} excluído com sucesso!")

            if novo:
                est_selecionado = None
                st.experimental_rerun()

    # ==========================
    # Regras
    # ==========================
    with tab_regras:
        st.subheader("Regras por Universidade (meses de contrato)")
        df_regras = list_regras()
        st.dataframe(df_regras, use_container_width=True)
        with st.form("form_regras"):
            keyword = st.text_input("Palavra-chave da Universidade").upper()
            meses = st.number_input("Meses de contrato", min_value=1, max_value=60, value=6)
            add = st.form_submit_button("➕ Adicionar/Atualizar")
            if add and keyword.strip():
                add_regra(keyword, meses)
                st.success(f"Regra {keyword} adicionada/atualizada!")
            delete_id = st.number_input("ID para deletar regra", min_value=0, step=1)
            del_btn = st.form_submit_button("🗑️ Deletar")
            if del_btn and delete_id > 0:
                delete_regra(delete_id)
                st.success(f"Regra {delete_id} deletada!")

    # ==========================
    # Import / Export
    # ==========================
    with tab_io:
        st.subheader("Importar / Exportar Estagiários")
        st.markdown("📥 Importar Excel")
        uploaded_file = st.file_uploader("Selecione arquivo Excel", type=["xlsx"])
        if uploaded_file:
            df_import = pd.read_excel(uploaded_file)
            st.dataframe(df_import)
            if st.button("💾 Importar para banco"):
                for _, row in df_import.iterrows():
                    nome = row.get("nome") or row.get("Nome")
                    universidade = row.get("universidade") or row.get("Universidade")
                    data_adm = row.get("data_admissao") or row.get("Data Admissão")
                    data_renov = row.get("data_ult_renovacao") or row.get("Data Últ. Renovação")
                    if isinstance(data_adm, pd.Timestamp):
                        data_adm = data_adm.date()
                    if isinstance(data_renov, pd.Timestamp):
                        data_renov = data_renov.date()
                    data_venc = calcular_vencimento(universidade, data_adm, data_renov)
                    ultimo_ano = date.today().year == data_adm.year + 2
                    insert_estagiario(nome, universidade, data_adm, data_renov, ultimo_ano, "", data_venc)
                st.success("Importação concluída!")

        st.markdown("📤 Exportar Excel completo")
        df_export = list_estagiarios_df()
        if not df_export.empty:
            st.download_button(
    label="📥 Exportar Excel",
    data=exportar_para_excel_bytes(df_export),
    file_name="estagiarios_export.xlsx",
    key="download_io"
)


if __name__ == "__main__":
    main()

