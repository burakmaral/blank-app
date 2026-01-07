import streamlit as st
import pandas as pd
from itertools import permutations
import re

st.set_page_config(page_title="Ramadan Unified Strategy (Debug)", layout="wide")
st.title("🌙 Ramadan Strategy (Debug Mode)")

# --- 1. LOAD DATA ---
@st.cache_data
def load_funnel_data():
    df = pd.read_csv("session-added-to-cart-reached-checkout-completed.csv")
    df['Landing page type'] = df['Landing page type'].fillna('Unknown')
    return df

@st.cache_data
def load_transaction_data():
    df = pd.read_csv("ramadan_transactions.csv")
    df.columns = [c.lower().replace(' ', '_').replace('.', '') for c in df.columns]
    return df

try:
    df_funnel = load_funnel_data()
    df_orders = load_transaction_data()
except Exception as e:
    st.error(f"Error loading files: {e}")
    st.stop()

# --- 2. PROCESS BASKETS ---
order_col = [c for c in df_orders.columns if 'order' in c and 'name' in c][0]
product_col = [c for c in df_orders.columns if 'product' in c and 'title' in c][0]

baskets = df_orders.groupby(order_col)[product_col].apply(list).reset_index()
baskets = baskets[baskets[product_col].apply(len) > 1]

pairs = []
for basket in baskets[product_col]:
    for p in permutations(set(basket), 2):
        pairs.append(p)

df_pairs = pd.DataFrame(pairs, columns=['Main Product', 'Upsell Candidate'])
df_pairs['Count'] = 1
df_assoc = df_pairs.groupby(['Main Product', 'Upsell Candidate']).count().reset_index()
# RELAXED RULE: Lowered threshold from 3 to 1 to ensure we see data
df_assoc = df_assoc[df_assoc['Count'] >= 1] 

# --- 3. PROCESS FUNNEL ---
df_funnel['Completion Rate'] = (df_funnel['Sessions that completed checkout'] / df_funnel['Sessions that reached checkout'] * 100).fillna(0)
df_funnel['Abandonment Rate'] = ((df_funnel['Sessions with cart additions'] - df_funnel['Sessions that reached checkout']) / df_funnel['Sessions with cart additions'] * 100).fillna(0)

# --- 4. MATCHING LOGIC (THE FIX) ---
def create_slug(text):
    if not isinstance(text, str): return ""
    text = text.lower().strip()
    text = re.sub(r'[^a-z0-9\s]', '', text) # Remove special chars
    return text.replace(' ', '-')

# Create Keys
df_assoc['match_key'] = df_assoc['Upsell Candidate'].apply(create_slug)
# Handle standard Shopify URL structure '/products/handle'
df_funnel['match_key'] = df_funnel['Landing page path'].astype(str).apply(lambda x: x.split('/')[-1] if '/' in x else x)

# --- 5. MERGE ---
merged_df = pd.merge(
    df_assoc,
    df_funnel[['match_key', 'Completion Rate', 'Abandonment Rate', 'Sessions']],
    on='match_key',
    how='inner'
)

# --- DASHBOARD ---
tab1, tab2, tab3, tab4 = st.tabs(["🚀 Risk-Free Upsells", "💰 Post-Purchase", "📦 Bundles", "🔧 Debug Data"])

with tab1:
    st.subheader("Safe Bets (Checkout Upsells)")
    # RELAXED RULES: Lowered Completion Rate to >20% and Count to >=2
    checkout_upsells = merged_df[
        (merged_df['Completion Rate'] > 20) &
        (merged_df['Count'] >= 2)
    ].sort_values(['Count', 'Completion Rate'], ascending=[False, False])
    
    if checkout_upsells.empty:
        st.warning("⚠️ Still empty. Check the 'Debug Data' tab.")
    else:
        st.dataframe(checkout_upsells, use_container_width=True)

with tab2:
    st.subheader("Post-Purchase Opportunities")
    post_purchase = merged_df[
        (merged_df['Abandonment Rate'] > 40) &
        (merged_df['Count'] >= 2)
    ].sort_values(['Count', 'Abandonment Rate'], ascending=[False, False])
    st.dataframe(post_purchase, use_container_width=True)

with tab3:
    st.subheader("Traffic Bundles")
    bundles = merged_df.sort_values('Count', ascending=False).head(15)
    st.dataframe(bundles, use_container_width=True)

with tab4:
    st.subheader("🔧 Why is my data not matching?")
    st.markdown("This tab shows you what the code is trying to match. If the 'Match Key' in the left table doesn't look EXACTLY like the right table, the merge fails.")
    
    col1, col2 = st.columns(2)
    with col1:
        st.write("### 1. Your Order Data (What people bought)")
        st.write("We converted Product Titles to these Keys:")
        st.dataframe(df_assoc[['Upsell Candidate', 'match_key']].head(10), use_container_width=True)
        
    with col2:
        st.write("### 2. Your Funnel Data (Web Traffic)")
        st.write("We converted Landing Page URLs to these Keys:")
        st.dataframe(df_funnel[['Landing page path', 'match_key']].head(10), use_container_width=True)

    st.write("### 3. Merge Result")
    st.metric("Total Successful Matches", len(merged_df))
    if len(merged_df) == 0:
        st.error("❌ 0 Matches found. The keys above do not match.")
