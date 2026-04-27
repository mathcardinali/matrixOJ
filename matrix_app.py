import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import date
import msal
import requests
from io import BytesIO
import base64
import urllib.parse as urlparse
import os

# ==========================================
# 1. CONFIGURAÇÕES E PERSISTÊNCIA
# ==========================================
st.set_page_config(page_title="Automotive MI & Launches", page_icon="🚗", layout="wide")

CACHE_FILE = "token_cache.bin"
EMAIL_DONO_ONEDRIVE = "matheus.cardinali@hotmail.com" 

# ==========================================
# 2. SISTEMA DE LOGIN
# ==========================================
def check_login():
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    if not st.session_state.authenticated:
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.markdown("<br><br><br>", unsafe_allow_html=True)
            st.subheader("🔒 Login - Market Intelligence")
            with st.form("login_form"):
                input_user = st.text_input("Usuário")
                input_pass = st.text_input("Senha", type="password")
                if st.form_submit_button("Entrar", use_container_width=True):
                    if "auth" in st.secrets and input_user == st.secrets["auth"]["username"] and input_pass == st.secrets["auth"]["password"]:
                        st.session_state.authenticated = True
                        st.rerun()
                    else:
                        st.error("Credenciais incorretas.")
        return False
    return True

if not check_login():
    st.stop()

# ==========================================
# 3. GESTÃO DE TOKEN (MSAL CACHE)
# ==========================================
def load_token_cache():
    cache = msal.SerializableTokenCache()
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "r") as f:
            cache.deserialize(f.read())
    return cache

def save_token_cache(cache):
    if cache.has_state_changed:
        with open(CACHE_FILE, "w") as f:
            f.write(cache.serialize())

def get_access_token():
    conf = st.secrets["azure"]
    scopes = ["Files.ReadWrite.All"]
    cache = load_token_cache()
    app = msal.ConfidentialClientApplication(
        conf["client_id"],
        authority="https://login.microsoftonline.com/consumers",
        client_credential=conf["client_secret"],
        token_cache=cache
    )
    accounts = app.get_accounts()
    if accounts:
        result = app.acquire_token_silent(scopes, account=accounts[0])
        if result: return result['access_token']
    
    auth_url = app.get_authorization_request_url(scopes, redirect_uri=conf["redirect_uri"])
    st.warning("🔒 Autorização Necessária")
    st.markdown(f"[Clique aqui para autorizar]({auth_url})")
    res_url = st.text_input("Cole a URL de retorno:")
    if res_url:
        try:
            query = urlparse.urlparse(res_url).query
            params = urlparse.parse_qs(query)
            code = params.get('code', [None])[0] or res_url.strip()
            result = app.acquire_token_by_authorization_code(code, scopes=scopes, redirect_uri=conf["redirect_uri"])
            if "access_token" in result:
                save_token_cache(cache)
                st.rerun()
        except: st.error("Link inválido.")
    return None

# ==========================================
# 4. PROCESSAMENTO DE DADOS E LOGOS
# ==========================================
@st.cache_data(ttl=3600)
def get_base64_image(url):
    try:
        resp = requests.get(url, timeout=5)
        if resp.status_code == 200:
            return "data:image/png;base64," + base64.b64encode(resp.content).decode()
    except: return None

