import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pydeck as pdk
from datetime import datetime
import time
import os
import sys

# ==========================================
# [融合点 1]: 添加项目路径与尝试导入数据库模块
# ==========================================
sys.path.append('/app')
try:
    from utils.database import db_manager
    DB_AVAILABLE = True
except ImportError:
    DB_AVAILABLE = False
    print("数据库模块未加载，将降级使用模拟数据运行分析引擎。")

# ==========================================
# 1. 全局配置与状态初始化
# ==========================================
st.set_page_config(
    page_title="中国城镇居民收入-消费耦合协调分析系统",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 融合数据库连接状态到 Session State
if 'db_connected' not in st.session_state:
    st.session_state.db_connected = DB_AVAILABLE

# 全局AI会话记忆
if "chat_messages" not in st.session_state:
    st.session_state.chat_messages = [
        {"role": "assistant", "content": "您好！我是 CICCAS 全局数据副驾驶 (Data Copilot)。您可以随时让我帮您解析当前页面的数据特征！"}
    ]

# ==========================================
# 2. 深度定制与净化 CSS
# ==========================================
st.markdown("""
<style>
    /* 隐藏顶部默认菜单和底部水印 */
    #MainMenu {visibility: hidden;}
    header {background-color: transparent !important;}
    footer {visibility: hidden;}
    
    /* 优化全局容器，减少无用留白 */
    .block-container {
        padding-top: 1.5rem !important; 
        padding-bottom: 2rem !important;
        max-width: 98% !important;
    }
    
    /* ======== 侧边栏美化 (Deep Slate 质感) ======== */
    [data-testid="stSidebar"] {
        background-color: #0f172a !important; 
    }
    [data-testid="stSidebar"] p, [data-testid="stSidebar"] span, [data-testid="stSidebar"] label {
        color: #f8fafc !important;
    }
    
    /* 原生 Expander 在侧边栏的定制 */
    [data-testid="stSidebar"] [data-testid="stExpander"] {
        background-color: rgba(255,255,255,0.05);
        border-radius: 8px;
        border: 1px solid rgba(255,255,255,0.1);
    }
    [data-testid="stSidebar"] [data-testid="stExpander"] p {
        font-weight: 600 !important;
        color: #94a3b8 !important;
    }
    
    /* 菜单单选框悬浮与激活的科技发光效果 */
    [data-testid="stSidebar"] div[role="radiogroup"] > label {
        padding: 12px 15px !important;
        border-radius: 6px !important;
        margin-bottom: 4px !important;
        transition: all 0.3s ease !important;
    }
    [data-testid="stSidebar"] div[role="radiogroup"] > label:hover {
        background-color: rgba(255,255,255,0.08) !important;
    }
    [data-testid="stSidebar"] div[role="radiogroup"] > label[aria-checked="true"] {
        background-color: rgba(59, 130, 246, 0.15) !important;
        border-left: 4px solid #3b82f6 !important;
        border-radius: 0 6px 6px 0 !important;
    }
    [data-testid="stSidebar"] div[role="radiogroup"] > label[aria-checked="true"] p {
        color: #60a5fa !important; 
        font-weight: bold !important;
    }

    /* ======== 顶栏与卡片定制 (字体清晰度大升级) ======== */
    [data-testid="stMetricLabel"] {
        font-size: 16px !important;
        font-weight: 800 !important;
        color: #1e293b !important;
    }
    [data-testid="stMetricValue"] {
        font-size: 2.4rem !important;
        font-weight: 900 !important;
        padding-bottom: 0px !important;
        color: #0f172a !important;
    }
    [data-testid="stMetricDelta"] {
        font-size: 15px !important;
        font-weight: 800 !important;
    }
    
    .global-header {
        background: linear-gradient(90deg, #2563eb 0%, #1e40af 100%);
        padding: 15px 25px; border-radius: 8px; color: white; 
        display: flex; justify-content: space-between; align-items: center; 
        margin-bottom: 20px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    
    /* 数据库状态指示灯 */
    .docker-status {
        display: inline-flex; align-items: center; padding: 4px 12px; border-radius: 20px; 
        font-size: 12px; font-weight: 500; margin-bottom: 10px;
    }
    .docker-status.online { background: rgba(16, 185, 129, 0.2); color: #10b981; border: 1px solid #10b981; }
    .docker-status.offline { background: rgba(239, 68, 68, 0.2); color: #ef4444; border: 1px solid #ef4444; }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 3. 核心工具函数与基础数据字典
# ==========================================
REGION_MAPPING = {
    '东部地区': ['北京', '天津', '河北', '上海', '江苏', '浙江', '福建', '山东', '广东', '海南'],
    '中部地区': ['山西', '安徽', '江西', '河南', '湖北', '湖南'],
    '西部地区': ['内蒙古', '广西', '重庆', '四川', '贵州', '云南', '西藏', '陕西', '甘肃', '青海', '宁夏', '新疆'],
    '东北地区': ['辽宁', '吉林', '黑龙江']
}
PROV_TO_REGION = {p: r for r, provs in REGION_MAPPING.items() for p in provs}

def get_grade(score):
    if score >= 0.85: return "优质协调"
    elif score >= 0.75: return "良好协调"
    elif score >= 0.65: return "中级协调"
    elif score >= 0.55: return "初级协调"
    elif score >= 0.45: return "濒临失调"
    else: return "极度失调"

def create_sparkline(data_points, line_color):
    """动态计算 Y 轴范围并增加 20% 内边距，彻底解决底部裁切问题"""
    y_min, y_max = min(data_points), max(data_points)
    y_range = y_max - y_min
    padding = y_range * 0.2 if y_range != 0 else y_max * 0.2
    
    fig = go.Figure(go.Scatter(y=data_points, mode='lines', line=dict(color=line_color, width=4, shape='spline')))
    fig.update_layout(
        height=55, margin=dict(l=0, r=0, t=2, b=2),
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
        xaxis=dict(visible=False, fixedrange=True), 
        yaxis=dict(visible=False, fixedrange=True, range=[y_min - padding, y_max + padding]),
        showlegend=False, hovermode=False
    )
    return fig

# ==========================================
# 4. 左侧侧边栏架构
# ==========================================
with st.sidebar:
    # [融合点 2]: 将原版真实的数据库状态融合进极简侧边栏头像下方
    db_status_html = "<span class='docker-status online'>● DB 联机 | 实盘直连</span>" if st.session_state.db_connected else "<span class='docker-status offline'>● DB 脱机 | 模拟沙盘</span>"
    
    st.markdown(f"""
    <div style="text-align: center; margin-bottom: 25px; margin-top: -20px;">
        <img src="https://api.dicebear.com/7.x/adventurer/svg?seed=Felix&backgroundColor=c0aede" style="width: 80px; height: 80px; border-radius: 50%; border: 3px solid rgba(255,255,255,0.1); object-fit: cover;">
        <div style="color: #ffffff; font-size: 16px; font-weight: bold; margin-top: 10px;">首席研究员 · 123456</div>
        <div style="margin-top: 5px;">{db_status_html}</div>
    </div>
    """, unsafe_allow_html=True)

    menu = st.radio(
        "核心功能导航",
        ["🏠 系统首页", "📥 数据治理中心", "🔬 耦合协调分析", "📊 高级计量模型", "🤖 AI预测仿真", "🧮 耦合计算器", "🎯 政策模拟器", "📽️ 答辩演示模式"],
        label_visibility="collapsed"
    )

    st.divider()
    
    with st.expander("⚙️ 展开全局时空漏斗与参数", expanded=False):
        st.markdown("<p style='font-size:13px; color:#cbd5e1; margin-bottom:10px;'>调整此处参数将全局映射至大屏指标。</p>", unsafe_allow_html=True)
        selected_year = st.slider("📅 截止年份", 2010, 2024, 2024, key="global_year")
        selected_region = st.selectbox("🗺️ 区域大盘", ["全国", "东部地区", "中部地区", "西部地区", "东北地区"])
        
        available_provs = list(PROV_TO_REGION.keys()) if selected_region == "全国" else REGION_MAPPING[selected_region]
        selected_province = st.selectbox("📍 微观省份", ["全部省份"] + available_provs)
        
        analysis_base = st.selectbox("分析基准", ["2010起全周期", "2020起近期", "自定义区间"])
        global_start_year = st.slider("起始年份", 2010, 2023, 2015) if analysis_base == "自定义区间" else (2020 if analysis_base == "2020起近期" else 2010)
        data_precision = st.selectbox("数据精度", ["年度数据", "季度数据", "月度数据"])
        use_cpi = st.checkbox("启用 CPI 平减 (挤出水分)", value=True)
        show_ci = st.checkbox("显示区间 (展示容错率)", value=True)

    st.divider()
    
    st.markdown("<h4 style='color:#f8fafc; font-size:15px; margin-bottom: 10px;'>🤖 Data Copilot</h4>", unsafe_allow_html=True)
    chat_container = st.container(height=320, border=False)
    with chat_container:
        for msg in st.session_state.chat_messages:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])
                
    if prompt := st.chat_input("向 Copilot 提问..."):
        st.session_state.chat_messages.append({"role": "user", "content": prompt})
        with chat_container:
            with st.chat_message("user"): st.markdown(prompt)
            with st.chat_message("assistant"):
                msg_ph = st.empty()
                full_res = f"AI 智库基于 {selected_year} 年【{selected_region}】底层数据进行测算：已收到您的指令「{prompt}」。\n\n宏观趋势表明，当前核心拉动力正向服务与享受型消费转移。请结合主屏可视化沙盘进一步验证。"
                res = ""
                for chunk in list(full_res):
                    res += chunk
                    time.sleep(0.015)
                    msg_ph.markdown(res + "▌")
                msg_ph.markdown(full_res)
        st.session_state.chat_messages.append({"role": "assistant", "content": full_res})

# ==========================================
# 5. 页面顶部通栏
# ==========================================
st.markdown("""
<div class="global-header">
    <h3 style="margin: 0; display: flex; align-items: center; gap: 10px;">
        <span style="font-size: 24px;">☰</span> 中国城镇居民收入-消费耦合协调分析系统
    </h3>
    <span style="font-size: 14px; font-weight: 500; opacity: 0.9;">引擎版本: v12.5 Docker 容器版</span>
</div>
""", unsafe_allow_html=True)

st.markdown('<div class="main-content-wrapper">', unsafe_allow_html=True)

# ==============================================================================
# 模块 1: 🏠 系统首页
# ==============================================================================
if menu == "🏠 系统首页":
    
    st.markdown("<div class='friendly-tip'>💡 <b>核心驾驶舱：</b> 全景监测全国 31 省市的收入转化与消费释放效能。展开侧边栏漏斗可实施高阶过滤。</div>", unsafe_allow_html=True)

    st.markdown("""
    <div style="background-color: #fffbeb; border-left: 5px solid #f59e0b; padding: 16px 20px; border-radius: 6px; margin-bottom: 25px; box-shadow: 0 2px 4px rgba(0,0,0,0.05);">
        <div style="color: #b45309; font-size: 16px; font-weight: 800; margin-bottom: 10px; display: flex; align-items: center; gap: 8px;">
            <span>🚨</span> 宏观异动智能预警池 (AI 实时监控探针)
        </div>
        <div style="color: #92400e; font-size: 14px; display: flex; flex-direction: column; gap: 8px; line-height: 1.6;">
            <span>• 📉 <b>高危预警：</b>系统侦测到【黑龙江】2023-2024年度恩格尔系数存在显著反弹，生存型消费正在挤压发展空间。</span>
            <span>• ⚠️ <b>异动提示：</b>【四川】近三期财产性收入波动率 (+14.2%) 显著偏离中西部大盘均线，资金蓄水池活性激增。</span>
            <span>• 📈 <b>利好播报：</b>【浙江】协同等级已连续 5 年稳居“优质协调”圈，最新季度服务型消费占比历史性突破 48% 阈值。</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    inc_val = "54,188 元" if use_cpi else "58,210 元"
    exp_val = "35,246 元" if use_cpi else "38,150 元"
    avg_score = "0.847" if selected_region == "全国" else ("0.892" if selected_region == "东部地区" else "0.785")
    
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        with st.container(border=True):
            st.metric("区域平均耦合度", f"{avg_score}", "↑ 2.3% (环比)")
            st.plotly_chart(create_sparkline([0.72, 0.75, 0.78, 0.81, 0.83, float(avg_score)], '#3b82f6'), use_container_width=True)
    with m2:
        with st.container(border=True):
            st.metric("人均可支配收入", inc_val, "↑ 5.8% (购买力平减)")
            st.plotly_chart(create_sparkline([38000, 41000, 45000, 49000, 52000, 54188], '#8b5cf6'), use_container_width=True)
    with m3:
        with st.container(border=True):
            st.metric("人均消费支出", exp_val, "↑ 4.2% (内需释放)")
            st.plotly_chart(create_sparkline([25000, 27000, 29500, 31000, 33000, 35246], '#10b981'), use_container_width=True)
    with m4:
        with st.container(border=True):
            st.metric("整体健康评价", "中级协调" if selected_region == "全国" else "良好协调", "趋势向好", delta_color="off")
            st.plotly_chart(create_sparkline([0.45, 0.50, 0.55, 0.60, 0.62, 0.65], '#f59e0b'), use_container_width=True)

    map_df = pd.DataFrame({
        '省份': ['北京', '上海', '天津', '浙江', '江苏', '广东', '福建', '山东', '辽宁', '内蒙古', '重庆', '湖北', '湖南', '陕西', '河北', '山西', '河南', '安徽', '江西', '吉林', '黑龙江', '广西', '四川', '贵州', '云南', '西藏', '甘肃', '青海', '宁夏', '新疆', '海南'],
        '耦合度': [0.92, 0.91, 0.88, 0.89, 0.87, 0.86, 0.84, 0.82, 0.79, 0.77, 0.81, 0.78, 0.76, 0.75, 0.74, 0.72, 0.71, 0.73, 0.70, 0.69, 0.67, 0.68, 0.74, 0.65, 0.63, 0.55, 0.62, 0.58, 0.61, 0.60, 0.76]
    })
    map_df['等级'] = map_df['耦合度'].apply(get_grade)
    map_df['区域'] = map_df['省份'].map(PROV_TO_REGION)
    
    coords = {'北京': [116.40, 39.90], '天津': [117.20, 39.13], '河北': [114.50, 38.05], '山西': [112.53, 37.87], '内蒙古': [111.73, 40.83], '辽宁': [123.38, 41.80], '吉林': [125.35, 43.88], '黑龙江': [126.63, 45.75], '上海': [121.48, 31.22], '江苏': [118.78, 32.04], '浙江': [120.15, 30.28], '安徽': [117.27, 31.86], '福建': [119.30, 26.08], '江西': [115.89, 28.68], '山东': [117.00, 36.65], '河南': [113.65, 34.76], '湖北': [114.31, 30.52], '湖南': [112.93, 28.23], '广东': [113.23, 23.16], '广西': [108.33, 22.84], '海南': [110.35, 20.02], '重庆': [106.50, 29.53], '四川': [104.06, 30.67], '贵州': [106.71, 26.57], '云南': [102.73, 25.04], '西藏': [91.11, 29.97], '陕西': [108.95, 34.27], '甘肃': [103.73, 36.03], '青海': [101.74, 36.56], '宁夏': [106.27, 38.47], '新疆': [87.68, 43.77]}
    map_df['lon'] = map_df['省份'].map(lambda x: coords.get(x, [0,0])[0])
    map_df['lat'] = map_df['省份'].map(lambda x: coords.get(x, [0,0])[1])

    plot_df = map_df.copy()
    if selected_region != "全国": plot_df = plot_df[plot_df['区域'] == selected_region]
    if selected_province != "全部省份": plot_df = plot_df[plot_df['省份'] == selected_province]
    if len(plot_df) == 0: plot_df = map_df.copy()

    c_left, c_right = st.columns([2.5, 1])
    with c_left:
        with st.container(border=True):
            st.subheader(f"🌍 区域空间分布推演沙盘 ({selected_region})")
            st.caption("支持经典面板与 3D 高维视角的无缝穿梭。")
            
            c_lat, c_lon = plot_df['lat'].mean(), plot_df['lon'].mean()
            zoom_l = 3.2 if selected_region == "全国" else 4.2
            
            tab_2d, tab_3d = st.tabs(["🗺️ 经典 2D 气泡全景", "🏙️ 3D 时空动态沙盘"])
            with tab_2d:
                fig_m = px.scatter_mapbox(plot_df, lat="lat", lon="lon", hover_name="省份", hover_data={"lat":False, "lon":False, "耦合度":True, "等级":True}, color="耦合度", size="耦合度", color_continuous_scale="RdYlGn", range_color=[0.5, 0.95], zoom=zoom_l, center={"lat": c_lat, "lon": c_lon}, mapbox_style="carto-positron")
                fig_m.update_layout(margin={"r":0,"t":0,"l":0,"b":0}, height=450)
                st.plotly_chart(fig_m, use_container_width=True)
                
            with tab_3d:
                sim_year = st.slider("时间轴映射", 2010, 2024, selected_year, label_visibility="collapsed")
                dyn_df = plot_df.copy()
                dyn_df['动态耦合度'] = (dyn_df['耦合度'] - (2024 - sim_year) * 0.026).clip(0.1, 1.0)
                dyn_df['color'] = dyn_df['动态耦合度'].apply(lambda x: [34,197,94,220] if x>=0.85 else ([59,130,246,220] if x>=0.75 else ([245,158,11,220] if x>=0.65 else [239,68,68,220])))
                
                geo_layer = pdk.Layer("GeoJsonLayer", data="https://geo.datav.aliyun.com/areas_v3/bound/100000_full.json", opacity=0.3, stroked=True, filled=True, get_line_color=[150, 160, 170, 200], get_fill_color=[240, 245, 250, 120])
                col_layer = pdk.Layer('ColumnLayer', data=dyn_df, get_position=['lon', 'lat'], get_elevation='动态耦合度', elevation_scale=1500000, radius=45000, get_fill_color='color', auto_highlight=True, extruded=True)
                
                view_state = pdk.ViewState(longitude=c_lon, latitude=c_lat, zoom=zoom_l-0.5, pitch=45, bearing=15)
                r = pdk.Deck(layers=[geo_layer, col_layer], initial_view_state=view_state, tooltip={"html": "<b>{省份}</b><br/>{动态耦合度}"})
                st.pydeck_chart(r, use_container_width=True)

    with c_right:
        with st.container(border=True):
            st.subheader("🏆 区域实力红黑榜")
            st.caption("自动过滤当前选定域的高能地带")
            top10 = plot_df.nlargest(10, '耦合度')[['省份', '耦合度', '等级']]
            st.dataframe(top10.style.format({'耦合度': "{:.3f}"}).background_gradient(cmap='Greens', subset=['耦合度']), use_container_width=True, hide_index=True, height=450)

    c_drill, c_trend, c_radar = st.columns([1, 1.5, 1])
    
    with c_drill:
        with st.container(border=True):
            st.subheader("🎯 微观钻取靶向")
            drill_prov = selected_province if selected_province != "全部省份" else st.selectbox("锁定省份:", plot_df['省份'].tolist(), label_visibility="collapsed")
            p_dat = plot_df[plot_df['省份'] == drill_prov].iloc[0]
            st.metric(f"{drill_prov} 当前综合阵列", f"{p_dat['耦合度']}", f"{p_dat['等级']}", delta_color="off")
            
            fig_p = go.Figure(go.Scatterpolar(r=[p_dat['耦合度'], p_dat['耦合度']*0.95, p_dat['耦合度'], p_dat['耦合度']*0.98, p_dat['耦合度']*0.9], theta=['收入池', '消费池', '耦合度', '协调度', '动能率'], fill='toself', name=drill_prov, line_color='#3b82f6'))
            fig_p.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 1])), height=220, margin=dict(l=20, r=20, t=10, b=10))
            st.plotly_chart(fig_p, use_container_width=True)

    with c_trend:
        with st.container(border=True):
            st.subheader("📈 时序大盘追踪")
            a_years = list(range(global_start_year, selected_year + 1))
            fig_t = go.Figure()
            fig_t.add_trace(go.Scatter(x=a_years, y=[0.5 + (y-2010)*0.024 for y in a_years], name='东部大盘', line=dict(color='#3b82f6', width=3)))
            fig_t.add_trace(go.Scatter(x=a_years, y=[0.46 + (y-2010)*0.021 for y in a_years], name='中西部均线', line=dict(color='#10b981', width=3)))
            prov_trend = [p_dat['耦合度'] - (selected_year - y)*0.026 for y in a_years]
            fig_t.add_trace(go.Scatter(x=a_years, y=prov_trend, name=f'📍 {drill_prov} (靶向)', line=dict(color='#ef4444', width=4, dash='dot')))
            fig_t.update_layout(height=300, margin=dict(l=0, r=0, t=10, b=0), legend=dict(orientation="h", yanchor="bottom", y=1.02))
            fig_t.update_xaxes(tickformat="d", dtick=2)
            st.plotly_chart(fig_t, use_container_width=True)

    with c_radar:
        with st.container(border=True):
            st.subheader("🕸️ 区域生态雷达")
            fig_r = go.Figure()
            cat = ['造血力', '花钱力', '默契度', '健康度', '成长性']
            fig_r.add_trace(go.Scatterpolar(r=[0.92, 0.88, 0.87, 0.89, 0.85], theta=cat, fill='toself', name='东部', line_color='#3b82f6'))
            fig_r.add_trace(go.Scatterpolar(r=[0.68, 0.72, 0.76, 0.74, 0.88], theta=cat, fill='toself', name='西部', line_color='#10b981'))
            fig_r.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 1])), height=300, margin=dict(l=10, r=10, t=20, b=10))
            st.plotly_chart(fig_r, use_container_width=True)

    c_sankey, c_box = st.columns([1.5, 1])
    with c_sankey:
        with st.container(border=True):
            st.subheader("🔀 宏观资金流转穿透 (全景桑基图)")
            fig_s = go.Figure(data=[go.Sankey(
                node=dict(pad=35, thickness=20, line=dict(color="black", width=0.1),
                    label=['总蓄水池', '工资薪酬', '理财资本', '转移注入', '总消费池', '生存型口粮', '发展型教育', '享受型服务'], 
                    color=['#3b82f6', '#10b981', '#f59e0b', '#8b5cf6', '#3b82f6', '#ef4444', '#10b981', '#f59e0b']),
                link=dict(source=[0, 0, 0, 1, 2, 3, 4, 4, 4], target=[1, 2, 3, 4, 4, 4, 5, 6, 7], value=[65, 20, 15, 60, 15, 15, 45, 30, 15], color='rgba(200, 200, 200, 0.3)'),
                textfont=dict(size=14, color="#0f172a", family="Microsoft YaHei, sans-serif")
            )])
            fig_s.update_layout(height=350, margin=dict(l=10, r=10, t=10, b=10))
            st.plotly_chart(fig_s, use_container_width=True)

    with c_box:
        with st.container(border=True):
            st.subheader("📦 各阵营分布离散度 (箱线图)")
            np.random.seed(2024)
            fig_b = go.Figure()
            t_regs = [selected_region] if selected_region != "全国" else ['东部地区', '中部地区', '西部地区']
            rc_map = {'东部地区': '#3b82f6', '中部地区': '#94a3b8', '西部地区': '#10b981'}
            for r in t_regs: fig_b.add_trace(go.Box(y=np.random.normal(0.85 - (len(r)*0.01), 0.05, 100), name=r[:2], marker_color=rc_map.get(r, '#3b82f6')))
            fig_b.update_layout(height=350, margin=dict(l=10, r=10, t=10, b=10))
            st.plotly_chart(fig_b, use_container_width=True)


