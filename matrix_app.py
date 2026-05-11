import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import date, datetime
from time import mktime
import time
import msal
import requests
from io import BytesIO
import base64
import urllib.parse as urlparse
import os
import feedparser

# ==========================================
# 1. CONFIGURAÇÕES GLOBAIS E ESTADOS
# ==========================================
st.set_page_config(page_title="Automotive MI & Launches", page_icon="🚗", layout="wide")

CACHE_FILE = "token_cache.bin"

# Dicionário de Internacionalização (i18n)
translations = {
    "EN": {
        "login_title": "🔒 Login - Market Intelligence",
        "user": "Username",
        "pass": "Password",
        "enter": "Login",
        "wrong_cred": "Incorrect credentials.",
        "auth_req": "🔒 Authorization Required",
        "click_auth": "Click here to authorize",
        "paste_url": "Paste the return URL here:",
        "invalid_link": "Invalid Link.",
        "sync_success": "Successfully Synced!",
        "sync_error": "Error saving data.",
        "app_title": "🚗 Automotive Market Intelligence",
        "settings": "View Settings",
        "time_group": "Time Grouping",
        "month": "Month",
        "quarter": "Quarter",
        "filters": "Market Filters",
        "launch_window": "Launch Window",
        "brand": "Brand",
        "category": "Category (Type)",
        "powertrain": "Powertrain",
        "price": "Price Range (R$)",
        "tab_matrix": "📊 Competitive Matrix",
        "tab_radar": "📰 News Radar & Fast Add",
        "tab_edit": "✏️ Edit Vehicle",
        "tab_spec": "📉 Spec Dispersion",
        "x_axis": "X Axis",
        "y_axis": "Y Axis",
        "name": "Name (Model)",
        "length": "Length (mm)",
        "width": "Width (mm)",
        "height": "Height (mm)",
        "status": "Status",
        "save": "Save & Sync",
        "select_edit": "Select Vehicle to Edit",
        "news_desc": "Latest launch news. Filter by date and click 'Fast Register' to auto-fill the form below.",
        "fetch_news_btn": "📰 Fetch News (On-Demand)",
        "start_date": "Start Date",
        "end_date": "End Date",
        "keyword_filter": "Keyword Filter",
        "loading_news": "Scanning news portals...",
        "no_news": "No recent launch news found for the selected period.",
        "fast_register": "⚡ Fast Register",
        "sent_to_add": "Data sent! Scroll down to complete the registration.",
        "add_new_vehicle": "➕ Add New Vehicle",
        "mandatory_warning": "⚠️ Please fill all mandatory fields: Brand, Name (Model), Category, Powertrain, and a valid Price.",
        "success_added": "✅ Vehicle {name} added successfully!",
        "others": "Others",
        "delete_btn": "🗑️ Delete Vehicle",
        "success_deleted": "✅ Vehicle {name} deleted successfully!",
        "dimension": "Dimension",
        "installation_ratio": "Installation Ratio",
        "value_filter": "Value Filter (Y/N)",
        "no_cross_data": "🔄 Cross data not found. Please fill in the Excel sheets correctly.",
        "download_hint": "💡 Tip: To download the High-DPI chart, click the camera icon in the top right corner of the chart."
    },
    "ZH": {
        "login_title": "🔒 登录 - 市场情报",
        "user": "用户名",
        "pass": "密码",
        "enter": "登录",
        "wrong_cred": "凭据不正确。",
        "auth_req": "🔒 需要授权",
        "click_auth": "点击此处授权",
        "paste_url": "在此处粘贴返回 URL：",
        "invalid_link": "无效链接。",
        "sync_success": "同步成功！",
        "sync_error": "保存数据时出错。",
        "app_title": "🚗 汽车市场情报",
        "settings": "视图设置",
        "time_group": "时间分组",
        "month": "月",
        "quarter": "季度",
        "filters": "市场筛选",
        "launch_window": "发布窗口",
        "brand": "品牌",
        "category": "类别 (Type)",
        "powertrain": "动力系统",
        "price": "价格范围 (R$)",
        "tab_matrix": "📊 竞争矩阵",
        "tab_radar": "📰 新闻雷达与快速添加",
        "tab_edit": "✏️ 编辑车辆",
        "tab_spec": "📉 规格分散",
        "x_axis": "X 轴",
        "y_axis": "Y 轴",
        "name": "名称 (型号)",
        "length": "长度 (mm)",
        "width": "宽度 (mm)",
        "height": "高度 (mm)",
        "status": "状态",
        "save": "保存并同步",
        "select_edit": "选择要编辑的车辆",
        "news_desc": "最新发布新闻。按日期筛选并点击“快速注册”自动填充下方表单。",
        "fetch_news_btn": "📰 获取新闻 (按需)",
        "start_date": "开始日期",
        "end_date": "结束日期",
        "keyword_filter": "关键字过滤",
        "loading_news": "扫描新闻门户...",
        "no_news": "在所选期间未找到最近的发布新闻。",
        "fast_register": "⚡ 快速注册",
        "sent_to_add": "数据已发送！向下滚动完成注册。",
        "add_new_vehicle": "➕ 添加新车辆",
        "mandatory_warning": "⚠️ 请填写所有必填字段：品牌，名称，类别，动力系统和有效价格。",
        "success_added": "✅ 车辆 {name} 成功添加！",
        "others": "其他",
        "delete_btn": "🗑️ 删除车辆",
        "success_deleted": "✅ 车辆 {name} 已成功删除！",
        "dimension": "维度",
        "installation_ratio": "安装率",
        "value_filter": "值筛选 (Y/N)",
        "no_cross_data": "🔄 未找到交叉数据。请正确填写 Excel 工作表。",
        "download_hint": "💡 提示：要下载高分辨率 (High-DPI) 图表，请点击图表右上角的相机图标。"
    }
}

plotly_export_config = {
    'toImageButtonOptions': {
        'format': 'png',
        'scale': 12
    }
}

# Inicialização de variáveis no State
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "current_module" not in st.session_state:
    st.session_state.current_module = "matriz"
if "lang" not in st.session_state:
    st.session_state.lang = "EN"

def t(key):
    return translations[st.session_state.lang].get(key, key)

# ==========================================
# 2. SISTEMA DE LOGIN GLOBAL
# ==========================================
def check_login():
    if not st.session_state.authenticated:
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.markdown("<br><br><br>", unsafe_allow_html=True)
            st.subheader(t("login_title"))
            with st.form("login_form"):
                input_user = st.text_input(t("user"))
                input_pass = st.text_input(t("pass"), type="password")
                if st.form_submit_button(t("enter"), use_container_width=True):
                    if "auth" in st.secrets and input_user == st.secrets["auth"]["username"] and input_pass == st.secrets["auth"]["password"]:
                        st.session_state.authenticated = True
                        st.rerun()
                    else:
                        st.error(t("wrong_cred"))
        return False
    return True

# Bloqueia a execução do script inteiro se não estiver logado
if not check_login():
    st.stop()

# ==========================================
# 3. FUNÇÕES GERAIS E DATA LOADERS
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
    st.warning(t("auth_req"))
    st.markdown(f"[{t('click_auth')}]({auth_url})")
    res_url = st.text_input(t("paste_url"))
    if res_url:
        try:
            query = urlparse.urlparse(res_url).query
            params = urlparse.parse_qs(query)
            code = params.get('code', [None])[0] or res_url.strip()
            result = app.acquire_token_by_authorization_code(code, scopes=scopes, redirect_uri=conf["redirect_uri"])
            if "access_token" in result:
                save_token_cache(cache)
                st.rerun()
        except: st.error(t("invalid_link"))
    return None

@st.cache_data(ttl=3600)
def get_base64_image(url):
    try:
        resp = requests.get(url, timeout=5)
        if resp.status_code == 200:
            return "data:image/png;base64," + base64.b64encode(resp.content).decode()
    except: return None

