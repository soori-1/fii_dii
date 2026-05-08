import streamlit as st
import pandas as pd
import plotly.graph_objects as go

st.set_page_config(page_title="FII/DII Flow Tracker", layout="wide")

st.title("📊 Institutional Equity Flows (2014 - Present)")

@st.cache_data(ttl=3600)
def load_data():
    # 'utf-8-sig' handles the hidden characters (BOM) often found in Excel-made CSVs
    # If this fails, try 'cp1252'
    df = pd.read_csv('fii_dii_checckpoint.csv', encoding='utf-8-sig')
    
    # Standardize column names: Strip spaces and make Uppercase
    df.columns = df.columns.str.strip().str.upper()
    
    # Convert DATE column
    df['DATE'] = pd.to_datetime(df['DATE'], errors='coerce')
    
    # Drop rows where DATE couldn't be parsed
    df = df.dropna(subset=['DATE'])

    # Clean the numeric columns (Removing commas like -3,621.60)
    # We use the exact names from your screenshot (now uppercase)
    cols = ['FII_NET_PURCHASE_SALES', 'DII_NET_PURCHASE_SALES', 'TOTAL_NET']
    for col in cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', ''), errors='coerce')
    
    return df.sort_values('DATE')

try:
    data = load_data()

    # --- Metrics Section ---
    latest = data.iloc[-1]
    m1, m2, m3 = st.columns(3)
    # We use the clean uppercase names here
    m1.metric("Latest FII Net", f"₹{latest['FII_NET_PURCHASE_SALES']:,.2f} Cr")
    m2.metric("Latest DII Net", f"₹{latest['DII_NET_PURCHASE_SALES']:,.2f} Cr")
    m3.metric("Total Net Flow", f"₹{latest['TOTAL_NET']:,.2f} Cr")

    # --- Charts ---
    fig = go.Figure()
    
    # FII Line
    fig.add_trace(go.Scatter(
        x=data['DATE'], 
        y=data['FII_NET_PURCHASE_SALES'], 
        name="FII Net", 
        line=dict(color='#00f2ff', width=1.5)
    ))
    
    # DII Line
    fig.add_trace(go.Scatter(
        x=data['DATE'], 
        y=data['DII_NET_PURCHASE_SALES'], 
        name="DII Net", 
        line=dict(color='#ff4b4b', width=1.5)
    ))
    
    # Total Net Bars
    fig.add_trace(go.Bar(
        x=data['DATE'], 
        y=data['TOTAL_NET'], 
        name="Total Net Inflow", 
        marker_color='gray',
        opacity=0.3
    ))

    fig.update_layout(
        title="Daily Institutional Flows",
        xaxis_title="Timeline",
        yaxis_title="Amount (₹ Crores)",
        hovermode="x unified",
        template="plotly_dark"
    )
    
    st.plotly_chart(fig, use_container_width=True)

    # Raw Data View
    with st.expander("View Raw Data Table"):
        st.dataframe(data.sort_values('DATE', ascending=False), use_container_width=True)

except Exception as e:
    st.error(f"Error loading data: {e}")
    # This "Debug" section will help us see if the file is loaded but headers are wrong
    if 'df' in locals() or 'df' in globals():
        st.write("Columns found in your file:", list(df.columns))
