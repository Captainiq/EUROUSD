import streamlit as st
from fredapi import Fred
import pandas as pd
import yfinance as yf # NEW: For Live News

# --- 1. CONFIGURATION ---
# ⚠️ PASTE YOUR API KEY HERE
API_KEY = 'e9c0ff93e863850792b45ad43f8fbf0e' 

st.set_page_config(page_title="EUR/USD Command Center", page_icon="💶", layout="wide")

# --- 2. CONNECT TO DATA ---
try:
    fred = Fred(api_key=API_KEY)
except:
    st.error("🚨 Error: Please enter a valid FRED API Key.")
    st.stop()

# --- 3. HELPER FUNCTIONS ---
def get_latest(series_id):
    try:
        data = fred.get_series(series_id)
        return data.iloc[-1]
    except:
        return None

def get_mom_change(series_id):
    try:
        data = fred.get_series(series_id)
        return ((data.iloc[-1] - data.iloc[-2]) / data.iloc[-2]) * 100
    except:
        return None

def get_change_value(series_id):
    try:
        data = fred.get_series(series_id)
        return data.iloc[-1] - data.iloc[-2]
    except:
        return None

# --- 4. FETCH MACRO DATA ---
with st.spinner('Fetching Macro Data, Sentiment & News...'):
    # ... (Your Original Indicators) ...
    ger_manuf = get_mom_change('DEUPROINDMISMEI')
    us_claims = get_latest('ICSA')
    us_earnings_mom = get_mom_change('CES0500000003')
    us_retail_mom = get_mom_change('RSXFS')
    us_nfp_change = get_change_value('PAYEMS')
    us_unemp = get_latest('UNRATE')
    us_manuf_mom = get_mom_change('IPMAN')
    
    # ... (Interest Rates for Header) ...
    us_rate = get_latest('DFEDTARU') or 3.75    eu_rate = get_latest('ECBDFR') or 2.00

    # ... (NEW: Sentiment Indicators) ...
    # 1. VIX (Fear Index) - VIXCLS
    vix = get_latest('VIXCLS')
    # 2. US 10Y-2Y Yield Spread (Recession Signal) - T10Y2Y
    yield_curve = get_latest('T10Y2Y')
    # 3. Oil Price (WTI) - DCOILWTICO
    oil_price = get_latest('DCOILWTICO')

# --- 5. LOGIC ---
def judge_indicator(name, us_val, eu_val=None):
    if us_val is None: return "No Data"
    
    if name == "US Jobless Claims":
        if us_val < 220000: return "USD 🇺🇸 (Strong Labor)"
        elif us_val > 250000: return "EUR 🇪🇺 (Weak USD Labor)"
        else: return "Neutral"
    if name == "US NFP Change":
        if us_val > 150: return "USD 🇺🇸 (Booming Jobs)"
        elif us_val < 100: return "EUR 🇪🇺 (Weak Hiring)"
        else: return "Neutral"
    if name == "US Earnings":
        if us_val > 0.3: return "USD 🇺🇸 (Inflation Risk)"
        else: return "Neutral"
    if name == "Manufacturing":
        if eu_val is None: return "No Data"
        diff = us_val - eu_val
        if diff > 0.5: return "USD 🇺🇸 (US Mfg Stronger)"
        elif diff < -0.5: return "EUR 🇪🇺 (German Mfg Stronger)"
        else: return "Tie ⚪"
    return "Neutral"

# --- 6. LAYOUT & SIDEBAR NEWS ---

# SIDEBAR: LIVE NEWS FEED
st.sidebar.title("📰 Live News Feed")
st.sidebar.caption("Source: Yahoo Finance (EUR=X)")
try:
    # Fetch news for EUR/USD
    ticker = yf.Ticker("EURUSD=X")
    news_list = ticker.news
    
    for item in news_list[:5]: # Show top 5
        st.sidebar.markdown(f"**[{item['title']}]({item['link']})**")
        st.sidebar.caption(f"Publisher: {item['publisher']}")
        st.sidebar.divider()
except:
    st.sidebar.warning("Could not fetch live news.")

# MAIN PAGE
st.title("🇪🇺 EUR/USD Command Center")

# SECTION A: RISK RADAR (NEW)
st.subheader("⚠️ Market Sentiment & Risk Radar")
col1, col2, col3 = st.columns(3)

# VIX Logic
vix_color = "inverse" if vix and vix > 20 else "normal"
col1.metric("VIX (Fear Gauge)", f"{vix:.2f}", delta="Risk Off > 20" if vix > 20 else "Stable", delta_color=vix_color)

# Yield Curve Logic
yc_color = "inverse" if yield_curve and yield_curve < 0 else "normal"
col2.metric("Yield Curve (10Y-2Y)", f"{yield_curve:.2f}%", "Recession Warning" if yield_curve < 0 else "Normal", delta_color=yc_color)

# Oil Logic
col3.metric("WTI Crude Oil", f"${oil_price:.2f}", "High Oil hurts EU" if oil_price > 85 else None)

st.divider()

# SECTION B: MACRO DASHBOARD (Your Existing Data)
st.subheader("📊 Fundamental Economic Data")

data = [
    {
        "Indicator": "1. German Manufacturing (Proxy)",
        "Value (Latest)": f"{ger_manuf:.2f}% (MoM)" if ger_manuf else "No Data",
        "Bias Impact": judge_indicator("Manufacturing", us_manuf_mom, ger_manuf)
    },
    {
        "Indicator": "2. US Weekly Jobless Claims",
        "Value (Latest)": f"{int(us_claims):,} Claims",
        "Bias Impact": judge_indicator("US Jobless Claims", us_claims)
    },
    {
        "Indicator": "3. US Avg Hourly Earnings",
        "Value (Latest)": f"{us_earnings_mom:.2f}%",
        "Bias Impact": judge_indicator("US Earnings", us_earnings_mom)
    },
    {
        "Indicator": "4. US Core Retail Sales",
        "Value (Latest)": f"{us_retail_mom:.2f}%",
        "Bias Impact": "USD 🇺🇸 (Strong Consumer)" if us_retail_mom and us_retail_mom > 0.3 else "Neutral"
    },
    {
        "Indicator": "5. US NFP (Jobs Added)",
        "Value (Latest)": f"+{int(us_nfp_change)}k Jobs",
        "Bias Impact": judge_indicator("US NFP Change", us_nfp_change)
    },
    {
        "Indicator": "6. US Unemployment Rate",
        "Value (Latest)": f"{us_unemp:.1f}%",
        "Bias Impact": "EUR 🇪🇺 (Bearish USD)" if us_unemp > 4.2 else "USD 🇺🇸"
    },
    {
        "Indicator": "7. US Manufacturing (Proxy)",
        "Value (Latest)": f"{us_manuf_mom:.2f}% (MoM)",
        "Bias Impact": judge_indicator("Manufacturing", us_manuf_mom, ger_manuf)
    }
]

df = pd.DataFrame(data)
st.table(df)

# SECTION C: VERDICT
usd_score = df['Bias Impact'].str.contains("USD").sum()
eur_score = df['Bias Impact'].str.contains("EUR").sum()

st.subheader("🤖 Final Verdict")
if usd_score > eur_score:
    st.error(f"BEARISH EUR/USD (USD Wins {usd_score}-{eur_score})")
elif eur_score > usd_score:
    st.success(f"BULLISH EUR/USD (Euro Wins {eur_score}-{usd_score})")
else:
    st.warning("NEUTRAL / CHOPPY")

if st.button("🔄 Refresh Data"):
    st.rerun()