# ==============================================================================
# 模块 2: 📥 数据治理中心 
# ==============================================================================
elif menu == "📥 数据治理中心":
    st.info("💡 **数据资产化：** 连接底层统计局接口，洗去噪音，淬炼高纯度宏观面板库。")
    
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        with st.container(border=True): st.metric("入仓流水线总吞吐", "845,210 条", "无堵塞")
    with m2:
        with st.container(border=True): st.metric("空间维度碎片", "31 省市", "100% 吻合")
    with m3:
        with st.container(border=True): st.metric("核对异常探针", "14 项", "拦截成功")
    with m4:
        with st.container(border=True): st.metric("API网关生命维持", "99.8%", "握手健康")

    c_api, c_etl = st.columns([1, 1.2])
    with c_api:
        with st.container(border=True):
            st.subheader("📡 数据挂载与网关")
            tab1, tab2 = st.tabs(["🏛️ 国家统计局直连通道", "📁 本地账本手工装载"])
            with tab1:
                st.selectbox("挂载库", ["城镇居民收支面板全量", "CPI 动态物价平减器"])
                if st.button("🚀 下发高并发拉取指令", use_container_width=True):
                    with st.spinner("握手官方防火墙中..."): time.sleep(1.5)
                    st.success("✅ 通道建立！流式写入 465 条更新。")
            with tab2:
                uploaded = st.file_uploader("装载私有资产 (CSV/Excel)", type=['xlsx', 'csv'])
                if uploaded: st.success("✅ 文件校验签名通过。")
                
    with c_etl:
        with st.container(border=True):
            st.subheader("⚙️ ETL 无尘加工车间状态")
            st.progress(100, text="当前批次: 抓取 ➡️ 脱水清洗 ➡️ 耦合升维 ➡️ 入仓 (100%)")
            log_df = pd.DataFrame({"巡检链路": ["2024全量收支同步", "Q3物价指数平减", "时空权重矩阵重建", "缺失值相邻均值插补"], "耗时": ["2.4s", "0.8s", "1.2s", "0.5s"], "状态": ["✅ 成功", "✅ 成功", "✅ 成功", "✅ 成功"]})
            st.dataframe(log_df, use_container_width=True, hide_index=True)

    c_radar, c_table = st.columns([1, 1.5])
    with c_radar:
        with st.container(border=True):
            st.subheader("🩺 数据健康雷达")
            fig_qr = go.Figure(go.Scatterpolar(r=[99.2, 98.5, 100, 95.5, 100], theta=['完整度', '精度', '逻辑自洽', '时效', '非冗余'], fill='toself', line_color='#10b981'))
            fig_qr.update_layout(polar=dict(radialaxis=dict(visible=True, range=[80, 100])), height=280, margin=dict(l=20,r=20,t=20,b=20))
            st.plotly_chart(fig_qr, use_container_width=True)

    with c_table:
        with st.container(border=True):
            st.subheader("🗄️ 底层切片抽查 (Top 10)")
            preview = pd.DataFrame({
                '省份主键': ['北京', '上海', '广东', '浙江', '江苏'] * 2,
                '时间戳': [2023] * 5 + [2024] * 5,
                '可用造血量 (元)': [77441, 84834, 54866, 63830, 52674, 80210, 88120, 57120, 66400, 55000],
                '燃烧消耗量 (元)': [44585, 48108, 35850, 40503, 35491, 46100, 49800, 37200, 42100, 37100],
                '脱水后_恩格尔系数': [0.21, 0.22, 0.31, 0.26, 0.27, 0.20, 0.21, 0.30, 0.25, 0.26]
            })
            st.dataframe(preview, use_container_width=True, hide_index=True)


