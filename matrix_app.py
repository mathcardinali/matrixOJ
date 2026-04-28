import streamlit as st
import pandas as pd
import plotly.express as px
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
# 1. CONFIGURAÇÕES, PERSISTÊNCIA E I18N
# ==========================================
st.set_page_config(page_title="Automotive MI & Launches", page_icon="🚗", layout="wide")

CACHE_FILE = "token_cache.bin"

# Dicionário de Internacionalização (i18n) - Atualizado para Fase 4
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
        "price": "Price Range (R$)",
        "tab_matrix": "📊 Competitive Matrix",
        "tab_radar": "📰 News Radar & Fast Add",
        "tab_edit": "✏️ Edit Vehicle",
        "x_axis": "X Axis",
        "y_axis": "Y Axis",
        "name": "Name (Model)",
        "powertrain": "Powertrain",
        "length": "Length (mm)",
        "width": "Width (mm)",
        "height": "Height (mm)",
        "status": "Status",
        "save": "Save & Sync",
        "select_edit": "Select Vehicle to Edit",
        "news_desc": "Latest launch news. Filter by date and click 'Fast Register' to auto-fill the form below.",
        "loading_news": "Scanning news portals...",
        "no_news": "No recent launch news found for the selected period.",
        "fast_register": "⚡ Fast Register",
        "sent_to_add": "Data sent! Scroll down to complete the registration.",
        "add_new_vehicle": "➕ Add New Vehicle",
        "mandatory_warning": "⚠️ Please fill all mandatory fields: Brand, Name (Model), Category, Powertrain, and a valid Price.",
        "success_added": "✅ Vehicle {name} added successfully!",
        "others": "Others"
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
        "price": "价格范围 (R$)",
        "tab_matrix": "📊 竞争矩阵",
        "tab_radar": "📰 新闻雷达与快速添加",
        "tab_edit": "✏️ 编辑车辆",
        "x_axis": "X 轴",
        "y_axis": "Y 轴",
        "name": "名称 (型号)",
        "powertrain": "动力系统",
        "length": "长度 (mm)",
        "width": "宽度 (mm)",
        "height": "高度 (mm)",
        "status": "状态",
        "save": "保存并同步",
        "select_edit": "选择要编辑的车辆",
        "news_desc": "最新发布新闻。按日期筛选并点击“快速注册”自动填充下方表单。",
        "loading_news": "扫描新闻门户...",
        "no_news": "在所选期间未找到最近的发布新闻。",
        "fast_register": "⚡ 快速注册",
        "sent_to_add": "数据已发送！向下滚动完成注册。",
        "add_new_vehicle": "➕ 添加新车辆",
        "mandatory_warning": "⚠️ 请填写所有必填字段：品牌，名称，类别，动力系统和有效价格。",
        "success_added": "✅ 车辆 {name} 成功添加！",
        "others": "其他"
    }
}

# Toggle Switch de Idioma
is_chinese = st.sidebar.toggle("🌐 中文 / English", value=False)
st.session_state.lang = "ZH" if is_chinese else "EN"

def t(key):
    return translations[st.session_state.lang].get(key, key)

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

if not check_login():
    st.stop()

# ==========================================
# 3. GESTÃO DE TOKEN E DADOS (ONEDRIVE)
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
def load_data(token):
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
            df['Type of info'] = df['Type of info'].fillna('Speculation').astype(str)
            return df
        except Exception as e:
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
        st.cache_data.clear()
        return True
    return False

# ==========================================
# 4. FUNÇÃO DE RADAR RSS (Com "Others")
# ==========================================
@st.cache_data(ttl=1800) 
def fetch_automotive_news():
    feeds = [
    # --- Os 8 Principais (Anteriormente citados) ---
    "https://motor1.uol.com.br/rss/news/all/",
    "https://insideevs.uol.com.br/rss/news/all/",
    "https://www.automotivebusiness.com.br/rss/",
    "https://autoesporte.globo.com/rss/autoesporte/",
    "https://quatrorodas.abril.com.br/feed/",
    "https://www.mobiauto.com.br/revista/rss",
    "https://www.noticiasautomotivas.com.br/feed/",
    "https://garagem360.com.br/feed/",
    
    # --- Inteligência de Mercado e Segredos (Novos) ---
    "https://www.autossegredos.com.br/feed/",
    "https://autoentusiastas.com.br/feed/",
    "https://www.autoo.com.br/noticias/rss.xml",
    "https://vrum.com.br/feed/",
    "https://car.blog.br/feeds/posts/default",
    
    # --- Negócios e Economia ---
    "https://valor.globo.com/rss/brasil/setor-automotivo/",
    "https://exame.com/noticias-sobre/setor-automotivo/feed/",
    "https://forbes.com.br/forbes-motors/feed/",
    
    # --- Grande Mídia e Marketplaces ---
    "https://jornaldocarro.estadao.com.br/feed/",
    "https://www.webmotors.com.br/wm1/rss",
    "https://www.icarros.com.br/noticias/rss"
]
    keywords = ['lançamento', 'novo', 'chega', 'flagra', 'híbrido', 'elétrico', 'rumores', 'segredo', 'projeção', 'facelift', 'reestilização', 'pré-venda', 'preços', 'SUV', 'PHEV', 'BEV', 'nacionalização', 'confirma']
    brands = ['OMODA','JAECOO','GEELY','GAC','BYD', 'GWM', 'CHERY', 'VOLKSWAGEN', 'VW', 'TOYOTA', 'FIAT', 'OMODA', 'JAECOO', 'RENAULT']
    
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

