import streamlit as st
import pandas as pd
from itertools import permutations
import re

st.set_page_config(page_title="Ramadan Unified Strategy", layout="wide")
st.title("🌙 Ramadan Master Strategy: Funnel + Basket Analysis")
st.markdown("Merging **Traffic Data** with **Order Data** to find the perfect Upsell Opportunities.")

# --- 1. LOAD BOTH DATASETS ---

@st.cache_data
def load_funnel_data():
    # Load your specific file
    df = pd.read_csv("session-added-to-cart-reached-checkout-completed.csv")
    df['Landing page type'] = df['Landing page type'].fillna('Unknown')
    return df

@st.cache_data
def load_transaction_data():
    # Load the ShopifyQL export
    df = pd.read_csv("ramadan_transactions.csv")
    # Clean columns
    df.columns = [c.lower().replace(' ', '_').replace('.', '') for c in df.columns]
    return df

try:
    df_funnel = load_funnel_data()
    df_orders = load_transaction_data()
    st.success(f"✅ Loaded: {len(df_funnel)} funnel records and {len(df_orders)} transaction rows.")
except FileNotFoundError as e:
    st.error(f"Missing File: {e}")
    st.stop()

# --- 2. PROCESS BASKET DATA (FIND ASSOCIATIONS) ---

# Identify columns automatically
order_col = [c for c in df_orders.columns if 'order' in c and 'name' in c][0]
product_col = [c for c in df_orders.columns if 'product' in c and 'title' in c][0]

# Group by order
baskets = df_orders.groupby(order_col)[product_col].apply(list).reset_index()
baskets = baskets[baskets[product_col].apply(len) > 1] # Only multi-item orders

# Generate Pairs
pairs = []
for basket in baskets[product_col]:
    for p in permutations(set(basket), 2):
        pairs.append(p)

# Create Association DataFrame
df_pairs = pd.DataFrame(pairs, columns=['Main Product', 'Upsell Candidate'])
df_pairs['Count'] = 1
df_assoc = df_pairs.groupby(['Main Product', 'Upsell Candidate']).count().reset_index()
df_assoc = df_assoc[df_assoc['Count'] >= 3] # Minimum threshold

# --- 3. PROCESS FUNNEL DATA (CALCULATE METRICS) ---

# Calculate key metrics needed for the strategy
df_funnel['Completion Rate'] = (df_funnel['Sessions that completed checkout'] / df_funnel['Sessions that reached checkout'] * 100).fillna(0)
df_funnel['Abandonment Rate'] = ((df_funnel['Sessions with cart additions'] - df_funnel['Sessions that reached checkout']) / df_funnel['Sessions with cart additions'] * 100).fillna(0)

# HELPER: Create a "Match Key" to join the two datasets
# We try to turn "Blue Prayer Mat" into "blue-prayer-mat" to match landing page handles
def create_slug(text):
    if not isinstance(text, str): return ""
    text = text.lower()
    text = re.sub(r'[^a-z0-9\s]', '', text)
    return text.replace(' ', '-')

df_assoc['match_key'] = df_assoc['Upsell Candidate'].apply(create_slug)
df_funnel['match_key'] = df_funnel['Landing page path'].astype(str).apply(lambda x: x.split('/')[-1] if '/' in x else x)

# --- 4. MERGE DATASETS ---

# We merge the "Upsell Candidate" with its "Funnel Metrics"
# This tells us: "Product B is bought with A (from Orders), AND here is how Product B performs (from Funnel)"
merged_df = pd.merge(
    df_assoc,
    df_funnel[['match_key', 'Completion Rate', 'Abandonment Rate', 'Sessions']],
    on='match_key',
    how='inner' # Only keep matches where we have data for both
)

# --- 5. THE STRATEGY DASHBOARD ---

st.markdown("---")
st.header("🎯 The 3 Golden Segments")

tab1, tab2, tab3 = st.tabs(["🚀 Risk-Free Checkout Upsells", "💰 'Second Chance' Post-Purchase", "📦 Traffic Bundles"])

# SEGMENT 1: CHECKOUT UPSELLS (High Affinity + High Completion)
with tab1:
    st.subheader("Safe Bets for In-Cart / Checkout Page")
    st.markdown("These products are frequently bought together **AND** represent 'Low Friction' (easy to sell).")
    
    # Logic: Bought together often (>5 times) AND Upsell has >50% Completion Rate
    checkout_upsells = merged_df[
        (merged_df['Completion Rate'] > 50) &
        (merged_df['Count'] >= 5)
    ].sort_values(['Count', 'Completion Rate'], ascending=[False, False])
    
    st.dataframe(
        checkout_upsells[['Main Product', 'Upsell Candidate', 'Count', 'Completion Rate']],
        use_container_width=True
    )
    
    if not checkout_upsells.empty:
        best = checkout_upsells.iloc[0]
        st.success(f"🌟 **Top Recommendation:** When someone buys **{best['Main Product']}**, offer **{best['Upsell Candidate']}** in the cart. It has a {best['Completion Rate']:.1f}% completion rate!")

# SEGMENT 2: POST-PURCHASE (High Affinity + High Abandonment)
with tab2:
    st.subheader("High Value Post-Purchase Offers")
    st.markdown("People want these with the main product, but usually abandon them. **Offer these AFTER payment with a discount.**")
    
    # Logic: Bought together often AND Upsell has High Abandonment (>60%)
    post_purchase = merged_df[
        (merged_df['Abandonment Rate'] > 60) &
        (merged_df['Count'] >= 3)
    ].sort_values(['Count', 'Abandonment Rate'], ascending=[False, False])
    
    st.dataframe(
        post_purchase[['Main Product', 'Upsell Candidate', 'Count', 'Abandonment Rate']],
        use_container_width=True
    )
    
    if not post_purchase.empty:
        best_pp = post_purchase.iloc[0]
        st.info(f"💡 **Opportunity:** **{best_pp['Upsell Candidate']}** is often paired with **{best_pp['Main Product']}** but has a {best_pp['Abandonment Rate']:.1f}% abandonment rate. It's a perfect candidate for a 'One-Click Upsell' offer.")

# SEGMENT 3: TRAFFIC BUNDLES
with tab3:
    st.subheader("High Traffic Bundles")
    st.markdown("These pairs have high affinity, and the Upsell product has high visibility. Good for 'Frequently Bought Together' widgets on product pages.")
    
    # Logic: High Volume
    bundles = merged_df.sort_values('Count', ascending=False).head(15)
    
    st.dataframe(
        bundles[['Main Product', 'Upsell Candidate', 'Count', 'Sessions']],
        use_container_width=True
    )