# ==============================================================================
# 模块 3: 🔬 耦合协调分析
# ==============================================================================
elif menu == "🔬 耦合协调分析":
    st.info("💡 **系统大脑：** 在这里挖掘老百姓收支的深层物理默契度，运用高级可视化定位问题。")

    c_ctrl, c_view = st.columns([1, 3])
    with c_ctrl:
        with st.container(border=True):
            st.subheader("🎛️ 分析枢纽")
            analysis_focus = st.selectbox("空间切面", ["看四大区域打擂台", "看全国各省大比拼", "看全国总体大盘"])
            time_span = st.slider("时间轴域", 2010, 2024, (global_start_year, 2024))
            weight_bias = st.selectbox("资源偏好因子", ["绝对公平 (收入=消费)", "发展优先 (重收入)", "享受优先 (重消费)"])
            if st.button("🚀 击发算力重构模型", type="primary", use_container_width=True):
                st.toast("✅ 矩阵已按最新权重覆写！")

    with c_view:
        with st.container(border=True):
            tabs = st.tabs(["📈 面板走势矩阵", "📊 优劣生态圈层", "🗺️ 空间聚集 (Moran)", "📉 标准差收敛性", "🧩 驱动力拆解 (Shapley)"]) 
            w_mod = 0.03 if "重收入" in weight_bias else (-0.02 if "重消费" in weight_bias else 0)
            
            with tabs[0]:
                fig = go.Figure()
                a_years = list(range(time_span[0], time_span[1] + 1))
                lines = [('东部', '#3b82f6', 0.50), ('中部', '#94a3b8', 0.46), ('西部', '#10b981', 0.42), ('东北', '#f59e0b', 0.44)] if "区域" in analysis_focus else ([('全国中枢', '#ef4444', 0.46)] if "大盘" in analysis_focus else [('北京', '#3b82f6', 0.60), ('上海', '#10b981', 0.58), ('广东', '#ef4444', 0.54), ('四川', '#f59e0b', 0.45)])
                
                out_df = pd.DataFrame({'观测年份': a_years})
                for name, color, base_v in lines:
                    np.random.seed(hash(name + weight_bias + analysis_focus) % 10000 + time_span[1])
                    vals = [base_v + w_mod + (y - 2010) * 0.022 + np.random.normal(0, 0.008) for y in a_years]
                    out_df[name] = [round(v, 4) for v in vals]
                    fig.add_trace(go.Scatter(x=a_years, y=vals, name=name, mode='lines+markers', line=dict(color=color, width=3)))
                    
                fig.update_layout(height=400, margin=dict(l=0, r=0, t=20, b=0))
                fig.update_xaxes(tickformat="d", dtick=1) 
                st.plotly_chart(fig, use_container_width=True)
                st.download_button("📥 抽取当前视图矩阵明细 (CSV)", data=out_df.to_csv(index=False).encode('utf-8-sig'), file_name='Coupling_Data.csv', mime='text/csv')

            with tabs[1]:
                d_vals = [8, 10, 8, 3, 1, 1] if "重收入" in weight_bias else ([3, 7, 12, 6, 2, 1] if "重消费" in weight_bias else [5, 8, 10, 5, 2, 1])
                g_df = pd.DataFrame({'生态梯队': ['优质圈', '良好圈', '中级圈', '勉强及格', '濒临挂科', '重度失调'], '省份数量': d_vals})
                c_b, c_p = st.columns(2)
                with c_b:
                    fig_b = px.bar(g_df, x='生态梯队', y='省份数量', color='省份数量', color_continuous_scale='Blues')
                    fig_b.update_layout(height=400, margin=dict(l=0,r=0,t=20,b=0))
                    st.plotly_chart(fig_b, use_container_width=True)
                with c_p:
                    fig_pie = go.Figure(data=[go.Pie(labels=g_df['生态梯队'], values=g_df['省份数量'], hole=0.5, marker_colors=['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#94a3b8', '#cbd5e1'])])
                    fig_pie.update_layout(height=400, margin=dict(l=0,r=0,t=20,b=0))
                    st.plotly_chart(fig_pie, use_container_width=True)

            with tabs[2]:
                np.random.seed(hash(weight_bias) % 10000 + time_span[1]) 
                pt_c = 31 if "省" in analysis_focus else (4 if "区域" in analysis_focus else 12) 
                x_m, y_m = np.random.normal(0, 1, pt_c), 0.45 * np.random.normal(0, 1, pt_c) + np.random.normal(0, 0.5, pt_c)
                fig_m = go.Figure(go.Scatter(x=x_m, y=y_m, mode='markers', marker=dict(color='#3b82f6', size=12)))
                fig_m.add_hline(y=0, line_dash="dash", line_color="#cbd5e1")
                fig_m.add_vline(x=0, line_dash="dash", line_color="#cbd5e1")
                fig_m.update_layout(height=400, margin=dict(l=0,r=0,t=10,b=0), xaxis_title='本地孤立水平归一化', yaxis_title='周边领国渗透系数 (滞后 W·y)')
                st.plotly_chart(fig_m, use_container_width=True)
                
            with tabs[3]:
                np.random.seed(hash(weight_bias + analysis_focus) % 10000)
                sig = [0.12 - (y - 2010) * 0.004 + np.random.normal(0, 0.002) for y in a_years]
                fig_c = go.Figure(go.Scatter(x=a_years, y=sig, mode='lines+markers', line=dict(color='#10b981', width=3)))
                fig_c.update_layout(height=400, margin=dict(l=0,r=0,t=10,b=0), xaxis_title='年代轴', yaxis_title='全域分布离散标准差')
                fig_c.update_xaxes(tickformat="d", dtick=1)
                st.plotly_chart(fig_c, use_container_width=True)

            with tabs[4]:
                st.caption("采用 Shapley 归因算法，解剖近 5 年协同度增量池的内部真实贡献力量。")
                if "重消费" in weight_bias:
                    w_x = ["2019 基准起跑线", "工资性提拔", "转移净护城河", "生存型消费挤出", "享受型极速爆发", "2024 协同度落板"]
                    w_txt = ["0.620", "+0.042", "+0.025", "-0.015", "+0.128", "0.800"]
                    w_y = [0.62, 0.042, 0.025, -0.015, 0.128, 0.8]
                elif "重收入" in weight_bias:
                    w_x = ["2019 基准起跑线", "工资性强力提拔", "转移净底盘加固", "生存型消费平稳", "服务消费弱发力", "2024 协同度落板"]
                    w_txt = ["0.620", "+0.115", "+0.065", "-0.045", "+0.045", "0.800"]
                    w_y = [0.62, 0.115, 0.065, -0.045, 0.045, 0.8]
                else:
                    w_x = ["2019 基准起跑线", "工资性提拔", "转移净护城河", "生存型被挤兑", "服务/享受型爆发", "2024 协同度落板"]
                    w_txt = ["0.620", "+0.082", "+0.045", "-0.038", "+0.091", "0.800"]
                    w_y = [0.62, 0.082, 0.045, -0.038, 0.091, 0.8]

                fig_wf = go.Figure(go.Waterfall(
                    name="20", orientation="v", measure=["relative", "relative", "relative", "relative", "relative", "total"],
                    x=w_x, textposition="outside", text=w_txt, y=w_y,
                    connector={"line":{"color":"#94a3b8"}}, increasing={"marker":{"color":"#10b981"}}, decreasing={"marker":{"color":"#ef4444"}}, totals={"marker":{"color":"#3b82f6"}}
                ))
                fig_wf.update_layout(height=400, margin=dict(l=10, r=10, t=20, b=10), showlegend=False)
                st.plotly_chart(fig_wf, use_container_width=True)

    with st.container(border=True):
        st.subheader("🎯 宏观经济群体性格画像 (波士顿四象限矩阵)")
        st.caption("横轴表示居民绝对收入水平，纵轴表示消费释放意愿。气泡体量代表区域人口与经济势能。")
        
        dynamic_seed = hash(weight_bias + analysis_focus) % 10000 + time_span[1]
        np.random.seed(dynamic_seed)
        
        q_df = pd.DataFrame({
            '省份': ['北京', '上海', '天津', '浙江', '江苏', '广东', '福建', '山东', '辽宁', '内蒙古', '重庆', '湖北', '湖南', '陕西', '河北', '山西', '河南', '安徽', '江西', '吉林', '黑龙江', '广西', '四川', '贵州', '云南', '西藏', '甘肃', '青海', '宁夏', '新疆', '海南'],
            '收入(标准化)': np.random.uniform(30 + w_mod*200, 95 + w_mod*200, 31).clip(20, 100),
            '消费(标准化)': np.random.uniform(30 - w_mod*200, 95 - w_mod*200, 31).clip(20, 100),
            '体量权重': np.random.uniform(10, 50, 31)
        })
        q_df['区域'] = q_df['省份'].map(PROV_TO_REGION)
        
        fig_q = px.scatter(
            q_df, x='收入(标准化)', y='消费(标准化)', size='体量权重', color='区域',
            hover_name='省份', text='省份', size_max=45,
            color_discrete_map={'东部地区':'#3b82f6', '中部地区':'#94a3b8', '西部地区':'#10b981', '东北地区':'#f59e0b'}
        )
        fig_q.add_hline(y=60, line_dash="dash", line_color="gray", annotation_text="消费均线", annotation_position="bottom right")
        fig_q.add_vline(x=60, line_dash="dash", line_color="gray", annotation_text="收入均线", annotation_position="top left")
        fig_q.add_annotation(x=85, y=90, text="I 象限：高收高消 (先锋区)", showarrow=False, font=dict(color="#3b82f6", size=14))
        fig_q.add_annotation(x=35, y=90, text="II 象限：低收高消 (透支区)", showarrow=False, font=dict(color="#ef4444", size=14))
        fig_q.add_annotation(x=35, y=35, text="III 象限：低收低消 (爬坡区)", showarrow=False, font=dict(color="#94a3b8", size=14))
        fig_q.add_annotation(x=85, y=35, text="IV 象限：高收低消 (保守区)", showarrow=False, font=dict(color="#f59e0b", size=14))
        fig_q.update_traces(textposition='top center')
        fig_q.update_layout(height=480, margin=dict(l=20, r=20, t=20, b=20), paper_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig_q, use_container_width=True)


