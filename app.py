import streamlit as st
import pandas as pd
from itertools import permutations
import re

st.set_page_config(page_title="Ramadan Unified Strategy", layout="wide")
st.title("🌙 Ramadan Strategy: Funnel + Basket Analysis")

# --- 1. DATA LOADING & CLEANING ---
@st.cache_data
def load_funnel_data():
    # Load Funnel Data
    try:
        df = pd.read_csv("session-added-to-cart-reached-checkout-completed.csv")
        df['Landing page type'] = df['Landing page type'].fillna('Unknown')
        return df
    except Exception as e:
        return None

@st.cache_data
def load_transaction_data():
    # Load Transaction Data
    try:
        df = pd.read_csv("ramadan_transactions.csv")
        # Standardize headers
        df.columns = [c.lower().replace(' ', '_').replace('.', '') for c in df.columns]
        
        # CLEANING STEP: Remove summary rows and returns
        # 1. Drop rows where Product Title is missing
        product_col = 'product_title' # Based on your file inspection
        df = df.dropna(subset=[product_col])
        
        # 2. Keep only positive quantities (removes returns & zero-qty lines)
        if 'quantity_ordered' in df.columns:
            df = df[df['quantity_ordered'] > 0]
            
        return df
    except Exception as e:
        return None

df_funnel = load_funnel_data()
df_orders = load_transaction_data()

if df_funnel is None or df_orders is None:
    st.error("⚠️ Error loading files. Please ensure both CSV files are in the directory.")
    st.stop()
else:
    st.success(f"✅ Loaded Data: {len(df_orders):,} valid transactions | {len(df_funnel):,} funnel pages")

# --- 2. BASKET ANALYSIS (FIND PAIRS) ---
order_col = 'order_name'
product_col = 'product_title'

# Group products by Order
baskets = df_orders.groupby(order_col)[product_col].apply(list).reset_index()
# Keep only orders with 2+ items
baskets = baskets[baskets[product_col].apply(len) > 1]

# Generate Pairs
pairs = []
for basket in baskets[product_col]:
    for p in permutations(set(basket), 2):
        pairs.append(p)

df_pairs = pd.DataFrame(pairs, columns=['Main Product', 'Upsell Candidate'])
df_pairs['Count'] = 1
# Count how often pairs appear together
df_assoc = df_pairs.groupby(['Main Product', 'Upsell Candidate']).count().reset_index()
# Filter: Pair must appear at least 2 times to be considered
df_assoc = df_assoc[df_assoc['Count'] >= 2]

# --- 3. FUNNEL METRICS ---
df_funnel['Completion Rate'] = (df_funnel['Sessions that completed checkout'] / df_funnel['Sessions that reached checkout'] * 100).fillna(0)
df_funnel['Abandonment Rate'] = ((df_funnel['Sessions with cart additions'] - df_funnel['Sessions that reached checkout']) / df_funnel['Sessions with cart additions'] * 100).fillna(0)

# --- 4. INTELLIGENT MATCHING (The Fix) ---
def create_slug(text):
    if not isinstance(text, str): return ""
    text = text.lower().strip()
    # Remove special characters to improve matching chance
    text = re.sub(r'[^a-z0-9\s]', '', text) 
    return text.replace(' ', '-')

# Generate keys for both datasets
df_assoc['match_key'] = df_assoc['Upsell Candidate'].apply(create_slug)
# Extract handle from URL: "/products/black-abaya" -> "black-abaya"
df_funnel['match_key'] = df_funnel['Landing page path'].astype(str).apply(lambda x: x.split('/')[-1] if '/' in x else x)

# MERGE
merged_df = pd.merge(
    df_assoc,
    df_funnel[['match_key', 'Completion Rate', 'Abandonment Rate', 'Sessions']],
    on='match_key',
    how='inner'
)

# --- 5. DASHBOARD ---
tab1, tab2, tab3, tab4 = st.tabs(["🚀 Risk-Free Upsells", "💰 Post-Purchase", "📦 Traffic Bundles", "🔧 Debug Data"])

# STRATEGY 1: CHECKOUT UPSELLS
with tab1:
    st.subheader("🛒 Safe Bets (Checkout Upsells)")
    st.markdown("Products that are bought together **AND** have high completion rates.")
    
    # Relaxed Logic: Count >= 2 and Completion > 20%
    checkout_upsells = merged_df[
        (merged_df['Completion Rate'] > 20)
    ].sort_values(['Count', 'Completion Rate'], ascending=[False, False])
    
    if not checkout_upsells.empty:
        st.dataframe(checkout_upsells[['Main Product', 'Upsell Candidate', 'Count', 'Completion Rate']], use_container_width=True)
    else:
        st.warning("No matches found. Check the 'Debug Data' tab to see name mismatches.")

# STRATEGY 2: POST-PURCHASE
with tab2:
    st.subheader("📦 Second Chance (Post-Purchase)")
    st.markdown("Products frequently bought together but often abandoned. **Offer these after payment.**")
    
    post_purchase = merged_df[
        (merged_df['Abandonment Rate'] > 50)
    ].sort_values(['Count', 'Abandonment Rate'], ascending=[False, False])
    
    if not post_purchase.empty:
        st.dataframe(post_purchase[['Main Product', 'Upsell Candidate', 'Count', 'Abandonment Rate']], use_container_width=True)
    else:
        st.warning("No matches found.")

# STRATEGY 3: TRAFFIC BUNDLES
with tab3:
    st.subheader("🔥 High Volume Bundles")
    st.markdown("The most popular pairs. Use these for 'Frequently Bought Together' widgets.")
    
    # This comes purely from Transaction Data (no matching required), so it should ALWAYS show data
    bundles = df_assoc.sort_values('Count', ascending=False).head(20)
    st.dataframe(bundles, use_container_width=True)

# DEBUG TAB
with tab4:
    st.subheader("🔧 Why is my data not matching?")
    st.markdown("If the tabs above are empty, it's because the **Product Title** (Shopify) doesn't match the **URL Handle** (Funnel Data).")
    
    col1, col2 = st.columns(2)
    with col1:
        st.write("#### 1. From Transaction CSV (Titles)")
        st.dataframe(df_assoc[['Upsell Candidate', 'match_key']].drop_duplicates().head(10), use_container_width=True)
        
    with col2:
        st.write("#### 2. From Funnel CSV (URLs)")
        st.dataframe(df_funnel[['Landing page path', 'match_key']].head(10), use_container_width=True)
        
    st.info(f"**Total Successful Matches:** {len(merged_df)}")
    st.write("If this number is 0 (or low), you need to rename your products or clean the names further.")