@st.cache_data(ttl=60)
def load_matriz_data(token):
    url = "https://graph.microsoft.com/v1.0/me/drive/root:/Base_MI.xlsx:/content"
    headers = {'Authorization': f'Bearer {token}'}
    resp = requests.get(url, headers=headers)
    if resp.status_code == 200:
        try:
            df = pd.read_excel(BytesIO(resp.content), sheet_name="Launches")
            df['Brand'] = df['Brand'].fillna('').astype(str).str.upper()
            df['Name'] = df['Name'].fillna('').astype(str)
            df['Label'] = "<b>" + df['Brand'] + "</b><br>" + df['Name']
            df['Launch Date'] = pd.to_datetime(df['Launch Date'], format='%d/%m/%Y', errors='coerce')
            df['Month_Year'] = df['Launch Date'].dt.strftime('%m/%Y')
            df['Quarter'] = df['Launch Date'].dt.to_period('Q').astype(str)
            df['Price'] = pd.to_numeric(df['Price'], errors='coerce').fillna(0)
            df['Type'] = df['Type'].fillna(t('others')).astype(str)
            df['Powertrain'] = df['Powertrain'].fillna(t('others')).astype(str)
            df['Type of info'] = df['Type of info'].fillna('Speculation').astype(str)
            return df
        except Exception as e:
            return pd.DataFrame()
    return pd.DataFrame()

@st.cache_data(ttl=60)
def load_spec_data(token):
    url = "https://graph.microsoft.com/v1.0/me/drive/root:/Base_MI.xlsx:/content"
    headers = {'Authorization': f'Bearer {token}'}
    resp = requests.get(url, headers=headers)
    if resp.status_code == 200:
        try:
            excel_data = BytesIO(resp.content)
            xls = pd.ExcelFile(excel_data)
            
            def load_sheet_by_keywords(xls_obj, keywords):
                for sheet in xls_obj.sheet_names:
                    if any(kw.lower() in sheet.lower().strip() for kw in keywords):
                        return pd.read_excel(xls_obj, sheet_name=sheet)
                raise ValueError(f"Aba {keywords[0].upper()} não encontrada.")

            df_keys = load_sheet_by_keywords(xls, ['keys', 'key', 'chave', 'de/para', 'depara'])
            df_fipe = load_sheet_by_keywords(xls, ['fipe', 'volume'])
            df_dim = load_sheet_by_keywords(xls, ['dimension', 'dimensão', 'dimensao', 'spec'])
            df_price = load_sheet_by_keywords(xls, ['price', 'preço', 'preco', 'policy'])

            for df_temp in [df_keys, df_fipe, df_dim, df_price]:
                df_temp.columns = df_temp.columns.astype(str).str.strip()

            feature_map = {}
            col_code = [c for c in df_keys.columns if str(c).strip().lower() in ['code', 'código', 'codigo']]
            col_dim_name = [c for c in df_keys.columns if str(c).strip().lower() in ['dimension', 'dimensão', 'dimensao', 'feature']]
            
            if col_code and col_dim_name:
                mapping_df = df_keys[[col_code[0], col_dim_name[0]]].dropna().drop_duplicates()
                feature_map = dict(zip(
                    mapping_df[col_code[0]].astype(str).str.strip().str.upper(), 
                    mapping_df[col_dim_name[0]].astype(str).str.strip()
                ))

            def padronizar_coluna(df, nomes_aceitos, nome_final):
                for col in df.columns:
                    if col.lower() in [n.lower() for n in nomes_aceitos]:
                        df.rename(columns={col: nome_final}, inplace=True)
                        break

            padronizar_coluna(df_keys, ['Comercial', 'Control', 'Dimensions_Key', 'Dimension_Key', 'Veiculo', 'Carro'], 'Dimensions_Key')
            padronizar_coluna(df_keys, ['FIPE', 'Fipe_Key', 'Fipe Key', 'Modelo_Versao'], 'Fipe_Key')
            padronizar_coluna(df_price, ['Control', 'Comercial', 'Dimensions_Key', 'Dimension_Key'], 'Dimensions_Key')
            padronizar_coluna(df_price, ['MSRP', 'Price', 'Preço', 'Preco', 'Valor'], 'Price')
            padronizar_coluna(df_fipe, ['Modelo_Versao', 'Modelo Versao', 'Fipe_Key', 'Modelo'], 'MODELO_VERSAO')
            padronizar_coluna(df_fipe, ['TIV', 'Volume', 'Vendas', 'Emplacamentos'], 'TIV')

            if 'Dimensions_Key' not in df_keys.columns:
                raise KeyError(f"Aba de Chaves (Keys) não possui coluna válida.")

            def clean_key(series):
                return series.astype(str).str.replace(r'\.0$', '', regex=True).str.strip().str.upper()

            df_keys['Dimensions_Key'] = clean_key(df_keys['Dimensions_Key'])
            if 'Fipe_Key' in df_keys.columns:
                df_keys['Fipe_Key'] = clean_key(df_keys['Fipe_Key'])
            
            if 'Dimensions_Key' in df_price.columns:
                df_price['Dimensions_Key'] = clean_key(df_price['Dimensions_Key'])
                
            df_fipe['MODELO_VERSAO'] = clean_key(df_fipe['MODELO_VERSAO'])

            if 'TIV' not in df_fipe.columns: df_fipe['TIV'] = 0
            df_fipe['TIV'] = pd.to_numeric(df_fipe['TIV'], errors='coerce').fillna(0)
            fipe_ytd = df_fipe.groupby('MODELO_VERSAO')['TIV'].sum().reset_index()

            if 'Price' not in df_price.columns: df_price['Price'] = 0
            df_price['Price'] = pd.to_numeric(df_price['Price'], errors='coerce').fillna(0)

            dim_col = df_dim.columns[0] 
            dim_melt = df_dim.melt(id_vars=[dim_col], var_name='Dimensions_Key', value_name='Value')
            dim_melt.rename(columns={dim_col: 'Dimension'}, inplace=True)
            
            dim_melt['Value'] = dim_melt['Value'].fillna('N').replace({
                'S': 'Y', 's': 'Y', 'Sim': 'Y', 'Yes': 'Y',
                'N': 'N', 'n': 'N', 'Não': 'N', 'No': 'N',
                '': 'N', ' ': 'N'
            })
            
            dim_melt['Dimension_Code'] = dim_melt['Dimension'].astype(str).str.strip().str.upper()
            if feature_map:
                dim_melt['Dimension'] = dim_melt['Dimension_Code'].map(feature_map).fillna(dim_melt['Dimension'])
            
            dim_melt['Dimensions_Key'] = clean_key(dim_melt['Dimensions_Key'])

            df_keys_clean = df_keys[['Dimensions_Key', 'Fipe_Key']].dropna().drop_duplicates('Dimensions_Key')
            merged = dim_melt.merge(df_keys_clean, on='Dimensions_Key', how='left')
            
            if 'Fipe_Key' in merged.columns:
                merged = merged.merge(fipe_ytd, left_on='Fipe_Key', right_on='MODELO_VERSAO', how='left')
            else:
                merged = merged.merge(fipe_ytd, left_on='Dimensions_Key', right_on='MODELO_VERSAO', how='left')
                
            if 'Dimensions_Key' in df_price.columns:
                df_price_clean = df_price[['Dimensions_Key', 'Price']].dropna().drop_duplicates('Dimensions_Key')
                merged = merged.merge(df_price_clean, on='Dimensions_Key', how='left')
            else:
                merged['Price'] = 0

            if 'TIV' in merged.columns: merged['TIV'] = merged['TIV'].fillna(0)
            if 'Price' in merged.columns: merged['Price'] = merged['Price'].fillna(0)

            return merged
        except Exception as e:
            st.error(f"⚠️ Erro de Estrutura no Excel: {e}")
            return pd.DataFrame()
    return pd.DataFrame()