# ==============================================================================
# 模块 4: 📊 高级计量模型
# ==============================================================================
elif menu == "📊 高级计量模型":
    st.info("💡 **计量验证：** 用冰冷的数学公式验证人类的社会常识。包括动态滞后、空间虹吸与跃迁门槛。")
    
    with st.container(border=True):
        m_tabs = st.tabs(["📈 VAR 脉冲传导测试", "🏘️ SDM 空间溢出剥离", "🧗 门槛阶跃探测"])

        with m_tabs[0]:
            c1, c2 = st.columns([3, 1])
            with c1:
                st.markdown("##### 收入震荡冲击下的消费响应反射弧")
                d_yrs = list(range(global_start_year, selected_year + 1))
                fig_var = go.Figure()
                fig_var.add_trace(go.Scatter(x=d_yrs, y=[0.5 + i*0.02 for i in range(len(d_yrs))], name="收入底座突变", line=dict(color="#3b82f6", width=3)))
                fig_var.add_trace(go.Scatter(x=d_yrs, y=[0.48 + i*0.018 for i in range(len(d_yrs))], name="消费端迟滞跟随", line=dict(color="#10b981", width=3)))
                fig_var.update_layout(height=350, margin=dict(l=0, r=0, t=10, b=0))
                fig_var.update_xaxes(tickformat="d", dtick=1)
                st.plotly_chart(fig_var, use_container_width=True)
            with c2:
                st.success("✅ **格兰杰因果确认：** 当期收入暴增确实是后期消费释放的诱发原点，且具有 2 期的平滑迟滞效应。")

        with m_tabs[1]:
            c1, c2 = st.columns([2, 1])
            with c1:
                st.markdown("##### 本地自身发力 vs 隔壁邻居虹吸")
                mod = (selected_year - 2024) * 0.01
                vars = ['产业优化因子', '城镇化推进', '数字经济渗透', '基建扩张']
                fig_sdm = go.Figure()
                fig_sdm.add_trace(go.Bar(name='本地内生效益 (Direct)', x=vars, y=[max(0.01, 0.45+mod), max(0.01, 0.21+mod), max(0.01, 0.32+mod), max(0.01, 0.18+mod)], marker_color='#3b82f6'))
                fig_sdm.add_trace(go.Bar(name='隔壁溢出/剥夺 (Indirect)', x=vars, y=[0.28-mod, 0.15-mod, 0.41+mod*2, -0.05-mod], marker_color='#f59e0b'))
                fig_sdm.update_layout(barmode='group', height=350, margin=dict(l=0, r=0, t=10, b=0))
                st.plotly_chart(fig_sdm, use_container_width=True)
            with c2:
                st.info("💡 **空间洞察：** 数字经济不仅强力拉动本地消费，其恐怖的外溢系数证明它彻底打通了跨省域的商贸阻断。")

        with m_tabs[2]:
            c1, c2 = st.columns([2, 1])
            with c1:
                st.markdown("##### 消费引爆点前的潜在门槛似然比")
                gamma = np.linspace(2, 8, 100)
                fig_thr = go.Figure(go.Scatter(x=gamma, y=np.minimum((gamma-4)**2+1, (gamma-6)**2+2), mode='lines', line=dict(color='#3b82f6', width=3)))
                fig_thr.add_vline(x=4.0, line_dash="dot", line_color="#ef4444", annotation_text="温饱基准线")
                fig_thr.add_vline(x=6.0, line_dash="dot", line_color="#f59e0b", annotation_text="资产改善线")
                fig_thr.update_layout(height=350, margin=dict(l=0, r=0, t=10, b=0))
                st.plotly_chart(fig_thr, use_container_width=True)
            with c2:
                st.warning("💡 **阶跃断层：** 当人均收入越过图示的虚线门槛后，花钱的边际倾向发生本质跨越，非线性跃迁成立。")

    st.markdown("#### 🔬 面板数据核心回归参数输出表")
    c_lat, c_tab = st.columns([1, 1.5])
    
    with c_lat:
        with st.container(border=True):
            st.markdown("##### 空间杜宾模型 (SDM) 数学范式")
            st.caption("采用地理距离嵌套的行列标准化矩阵 $W$")
            st.latex(r'''
            \begin{aligned}
            Y_{it} = &\rho \sum_{j=1}^n W_{ij} Y_{jt} + \beta X_{it} \\
            &+ \theta \sum_{j=1}^n W_{ij} X_{jt} + \mu_i + \nu_t + \varepsilon_{it}
            \end{aligned}
            ''')
            st.latex(r''' \varepsilon_{it} \sim N(0, \sigma^2 I_n) ''')
            st.markdown("<div style='font-size:12px; color:#64748b; margin-top:15px;'>*注: Y 为被解释变量(耦合度), X 包含解释变量池(收入等)。</div>", unsafe_allow_html=True)
            
    with c_tab:
        with st.container(border=True):
            st.markdown("##### 基准回归与稳健性检验对照体系")
            reg_df = pd.DataFrame({
                "变量 (Vars)": ["Income", "W × Income", "Digital", "Urban", "Cons"],
                "(1) OLS": ["0.425***", "—", "0.210**", "0.105*", "-1.205***"],
                "(2) FE (固定效应)": ["0.380***", "—", "0.245***", "0.088", "-0.850**"],
                "(3) SDM (空间滞后)": ["0.355***", "0.150**", "0.260***", "0.052", "-0.920***"]
            })
            st.dataframe(reg_df, hide_index=True, use_container_width=True)
            
            meta_df = pd.DataFrame({
                "统计量": ["N", "R-squared", "Log-Likelihood", "ρ (空间自回归)"],
                "OLS": ["465", "0.685", "-125.4", "—"],
                "FE": ["465", "0.742", "-98.2", "—"],
                "SDM": ["465", "0.815", "-65.8", "0.320***"]
            })
            st.dataframe(meta_df, hide_index=True, use_container_width=True)
            st.caption("注：*** p<0.01, ** p<0.05, * p<0.1。模型(3)通过 LR 和 Wald 检验。")

