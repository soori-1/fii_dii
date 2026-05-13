import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import numpy as np

# --- PAGE CONFIG ---
st.set_page_config(page_title="Institutional Flow Analytics", layout="wide", page_icon="📈")

st.title("📈 Institutional Flow & Macro Analytics")
st.markdown("Advanced structural tracking of FII & DII equity flows (2014 - Present)")

# --- DATA LOADER ---
@st.cache_data(ttl=60)
def load_data():
    df = pd.read_csv('fii_dii_checkpoint.csv', encoding='utf-8-sig')
    df.columns = df.columns.str.strip().str.upper()
    
    raw_rows = len(df)
    
    # Robust date parsing for mixed formats
    df['DATE'] = pd.to_datetime(df['DATE'], format='mixed', dayfirst=True, errors='coerce')
    df = df.dropna(subset=['DATE'])
    parsed_rows = len(df)

    # Clean numeric columns
    cols = ['FII_NET_PURCHASE_SALES', 'DII_NET_PURCHASE_SALES', 'TOTAL_NET']
    for col in cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', ''), errors='coerce')
    
    df = df.sort_values('DATE').reset_index(drop=True)
    return df, raw_rows, parsed_rows

try:
    data, raw_count, parsed_count = load_data()

    # --- SIDEBAR DIAGNOSTICS ---
    with st.sidebar:
        st.markdown("### 🛠️ Data Settings")
        # Feature 2: View Mode Selection
        view_mode = st.radio("Select View Mode:", ["Daily View", "Monthly Aggregated"], index=0)
        
        st.markdown("---")
        st.write(f"**Rows in CSV:** {raw_count}")
        st.write(f"**Rows Plotted:** {parsed_count}")

    # --- DATA PROCESSING FOR VIEWS ---
    if view_mode == "Monthly Aggregated":
        # Aggregate by Month-Year and sum the flows
        plot_df = data.set_index('DATE').resample('ME').sum().reset_index()
        # Format date for cleaner x-axis labels in monthly view
        plot_df['DISPLAY_DATE'] = plot_df['DATE'].dt.strftime('%b %Y')
        sma_window = 3 # 3-month average for monthly view
    else:
        plot_df = data.copy()
        # Format date for daily view
        plot_df['DISPLAY_DATE'] = plot_df['DATE'].dt.strftime('%d %b %y')
        sma_window = 20 # 20-day average for daily view

    # Calculate SMAs on the processed dataframe
    plot_df['FII_SMA'] = plot_df['FII_NET_PURCHASE_SALES'].rolling(window=sma_window).mean()
    plot_df['DII_SMA'] = plot_df['DII_NET_PURCHASE_SALES'].rolling(window=sma_window).mean()
    plot_df['TOTAL_SMA'] = plot_df['TOTAL_NET'].rolling(window=sma_window).mean()
    
    # Statistical Calcs (Z-Score)
    fii_mean = plot_df['FII_NET_PURCHASE_SALES'].rolling(window=60).mean()
    fii_std = plot_df['FII_NET_PURCHASE_SALES'].rolling(window=60).std()
    plot_df['FII_Z_SCORE'] = (plot_df['FII_NET_PURCHASE_SALES'] - fii_mean) / fii_std
    plot_df['ABSORPTION_RATIO'] = np.where(plot_df['FII_NET_PURCHASE_SALES'] < 0, abs(plot_df['DII_NET_PURCHASE_SALES'] / plot_df['FII_NET_PURCHASE_SALES']), np.nan)

    # --- TOP METRICS ---
    st.markdown(f"### 📊 Latest {view_mode} Summary")
    latest = plot_df.iloc[-1]
    col1, col2, col3 = st.columns(3)
    col1.metric("FII Net", f"₹{latest['FII_NET_PURCHASE_SALES']:,.2f} Cr")
    col2.metric("DII Net", f"₹{latest['DII_NET_PURCHASE_SALES']:,.2f} Cr")
    col3.metric("Total Net", f"₹{latest['TOTAL_NET']:,.2f} Cr")

    # --- TIMEFRAME SELECTOR ---
    timeframes = {
        "1 Month": pd.DateOffset(months=1),
        "3 Months": pd.DateOffset(months=3),
        "6 Months": pd.DateOffset(months=6),
        "1 Year": pd.DateOffset(years=1),
        "3 Years": pd.DateOffset(years=3),
        "5 Years": pd.DateOffset(years=5),
        "Max": None
    }
    selected_tf = st.radio("Select Timeframe:", options=list(timeframes.keys()), horizontal=True, index=3)

    if timeframes[selected_tf] is not None:
        cutoff = plot_df['DATE'].max() - timeframes[selected_tf]
        filtered_df = plot_df[plot_df['DATE'] >= cutoff]
    else:
        filtered_df = plot_df

    # --- TABS ---
    tab1, tab2 = st.tabs(["📉 Trend & Averages", "⚡ Statistical Extremes"])

    with tab1:
        # Feature 1: chart function with Gap Removal (type='category')
        def create_trend_chart(df, y_col, sma_col, title, color):
            fig = go.Figure()
            # Daily/Monthly Bars
            fig.add_trace(go.Bar(
                x=df['DISPLAY_DATE'], 
                y=df[y_col], 
                name="Net Flow", 
                marker_color=color, 
                opacity=0.4
            ))
            # Average Line
            fig.add_trace(go.Scatter(
                x=df['DISPLAY_DATE'], 
                y=df[sma_col], 
                mode='lines', 
                name=f"{sma_window} Period Avg", 
                line=dict(color=color, width=3)
            ))
            
            fig.update_layout(
                title=title, 
                hovermode="x unified", 
                template="plotly_dark", 
                height=350,
                xaxis=dict(
                    type='category', # THIS REMOVES THE SPACES (WEEKENDS/HOLIDAYS)
                    categoryorder='array',
                    categoryarray=df['DISPLAY_DATE'],
                    nticks=20 # Keeps the axis readable
                )
            )
            return fig

        st.plotly_chart(create_trend_chart(filtered_df, 'FII_NET_PURCHASE_SALES', 'FII_SMA', 'FII Flows', '#00f2ff'), use_container_width=True)
        st.plotly_chart(create_trend_chart(filtered_df, 'DII_NET_PURCHASE_SALES', 'DII_SMA', 'DII Flows', '#ff4b4b'), use_container_width=True)
        st.plotly_chart(create_trend_chart(filtered_df, 'TOTAL_NET', 'TOTAL_SMA', 'Combined Total Flows', '#00ff88'), use_container_width=True)

    with tab2:
        # Z-Score and Absorption Charts using the same filtered_df and category axis
        st.markdown("#### Flow Extremes & Market Absorption")
        c1, c2 = st.columns(2)
        with c1:
            fig_z = go.Figure()
            fig_z.add_trace(go.Bar(
                x=filtered_df['DISPLAY_DATE'], y=filtered_df['FII_Z_SCORE'],
                name="FII Z-Score", marker_color=np.where(filtered_df['FII_Z_SCORE'] > 0, '#00f2ff', '#ff4b4b')
            ))
            fig_z.add_hline(y=2, line_dash="dash", line_color="red")
            fig_z.add_hline(y=-2, line_dash="dash", line_color="green")
            fig_z.update_layout(title="FII Z-Score (Volatility)", template="plotly_dark", xaxis=dict(type='category', nticks=10))
            st.plotly_chart(fig_z, use_container_width=True)

        with c2:
            sell_days = filtered_df[filtered_df['FII_NET_PURCHASE_SALES'] < 0]
            fig_abs = go.Figure()
            fig_abs.add_trace(go.Scatter(
                x=sell_days['DISPLAY_DATE'], y=sell_days['ABSORPTION_RATIO'],
                mode='markers', marker=dict(size=8, color=np.where(sell_days['ABSORPTION_RATIO'] > 1, '#00ff88', 'gray'))
            ))
            fig_abs.add_hline(y=1, line_dash="dot", line_color="white")
            fig_abs.update_layout(title="DII Absorption Ratio", template="plotly_dark", yaxis=dict(range=[0, 3]), xaxis=dict(type='category', nticks=10))
            st.plotly_chart(fig_abs, use_container_width=True)

except Exception as e:
    st.error(f"Error in system execution: {e}")
