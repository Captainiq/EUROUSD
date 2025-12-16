import streamlit as st
from fredapi import Fred
import pandas as pd

# --- 1. CONFIGURATION ---
# ⚠️ PASTE YOUR API KEY HERE
API_KEY = 'e9c0ff93e863850792b45ad43f8fbf0e' 

st.set_page_config(page_title="EUR/USD Event Analyzer", page_icon="📉", layout="wide")

# --- 2. CONNECT TO DATA ---
try:
    fred = Fred(api_key=API_KEY)
except:
    st.error("🚨 Error: Please enter a valid FRED API Key.")
    st.stop()

# --- 3. HELPER FUNCTIONS ---
def get_latest(series_id):
    """Fetches the latest value and date."""
    try:
        data = fred.get_series(series_id)
        return data.iloc[-1], data.index[-1]
    except:
        return None, None

def get_mom_change(series_id):
    """Calculates Month-over-Month change (Actual value difference)."""
    try:
        data = fred.get_series(series_id)
        return data.iloc[-1] - data.iloc[-2]
    except:
        return 0.0

def get_pct_change(series_id):
    """Calculates Month-over-Month % change."""
    try:
        data = fred.get_series(series_id)
        return ((data.iloc[-1] - data.iloc[-2]) / data.iloc[-2]) * 100
    except:
        return 0.0

# --- 4. FETCH DATA (EXPANDED) ---
with st.spinner('Fetching latest Labor, Retail, and Production data...'):
    
    # --- EXISTING MACRO DATA ---
    us_rate, _ = get_latest('DFEDTARU') # Fed Rate
    if us_rate is None: us_rate = 3.75
    eu_rate, _ = get_latest('ECBDFR')   # ECB Rate
    us_10y, _ = get_latest('DGS10')     # US 10Y Yield

    # --- NEW POINTS FROM SCREENSHOT ---
    
    # 1. US EMPLOYMENT (The "NFP" & "Earnings" Block)
    # Non-Farm Payrolls (PAYEMS) -> We need the CHANGE (Jobs Added)
    nfp_total, nfp_date = get_latest('PAYEMS')
    nfp_change = get_mom_change('PAYEMS') * 1000 # Convert to actual jobs
    
    # Unemployment Rate (UNRATE)
    us_unemp, _ = get_latest('UNRATE')
    
    # Avg Hourly Earnings (CES0500000003) -> MoM % Change
    earnings_mom = get_pct_change('CES0500000003')

    # 2. US CONSUMER (The "Retail Sales" Block)
    # Advance Retail Sales (RSXFS) - Excl. Food Services
    retail_mom = get_pct_change('RSXFS')

    # 3. EUROPEAN PRODUCTION (Proxy for "Flash PMI")
    # Germany Industrial Production (DEUPROINDMISMEI)
    ger_prod_mom = get_pct_change('DEUPROINDMISMEI')
    # France Industrial Production (FRAPROINDMISMEI)
    fra_prod_mom = get_pct_change('FRAPROINDMISMEI')

# --- 5. LOGIC: NEXT DAY BIAS ---
def analyze_bias(nfp_chg, retail_chg, ger_prod):
    score = 0
    reasons = []

    # Labor Logic
    if nfp_chg > 150000: 
        score += 1
        reasons.append("🇺🇸 Strong US Jobs (+150k+)")
    elif nfp_chg < 100000:
        score -= 1
        reasons.append("🇺🇸 Weak US Jobs (<100k)")

    # Retail Logic
    if retail_chg > 0.3:
        score += 1
        reasons.append("🇺🇸 Strong US Shopping (>0.3%)")
    elif retail_chg < 0.0:
        score -= 1
        reasons.append("🇺🇸 US Retail Sales Negative")

    # Europe Logic (Inverse)
    if ger_prod < -0.5:
        score += 1 # Bad for EU = Good for USD pair
        reasons.append("🇪🇺 German Factory Slump")
    elif ger_prod > 0.5:
        score -= 1
        reasons.append("🇪🇺 German Factory Rebound")

    if score > 0: return "BEARISH EUR/USD (Strong USD)", "rw-down", reasons
    elif score < 0: return "BULLISH EUR/USD (Weak USD)", "rw-up", reasons
    else: return "NEUTRAL / MIXED", "scale", reasons

