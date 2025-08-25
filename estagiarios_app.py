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
            /* Seu CSS completo aqui... (mantido como no original para brevidade) */
            @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;600;700&display=swap');
            :root {
                --primary-color: #E2A144; --background-color: #0F0F0F;
                --secondary-background-color: #212121; --text-color: #FFFFFF;
                --text-color-dark: #0F0F0F; --font-family: 'Poppins', sans-serif;
            }
            html, body, [class*="st-"], .st-emotion-cache-10trblm {
                font-family: var(--font-family); color: var(--text-color);
            }
            .main > div { background-color: var(--background-color); }
            h1, h2, h3 { color: var(--text-color) !important; font-weight: 600 !important;}
            .stButton > button {
                background-color: transparent; color: var(--primary-color);
                border-radius: 8px; border: 2px solid var(--primary-color);
                font-weight: 600; transition: all 0.2s ease-in-out; padding: 8px 16px;
            }
            .stButton > button:hover { background-color: var(--primary-color); color: #FFFFFF; }
            .stButton > button:focus { box-shadow: 0 0 0 2px var(--secondary-background-color), 0 0 0 4px var(--primary-color) !important; }
            [data-testid="stMetric"] {
                background-color: rgba(33, 33, 33, 0.3); border-radius: 10px;
                padding: 20px; border-left: 5px solid var(--primary-color);
                box-shadow: 0 4px 8px 0 rgba(0,0,0,0.2);
            }
            div[data-testid="stVerticalBlock"] > div[style*="flex-direction: column;"] > div[data-testid="stForm"] {
                background-color: var(--secondary-background-color); border-radius: 10px;
                padding: 25px; border: 1px solid #333;
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
            id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp TEXT NOT NULL,
            action TEXT NOT NULL, details TEXT
        )
    """)
    
    if not c.execute("SELECT 1 FROM config WHERE key='regras_iniciadas'").fetchone():
        for kw, meses in DEFAULT_REGRAS:
            c.execute("INSERT OR IGNORE INTO regras(keyword, meses) VALUES (?, ?)", (kw.upper(), meses))
        c.execute("INSERT INTO config(key, value) VALUES(?, ?)", ('regras_iniciadas', 'true'))

    c.execute("INSERT OR IGNORE INTO config(key, value) VALUES(?, ?)", ('proximos_dias', str(DEFAULT_PROXIMOS_DIAS)))
    c.execute("INSERT OR IGNORE INTO config(key, value) VALUES(?, ?)", ('admin_password', '123456'))
    conn.commit()

def get_config(key: str, default: Optional[str] = None) -> str:
    row = get_db_connection().execute("SELECT value FROM config WHERE key=?", (key,)).fetchone()
    return row['value'] if row else (default if default is not None else "")

def set_config(key: str, value: str):
    conn = get_db_connection()
    conn.execute("INSERT OR REPLACE INTO config(key, value) VALUES(?, ?)", (key, value))
    conn.commit()

# ==========================
# Funções de Lógica e CRUD
# ==========================
def normalize_text(text: str) -> str:
    """Converte string para minúsculas e remove acentos."""
    if not isinstance(text, str):
        return ""
    return "".join(c for c in unicodedata.normalize('NFD', text.lower()) if unicodedata.category(c) != 'Mn')

def log_action(action: str, details: str = ""):
    conn = get_db_connection()
    timestamp = datetime.now(TIMEZONE).strftime("%Y-%m-%d %H:%M:%S")
    conn.execute("INSERT INTO logs (timestamp, action, details) VALUES (?, ?, ?)", (timestamp, action, details))
    conn.commit()

def list_regras() -> pd.DataFrame:
    return pd.read_sql_query("SELECT id, keyword, meses FROM regras ORDER BY keyword", get_db_connection())

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

def get_estagiarios_df() -> pd.DataFrame:
    try:
        df = pd.read_sql_query("SELECT * FROM estagiarios", get_db_connection(), index_col="id")
    except (pd.io.sql.DatabaseError, ValueError):
        return pd.DataFrame()
    if df.empty:
        return df
    
    for col in ['data_admissao', 'data_ult_renovacao', 'data_vencimento']:
        df[col] = pd.to_datetime(df[col], errors='coerce')

    df = df.sort_values(by='data_vencimento', ascending=True)
    df.reset_index(inplace=True)
    return df

def insert_estagiario(nome: str, universidade: str, data_adm: date, data_renov: Optional[date], obs: str, data_venc: Optional[date]):
    conn = get_db_connection()
    conn.execute("INSERT INTO estagiarios(nome, universidade, data_admissao, data_ult_renovacao, obs, data_vencimento) VALUES (?, ?, ?, ?, ?, ?)",
                 (nome, universidade, str(data_adm), str(data_renov) if data_renov else None, obs, str(data_venc) if data_venc else None))
    conn.commit()
    log_action("NOVO ESTAGIÁRIO", f"Nome: {nome}, Universidade: {universidade}")

def update_estagiario(est_id: int, nome: str, universidade: str, data_adm: date, data_renov: Optional[date], obs: str, data_venc: Optional[date]):
    conn = get_db_connection()
    conn.execute("UPDATE estagiarios SET nome=?, universidade=?, data_admissao=?, data_ult_renovacao=?, obs=?, data_vencimento=? WHERE id=?",
                 (nome, universidade, str(data_adm), str(data_renov) if data_renov else None, obs, str(data_venc) if data_venc else None, est_id))
    conn.commit()
    log_action("ESTAGIÁRIO ATUALIZADO", f"ID: {est_id}, Nome: {nome}")

def delete_estagiario(est_id: int, nome: str):
    conn = get_db_connection()
    conn.execute("DELETE FROM estagiarios WHERE id=?", (int(est_id),))
    conn.commit()
    log_action("ESTAGIÁRIO EXCLUÍDO", f"ID: {est_id}, Nome: {nome}")

def meses_por_universidade(universidade: str) -> int:
    if not universidade: return DEFAULT_DURATION_OTHERS
    df_regras = list_regras()
    regras_dict = {row["keyword"]: int(row["meses"]) for _, row in df_regras.iterrows()}
    return regras_dict.get(universidade.upper(), DEFAULT_DURATION_OTHERS)

def calcular_vencimento_final(data_adm: Optional[date]) -> Optional[date]:
    return data_adm + relativedelta(months=24) if data_adm else None

def classificar_status(data_venc: Optional[datetime], proximos_dias: int) -> str:
    if pd.isna(data_venc): return "SEM DATA"
    delta = (data_venc.date() - date.today()).days
    if delta < 0: return "Vencido"
    if delta <= proximos_dias: return "Venc.Proximo"
    return "OK"

def calcular_proxima_renovacao(row: pd.Series) -> str:
    hoje = date.today()
    data_adm = row['data_admissao'].date() if pd.notna(row['data_admissao']) else None
    data_ult_renov = row.get('data_ult_renovacao', pd.NaT).date() if pd.notna(row.get('data_ult_renovacao')) else None
    
    if not data_adm: return ""

    termo_meses = meses_por_universidade(row['universidade'])
    if termo_meses >= 24: return ""
    
    limite_2_anos = data_adm + relativedelta(months=24)
    if limite_2_anos < hoje: return "Contrato Encerrado"
    
    base_date = data_ult_renov if data_ult_renov else data_adm
    proxima_data_renovacao = base_date + relativedelta(months=6)

    if proxima_data_renovacao > limite_2_anos: return "Término do Contrato"
    if proxima_data_renovacao < hoje: return "Renovação Pendente"
    return proxima_data_renovacao.strftime("%d.%m.%Y")

def list_logs_df(start_date: Optional[date] = None, end_date: Optional[date] = None) -> pd.DataFrame:
    query = "SELECT timestamp, action, details FROM logs"
    params = {}
    if start_date and end_date:
        query += " WHERE date(timestamp) BETWEEN :start_date AND :end_date"
        params = {'start_date': str(start_date), 'end_date': str(end_date)}
    query += " ORDER BY id DESC LIMIT 50"
    return pd.read_sql_query(query, get_db_connection(), params=params)

def exportar_logs_bytes(start_date: Optional[date] = None, end_date: Optional[date] = None) -> bytes:
    query = "SELECT timestamp, action, details FROM logs"
    params = {}
    if start_date and end_date:
        query += " WHERE date(timestamp) BETWEEN :start_date AND :end_date"
        params = {'start_date': str(start_date), 'end_date': str(end_date)}
    query += " ORDER BY id ASC"
    df = pd.read_sql_query(query, get_db_connection(), params=params)
    return df.to_string(index=False).encode('utf-8')

def exportar_para_excel_bytes(df: pd.DataFrame) -> bytes:
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df_export = df.copy()
        for col in ["data_admissao", "data_ult_renovacao", "data_vencimento"]:
            if col in df_export.columns:
                 df_export[col] = pd.to_datetime(df_export[col]).dt.date
        df_export.to_excel(writer, index=False, sheet_name='Estagiarios')
    return output.getvalue()

def show_message(message: Dict[str, Any]):
    msg_type = message.get('type', 'info')
    text = message.get('text', 'Ação concluída.')
    icon_map = {'success': '✅', 'warning': '⚠️', 'error': '❌', 'info': 'ℹ️'}
    st.toast(text, icon=icon_map.get(msg_type, 'ℹ️'))

# ===============================================
# SEÇÕES DA APLICAÇÃO (PÁGINAS)
# ===============================================

def page_dashboard():
    st.header("Dashboard de Contratos")
    
    proximos_dias_input = st.number_input(
        "'Venc. Próximo' (dias)", min_value=1, max_value=120, 
        value=int(get_config("proximos_dias", DEFAULT_PROXIMOS_DIAS)), step=1,
        help="Define o número de dias para um contrato ser considerado 'Próximo do Vencimento'."
    )
    if str(proximos_dias_input) != get_config("proximos_dias"):
        set_config("proximos_dias", str(proximos_dias_input))

    df = get_estagiarios_df()

    if df.empty:
        st.info("Nenhum estagiário cadastrado ainda.")
        return

    df["status"] = df["data_vencimento"].apply(lambda d: classificar_status(d, proximos_dias_input))
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("👥 Total de Estagiários", len(df))
    c2.metric("✅ Contratos OK", (df["status"] == "OK").sum())
    c3.metric("⚠️ Vencimentos Próximos", (df["status"] == "Venc.Proximo").sum())
    c4.metric("⛔ Contratos Vencidos", (df["status"] == "Vencido").sum())
    st.divider()

    filtros_c1, filtros_c2 = st.columns(2)
    filtro_status = filtros_c1.multiselect("Filtrar por status", options=["OK", "Venc.Proximo", "Vencido"])
    filtro_nome = filtros_c2.text_input("🔎 Buscar por Nome do Estagiário")

    if filtro_status or filtro_nome.strip():
        df_view = df.copy()
        if filtro_status: df_view = df_view[df_view["status"].isin(filtro_status)]
        if filtro_nome.strip(): df_view = df_view[df_view["nome"].str.contains(filtro_nome.strip(), case=False, na=False)]

        if df_view.empty:
            st.warning("Nenhum registro encontrado para os filtros selecionados.")
        else:
            df_display = df_view.copy()
            df_display["proxima_renovacao"] = df_display.apply(calcular_proxima_renovacao, axis=1)
            df_display["ultimo_ano"] = df_display["data_vencimento"].dt.year.apply(lambda y: "SIM" if pd.notna(y) and y == date.today().year else "NÃO")
            
            regras_df = list_regras()
            regras_24m_keywords = [row['keyword'] for _, row in regras_df.iterrows() if row['meses'] >= 24]
            df_display['data_ult_renovacao_str'] = ''
            if regras_24m_keywords:
                mask = (df_display['universidade'].str.upper().isin(regras_24m_keywords)) & (df_display['data_ult_renovacao'].isnull())
                df_display.loc[mask, 'data_ult_renovacao_str'] = "Contrato Único"
            
            for col in ["data_admissao", "data_vencimento"]:
                df_display[col] = df_display[col].dt.strftime('%d.%m.%Y').replace('NaT', '')
            
            df_display['data_ult_renovacao_str'] = df_display.apply(
                lambda row: row['data_ult_renovacao_str'] if row['data_ult_renovacao_str'] else
                            row['data_ult_renovacao'].strftime('%d.%m.%Y') if pd.notna(row['data_ult_renovacao']) else '',
                axis=1
            )

            df_display = df_display.rename(columns={
                'id': 'ID', 'nome': 'Nome', 'universidade': 'Universidade',
                'data_admissao': 'Data Admissão', 'data_ult_renovacao_str': 'Renovado em:',
                'status': 'Status', 'ultimo_ano': 'Ultimo Ano?',
                'proxima_renovacao': 'Proxima Renovação', 'data_vencimento': 'Termino de Contrato', 'obs': 'Observação'
            })
            
            colunas_ordenadas = ['ID', 'Nome', 'Universidade', 'Data Admissão', 'Renovado em:', 'Status', 'Ultimo Ano?', 'Proxima Renovação', 'Termino de Contrato', 'Observação']
            st.dataframe(df_display[colunas_ordenadas], use_container_width=True, hide_index=True)
            
            st.download_button("📥 Exportar Resultado", exportar_para_excel_bytes(df_view), "estagiarios_filtrados.xlsx", key="download_dashboard")
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
        
        nome = st.text_input("Nome*", key="novo_nome").strip().upper()
        
        universidade_selecionada = st.selectbox("Universidade*", options=universidades_padrao, index=None, placeholder="Selecione uma universidade...", key="novo_uni")
        universidade = universidade_selecionada
        if universidade_selecionada == "Outra (cadastrar manualmente)":
            universidade = st.text_input("Digite o nome da Universidade*", key="novo_uni_manual").strip().upper()

        c1, c2 = st.columns(2)
        data_adm = c1.date_input("Data de Admissão*", key="novo_data_adm")
        
        termo_meses = meses_por_universidade(universidade if universidade else "")
        renov_disabled = (termo_meses >= 24)
        
        data_renov = c2.date_input("Data da Última Renovação", value=None, disabled=renov_disabled, key="novo_data_renov")
        if renov_disabled: c2.info("Contrato único. Não requer renovação.")
        
        obs = st.text_area("Observações", key="novo_obs").strip().upper()
        
        c_submit, c_cancel = st.columns(2)
        if c_submit.button("💾 Salvar Novo Estagiário", use_container_width=True, key="btn_salvar_novo"):
            if not nome or not universidade or not data_adm:
                st.session_state.message = {'text': "Preencha todos os campos obrigatórios (*).", 'type': 'warning'}
            else:
                data_venc = calcular_vencimento_final(data_adm)
                insert_estagiario(nome, universidade, data_adm, data_renov if not renov_disabled else None, obs, data_venc)
                st.session_state.message = {'text': f"Estagiário {nome} cadastrado!", 'type': 'success'}
                st.session_state.sub_menu_cad = None
            st.rerun()
            
        if c_cancel.button("Cancelar", use_container_width=True, key="btn_cancelar_novo"):
            st.session_state.sub_menu_cad = None
            st.rerun()

    # <<< ALTERAÇÃO AQUI: Lógica de busca e edição com estado explícito >>>
    if st.session_state.sub_menu_cad == "Editar":
        df_estagiarios = get_estagiarios_df()

        # Se um estagiário já foi selecionado para edição, mostra o formulário
        if 'id_para_editar' in st.session_state and st.session_state.id_para_editar:
            est_data_para_edicao = df_estagiarios[df_estagiarios['id'] == st.session_state.id_para_editar].iloc[0]
            
            st.subheader(f"Editando: {est_data_para_edicao['nome']}")
            with st.form("form_edit_cadastro"):
                nome = st.text_input("Nome*", value=est_data_para_edicao["nome"]).strip().upper()
                
                uni_default = est_data_para_edicao.get("universidade")
                uni_index = universidades_padrao.index(uni_default) if uni_default in universidades_padrao else None
                universidade = st.selectbox("Universidade*", options=universidades_padrao, index=uni_index)
                if universidade == "Outra (cadastrar manualmente)":
                    universidade = st.text_input("Digite o nome da Universidade*", value=uni_default if uni_default not in universidades_padrao else "").strip().upper()

                termo_meses = meses_por_universidade(universidade if universidade else "")
                renov_disabled = (termo_meses >= 24)
                
                c1, c2 = st.columns(2)
                data_adm = c1.date_input("Data de Admissão*", value=est_data_para_edicao["data_admissao"])
                
                valor_data_renov = est_data_para_edicao["data_ult_renovacao"]
                if pd.isna(valor_data_renov): valor_data_renov = None

                data_renov = c2.date_input("Data da Última Renovação", value=valor_data_renov, disabled=renov_disabled)
                if renov_disabled: c2.info("Contrato único. Não requer renovação.")
                
                obs = st.text_area("Observações", value=est_data_para_edicao.get("obs", "")).strip().upper()
                
                c_save, c_delete, c_cancel = st.columns([2, 2, 1])
                if c_save.form_submit_button("💾 Salvar Alterações", use_container_width=True):
                    if not nome or not universidade or not data_adm:
                        st.session_state.message = {'text': "Preencha todos os campos obrigatórios (*).", 'type': 'warning'}
                    else:
                        data_venc = calcular_vencimento_final(data_adm)
                        update_estagiario(st.session_state.id_para_editar, nome, universidade, data_adm, data_renov if not renov_disabled else None, obs, data_venc)
                        st.session_state.message = {'text': f"Dados de {nome} atualizados!", 'type': 'success'}
                        st.session_state.sub_menu_cad = None
                        st.session_state.id_para_editar = None
                    st.rerun()

                if c_delete.form_submit_button("🗑️ Excluir Estagiário", use_container_width=True):
                    st.session_state.confirm_delete_id = {'id': st.session_state.id_para_editar, 'nome': nome}
                    st.rerun()

                if c_cancel.form_submit_button("Cancelar Edição", use_container_width=True):
                    st.session_state.id_para_editar = None
                    st.rerun()
            
            # Lógica de confirmação de exclusão
            if 'confirm_delete_id' in st.session_state and st.session_state.confirm_delete_id:
                data_to_delete = st.session_state.confirm_delete_id
                st.warning(f"Tem certeza que deseja excluir **{data_to_delete['nome']}**? Esta ação não pode ser desfeita.")
                c1, c2, _ = st.columns([1, 1, 3])
                if c1.button("SIM, EXCLUIR", key="confirm_del_btn"):
                    delete_estagiario(data_to_delete['id'], data_to_delete['nome'])
                    st.session_state.message = {'text': 'Estagiário excluído com sucesso!', 'type': 'success'}
                    st.session_state.confirm_delete_id = None
                    st.session_state.id_para_editar = None
                    st.session_state.sub_menu_cad = None
                    st.rerun()
                if c2.button("NÃO, CANCELAR", key="cancel_del_btn"):
                    st.session_state.confirm_delete_id = None
                    st.rerun()
        
        # Se nenhum estagiário estiver selecionado, mostra a interface de busca
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
                    st.info(f"{len(df_results)} estagiários encontrados. Por favor, selecione um da tabela abaixo para editar.")
                    df_results['data_admissao_str'] = df_results['data_admissao'].dt.strftime('%d/%m/%Y')
                    df_results['data_vencimento_str'] = df_results['data_vencimento'].dt.strftime('%d/%m/%Y')
                    
                    st.data_editor(
                        df_results[['id', 'nome', 'universidade', 'data_admissao_str', 'data_vencimento_str']], 
                        use_container_width=True, 
                        hide_index=True,
                        key="editor_selecao",
                        disabled=df_results.columns
                    )

                    if ('editor_selecao' in st.session_state and 
                        'selection' in st.session_state.editor_selecao and 
                        st.session_state.editor_selecao['selection']['rows']):
                        selected_row_index = st.session_state.editor_selecao["selection"]["rows"][0]
                        st.session_state.id_para_editar = df_results.iloc[selected_row_index]['id']
                        st.rerun()


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
        if df_regras.empty:
            st.info("Nenhuma regra personalizada cadastrada.")
        else:
            st.table(df_regras.rename(columns={"keyword": "Universidade", "meses": "Duração (Meses)"}))
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
        st.download_button(
            label="Baixar Planilha Completa (.xlsx)",
            data=exportar_para_excel_bytes(df_export),
            file_name="estagiarios_export_completo.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )

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
        if logs_df.empty:
            st.info("Nenhum log encontrado para o período selecionado.")
        else:
            st.dataframe(logs_df, use_container_width=True, hide_index=True)
        
        log_bytes = exportar_logs_bytes(start_date=start_date, end_date=end_date)
        st.download_button(
            label="📥 Baixar Log do Período", data=log_bytes,
            file_name=f"log_{start_date}_a_{end_date}.txt" if start_date and end_date else "log_periodo.txt",
            mime="text/plain", use_container_width=True
        )

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
            options=["Dashboard", "Cadastro", "Regras", "Import/Export", "Área Administrativa"],
            icons=['bar-chart-line-fill', 'pencil-square', 'gear-fill', 'cloud-upload-fill', 'key-fill'],
            default_index=0, orientation="horizontal",
            styles={
                "container": {"padding": "0!important", "background-color": "transparent"},
                "nav-link": {
                    "padding-bottom": "10px",
                    "border-bottom": "3px solid transparent",
                    "transition": "color 0.2s, border-bottom 0.2s",
                },
                "nav-link-selected": {
                    "background-color": "transparent",
                    "color": "var(--primary-color)",
                    "border-bottom": "3px solid var(--primary-color)",
                },
            }
        )
    st.divider()
    
    if 'main_selection' not in st.session_state or selected != st.session_state.main_selection:
        st.session_state.main_selection = selected
        keys_to_reset = ['sub_menu_cad', 'confirm_delete_id', 'rule_to_delete', 'id_para_editar']
        for key in keys_to_reset:
            if key in st.session_state:
                st.session_state[key] = None
        st.rerun()

    page_mapper = {
        "Dashboard": page_dashboard,
        "Cadastro": page_cadastro,
        "Regras": page_regras,
        "Import/Export": page_import_export,
        "Área Administrativa": page_admin
    }
    
    if selected in page_mapper:
        page_mapper[selected]()

if __name__ == "__main__":
    main()
