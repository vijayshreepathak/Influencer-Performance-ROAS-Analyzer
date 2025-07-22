import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np
import datetime

# --- Dynamic Greeting ---
hour = datetime.datetime.now().hour
if hour < 12:
    st.success('Good morning! ☀️ Ready to analyze your influencer campaigns?')
elif hour < 18:
    st.info("Good afternoon! Let's boost your ROI insights. 🚀")
else:
    st.warning('Good evening! Time for some data magic. ✨')

# --- Page Config ---
st.set_page_config(page_title='HealthKart Influencer ROI Dashboard', layout='wide')
st.markdown('<style>div.block-container{padding-top:2rem;}</style>', unsafe_allow_html=True)

# --- Load Data ---
influencers = pd.read_csv('influencers.csv')
posts = pd.read_csv('posts.csv')
tracking_data = pd.read_csv('tracking_data.csv')
payouts = pd.read_csv('payouts.csv')

# --- Data Merging and Preprocessing ---

# Total payout (cost) per influencer
influencer_cost = payouts.groupby('influencer_id')['total_payout'].sum().reset_index().rename(columns={'total_payout': 'total_cost'})

# Total revenue per influencer (from tracking_data, only influencer source)
influencer_revenue = tracking_data[tracking_data['source'] == 'influencer'].groupby('influencer_id')['revenue'].sum().reset_index().rename(columns={'revenue': 'total_revenue'})

# Merge influencer details with cost and revenue
influencer_summary = influencers.merge(influencer_cost, on='influencer_id', how='left')
influencer_summary = influencer_summary.merge(influencer_revenue, on='influencer_id', how='left')

# Fill NaN with 0 for cost/revenue (in case of missing data)
influencer_summary['total_cost'] = influencer_summary['total_cost'].fillna(0)
influencer_summary['total_revenue'] = influencer_summary['total_revenue'].fillna(0)

# Merge posts and tracking_data for detailed analysis (optional, for later use)
posts_with_influencer = posts.merge(influencers, on=['influencer_id', 'platform'], how='left')
tracking_with_influencer = tracking_data.merge(influencers, on='influencer_id', how='left')

# --- Core Metric Calculations ---

def calculate_roas(df):
    # Avoid division by zero
    return df['total_revenue'] / df['total_cost'].replace(0, np.nan)

def calculate_incremental_roas(tracking_data, influencer_summary, start_date=None, end_date=None):
    # Filter by date if provided
    td = tracking_data.copy()
    td['transaction_date'] = pd.to_datetime(td['transaction_date'])
    if start_date and end_date:
        td = td[(td['transaction_date'] >= start_date) & (td['transaction_date'] <= end_date)]
    # Baseline: non-influencer sources
    baseline = td[td['source'].isin(['organic', 'paid_ad'])]
    if baseline.empty:
        baseline_daily_revenue = 0
        n_days = 1
    else:
        baseline['transaction_date'] = pd.to_datetime(baseline['transaction_date'])
        daily_baseline = baseline.groupby('transaction_date')['revenue'].sum()
        baseline_daily_revenue = daily_baseline.mean()
        n_days = (td['transaction_date'].max() - td['transaction_date'].min()).days + 1
    # Influencer revenue
    influencer_rev = td[td['source'] == 'influencer'].groupby('influencer_id')['revenue'].sum()
    # Incremental revenue per influencer
    incremental_revenue = influencer_rev - (baseline_daily_revenue * n_days / len(influencer_rev) if len(influencer_rev) > 0 else 0)
    # Merge with payouts
    payout_map = influencer_summary.set_index('influencer_id')['total_cost']
    incremental_roas = incremental_revenue / payout_map
    return incremental_roas.fillna(0)

# Add ROAS to influencer_summary
df = influencer_summary.copy()
df['ROAS'] = calculate_roas(df).fillna(0)

# Add Incremental ROAS (for full period, will be dynamic later)
df['Incremental_ROAS'] = calculate_incremental_roas(tracking_data, df)

influencer_summary = df

