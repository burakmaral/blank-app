import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os

# Set page configuration
st.set_page_config(page_title="E-Commerce Funnel & Upsell Strategy", layout="wide")

st.title("🛍️ E-Commerce Session & Conversion Analysis")
st.markdown("Dashboard analyzing conversion funnels and product upsell opportunities.")

# --- Data Loading (Directly from file) ---
FILENAME = "session-added-to-cart-reached-checkout-completed.csv"

@st.cache_data
def load_data(file_path):
    df = pd.read_csv(file_path)
    df['Landing page type'] = df['Landing page type'].fillna('Unknown')
    return df

try:
    if os.path.exists(FILENAME):
        df = load_data(FILENAME)
        st.success(f"✅ Automatically loaded data from: `{FILENAME}`")
    else:
        st.error(f"⚠️ Could not find the file: `{FILENAME}` in the current directory.")
        st.stop()
except Exception as e:
    st.error(f"An error occurred while loading the file: {e}")
    st.stop()

# --- Sidebar Filters ---
st.sidebar.header("Filters")

all_types = df['Landing page type'].unique().tolist()
selected_types = st.sidebar.multiselect("Select Landing Page Type", all_types, default=all_types)

# Slider for minimum sessions to filter out statistical noise
min_sessions = st.sidebar.slider("Minimum Sessions Threshold", min_value=10, max_value=int(df['Sessions'].max()/10), value=50, step=10)

df_filtered = df[
    (df['Landing page type'].isin(selected_types)) & 
    (df['Sessions'] >= min_sessions)
]

# --- Calculate Additional Metrics ---
df_filtered['Conversion Rate (%)'] = (df_filtered['Sessions that completed checkout'] / df_filtered['Sessions'] * 100).round(2)
df_filtered['Add to Cart Rate (%)'] = (df_filtered['Sessions with cart additions'] / df_filtered['Sessions'] * 100).round(2)
df_filtered['Cart to Checkout Rate (%)'] = (df_filtered['Sessions that reached checkout'] / df_filtered['Sessions with cart additions'] * 100).fillna(0).round(2)
df_filtered['Checkout Completion Rate (%)'] = (df_filtered['Sessions that completed checkout'] / df_filtered['Sessions that reached checkout'] * 100).fillna(0).round(2)
df_filtered['Cart Abandonment Rate (%)'] = ((df_filtered['Sessions with cart additions'] - df_filtered['Sessions that reached checkout']) / df_filtered['Sessions with cart additions'] * 100).fillna(0).round(2)

# --- Main Dashboard ---

# 1. High-Level Metrics (KPIs)
st.subheader("📊 Overall Performance")
total_sessions = df_filtered['Sessions'].sum()
total_atc = df_filtered['Sessions with cart additions'].sum()
total_checkout = df_filtered['Sessions that reached checkout'].sum()
total_purchases = df_filtered['Sessions that completed checkout'].sum()

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

st.markdown("---")

# ==============================================================================
# STRATEGIC RECOMMENDATIONS (Text Summary)
# ==============================================================================

st.header("🤖 Strategic Recommendations")
st.markdown("Based on your data, here are the top candidates for your specific upsell strategies.")

rec_col1, rec_col2, rec_col3 = st.columns(3)

# 1. Checkout Upsells (High Completion)
df_checkout_upsell = df_filtered[
    (df_filtered['Sessions with cart additions'] >= 10) & 
    (df_filtered['Checkout Completion Rate (%)'] >= 50)
].sort_values(by='Checkout Completion Rate (%)', ascending=False).head(5)

with rec_col1:
    st.subheader("🛒 Checkout Upsells")
    st.caption("Low friction items. High completion rate.")
    if not df_checkout_upsell.empty:
        for index, row in df_checkout_upsell.iterrows():
            st.success(f"**{row['Landing page path']}**")
            st.markdown(f"Completion Rate: **{row['Checkout Completion Rate (%)']}%**")
    else:
        st.warning("No products meet the criteria")

