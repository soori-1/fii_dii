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

    # --- SIDEBAR SETTINGS ---
    with st.sidebar:
        st.markdown("### 🛠️ Data Settings")
        # Added 'Yearly Aggregated' option
        view_mode = st.radio("Select View Mode:", ["Daily View", "Monthly Aggregated", "Yearly Aggregated"], index=0)
        
        st.markdown("---")
        st.write(f"**Rows in CSV:** {raw_count}")
        st.write(f"**Rows Plotted:** {parsed_count}")

    # --- DATA PROCESSING FOR VIEWS ---
    if view_mode == "Yearly Aggregated":
        # Aggregate by Year
        plot_df = data.set_index('DATE').resample('YE').sum().reset_index()
        plot_df['DISPLAY_DATE'] = plot_df['DATE'].dt.strftime('%Y')
        sma_window = 2 # 2-year average
    elif view_mode == "Monthly Aggregated":
        # Aggregate by Month
        plot_df = data.set_index('DATE').resample('ME').sum().reset_index()
        plot_df['DISPLAY_DATE'] = plot_df['DATE'].dt.strftime('%b %Y')
        sma_window = 3 # 3-month average
    else:
        # Daily View
        plot_df = data.copy()
        plot_df['DISPLAY_DATE'] = plot_df['DATE'].dt.strftime('%d %b %y')
        sma_window = 20 # 20-day average

    # Calculate SMAs on the processed dataframe
    plot_df['FII_SMA'] = plot_df['FII_NET_PURCHASE_SALES'].rolling(window=sma_window).mean()
    plot_df['DII_SMA'] = plot_df['DII_NET_PURCHASE_SALES'].rolling(window=sma_window).mean()
    plot_df['TOTAL_SMA'] = plot_df['TOTAL_NET'].rolling(window=sma_window).mean()
    
    # Statistical Calcs (Z-Score) - Standardized for each view mode
    fii_mean = plot_df['FII_NET_PURCHASE_SALES'].rolling(window=60 if view_mode == "Daily View" else 12).mean()
    fii_std = plot_df['FII_NET_PURCHASE_SALES'].rolling(window=60 if view_mode == "Daily View" else 12).std()
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
    # We disable small timeframes if 'Yearly' is selected to avoid empty graphs
    if view_mode == "Yearly Aggregated":
        tf_options = ["Max"]
        default_idx = 0
    else:
        tf_options = ["1 Month", "3 Months", "6 Months", "1 Year", "3 Years", "5 Years", "Max"]
        default_idx = 6

    timeframes = {
        "1 Month": pd.DateOffset(months=1),
        "3 Months": pd.DateOffset(months=3),
        "6 Months": pd.DateOffset(months=6),
        "1 Year": pd.DateOffset(years=1),
        "3 Years": pd.DateOffset(years=3),
        "5 Years": pd.DateOffset(years=5),
        "Max": None
    }
    
    selected_tf = st.radio("Select Timeframe:", options=tf_options, horizontal=True, index=default_idx)

    if timeframes[selected_tf] is not None:
        cutoff = plot_df['DATE'].max() - timeframes[selected_tf]
        filtered_df = plot_df[plot_df['DATE'] >= cutoff]
    else:
        filtered_df = plot_df

    # --- TABS ---
    tab1, tab2 = st.tabs(["📉 Trend & Averages", "⚡ Statistical Extremes"])

    with tab1:
        def create_trend_chart(df, y_col, sma_col, title, color):
            fig = go.Figure()
            # Bars
            fig.add_trace(go.Bar(
                x=df['DISPLAY_DATE'], 
                y=df[y_col], 
                name="Net Flow", 
                marker_color=color, 
                opacity=0.4
            ))
            # Average Line (Hidden if there isn't enough data for Yearly SMA)
            if not df[sma_col].isnull().all():
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
                    type='category', 
                    categoryorder='array',
                    categoryarray=df['DISPLAY_DATE'],
                    nticks=20
                )
            )
            return fig

        st.plotly_chart(create_trend_chart(filtered_df, 'FII_NET_PURCHASE_SALES', 'FII_SMA', 'FII Flows', '#00f2ff'), use_container_width=True)
        st.plotly_chart(create_trend_chart(filtered_df, 'DII_NET_PURCHASE_SALES', 'DII_SMA', 'DII Flows', '#ff4b4b'), use_container_width=True)
        st.plotly_chart(create_trend_chart(filtered_df, 'TOTAL_NET', 'TOTAL_SMA', 'Combined Total Flows', '#00ff88'), use_container_width=True)

    with tab2:
        st.markdown("#### Flow Extremes & Market Absorption")
        # Z-Score and Absorption Logic (Handles low data points in Yearly mode gracefully)
        if len(filtered_df) > 1:
            c1, c2 = st.columns(2)
            with c1:
                fig_z = go.Figure()
                fig_z.add_trace(go.Bar(
                    x=filtered_df['DISPLAY_DATE'], y=filtered_df['FII_Z_SCORE'],
                    name="FII Z-Score", marker_color=np.where(filtered_df['FII_Z_SCORE'] > 0, '#00f2ff', '#ff4b4b')
                ))
                fig_z.update_layout(title="FII Z-Score (Volatility)", template="plotly_dark", xaxis=dict(type='category', nticks=10))
                st.plotly_chart(fig_z, use_container_width=True)

            with c2:
                sell_days = filtered_df[filtered_df['FII_NET_PURCHASE_SALES'] < 0]
                if not sell_days.empty:
                    fig_abs = go.Figure()
                    fig_abs.add_trace(go.Scatter(
                        x=sell_days['DISPLAY_DATE'], y=sell_days['ABSORPTION_RATIO'],
                        mode='markers', marker=dict(size=12, color=np.where(sell_days['ABSORPTION_RATIO'] > 1, '#00ff88', 'gray'))
                    ))
                    fig_abs.add_hline(y=1, line_dash="dot", line_color="white")
                    fig_abs.update_layout(title="DII Absorption Ratio", template="plotly_dark", yaxis=dict(range=[0, 3]), xaxis=dict(type='category', nticks=10))
                    st.plotly_chart(fig_abs, use_container_width=True)
                else:
                    st.info("No net selling periods found in current selection for absorption analysis.")
        else:
            st.info("Not enough data points in the current view to calculate statistical extremes.")

except Exception as e:
    st.error(f"Error in system execution: {e}")
