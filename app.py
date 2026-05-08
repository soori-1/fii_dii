import streamlit as st
import pandas as pd
import plotly.graph_objects as go

# Page Config
st.set_page_config(page_title="FII/DII Flow Tracker", layout="wide")

st.title("📊 Institutional Equity Flows (2014 - Present)")
st.subheader("FII & DII Net Inflow Analysis")

# Load Data
@st.cache_data(ttl=3600)
def load_data():
    # 1. Load with encoding fix
    df = pd.read_csv('FII_DII_Daily_Data_2014_to_Today.csv', encoding='cp1252')
    
    # 2. Clean Column Names (The "Secret Sauce")
    # This turns '  Date ' or 'date' into 'DATE'
    df.columns = df.columns.str.strip().str.upper()
    
    # 3. Convert Date
    # We now look for 'DATE' because we capitalized everything above
    df['DATE'] = pd.to_datetime(df['DATE'])
    
    # 4. Clean Numeric Columns
    # Adjust names here to match the capitalized version
    cols_to_fix = ['FII_NET_PURCHASE_SALES', 'DII_NET_PURCHASE_SALES']
    for col in cols_to_fix:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', ''), errors='coerce')
    
    # 5. Calculate Total
    df['TOTAL_NET'] = df['FII_NET_PURCHASE_SALES'] + df['DII_NET_PURCHASE_SALES']
    
    return df.sort_values('DATE')

try:
    data = load_data()

    # --- Metrics Section ---
    latest = data.iloc[-1]
    m1, m2, m3 = st.columns(3)
    m1.metric("Latest FII Net", f"₹{latest['FII_Net_Purchase_Sales']:.2f} Cr")
    m2.metric("Latest DII Net", f"₹{latest['DII_Net_Purchase_Sales']:.2f} Cr")
    m3.metric("Total Net Flow", f"₹{latest['Total_Net']:.2f} Cr")

    # --- Charts ---
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=data['DATE'], y=data['FII_Net_Purchase_Sales'], name="FII Net", line=dict(color='#00f2ff')))
    fig.add_trace(go.Scatter(x=data['DATE'], y=data['DII_Net_Purchase_Sales'], name="DII Net", line=dict(color='#ff4b4b')))
    fig.add_trace(go.Bar(x=data['DATE'], y=data['Total_Net'], name="Total Net Inflow", opacity=0.3))

    fig.update_layout(title="Daily Institutional Flows", xaxis_title="Year", yaxis_title="Amount (Cr)", hovermode="x unified")
    st.plotly_chart(fig, use_container_width=True)

    # Show Raw Data
    if st.checkbox("Show Raw Data"):
        st.dataframe(data.tail(100), use_container_width=True)

except Exception as e:
    st.error(f"Waiting for data file... Ensure the CSV is in the repository. Error: {e}")