# --- Sidebar Filters ---
with st.sidebar:
    st.header('🧰 Filters')
    products = tracking_data['product'].dropna().unique().tolist()
    selected_products = st.multiselect('Brand/Product', products, default=products)
    platforms = influencers['platform'].dropna().unique().tolist()
    selected_platforms = st.multiselect('Platform', platforms, default=platforms)
    categories = influencers['category'].dropna().unique().tolist()
    selected_categories = st.multiselect('Influencer Category', categories, default=categories)
    tracking_data['transaction_date'] = pd.to_datetime(tracking_data['transaction_date'])
    min_date = tracking_data['transaction_date'].min()
    max_date = tracking_data['transaction_date'].max()
    date_range = st.date_input('Analysis Period', [min_date, max_date], min_value=min_date, max_value=max_date)

# --- Filter Data ---
filtered_tracking = tracking_data[
    (tracking_data['product'].isin(selected_products)) &
    (tracking_data['transaction_date'] >= pd.to_datetime(date_range[0])) &
    (tracking_data['transaction_date'] <= pd.to_datetime(date_range[1]))
]

filtered_influencers = influencers[
    (influencers['platform'].isin(selected_platforms)) &
    (influencers['category'].isin(selected_categories))
]

filtered_summary = influencer_summary[
    (influencer_summary['platform'].isin(selected_platforms)) &
    (influencer_summary['category'].isin(selected_categories))
]

# --- KPI Section ---
# Recalculate metrics for filtered data
filtered_ids = filtered_influencers['influencer_id'].tolist()
filtered_summary = filtered_summary[filtered_summary['influencer_id'].isin(filtered_ids)]

# Total Revenue (from influencer sales in filtered period)
total_revenue = filtered_tracking[filtered_tracking['source'] == 'influencer']
total_revenue = total_revenue[total_revenue['influencer_id'].isin(filtered_ids)]['revenue'].sum()
# Total Spend (payouts)
total_spend = filtered_summary['total_cost'].sum()
# Overall ROAS
overall_roas = total_revenue / total_spend if total_spend > 0 else 0
# Overall Incremental ROAS
# Recalculate incremental ROAS for filtered data
inc_roas = calculate_incremental_roas(filtered_tracking, filtered_summary)
overall_inc_roas = inc_roas.replace([np.inf, -np.inf], np.nan).mean()

# Display KPIs
col1, col2, col3, col4 = st.columns(4)
col1.metric('💰 Total Revenue', f"₹{total_revenue:,.0f}")
col2.metric('Total Spend', f"₹{total_spend:,.0f}")
col3.metric('Overall ROAS', f"{overall_roas:.2f}")
col4.metric('Overall Incremental ROAS', f"{overall_inc_roas:.2f}")

# --- Optional: Download Data as CSV ---
def convert_df_to_csv(df):
    return df.to_csv(index=False).encode('utf-8')

csv_data = convert_df_to_csv(filtered_summary)

# --- Tabs Layout ---
tab1, tab2, tab3 = st.tabs(["📈 KPIs", "📊 Visualizations", "🗃️ Data Table"])

with tab1:
    st.markdown('## 📊 HealthKart Influencer ROI Dashboard')
    st.markdown('---')
    # Card-style KPIs
    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
    kpi1.markdown(f"""
        <div style='background-color:#242526;padding:20px;border-radius:10px;text-align:center'>
        <h4 style='color:#00C49A'>💰 Total Revenue</h4>
        <h2 style='color:white'>₹{total_revenue:,.0f}</h2>
        </div>
        """, unsafe_allow_html=True)
    kpi2.markdown(f"""
        <div style='background-color:#242526;padding:20px;border-radius:10px;text-align:center'>
        <h4 style='color:#00C49A'>💸 Total Spend</h4>
        <h2 style='color:white'>₹{total_spend:,.0f}</h2>
        </div>
        """, unsafe_allow_html=True)
    kpi3.metric('📈 Overall ROAS', f"{overall_roas:.2f}", help="Return on Ad Spend: Revenue / Spend")
    kpi4.metric('✨ Overall Incremental ROAS', f"{overall_inc_roas:.2f}", help="Incremental Revenue / Spend")
    if overall_roas > 2:
        st.balloons()
    st.download_button(
        label='⬇️ Download Data as CSV',
        data=csv_data,
        file_name='influencer_summary_filtered.csv',
        mime='text/csv'
    )