# 2. Post-Purchase Upsells (High Interest, Lower Completion)
df_post_purchase = df_filtered[
    (df_filtered['Sessions'] >= 50) &
    (df_filtered['Add to Cart Rate (%)'] >= 10) &         
    (df_filtered['Checkout Completion Rate (%)'] < 50)    
].sort_values(by='Add to Cart Rate (%)', ascending=False).head(5)

with rec_col2:
    st.subheader("📦 Post-Purchase")
    st.caption("High desire, higher friction items.")
    if not df_post_purchase.empty:
        for index, row in df_post_purchase.iterrows():
            st.info(f"**{row['Landing page path']}**")
            st.markdown(f"Add-to-Cart Rate: **{row['Add to Cart Rate (%)']}%**")
    else:
        st.warning("No products meet the criteria")

# 3. Cross-Sell / Bundles (Stars)
df_cross_sell = df_filtered[
    (df_filtered['Sessions'] >= 50) &
    (df_filtered['Add to Cart Rate (%)'] >= 8) &
    (df_filtered['Checkout Completion Rate (%)'] >= 60)
].sort_values(by='Conversion Rate (%)', ascending=False).head(5)

with rec_col3:
    st.subheader("🔗 Cross-Sell / Bundles")
    st.caption("Star products. Combine these.")
    if not df_cross_sell.empty:
        for index, row in df_cross_sell.iterrows():
            st.warning(f"**{row['Landing page path']}**")
            st.markdown(f"Conversion Rate: **{row['Conversion Rate (%)']}%**")
    else:
        st.warning("No products meet the criteria")

st.markdown("---")

# ==============================================================================
# DETAILED STRATEGIC UPSELL ANALYSIS (Tabs)
# ==============================================================================

st.header("🎯 Detailed Product Analysis")

upsell_tab1, upsell_tab2, upsell_tab3, upsell_tab4 = st.tabs([
    "💡 Checkout Upsell Candidates", 
    "📦 Post-Purchase Candidates", 
    "📈 The Strategy Matrix", 
    "🚨 Fix These First"
])

# --- TAB 1: Checkout Upsells (Order Bumps) ---
with upsell_tab1:
    st.subheader("🏆 Best Candidates for Checkout Upsells (In-Cart)")
    st.info("**Strategy:** These products have a **High Checkout Completion Rate**. Once users add them to the cart, they rarely abandon them.")
    
    checkout_candidates = df_filtered[
        (df_filtered['Sessions with cart additions'] > 10)
    ].sort_values(by='Checkout Completion Rate (%)', ascending=False).head(10)
    
    fig_bump = px.bar(
        checkout_candidates,
        x='Checkout Completion Rate (%)',
        y='Landing page path',
        orientation='h',
        color='Checkout Completion Rate (%)',
        color_continuous_scale='Greens',
        title="Top 10 'Closers': Highest Checkout Completion Rate",
        hover_data=['Sessions', 'Sessions that completed checkout']
    )
    fig_bump.update_layout(yaxis=dict(autorange="reversed"))
    st.plotly_chart(fig_bump, use_container_width=True)
    
    st.dataframe(checkout_candidates[['Landing page path', 'Checkout Completion Rate (%)', 'Conversion Rate (%)', 'Sessions']])

# --- TAB 2: Post-Purchase Upsells ---
with upsell_tab2:
    st.subheader("📦 Best Candidates for Post-Purchase Upsells")
    st.info("**Strategy:** These products have **High Add-to-Cart Rates** (High Desire). Offering them *after* purchase removes friction.")
    
    post_purchase_candidates = df_filtered[
        (df_filtered['Sessions'] > min_sessions)
    ].sort_values(by='Add to Cart Rate (%)', ascending=False).head(10)

    fig_post = px.bar(
        post_purchase_candidates,
        x='Add to Cart Rate (%)',
        y='Landing page path',
        orientation='h',
        color='Add to Cart Rate (%)',
        color_continuous_scale='Blues',
        title="Top 10 'High Desire': Highest Add-to-Cart Rate",
        hover_data=['Sessions', 'Sessions with cart additions']
    )
    fig_post.update_layout(yaxis=dict(autorange="reversed"))
    st.plotly_chart(fig_post, use_container_width=True)
    
    st.dataframe(post_purchase_candidates[['Landing page path', 'Add to Cart Rate (%)', 'Conversion Rate (%)', 'Sessions']])

