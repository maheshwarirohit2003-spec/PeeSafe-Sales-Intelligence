import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# --- CONFIGURATION ---
st.set_page_config(
    page_title="PeeSafe Sales Intelligence",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)


# --- CONSTANTS & CONFIG ---
# UPDATE THIS PATH TO YOUR LOCAL FILE
DATA_PATH = r"Nov_to_Jan_sec.xlsx" 

# Zone Anchors for Regional Visualization
ZONE_COORDS = {
    'North': {'lat': 28.61, 'lon': 77.20},
    'West':  {'lat': 19.07, 'lon': 72.87},
    'East':  {'lat': 22.57, 'lon': 88.36},
    'South': {'lat': 12.97, 'lon': 77.59},
    'Central': {'lat': 21.14, 'lon': 79.08}
}

# --- DATA ENGINE ---
@st.cache_data
def load_data(filepath):
    try:
        if filepath.endswith('.csv'):
            df = pd.read_csv(filepath)
        else:
            df = pd.read_excel(filepath)
    except FileNotFoundError:
        st.error(f"Critical Error: Data file not found at {filepath}")
        st.stop()
    except Exception as e:
        st.error(f"Data Load Error: {e}")
        st.stop()

    # Standardization
    try:
        df['Date'] = pd.to_datetime(df['Month2'], format="%b'%y")
    except:
        df['Date'] = pd.to_datetime(df['Month2'], errors='coerce')
    
    if 'ASP' not in df.columns:
        df['ASP'] = df['Amount'] / df['Unit Sold']

    # Map Logic: Assign Fixed Anchor Coordinates per Zone
    df['Lat'] = df['Zone'].map(lambda z: ZONE_COORDS.get(z, ZONE_COORDS['Central'])['lat'])
    df['Lon'] = df['Zone'].map(lambda z: ZONE_COORDS.get(z, ZONE_COORDS['Central'])['lon'])

    return df

# --- INITIALIZATION ---
df = load_data(DATA_PATH)

# --- SIDEBAR: CONFIGURATION PARAMETERS ---
with st.sidebar:
    st.title("Configuration Parameters")
    st.markdown("---")
    
    # Chronological sort for month selector
    sorted_months = sorted(df['Month2'].unique(), key=lambda x: pd.to_datetime(x, format="%b'%y"))
    
    sel_month = st.multiselect("Reporting Period", sorted_months, default=sorted_months)
    sel_zone = st.multiselect("Geographic Zone", df['Zone'].unique(), default=df['Zone'].unique())
    sel_cat = st.multiselect("Product Category", df['Category'].unique(), default=df['Category'].unique())
    
    st.markdown("---")
    st.caption("v1.2.0 | Production Build")

# Global Filter Application
if not sel_month: sel_month = df['Month2'].unique()
if not sel_zone: sel_zone = df['Zone'].unique()
if not sel_cat: sel_cat = df['Category'].unique()

df_filtered = df[
    (df['Month2'].isin(sel_month)) & 
    (df['Zone'].isin(sel_zone)) & 
    (df['Category'].isin(sel_cat))
]

if df_filtered.empty:
    st.warning("No data matches the selected parameters.")
    st.stop()

# --- KPI HEADER ---
kpi_rev = df_filtered['Amount'].sum()
kpi_vol = df_filtered['Unit Sold'].sum()
kpi_asp = df_filtered['ASP'].mean()
kpi_stores = df_filtered['Store Name'].nunique()

st.title("PeeSafe Sales Intelligence")
st.markdown("### Executive Summary")

c1, c2, c3, c4 = st.columns(4)
c1.metric("Total Revenue", f"₹{kpi_rev:,.0f}")
c2.metric("Total Volume", f"{kpi_vol:,.0f}")
c3.metric("Avg Selling Price", f"₹{kpi_asp:.1f}")
c4.metric("Active Outlets", f"{kpi_stores}")

st.markdown("---")

# --- MAIN DASHBOARD ---
tab_strat, tab_micro, tab_leader = st.tabs(["Strategy Map", "Micro-Analysis", "Performance Leaderboard"])

