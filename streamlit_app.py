import requests
import json
import time
import pandas as pd
import streamlit as st

# ----- CONFIG -----
st.set_page_config(page_title="ETF Performance Dashboard", layout="wide")

URL = "https://api.tickertape.in/screener/query"
HEADERS = {
    "Content-Type": "application/json",
    "User-Agent": "Mozilla/5.0"
}

payload_template = {
    "match": {
        "subindustry": ["E_G", "E_Q", "E_D"]
    },
    "sortBy": "mrktCapf",
    "sortOrder": -1,
    "project": [
        "subindustry", "mrktCapf", "lastPrice", "pr1d",
        "4wpct", "26wpct", "52wpct", "12mVolN", "expenseRatio"
    ],
    "offset": 0,
    "count": 20,
    "sids": []
}

# ----- FETCH FUNCTION -----
def fetch_etf_data():
    total_results = 271
    count = 20
    all_data = []

    for offset in range(0, total_results, count):
        payload = payload_template.copy()
        payload["offset"] = offset
        response = requests.post(URL, headers=HEADERS, data=json.dumps(payload))

        if response.status_code == 200:
            results = response.json().get("data", {}).get("results", [])
            for item in results:
                stock_info = item.get("stock", {})
                ratios = stock_info.get("advancedRatios", {})
                info = stock_info.get("info", {})

                row = {
                    "Name": info.get("name", ""),
                    "Sub-Sector": ratios.get("subindustry", ""),
                    "↓Market Cap": ratios.get("mrktCapf", 'NA'),
                    "Close Price": ratios.get("lastPrice", 'NA'),
                    "1D Return": ratios.get("pr1d", 'NA'),
                    "1M Return": ratios.get("4wpct", 'NA'),
                    "6M Return": ratios.get("26wpct", 'NA'),
                    "1Y Return": ratios.get("52wpct", 'NA'),
                    "Volatility vs Nifty": ratios.get("12mVolN", 'NA'),
                    "Expense Ratio": ratios.get("expenseRatio", 'NA')
                }
                all_data.append(row)
        else:
            st.error(f"Failed at offset {offset}: {response.status_code}")
        time.sleep(1)

    df = pd.DataFrame(all_data)
    df.dropna(inplace=True)
    df.columns = df.columns.str.strip().str.replace('↓', '').str.replace(' ', '_')
    numeric_cols = [
        'Market_Cap', 'Close_Price', '1D_Return', '1M_Return',
        '6M_Return', '1Y_Return', 'Volatility_vs_Nifty', 'Expense_Ratio'
    ]
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    df.dropna(inplace=True)
    return df

# ----- FETCH BUTTON -----
st.title("📊 ETF Performance Dashboard")

if "etf_data" not in st.session_state:
    st.session_state.etf_data = None

if st.button("📥 Fetch Latest ETF Data"):
    with st.spinner("Fetching data..."):
        st.session_state.etf_data = fetch_etf_data()
    st.success("✅ Data fetched and loaded.")

# ----- IF DATA IS NOT LOADED -----
if st.session_state.etf_data is None:
    st.warning("Please click the button above to fetch ETF data.")
    st.stop()

df = st.session_state.etf_data.copy()

# ----- SELECT PERFORMANCE METRIC -----
metric_map = {
    "1 Day Return": "1D_Return",
    "30 Day Return": "1M_Return",
    "6 Month Return": "6M_Return",
    "1 Year Return": "1Y_Return"
}

selected_metric_label = st.selectbox("📈 Select Performance Metric", list(metric_map.keys()), index=3)
metric_col = metric_map[selected_metric_label]

top_n = st.sidebar.slider("Top/Bottom N ETFs", 10, len(df), 50)

# ----- SPLIT TOP & UNDERPERFORMERS -----
top_df = df.sort_values(by=metric_col, ascending=False).head(top_n)
under_df = df.sort_values(by=metric_col, ascending=True).head(top_n)

# ----- TOP PERFORMERS -----
with st.expander("🔼 Top Performer ETFs", expanded=True):
    st.subheader(f"Top ETFs by {selected_metric_label}")

    with st.sidebar:
        st.markdown("### 🎚️ Filters for Top Performers")
        top_expense = st.slider("Expense Ratio", float(top_df['Expense_Ratio'].min()), float(top_df['Expense_Ratio'].max()),
                                (float(top_df['Expense_Ratio'].min()), float(top_df['Expense_Ratio'].max())))
        top_mcap = st.slider("Market Cap", float(top_df['Market_Cap'].min()), float(top_df['Market_Cap'].max()),
                             (float(top_df['Market_Cap'].min()), float(top_df['Market_Cap'].max())))

    top_filtered = top_df[
        (top_df['Expense_Ratio'] >= top_expense[0]) & (top_df['Expense_Ratio'] <= top_expense[1]) &
        (top_df['Market_Cap'] >= top_mcap[0]) & (top_df['Market_Cap'] <= top_mcap[1])
    ]

    st.dataframe(top_filtered.reset_index(drop=True), use_container_width=True)
    st.bar_chart(top_filtered.set_index('Name')[metric_col])

# ----- UNDERPERFORMERS -----
with st.expander("🔽 Underperformer ETFs", expanded=True):
    st.subheader(f"Underperforming ETFs by {selected_metric_label}")

    with st.sidebar:
        st.markdown("### 🎚️ Filters for Underperformers")
        under_expense = st.slider("Under: Expense Ratio", float(under_df['Expense_Ratio'].min()), float(under_df['Expense_Ratio'].max()),
                                  (float(under_df['Expense_Ratio'].min()), float(under_df['Expense_Ratio'].max())))
        under_mcap = st.slider("Under: Market Cap", float(under_df['Market_Cap'].min()), float(under_df['Market_Cap'].max()),
                               (float(under_df['Market_Cap'].min()), float(under_df['Market_Cap'].max())))

    under_filtered = under_df[
        (under_df['Expense_Ratio'] >= under_expense[0]) & (under_df['Expense_Ratio'] <= under_expense[1]) &
        (under_df['Market_Cap'] >= under_mcap[0]) & (under_df['Market_Cap'] <= under_mcap[1])
    ]

    st.dataframe(under_filtered.reset_index(drop=True), use_container_width=True)
    st.bar_chart(under_filtered.set_index('Name')[metric_col])