def save_data(df, token):
    url = "https://graph.microsoft.com/v1.0/me/drive/root:/Base_MI.xlsx:/content"
    headers = {'Authorization': f'Bearer {token}'}
    
    resp_get = requests.get(url, headers=headers)
    if resp_get.status_code != 200:
        st.error("Erro ao comunicar com o servidor OneDrive para atualizar a planilha.")
        return False
        
    output = BytesIO(resp_get.content)
    
    df_save = df.copy()
    cols = [c for c in df_save.columns if c not in ['Month_Year', 'Quarter', 'Label']]
    df_to_xlsx = df_save[cols]
    df_to_xlsx['Launch Date'] = pd.to_datetime(df_to_xlsx['Launch Date']).dt.strftime('%d/%m/%Y')
    
    try:
        with pd.ExcelWriter(output, engine='openpyxl', mode='a', if_sheet_exists='replace') as writer:
            df_to_xlsx.to_excel(writer, sheet_name="Launches", index=False)
    except Exception as e:
        st.error(f"Erro na conversão do arquivo: {e}")
        return False
        
    headers_put = {
        'Authorization': f'Bearer {token}', 
        'Content-Type': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    }
    
    resp = requests.put(url, headers=headers_put, data=output.getvalue())
    if resp.status_code in [200, 201]:
        st.cache_data.clear()
        return True
    return False

@st.cache_data(ttl=1800) 
def fetch_automotive_news():
    feeds = [
        "https://motor1.uol.com.br/rss/news/all/",
        "https://insideevs.uol.com.br/rss/news/all/",
        "https://www.automotivebusiness.com.br/rss/",
        "https://autoesporte.globo.com/rss/autoesporte/",
        "https://quatrorodas.abril.com.br/feed/",
        "https://www.mobiauto.com.br/revista/rss",
        "https://www.noticiasautomotivas.com.br/feed/",
        "https://garagem360.com.br/feed/",
        "https://www.autossegredos.com.br/feed/",
        "https://autoentusiastas.com.br/feed/",
        "https://www.autoo.com.br/noticias/rss.xml",
        "https://vrum.com.br/feed/",
        "https://car.blog.br/feeds/posts/default",
        "https://valor.globo.com/rss/brasil/setor-automotivo/",
        "https://exame.com/noticias-sobre/setor-automotivo/feed/",
        "https://forbes.com.br/forbes-motors/feed/",
        "https://jornaldocarro.estadao.com.br/feed/",
        "https://www.webmotors.com.br/wm1/rss",
        "https://www.icarros.com.br/noticias/rss"
    ]
    keywords = ['lançamento', 'novo', 'chega', 'flagra', 'híbrido', 'elétrico', 'rumores', 'segredo', 'projeção', 'facelift', 'reestilização', 'pré-venda', 'preços', 'SUV', 'PHEV', 'BEV', 'nacionalização', 'confirma']
    brands = ['OMODA','JAECOO','GEELY','GAC','BYD', 'GWM', 'CHERY', 'VOLKSWAGEN', 'VW', 'TOYOTA', 'FIAT', 'RENAULT']
    
    news_data = []
    for url in feeds:
        try:
            parsed = feedparser.parse(url)
            for entry in parsed.entries:
                title = entry.title
                if any(kw.lower() in title.lower() for kw in keywords):
                    matched_brand = t("others")
                    for b in brands:
                        if b in title.upper():
                            matched_brand = b if b != 'VW' else 'VOLKSWAGEN'
                            break
                    
                    pub_date = date.today()
                    if hasattr(entry, 'published_parsed') and entry.published_parsed:
                        pub_date = datetime.fromtimestamp(mktime(entry.published_parsed)).date()

                    news_data.append({
                        "Brand": matched_brand,
                        "Title": title,
                        "Link": entry.link,
                        "Date": pub_date,
                        "DateStr": entry.get('published', 'Recent')
                    })
        except:
            continue
    return pd.DataFrame(news_data)

@st.cache_data
def load_survey_data():
    df = pd.read_csv('Buyers Survey 20260511.csv')
    return df

def process_multiple_choice(df, keyword):
    cols = [c for c in df.columns if keyword in c and '[' in c]
    counts = {}
    for c in cols:
        item_name = c.split('[')[-1].replace(']', '')
        counts[item_name] = df[c].notna().sum()
    return pd.DataFrame(list(counts.items()), columns=['Categoria', 'Contagem']).sort_values('Contagem', ascending=True)