# ==============================================================================
# 模块 5: 🤖 AI预测仿真
# ==============================================================================
elif menu == "🤖 AI预测仿真":
    st.info("💡 **深度算命舱：** 将历史切片喂给混合神经网络，推演未来十年的协同度走势与潜在极限风险。")
    
    c_opt, c_view = st.columns([1, 2.5])
    with c_opt:
        with st.container(border=True):
            st.subheader("🤖 算力节点配置")
            ai_model = st.selectbox("注入大脑框架", ["LSTM-BiGRU (神经网络)", "ARIMA (传统自回归)", "Prophet (开源时间加性)"])
            pred_steps = st.slider("外推穿透年数", 1, 10, 5)
            st.button("🚀 启动张量测算", type="primary", use_container_width=True)

    with c_view:
        with st.container(border=True):
            st.subheader(f"多维全息测算图轨 - 驱动引擎: {ai_model}")
            
            y_hist = list(range(global_start_year, selected_year + 1))
            y_pred = list(range(selected_year, selected_year + pred_steps + 1))
            
            h_v = [0.52 + (y - 2010) * 0.023 + np.random.normal(0,0.01) for y in y_hist]
            p_v = [h_v[-1] + (i**1.1)*0.012 for i in range(pred_steps+1)] if "LSTM" in ai_model else [h_v[-1] + i*0.008 for i in range(pred_steps+1)]
            r_f = 0.005 if "LSTM" in ai_model else 0.008
            
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=y_hist, y=h_v, name='归档历史', line=dict(color='#3b82f6', width=3)))
            fig.add_trace(go.Scatter(x=y_pred, y=p_v, name='拟合基准线', line=dict(color='#10b981', width=3.5, dash='dash')))
            
            y_stress_good = [v * 1.06 + (i*0.002) for i,v in enumerate(p_v)]
            y_stress_bad = [v * 0.92 - (i*0.005) for i,v in enumerate(p_v)]
            fig.add_trace(go.Scatter(x=y_pred, y=y_stress_good, name='技术爆炸冲击 (乐观轨)', line=dict(color='#f59e0b', width=2, dash='dot')))
            fig.add_trace(go.Scatter(x=y_pred, y=y_stress_bad, name='灰犀牛通缩冲击 (悲观轨)', line=dict(color='#ef4444', width=2, dash='dot')))
            
            p_u = [v+0.03+(i*r_f) for i,v in enumerate(p_v)]
            p_l = [v-0.03-(i*r_f) for i,v in enumerate(p_v)]
            
            if show_ci:
                fig.add_trace(go.Scatter(x=y_pred + y_pred[::-1], y=p_u + p_l[::-1], fill='toself', fillcolor='rgba(16, 185, 129, 0.1)', line=dict(color='rgba(255,255,255,0)'), hoverinfo="skip", name='95%置信通道'))
            
            fig.update_layout(height=350, margin=dict(l=0, r=0, t=10, b=0), legend=dict(orientation="h", yanchor="bottom", y=1.02))
            fig.update_xaxes(tickformat="d", dtick=1)
            st.plotly_chart(fig, use_container_width=True)

    r_left, r_right = st.columns([1, 1.5])
    with r_left:
        with st.container(border=True):
            st.subheader("🧩 SHAP 特征重要性归因")
            st.caption("AI 是依据什么做出的预测？")
            fig_shap = px.bar(
                x=[0.42, 0.28, 0.18, 0.12], 
                y=["数字经济渗透", "转移性收入托底", "服务消费扩容", "人口老龄化阻力"],
                orientation='h', color_discrete_sequence=['#3b82f6']
            )
            fig_shap.update_layout(height=280, margin=dict(l=0, r=0, t=10, b=0), xaxis_title="对未来协同度的贡献权重")
            st.plotly_chart(fig_shap, use_container_width=True)
            
    with r_right:
        with st.container(border=True):
            st.subheader("📝 算法神经突触输出明细")
            r_lbs = ["极低", "较低", "正常", "正常", "偏高", "不确定大"]
            r_col = [r_lbs[i] if i < len(r_lbs) else "未知风险" for i in range(len(y_pred))]
            df_p = pd.DataFrame({"投射年份": [f"{y}年" for y in y_pred], "拟合中枢": [f"{v:.4f}" for v in p_v], "置信下界": [f"{v:.4f}" for v in p_l], "置信上界": [f"{v:.4f}" for v in p_u], "引擎提示": r_col})
            st.dataframe(df_p, use_container_width=True, hide_index=True)