# ==========================================
# 5. EXECUÇÃO E INTERFACE
# ==========================================
token_atual = get_access_token()
if not token_atual: st.stop()

df = load_data(token_atual)

if not df.empty:
    with st.sidebar:
        st.header(t("settings"))
        view_mode = st.radio(t("time_group"), [t("month"), t("quarter")], horizontal=True)
        
        st.divider()
        st.header(t("filters"))
        
        all_months = sorted(df['Month_Year'].dropna().unique(), key=lambda x: pd.to_datetime(x, format='%m/%Y'))
        default_period = [m for m in all_months if "2026" in m]
        mo_sel = st.multiselect(t("launch_window"), all_months, default=default_period)
        
        brand_list = sorted(df['Brand'].unique())
        type_list = sorted(df['Type'].unique())
        
        # Garante exposição explícita das marcas no filtro
        m_sel = st.multiselect(t("brand"), brand_list, default=brand_list)
        t_sel = st.multiselect(t("category"), type_list, default=type_list)
        
        # Filtro de Preços Fixo (Default: 85.000 a 400.000)
        min_p_data, max_p_data = float(df['Price'].min()), float(df['Price'].max())
        slider_min = min(85000.0, min_p_data)
        slider_max = max(400000.0, max_p_data)
        p_sel = st.slider(t("price"), slider_min, slider_max, (85000.0, 400000.0))

        df_f = df[
            (df['Brand'].isin(m_sel)) & (df['Type'].isin(t_sel)) & 
            (df['Month_Year'].isin(mo_sel)) & (df['Price'] >= p_sel[0]) & (df['Price'] <= p_sel[1])
        ]

    st.title(t("app_title"))
    
    # Abas consolidadas: Cadastro migrou para dentro do Radar
    tab1, tab2, tab3 = st.tabs([t("tab_matrix"), t("tab_radar"), t("tab_edit")])

    # ==================== ABA 1: MATRIZ ====================
    with tab1:
        c1, c2 = st.columns(2)
        y_axis_label = 'Month_Year' if view_mode == t("month") else 'Quarter'
        
        e_x = c1.selectbox(t("x_axis"), ['Lenght', 'Width', 'Height', 'Price', 'Launch Date'], index=4) 
        e_y = c2.selectbox(t("y_axis"), [y_axis_label, 'Price', 'Lenght', 'Width', 'Height'], index=1)

        # Legenda agrupada por Categoria ('Type')
        fig = px.scatter(df_f, x=e_x, y=e_y, 
                         color='Type', 
                         text='Label', 
                         hover_data=['Brand', 'Powertrain', 'Price', 'Month_Year', 'Type of info'])
        
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
        
        # Respiro de 800px no layout, responsividade ligada
        fig.update_layout(
            height=800,
            template="plotly_white", 
            margin=dict(r=50, l=50, t=50, b=50),
            uniformtext_minsize=7, 
            uniformtext_mode='hide',
            legend_title_text=t("category")
        )
        fig.update_xaxes(autorange=True)
        fig.update_yaxes(autorange=True)

        st.plotly_chart(fig, use_container_width=True)

    # ==================== ABA 2: NEWS RADAR & CADASTRO IN-PAGE ====================
    with tab2:
        st.subheader(t("tab_radar"))
        st.markdown(f"*{t('news_desc')}*")
        
        # Filtro de Timeframe
        col_dates = st.columns(2)
        start_news = col_dates[0].date_input("Start Date", date.today().replace(day=1))
        end_news = col_dates[1].date_input("End Date", date.today())
        
        with st.spinner(t("loading_news")):
            df_news = fetch_automotive_news()
            
            if not df_news.empty:
                df_news = df_news[(df_news['Date'] >= start_news) & (df_news['Date'] <= end_news)]
                
                if not df_news.empty:
                    brands_found = sorted(df_news['Brand'].unique())
                    tabs_news = st.tabs(brands_found)
                    for i, b in enumerate(brands_found):
                        with tabs_news[i]:
                            news_b = df_news[df_news['Brand'] == b]
                            for idx, row in news_b.iterrows():
                                n_col1, n_col2 = st.columns([4, 1])
                                n_col1.markdown(f"**[{row['Title']}]({row['Link']})** - *{row['DateStr']}*")
                                
                                # Fast Register Action
                                if n_col2.button(t("fast_register"), key=f"btn_news_{idx}"):
                                    st.session_state['fast_brand'] = row['Brand'] if row['Brand'] != t("others") else brand_list[0]
                                    st.session_state['fast_title'] = row['Title'][:40] 
                                    st.toast(t("sent_to_add"))
                else:
                    st.info(t("no_news"))
            else:
                st.info(t("no_news"))

        st.markdown("---")
        
        # --- Formulário de Cadastro Embutido (In-Page) ---
        default_brand_add = st.session_state.get('fast_brand', brand_list[0])
        default_name_add = st.session_state.get('fast_title', '')

        with st.expander(t("add_new_vehicle"), expanded=bool(default_name_add)):
            with st.form("quick_add_form", clear_on_submit=True):
                col_f1, col_f2, col_f3 = st.columns(3)
                with col_f1:
                    nb = st.selectbox(t("brand") + " *", brand_list, index=brand_list.index(default_brand_add) if default_brand_add in brand_list else 0)
                    nn = st.text_input(t("name") + " *", value=default_name_add)
                    nt = st.selectbox(t("category") + " *", type_list)
                with col_f2:
                    npt = st.selectbox(t("powertrain") + " *", ["BEV", "PHEV", "HEV", "MHEV", "ICE", "REEV"])
                    np = st.number_input(t("price") + " *", min_value=0.0, step=1000.0)
                    nl = st.number_input(t("length"), min_value=0, step=1)
                with col_f3:
                    nw = st.number_input(t("width"), min_value=0, step=1)
                    nh = st.number_input(t("height"), min_value=0, step=1)
                    nd = st.date_input(t("launch_window"))
                    ns = st.selectbox(t("status"), ["Official", "Speculation"])

                if st.form_submit_button(t("save")):
                    # Validação de Campos Obrigatórios
                    if not nb or not nn or not nt or not npt or np <= 0:
                        st.warning(t("mandatory_warning"))
                    else:
                        new_data = {
                            'Brand': nb, 'Name': nn, 'Type': nt, 'Powertrain': npt, 
                            'Price': np, 'Lenght': nl, 'Width': nw, 'Height': nh, 
                            'Launch Date': nd.strftime('%d/%m/%Y'), 'Type of info': ns
                        }
                        if save_data(pd.concat([df, pd.DataFrame([new_data])], ignore_index=True), token_atual):
                            # Limpeza de variáveis de sessão e feedback visual
                            if 'fast_brand' in st.session_state: del st.session_state['fast_brand']
                            if 'fast_title' in st.session_state: del st.session_state['fast_title']
                            
                            st.success(t("success_added").format(name=nn))
                            time.sleep(2) # Pausa breve para o usuário ler o sucesso antes de recarregar
                            st.rerun()

    # ==================== ABA 3: EDIÇÃO (CRUD) ====================
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
                    eb = st.selectbox(t("brand") + " *", brand_list, index=brand_list.index(row_edit['Brand']) if row_edit['Brand'] in brand_list else 0)
                    en = st.text_input(t("name") + " *", value=row_edit['Name'])
                    et = st.selectbox(t("category") + " *", type_list, index=type_list.index(row_edit['Type']) if row_edit['Type'] in type_list else 0)
                with col2:
                    pts = ["BEV", "PHEV", "HEV", "MHEV", "ICE", "REEV"]
                    ept = st.selectbox(t("powertrain") + " *", pts, index=pts.index(row_edit['Powertrain']) if row_edit['Powertrain'] in pts else 0)
                    ep = st.number_input(t("price") + " *", min_value=0.0, step=1000.0, value=float(row_edit['Price']))
                    el = st.number_input(t("length"), min_value=0, step=1, value=int(row_edit['Lenght']) if pd.notnull(row_edit['Lenght']) else 0)
                with col3:
                    ew = st.number_input(t("width"), min_value=0, step=1, value=int(row_edit['Width']) if pd.notnull(row_edit['Width']) else 0)
                    eh = st.number_input(t("height"), min_value=0, step=1, value=int(row_edit['Height']) if pd.notnull(row_edit['Height']) else 0)
                    ed = st.date_input(t("launch_window"), value=row_edit['Launch Date'] if pd.notnull(row_edit['Launch Date']) else date.today())
                    stss = ["Official", "Speculation"]
                    es = st.selectbox(t("status"), stss, index=stss.index(row_edit['Type of info']) if row_edit['Type of info'] in stss else 0)

                if st.form_submit_button(t("save")):
                    # Revalidação para a edição
                    if not eb or not en or not et or not ept or ep <= 0:
                        st.warning(t("mandatory_warning"))
                    else:
                        df.at[idx, 'Brand'] = eb
                        df.at[idx, 'Name'] = en
                        df.at[idx, 'Type'] = et
                        df.at[idx, 'Powertrain'] = ept
                        df.at[idx, 'Price'] = ep
                        df.at[idx, 'Lenght'] = el
                        df.at[idx, 'Width'] = ew
                        df.at[idx, 'Height'] = eh
                        df.at[idx, 'Launch Date'] = ed
                        df.at[idx, 'Type of info'] = es
                        
                        if save_data(df, token_atual):
                            st.success(t("success_added").format(name=en))
                            time.sleep(1.5)
                            st.rerun()