# --- TAB 3: Strategy Matrix ---
with upsell_tab3:
    st.subheader("📈 The Upsell Strategy Matrix")
    st.markdown("This chart segments your products to help you decide where to place them in the funnel.")
    
    matrix_df = df_filtered[df_filtered['Sessions with cart additions'] > 5].copy()
    
    fig_matrix = px.scatter(
        matrix_df,
        x="Add to Cart Rate (%)",
        y="Checkout Completion Rate (%)",
        size="Sessions that completed checkout", 
        color="Landing page type",
        hover_name="Landing page path",
        title="Product Matrix: Desire (X) vs. Closing Ability (Y)",
        labels={"Add to Cart Rate (%)": "Desire (Add to Cart %)", "Checkout Completion Rate (%)": "Low Friction (Checkout Completion %)"}
    )
    
    avg_atc = matrix_df['Add to Cart Rate (%)'].mean()
    avg_checkout = matrix_df['Checkout Completion Rate (%)'].mean()
    
    fig_matrix.add_hline(y=avg_checkout, line_dash="dash", line_color="gray", annotation_text="Avg Completion")
    fig_matrix.add_vline(x=avg_atc, line_dash="dash", line_color="gray", annotation_text="Avg ATC")
    
    fig_matrix.add_annotation(x=matrix_df['Add to Cart Rate (%)'].max(), y=matrix_df['Checkout Completion Rate (%)'].max(), 
                              text="⭐ STARS", showarrow=False, xanchor="right", yanchor="top")
    fig_matrix.add_annotation(x=matrix_df['Add to Cart Rate (%)'].min(), y=matrix_df['Checkout Completion Rate (%)'].max(), 
                              text="✅ CHECKOUT BUMPS", showarrow=False, xanchor="left", yanchor="top")
    fig_matrix.add_annotation(x=matrix_df['Add to Cart Rate (%)'].max(), y=matrix_df['Checkout Completion Rate (%)'].min(), 
                              text="🛒 POST-PURCHASE", showarrow=False, xanchor="right", yanchor="bottom")
    
    st.plotly_chart(fig_matrix, use_container_width=True)

# --- TAB 4: Fix These First ---
with upsell_tab4:
    st.subheader("🚨 High Abandonment Opportunities")
    st.markdown("These products get added to the cart frequently but lose the customer at checkout.")
    
    abandonment_df = df_filtered[df_filtered['Sessions with cart additions'] > 10].sort_values(by='Cart Abandonment Rate (%)', ascending=False).head(10)
    
    # FIXED: Removed .style.background_gradient to avoid matplotlib dependency error
    st.dataframe(
        abandonment_df[['Landing page path', 'Cart Abandonment Rate (%)', 'Sessions with cart additions', 'Sessions that completed checkout']],
        use_container_width=True
    )

st.markdown("---")

# ==============================================================================
# ORIGINAL ANALYSIS SECTIONS
# ==============================================================================

st.subheader("🏆 General Top Performing Pages")
sort_by = st.radio("Sort Top Pages By:", ["Sessions", "Sessions that completed checkout", "Conversion Rate (%)"], horizontal=True)

top_n = df_filtered.sort_values(by=sort_by, ascending=False).head(10)

fig_bar = px.bar(
    top_n, 
    x=sort_by, 
    y='Landing page path', 
    orientation='h',
    title=f"Top 10 Pages by {sort_by}",
    color='Landing page type',
    hover_data=['Sessions', 'Sessions with cart additions', 'Sessions that completed checkout']
)
fig_bar.update_layout(yaxis=dict(autorange="reversed"))
st.plotly_chart(fig_bar, use_container_width=True)

st.subheader("🔍 Traffic vs. Conversion Quality")
fig_scatter = px.scatter(
    df_filtered,
    x="Sessions",
    y="Conversion Rate (%)",
    size="Sessions that completed checkout",
    color="Landing page type",
    hover_name="Landing page path",
    log_x=True,
    title="Sessions vs. Conversion Rate (Size = Orders)"
)
st.plotly_chart(fig_scatter, use_container_width=True)