with tab2:
    st.markdown('## 🏆 Influencer Performance Insights')
    # Top 5 Influencers by ROAS (with avatars)
    st.markdown('### 🥇 Top 5 Influencers by ROAS')
    top5_roas = filtered_summary.sort_values('ROAS', ascending=False).head(5)
    for idx, row in top5_roas.iterrows():
        st.markdown(f"<img src='https://ui-avatars.com/api/?name={row['name'].replace(' ', '+')}&background=00C49A&color=fff&size=64' style='border-radius:50%;margin-right:10px;'> <b>{row['name']}</b> ({row['category']}, {row['platform']}) - ROAS: <b>{row['ROAS']:.2f}</b>", unsafe_allow_html=True)
    fig_roas = px.bar(top5_roas, x='name', y='ROAS', color='category',
                      hover_data=['total_revenue', 'total_cost'],
                      labels={'name': 'Influencer', 'ROAS': 'ROAS'},
                      title='Top 5 Influencers by ROAS')
    st.plotly_chart(fig_roas, use_container_width=True)
    # Top 5 by Revenue
    st.markdown('### 💵 Top 5 Influencers by Revenue')
    top5_revenue = filtered_summary.sort_values('total_revenue', ascending=False).head(5)
    fig_revenue = px.bar(top5_revenue, x='name', y='total_revenue', color='category',
                         hover_data=['ROAS', 'total_cost'],
                         labels={'name': 'Influencer', 'total_revenue': 'Revenue'},
                         title='Top 5 Influencers by Revenue')
    st.plotly_chart(fig_revenue, use_container_width=True)
    # Poor ROI Table
    st.markdown('### ⚠️ Influencers with Poor ROI (ROAS < 1)')
    poor_roi = filtered_summary[filtered_summary['ROAS'] < 1][['name', 'category', 'platform', 'total_revenue', 'total_cost', 'ROAS']]
    st.dataframe(poor_roi.style.format({'total_revenue': '₹{:.0f}', 'total_cost': '₹{:.0f}', 'ROAS': '{:.2f}'}), use_container_width=True)
    # Revenue Over Time
    st.markdown('### 📅 Revenue Over Time by Source')
    revenue_time = filtered_tracking.copy()
    revenue_time['transaction_date'] = pd.to_datetime(revenue_time['transaction_date'])
    revenue_time = revenue_time.groupby(['transaction_date', 'source'])['revenue'].sum().reset_index()
    fig_time = px.line(revenue_time, x='transaction_date', y='revenue', color='source',
                       labels={'transaction_date': 'Date', 'revenue': 'Revenue', 'source': 'Source'},
                       title='Revenue Over Time by Source')
    st.plotly_chart(fig_time, use_container_width=True)

with tab3:
    st.markdown('## 🗃️ Detailed Influencer Summary Table')
    st.dataframe(filtered_summary.style.format({'total_revenue': '₹{:.0f}', 'total_cost': '₹{:.0f}', 'ROAS': '{:.2f}', 'Incremental_ROAS': '{:.2f}'}), use_container_width=True)

# --- Custom Theme (config.toml) ---
# To apply a custom theme, create .streamlit/config.toml in your project root with the following:
# [theme]
# base="dark"
# primaryColor="#00C49A"
# backgroundColor="#18191A"
# secondaryBackgroundColor="#242526"
# textColor="#F5F6FA"
# font="sans serif"

# --- Footer ---
footer = '''
<style>
.footer {
    position: fixed;
    left: 0;
    bottom: 0;
    width: 100%;
    background: #18191A;
    color: #F5F6FA;
    text-align: center;
    padding: 10px 0 8px 0;
    font-size: 1rem;
    z-index: 100;
}
.footer a { color: #00C49A; text-decoration: none; font-weight: bold; }
.footer a:hover { text-decoration: underline; }
</style>
<div class="footer">
    Made with ❤️ by <b>Vijayshree Vaibhav</b> | 7x hackathon winner |
    <a href="https://www.linkedin.com/in/vijayshreevaibhav/" target="_blank">LinkedIn</a> |
    <a href="https://vijayshreepathak.netlify.app/" target="_blank">Portfolio</a>
</div>
'''
st.markdown(footer, unsafe_allow_html=True)