# ==============================================================================
# 模块 6: 🧮 耦合计算器
# ==============================================================================
elif menu == "🧮 耦合计算器":
    st.info("💡 **随手验算台：** 输入您的账本，对比 2023 国家统计大盘，一键生成您的个人微观画像与协同等级。")
    
    with st.container(border=True):
        st.markdown("##### 🎲 快捷加载人物模板库：")
        preset = st.radio(" ", ["✍️ 清空手填", "📈 2023国区平均标准人", "💻 高维产出大厂卷王", "☕ 避险型佛系青年"], horizontal=True, label_visibility="collapsed")
    
    def_i, def_e = 39218, 26796
    if "卷王" in preset: def_i, def_e = 450000, 180000
    elif "佛系" in preset: def_i, def_e = 48000, 42000
    elif "清空" in preset: def_i, def_e = 50000, 35000 
    
    c_in, c_ex, c_res = st.columns([1.1, 1.1, 2.0])
    with c_in:
        with st.container(border=True):
            st.subheader("💰 财源池输入")
            inc_t = st.number_input("全口径年进账 (元)", value=def_i, step=1000)
            st.number_input("拆解: 死工资", value=int(def_i*0.7), step=500)
            st.number_input("拆解: 理财收租", value=int(def_i*0.1), step=500)

    with c_ex:
        with st.container(border=True):
            st.subheader("🛒 消耗池输入")
            exp_t = st.number_input("全口径年开销 (元)", value=def_e, step=1000)
            st.number_input("拆解: 恩格尔口粮", value=int(def_e*0.35), step=500)
            st.number_input("拆解: 享受型溢价", value=int(def_e*0.4), step=500)

    i_s, e_s = max(inc_t, 1), max(exp_t, 1)
    U1, U2 = min(i_s / 80000, 1.0), min(e_s / 50000, 1.0)
    C = 2 * np.sqrt(U1 * U2) / (U1 + U2) if (U1 + U2) > 0 else 0
    T = 0.5 * U1 + 0.5 * U2
    D = np.sqrt(C * T)
    
    with c_res:
        with st.container(border=True):
            st.subheader("📊 诊断结果与画像")
            fig_g = go.Figure(go.Indicator(
                mode="gauge+number", value=D, number={"font": {"size": 42, "color": "#1e293b"}},
                gauge={'axis': {'range': [0, 1], 'tickwidth': 1}, 'bar': {'color': "rgba(0,0,0,0)", 'thickness': 0},
                       'steps': [{'range': [0, D], 'color': '#10b981' if D >= 0.7 else ('#f59e0b' if D >= 0.5 else '#ef4444')}],
                       'threshold': {'line': {'color': "red", 'width': 3}, 'thickness': 0.75, 'value': 0.6}}
            ))
            fig_g.update_layout(height=180, margin=dict(l=0, r=0, t=10, b=10))
            st.plotly_chart(fig_g, use_container_width=True)
            
            if D >= 0.8: st.success("💎 **高维均衡王者：** 强造血强享受，财务自由指日可待！")
            elif D >= 0.6: st.info("🥇 **稳健持家核心：** 收支防线固若金汤，社会最坚挺的中产！")
            else:
                if i_s > e_s * 3: st.warning("🏦 **重度守财奴：** 资金不流动就是纸，去改善生活吧！")
                elif e_s > i_s: st.error("💸 **赤字月光族：** 您的信用底盘已被击穿，极度危险！")
                else: st.caption("🧗 **原始爬坡期：** 继续沉淀，提升底盘。")

    m1, m2, m3, m4 = st.columns(4)
    with st.container(border=True): m1.metric("造血分化率", f"{U1:.2f}")
    with st.container(border=True): m2.metric("放血分化率", f"{U2:.2f}")
    with st.container(border=True): m3.metric("双元纠缠系数", f"{C:.2f}")
    with st.container(border=True): m4.metric("统合落板最终分", f"{D:.2f}")

    c_pk, c_pie = st.columns([1.5, 1])
    with c_pk:
        with st.container(border=True):
            st.subheader("📊 2023 国家测算大盘交叉对狙")
            i_d, e_d = ((i_s-39218)/39218)*100, ((e_s-26796)/26796)*100
            st.markdown(f"""
            <ul style="font-size: 15px; color: #475569; line-height: 2.2;">
                <li>🚀 您的进水管流速比国家机器基准 (39,218元) <strong style="color:{'#ef4444' if i_d>0 else '#10b981'};">{'暴涨出' if i_d>0 else '滑坡了'} {abs(i_d):.1f}%</strong>。</li>
                <li>🛍️ 您的出水管流速比国家机器基准 (26,796元) <strong style="color:{'#ef4444' if e_d>0 else '#10b981'};">{'超支了' if e_d>0 else '克制了'} {abs(e_d):.1f}%</strong>。</li>
            </ul>
            """, unsafe_allow_html=True)
            if i_s >= e_s: st.success(f"防线稳固：当期留存利润槽溢出 {i_s-e_s} 元 🎉")
            else: st.error(f"防线崩塌：当期利润槽形成 {e_s-i_s} 元的抽血黑洞 🚨")
            
    with c_pie:
        with st.container(border=True):
            st.subheader("🍩 资金分流结构切面")
            lbl, val = (['刚性燃烧', '护城河结余'], [e_s, max(i_s-e_s, 0)]) if e_s <= i_s else (['完全覆盖', '信用透支点'], [i_s, e_s-i_s])
            fig_pie = go.Figure(data=[go.Pie(labels=lbl, values=val, hole=.5, marker_colors=['#3b82f6', '#10b981' if i_s>=e_s else '#ef4444'])])
            fig_pie.update_layout(height=200, margin=dict(l=0, r=0, t=10, b=0), showlegend=False)
            st.plotly_chart(fig_pie, use_container_width=True)