# ==========================================
# 4. MÓDULO PRINCIPAL: MATRIZ (APP 1)
# ==========================================
def run_matriz():
    # Botão para alternar para o Survey
    if st.sidebar.button("📊 Go to Buyers Survey Dashboard", use_container_width=True):
        st.session_state.current_module = "survey"
        st.rerun()
        
    st.sidebar.markdown("---")
    
    # Interruptor de Idioma
    lang_choice = st.sidebar.radio("🌐 Language / 语言", ["English", "中文 (Chinese)"], horizontal=True)
    st.session_state.lang = "ZH" if "中文" in lang_choice else "EN"

    token_atual = get_access_token()
    if not token_atual: st.stop()

    df = load_matriz_data(token_atual)

    if not df.empty:
        with st.sidebar:
            st.header(t("settings"))
            view_mode = st.radio(t("time_group"), [t("month"), t("quarter")], horizontal=True)
            st.divider()

        all_months = sorted(df['Month_Year'].dropna().unique(), key=lambda x: pd.to_datetime(x, format='%m/%Y'))
        default_period = [m for m in all_months if "2026" in m]
        brand_list = sorted(df['Brand'].unique())
        type_list = sorted(df['Type'].unique())
        powertrain_list = sorted(df['Powertrain'].unique())
        
        min_p_data, max_p_data = int(df['Price'].min()), int(df['Price'].max())
        slider_min = min(85000, min_p_data)
        slider_max = max(400000, max_p_data)

        st.title(t("app_title"))
        
        st.markdown(
            """
            <style>
            div[data-baseweb="select"] > div:first-child {
                max-height: 85px; 
                overflow-y: auto;
            }
            div[data-baseweb="select"] > div:first-child::-webkit-scrollbar {
                width: 4px;
            }
            div[data-baseweb="select"] > div:first-child::-webkit-scrollbar-thumb {
                background-color: #cccccc;
                border-radius: 4px;
            }
            </style>
            """,
            unsafe_allow_html=True,
        )

        with st.expander(t("filters"), expanded=True):
            f_col1, f_col2, f_col3, f_col4, f_col5, f_col6 = st.columns([1, 1.2, 1.2, 1.2, 2.5, 0.8])
            
            with f_col1: mo_sel = st.multiselect(t("launch_window"), all_months, default=default_period)
            with f_col2: m_sel = st.multiselect(t("brand"), brand_list, default=brand_list)
            with f_col3: t_sel = st.multiselect(t("category"), type_list, default=type_list)
            with f_col4: pt_sel = st.multiselect(t("powertrain"), powertrain_list, default=powertrain_list)
            with f_col5: p_sel = st.slider(t("price"), slider_min, slider_max, (85000, 400000), step=1000)
            with f_col6:
                value_options = ["Y", "N"]
                value_sel = st.multiselect(t("value_filter"), value_options, default=value_options)

        df_f = df[
            (df['Brand'].isin(m_sel)) & 
            (df['Type'].isin(t_sel)) & 
            (df['Powertrain'].isin(pt_sel)) & 
            (df['Month_Year'].isin(mo_sel)) & 
            (df['Price'] >= p_sel[0]) & 
            (df['Price'] <= p_sel[1])
        ]

        tab1, tab2, tab3, tab4 = st.tabs([t("tab_matrix"), t("tab_radar"), t("tab_edit"), t("tab_spec")])

        # ABA 1: MATRIZ
        with tab1:
            c1, c2 = st.columns(2)
            e_x = c1.selectbox(t("x_axis"), ['Lenght', 'Price', 'Launch Date'], index=2) 
            e_y = c2.selectbox(t("y_axis"), ['Price', 'Lenght'], index=0)

            df_f = df_f.copy()
            df_f['Price (BRL)'] = df_f['Price'].apply(lambda x: f"R$ {int(x):,}".replace(",", "."))

            st.caption(t("download_hint"))
            fig = px.scatter(df_f, x=e_x, y=e_y, 
                             color='Type', 
                             text='Label', 
                             hover_data={'Brand': True, 'Powertrain': True, 'Price (BRL)': True, 'Month_Year': True, 'Type of info': True, 'Price': False})
            
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
                    'TOYOTA': 'https://upload.wikimedia.org/wikipedia/commons/thumb/9/9d/Toyota_carlogo.svg/512px-Toyota_carlogo.svg.png',
                    'FIAT': 'https://upload.wikimedia.org/wikipedia/commons/thumb/1/12/Fiat_Automobiles_logo.svg/512px-Fiat_Automobiles_logo.svg.png',
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

            fig.update_traces(
                marker=dict(size=45, opacity=0.7), 
                textposition='middle center',       
                texttemplate="%{text}", 
                textfont=dict(size=9, color="white", family="Arial Black") 
            )
            
            fig.update_layout(
                height=800,
                template="plotly_white", 
                margin=dict(r=50, l=50, t=50, b=50),
                uniformtext_minsize=7, 
                uniformtext_mode='hide',
                legend_title_text=t("category")
            )
            
            if e_x == 'Launch Date':
                fig.update_xaxes(autorange=True, dtick="M1", tickformat="%m/%Y")
            else:
                fig.update_xaxes(autorange=True)
                
            fig.update_yaxes(autorange=True)

            st.plotly_chart(fig, use_container_width=True, config=plotly_export_config)

        # ABA 2: NEWS RADAR & CADASTRO
        with tab2:
            st.subheader(t("tab_radar"))
            st.markdown(f"*{t('news_desc')}*")
            
            if st.button(t("fetch_news_btn"), use_container_width=True):
                st.session_state['show_news'] = True
            
            col_dates = st.columns([1, 1, 2])
            start_news = col_dates[0].date_input(t("start_date"), date.today().replace(day=1))
            end_news = col_dates[1].date_input(t("end_date"), date.today())
            user_keyword = col_dates[2].text_input(t("keyword_filter"), placeholder="e.g. Omoda, PHEV, Preço...")
            
            if st.session_state.get('show_news', False):
                with st.spinner(t("loading_news")):
                    df_news = fetch_automotive_news()
                    
                    if not df_news.empty:
                        df_news = df_news[(df_news['Date'] >= start_news) & (df_news['Date'] <= end_news)]
                        
                        if user_keyword.strip():
                            mask = df_news['Title'].str.contains(user_keyword.strip(), case=False, na=False) | \
                                   df_news['Link'].str.contains(user_keyword.strip(), case=False, na=False)
                            df_news = df_news[mask]
                        
                        if not df_news.empty:
                            brands_found = sorted(df_news['Brand'].unique())
                            tabs_news = st.tabs(brands_found)
                            for i, b in enumerate(brands_found):
                                with tabs_news[i]:
                                    news_b = df_news[df_news['Brand'] == b]
                                    for idx, row in news_b.iterrows():
                                        n_col1, n_col2 = st.columns([4, 1])
                                        n_col1.markdown(f"**[{row['Title']}]({row['Link']})** - *{row['DateStr']}*")
                                        
                                        if n_col2.button(t("fast_register"), key=f"btn_news_{idx}"):
                                            st.session_state['fast_brand'] = row['Brand'] if row['Brand'] != t("others") else brand_list[0]
                                            st.session_state['fast_title'] = row['Title'][:40] 
                                            st.toast(t("sent_to_add"))
                        else:
                            st.info(t("no_news"))
                    else:
                        st.info(t("no_news"))

            st.markdown("---")
            
            default_brand_add = st.session_state.get('fast_brand', brand_list[0])
            default_name_add = st.session_state.get('fast_title', '')

            with st.expander(t("add_new_vehicle"), expanded=bool(default_name_add)):
                with st.form("quick_add_form", clear_on_submit=True):
                    col_f1, col_f2, col_f3 = st.columns(3)
                    with col_f1:
                        ext_brands = brand_list + [t("new_brand_opt")] if "new_brand_opt" in translations[st.session_state.lang] else brand_list + ["➕ New Brand"]
                        nb_sel = st.selectbox(t("brand") + " *", ext_brands, index=brand_list.index(default_brand_add) if default_brand_add in brand_list else 0)
                        nb_new = st.text_input("New Brand Name", placeholder="If '➕ New Brand' is selected")
                        nn = st.text_input(t("name") + " *", value=default_name_add)
                        
                    with col_f2:
                        nt = st.selectbox(t("category") + " *", type_list)
                        npt = st.selectbox(t("powertrain") + " *", ["BEV", "PHEV", "HEV", "MHEV", "ICE", "REEV"])
                        np = st.number_input(t("price") + " *", min_value=0, step=1000)
                        
                    with col_f3:
                        nl = st.number_input(t("length"), min_value=0, step=1)
                        nd = st.date_input(t("launch_window"))
                        ns = st.selectbox(t("status"), ["Official", "Speculation"])

                    if st.form_submit_button(t("save")):
                        new_opt = t("new_brand_opt") if "new_brand_opt" in translations[st.session_state.lang] else "➕ New Brand"
                        nb = nb_new.strip().upper() if nb_sel == new_opt else nb_sel
                        
                        if not nb or not nn or not nt or not npt or np <= 0:
                            st.warning(t("mandatory_warning"))
                        else:
                            new_data = {
                                'Brand': nb, 'Name': nn, 'Type': nt, 'Powertrain': npt, 
                                'Price': np, 'Lenght': nl, 
                                'Launch Date': nd.strftime('%d/%m/%Y'), 'Type of info': ns
                            }
                            if save_data(pd.concat([df, pd.DataFrame([new_data])], ignore_index=True), token_atual):
                                if 'fast_brand' in st.session_state: del st.session_state['fast_brand']
                                if 'fast_title' in st.session_state: del st.session_state['fast_title']
                                st.session_state['show_news'] = False 
                                st.success(t("success_added").format(name=nn))
                                time.sleep(2)
                                st.rerun()

        # ABA 3: EDIÇÃO (CRUD)
        with tab3:
            st.subheader(t("tab_edit"))
            df_edit_options = df['Brand'] + " " + df['Name']
            veh_sel = st.selectbox(t("select_edit"), df_edit_options.tolist())
            
            if veh_sel:
                idx = df_edit_options[df_edit_options == veh_sel].index[0]
                row_edit = df.loc[idx]
                
                with st.form("edit_car"):
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        ext_brands = brand_list + [t("new_brand_opt")] if "new_brand_opt" in translations[st.session_state.lang] else brand_list + ["➕ New Brand"]
                        eb_sel = st.selectbox(t("brand") + " *", ext_brands, index=brand_list.index(row_edit['Brand']) if row_edit['Brand'] in brand_list else 0)
                        eb_new = st.text_input("New Brand Name", placeholder="If '➕ New Brand' is selected", key="edit_brand_new")
                        en = st.text_input(t("name") + " *", value=row_edit['Name'])
                        
                    with col2:
                        et = st.selectbox(t("category") + " *", type_list, index=type_list.index(row_edit['Type']) if row_edit['Type'] in type_list else 0)
                        pts = ["BEV", "PHEV", "HEV", "MHEV", "ICE", "REEV"]
                        ept = st.selectbox(t("powertrain") + " *", pts, index=pts.index(row_edit['Powertrain']) if row_edit['Powertrain'] in pts else 0)
                        ep = st.number_input(t("price") + " *", min_value=0, step=1000, value=int(row_edit['Price']))
                        el = st.number_input(t("length"), min_value=0, step=1, value=int(row_edit['Lenght']) if pd.notnull(row_edit['Lenght']) else 0)
                    with col3:
                        ed = st.date_input(t("launch_window"), value=row_edit['Launch Date'] if pd.notnull(row_edit['Launch Date']) else date.today())
                        stss = ["Official", "Speculation"]
                        es = st.selectbox(t("status"), stss, index=stss.index(row_edit['Type of info']) if row_edit['Type of info'] in stss else 0)

                    col_btn1, col_btn2 = st.columns(2)
                    with col_btn1:
                        btn_save = st.form_submit_button(t("save"))
                    with col_btn2:
                        btn_delete = st.form_submit_button(t("delete_btn"))

                if btn_save:
                    new_opt = t("new_brand_opt") if "new_brand_opt" in translations[st.session_state.lang] else "➕ New Brand"
                    eb = eb_new.strip().upper() if eb_sel == new_opt else eb_sel
                    
                    if not eb or not en or not et or not ept or ep <= 0:
                        st.warning(t("mandatory_warning"))
                    else:
                        df.at[idx, 'Brand'] = eb
                        df.at[idx, 'Name'] = en
                        df.at[idx, 'Type'] = et
                        df.at[idx, 'Powertrain'] = ept
                        df.at[idx, 'Price'] = ep
                        df.at[idx, 'Lenght'] = el
                        df.at[idx, 'Launch Date'] = pd.to_datetime(ed)
                        df.at[idx, 'Type of info'] = es
                        
                        if save_data(df, token_atual):
                            st.success(t("success_added").format(name=en))
                            time.sleep(1.5)
                            st.rerun()

                if btn_delete:
                    df = df.drop(index=idx)
                    if save_data(df, token_atual):
                        st.success(t("success_deleted").format(name=en))
                        time.sleep(1.5)
                        st.rerun()

        # ABA 4: SPEC DISPERSION
        with tab4:
            st.subheader(t("tab_spec"))
            
            df_spec = load_spec_data(token_atual)
            
            if not df_spec.empty and 'Dimension' in df_spec.columns:
                sc1, sc2 = st.columns([1, 2])
                
                with sc1:
                    dim_options = sorted(df_spec['Dimension'].unique())
                    dim_sel = st.selectbox(t("dimension"), dim_options)
                    
                    spec_pmin, spec_pmax = int(df_spec['Price'].min()), int(df_spec['Price'].max())
                    spec_slider_min = min(85000, spec_pmin)
                    spec_slider_max = max(400000, spec_pmax)
                    spec_p_sel = st.slider(t("price") + " (Spec Range)", spec_slider_min, spec_slider_max, (85000, 400000), step=1000)
                    
                df_spec_filtered = df_spec[(df_spec['Dimension'] == dim_sel) & 
                                           (df_spec['Price'] >= spec_p_sel[0]) & 
                                           (df_spec['Price'] <= spec_p_sel[1]) &
                                           (df_spec['Value'].isin(value_sel))].copy()
                
                with sc2:
                    tiv_y = df_spec_filtered[df_spec_filtered['Value'] == 'Y']['TIV'].sum()
                    tiv_total = df_spec_filtered['TIV'].sum()
                    ratio = (tiv_y / tiv_total * 100) if tiv_total > 0 else 0
                    st.metric(t("installation_ratio"), f"{ratio:.1f}%")
                    
                st.caption(t("download_hint"))
                fig_spec = px.scatter(df_spec_filtered, x='Price', y='TIV', color='Value', 
                                      color_discrete_map={'Y': '#2E7D32', 'N': '#D32F2F'},
                                      hover_data=['Dimensions_Key', 'Price', 'TIV'])
                
                fig_spec.update_layout(template="plotly_white", height=600)
                st.plotly_chart(fig_spec, use_container_width=True, config=plotly_export_config)
                
            else:
                st.info(t("no_cross_data"))