@st.cache_data(ttl=60)
def load_data(token):
    url = "https://graph.microsoft.com/v1.0/me/drive/root:/Base_MI.xlsx:/content"
    headers = {'Authorization': f'Bearer {token}'}
    resp = requests.get(url, headers=headers)
    if resp.status_code == 200:
        try:
            df = pd.read_excel(BytesIO(resp.content), sheet_name="Launches")
            df['Brand'] = df['Brand'].fillna('').astype(str).str.upper()
            df['Name'] = df['Name'].fillna('').astype(str)
            # Label em duas linhas para o centro da bolinha
            df['Label'] = "<b>" + df['Brand'] + "</b><br>" + df['Name']
            
            df['Launch Date'] = pd.to_datetime(df['Launch Date'], format='%d/%m/%Y', errors='coerce')
            df['Month_Year'] = df['Launch Date'].dt.strftime('%m/%Y')
            df['Quarter'] = df['Launch Date'].dt.to_period('Q').astype(str)
            df['Price'] = pd.to_numeric(df['Price'], errors='coerce').fillna(0)
            df['Type of info'] = df['Type of info'].fillna('Speculation').astype(str)
            return df
        except Exception as e:
            st.error(f"Erro ao processar dados: {e}")
            return pd.DataFrame()
    return pd.DataFrame()

def save_data(df, token):
    output = BytesIO()
    df_save = df.copy()
    cols = [c for c in df_save.columns if c not in ['Month_Year', 'Quarter', 'Label']]
    df_to_xlsx = df_save[cols]
    df_to_xlsx['Launch Date'] = pd.to_datetime(df_to_xlsx['Launch Date']).dt.strftime('%d/%m/%Y')
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df_to_xlsx.to_excel(writer, sheet_name="Launches", index=False)
    url = "https://graph.microsoft.com/v1.0/me/drive/root:/Base_MI.xlsx:/content"
    headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'}
    resp = requests.put(url, headers=headers, data=output.getvalue())
    if resp.status_code in [200, 201]:
        st.success("Sincronizado!")
        st.cache_data.clear()
        return True
    return False

# ==========================================
# 5. EXECUÇÃO E INTERFACE
# ==========================================
token_atual = get_access_token()
if not token_atual: st.stop()

df = load_data(token_atual)

