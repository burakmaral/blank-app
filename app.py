import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# Set page configuration
st.set_page_config(page_title="E-Commerce Funnel Analysis", layout="wide")

st.title("🛍️ E-Commerce Session & Conversion Analysis")
st.markdown("Upload your CSV file or use the default dataset to visualize the conversion funnel and top-performing landing pages.")

# --- File Uploader & Data Loading ---
uploaded_file = st.sidebar.file_uploader("Upload CSV", type=["csv"])

@st.cache_data
def load_data(file):
    df = pd.read_csv(file)
    # Fill missing values in 'Landing page type' just in case
    df['Landing page type'] = df['Landing page type'].fillna('Unknown')
    return df

# Logic to load user file or default file if available locally
try:
    if uploaded_file is not None:
        df = load_data(uploaded_file)
    else:
        # Default filename based on your request
        default_file = "session-added-to-cart-reached-checkout-completed.csv"
        df = load_data(default_file)
except FileNotFoundError:
    st.warning("⚠️ CSV file not found. Please upload your CSV file using the sidebar.")
    st.stop()

# --- Sidebar Filters ---
st.sidebar.header("Filters")

# Filter by Landing Page Type
all_types = df['Landing page type'].unique().tolist()
selected_types = st.sidebar.multiselect("Select Landing Page Type", all_types, default=all_types)

# Filter by Minimum Sessions (to remove noise)
min_sessions = st.sidebar.slider("Minimum Sessions", min_value=0, max_value=int(df['Sessions'].max()/10), value=100)

# Apply filters
df_filtered = df[
    (df['Landing page type'].isin(selected_types)) & 
    (df['Sessions'] >= min_sessions)
]

# --- Main Dashboard ---

# 1. High-Level Metrics (KPIs)
st.subheader("📊 Overall Performance")
total_sessions = df_filtered['Sessions'].sum()
total_atc = df_filtered['Sessions with cart additions'].sum()
total_checkout = df_filtered['Sessions that reached checkout'].sum()
total_purchases = df_filtered['Sessions that completed checkout'].sum()

# Calculate Rates
atc_rate = (total_atc / total_sessions * 100) if total_sessions > 0 else 0
checkout_rate = (total_checkout / total_sessions * 100) if total_sessions > 0 else 0
conversion_rate = (total_purchases / total_sessions * 100) if total_sessions > 0 else 0

col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Sessions", f"{total_sessions:,}")
col2.metric("Add to Cart Rate", f"{atc_rate:.2f}%", f"{total_atc:,} sessions")
col3.metric("Reached Checkout Rate", f"{checkout_rate:.2f}%", f"{total_checkout:,} sessions")
col4.metric("Conversion Rate", f"{conversion_rate:.2f}%", f"{total_purchases:,} orders")

st.markdown("---")

# 2. Funnel Visualization
st.subheader("🔻 Conversion Funnel")

funnel_data = dict(
    number=[total_sessions, total_atc, total_checkout, total_purchases],
    stage=["Sessions", "Add to Cart", "Reached Checkout", "Completed Purchase"]
)

fig_funnel = go.Figure(go.Funnel(
    y=funnel_data['stage'],
    x=funnel_data['number'],
    textposition="inside",
    textinfo="value+percent initial",
    marker={"color": ["#636EFA", "#EF553B", "#00CC96", "#AB63FA"]}
))
fig_funnel.update_layout(title_text="Aggregate Conversion Funnel")
st.plotly_chart(fig_funnel, use_container_width=True)

# 3. Top Performing Pages Analysis
st.markdown("---")
st.subheader("🏆 Top Performing Landing Pages")

# Calculate Conversion Rate per page for the table
df_filtered['Conversion Rate (%)'] = (df_filtered['Sessions that completed checkout'] / df_filtered['Sessions'] * 100).round(2)

# Sort options
sort_by = st.radio("Sort Top Pages By:", ["Sessions", "Sessions that completed checkout", "Conversion Rate (%)"], horizontal=True)

