import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime

# --- 1. 页面设置（适应手机屏） ---
st.set_page_config(
    page_title="纳斯达克100与情绪监控",
    page_icon="📈",
    layout="centered"
)

# 自定义卡片样式（模仿原生App）
st.markdown("""
    <style>
    .metric-card {
        background-color: #f8f9fa;
        border-radius: 12px;
        padding: 14px;
        margin-bottom: 12px;
        border: 2px solid #e9ecef;
    }
    .status-triggered { border-color: #28a745 !important; background-color: #e8f5e9 !important; }
    .status-warning { border-color: #ffc107 !important; background-color: #fffde7 !important; }
    .status-normal { border-color: #e0e0e0 !important; }
    
    .badge-green { color: #28a745; font-weight: bold; float: right; }
    .badge-yellow { color: #d39e00; font-weight: bold; float: right; }
    .badge-gray { color: #6c757d; float: right; }
    
    .card-title { font-size: 14px; color: #6c757d; font-weight: 600; }
    .card-value { font-size: 26px; font-weight: bold; margin: 6px 0; }
    .card-desc { font-size: 12px; color: #495057; line-height: 1.4; }
    </style>
""", unsafe_allow_html=True)

# --- 2. 获取数据函数（带缓存防止刷新频繁） ---
@st.cache_data(ttl=1800) # 缓存30分钟
def get_data():
    # 抓取 QQQ(纳指100ETF), SPY(标普500ETF), ^VIX(恐慌指数)
    tickers = yf.download(['QQQ', 'SPY', '^VIX'], period='1y', interval='1d')['Close']
    
    vix = float(tickers['^VIX'].iloc[-1])
    qqq = tickers['QQQ']
    spy = tickers['SPY']
    
    # 算 RSI (6日)
    delta = qqq.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=6).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=6).mean()
    rs = gain / loss
    rsi_6 = float((100 - (100 / (1 + rs))).iloc[-1])

    # 算 52周回撤
    qqq_high = float(qqq.max())
    qqq_dd = float(((qqq.iloc[-1] - qqq_high) / qqq_high) * 100)
    spy_high = float(spy.max())
    spy_dd = float(((spy.iloc[-1] - spy_high) / spy_high) * 100)

    # 算 25日急跌
    qqq_25d = float(qqq.iloc[-25]) if len(qqq) >= 25 else float(qqq.iloc[0])
    qqq_chg = float(((qqq.iloc[-1] - qqq_25d) / qqq_25d) * 100)
    
    spy_25d = float(spy.iloc[-25]) if len(spy) >= 25 else float(spy.iloc[0])
    spy_chg = float(((spy.iloc[-1] - spy_25d) / spy_25d) * 100)

    return {
        "vix": vix,
        "rsi": rsi_6,
        "qqq_dd": qqq_dd,
        "spy_dd": spy_dd,
        "qqq_chg": qqq_chg,
        "spy_chg": spy_chg
    }

# --- 3. 页面内容渲染 ---
st.title("美股估值与情绪监控看板")
st.caption(f"📅 数据更新时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}")

# 卡片生成器
def make_card(title, value, status, badge, lines):
    cls = f"status-{status}"
    b_cls = f"badge-{'green' if status=='triggered' else 'yellow' if status=='warning' else 'gray'}"
    desc = "<br>".join(lines)
    st.markdown(f"""
    <div class="metric-card {cls}">
        <span class="{b_cls}">{badge}</span>
        <div class="card-title">{title}</div>
        <div class="card-value">{value}</div>
        <div class="card-desc">{desc}</div>
    </div>
    """, unsafe_allow_html=True)

try:
    data = get_data()

    st.subheader("🚨 极端买入信号监控")
    st.caption("🟢 **触发**（极端买入） | 🟡 **接近**（观察区） | ⚪ **未触发**")

    c1, c2 = st.columns(2)

    with c1:
        # VIX 卡片
        v = data['vix']
        v_st = "triggered" if v > 30 else ("warning" if v > 25 else "normal")
        v_bg = "触发 🟢" if v > 30 else ("接近 🟡" if v > 25 else "未触发")
        make_card("VIX 恐慌指数", f"{v:.2f}", v_st, v_bg, [
            "VIX: " + ("恐慌" if v > 30 else "正常"),
            "触发条件: > 30",
            "来源: CBOE"
        ])

        # RSI 卡片
        r = data['rsi']
        r_st = "triggered" if r < 22 else ("warning" if r < 30 else "normal")
        r_bg = "触发 🟢" if r < 22 else ("接近 🟡" if r < 30 else "未触发")
        make_card("RSI(6日)", f"{r:.1f}", r_st, r_bg, [
            "RSI: " + ("超卖" if r < 22 else "正常"),
            "触发条件: < 22",
            "标的: 纳指100(QQQ)"
        ])

    with c2:
        # 回撤卡片
        d = data['qqq_dd']
        d_st = "triggered" if d <= -20 else ("warning" if d <= -12 else "normal")
        d_bg = "触发 🟢" if d <= -20 else ("接近 🟡" if d <= -12 else "未触发")
        make_card("52周回撤", f"{d:.2f}%", d_st, d_bg, [
            "回撤: " + ("重度" if d <= -20 else "正常/中度"),
            "触发条件: ≤ -20%",
            f"纳指:{d:.2f}% | 标普:{data['spy_dd']:.2f}%"
        ])

        # 急跌卡片
        c = data['qqq_chg']
        c_st = "triggered" if c <= -12 else ("warning" if c <= -8 else "normal")
        c_bg = "触发 🟢" if c <= -12 else ("接近 🟡" if c <= -8 else "未触发")
        make_card("25日急跌", f"{c:.2f}%", c_st, c_bg, [
            "状态: " + ("极端" if c <= -12 else "正常"),
            "触发条件: ≤ -12%",
            f"纳指:{c:.2f}% | 标普:{data['spy_chg']:.2f}%"
        ])

except Exception as e:
    st.error("数据加载中或请求超时，请稍后重试。")

if st.button("🔄 刷新最新数据", use_container_width=True):
    st.cache_data.clear()
    st.rerun()