if not df.empty:
    with st.sidebar:
        st.header("Configurações de Visão")
        view_mode = st.radio("Agrupamento Temporal", ["Mês", "Trimestre (Quarter)"], horizontal=True)
        
        st.divider()
        st.header("Filtros")
        
        all_months = sorted(df['Month_Year'].dropna().unique(), key=lambda x: pd.to_datetime(x, format='%m/%Y'))
        default_period = [m for m in all_months if "2026" in m]
        mo_sel = st.multiselect("Janela de Lançamento", all_months, default=default_period)
        
        m_sel = st.multiselect("Brand", sorted(df['Brand'].unique()), default=df['Brand'].unique())
        t_sel = st.multiselect("Category (Type)", sorted(df['Type'].unique()), default=df['Type'].unique())
        
        min_p, max_p = float(df['Price'].min()), float(df['Price'].max())
        p_sel = st.slider("Faixa de Preço (R$)", min_p, max_p, (min_p, max_p))

        df_f = df[
            (df['Brand'].isin(m_sel)) & (df['Type'].isin(t_sel)) & 
            (df['Month_Year'].isin(mo_sel)) & (df['Price'] >= p_sel[0]) & (df['Price'] <= p_sel[1])
        ]

    tab1, tab2 = st.tabs(["📊 Matriz Competitiva", "➕ Cadastrar Veículo"])

    with tab1:
        c1, c2 = st.columns(2)
        y_axis_label = 'Month_Year' if view_mode == "Mês" else 'Quarter'
        
        # --- AJUSTE DE EIXOS PADRÃO SOLICITADO ---
        e_x = c1.selectbox("Eixo X", ['Lenght', 'Width', 'Height', 'Price', 'Launch Date'], index=4) # Index 4 = Launch Date
        e_y = c2.selectbox("Eixo Y", [y_axis_label, 'Price', 'Lenght', 'Width', 'Height'], index=1) # Index 1 = Price

        fig = px.scatter(df_f, x=e_x, y=e_y, 
                         color='Type of info', 
                         text='Label', 
                         color_discrete_map={'Official': '#1B5E20', 'Speculation': '#B71C1C'}, # Tons mais escuros para contraste
                         hover_data=['Powertrain', 'Price', 'Month_Year'])
        
        def get_scale(series):
            if pd.api.types.is_numeric_dtype(series):
                return (series.max() - series.min()) * 0.16 if len(series)>1 else 100
            return 30*24*60*60*1000*3.5

        if not df_f.empty:
            tx, ty = get_scale(df_f[e_x]), get_scale(df_f[e_y])

            logos_marcas = {
                'BYD': 'https://upload.wikimedia.org/wikipedia/commons/thumb/f/f6/BYD_Auto_2022_logo.svg/512px-BYD_Auto_2022_logo.svg.png',
                'GWM': 'https://upload.wikimedia.org/wikipedia/commons/thumb/1/14/GWM_logo.svg/512px-GWM_logo.svg.png',
                'VW': 'https://upload.wikimedia.org/wikipedia/commons/thumb/6/6d/Volkswagen_logo_2019.svg/512px-Volkswagen_logo_2019.svg.png',
                'Toyota': 'https://upload.wikimedia.org/wikipedia/commons/thumb/9/9d/Toyota_carlogo.svg/512px-Toyota_carlogo.svg.png',
                'Fiat': 'https://upload.wikimedia.org/wikipedia/commons/thumb/1/12/Fiat_Automobiles_logo.svg/512px-Fiat_Automobiles_logo.svg.png',
                'OMODA': 'https://upload.wikimedia.org/wikipedia/commons/5/52/Omoda_logo.png',
                'JAECOO': 'https://upload.wikimedia.org/wikipedia/commons/1/1d/Jaecoo_logo.png'
            }

            for _, row in df_f.iterrows():
                if row['Brand'] in logos_marcas:
                    b64 = get_base64_image(logos_marcas[row['Brand']])
                    if b64:
                        fig.add_layout_image(dict(
                            source=b64, xref="x", yref="y", x=row[e_x], y=row[e_y],
                            sizex=tx, sizey=ty, xanchor="center", yanchor="middle",
                            sizing="contain", layer="above"
                        ))

        # --- AJUSTE DE POSIÇÃO E CONTRASTE SOLICITADO ---
        fig.update_traces(
            marker=dict(size=45, opacity=0.7), # Bolinha maior e mais opaca para servir de fundo sólido
            textposition='middle center',       # Texto centralizado na bolinha
            texttemplate="%{text}", 
            textfont=dict(size=9, color="white", family="Arial Black") # Fonte branca em negrito para contraste
        )
        
        fig.update_layout(
            height=850, 
            template="plotly_white", 
            margin=dict(r=50, l=50, t=50, b=50),
            uniformtext_minsize=7, 
            uniformtext_mode='hide'
        )
        st.plotly_chart(fig, use_container_width=True)

    with tab2:
        st.subheader("Inserir Novo Veículo")
        with st.form("new_car"):
            col1, col2, col3 = st.columns(3)
            with col1:
                nb, nn, nt = st.text_input("Brand"), st.text_input("Name"), st.text_input("Category")
            with col2:
                npt = st.selectbox("Powertrain", ["BEV", "PHEV", "HEV", "ICE"])
                np, nl = st.number_input("Price (R$)", min_value=0.0), st.number_input("Length (mm)", min_value=0)
            with col3:
                nw, nh = st.number_input("Width (mm)", min_value=0), st.number_input("Height (mm)", min_value=0)
                nd, ns = st.date_input("Launch Date"), st.selectbox("Status", ["Official", "Speculation"])

            if st.form_submit_button("Salvar e Sincronizar"):
                new_data = {'Brand': nb, 'Name': nn, 'Type': nt, 'Powertrain': npt, 'Price': np, 'Lenght': nl, 'Width': nw, 'Height': nh, 'Launch Date': nd.strftime('%d/%m/%Y'), 'Type of info': ns}
                if save_data(pd.concat([df, pd.DataFrame([new_data])], ignore_index=True), token_atual):
                    st.rerun()