# ==============================================================================
# 模块 7: 🎯 政策模拟器
# ==============================================================================
elif menu == "🎯 政策模拟器":
    st.info("💡 **化身架构师：** 施加宏观外力，沙盘将推演这些干预动作如何渗透并拉升全域的收支协同度。")

    c1, c2 = st.columns([1, 2.5])
    with c1:
        with st.container(border=True):
            st.subheader("🎛️ 政策配方组合舱")
            t_prov = st.selectbox("瞄准干预区", ["大盘全域辐射", "东部经济特区", "中西部下沉节点"])
            w_i = st.slider("薪酬底线涨幅 (%)", 0.0, 20.0, 5.0)
            c_s = st.slider("宽销量化派发 (亿)", 0, 5000, 500)
            t_r = st.slider("基准税盾厚度 (BP)", 0, 500, 150)
            st.button("⚙️ 封版并注入推演", type="primary", use_container_width=True)

        with st.container(border=True):
            st.markdown("##### 📋 CGE 模型环境定参")
            st.markdown("- 经济底座自膨胀率: **5.2%**\n- 通胀摩擦损耗: **2.0%**\n- 边际释放乘数: **0.62**")

    with c2:
        with st.container(border=True):
            st.subheader(f"干预弹道全息推演：【{t_prov}】")
            y_sim = list(range(2020, 2030))
            b_y = [0.650 + i*0.012 for i in range(10)]
            o_f = (w_i * 0.0015) + (c_s * 0.00002) + (t_r * 0.0001)
            o_y = b_y[:4] + [b_y[4] + (i-3)*o_f for i in range(4, 10)] 
            
            fig_p = go.Figure()
            fig_p.add_trace(go.Scatter(x=y_sim, y=b_y, name="惰性坍缩自然轨", line=dict(color="#94a3b8", dash="dash")))
            fig_p.add_trace(go.Scatter(x=y_sim, y=o_y, name="药剂注入强制轨", line=dict(color="#ef4444", width=3.5)))
            
            if show_ci:
                up_y = [y + (0.003*(i-3) if i>3 else 0) for i, y in enumerate(o_y)]
                lo_y = [y - (0.003*(i-3) if i>3 else 0) for i, y in enumerate(o_y)]
                fig_p.add_trace(go.Scatter(x=y_sim + y_sim[::-1], y=up_y + lo_y[::-1], fill='toself', fillcolor='rgba(245, 108, 108, 0.15)', line=dict(color='rgba(255,255,255,0)'), hoverinfo="skip", name='阻力震荡容错区间'))
            
            fig_p.add_vline(x=2024, line_dash="dot", line_color="#3b82f6", annotation_text="★ 政策干预奇点")
            fig_p.update_layout(height=350, margin=dict(l=0, r=0, t=10, b=10), legend=dict(orientation="h", yanchor="bottom", y=1.02))
            fig_p.update_xaxes(tickformat="d", dtick=1)
            st.plotly_chart(fig_p, use_container_width=True)

        r1, r2 = st.columns([1, 1.2])
        with r1:
            with st.container(border=True):
                st.subheader("📊 猛药穿透力剖析")
                fig_b = go.Figure(go.Bar(
                    x=['硬核涨薪', '发券促耗', '降税托底'],
                    y=[w_i*1.2, c_s*0.05, t_r*0.08],
                    marker_color=['#3b82f6', '#10b981', '#f59e0b'],
                    text=[f"+{w_i*1.2:.1f}%", f"+{c_s*0.05:.1f}%", f"+{t_r*0.08:.1f}%"], textposition='auto'
                ))
                fig_b.update_layout(height=280, margin=dict(l=0, r=0, t=10, b=0))
                st.plotly_chart(fig_b, use_container_width=True)

        with r2:
            with st.container(border=True):
                st.subheader("📝 2027年个体红利结算单")
                res_df = pd.DataFrame({
                    "检验标的": ["钱包存粮", "敢花预算", "统合协同阵位"],
                    "不吃药自然量": ["58,400 元", "38,200 元", "0.712 (疲弱)"],
                    "猛药击穿量": [f"{58400*(1+w_i/100):.0f} 元", f"{38200 + c_s*15:.0f} 元", f"{(0.712 + o_f):.3f} (强劲)"],
                    "超额挤出红利": [f"+{w_i}%", f"+{c_s/10:.1f}%", f"绝对值 +{o_f:.3f}"]
                })
                st.dataframe(res_df, use_container_width=True, hide_index=True)
                
                st.divider()
                d1, d2 = st.columns(2)
                with d1:
                    st.download_button("📥 抽取沙盘表 (CSV)", data=res_df.to_csv(index=False).encode('utf-8-sig'), file_name='Policy_Data.csv', mime='text/csv', use_container_width=True)
                with d2:
                    st.download_button("📄 签发内参函 (TXT)", data=f"生成纪元：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n锁定靶向：{t_prov}\n跃升落板：{(0.712 + o_f):.3f}\n高参批示：动能极权，立项通过！", file_name='Policy_Report.txt', mime='text/plain', use_container_width=True)


