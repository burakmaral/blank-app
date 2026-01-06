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
    df['Landing page type'] = df['Landing page type'].fillna('Unknown')
    return df

try:
    if uploaded_file is not None:
        df = load_data(uploaded_file)
    else:
        default_file = "session-added-to-cart-reached-checkout-completed.csv"
        df = load_data(default_file)
except FileNotFoundError:
    st.warning("⚠️ CSV file not found. Please upload your CSV file using the sidebar.")
    st.stop()

# --- Sidebar Filters ---
st.sidebar.header("Filters")

all_types = df['Landing page type'].unique().tolist()
selected_types = st.sidebar.multiselect("Select Landing Page Type", all_types, default=all_types)

min_sessions = st.sidebar.slider("Minimum Sessions", min_value=0, max_value=int(df['Sessions'].max()/10), value=100)

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

# Calculate drop-off counts
df_filtered['Added but Never Checkout'] = df_filtered['Sessions with cart additions'] - df_filtered['Sessions that reached checkout']
df_filtered['Reached but Never Completed'] = df_filtered['Sessions that reached checkout'] - df_filtered['Sessions that completed checkout']

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

# ========================================
# NEW SECTION: DETAILED PRODUCT ANALYSIS FOR UPSELLS
# ========================================

st.header("🎯 Detailed Product Performance Analysis (For Upsell Strategy)")

tab1, tab2, tab3, tab4 = st.tabs([
    "🏆 Best Performers", 
    "⚠️ High Interest, Low Conversion", 
    "🚨 Checkout Abandoners",
    "📊 Comparison Matrix"
])

# TAB 1: Best Performing Products
with tab1:
    st.subheader("Best Converting Products (Full Funnel Winners)")
    st.markdown("**These products have high cart additions AND high checkout completion. Use these for upsells!**")
    
    # Filter for products with meaningful traffic
    df_best = df_filtered[df_filtered['Sessions with cart additions'] >= 10].copy()
    
    # Sort by products that complete the full journey well
    df_best['Quality Score'] = (
        df_best['Sessions that completed checkout'] * 0.5 +  # Actual conversions matter most
        df_best['Checkout Completion Rate (%)'] * 0.3 +      # Good at closing
        df_best['Add to Cart Rate (%)'] * 0.2                # Initial interest
    )
    
    df_best_sorted = df_best.sort_values('Quality Score', ascending=False).head(15)
    
    # Display chart
    fig_best = go.Figure()
    fig_best.add_trace(go.Bar(
        name='Completed Checkout',
        y=df_best_sorted['Landing page path'],
        x=df_best_sorted['Sessions that completed checkout'],
        orientation='h',
        marker_color='#00CC96'
    ))
    fig_best.add_trace(go.Bar(
        name='Reached Checkout',
        y=df_best_sorted['Landing page path'],
        x=df_best_sorted['Sessions that reached checkout'],
        orientation='h',
        marker_color='#FFA15A'
    ))
    fig_best.add_trace(go.Bar(
        name='Added to Cart',
        y=df_best_sorted['Landing page path'],
        x=df_best_sorted['Sessions with cart additions'],
        orientation='h',
        marker_color='#636EFA'
    ))
    fig_best.update_layout(
        barmode='group',
        title="Top 15 Best Converting Products",
        yaxis=dict(autorange="reversed"),
        height=600
    )
    st.plotly_chart(fig_best, use_container_width=True)
    
    st.dataframe(
        df_best_sorted[[
            'Landing page path', 'Landing page type',
            'Sessions with cart additions', 
            'Sessions that reached checkout',
            'Sessions that completed checkout',
            'Checkout Completion Rate (%)',
            'Conversion Rate (%)'
        ]],
        use_container_width=True
    )

