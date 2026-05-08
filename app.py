import streamlit as st
import pandas as pd
import plotly.graph_objects as go

st.set_page_config(page_title="FII/DII Flow Tracker", layout="wide")

st.title("📊 Institutional Equity Flows (2014 - Present)")

@st.cache_data(ttl=3600)
def load_data():
    # 'utf-8-sig' handles the hidden characters (BOM) often found in Excel-made CSVs
    # If this fails, try 'cp1252'
    df = pd.read_csv('fii_dii_checkpoint.csv', encoding='utf-8-sig')
    
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
    m1.metric("Latest FII Net", f"₹{latest['FII_NET_PURCHASE_SALES']:,.2f} Cr")
    m2.metric("Latest DII Net", f"₹{latest['DII_NET_PURCHASE_SALES']:,.2f} Cr")
    m3.metric("Total Net Flow", f"₹{latest['TOTAL_NET']:,.2f} Cr")

    st.markdown("---")

    # --- Timeframe Selector ---
    # Dictionary mapping UI labels to Pandas DateOffsets
    timeframes = {
        "1 Month": pd.DateOffset(months=1),
        "3 Months": pd.DateOffset(months=3),
        "6 Months": pd.DateOffset(months=6),
        "1 Year": pd.DateOffset(years=1),
        "3 Years": pd.DateOffset(years=3),
        "5 Years": pd.DateOffset(years=5),
        "Max (2014-Now)": None
    }
    
    # Create horizontal radio buttons
    selected_tf = st.radio(
        "Select Timeframe:", 
        options=list(timeframes.keys()), 
        horizontal=True,
        index=6 # Defaults to "Max"
    )

    # Filter the data based on selection
    if timeframes[selected_tf] is not None:
        # Calculate the cutoff date relative to the most recent date in the dataset
        latest_date = data['DATE'].max()
        cutoff_date = latest_date - timeframes[selected_tf]
        
        # Apply the filter
        filtered_data = data[data['DATE'] >= cutoff_date]
    else:
        filtered_data = data

    # --- Helper function for cleaner charts ---
    def create_line_chart(df, y_col, title, color):
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=df['DATE'], 
            y=df[y_col], 
            mode='lines',
            name=title, 
            line=dict(color=color, width=2)
        ))
        fig.update_layout(
            title=title,
            xaxis_title="Timeline",
            yaxis_title="Amount (₹ Crores)",
            hovermode="x unified",
            template="plotly_dark",
            height=350, # Keep them slightly shorter since there are three
            margin=dict(l=20, r=20, t=40, b=20)
        )
        return fig

    # --- Render the 3 distinct charts ---
    st.plotly_chart(create_line_chart(filtered_data, 'FII_NET_PURCHASE_SALES', 'FII Net Flows', '#00f2ff'), use_container_width=True)
    st.plotly_chart(create_line_chart(filtered_data, 'DII_NET_PURCHASE_SALES', 'DII Net Flows', '#ff4b4b'), use_container_width=True)
    st.plotly_chart(create_line_chart(filtered_data, 'TOTAL_NET', 'Combined Total Net Inflow', '#00ff88'), use_container_width=True)

    st.markdown("---")

    # Raw Data View (Also filters based on timeframe)
    with st.expander(f"View Raw Data Table ({selected_tf})"):
        st.dataframe(filtered_data.sort_values('DATE', ascending=False), use_container_width=True)

except Exception as e:
    st.error(f"Error loading data: {e}")
    if 'df' in locals() or 'df' in globals():
        st.write("Columns found in your file:", list(df.columns))