top_n = df_filtered.sort_values(by=sort_by, ascending=False).head(10)

# Display Bar Chart
fig_bar = px.bar(
    top_n, 
    x=sort_by, 
    y='Landing page path', 
    orientation='h',
    title=f"Top 10 Pages by {sort_by}",
    color='Landing page type',
    hover_data=['Sessions', 'Sessions with cart additions', 'Sessions that completed checkout']
)
fig_bar.update_layout(yaxis=dict(autorange="reversed")) # Top item at top
st.plotly_chart(fig_bar, use_container_width=True)

# 4. Detailed Data View
with st.expander("📂 View Detailed Data Table"):
    st.dataframe(
        df_filtered[[
            'Landing page path', 'Landing page type', 'Sessions', 
            'Sessions with cart additions', 'Sessions that completed checkout', 
            'Conversion Rate (%)'
        ]].sort_values(by='Sessions', ascending=False)
    )

# 5. Scatter Plot: Traffic vs Conversion Quality
st.subheader("🔍 Traffic vs. Conversion Quality")
st.markdown("Are high-traffic pages converting well? (Size of bubble = Total Orders)")

fig_scatter = px.scatter(
    df_filtered,
    x="Sessions",
    y="Conversion Rate (%)",
    size="Sessions that completed checkout",
    color="Landing page type",
    hover_name="Landing page path",
    log_x=True, # Log scale usually looks better for traffic data
    title="Sessions vs. Conversion Rate (Log Scale)"
)
st.plotly_chart(fig_scatter, use_container_width=True)
# --- ADD THIS TO THE END OF YOUR APP.PY FILE ---

st.markdown("---")
st.subheader("🛒 Cart Abandonment Analysis")
st.markdown("Analysis of sessions where items were added to the cart but checkout was never initiated.")

# 1. Calculate Abandonment Rate
# Formula: (Added to Cart - Reached Checkout) / Added to Cart
df_filtered['Cart Abandonment Rate (%)'] = (
    (df_filtered['Sessions with cart additions'] - df_filtered['Sessions that reached checkout']) / 
    df_filtered['Sessions with cart additions'] * 100
)

# Handle cases where division by zero might occur (0 cart additions)
df_filtered['Cart Abandonment Rate (%)'] = df_filtered['Cart Abandonment Rate (%)'].fillna(0)

# 2. Filter for meaningful data
# We ignore pages with very few cart additions (< 10) to prevent 100% abandonment on 1 visitor from skewing the chart.
df_abandonment = df_filtered[df_filtered['Sessions with cart additions'] > 10].copy()

# 3. Visualization: Histogram of Abandonment Rates
# This helps you see if most products have a "normal" abandonment (e.g., 60-70%) or if some are dangerously high.
fig_hist = px.histogram(
    df_abandonment, 
    x="Cart Abandonment Rate (%)",
    nbins=20,
    title="Distribution of Cart Abandonment Rates (Pages with >10 Cart Adds)",
    labels={'Cart Abandonment Rate (%)': 'Abandonment Rate %'},
    color_discrete_sequence=['#EF553B'] # Red to signal "loss"
)
fig_hist.update_layout(bargap=0.1)
st.plotly_chart(fig_hist, use_container_width=True)

# 4. Table: Top "Leaky" Pages
st.markdown("#### 🚨 High Abandonment Pages (Fix These First)")
st.markdown("These pages have high interest (Adds) but high drop-off. Check for shipping cost surprises or technical errors.")

st.dataframe(
    df_abandonment[[
        'Landing page path', 
        'Sessions with cart additions', 
        'Sessions that reached checkout', 
        'Cart Abandonment Rate (%)'
    ]].sort_values(by='Cart Abandonment Rate (%)', ascending=False).head(10).style.format({
        'Cart Abandonment Rate (%)': '{:.2f}%'
    })
)
