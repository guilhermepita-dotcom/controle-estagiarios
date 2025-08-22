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
LOGO_FILE = "logo.png"  # Coloque a logo na mesma pasta do app
DEFAULT_PROXIMOS_DIAS = 30
DEFAULT_DURATION_OTHERS = 6  # meses
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
        # Colunas de data
        for col in ["data_admissao", "data_ult_renovacao", "data_vencimento"]:
            df[col] = pd.to_datetime(df[col], errors='coerce').dt.date
        # Último ano automático
        df["ultimo_ano"] = df["data_admissao"].apply(lambda d: "SIM" if d and date.today() >= d + relativedelta(years=1, months=6) else "NÃO")
        # Formato dd.mm.yyyy
        for col in ["data_admissao", "data_ult_renovacao", "data_vencimento"]:
            df[col] = df[col].apply(lambda x: x.strftime("%d.%m.%Y") if pd.notnull(x) else "")
    return df


def insert_estagiario(nome: str, universidade: str, data_adm: date, data_renov: Optional[date], obs: str, data_venc: date):
    with get_conn() as conn:
        c = conn.cursor()
        ultimo_ano = 1 if date.today() >= data_adm + relativedelta(years=1, months=6) else 0
        c.execute(
            """
            INSERT INTO estagiarios(nome, universidade, data_admissao, data_ult_renovacao, ultimo_ano, obs, data_vencimento)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (nome.strip(), universidade.strip(), str(data_adm),
             str(data_renov) if data_renov else None, ultimo_ano,
             obs.strip() if obs else "", str(data_venc))
        )


def update_estagiario(est_id: int, nome: str, universidade: str, data_adm: date,
                      data_renov: Optional[date], obs: str, data_venc: date):
    with get_conn() as conn:
        c = conn.cursor()
        ultimo_ano = 1 if date.today() >= data_adm + relativedelta(years=1, months=6) else 0
        c.execute(
            """
            UPDATE estagiarios
            SET nome=?, universidade=?, data_admissao=?, data_ult_renovacao=?, ultimo_ano=?, obs=?, data_vencimento=?
            WHERE id=?
            """,
            (nome.strip(), universidade.strip(), str(data_adm),
             str(data_renov) if data_renov else None, ultimo_ano,
             obs.strip() if obs else "", str(data_venc), int(est_id))
        )


def delete_estagiario(est_id: int):
    with get_conn() as conn:
        c = conn.cursor()
        c.execute("DELETE FROM estagiarios WHERE id=?", (int(est_id),))

# ==========================
# Funções Regras e Status
# ==========================
def list_regras() -> pd.DataFrame:
    with get_conn() as conn:
        return pd.read_sql_query("SELECT id, keyword, meses FROM regras ORDER BY keyword", conn)


def add_regra(keyword: str, meses: int):
    with get_conn() as conn:
        c = conn.cursor()
        c.execute("INSERT OR IGNORE INTO regras(keyword, meses) VALUES (?, ?)", (keyword.upper().strip(), int(meses)))

# NOVA FUNÇÃO para atualizar regra
def update_regra(regra_id: int, keyword: str, meses: int):
    with get_conn() as conn:
        c = conn.cursor()
        c.execute("UPDATE regras SET keyword=?, meses=? WHERE id=?", (keyword.upper().strip(), int(meses), regra_id))

def delete_regra(regra_id: int):
    with get_conn() as conn:
        c = conn.cursor()
        c.execute("DELETE FROM regras WHERE id=?", (regra_id,))


def meses_por_universidade(universidade: str) -> int:
    if not universidade:
        return DEFAULT_DURATION_OTHERS
    uni_up = universidade.upper()
    df = list_regras()
    # Inicia com o padrão
    meses_encontrados = [DEFAULT_DURATION_OTHERS]
    for _, row in df.iterrows():
        if row["keyword"] in uni_up:
            meses_encontrados.append(int(row["meses"]))
    # Retorna o maior valor encontrado para garantir a regra mais específica/longa
    return max(meses_encontrados)


def calcular_vencimento(universidade: str, data_adm: Optional[date], data_renov: Optional[date]) -> Optional[date]:
    if not data_adm:
        return None
    # A base de cálculo é sempre a data de admissão
    base = data_adm
    meses = meses_por_universidade(universidade)

    # Se houver data de renovação, significa que estamos no segundo período de contrato
    if data_renov and data_renov > data_adm:
        return data_renov + relativedelta(months=meses)
    
    return base + relativedelta(months=meses)


def classificar_status(data_venc: Optional[date], proximos_dias: int) -> str:
    if not data_venc:
        return "SEM DATA"
    delta = (data_venc - date.today()).days
    if delta < 0:
        return "Vencido"
    if delta <= proximos_dias:
        return "Venc.Proximo"
    return "OK"


def exportar_para_excel_bytes(df: pd.DataFrame) -> bytes:
    df_export = df.copy()
    # Converte a data de vencimento para objeto date para ordenação correta
    df_export['data_vencimento_obj'] = pd.to_datetime(df_export['data_vencimento'], dayfirst=True, errors='coerce')
    df_export.sort_values("data_vencimento_obj", inplace=True)
    df_export.drop(columns=['data_vencimento_obj'], inplace=True)
    
    path_temp = "temp.xlsx"
    with pd.ExcelWriter(path_temp, engine="openpyxl") as writer:
        df_export.to_excel(writer, index=False, sheet_name="Estagiarios")
    with open(path_temp, "rb") as f:
        data_bytes = f.read()
    os.remove(path_temp)
    return data_bytes
# ==========================
# Funções Auxiliares UI
# ==========================
def highlight_status_and_year(row):
    styles = [''] * len(row)
    # Highlight para status
    status_idx = list(row.index).index('status')
    if row['status'] == "Vencido":
        styles[status_idx] = "background-color: rgba(255, 0, 0, 0.3);" # Vermelho
    elif row['status'] == "Venc.Proximo":
        styles[status_idx] = "background-color: rgba(255, 255, 0, 0.4);" # Amarelo
    
    # Highlight para último ano
    if 'ultimo_ano' in row.index and row['ultimo_ano'] == "SIM":
        ano_idx = list(row.index).index('ultimo_ano')
        styles[ano_idx] = "background-color: rgba(255, 165, 0, 0.3);" # Laranja
        
    return styles


# ==========================
# Main App
# ==========================
def main():
    init_db()

    # --- NOVO LAYOUT DO CABEÇALHO ---
    col1, col2 = st.columns([1, 4])
    with col1:
        if os.path.exists(LOGO_FILE):
            logo = Image.open(LOGO_FILE)
            st.image(logo, width=150)
    with col2:
        st.markdown(
            "<h1 style='text-align: left; margin-top: 20px;'>Controle de Contratos de Estagiários</h1>",
            unsafe_allow_html=True
        )
        st.markdown(
            "<p style='text-align: left; font-size:18px;'>Cadastro, Renovação e Acompanhamento de Vencimentos</p>",
            unsafe_allow_html=True
        )
    
    st.divider()

    proximos_dias = int(get_config("proximos_dias", str(DEFAULT_PROXIMOS_DIAS)))
    proximos_dias = st.sidebar.number_input(
        "Janela 'Venc.Proximo' (dias)", min_value=1, max_value=120, value=proximos_dias, step=1
    )
    set_config("proximos_dias", str(proximos_dias))

    tab_dash, tab_cad, tab_regras, tab_io = st.tabs([
        "📊 Dashboard", "📝 Cadastro/Editar", "⚙️ Regras", "📥 Import/Export"
    ])

    # ==========================
    # Dashboard
    # ==========================
    with tab_dash:
        df = list_estagiarios_df()
        if df.empty:
            st.info("Nenhum estagiário cadastrado ainda.")
        else:
            df["status"] = df["data_vencimento"].apply(
                lambda d: classificar_status(pd.to_datetime(d, dayfirst=True, errors='coerce').date(), proximos_dias)
            )
            total = len(df)
            ok = (df["status"] == "OK").sum()
            prox = (df["status"] == "Venc.Proximo").sum()
            venc = (df["status"] == "Vencido").sum()

            c1, c2, c3, c4 = st.columns(4)
            for col, titulo, valor in zip([c1, c2, c3, c4],
                                         ["👥Total de Estagiários", "✅Contratos OK",
                                          "⚠️Vencimentos Próximos", "⛔Contratos Vencidos"],
                                         [total, ok, prox, venc]):
                col.metric(titulo, valor)

            st.divider()
            st.subheader("Consulta Rápida de Estagiários")
            
            # Filtros
            filtro_status = st.multiselect("Filtrar por status", options=["OK", "Venc.Proximo", "Vencido"], default=[])
            filtro_nome = st.text_input("Buscar por Nome do Estagiário")

            df_view = df.copy()
            if filtro_status:
                df_view = df_view[df_view["status"].isin(filtro_status)]
            if filtro_nome.strip():
                df_view = df_view[df_view["nome"].str.contains(filtro_nome.strip(), case=False, na=False)]

            st.dataframe(df_view.style.apply(highlight_status_and_year, axis=1), use_container_width=True)

            st.download_button(
                "📥 Exportar para Excel",
                exportar_para_excel_bytes(df_view),
                file_name="estagiarios_export.xlsx",
                key="download_dashboard"
            )

    # ==========================
    # Cadastro/Editar
    # ==========================
    with tab_cad:
        st.subheader("Gerenciar Cadastro de Estagiário")

        df_estagiarios = list_estagiarios_df()
        
        # Lógica para seleção
        if 'est_selecionado_id' not in st.session_state:
            st.session_state.est_selecionado_id = None

        est_selecionado = None
        if st.session_state.est_selecionado_id:
            est_selecionado_list = df_estagiarios[df_estagiarios['id'] == st.session_state.est_selecionado_id]
            if not est_selecionado_list.empty:
                est_selecionado = est_selecionado_list.iloc[0]

        # Busca
        nomes_estagiarios = [""] + df_estagiarios["nome"].tolist()
        nome_selecionado = st.selectbox("Buscar e Selecionar Estagiário para Editar", options=nomes_estagiarios)
        
        if nome_selecionado:
            id_selecionado = df_estagiarios[df_estagiarios["nome"] == nome_selecionado].iloc[0]['id']
            st.session_state.est_selecionado_id = id_selecionado
            st.rerun() # Força o rerun para carregar os dados

        # Valores default - ALTERADO para campos em branco
        nome_default = est_selecionado["nome"] if est_selecionado is not None else ""
        uni_default_val = est_selecionado["universidade"] if est_selecionado is not None else None
        data_adm_default = pd.to_datetime(est_selecionado["data_admissao"], dayfirst=True).date() if est_selecionado is not None and est_selecionado["data_admissao"] else None
        data_renov_default = pd.to_datetime(est_selecionado["data_ult_renovacao"], dayfirst=True).date() if est_selecionado is not None and est_selecionado["data_ult_renovacao"] else None
        obs_default = est_selecionado["obs"] if est_selecionado is not None else ""

        with st.form("form_cadastro", clear_on_submit=True):
            nome = st.text_input("Nome do Estagiário*", value=nome_default)
            
            # Lógica para o selectbox de universidade
            uni_index = 0
            if uni_default_val:
                try:
                    uni_index = universidades_padrao.index(uni_default_val)
                except ValueError:
                    uni_index = len(universidades_padrao) -1 # Index de 'Outra'

            universidade_selecionada = st.selectbox("Universidade*", options=universidades_padrao, index=uni_index)
            
            if universidade_selecionada == "Outra (cadastrar manualmente)":
                universidade_final = st.text_input(
                    "Digite o nome da Universidade*",
                    value=uni_default_val if uni_default_val not in universidades_padrao else ""
                )
            else:
                universidade_final = universidade_selecionada

            c1, c2 = st.columns(2)
            data_adm = c1.date_input("Data de Admissão*", value=data_adm_default)
            data_renov = c2.date_input("Data da Última Renovação (se houver)", value=data_renov_default)
            
            obs = st.text_area("Observações", value=obs_default, height=100)

            st.markdown("---")
            col1, col2, col3, col4 = st.columns([2,2,2,2])
            submit = col1.form_submit_button("💾 Salvar")
            delete = col2.form_submit_button("🗑️ Excluir")
            novo = col3.form_submit_button("➕ Novo Cadastro")
            limpar = col4.form_submit_button("🧹 Limpar Campos") # NOVO BOTÃO

            if submit:
                if not nome.strip() or not universidade_final.strip() or not data_adm:
                    st.warning("Preencha todos os campos obrigatórios (*).")
                else:
                    data_venc = calcular_vencimento(universidade_final, data_adm, data_renov)
                    if data_venc:
                        if est_selecionado is None:
                            insert_estagiario(nome, universidade_final, data_adm, data_renov, obs, data_venc)
                            st.success(f"Estagiário {nome} cadastrado com sucesso!")
                        else:
                            update_estagiario(est_selecionado["id"], nome, universidade_final, data_adm, data_renov, obs, data_venc)
                            st.success(f"Estagiário {nome} atualizado com sucesso!")
                        st.session_state.est_selecionado_id = None # Limpa a seleção
                    else:
                        st.error("Não foi possível calcular a data de vencimento.")
            
            if delete:
                if est_selecionado is None:
                    st.warning("Selecione um estagiário para excluir.")
                else:
                    delete_estagiario(est_selecionado["id"])
                    st.success(f"🗑️ Estagiário {est_selecionado['nome']} excluído com sucesso!")
                    st.session_state.est_selecionado_id = None # Limpa a seleção

        # Ações dos botões que precisam de rerun
        if novo or limpar:
            st.session_state.est_selecionado_id = None
            st.rerun()

    # ==========================
    # Regras
    # ==========================
    with tab_regras:
        st.subheader("Regras de Duração do Contrato por Universidade (em meses)")
        
        st.info("O sistema aplicará a regra com o maior número de meses que corresponda a uma palavra-chave no nome da universidade. O padrão para outras é 6 meses.")
        
        df_regras = list_regras()
        st.dataframe(df_regras, use_container_width=True, hide_index=True)
        
        c1, c2 = st.columns(2)

        with c1:
            with st.form("form_regras"):
                st.subheader("Adicionar Nova Regra")
                keyword = st.text_input("Palavra-chave da Universidade").upper()
                meses = st.number_input("Meses de contrato", min_value=1, max_value=60, value=6, step=1)
                add_button = st.form_submit_button("Adicionar Regra")
                if add_button and keyword.strip():
                    add_regra(keyword, meses)
                    st.success(f"Regra '{keyword}' adicionada/atualizada com sucesso!")
                    st.rerun()

        # --- NOVA SEÇÃO DE EDIÇÃO DE REGRA ---
        with c2:
            with st.form("form_editar_regra"):
                st.subheader("Editar Regra Existente")
                if not df_regras.empty:
                    id_para_editar = st.selectbox(
                        "Selecione o ID da regra para editar", 
                        options=df_regras['id'].tolist()
                    )
                    regra_selecionada = df_regras[df_regras['id'] == id_para_editar].iloc[0]
                    
                    novo_keyword = st.text_input(
                        "Novo nome/palavra-chave", 
                        value=regra_selecionada['keyword']
                    ).upper()
                    
                    novos_meses = st.number_input(
                        "Novos meses de contrato", 
                        min_value=1, max_value=60, 
                        value=int(regra_selecionada['meses']), 
                        step=1
                    )
                    
                    update_button = st.form_submit_button("Salvar Alterações")
                    if update_button and novo_keyword.strip():
                        update_regra(id_para_editar, novo_keyword, novos_meses)
                        st.success(f"Regra ID {id_para_editar} atualizada com sucesso!")
                        st.rerun()
                else:
                    st.warning("Nenhuma regra cadastrada para editar.")

    # ==========================
    # Import / Export
    # ==========================
    with tab_io:
        st.subheader("Importar / Exportar Dados")
        st.info("Para importar, o arquivo Excel deve conter as colunas: 'nome', 'universidade', 'data_admissao', 'data_ult_renovacao' (opcional), 'obs' (opcional).")

        arquivo = st.file_uploader("Importar de um arquivo Excel (.xlsx)", type=["xlsx"])
        if arquivo:
            df_import = pd.read_excel(arquivo)
            count = 0
            with st.spinner("Importando dados..."):
                for _, row in df_import.iterrows():
                    try:
                        nome = str(row.get("nome","")).strip()
                        universidade = str(row.get("universidade","")).strip()
                        data_adm = pd.to_datetime(row.get("data_admissao")).date()
                        data_renov = pd.to_datetime(row.get("data_ult_renovacao")).date() if pd.notna(row.get("data_ult_renovacao")) else None
                        obs = str(row.get("obs","")).strip()
                        
                        if nome and universidade and data_adm:
                            data_venc = calcular_vencimento(universidade, data_adm, data_renov)
                            if data_venc:
                                insert_estagiario(nome, universidade, data_adm, data_renov, obs, data_venc)
                                count += 1
                    except Exception as e:
                        st.warning(f"Erro ao importar a linha com nome '{nome}': {e}")
                        continue
            st.success(f"{count} estagiários importados com sucesso!")

        st.divider()
        
        df_export = list_estagiarios_df()
        st.download_button(
            "📥 Exportar Todos os Dados para Excel",
            exportar_para_excel_bytes(df_export),
            file_name="estagiarios_export_completo.xlsx"
        )


if __name__ == "__main__":
    main()