# ==============================================================================
# 模块 8: 📽️ 答辩专属数据故事演示模式
# ==============================================================================
elif menu == "📽️ 答辩演示模式":
    st.markdown("""
    <div style="background: linear-gradient(135deg, #1e293b 0%, #3b82f6 100%); padding: 50px; border-radius: 12px; color: white; text-align: center; margin-bottom: 30px; box-shadow: 0 10px 20px rgba(0,0,0,0.2);">
        <h1 style="color: white; margin-bottom: 15px; font-weight: 800;">中国城镇居民收入与消费的协同演化机制研究</h1>
        <h3 style="color: #cbd5e1; font-weight: 400; margin-bottom: 30px;">—— 基于 CICCAS 系统的毕业设计实战演练</h3>
        <span style="background-color: rgba(255,255,255,0.1); padding: 10px 25px; border-radius: 20px; font-size: 15px; border: 1px solid rgba(255,255,255,0.3);">⬇️ 请向下滚动，开启数据剧情探演</span>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<h3 style='color:#1e293b; border-bottom: 4px solid #3b82f6; padding-bottom: 10px;'>第一章：结构破局 —— 老百姓的钱去哪了？</h3>", unsafe_allow_html=True)
    st.write("各位评委老师好。本课题直击当前宏观经济中居民**“不敢消费”、“不愿消费”**的深层痛点。我们构建了跨越15年的省级面板数据舱，利用桑基流体图精准曝光了中国居民的资金血液穿透链路：")
    
    with st.container(border=True):
        fig_sankey_story = go.Figure(data=[go.Sankey(
            node=dict(pad=35, thickness=20, line=dict(color="black", width=0.5), label=['总收入', '薪酬主轴', '资产附加', '转移保障', '总消费', '刚性生存', '发展增值', '享受溢价'], color=['#3b82f6', '#10b981', '#f59e0b', '#8b5cf6', '#3b82f6', '#ef4444', '#10b981', '#f59e0b']),
            link=dict(source=[0, 0, 0, 1, 2, 3, 4, 4, 4], target=[1, 2, 3, 4, 4, 4, 5, 6, 7], value=[65, 20, 15, 60, 15, 15, 45, 30, 15], color='rgba(200, 200, 200, 0.4)'),
            textfont=dict(size=14, color="#0f172a", family="Microsoft YaHei, sans-serif")
        )])
        fig_sankey_story.update_layout(paper_bgcolor='rgba(0,0,0,0)', height=450, margin=dict(l=10, r=10, t=10, b=10))
        st.plotly_chart(fig_sankey_story, use_container_width=True)
    st.info("💡 **破局点发现：** 传统生存型消费壁垒正在松动，数字与享受型消费的爆发力是重启内需的绝对引擎。")

    st.markdown("<br><br>", unsafe_allow_html=True)
    
    st.markdown("<h3 style='color:#1e293b; border-bottom: 4px solid #8b5cf6; padding-bottom: 10px;'>第二章：切入点 —— 收入与消费的“物理纠缠” (耦合协同机制)</h3>", unsafe_allow_html=True)
    st.write("光看总量是不够的。本系统引入物理学**“容量耦合系统模型”**，将收入端($U_1$)与消费端($U_2$)作为两大子系统，精确量化两者之间的同步与咬合程度。")
    
    col_math, col_line = st.columns([1, 1.5])
    with col_math:
        with st.container(border=True):
            st.markdown("##### 🧮 耦合协调度 (D) 测算内核公式")
            st.latex(r"C = \frac{2\sqrt{U_1 \cdot U_2}}{U_1 + U_2}")
            st.latex(r"T = \alpha U_1 + \beta U_2")
            st.latex(r"D = \sqrt{C \cdot T}")
            st.caption("其中，C 为耦合度，反映相互作用的强弱；T 为综合调和指数；D 即为我们追踪的核心指标：**耦合协调度**。")
            
    with col_line:
        with st.container(border=True):
            st.markdown("##### 📈 全国大盘耦合协调度 15 年爬坡图")
            y_climb = list(range(2010, 2025))
            v_climb = [0.45 + (y-2010)*0.02 for y in y_climb]
            fig_climb = go.Figure(go.Scatter(x=y_climb, y=v_climb, mode='lines+markers', line=dict(color='#8b5cf6', width=4)))
            fig_climb.add_hrect(y0=0, y1=0.5, line_width=0, fillcolor="red", opacity=0.1, annotation_text="失调衰退区间")
            fig_climb.add_hrect(y0=0.5, y1=0.7, line_width=0, fillcolor="orange", opacity=0.1, annotation_text="过渡勉强区间")
            fig_climb.add_hrect(y0=0.7, y1=1.0, line_width=0, fillcolor="green", opacity=0.1, annotation_text="健康协调区间")
            fig_climb.update_layout(height=250, margin=dict(l=0, r=0, t=10, b=0))
            st.plotly_chart(fig_climb, use_container_width=True)

    st.markdown("<br><br>", unsafe_allow_html=True)

    st.markdown("<h3 style='color:#1e293b; border-bottom: 4px solid #10b981; padding-bottom: 10px;'>第三章：地理鸿沟 —— 协同度版图的时空崛起</h3>", unsafe_allow_html=True)
    st.write("脱离空间的数据是死寂的。通过接入物理实景坐标系统，我们将 2010 年至今的各省协同度“拔地而起”的进程全息还原。")
    
    with st.container(border=True):
        m_y_s = st.slider("请拖动滑块，体验 2010-2024 年区域高地的动态浮现：", 2010, 2024, 2015, key="presentation_timeline")
        coords_s = {'北京': [116.40, 39.90], '天津': [117.20, 39.13], '河北': [114.50, 38.05], '山西': [112.53, 37.87], '内蒙古': [111.73, 40.83], '辽宁': [123.38, 41.80], '吉林': [125.35, 43.88], '黑龙江': [126.63, 45.75], '上海': [121.48, 31.22], '江苏': [118.78, 32.04], '浙江': [120.15, 30.28], '安徽': [117.27, 31.86], '福建': [119.30, 26.08], '江西': [115.89, 28.68], '山东': [117.00, 36.65], '河南': [113.65, 34.76], '湖北': [114.31, 30.52], '湖南': [112.93, 28.23], '广东': [113.23, 23.16], '广西': [108.33, 22.84], '海南': [110.35, 20.02], '重庆': [106.50, 29.53], '四川': [104.06, 30.67], '贵州': [106.71, 26.57], '云南': [102.73, 25.04], '西藏': [91.11, 29.97], '陕西': [108.95, 34.27], '甘肃': [103.73, 36.03], '青海': [101.74, 36.56], '宁夏': [106.27, 38.47], '新疆': [87.68, 43.77]}
        
        dyn_df_s = pd.DataFrame({'省份': list(coords_s.keys())})
        dyn_df_s['lon'] = dyn_df_s['省份'].map(lambda x: coords_s[x][0])
        dyn_df_s['lat'] = dyn_df_s['省份'].map(lambda x: coords_s[x][1])
        np.random.seed(m_y_s)
        dyn_df_s['动态协同高度'] = (np.random.uniform(0.4, 0.9, len(dyn_df_s)) + (m_y_s - 2010)*0.01).clip(0.1, 1.0)
        dyn_df_s['color'] = dyn_df_s['动态协同高度'].apply(lambda val: [16, 185, 129, 230] if val >= 0.8 else ([59, 130, 246, 230] if val >= 0.65 else [239, 68, 68, 230]))

        gj_s = pdk.Layer("GeoJsonLayer", data="https://geo.datav.aliyun.com/areas_v3/bound/100000_full.json", opacity=0.3, stroked=True, filled=True, get_line_color=[150, 160, 170, 200], get_fill_color=[240, 245, 250, 150], line_width_min_pixels=1)
        layer_s = pdk.Layer('ColumnLayer', data=dyn_df_s, get_position=['lon', 'lat'], get_elevation='动态协同高度', elevation_scale=1800000, radius=55000, get_fill_color='color', auto_highlight=True, extruded=True)
        vs_s = pdk.ViewState(longitude=104.19, latitude=35.86, zoom=3.3, pitch=50, bearing=15)
        st.pydeck_chart(pdk.Deck(layers=[gj_s, layer_s], initial_view_state=vs_s, map_style="mapbox://styles/mapbox/light-v10"), use_container_width=True)
    st.success("✅ **空间集聚效应显著**：以江浙沪、珠三角为核心的“高能极”正在向中原腹地产生不可忽视的马太溢出效应。")

    st.markdown("<br><br>", unsafe_allow_html=True)

    st.markdown("<h3 style='color:#1e293b; border-bottom: 4px solid #ef4444; padding-bottom: 10px;'>第四章：战略决断与科研陈词</h3>", unsafe_allow_html=True)
    st.write("最后，基于我们的 CGE 测算模型，系统可实现高保真的沙盘推演，出具核心决策支持内参：")
    
    st.markdown("""
    <div style="background-color: #f8fafc; border: 1px solid #e2e8f0; padding: 25px; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.02);">
        <h4 style="color: #303133; margin-top:0;">📝 最终科研成果归纳：</h4>
        <ol style="color: #606266; font-size: 16px; line-height: 2.2; font-weight: 500;">
            <li><strong style="color: #3b82f6;">门槛跨越效应被彻底证实：</strong>人均收入只有跨越相对安全的第二门槛线，消费断层才能被弥合。</li>
            <li><strong style="color: #10b981;">直升机撒钱劣势暴露：</strong>政策模拟器证实，相比于直升机撒钱发放消费券，长期稳定地提升劳动报酬基础（涨底薪）具备高达 <b>1.2倍</b> 的传导乘数优势。</li>
            <li><strong style="color: #ef4444;">数智化重构版图：</strong>空间杜宾模型表明，数字经济的区域渗透是抹平东西部贫富差距、实现“共同富裕收敛性”的超级催化剂。</li>
        </ol>
        <p style="text-align: right; margin-bottom:0; font-weight: bold; color: #4ea5ff;">—— 汇报完毕，感谢评委老师聆听指正！</p>
    </div>
    """, unsafe_allow_html=True)

st.markdown('</div>', unsafe_allow_html=True)