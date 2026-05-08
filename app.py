import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import yfinance as yf
import numpy as np

# --- PAGE CONFIG ---
st.set_page_config(page_title="Institutional Flow Analytics", layout="wide", page_icon="📈")

st.title("📈 Institutional Flow & Macro Analytics")
st.markdown("Advanced structural tracking of FII & DII equity flows (2014 - Present)")

# --- DATA LOADER ---
@st.cache_data(ttl=3600)
def load_data():
    # 1. Load FII/DII CSV
    df = pd.read_csv('fii_dii_checkpoint.csv', encoding='utf-8-sig')
    df.columns = df.columns.str.strip().str.upper()
    df['DATE'] = pd.to_datetime(df['DATE'], errors='coerce')
    df = df.dropna(subset=['DATE'])

    # Clean numeric columns
    cols = ['FII_NET_PURCHASE_SALES', 'DII_NET_PURCHASE_SALES', 'TOTAL_NET']
    for col in cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', ''), errors='coerce')
    
    # Sort chronologically for accurate rolling calculations
    df = df.sort_values('DATE').reset_index(drop=True)

    # 2. Advanced CMT Calculations
    # Moving Averages
    df['FII_SMA_20'] = df['FII_NET_PURCHASE_SALES'].rolling(window=20).mean()
    df['DII_SMA_20'] = df['DII_NET_PURCHASE_SALES'].rolling(window=20).mean()
    
    # Cumulative "Dry Powder" (Total accumulated flow since 2014)
    df['CUMULATIVE_FII'] = df['FII_NET_PURCHASE_SALES'].cumsum()
    df['CUMULATIVE_DII'] = df['DII_NET_PURCHASE_SALES'].cumsum()
    
    # Z-Score (Standard Deviation from 60-day mean) to find extreme panic/euphoria
    fii_mean_60 = df['FII_NET_PURCHASE_SALES'].rolling(window=60).mean()
    fii_std_60 = df['FII_NET_PURCHASE_SALES'].rolling(window=60).std()
    df['FII_Z_SCORE'] = (df['FII_NET_PURCHASE_SALES'] - fii_mean_60) / fii_std_60

    # Absorption Ratio (DII Buying / FII Selling). Only calculate when FII is selling.
    df['ABSORPTION_RATIO'] = np.where(
        df['FII_NET_PURCHASE_SALES'] < 0, 
        abs(df['DII_NET_PURCHASE_SALES'] / df['FII_NET_PURCHASE_SALES']), 
        np.nan
    )

    # 3. Fetch Nifty 50 Data automatically
    try:
        start_date = df['DATE'].min().strftime('%Y-%m-%d')
        end_date = df['DATE'].max().strftime('%Y-%m-%d')
        nifty = yf.download('^NSEI', start=start_date, end=end_date, progress=False)
        nifty = nifty.reset_index()
        nifty['Date'] = pd.to_datetime(nifty['Date']).dt.tz_localize(None)
        
        # Merge Nifty data with our Flow data
        df = pd.merge(df, nifty[['Date', 'Close']], left_on='DATE', right_on='Date', how='left')
        df.rename(columns={'Close': 'NIFTY_50'}, inplace=True)
    except Exception as e:
        st.warning(f"Could not load Nifty 50 data: {e}")
        df['NIFTY_50'] = np.nan

    return df