# ==========================================
# 5. MÓDULO INDEPENDENTE: SURVEY (APP 2)
# ==========================================
def run_survey():
    # Botão para voltar à Matriz
    if st.sidebar.button("🔙 Back to Matrix", use_container_width=True):
        st.session_state.current_module = "matriz"
        st.rerun()

    st.sidebar.markdown("---")

    # UPLOADER DE ARQUIVO
    st.sidebar.header("Update Data / 更新数据")
    uploaded_file = st.sidebar.file_uploader("Upload new CSV / 上传新CSV", type=["csv"])
    if uploaded_file is not None:
        with open('Buyers Survey 20260511.csv', 'wb') as f:
            f.write(uploaded_file.getbuffer())
        load_survey_data.clear()
        st.sidebar.success("Data updated successfully! / 数据更新成功！")
        time.sleep(1.5)
        st.rerun()
        
    st.sidebar.markdown("---")
    
    st.title("🚀 Market Intelligence / 市场情报: Omoda & Jaecoo")
    st.markdown("A complete immersion in the journey, profile, satisfaction, and routine of buyers. / 全面沉浸在买家的旅程、个人资料、满意度和日常中。")

    df = load_survey_data()

    # Filtros Globais da barra lateral
    st.sidebar.image("https://upload.wikimedia.org/wikipedia/commons/thumb/a/a7/Streamlit_logo_primary_colormark_darktext.png/300px-Streamlit_logo_primary_colormark_darktext.png", width=150)
    st.sidebar.header("Global Filters / 全局过滤")

    modelo_col = "Qual modelo Omoda & Jaecoo você adquiriu?"
    if modelo_col in df.columns:
        modelos = df[modelo_col].dropna().unique().tolist()
        filtro_modelo = st.sidebar.multiselect("Filter by Purchased Model / 按购买的车型过滤:", modelos, default=modelos)
        if filtro_modelo: df = df[df[modelo_col].isin(filtro_modelo)]

    genero_col = "Qual seu gênero?"
    if genero_col in df.columns:
        generos = df[genero_col].dropna().unique().tolist()
        filtro_genero = st.sidebar.multiselect("Filter by Gender / 按性别过滤:", generos, default=generos)
        if filtro_genero: df = df[df[genero_col].isin(filtro_genero)]

    renda_col = "Qual sua renda familiar mensal?"
    if renda_col in df.columns:
        rendas = df[renda_col].dropna().unique().tolist()
        filtro_renda = st.sidebar.multiselect("Filter by Family Income / 按家庭收入过滤:", rendas, default=rendas)
        if filtro_renda: df = df[df[renda_col].isin(filtro_renda)]

    est_civil_col = "Qual seu estado civil?"
    if est_civil_col in df.columns:
        estados_civis = df[est_civil_col].dropna().unique().tolist()
        filtro_civil = st.sidebar.multiselect("Filter by Marital Status / 按婚姻状况过滤:", estados_civis, default=estados_civis)
        if filtro_civil: df = df[df[est_civil_col].isin(filtro_civil)]

    # KPIs Globais
    st.markdown("---")
    kpi1, kpi2, kpi3 = st.columns(3)
    kpi1.metric("Total Responses / 总回复数", len(df))
    if "CSAT Score" in df.columns:
        csat_val = pd.to_numeric(df["CSAT Score"], errors="coerce").mean()
        kpi2.metric("Avg CSAT Score / 平均CSAT得分", f"{csat_val:.1f}")
    if "Qual foi o método de pagamento do seu Omoda & Jaecoo?" in df.columns:
        top_pagamento = df["Qual foi o método de pagamento do seu Omoda & Jaecoo?"].mode()
        top_pag = top_pagamento[0] if not top_pagamento.empty else "N/A"
        kpi3.metric("Top Payment Method / 主要付款方式", str(top_pag))

    kpi4, kpi5, kpi6 = st.columns(3)
    val_col = "Qual valor negociado com a concessionária pelo seu veículo usado?"
    if val_col in df.columns:
        df['ValorUsadoNum'] = pd.to_numeric(df[val_col], errors='coerce')
        avg_trade = df['ValorUsadoNum'].mean()
        kpi4.metric("Avg Trade-in Value / 平均以旧换新价值", f"R$ {avg_trade:,.0f}" if pd.notnull(avg_trade) else "N/A")

    km_col = "Quantos quilômetros você dirige mensalmente em média?"
    if km_col in df.columns:
        df['KmNum'] = pd.to_numeric(df[km_col], errors='coerce')
        avg_km = df['KmNum'].mean()
        kpi5.metric("Avg Monthly Mileage / 平均月里程", f"{avg_km:,.0f} km" if pd.notnull(avg_km) else "N/A")

    preco_col = "Qual foi o preço pago pelo seu Omoda & Jaecoo? Pode ser o preço aproximado, apenas com números e desconsiderando os centavos."
    if preco_col in df.columns:
        df['PrecoNum'] = pd.to_numeric(df[preco_col].astype(str).str.replace(r'\D', '', regex=True), errors='coerce')
        avg_price = df['PrecoNum'].mean()
        kpi6.metric("Avg Price Paid / 平均支付价格", f"R$ {avg_price:,.0f}" if pd.notnull(avg_price) else "N/A")
    st.markdown("---")

    tabs = st.tabs([
        "👥 Profile & Lifestyle / 个人资料与生活方式", 
        "🛒 Purchase Journey / 购买旅程", 
        "🔄 Competition & Trade-in / 竞争与以旧换新", 
        "🔋 Routine & Usage / 日常与使用", 
        "⭐ 360º Satisfaction / 360º满意度", 
        "🧠 Brand Perception / 品牌认知"
    ])

    # ABA 1: Profile & Lifestyle
    with tabs[0]:
        st.header("Who is our client? / 我们的客户是谁？")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            idade_c = "Qual sua idade?" if "Qual sua idade?" in df.columns else ("Qual sua faixa etária?" if "Qual sua faixa etária?" in df.columns else None)
            if idade_c:
                fig_idade = px.histogram(df, x=idade_c, title="Age Distribution / 年龄分布", color_discrete_sequence=['#4C72B0'])
                st.plotly_chart(fig_idade, use_container_width=True)
                
        with col2:
            if "Qual sua renda familiar mensal?" in df.columns:
                fig_renda = px.pie(df, names=renda_col, title="Family Income / 家庭收入", hole=0.4, color_discrete_sequence=px.colors.qualitative.Pastel)
                st.plotly_chart(fig_renda, use_container_width=True)
                
        with col3:
            if "Qual seu estado civil?" in df.columns:
                fig_estado = px.bar(df[est_civil_col].value_counts().reset_index(), x='count', y=est_civil_col, orientation='h', title="Marital Status / 婚姻状况")
                st.plotly_chart(fig_estado, use_container_width=True)

        col_heat, col_sun = st.columns(2)
        with col_heat:
            if idade_c and renda_col in df.columns:
                st.subheader("Demographics Cross-Analysis / 人口统计交叉分析")
                fig_cross = px.density_heatmap(df, x=idade_c, y=renda_col, title="Income vs Age / 收入与年龄 (Heatmap)", color_continuous_scale="Blues")
                st.plotly_chart(fig_cross, use_container_width=True)
        with col_sun:
            st.subheader("Deep Persona Segmentation / 深度用户画像分割")
            if all(c in df.columns for c in [genero_col, est_civil_col, renda_col]):
                df_sun = df.dropna(subset=[genero_col, est_civil_col, renda_col])
                fig_sun = px.sunburst(df_sun, path=[genero_col, est_civil_col, renda_col], title="Persona Sunburst / 用户画像旭日图", color_discrete_sequence=px.colors.qualitative.Set3)
                st.plotly_chart(fig_sun, use_container_width=True)

        col4, col5, col_filhos = st.columns(3)
        with col4:
            esc_col = "Qual seu grau de escolaridade?"
            if esc_col in df.columns:
                fig_esc = px.bar(df[esc_col].value_counts().reset_index(), x='count', y=esc_col, orientation='h', title="Education Level / 教育程度", color_discrete_sequence=['#55A868'])
                st.plotly_chart(fig_esc, use_container_width=True)
                
        with col5:
            df_pets = process_multiple_choice(df, "Quais animais de estimação você tem?")
            if not df_pets.empty:
                fig_pets = px.pie(df_pets, names='Categoria', values='Contagem', title="Client's Pets / 客户的宠物", hole=0.3)
                st.plotly_chart(fig_pets, use_container_width=True)
                
        with col_filhos:
            filhos_col = "Você tem filhos?"
            if filhos_col in df.columns:
                fig_filhos = px.pie(df, names=filhos_col, title="Do you have children? / 你有孩子吗？", hole=0.3, color_discrete_sequence=['#E15759', '#76B7B2'])
                st.plotly_chart(fig_filhos, use_container_width=True)

        col6, col7 = st.columns(2)
        with col6:
            ocup_col = "Qual sua ocupação atual?"
            if ocup_col in df.columns:
                fig_ocup = px.bar(df[ocup_col].value_counts().reset_index().head(10), x='count', y=ocup_col, orientation='h', title="Top 10 Occupations / 前10名职业", color_discrete_sequence=['#8C564B'])
                st.plotly_chart(fig_ocup, use_container_width=True)
        
        with col7:
            moradores_col = "Quantas pessoas moram em sua residência?"
            if moradores_col in df.columns:
                fig_moradores = px.pie(df, names=moradores_col, title="Family Size / 家庭规模", hole=0.4, color_discrete_sequence=px.colors.sequential.Teal)
                st.plotly_chart(fig_moradores, use_container_width=True)

        st.subheader("Lifestyle and Hobbies / 生活方式和爱好")
        df_hobbies = process_multiple_choice(df, "Quais são seus hobbies ou atividades preferidas")
        if not df_hobbies.empty:
            fig_hobbies = px.bar(df_hobbies, x='Contagem', y='Categoria', orientation='h', title="Most Popular Hobbies / 最受欢迎的爱好", color='Contagem', color_continuous_scale="Teal")
            st.plotly_chart(fig_hobbies, use_container_width=True)

    # ABA 2: Purchase Journey
    with tabs[1]:
        st.header("How and where does the client decide? / 客户如何及在何处决定？")
        
        col1, col2 = st.columns(2)
        with col1:
            df_fontes = process_multiple_choice(df, "Onde você buscou informações sobre esses modelos")
            if not df_fontes.empty:
                fig_fontes = px.bar(df_fontes, x='Contagem', y='Categoria', orientation='h', title="Info Channels Used / 使用的信息渠道")
                st.plotly_chart(fig_fontes, use_container_width=True)
            
        with col2:
            if "Dirigir o modelo fez diferença na sua decisão de compra?" in df.columns:
                td_col = "Dirigir o modelo fez diferença na sua decisão de compra?"
                fig_td = px.pie(df, names=td_col, title="Test-Drive Impact / 试驾影响", hole=0.3, color_discrete_sequence=px.colors.qualitative.Set2)
                st.plotly_chart(fig_td, use_container_width=True)

        st.subheader("Purchase Deep Dive / 购买深入分析")
        col_razao, col_preco = st.columns(2)
        
        with col_razao:
            razao_col = "Quais foram as principais razões pelas quais você adquiriu esse modelo?"
            if razao_col in df.columns:
                fig_razao = px.bar(df[razao_col].value_counts().reset_index().head(5), x='count', y=razao_col, orientation='h', title="Main Reasons for Purchase / 购买的主要原因", color_discrete_sequence=['#2CA02C'])
                st.plotly_chart(fig_razao, use_container_width=True)

        with col_preco:
            if 'PrecoNum' in df.columns:
                fig_preco = px.box(df, x='PrecoNum', title="Price Paid Distribution / 支付价格分布", points="all", color_discrete_sequence=['#9467BD'])
                st.plotly_chart(fig_preco, use_container_width=True)

        if 'PrecoNum' in df.columns and "CSAT Score" in df.columns and modelo_col in df.columns:
            st.subheader("Price vs Satisfaction Correlation / 价格与满意度相关性")
            df['CSAT_Num'] = pd.to_numeric(df['CSAT Score'], errors='coerce')
            fig_scatter_price = px.scatter(df, x='PrecoNum', y='CSAT_Num', color=modelo_col, title="Does paying more mean higher satisfaction? / 支付更多意味着更高的满意度吗？", opacity=0.7)
            st.plotly_chart(fig_scatter_price, use_container_width=True)

        col3, col4 = st.columns(2)
        with col3:
            psico_col = "Eu considero que carros são:"
            if psico_col in df.columns:
                fig_psico = px.bar(df[psico_col].value_counts().reset_index(), x='count', y=psico_col, orientation='h', title="What the car means / 汽车的意义", color_discrete_sequence=['#D62728'])
                st.plotly_chart(fig_psico, use_container_width=True)

        with col4:
            compra_col = "Esse veículo foi comprado como?"
            if compra_col in df.columns:
                fig_compra = px.pie(df, names=compra_col, title="Purchase Modality / 购买方式", hole=0.3, color_discrete_sequence=px.colors.qualitative.Bold)
                st.plotly_chart(fig_compra, use_container_width=True)

        st.subheader("Decision Drivers / 购买决策驱动因素")
        col_d1, col_d2 = st.columns(2)
        
        with col_d1:
            driver1_col = "Ao decidir um novo modelo:"
            if driver1_col in df.columns:
                fig_driver1 = px.bar(df[driver1_col].value_counts().reset_index().head(5), x='count', y=driver1_col, orientation='h', title="When deciding a new model / 决定新车型时", color_discrete_sequence=['#F28E2B'])
                st.plotly_chart(fig_driver1, use_container_width=True)
                
        with col_d2:
            driver2_col = "Prefiro carros que tenham:"
            if driver2_col in df.columns:
                fig_driver2 = px.bar(df[driver2_col].value_counts().reset_index().head(5), x='count', y=driver2_col, orientation='h', title="I prefer cars with / 我更喜欢有...的车", color_discrete_sequence=['#4E79A7'])
                st.plotly_chart(fig_driver2, use_container_width=True)

        st.subheader("Attributes of Choice / 选择的属性")
        df_mod_adj = process_multiple_choice(df, "Quais das palavras abaixo descrevem o modelo que você comprou?")
        if not df_mod_adj.empty:
            fig_mod_adj = px.treemap(df_mod_adj, path=['Categoria'], values='Contagem', title="Words for the purchased car / 所购汽车的关联词", color='Contagem', color_continuous_scale='Blues')
            st.plotly_chart(fig_mod_adj, use_container_width=True)

        if "Qual foi o método de pagamento do seu Omoda & Jaecoo?" in df.columns:
            pag_col = "Qual foi o método de pagamento do seu Omoda & Jaecoo?"
            fig_pag = px.histogram(df, x=pag_col, title="Payment Methods / 付款方式", color=pag_col)
            st.plotly_chart(fig_pag, use_container_width=True)

    # ABA 3: Competition & Trade-in
    with tabs[2]:
        st.header("Competitive Analysis / 竞争分析")
        
        col1, col2 = st.columns(2)
        with col1:
            considerou_col = "Durante seu processo de compra, você considerou seriamente algum outro modelo?"
            if considerou_col in df.columns:
                fig_cons = px.pie(df, names=considerou_col, title="Considered competitors? / 考虑过竞争对手吗？", hole=0.5)
                st.plotly_chart(fig_cons, use_container_width=True)
                
        with col2:
            marca_sub_col = "Qual é / era a marca do seu carro substituido?"
            if marca_sub_col in df.columns and modelo_col in df.columns:
                df_subst = df.dropna(subset=[marca_sub_col, modelo_col])
                fig_treemap = px.treemap(df_subst, path=[marca_sub_col, modelo_col], title="Conquest Matrix (Replaced Brand -> New Model) / 征服矩阵 (替换品牌 -> 新车型)", color_discrete_sequence=px.colors.qualitative.Pastel)
                st.plotly_chart(fig_treemap, use_container_width=True)

        col3, col4 = st.columns(2)
        with col3:
            ano_col = "Qual é / era o ano modelo do seu carro substituido?"
            if ano_col in df.columns:
                fig_ano = px.histogram(df, x=ano_col, title="Year of Replaced Vehicle / 替换车辆年份", nbins=15, color_discrete_sequence=['#F28E2B'])
                st.plotly_chart(fig_ano, use_container_width=True)
                
        with col4:
            motivo_col = "Quais foram as principais razões pelas quais você não comprou o modelo que considerou mais seriamente?"
            if motivo_col in df.columns:
                df_motivos = df[motivo_col].value_counts().reset_index().head(5)
                fig_motivos = px.bar(df_motivos, x='count', y=motivo_col, orientation='h', title="Top 5 Reasons for Rejecting / 拒绝前5大原因")
                st.plotly_chart(fig_motivos, use_container_width=True)

        col_dest, col_box = st.columns(2)
        with col_dest:
            destino_usado_col = "Você deu seu carro usado como entrada na concessionária ou decidiu vender por sua conta?"
            if destino_usado_col in df.columns:
                fig_destino = px.pie(df, names=destino_usado_col, title="What they did with the old car / 旧车处理方式", hole=0.4, color_discrete_sequence=px.colors.qualitative.Set3)
                st.plotly_chart(fig_destino, use_container_width=True)

        with col_box:
            if 'ValorUsadoNum' in df.columns:
                fig_box = px.box(df, y='ValorUsadoNum', title="Trade-in Value Distribution / 以旧换新价值分布", points="all")
                st.plotly_chart(fig_box, use_container_width=True)

        if 'PrecoNum' in df.columns and 'ValorUsadoNum' in df.columns and modelo_col in df.columns:
            st.subheader("Financial Correlation / 财务相关性")
            fig_scatter_fin = px.scatter(df, x='ValorUsadoNum', y='PrecoNum', color=modelo_col, title="Trade-in Value vs Price Paid for New Car / 旧车价值与新车价格对比", opacity=0.8)
            st.plotly_chart(fig_scatter_fin, use_container_width=True)

    # ABA 4: Routine & Usage
    with tabs[3]:
        st.header("Routine & Charging (Electrified) / 日常与充电 (电动化)")
        
        col1, col2 = st.columns(2)
        with col1:
            if 'KmNum' in df.columns:
                fig_km = px.histogram(df, x='KmNum', title="Avg Monthly Mileage / 平均月行驶里程", color_discrete_sequence=['#55A868'])
                st.plotly_chart(fig_km, use_container_width=True)
                
        with col2:
            outros_carros = "Tem outros carros em sua residência?"
            if outros_carros in df.columns:
                fig_frota = px.pie(df, names=outros_carros, title="Owns other vehicles? / 有其他车辆吗？", hole=0.3, color_discrete_sequence=px.colors.qualitative.Dark2)
                st.plotly_chart(fig_frota, use_container_width=True)

        if 'KmNum' in df.columns and modelo_col in df.columns:
            st.subheader("Mileage Analysis by Product / 各产品里程分析")
            fig_km_box = px.box(df, x=modelo_col, y='KmNum', color=modelo_col, title="Mileage Variance by Model / 各车型里程差异")
            st.plotly_chart(fig_km_box, use_container_width=True)
                
        st.subheader("Vehicle Usage Activities / 车辆使用活动")
        df_uso = process_multiple_choice(df, "Com que frequência você usa seu carro atual para as seguintes atividades?")
        if not df_uso.empty:
            fig_uso = px.bar(df_uso.tail(10), x='Contagem', y='Categoria', orientation='h', title="Top 10 Usage Patterns / 前10种使用模式", color='Contagem', color_continuous_scale="Greens")
            st.plotly_chart(fig_uso, use_container_width=True)

        st.subheader("Where do they charge? / 他们在哪里充电？")
        df_carregamento = process_multiple_choice(df, "Com que frequência você carrega seu carro?")
        if not df_carregamento.empty:
            fig_carr = px.bar(df_carregamento, x='Contagem', y='Categoria', orientation='h', title="Charging Locations / 充电地点", color='Contagem', color_continuous_scale="Purples")
            st.plotly_chart(fig_carr, use_container_width=True)

    # ABA 5: 360º Satisfaction
    with tabs[4]:
        st.header("Vehicle Satisfaction Radiography / 车辆满意度图谱")
        
        col_kpi1, col_kpi2 = st.columns(2)
        
        with col_kpi1:
            if "CSAT Score" in df.columns:
                csat_media = pd.to_numeric(df["CSAT Score"], errors='coerce').mean()
                fig_gauge = go.Figure(go.Indicator(
                    mode = "gauge+number",
                    value = csat_media,
                    title = {'text': "Average CSAT Score / 平均CSAT得分"},
                    gauge = {'axis': {'range': [None, 100]}, 'bar': {'color': "darkgreen"}, 'steps' : [{'range': [0, 50], 'color': "lightgray"}]}
                ))
                fig_gauge.update_layout(height=300)
                st.plotly_chart(fig_gauge, use_container_width=True)
                
        with col_kpi2:
            recompra_col = "Você consideraria comprar um novo carro dessa mesma marca no futuro?"
            if recompra_col in df.columns:
                fig_recompra = px.pie(df, names=recompra_col, title="Loyalty Index / 忠诚度指数", hole=0.4, color_discrete_sequence=['#2CA02C', '#D62728', '#7F7F7F'])
                fig_recompra.update_layout(height=300)
                st.plotly_chart(fig_recompra, use_container_width=True)

        geral_sat_col = next((c for c in df.columns if "[Geral]" in c and "[Satisfação]" in c), None)
        if geral_sat_col and modelo_col in df.columns:
            df['GeralSatNum'] = pd.to_numeric(df[geral_sat_col], errors='coerce')
            fig_box_sat = px.box(df, x=modelo_col, y='GeralSatNum', color=modelo_col, title="General Satisfaction by Model / 各车型总体满意度")
            st.plotly_chart(fig_box_sat, use_container_width=True)
        
        sat_cols = [c for c in df.columns if "[Satisfação]" in c]
        if sat_cols:
            df_sat = df[sat_cols].apply(pd.to_numeric, errors='coerce')
            df_sat.columns = [c.split('[')[1].replace(']', '') for c in sat_cols]
            medias = df_sat.mean().reset_index()
            medias.columns = ['Atributo', 'Nota']
            
            if modelo_col in df.columns:
                st.subheader("Satisfaction Matrix by Model / 各车型满意度矩阵")
                sat_model_df = df[[modelo_col] + sat_cols].copy()
                for c in sat_cols: sat_model_df[c] = pd.to_numeric(sat_model_df[c], errors='coerce')
                sat_model_df.columns = [modelo_col] + [c.split('[')[1].replace(']', '') for c in sat_cols]
                sat_grouped = sat_model_df.groupby(modelo_col).mean()
                fig_sat_heat = px.imshow(sat_grouped.T, text_auto=".1f", aspect="auto", title="Attribute Satisfaction Across Models / 跨车型属性满意度", color_continuous_scale="RdYlGn")
                st.plotly_chart(fig_sat_heat, use_container_width=True)

            col_rad, col_top = st.columns(2)
            
            with col_rad:
                fig_radar = go.Figure()
                fig_radar.add_trace(go.Scatterpolar(
                    r=medias['Nota'],
                    theta=medias['Atributo'],
                    fill='toself',
                    name='Avg / 平均',
                    line_color='darkorange'
                ))
                fig_radar.update_layout(
                    polar=dict(radialaxis=dict(visible=True, range=[0, 10])),
                    title="Vehicle Attributes Radar / 车辆属性雷达",
                    height=500
                )
                st.plotly_chart(fig_radar, use_container_width=True)
                
            with col_top:
                medias_sorted = medias.sort_values(by='Nota', ascending=False)
                top5 = medias_sorted.head(5)
                bot5 = medias_sorted.tail(5)
                
                fig_topbot = go.Figure()
                fig_topbot.add_trace(go.Bar(y=top5['Atributo'], x=top5['Nota'], orientation='h', name='Best / 最佳', marker_color='#2CA02C'))
                fig_topbot.add_trace(go.Bar(y=bot5['Atributo'], x=bot5['Nota'], orientation='h', name='Worst / 最差', marker_color='#D62728'))
                fig_topbot.update_layout(title="Best and Worst Attributes / 最佳和最差属性", barmode='group')
                st.plotly_chart(fig_topbot, use_container_width=True)

            st.subheader("Correlation with General Satisfaction / 与总体满意度相关性")
            if 'Geral' in df_sat.columns:
                corr_geral = df_sat.corr()[['Geral']].sort_values(by='Geral', ascending=False).drop('Geral')
                fig_corr_geral = px.bar(corr_geral, x='Geral', y=corr_geral.index, orientation='h', title="What drives satisfaction? / 什么推动了满意度？", color='Geral', color_continuous_scale="RdBu")
                st.plotly_chart(fig_corr_geral, use_container_width=True)

    # ABA 6: Brand Perception
    with tabs[5]:
        st.header("Brand Perception & Future / 品牌认知与未来")
        
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("What defines the brand? / 什么定义了品牌？")
            df_adjetivos = process_multiple_choice(df, "Escolha as 3 palavras que melhor descrevem a marca")
            if not df_adjetivos.empty:
                fig_adj = px.funnel(df_adjetivos.sort_values('Contagem', ascending=False).head(10), x='Contagem', y='Categoria', title="Perception Funnel (Positive) / 认知漏斗（积极）")
                st.plotly_chart(fig_adj, use_container_width=True)
                
        with col2:
            st.subheader("What DOES NOT define the brand? / 什么不定义品牌？")
            df_nao_desc = process_multiple_choice(df, "E quais as 3 palavras que não descrevem a marca")
            if not df_nao_desc.empty:
                fig_nao_desc = px.funnel(df_nao_desc.sort_values('Contagem', ascending=False).head(10), x='Contagem', y='Categoria', title="Perception Funnel (Negative) / 认知漏斗（消极）", color_discrete_sequence=['#E15759'])
                st.plotly_chart(fig_nao_desc, use_container_width=True)
                
        col3, col4 = st.columns(2)
        with col3:
            motor_col = "Qual motor você gostaria que seu próximo carro tivesse?"
            if motor_col in df.columns:
                fig_motor = px.pie(df, names=motor_col, title="Desired Future Engine / 渴望的未来引擎", hole=0.3)
                st.plotly_chart(fig_motor, use_container_width=True)
                
        with col4:
            tempo_troca = "Dentro de quanto tempo você pretende trocar seu carro?"
            if tempo_troca in df.columns:
                fig_tempo = px.pie(df, names=tempo_troca, title="Expectation for Next Purchase / 下次购买的期望", hole=0.3, color_discrete_sequence=px.colors.qualitative.Pastel)
                st.plotly_chart(fig_tempo, use_container_width=True)

        if motor_col in df.columns and modelo_col in df.columns:
            st.subheader("Future Projection / 未来预测")
            fig_proj = px.histogram(df, x=modelo_col, color=motor_col, barmode="group", title="Future Engine Preference by Current Model / 当前车型的未来引擎偏好", color_discrete_sequence=px.colors.qualitative.Safe)
            st.plotly_chart(fig_proj, use_container_width=True)

        col5, col6 = st.columns(2)
        with col5:
            marca_fav_col = "Qual sua marca de carros favorita?"
            if marca_fav_col in df.columns:
                df_fav = df[marca_fav_col].value_counts().reset_index().head(10)
                fig_fav = px.bar(df_fav, x='count', y=marca_fav_col, orientation='h', title="Top 10 Favorite Brands / 前10名最爱品牌", color_discrete_sequence=['#17BECF'])
                st.plotly_chart(fig_fav, use_container_width=True)

        with col6:
            df_rejeitados = process_multiple_choice(df, "E existe alguma marca que você não compraria de jeito nenhum?")
            if not df_rejeitados.empty:
                fig_rej = px.bar(df_rejeitados.tail(10), x='Contagem', y='Categoria', orientation='h', title="Most Rejected Brands / 最被拒绝的品牌", color_discrete_sequence=['#8B0000'])
                st.plotly_chart(fig_rej, use_container_width=True)

        st.subheader("Customer Voice (Open Feedback) / 客户之声 (公开反馈)")
        col_like, col_dislike = st.columns(2)
        
        with col_like:
            like_col = "O que você mais gosta no seu carro novo? Pode nos dar detalhes."
            if like_col in df.columns:
                df_likes = df[[like_col]].dropna().rename(columns={like_col: "What they love / 他们喜欢什么"}).head(10)
                st.dataframe(df_likes, use_container_width=True)

        with col_dislike:
            dislike_col = "E o que você não gosta? Pode nos dar detalhes."
            if dislike_col in df.columns:
                df_dislikes = df[[dislike_col]].dropna().rename(columns={dislike_col: "What they dislike / 他们不喜欢什么"}).head(10)
                st.dataframe(df_dislikes, use_container_width=True)

# ==========================================
# 6. EXECUTOR PRINCIPAL DO ROTEAMENTO
# ==========================================
if st.session_state.current_module == "matriz":
    run_matriz()
elif st.session_state.current_module == "survey":
    run_survey()
