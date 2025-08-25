import os
from datetime import date, datetime
from typing import Optional, Dict, Any
import io
import unicodedata

import pandas as pd
import sqlite3
import streamlit as st
from dateutil.relativedelta import relativedelta
from streamlit_option_menu import option_menu
import pytz

# ==========================
# Configurações e Constantes
# ==========================

# ***** CAMINHO ABSOLUTO DEFINITIVO APLICADO *****
# O programa agora está forçado a usar este arquivo, eliminando qualquer confusão.
DB_FILE = "H:/GUILHERME PITA/6.EstagiariosApp/estagiarios.db"

LOGO_FILE = "logo.png"
DEFAULT_PROXIMOS_DIAS = 30
DEFAULT_DURATION_OTHERS = 6
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
                --primary-color: #E2A144; --background-color: #0F0F0F;
                --secondary-background-color: #212121; --text-color: #FFFFFF;
                --text-color-dark: #0F0F0F; --font-family: 'Poppins', sans-serif;
            }
            html, body, [class*="st-"], .st-emotion-cache-10trblm { font-family: var(--font-family); color: var(--text-color); }
            .main > div { background-color: var(--background-color); }
            h1, h2, h3 { color: var(--text-color) !important; font-weight: 600 !important;}
            .stButton > button { background-color: transparent; color: var(--primary-color); border-radius: 8px; border: 2px solid var(--primary-color); font-weight: 600; transition: all 0.2s ease-in-out; padding: 8px 16px; }
            .stButton > button:hover { background-color: var(--primary-color); color: #FFFFFF; }
            .stButton > button:focus { box-shadow: 0 0 0 2px var(--secondary-background-color), 0 0 0 4px var(--primary-color) !important; }
            [data-testid="stMetric"] { background-color: rgba(33, 33, 33, 0.3); border-radius: 10px; padding: 20px; border-left: 5px solid var(--primary-color); box-shadow: 0 4px 8px 0 rgba(0,0,0,0.2); }
            div[data-testid="stVerticalBlock"] > div[style*="flex-direction: column;"] > div[data-testid="stForm"] { background-color: var(--secondary-background-color); border-radius: 10px; padding: 25px; border: 1px solid #333; }
        </style>
    """, unsafe_allow_html=True)

# ==========================
# Banco de Dados (Arquitetura Robusta)
# ==========================
def get_db_connection():
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def execute_write_query(query: str, params: tuple = ()):
    try:
        with sqlite3.connect(DB_FILE, timeout=10) as conn:
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute(query, params)
            conn.commit()
    except Exception as e:
        st.error(f"Erro ao escrever no banco de dados: {e}")
        st.stop()


def init_db():
    execute_write_query("CREATE TABLE IF NOT EXISTS estagiarios (id INTEGER PRIMARY KEY, nome TEXT NOT NULL, universidade TEXT NOT NULL, data_admissao TEXT NOT NULL, data_ult_renovacao TEXT, obs TEXT, data_vencimento TEXT)")
    execute_write_query("CREATE TABLE IF NOT EXISTS regras (id INTEGER PRIMARY KEY, keyword TEXT UNIQUE NOT NULL, meses INTEGER NOT NULL)")
    execute_write_query("CREATE TABLE IF NOT EXISTS config (key TEXT PRIMARY KEY, value TEXT)")
    execute_write_query("CREATE TABLE IF NOT EXISTS logs (id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp TEXT NOT NULL, action TEXT NOT NULL, details TEXT)")
    
    conn = get_db_connection()
    try:
        config_check = conn.execute("SELECT value FROM config WHERE key='proximos_dias'").fetchone()
        if not config_check:
            execute_write_query("INSERT OR REPLACE INTO config(key, value) VALUES(?, ?)", ('proximos_dias', str(DEFAULT_PROXIMOS_DIAS)))
        
        config_check = conn.execute("SELECT value FROM config WHERE key='admin_password'").fetchone()
        if not config_check:
            execute_write_query("INSERT OR REPLACE INTO config(key, value) VALUES(?, ?)", ('admin_password', '123456'))
    finally:
        conn.close()

def get_config(key: str, default: Optional[str] = None) -> str:
    conn = get_db_connection()
    try:
        row = conn.execute("SELECT value FROM config WHERE key=?", (key,)).fetchone()
        return row['value'] if row else (default if default is not None else "")
    finally:
        conn.close()

def set_config(key: str, value: str):
    execute_write_query("INSERT OR REPLACE INTO config(key, value) VALUES(?, ?)", (key, value))

# ==========================
# Funções de Lógica e CRUD
# ==========================
def log_action(action: str, details: str = ""):
    timestamp = datetime.now(TIMEZONE).strftime("%Y-%m-%d %H:%M:%S")
    execute_write_query("INSERT INTO logs (timestamp, action, details) VALUES (?, ?, ?)", (timestamp, action, details))

def list_regras() -> pd.DataFrame:
    conn = get_db_connection()
    try:
        return pd.read_sql_query("SELECT id, keyword, meses FROM regras ORDER BY keyword", conn)
    finally:
        conn.close()

def add_regra(keyword: str, meses: int):
    execute_write_query("INSERT OR REPLACE INTO regras(keyword, meses) VALUES (?, ?)", (keyword.upper().strip(), meses))
    log_action("REGRA ADICIONADA/EDITADA", f"Universidade: {keyword}, Meses: {meses}")

def delete_regra(regra_id: int, keyword: str):
    execute_write_query("DELETE FROM regras WHERE id=?", (int(regra_id),))
    log_action("REGRA EXCLUÍDA", f"ID: {regra_id}, Universidade: {keyword}")

def get_estagiarios_df() -> pd.DataFrame:
    conn = get_db_connection()
    try:
        df = pd.read_sql_query("SELECT * FROM estagiarios", conn, index_col="id")
    except (pd.io.sql.DatabaseError, ValueError):
        return pd.DataFrame()
    finally:
        conn.close()

    if df.empty: return df
    for col in ['data_admissao', 'data_ult_renovacao', 'data_vencimento']:
        df[col] = pd.to_datetime(df[col], errors='coerce')
    df = df.sort_values(by='data_vencimento', ascending=True)
    df.reset_index(inplace=True)
    return df

def insert_estagiario(nome: str, universidade: str, data_adm: date, data_renov: Optional[date], obs: str, data_venc: Optional[date]):
    query = "INSERT INTO estagiarios(nome, universidade, data_admissao, data_ult_renovacao, obs, data_vencimento) VALUES (?, ?, ?, ?, ?, ?)"
    params = (
        nome, universidade, data_adm.isoformat(), 
        data_renov.isoformat() if data_renov else None, 
        obs, 
        data_venc.isoformat() if data_venc else None
    )
    execute_write_query(query, params)
    log_action("NOVO ESTAGIÁRIO", f"Nome: {nome}, Universidade: {universidade}")

def update_estagiario(est_id: int, nome: str, universidade: str, data_adm: date, data_renov: Optional[date], obs: str, data_venc: Optional[date]):
    query = "UPDATE estagiarios SET nome=?, universidade=?, data_admissao=?, data_ult_renovacao=?, obs=?, data_vencimento=? WHERE id=?"
    params = (
        nome, universidade, data_adm.isoformat(), 
        data_renov.isoformat() if data_renov else None, 
        obs, 
        data_venc.isoformat() if data_venc else None, 
        est_id
    )
    execute_write_query(query, params)
    log_action("ESTAGIÁRIO ATUALIZADO", f"ID: {est_id}, Nome: {nome}")

def delete_estagiario(est_id: int, nome: str):
    execute_write_query("DELETE FROM estagiarios WHERE id=?", (int(est_id),))
    log_action("ESTAGIÁRIO EXCLUÍDO", f"ID: {est_id}, Nome: {nome}")

def normalize_text(text: str) -> str:
    if not isinstance(text, str): return ""
    return "".join(c for c in unicodedata.normalize('NFD', text.lower()) if unicodedata.category(c) != 'Mn')

def meses_por_universidade(universidade: str) -> int:
    if not universidade: return DEFAULT_DURATION_OTHERS
    df_regras = list_regras()
    if df_regras.empty: return DEFAULT_DURATION_OTHERS
    regras_dict = {row["keyword"]: int(row["meses"]) for _, row in df_regras.iterrows()}
    return regras_dict.get(universidade.upper(), DEFAULT_DURATION_OTHERS)

def calcular_vencimento_final(data_adm: Optional[date]) -> Optional[date]:
    return data_adm + relativedelta(months=24) if data_adm else None

def calcular_proxima_renovacao(row: pd.Series) -> str:
    hoje = date.today()
    data_adm = row['data_admissao'].date() if pd.notna(row['data_admissao']) else None
    data_ult_renov = row.get('data_ult_renovacao', pd.NaT).date() if pd.notna(row.get('data_ult_renovacao')) else None
    if not data_adm: return ""
    termo_meses = meses_por_universidade(row['universidade'])
    if termo_meses >= 24: return "Contrato único"
    limite_2_anos = data_adm + relativedelta(months=24)
    if limite_2_anos < hoje: return "Contrato Encerrado"
    base_date = data_ult_renov if data_ult_renov else data_adm
    proxima_data_renovacao = base_date + relativedelta(months=6)
    if proxima_data_renovacao > limite_2_anos: return "Término do Contrato"
    if proxima_data_renovacao < hoje: return "Renovação Pendente"
    return proxima_data_renovacao.strftime("%d.%m.%Y")

def _determinar_status(row: pd.Series, proximos_dias: int) -> str:
    if row['proxima_renovacao'] == "Renovação Pendente": return "Vencido"
    data_alvo = pd.to_datetime(row['proxima_renovacao'], format='%d.%m.%Y', errors='coerce')
    if pd.isna(data_alvo): data_alvo = row['data_vencimento']
    if pd.isna(data_alvo): return "SEM DATA"
    delta = (data_alvo.date() - date.today()).days
    if delta < 0: return "Vencido"
    if delta <= proximos_dias: return "Venc.Proximo"
    return "OK"

def processar_df_para_exibicao(df: pd.DataFrame, proximos_dias: int) -> pd.DataFrame:
    if df.empty: return df
    df_proc = df.copy()
    df_proc['proxima_renovacao'] = df_proc.apply(calcular_proxima_renovacao, axis=1)
    df_proc['status'] = df_proc.apply(_determinar_status, axis=1, args=(proximos_dias,))
    df_proc["ultimo_ano"] = df_proc["data_vencimento"].dt.year.apply(lambda y: "SIM" if pd.notna(y) and y == date.today().year else "NÃO")
    regras_df = list_regras()
    if not regras_df.empty:
        regras_24m_keywords = [row['keyword'] for _, row in regras_df.iterrows() if row['meses'] >= 24]
        if regras_24m_keywords:
            df_proc['data_ult_renovacao_str'] = ''
            mask = (df_proc['universidade'].str.upper().isin(regras_24m_keywords)) & (df_proc['data_ult_renovacao'].isnull())
            df_proc.loc[mask, 'data_ult_renovacao_str'] = "Contrato único"
            df_proc['data_ult_renovacao_str'] = df_proc.apply(lambda row: row['data_ult_renovacao_str'] if row['data_ult_renovacao_str'] else row['data_ult_renovacao'].strftime('%d.%m.%Y') if pd.notna(row['data_ult_renovacao']) else '', axis=1)
    else:
        df_proc['data_ult_renovacao_str'] = df_proc['data_ult_renovacao'].apply(lambda x: x.strftime('%d.%m.%Y') if pd.notna(x) else '')
        
    for col in ["data_admissao", "data_vencimento"]:
        df_proc[col] = df_proc[col].dt.strftime('%d.%m.%Y').replace('NaT', '')
    df_proc = df_proc.rename(columns={'id': 'ID', 'nome': 'Nome', 'universidade': 'Universidade', 'data_admissao': 'Data Admissão', 'data_ult_renovacao_str': 'Renovado em:', 'status': 'Status', 'ultimo_ano': 'Ultimo Ano?', 'proxima_renovacao': 'Proxima Renovação', 'data_vencimento': 'Termino de Contrato', 'obs': 'Observação'})
    return df_proc

def list_logs_df(start_date: Optional[date] = None, end_date: Optional[date] = None) -> pd.DataFrame:
    conn = get_db_connection()
    try:
        query = "SELECT timestamp, action, details FROM logs ORDER BY id DESC LIMIT 50"
        params = ()
        if start_date and end_date:
            query = "SELECT timestamp, action, details FROM logs WHERE date(timestamp) BETWEEN ? AND ? ORDER BY id DESC LIMIT 50"
            params = (start_date.isoformat(), end_date.isoformat())
        return pd.read_sql_query(query, conn, params=params)
    finally:
        conn.close()

def exportar_logs_bytes(start_date: Optional[date] = None, end_date: Optional[date] = None) -> bytes:
    conn = get_db_connection()
    try:
        query = "SELECT timestamp, action, details FROM logs ORDER BY id ASC"
        params = ()
        if start_date and end_date:
            query = "SELECT timestamp, action, details FROM logs WHERE date(timestamp) BETWEEN ? AND ? ORDER BY id ASC"
            params = (start_date.isoformat(), end_date.isoformat())
        df = pd.read_sql_query(query, conn, params=params)
        return df.to_string(index=False).encode('utf-8')
    finally:
        conn.close()

def exportar_para_excel_bytes(df: pd.DataFrame) -> bytes:
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df_export = df.copy()
        df_export.to_excel(writer, index=False, sheet_name='Estagiarios')
    return output.getvalue()

def show_message(message: Dict[str, Any]):
    msg_type = message.get('type', 'info')
    text = message.get('text', 'Ação concluída.')
    # A correção está na linha abaixo
    icon_map = {'success': '✅', 'warning': '⚠️', 'error': '❌', 'info': 'ℹ️'}
    st.toast(text, icon=icon_map.get(msg_type, 'ℹ️'))

def page_dashboard():
    st.header("Dashboard de Contratos")
    proximos_dias_input = st.number_input(
        "'Venc. Próximo' (dias)", min_value=1, max_value=120, 
        value=int(get_config("proximos_dias", DEFAULT_PROXIMOS_DIAS)), step=1,
        help="Define o número de dias para um contrato ser considerado 'Próximo do Vencimento'."
    )
    if str(proximos_dias_input) != get_config("proximos_dias"):
        set_config("proximos_dias", str(proximos_dias_input))
    df_raw = get_estagiarios_df()
    if df_raw.empty:
        st.info("Nenhum estagiário cadastrado ainda.")
        return
    df_display = processar_df_para_exibicao(df_raw, proximos_dias_input)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("👥 Total de Estagiários", len(df_display))
    c2.metric("✅ Contratos OK", (df_display["Status"] == "OK").sum())
    c3.metric("⚠️ Vencimentos Próximos", (df_display["Status"] == "Venc.Proximo").sum())
    c4.metric("⛔ Contratos Vencidos", (df_display["Status"] == "Vencido").sum())
    st.divider()
    filtros_c1, filtros_c2 = st.columns(2)
    filtro_status = filtros_c1.multiselect("Filtrar por status", options=["OK", "Venc.Proximo", "Vencido"])
    filtro_nome = filtros_c2.text_input("🔎 Buscar por Nome do Estagiário")
    if filtro_status or filtro_nome.strip():
        df_view = df_display.copy()
        if filtro_status: df_view = df_view[df_view["Status"].isin(filtro_status)]
        if filtro_nome.strip(): df_view = df_view[df_view["Nome"].str.contains(filtro_nome.strip(), case=False, na=False)]
        if df_view.empty:
            st.warning("Nenhum registro encontrado para os filtros selecionados.")
        else:
            colunas_ordenadas = ['ID', 'Nome', 'Universidade', 'Data Admissão', 'Renovado em:', 'Status', 'Ultimo Ano?', 'Proxima Renovação', 'Termino de Contrato', 'Observação']
            st.dataframe(df_view[colunas_ordenadas], use_container_width=True, hide_index=True)
            df_export_raw = get_estagiarios_df()
            df_export_filtered = df_export_raw[df_export_raw['id'].isin(df_view['ID'])]
            st.download_button("📥 Exportar Resultado", exportar_para_excel_bytes(df_export_filtered), "estagiarios_filtrados.xlsx", key="download_dashboard")
    else:
        st.info("ℹ️ Utilize os filtros acima para pesquisar e exibir os dados dos estagiários.")

def page_cadastro():
    st.header("Gerenciar Estagiários")
    if 'sub_menu_cad' not in st.session_state: st.session_state.sub_menu_cad = None
    if 'message' in st.session_state and st.session_state.message:
        show_message(st.session_state.message)
        st.session_state.message = None
    cols = st.columns(2)
    if cols[0].button("➕ Novo Estagiário", use_container_width=True, key="btn_novo_estagiario"): 
        st.session_state.sub_menu_cad = "Novo"
        st.session_state.id_para_editar = None
        st.rerun()
    if cols[1].button("🔎 Consultar / Editar", use_container_width=True, key="btn_consultar_estagiario"): 
        st.session_state.sub_menu_cad = "Editar"
        st.session_state.id_para_editar = None
        st.rerun()
    st.divider()
    if st.session_state.sub_menu_cad == "Novo":
        st.subheader("Cadastrar Novo Estagiário")
        with st.form("form_novo", clear_on_submit=True):
            nome = st.text_input("Nome*").strip().upper()
            universidade_selecionada = st.selectbox("Universidade*", options=universidades_padrao, index=None, placeholder="Selecione uma universidade...")
            universidade = universidade_selecionada
            if universidade_selecionada == "Outra (cadastrar manualmente)":
                universidade = st.text_input("Digite o nome da Universidade*").strip().upper()
            
            c1, c2 = st.columns(2)
            data_adm = c1.date_input("Data de Admissão*", value=date.today())
            
            termo_meses = meses_por_universidade(universidade if universidade else "")
            renov_disabled = (termo_meses >= 24)
            data_renov = c2.date_input("Data da Última Renovação", value=None, disabled=renov_disabled)
            if renov_disabled: c2.info("Contrato único. Não requer renovação.")
            
            obs = st.text_area("Observações").strip().upper()
            
            submitted = st.form_submit_button("💾 Salvar Novo Estagiário", use_container_width=True)
            if submitted:
                if not nome or not universidade or not data_adm:
                    st.session_state.message = {'text': "Preencha todos os campos obrigatórios (*).", 'type': 'warning'}
                else:
                    data_venc = calcular_vencimento_final(data_adm)
                    insert_estagiario(nome, universidade, data_adm, data_renov if not renov_disabled else None, obs, data_venc)
                    st.session_state.message = {'text': f"Estagiário {nome} cadastrado!", 'type': 'success'}
                st.rerun()

        if st.button("Cancelar", use_container_width=True, key="btn_cancelar_novo"):
            st.session_state.sub_menu_cad = None
            st.rerun()

    if st.session_state.sub_menu_cad == "Editar":
        df_estagiarios = get_estagiarios_df()

        if 'id_para_editar' in st.session_state and st.session_state.id_para_editar:
            # Filtra o DataFrame para obter os dados do estagiário a ser editado
            est_data_list = df_estagiarios[df_estagiarios['id'] == st.session_state.id_para_editar]
            
            if est_data_list.empty:
                st.warning("Estagiário não encontrado. Retornando para a busca.")
                st.session_state.id_para_editar = None
                st.rerun()

            est_data_para_edicao = est_data_list.iloc[0]
            st.subheader(f"Editando: {est_data_para_edicao['nome']}")

            with st.form("form_edicao"):
                st.text_input("Nome*", value=est_data_para_edicao["nome"], key="nome_edit")
                
                uni_default = est_data_para_edicao.get("universidade")
                uni_index = universidades_padrao.index(uni_default) if uni_default in universidades_padrao else None
                st.selectbox("Universidade*", options=universidades_padrao, index=uni_index, key="universidade_select_edit")
                
                universidade_manual_default = uni_default if uni_default not in universidades_padrao else ""
                if 'universidade_select_edit' in st.session_state and st.session_state.universidade_select_edit == "Outra (cadastrar manualmente)":
                    st.text_input("Digite o nome da Universidade*", value=universidade_manual_default, key="universidade_manual_edit")
                
                termo_meses = meses_por_universidade(st.session_state.get("universidade_select_edit", ""))
                renov_disabled = (termo_meses >= 24)
                
                c1, c2 = st.columns(2)
                c1.date_input("Data de Admissão*", value=est_data_para_edicao["data_admissao"].date(), key="data_adm_edit")
                c2.date_input("Data da Última Renovação", value=None if pd.isna(est_data_para_edicao["data_ult_renovacao"]) else est_data_para_edicao["data_ult_renovacao"].date(), disabled=renov_disabled, key="data_renov_edit")
                if renov_disabled: c2.info("Contrato único. Não requer renovação.")
                
                st.text_area("Observações", value=est_data_para_edicao.get("obs", ""), key="obs_edit")
                
                submitted = st.form_submit_button("💾 Salvar Alterações", use_container_width=True)
                if submitted:
                    nome_novo = st.session_state.get('nome_edit')
                    uni_select = st.session_state.get('universidade_select_edit')
                    
                    if uni_select == "Outra (cadastrar manualmente)":
                        universidade_nova = st.session_state.get('universidade_manual_edit')
                    else:
                        universidade_nova = uni_select

                    data_adm_nova = st.session_state.get('data_adm_edit')

                    if not nome_novo or not universidade_nova or not data_adm_nova:
                        st.session_state.message = {'text': "VERIFICAÇÃO FALHOU: Um campo obrigatório está vazio.", 'type': 'error'}
                    else:
                        data_renov_nova = st.session_state.get('data_renov_edit')
                        obs_nova = st.session_state.get('obs_edit')
                        data_venc = calcular_vencimento_final(data_adm_nova)
                        
                        update_estagiario(
                            st.session_state.id_para_editar,
                            nome_novo.strip().upper(),
                            universidade_nova.strip().upper(),
                            data_adm_nova,
                            data_renov_nova if not renov_disabled else None,
                            obs_nova.strip().upper(),
                            data_venc
                        )
                        st.session_state.message = {'text': f"Dados de {nome_novo.strip().upper()} atualizados com sucesso!", 'type': 'success'}
                    
                    st.rerun()


            c_delete, c_cancel = st.columns(2)
            if c_delete.button("🗑️ Excluir Estagiário", use_container_width=True):
                st.session_state.confirm_delete_id = {'id': st.session_state.id_para_editar, 'nome': est_data_para_edicao["nome"]}
                st.rerun()

            if c_cancel.button("Voltar para a Busca", use_container_width=True):
                st.session_state.id_para_editar = None
                st.rerun()
            
            if 'confirm_delete_id' in st.session_state and st.session_state.confirm_delete_id:
                data_to_delete = st.session_state.confirm_delete_id
                st.warning(f"Tem certeza que deseja excluir **{data_to_delete['nome']}**? Esta ação não pode ser desfeita.")
                c1_del, c2_del, _ = st.columns([1, 1, 3])
                if c1_del.button("SIM, EXCLUIR", key="confirm_del_btn"):
                    delete_estagiario(data_to_delete['id'], data_to_delete['nome'])
                    st.session_state.message = {'text': 'Estagiário excluído com sucesso!', 'type': 'success'}
                    st.session_state.confirm_delete_id = None
                    st.session_state.id_para_editar = None
                    st.session_state.sub_menu_cad = "Editar"
                    st.rerun()
                if c2_del.button("NÃO, CANCELAR", key="cancel_del_btn"):
                    st.session_state.confirm_delete_id = None
                    st.rerun()
        else:
            if df_estagiarios.empty:
                st.info("Nenhum estagiário para editar.")
                return
            search_term = st.text_input("🔎 Digite o nome do estagiário para buscar", placeholder="Ex: João da Silva")
            if search_term.strip():
                normalized_search = normalize_text(search_term.strip())
                df_estagiarios['nome_normalizado'] = df_estagiarios['nome'].apply(normalize_text)
                df_results = df_estagiarios[df_estagiarios['nome_normalizado'].str.contains(normalized_search, na=False)].copy()
                df_results.reset_index(drop=True, inplace=True)
                if df_results.empty:
                    st.warning("Nenhum estagiário encontrado com esse nome.")
                elif len(df_results) == 1:
                    st.success(f"Estagiário encontrado: {df_results.iloc[0]['nome']}. Carregando formulário de edição...")
                    st.session_state.id_para_editar = df_results.iloc[0]['id']
                    st.rerun()
                else:
                    st.info(f"{len(df_results)} estagiários encontrados. Por favor, selecione um abaixo para editar.")
                    df_results['data_admissao_str'] = df_results['data_admissao'].dt.strftime('%d/%m/%Y')
                    df_display_cols = ['id', 'nome', 'universidade', 'data_admissao_str']
                    st.dataframe(df_results[df_display_cols], use_container_width=True, hide_index=True)
                    radio_options_map = {f"{row['nome']} (ID: {row['id']}, Admissão: {row['data_admissao_str']})": row['id'] for index, row in df_results.iterrows()}
                    selected_option = st.radio("Selecione o estagiário:", options=radio_options_map.keys(), key="radio_selecao_estagiario")
                    if st.button("Editar Selecionado", use_container_width=True):
                        st.session_state.id_para_editar = radio_options_map[selected_option]
                        st.rerun()
                        
def page_base():
    st.header("Base de Dados de Estagiários")
    st.info("Abaixo está a lista completa de todos os estagiários cadastrados no sistema.")
    df_raw = get_estagiarios_df()
    if df_raw.empty:
        st.warning("Nenhum estagiário cadastrado para exibir.")
        return
    proximos_dias_config = int(get_config("proximos_dias", DEFAULT_PROXIMOS_DIAS))
    df_display = processar_df_para_exibicao(df_raw, proximos_dias_config)
    colunas_ordenadas = ['ID', 'Nome', 'Universidade', 'Data Admissão', 'Renovado em:', 'Status', 'Ultimo Ano?', 'Proxima Renovação', 'Termino de Contrato', 'Observação']
    st.dataframe(df_display[colunas_ordenadas], use_container_width=True, hide_index=True)
    st.download_button("📥 Exportar Base Completa", exportar_para_excel_bytes(get_estagiarios_df()), "base_completa_estagiarios.xlsx", key="download_base")

def page_regras():
    st.header("Gerenciar Regras de Contrato")
    st.info("Defina o tempo máximo de contrato para cada universidade (não pode exceder 24 meses). Universidades sem regra específica usarão o padrão de 6 meses.")
    if 'message_rule' in st.session_state and st.session_state.message_rule:
        show_message(st.session_state.message_rule)
        st.session_state.message_rule = None
    if 'rule_to_delete' in st.session_state and st.session_state.rule_to_delete:
        rule = st.session_state.rule_to_delete
        st.warning(f"Tem certeza que deseja excluir a regra para **{rule['keyword']}**?")
        c1, c2, _ = st.columns([1, 1, 3])
        if c1.button("SIM, EXCLUIR REGRA"):
            delete_regra(rule['id'], rule['keyword'])
            st.session_state.message_rule = {'text': f"Regra para {rule['keyword']} excluída!", 'type': 'success'}
            st.session_state.rule_to_delete = None
            st.rerun()
        if c2.button("NÃO, CANCELAR"):
            st.session_state.rule_to_delete = None
            st.rerun()
    else:
        df_regras = list_regras()
        if df_regras.empty: st.info("Nenhuma regra personalizada cadastrada.")
        else: st.table(df_regras.rename(columns={"keyword": "Universidade", "meses": "Duração (Meses)"}))
        st.divider()
        c1, c2 = st.columns(2)
        with c1:
            with st.form("form_add_edit_regra"):
                st.subheader("Adicionar / Editar Regra")
                keyword_raw = st.selectbox("Universidade", options=universidades_padrao, index=None, placeholder="Selecione para adicionar ou editar...")
                if keyword_raw == "Outra (cadastrar manualmente)":
                    keyword_raw = st.text_input("Digite o Nome ou Palavra-chave da Universidade")
                meses = st.number_input("Meses de contrato", min_value=1, max_value=24, value=6, step=1)
                if st.form_submit_button("Salvar Regra", use_container_width=True) and keyword_raw:
                    add_regra(keyword_raw, meses)
                    st.session_state.message_rule = {'text': f"Regra para '{keyword_raw}' salva!", 'type': 'success'}
                    st.rerun()
        with c2:
            with st.form("form_delete_regra"):
                st.subheader("Excluir Regra")
                if not df_regras.empty:
                    opcoes = {f"{r['keyword']} ({r['meses']} meses)": {"id": r['id'], "keyword": r['keyword']} for _, r in df_regras.iterrows()}
                    regra_para_deletar_str = st.selectbox("Selecione a regra para excluir", options=opcoes.keys())
                    if st.form_submit_button("🗑️ Excluir Regra Selecionada", use_container_width=True):
                        st.session_state.rule_to_delete = opcoes[regra_para_deletar_str]
                        st.rerun()
                else:
                    st.selectbox("Selecione a regra para excluir", [], disabled=True)
                    st.form_submit_button("🗑️ Excluir Regra Selecionada", disabled=True, use_container_width=True)

def page_import_export():
    st.header("Importar e Exportar Dados")
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("📥 Exportar Todos os Dados")
        df_export = get_estagiarios_df()
        st.download_button(label="Baixar Planilha Completa (.xlsx)", data=exportar_para_excel_bytes(df_export), file_name="estagiarios_export_completo.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)
    with c2:
        st.subheader("📤 Importar de Arquivo Excel")
        st.info("Colunas obrigatórias: `nome`, `universidade`, `data_admissao`.")
        with st.form("form_import"):
            arquivo = st.file_uploader("Selecione o arquivo Excel (.xlsx)", type=["xlsx"])
            submitted = st.form_submit_button("Iniciar Importação", use_container_width=True)
            if submitted and arquivo:
                try:
                    df_import = pd.read_excel(arquivo)
                    required_cols = ['nome', 'universidade', 'data_admissao']
                    if not all(col in df_import.columns for col in required_cols):
                        st.error(f"O arquivo precisa ter as colunas obrigatórias: {', '.join(required_cols)}")
                    else:
                        count = 0
                        with st.spinner("Importando dados..."):
                            for _, row in df_import.iterrows():
                                try:
                                    nome = str(row["nome"]).strip().upper()
                                    universidade = str(row["universidade"]).strip().upper()
                                    data_adm = pd.to_datetime(row["data_admissao"]).date()
                                    if nome and universidade and data_adm:
                                        data_renov = pd.to_datetime(row.get("data_ult_renovacao")).date() if pd.notna(row.get("data_ult_renovacao")) else None
                                        obs = str(row.get("obs","")).strip().upper()
                                        data_venc = calcular_vencimento_final(data_adm)
                                        insert_estagiario(nome, universidade, data_adm, data_renov, obs, data_venc)
                                        count += 1
                                except Exception as e:
                                    st.warning(f"Erro ao importar a linha com nome '{row.get('nome', 'N/A')}': {e}")
                        st.success(f"{count} estagiários importados com sucesso!")
                except Exception as e:
                    st.error(f"Não foi possível ler o arquivo. Erro: {e}")
            elif submitted and not arquivo:
                st.warning("Por favor, selecione um arquivo para importar.")

def page_admin():
    st.header("🔑 Área Administrativa")
    if 'admin_logged_in' not in st.session_state: st.session_state.admin_logged_in = False
    admin_password = get_config("admin_password")
    if not st.session_state.admin_logged_in:
        with st.form("admin_login_form"):
            senha = st.text_input("Senha", type="password", label_visibility="collapsed", placeholder="Senha de Administrador")
            if st.form_submit_button("Entrar", use_container_width=True):
                if senha == admin_password:
                    st.session_state.admin_logged_in = True
                    st.rerun()
                else:
                    st.error("Senha incorreta.")
        return
    st.success("Acesso de administrador liberado!")
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Backup do Banco de Dados")
        if os.path.exists(DB_FILE):
            with open(DB_FILE, "rb") as f: db_bytes = f.read()
            st.download_button(label="📥 Baixar Backup (.db)", data=db_bytes, file_name="backup_estagiarios.db", use_container_width=True)
    with c2:
        st.subheader("Logs do Sistema")
        col_f1, col_f2 = st.columns(2)
        start_date = col_f1.date_input("Data Início", value=None)
        end_date = col_f2.date_input("Data Fim", value=date.today())
        logs_df = list_logs_df(start_date=start_date, end_date=end_date)
        if logs_df.empty: st.info("Nenhum log encontrado para o período selecionado.")
        else: st.dataframe(logs_df, use_container_width=True, hide_index=True)
        log_bytes = exportar_logs_bytes(start_date=start_date, end_date=end_date)
        st.download_button(label="📥 Baixar Log do Período", data=log_bytes, file_name=f"log_{start_date}_a_{end_date}.txt" if start_date and end_date else "log_periodo.txt", mime="text/plain", use_container_width=True)
    st.divider()
    if st.button("Sair da Área Admin", use_container_width=True):
        st.session_state.admin_logged_in = False
        st.rerun()

# ==========================
# Main App
# ==========================
def main():
    load_custom_css()
    init_db()
    c1, c2 = st.columns([1, 4], vertical_alignment="center")
    if os.path.exists(LOGO_FILE): c1.image(LOGO_FILE, width=150)
    with c2:
        selected = option_menu(
            menu_title=None,
            options=["Dashboard", "Base", "Cadastro", "Regras", "Import/Export", "Área Administrativa"],
            icons=['bar-chart-line-fill', 'database-fill', 'pencil-square', 'gear-fill', 'cloud-upload-fill', 'key-fill'],
            default_index=0, orientation="horizontal",
            styles={
                "container": {"padding": "0!important", "background-color": "transparent"},
                "nav-link": {"padding-bottom": "10px", "border-bottom": "3px solid transparent", "transition": "color 0.2s, border-bottom 0.2s"},
                "nav-link-selected": {"background-color": "transparent", "color": "var(--primary-color)", "border-bottom": "3px solid var(--primary-color)"},
            })
    st.divider()
    if 'main_selection' not in st.session_state or selected != st.session_state.main_selection:
        st.session_state.main_selection = selected
        keys_to_reset = ['sub_menu_cad', 'confirm_delete_id', 'rule_to_delete', 'id_para_editar', 'current_edit_id']
        for key in keys_to_reset:
            if key in st.session_state:
                st.session_state[key] = None
        st.rerun()
    page_mapper = {
        "Dashboard": page_dashboard, "Base": page_base, "Cadastro": page_cadastro,
        "Regras": page_regras, "Import/Export": page_import_export, "Área Administrativa": page_admin
    }
    if selected in page_mapper:
        page_mapper[selected]()

if __name__ == "__main__":
    main()