with tab_strat:
    col_map, col_trend = st.columns([1.5, 1])
    
    with col_map:
        st.subheader("Regional Performance Density")
        # Aggregated Map View (Zone Level)
        zone_agg = df_filtered.groupby(['Zone', 'Lat', 'Lon'])[['Amount', 'Unit Sold']].sum().reset_index()
        
        fig_map = px.scatter_mapbox(
            zone_agg,
            lat="Lat",
            lon="Lon",
            size="Amount",
            color="Zone", 
            zoom=3.8,
            center={"lat": 22.0, "lon": 82.0},
            size_max=50, # Large beacons
            mapbox_style="carto-darkmatter",
            title="Revenue Contribution by Zone"
        )
        fig_map.update_layout(margin={"r":0,"t":30,"l":0,"b":0}, height=450, showlegend=False)
        st.plotly_chart(fig_map, use_container_width=True)

    with col_trend:
        st.subheader("Revenue Trajectory")
        trend_df = df_filtered.groupby('Date')[['Amount']].sum().reset_index().sort_values('Date')
        
        fig_trend = go.Figure()
        fig_trend.add_trace(go.Scatter(
            x=trend_df['Date'], y=trend_df['Amount'],
            mode='lines+markers',
            line=dict(color='#10B981', width=3),
            fill='tozeroy',
            fillcolor='rgba(16, 185, 129, 0.1)'
        ))
        fig_trend.update_layout(
            height=450, 
            margin={"r":0,"t":30,"l":0,"b":0}, 
            paper_bgcolor='rgba(0,0,0,0)', 
            plot_bgcolor='rgba(0,0,0,0)',
            xaxis_title=None,
            yaxis_title=None
        )
        st.plotly_chart(fig_trend, use_container_width=True)

with tab_micro:
    c1, c2 = st.columns(2)
    
    with c1:
        st.subheader("Portfolio Composition")
        fig_sun = px.sunburst(
            df_filtered,
            path=['Category', 'Sub Category', 'SKU Placed'],
            values='Amount',
            color='Amount',
            color_continuous_scale='Magma',
        )
        fig_sun.update_layout(height=500, margin={"r":0,"t":0,"l":0,"b":0})
        st.plotly_chart(fig_sun, use_container_width=True)
        
    with c2:
        st.subheader("Pricing Elasticity Model")
        fig_scatter = px.scatter(
            df_filtered,
            x="ASP",
            y="Unit Sold",
            color="Category",
            size="Amount",
            trendline="ols",
            opacity=0.7,
            labels={"ASP": "Price Point (₹)", "Unit Sold": "Volume"}
        )
        fig_scatter.update_layout(height=500)
        st.plotly_chart(fig_scatter, use_container_width=True)

with tab_leader:
    st.subheader("🏆 Performance Leaderboards")
    
    lc1, lc2 = st.columns(2)
    
    with lc1:
        st.markdown("#### Top 10 Stores (Revenue)")
        top_stores = df_filtered.groupby('Store Name')['Amount'].sum().nlargest(10).reset_index()
        st.dataframe(
            top_stores.style.format({"Amount": "₹{:,.2f}"}).background_gradient(cmap="Greens", subset=["Amount"]),
            use_container_width=True,
            hide_index=True
        )
        
        st.markdown("#### Bottom 10 Stores (Revenue)")
        bottom_stores = df_filtered.groupby('Store Name')['Amount'].sum().nsmallest(10).reset_index()
        st.dataframe(
            bottom_stores.style.format({"Amount": "₹{:,.2f}"}),
            use_container_width=True,
            hide_index=True
        )

    with lc2:
        st.markdown("#### Top 10 Products (Volume)")
        top_sku = df_filtered.groupby('SKU Placed')['Unit Sold'].sum().nlargest(10).reset_index()
        st.dataframe(
            top_sku.style.background_gradient(cmap="Blues", subset=["Unit Sold"]),
            use_container_width=True,
            hide_index=True
        )

        st.markdown("#### Top Zones (Revenue)")
        top_zone = df_filtered.groupby('Zone')['Amount'].sum().sort_values(ascending=False).reset_index()
        st.dataframe(
            top_zone.style.format({"Amount": "₹{:,.2f}"}).background_gradient(cmap="Purples", subset=["Amount"]),
            use_container_width=True,
            hide_index=True
        )