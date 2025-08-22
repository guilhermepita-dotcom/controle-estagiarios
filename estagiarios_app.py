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
# Inicialização Streamlit e Conexão com DB
# ==========================
st.set_page_config(page_title="Controle de Estagiários", layout="wide")

# Conexão principal com o banco de dados persistente do Streamlit
conn = st.connection("estagiarios_db", type="sql")

# ==========================
# Funções de Banco de Dados (Adaptadas para st.connection)
# ==========================
def init_db():
    with conn.session as s:
        s.execute("""
            CREATE TABLE IF NOT EXISTS estagiarios (
                id INTEGER PRIMARY KEY, nome TEXT NOT NULL, universidade TEXT NOT NULL,
                data_admissao TEXT NOT NULL, data_ult_renovacao TEXT,
                obs TEXT, data_vencimento TEXT
            )
        """)
        s.execute("CREATE TABLE IF NOT EXISTS regras (id INTEGER PRIMARY KEY, keyword TEXT UNIQUE NOT NULL, meses INTEGER NOT NULL)")
        s.execute("CREATE TABLE IF NOT EXISTS config (key TEXT PRIMARY KEY, value TEXT)")
        for kw, meses in DEFAULT_REGRAS:
            s.execute("INSERT OR IGNORE INTO regras(keyword, meses) VALUES (:kw, :meses)", params=dict(kw=kw.upper(), meses=meses))
        s.execute("INSERT OR IGNORE INTO config(key, value) VALUES('proximos_dias', :dias)", params=dict(dias=str(DEFAULT_PROXIMOS_DIAS)))
        s.commit()

def get_config(key: str, default: Optional[str] = None) -> str:
    df = conn.query(f"SELECT value FROM config WHERE key='{key}'")
    return df.iloc[0]['value'] if not df.empty else (default if default is not None else "")

def set_config(key: str, value: str):
    with conn.session as s:
        s.execute(
            "INSERT INTO config(key, value) VALUES(:key, :value) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            params=dict(key=key, value=value)
        )
        s.commit()

def list_regras() -> pd.DataFrame:
    return conn.query("SELECT id, keyword, meses FROM regras ORDER BY keyword")

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
    df = conn.query("SELECT * FROM estagiarios")
    if df.empty:
        return df

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
    with conn.session as s:
        s.execute(
            "INSERT INTO estagiarios(nome, universidade, data_admissao, data_ult_renovacao, obs, data_vencimento) VALUES (:nome, :uni, :adm, :renov, :obs, :venc)",
            params=dict(nome=nome, uni=universidade, adm=str(data_adm), renov=str(data_renov) if data_renov else None, obs=obs, venc=str(data_venc) if data_venc else None)
        )
        s.commit()

def update_estagiario(est_id: int, nome: str, universidade: str, data_adm: date, data_renov: Optional[date], obs: str, data_venc: Optional[date]):
    with conn.session as s:
        s.execute(
            "UPDATE estagiarios SET nome=:nome, universidade=:uni, data_admissao=:adm, data_ult_renovacao=:renov, obs=:obs, data_vencimento=:venc WHERE id=:id",
            params=dict(nome=nome, uni=universidade, adm=str(data_adm), renov=str(data_renov) if data_renov else None, obs=obs, venc=str(data_venc) if data_venc else None, id=est_id)
        )
        s.commit()

def delete_estagiario(est_id: int):
    with conn.session as s:
        s.execute("DELETE FROM estagiarios WHERE id=:id", params=dict(id=est_id))
        s.commit()

def add_regra(keyword: str, meses: int):
    with conn.session as s:
        s.execute("INSERT OR IGNORE INTO regras(keyword, meses) VALUES (:kw, :meses)", params=dict(kw=keyword.upper().strip(), meses=meses))
        s.commit()

def update_regra(regra_id: int, keyword: str, meses: int):
    with conn.session as s:
        s.execute("UPDATE regras SET keyword=:kw, meses=:meses WHERE id=:id", params=dict(kw=keyword.upper().strip(), meses=meses, id=regra_id))
        s.commit()

# ==========================
# Funções de Lógica de Data e UI
# ==========================
def calcular_vencimento_final(data_adm: Optional[date]) -> Optional[date]:
    if not data_adm: return None
    return data_adm + relativedelta(months=24)