# TAB 2: High Interest but Low Conversion
with tab2:
    st.subheader("High Cart Adds, Low Checkout Completion")
    st.markdown("**⚠️ These products get added to cart often but don't convert well. Prime candidates for:**")
    st.markdown("- Exit-intent popups with discounts\n- Free shipping offers\n- Trust badges (reviews, guarantees)\n- Cart abandonment emails")
    
    # Products with high cart additions but poor checkout completion
    df_interest = df_filtered[df_filtered['Sessions with cart additions'] >= 20].copy()
    df_interest = df_interest[df_interest['Checkout Completion Rate (%)'] < 50]  # Less than 50% complete after reaching checkout
    df_interest_sorted = df_interest.sort_values('Sessions with cart additions', ascending=False).head(15)
    
    fig_interest = px.scatter(
        df_interest_sorted,
        x='Sessions with cart additions',
        y='Checkout Completion Rate (%)',
        size='Added but Never Checkout',
        color='Landing page type',
        hover_name='Landing page path',
        title="Products with High Interest but Poor Conversion",
        labels={'Added but Never Checkout': 'Lost Customers'}
    )
    st.plotly_chart(fig_interest, use_container_width=True)
    
    st.dataframe(
        df_interest_sorted[[
            'Landing page path',
            'Sessions with cart additions',
            'Sessions that reached checkout',
            'Added but Never Checkout',
            'Cart to Checkout Rate (%)',
            'Checkout Completion Rate (%)'
        ]].sort_values('Added but Never Checkout', ascending=False),
        use_container_width=True
    )

# TAB 3: Checkout Abandoners
with tab3:
    st.subheader("Reached Checkout but Didn't Complete")
    st.markdown("**🚨 These users were VERY close to buying. Focus recovery efforts here:**")
    st.markdown("- Retargeting ads\n- Personalized email sequences\n- One-click checkout improvements\n- Payment option expansion")
    
    df_abandon = df_filtered[df_filtered['Sessions that reached checkout'] >= 10].copy()
    df_abandon_sorted = df_abandon.sort_values('Reached but Never Completed', ascending=False).head(15)
    
    # Stacked bar chart showing the gap
    fig_abandon = go.Figure()
    fig_abandon.add_trace(go.Bar(
        name='Completed',
        y=df_abandon_sorted['Landing page path'],
        x=df_abandon_sorted['Sessions that completed checkout'],
        orientation='h',
        marker_color='#00CC96'
    ))
    fig_abandon.add_trace(go.Bar(
        name='Abandoned at Checkout',
        y=df_abandon_sorted['Landing page path'],
        x=df_abandon_sorted['Reached but Never Completed'],
        orientation='h',
        marker_color='#EF553B'
    ))
    fig_abandon.update_layout(
        barmode='stack',
        title="Top 15 Products with Most Checkout Abandonment",
        yaxis=dict(autorange="reversed"),
        height=600
    )
    st.plotly_chart(fig_abandon, use_container_width=True)
    
    st.dataframe(
        df_abandon_sorted[[
            'Landing page path',
            'Sessions that reached checkout',
            'Sessions that completed checkout',
            'Reached but Never Completed',
            'Checkout Completion Rate (%)'
        ]],
        use_container_width=True
    )

