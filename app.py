import streamlit as st
import pandas as pd
import plotly.graph_objects as go

# Page Config
st.set_page_config(page_title="FII/DII Flow Tracker", layout="wide")

st.title("📊 Institutional Equity Flows (2014 - Present)")
st.subheader("FII & DII Net Inflow Analysis")

# Load Data
@st.cache_data(ttl=3600) # Refreshes every hour
def load_data():
    df = pd.read_csv('FII_DII_Daily_Data_2014_to_Today.csv')
    
    # Convert dates and clean numeric columns
    df['Date'] = pd.to_datetime(df['Date'])
    cols_to_fix = ['FII_Net_Purchase_Sales', 'DII_Net_Purchase_Sales']
    for col in cols_to_fix:
        df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', ''), errors='coerce')
    
    # Calculate Total Net Inflow
    # $$\text{Total Net Inflow} = \text{FII Net} + \text{DII Net}$$
    df['Total_Net'] = df['FII_Net_Purchase_Sales'] + df['DII_Net_Purchase_Sales']
    return df.sort_values('Date')

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
    fig.add_trace(go.Scatter(x=data['Date'], y=data['FII_Net_Purchase_Sales'], name="FII Net", line=dict(color='#00f2ff')))
    fig.add_trace(go.Scatter(x=data['Date'], y=data['DII_Net_Purchase_Sales'], name="DII Net", line=dict(color='#ff4b4b')))
    fig.add_trace(go.Bar(x=data['Date'], y=data['Total_Net'], name="Total Net Inflow", opacity=0.3))

    fig.update_layout(title="Daily Institutional Flows", xaxis_title="Year", yaxis_title="Amount (Cr)", hovermode="x unified")
    st.plotly_chart(fig, use_container_width=True)

    # Show Raw Data
    if st.checkbox("Show Raw Data"):
        st.dataframe(data.tail(100), use_container_width=True)

except Exception as e:
    st.error(f"Waiting for data file... Ensure the CSV is in the repository. Error: {e}")