def classificar_status(data_venc: Optional[str], proximos_dias: int) -> str:
    if not data_venc or pd.isna(data_venc): return "SEM DATA"
    data_venc_obj = pd.to_datetime(data_venc, errors='coerce').date()
    if pd.isna(data_venc_obj): return "SEM DATA"
    
    delta = (data_venc_obj - date.today()).days
    if delta < 0: return "Vencido"
    if delta <= proximos_dias: return "Venc.Proximo"
    return "OK"

def calcular_proxima_renovacao(row: pd.Series) -> str:
    hoje = date.today()
    data_adm = pd.to_datetime(row['data_admissao'], errors='coerce').date()
    data_ult_renov = pd.to_datetime(row['data_ult_renovacao'], errors='coerce').date()
    
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
    
    admin_password = st.secrets.get("passwords", {}).get("admin")
    if not st.session_state.admin_logged_in:
        admin_pw_input = st.sidebar.text_input("Senha de Administrador", type="password", key="admin_pw_input")
        if st.sidebar.button("Entrar"):
            if admin_password and admin_pw_input == admin_password:
                st.session_state.admin_logged_in = True
                st.rerun()
            elif admin_pw_input:
                st.sidebar.error("Senha incorreta.")
    
    if st.session_state.admin_logged_in:
        st.sidebar.success("Acesso liberado!")
        if st.sidebar.button("Sair"):
            st.session_state.admin_logged_in = False
            st.rerun()
        
        st.sidebar.subheader("Backup do Banco de Dados")
        st.sidebar.info("Clique para baixar uma cópia completa do banco de dados.")
        try:
            db_path = conn.url.replace('sqlite:///', '')
            if os.path.exists(db_path):
                with open(db_path, "rb") as f:
                    db_bytes = f.read()
                st.sidebar.download_button(label="📥 Baixar Backup", data=db_bytes, file_name="backup_estagiarios.db", mime="application/octet-stream")
        except Exception as e:
            st.sidebar.error(f"Erro ao gerar backup: {e}")

    tab_dash, tab_cad, tab_regras, tab_io = st.tabs(["📊 Dashboard", "📝 Cadastro/Editar", "⚙️ Regras", "📥 Import/Export"])

    with tab_dash:
        df = list_estagiarios_df()
        if df.empty:
            st.info("Nenhum estagiário cadastrado ainda.")
        else:
            df["status"] = df["data_vencimento"].apply(lambda d: classificar_status(d, proximos_dias_input))
            df["proxima_renovacao"] = df.apply(calcular_proxima_renovacao, axis=1)
            
            total, ok, prox, venc = len(df), (df["status"] == "OK").sum(), (df["status"] == "Venc.Proximo").sum(), (df["status"] == "Vencido").sum()
            c1, c2, c3, c4 = st.columns(4)
            for col, titulo, valor in zip([c1, c2, c3, c4], ["👥Total", "✅OK", "⚠️Próximos", "⛔Vencidos"], [total, ok, prox, venc]):
                col.metric(titulo, valor)

            st.divider()
            st.subheader("Consulta Rápida de Estagiários")
            filtro_status = st.multiselect("Filtrar por status", options=["OK", "Venc.Proximo", "Vencido"], default=[])
            filtro_nome = st.text_input("🔎 Buscar por Nome do Estagiário")

            df_view = df.copy()
            if filtro_status: df_view = df_view[df_view["status"].isin(filtro_status)]
            if filtro_nome.strip(): df_view = df_view[df_view["nome"].str.contains(filtro_nome.strip(), case=False, na=False)]

            if df_view.empty:
                st.warning("Nenhum registro encontrado para os filtros selecionados.")
            else:
                colunas_ordenadas = ['id', 'nome', 'universidade', 'data_admissao', 'data_ult_renovacao', 'status', 'ultimo_ano', 'proxima_renovacao', 'data_vencimento', 'obs']
                df_view = df_view.reindex(columns=colunas_ordenadas)
                st.dataframe(
                    df_view,
                    column_config={ "nome": st.column_config.TextColumn(label="Nome", width="large"), "id": "ID", "universidade": "Universidade", "data_admissao": "Admissão", "data_ult_renovacao": "Últ. Renovação", "status": "Status", "ultimo_ano": "Último Ano?", "proxima_renovacao": "Próx. Renovação", "data_vencimento": "Venc. Final", "obs": "Observação" },
                    use_container_width=True, hide_index=True
                )
                st.download_button("📥 Exportar Resultado", exportar_para_excel_bytes(df_view), "estagiarios_filtrados.xlsx", key="download_dashboard")

    with tab_cad:
        st.subheader("Gerenciar Cadastro de Estagiário")
        
        if 'form_mode' not in st.session_state: st.session_state.form_mode = None
        if 'est_selecionado_id' not in st.session_state: st.session_state.est_selecionado_id = None
        if 'message' not in st.session_state: st.session_state.message = None
        if 'cadastro_universidade' not in st.session_state: st.session_state.cadastro_universidade = None
        
        if st.session_state.message:
            show_message(st.session_state.message)
            st.session_state.message = None
        
        c1, c2 = st.columns([1, 3])
        if c1.button("➕ Novo Cadastro"):
            st.session_state.form_mode = 'new'
            st.session_state.est_selecionado_id = None
            st.session_state.cadastro_universidade = None
            st.rerun()

        df_estagiarios = list_estagiarios_df()
        nomes_estagiarios = [""] + df_estagiarios["nome"].tolist()
        
        nome_atual = ""
        if st.session_state.est_selecionado_id:
            nome_filtrado = df_estagiarios[df_estagiarios['id'] == st.session_state.est_selecionado_id]
            if not nome_filtrado.empty: nome_atual = nome_filtrado.iloc[0]['nome']

        nome_selecionado = c2.selectbox("🔎 Buscar e Selecionar Estagiário para Editar", options=nomes_estagiarios, index=nomes_estagiarios.index(nome_atual) if nome_atual in nomes_estagiarios else 0)
        st.markdown("---")

        if nome_selecionado:
            id_novo = df_estagiarios[df_estagiarios["nome"] == nome_selecionado].iloc[0]['id']
            if st.session_state.est_selecionado_id != id_novo:
                st.session_state.est_selecionado_id, st.session_state.form_mode, st.session_state.cadastro_universidade = id_novo, 'edit', None
                st.rerun()
        elif st.session_state.est_selecionado_id is not None and not nome_selecionado:
             st.session_state.est_selecionado_id, st.session_state.form_mode, st.session_state.cadastro_universidade = None, None, None
             st.rerun()

        universidade_para_form = None
        if st.session_state.form_mode == 'edit':
             if st.session_state.est_selecionado_id and not df_estagiarios[df_estagiarios['id'] == st.session_state.est_selecionado_id].empty:
                 universidade_para_form = df_estagiarios[df_estagiarios['id'] == st.session_state.est_selecionado_id].iloc[0]['universidade']
        elif st.session_state.form_mode == 'new':
            st.subheader("Passo 1: Selecione a Universidade")
            uni_selecionada = st.selectbox("Universidade*", options=universidades_padrao, index=None, placeholder="Selecione a universidade...", key="uni_select_novo")
            
            if st.session_state.uni_select_novo:
                if st.session_state.uni_select_novo == "Outra (cadastrar manualmente)":
                    uni_outra = st.text_input("Digite o nome da Universidade*")
                    if st.button("Continuar"):
                        st.session_state.cadastro_universidade = uni_outra.strip().upper()
                        st.rerun()
                else:
                    st.session_state.cadastro_universidade = st.session_state.uni_select_novo
                    st.rerun()
            if st.session_state.cadastro_universidade:
                universidade_para_form = st.session_state.cadastro_universidade

        if universidade_para_form:
            est_selecionado = None
            if st.session_state.form_mode == 'edit' and st.session_state.est_selecionado_id:
                resultado = df_estagiarios[df_estagiarios['id'] == st.session_state.est_selecionado_id]
                if not resultado.empty: est_selecionado = resultado.iloc[0]

            nome_default = est_selecionado["nome"] if est_selecionado is not None else ""
            data_adm_default = pd.to_datetime(est_selecionado["data_admissao"], dayfirst=True, errors='coerce').date() if est_selecionado is not None else None
            data_renov_default = pd.to_datetime(est_selecionado["data_ult_renovacao"], dayfirst=True, errors='coerce').date() if est_selecionado is not None and "Contrato" not in str(est_selecionado["data_ult_renovacao"]) else None
            obs_default = est_selecionado["obs"] if est_selecionado is not None else ""
            
            with st.form("form_cadastro"):
                if st.session_state.form_mode == 'new': st.subheader(f"Passo 2: Detalhes ({universidade_para_form})")
                elif est_selecionado is not None: st.subheader(f"Editando: {nome_default} ({universidade_para_form})")
                
                nome = st.text_input("Nome*", value=nome_default)
                termo_meses = meses_por_universidade(universidade_para_form)
                
                c1_form, c2_form = st.columns(2)
                data_adm = c1_form.date_input("Data de Admissão*", value=data_adm_default)
                data_renov = c2_form.date_input("Data da Última Renovação", value=data_renov_default, disabled=(termo_meses >= 24))
                if termo_meses >= 24:
                    c2_form.info("Contrato único. Não requer renovação.")

                obs = st.text_area("Observações", value=obs_default, height=100)
                st.markdown("---")
                
                col1_form, col2_form, _, col4_form = st.columns(4)
                submit = col1_form.form_submit_button("💾 Salvar")
                delete = col2_form.form_submit_button("🗑️ Excluir", disabled=(st.session_state.form_mode == 'new'))
                cancelar = col4_form.form_submit_button("🧹 Cancelar")

                if submit:
                    if not nome.strip() or not universidade_para_form or not data_adm:
                        st.session_state.message = {'text': "Preencha todos os campos obrigatórios (*).", 'type': 'warning'}
                    else:
                        nome_upper, universidade_upper, obs_upper = nome.strip().upper(), universidade_para_form.strip().upper(), obs.strip().upper()
                        data_venc = calcular_vencimento_final(data_adm)
                        if st.session_state.form_mode == 'new':
                            insert_estagiario(nome_upper, universidade_upper, data_adm, data_renov, obs_upper, data_venc)
                            st.session_state.message = {'text': f"Estagiário {nome_upper} cadastrado!", 'type': 'success'}
                        elif est_selecionado is not None:
                            update_estagiario(est_selecionado["id"], nome_upper, universidade_upper, data_adm, data_renov, obs_upper, data_venc)
                            st.session_state.message = {'text': f"Estagiário {nome_upper} atualizado!", 'type': 'success'}
                        st.session_state.form_mode, st.session_state.est_selecionado_id, st.session_state.cadastro_universidade = None, None, None
                    st.rerun()

                if delete and est_selecionado is not None:
                    delete_estagiario(est_selecionado["id"])
                    st.session_state.message = {'text': f"🗑️ Estagiário {est_selecionado['nome']} excluído!", 'type': 'success'}
                    st.session_state.form_mode, st.session_state.est_selecionado_id, st.session_state.cadastro_universidade = None, None, None
                    st.rerun()

                if cancelar:
                    st.session_state.form_mode, st.session_state.est_selecionado_id, st.session_state.cadastro_universidade = None, None, None
                    st.rerun()
    
    with tab_regras:
        st.subheader("Regras de Duração do Contrato por Universidade")
        st.info("Define o tempo máximo de contrato para cada universidade (não pode exceder 24 meses).")
        df_regras = list_regras()
        st.dataframe(df_regras, use_container_width=True, hide_index=True)
        c1, c2 = st.columns(2)
        with c1:
            with st.form("form_regras"):
                st.subheader("Adicionar Nova Regra")
                keyword = st.text_input("🔎 Palavra-chave da Universidade").upper()
                meses = st.number_input("Meses de contrato", min_value=1, max_value=24, value=6, step=1)
                add_button = st.form_submit_button("Adicionar Regra")
                if add_button and keyword.strip():
                    add_regra(keyword, meses)
                    st.success(f"Regra '{keyword}' adicionada/atualizada!")
                    st.rerun()
        with c2:
            with st.form("form_editar_regra"):
                st.subheader("Editar Regra Existente")
                if not df_regras.empty:
                    id_para_editar = st.selectbox("Selecione o ID da regra para editar", options=df_regras['id'].tolist())
                    regra_selecionada = df_regras[df_regras['id'] == id_para_editar].iloc[0]
                    novo_keyword = st.text_input("Novo nome/palavra-chave", value=regra_selecionada['keyword']).upper()
                    novos_meses = st.number_input("Novos meses de contrato", min_value=1, max_value=24, value=int(regra_selecionada['meses']), step=1)
                    update_button = st.form_submit_button("Salvar Alterações")
                    if update_button and novo_keyword.strip():
                        update_regra(id_para_editar, novo_keyword, novos_meses)
                        st.success(f"Regra ID {id_para_editar} atualizada!")
                        st.rerun()
                else: st.warning("Nenhuma regra cadastrada para editar.")

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
            st.success(f"{count} estagiários importados com sucesso!")
        st.divider()
        df_export = list_estagiarios_df()
        st.download_button("📥 Exportar Todos os Dados para Excel", exportar_para_excel_bytes(df_export), "estagiarios_export_completo.xlsx")

if __name__ == "__main__":
    main()
        