# TAB 4: Comparison Matrix
with tab4:
    st.subheader("Product Performance Matrix")
    st.markdown("**Compare all products across key metrics. Identify patterns for upsell bundling.**")
    
    # Create a comprehensive view
    df_matrix = df_filtered[df_filtered['Sessions with cart additions'] >= 10].copy()
    
    # Scatter plot: Cart-to-Checkout vs Checkout Completion
    fig_matrix = px.scatter(
        df_matrix,
        x='Cart to Checkout Rate (%)',
        y='Checkout Completion Rate (%)',
        size='Sessions with cart additions',
        color='Landing page type',
        hover_name='Landing page path',
        hover_data={
            'Sessions with cart additions': True,
            'Sessions that completed checkout': True,
            'Conversion Rate (%)': ':.2f'
        },
        title="Product Performance Matrix: Cart Behavior vs Checkout Behavior"
    )
    
    # Add quadrant lines
    fig_matrix.add_hline(y=50, line_dash="dash", line_color="gray", opacity=0.5)
    fig_matrix.add_vline(x=50, line_dash="dash", line_color="gray", opacity=0.5)
    
    # Add annotations for quadrants
    fig_matrix.add_annotation(x=75, y=75, text="🌟 Stars<br>(High Intent + High Close)", showarrow=False, font=dict(size=10, color="green"))
    fig_matrix.add_annotation(x=25, y=75, text="💎 Hidden Gems<br>(Low Checkout Start, High Close)", showarrow=False, font=dict(size=10, color="blue"))
    fig_matrix.add_annotation(x=75, y=25, text="⚠️ Leaky Funnels<br>(High Intent, Poor Close)", showarrow=False, font=dict(size=10, color="orange"))
    fig_matrix.add_annotation(x=25, y=25, text="🔴 Strugglers<br>(Low Intent + Poor Close)", showarrow=False, font=dict(size=10, color="red"))
    
    st.plotly_chart(fig_matrix, use_container_width=True)
    
    # Full data table with all metrics
    st.markdown("#### Complete Performance Data")
    st.dataframe(
        df_matrix[[
            'Landing page path', 'Landing page type',
            'Sessions', 'Sessions with cart additions',
            'Sessions that reached checkout', 'Sessions that completed checkout',
            'Add to Cart Rate (%)', 'Cart to Checkout Rate (%)',
            'Checkout Completion Rate (%)', 'Conversion Rate (%)',
            'Added but Never Checkout', 'Reached but Never Completed'
        ]].sort_values('Sessions that completed checkout', ascending=False),
        use_container_width=True
    )

st.markdown("---")

# Original sections
st.subheader("🏆 Top Performing Landing Pages")

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

with st.expander("📂 View Detailed Data Table"):
    st.dataframe(
        df_filtered[[
            'Landing page path', 'Landing page type', 'Sessions', 
            'Sessions with cart additions', 'Sessions that completed checkout', 
            'Conversion Rate (%)'
        ]].sort_values(by='Sessions', ascending=False)
    )

st.subheader("🔍 Traffic vs. Conversion Quality")
st.markdown("Are high-traffic pages converting well? (Size of bubble = Total Orders)")

fig_scatter = px.scatter(
    df_filtered,
    x="Sessions",
    y="Conversion Rate (%)",
    size="Sessions that completed checkout",
    color="Landing page type",
    hover_name="Landing page path",
    log_x=True,
    title="Sessions vs. Conversion Rate (Log Scale)"
)
st.plotly_chart(fig_scatter, use_container_width=True)

st.markdown("---")
st.subheader("🛒 Cart Abandonment Analysis")
st.markdown("Analysis of sessions where items were added to the cart but checkout was never initiated.")

df_abandonment = df_filtered[df_filtered['Sessions with cart additions'] > 10].copy()

fig_hist = px.histogram(
    df_abandonment, 
    x="Cart Abandonment Rate (%)",
    nbins=20,
    title="Distribution of Cart Abandonment Rates (Pages with >10 Cart Adds)",
    labels={'Cart Abandonment Rate (%)': 'Abandonment Rate %'},
    color_discrete_sequence=['#EF553B']
)
fig_hist.update_layout(bargap=0.1)
st.plotly_chart(fig_hist, use_container_width=True)

st.markdown("#### 🚨 High Abandonment Pages (Fix These First)")
st.markdown("These pages have high interest (Adds) but high drop-off. Check for shipping cost surprises or technical errors.")

st.dataframe(
    df_abandonment[[
        'Landing page path', 
        'Sessions with cart additions', 
        'Sessions that reached checkout', 
        'Cart Abandonment Rate (%)'
    ]].sort_values(by='Cart Abandonment Rate (%)', ascending=False).head(10)
)