try:
    data = load_data()

    # --- TOP METRICS DASHBOARD ---
    st.markdown("### 📊 Latest Market Session")
    latest = data.iloc[-1]
    
    # Format numbers cleanly
    fii_net = latest['FII_NET_PURCHASE_SALES']
    dii_net = latest['DII_NET_PURCHASE_SALES']
    total_net = latest['TOTAL_NET']
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("FII Net Flow", f"₹{fii_net:,.2f} Cr")
    col2.metric("DII Net Flow", f"₹{dii_net:,.2f} Cr")
    col3.metric("Total Net Inflow", f"₹{total_net:,.2f} Cr")
    
    if pd.notna(latest['NIFTY_50']):
        col4.metric("Nifty 50 (Close)", f"{float(latest['NIFTY_50']):,.2f}")
    else:
        col4.metric("Nifty 50", "Data Pending")

    st.markdown("---")

    # --- TIMEFRAME SELECTOR ---
    timeframes = {
        "1 Month": pd.DateOffset(months=1),
        "3 Months": pd.DateOffset(months=3),
        "6 Months": pd.DateOffset(months=6),
        "1 Year": pd.DateOffset(years=1),
        "3 Years": pd.DateOffset(years=3),
        "5 Years": pd.DateOffset(years=5),
        "Max (2014-Now)": None
    }
    
    selected_tf = st.radio("Select Analytical Timeframe:", options=list(timeframes.keys()), horizontal=True, index=3)

    # Filter data
    if timeframes[selected_tf] is not None:
        cutoff_date = data['DATE'].max() - timeframes[selected_tf]
        filtered_data = data[data['DATE'] >= cutoff_date]
    else:
        filtered_data = data

    # --- TABS FOR ORGANIZATION ---
    tab1, tab2, tab3 = st.tabs(["📉 Trend & Averages", "🏛️ Macro Context (Cumulative & Nifty)", "⚡ Statistical Extremes (Z-Score)"])

    # === TAB 1: TRENDS & AVERAGES ===
    with tab1:
        st.markdown("#### Moving Average Flow Analysis")
        st.caption("Displays raw daily flows with a 20-Day Simple Moving Average (SMA) to identify accelerating institutional support or distribution.")
        
        def create_trend_chart(df, y_col, sma_col, title, color):
            fig = go.Figure()
            # Daily Bars
            fig.add_trace(go.Bar(x=df['DATE'], y=df[y_col], name="Daily Flow", marker_color=color, opacity=0.4))
            # 20-Day SMA Line
            fig.add_trace(go.Scatter(x=df['DATE'], y=df[sma_col], mode='lines', name="20-Day SMA", line=dict(color=color, width=3)))
            
            fig.update_layout(title=title, hovermode="x unified", template="plotly_dark", height=350, margin=dict(b=0))
            return fig

        st.plotly_chart(create_trend_chart(filtered_data, 'FII_NET_PURCHASE_SALES', 'FII_SMA_20', 'FII Flows vs 20-Day SMA', '#00f2ff'), use_container_width=True)
        st.plotly_chart(create_trend_chart(filtered_data, 'DII_NET_PURCHASE_SALES', 'DII_SMA_20', 'DII Flows vs 20-Day SMA', '#ff4b4b'), use_container_width=True)


    # === TAB 2: MACRO CONTEXT ===
    with tab2:
        st.markdown("#### Cumulative Flow vs. Nifty 50 Correlation")
        st.caption("Tracks the 'inventory' of institutional money. Divergences between Cumulative FII flow and Nifty 50 price often signal structural market shifts.")
        
        fig_macro = make_subplots(specs=[[{"secondary_y": True}]])
        
        # Cumulative FII (Area Chart)
        fig_macro.add_trace(go.Scatter(
            x=filtered_data['DATE'], y=filtered_data['CUMULATIVE_FII'], 
            name="Cumulative FII", fill='tozeroy', line=dict(color='#00f2ff', width=1), opacity=0.3
        ), secondary_y=False)
        
        # Cumulative DII (Area Chart)
        fig_macro.add_trace(go.Scatter(
            x=filtered_data['DATE'], y=filtered_data['CUMULATIVE_DII'], 
            name="Cumulative DII", fill='tozeroy', line=dict(color='#ff4b4b', width=1), opacity=0.3
        ), secondary_y=False)

        # Nifty 50 (Line Chart on Secondary Axis)
        if 'NIFTY_50' in filtered_data.columns and not filtered_data['NIFTY_50'].isna().all():
            # Flatten the multi-index column if yfinance returned one
            nifty_series = filtered_data['NIFTY_50']
            if isinstance(nifty_series, pd.DataFrame):
                nifty_series = nifty_series.iloc[:, 0]
                
            fig_macro.add_trace(go.Scatter(
                x=filtered_data['DATE'], y=nifty_series, 
                name="Nifty 50", mode='lines', line=dict(color='#00ff88', width=2)
            ), secondary_y=True)

        fig_macro.update_layout(title="Structural Flow Correlation", template="plotly_dark", height=500, hovermode="x unified")
        fig_macro.update_yaxes(title_text="Cumulative Flow (₹ Cr)", secondary_y=False)
        fig_macro.update_yaxes(title_text="Nifty 50 Price", secondary_y=True)
        
        st.plotly_chart(fig_macro, use_container_width=True)


    # === TAB 3: STATISTICAL EXTREMES ===
    with tab3:
        st.markdown("#### Flow Extremes & Market Absorption")
        st.caption("A Z-Score of > 2 or < -2 indicates a statistically extreme buying/selling day. Absorption ratio > 1 means DIIs bought more than FIIs sold.")
        
        c1, c2 = st.columns(2)
        with c1:
            # Z-Score Chart
            fig_z = go.Figure()
            fig_z.add_trace(go.Bar(
                x=filtered_data['DATE'], y=filtered_data['FII_Z_SCORE'],
                name="FII Z-Score", marker_color=np.where(filtered_data['FII_Z_SCORE'] > 0, '#00f2ff', '#ff4b4b')
            ))
            # Add +2 and -2 Standard Deviation Lines
            fig_z.add_hline(y=2, line_dash="dash", line_color="red", annotation_text="+2 Std Dev (Euphoria)")
            fig_z.add_hline(y=-2, line_dash="dash", line_color="green", annotation_text="-2 Std Dev (Panic/Climax)")
            fig_z.update_layout(title="FII Flow Volatility (Z-Score)", template="plotly_dark", height=400)
            st.plotly_chart(fig_z, use_container_width=True)

        with c2:
            # Absorption Scatter
            fig_abs = go.Figure()
            # Only plot days where FII sold
            sell_days = filtered_data[filtered_data['FII_NET_PURCHASE_SALES'] < 0]
            fig_abs.add_trace(go.Scatter(
                x=sell_days['DATE'], y=sell_days['ABSORPTION_RATIO'],
                mode='markers', name="Absorption Ratio",
                marker=dict(size=6, color=np.where(sell_days['ABSORPTION_RATIO'] > 1, '#00ff88', 'gray'))
            ))
            fig_abs.add_hline(y=1, line_dash="dot", line_color="white", annotation_text="1.0 (Full Absorption)")
            fig_abs.update_layout(title="DII Absorption Ratio (On FII Sell Days)", template="plotly_dark", height=400, yaxis=dict(range=[0, 3]))
            st.plotly_chart(fig_abs, use_container_width=True)

    st.markdown("---")
    with st.expander("View Underlying Data Structure"):
        st.dataframe(filtered_data.sort_values('DATE', ascending=False), use_container_width=True)

except Exception as e:
    st.error(f"Error loading systems: {e}")