bias_text, icon, bias_reasons = analyze_bias(nfp_change, retail_mom, ger_prod_mom)

# --- 6. DISPLAY DASHBOARD ---
st.title("🇪🇺 EUR/USD: High-Impact Event Dashboard")
st.markdown(f"**Data Date:** {nfp_date.strftime('%Y-%m-%d')}")

# TOP SECTION: BIAS VERDICT
st.markdown("### 🚦 Next Day Bias Verdict")
if "BEARISH" in bias_text:
    st.error(f"### {bias_text}")
elif "BULLISH" in bias_text:
    st.success(f"### {bias_text}")
else:
    st.warning(f"### {bias_text}")

st.write(f"**Drivers:** {', '.join(bias_reasons)}")

st.divider()

# MIDDLE SECTION: THE "SCREENSHOT" DATA POINTS
col1, col2 = st.columns(2)

with col1:
    st.subheader("🇺🇸 US High-Impact Data")
    
    # NFP Card
    st.metric(
        label="Non-Farm Payrolls (Jobs Added)", 
        value=f"{int(nfp_change):,} Jobs",
        delta="Above 150k is Bullish USD" if nfp_change > 150000 else "Below 100k is Bearish USD",
        delta_color="off"
    )
    
    # Unemployment & Earnings
    c1, c2 = st.columns(2)
    c1.metric("Unemployment Rate", f"{us_unemp}%", delta=None)
    c2.metric("Avg Hourly Earnings (MoM)", f"{earnings_mom:.2f}%", help="Higher wages = Inflation Risk")

    # Retail Sales
    st.metric(
        label="Retail Sales (MoM)", 
        value=f"{retail_mom:.2f}%",
        delta="Consumer Spending Strength"
    )

with col2:
    st.subheader("🇪🇺 Eurozone High-Impact Data")
    
    # Germany Card (The Engine)
    st.metric(
        label="🇩🇪 German Industrial Production (MoM)",
        value=f"{ger_prod_mom:.2f}%",
        delta="Proxy for Mfg PMI",
        delta_color="normal" if ger_prod_mom > 0 else "inverse"
    )
    
    # France Card
    st.metric(
        label="🇫🇷 French Industrial Production (MoM)",
        value=f"{fra_prod_mom:.2f}%",
        delta="Proxy for Mfg PMI",
        delta_color="normal" if fra_prod_mom > 0 else "inverse"
    )
    
    # Interest Rate Context
    st.info(f"**ECB Rate:** {eu_rate}% vs **Fed Rate:** {us_rate}%")

# BOTTOM SECTION: TRADING CHEAT SHEET
st.divider()
st.subheader("📝 Trading Plan for Tomorrow")

tab1, tab2 = st.tabs(["📉 If Bearish (Sell)", "📈 If Bullish (Buy)"])

with tab1:
    st.markdown("""
    **Scenario: US Data Strong / EU Weak**
    * **Focus:** Sell Rallies (Short)
    * **Key Level:** Break below 1.0500?
    * **Why:** If US Retail Sales are > 0.3% and German Production is negative, the divergence widens.
    """)

with tab2:
    st.markdown("""
    **Scenario: US Data Weak / EU Resilient**
    * **Focus:** Buy Dips (Long)
    * **Key Level:** Break above 1.0800?
    * **Why:** If US NFP < 100k or Unemployment spikes, the Fed might cut rates faster.
    """)

if st.button("Refresh Live Data"):
    st.rerun()
