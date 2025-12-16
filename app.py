import streamlit as st
from fredapi import Fred
import pandas as pd

# --- 1. CONFIGURATION ---
# ⚠️ PASTE YOUR API KEY HERE
API_KEY = 'e9c0ff93e863850792b45ad43f8fbf0e' 

st.set_page_config(page_title="EUR/USD Fundamental Command Center", page_icon="💶", layout="wide")

# --- 2. CONNECT TO DATA ---
try:
    fred = Fred(api_key=API_KEY)
except:
    st.error("🚨 Error: Please enter a valid FRED API Key in the code.")
    st.stop()

# --- 3. HELPER FUNCTIONS ---
def get_latest(series_id):
    """Fetches the absolute latest value."""
    try:
        data = fred.get_series(series_id)
        return data.iloc[-1]
    except:
        return None

def get_mom_change(series_id):
    """Calculates Month-over-Month % Change (for Retail, Earnings)."""
    try:
        data = fred.get_series(series_id)
        current = data.iloc[-1]
        prev = data.iloc[-2]
        return ((current - prev) / prev) * 100
    except:
        return None

def get_change_value(series_id):
    """Calculates absolute change (for NFP Jobs added)."""
    try:
        data = fred.get_series(series_id)
        return data.iloc[-1] - data.iloc[-2]
    except:
        return None

# --- 4. FETCH DATA (THE ENGINE) ---
with st.spinner('Fetching live economic data...'):
    
    # 1. GERMAN MANUFACTURING HEALTH (Proxy for Flash PMI)
    # Series: Production of Total Industry in Germany (DEUPROINDMISMEI)
    # Logic: Rising = Bullish EUR
    ger_manuf = get_mom_change('DEUPROINDMISMEI')

    # 2. WEEKLY EMPLOYMENT HEALTH (Proxy for ADP Weekly)
    # Series: Initial Claims (ICSA) - The #1 Weekly Labor Metric
    # Logic: LOWER claims = Bullish USD
    us_claims = get_latest('ICSA')

    # 3. AVERAGE HOURLY EARNINGS m/m
    # Series: Avg Hourly Earnings of All Employees, Total Private (CES0500000003)
    us_earnings_mom = get_mom_change('CES0500000003')

    # 4. CORE RETAIL SALES m/m
    # Series: Advance Retail Sales: Excl. Motor Vehicle & Parts (RSXFS)
    us_retail_mom = get_mom_change('RSXFS')

    # 5. NON-FARM EMPLOYMENT CHANGE (NFP)
    # Series: All Employees, Total Nonfarm (PAYEMS) -> We calculate the 'Change'
    us_nfp_change = get_change_value('PAYEMS') # Returns eg. 150 (thousands)

    # 6. UNEMPLOYMENT RATE
    # Series: Unemployment Rate (UNRATE)
    us_unemp = get_latest('UNRATE')

    # 7. US MANUFACTURING HEALTH (Proxy for Flash PMI)
    # Series: Industrial Production: Manufacturing (IPMAN)
    us_manuf_mom = get_mom_change('IPMAN')

# --- 5. LOGIC & WINNER CALCULATION ---
def judge_indicator(name, us_val, eu_val=None):
    """
    Decides if the data is Bullish for USD or EUR.
    """
    if us_val is None: return "No Data"

    # A. Special Logic for Single-Currency Metrics (US Data)
    if name == "US Jobless Claims":
        # Lower claims = Strong Economy = Bullish USD
        if us_val < 220000: return "USD 🇺🇸 (Strong Labor)"
        elif us_val > 250000: return "EUR 🇪🇺 (Weak USD Labor)"
        else: return "Neutral"

    if name == "US NFP Change":
        # More jobs = Bullish USD
        if us_val > 150: return "USD 🇺🇸 (Booming Jobs)"
        elif us_val < 100: return "EUR 🇪🇺 (Weak Hiring)"
        else: return "Neutral"
        
    if name == "US Earnings":
        # Higher earnings = Inflation fear = Fed Hikes = Bullish USD
        if us_val > 0.3: return "USD 🇺🇸 (Inflation Risk)"
        else: return "Neutral"

    # B. Comparison Logic (US vs Germany/EU)
    if name == "Manufacturing":
        # Compare US Manuf Growth vs German Manuf Growth
        if eu_val is None: return "No Data"
        diff = us_val - eu_val
        if diff > 0.5: return "USD 🇺🇸 (US Factories Stronger)"
        elif diff < -0.5: return "EUR 🇪🇺 (German Factories Stronger)"
        else: return "Tie ⚪"

    return "Neutral"

# --- 6. DISPLAY DASHBOARD ---
st.title("🇪🇺 EUR/USD: Advanced Economic Calendar Dashboard")
st.markdown("### 📊 Live Fundamental Indicators (Auto-Updated)")

# We build the data row by row
data = [
    {
        "Indicator": "1. German Manufacturing (Proxy)",
        "Value (Latest)": f"{ger_manuf:.2f}% (MoM)" if ger_manuf else "No Data",
        "Bias Impact": judge_indicator("Manufacturing", us_manuf_mom, ger_manuf)
    },
    {
        "Indicator": "2. US Weekly Jobless Claims (Proxy for ADP)",
        "Value (Latest)": f"{int(us_claims):,} Claims",
        "Bias Impact": judge_indicator("US Jobless Claims", us_claims)
    },
    {
        "Indicator": "3. US Avg Hourly Earnings (m/m)",
        "Value (Latest)": f"{us_earnings_mom:.2f}%",
        "Bias Impact": judge_indicator("US Earnings", us_earnings_mom)
    },
    {
        "Indicator": "4. US Core Retail Sales (m/m)",
        "Value (Latest)": f"{us_retail_mom:.2f}%",
        "Bias Impact": "USD 🇺🇸 (Strong Consumer)" if us_retail_mom and us_retail_mom > 0.3 else "Neutral"
    },
    {
        "Indicator": "5. US Non-Farm Payrolls (Change)",
        "Value (Latest)": f"+{int(us_nfp_change)}k Jobs",
        "Bias Impact": judge_indicator("US NFP Change", us_nfp_change)
    },
    {
        "Indicator": "6. US Unemployment Rate",
        "Value (Latest)": f"{us_unemp:.1f}%",
        "Bias Impact": "EUR 🇪🇺 (Bearish USD)" if us_unemp > 4.2 else "USD 🇺🇸 (Bullish)"
    },
    {
        "Indicator": "7. US Manufacturing (Proxy)",
        "Value (Latest)": f"{us_manuf_mom:.2f}% (MoM)",
        "Bias Impact": judge_indicator("Manufacturing", us_manuf_mom, ger_manuf)
    }
]

df = pd.DataFrame(data)
st.table(df)

# --- 7. AUTOMATIC CONCLUSION ---
usd_score = df['Bias Impact'].str.contains("USD").sum()
eur_score = df['Bias Impact'].str.contains("EUR").sum()

st.divider()
st.subheader("🤖 Algorithmic Forecast")

if usd_score > eur_score:
    st.error(f"### 📉 VERDICT: BEARISH EUR/USD (Score: {usd_score} vs {eur_score})")
    st.write("US Data is currently overpowering European Data. Favor **Short** positions.")
elif eur_score > usd_score:
    st.success(f"### 📈 VERDICT: BULLISH EUR/USD (Score: {eur_score} vs {usd_score})")
    st.write("Weak US Data or Strong German Data is lifting the Euro. Favor **Long** positions.")
else:
    st.warning("### ⚖️ VERDICT: NEUTRAL / MIXED")
    st.write("Data is conflicting. Volatility expected but no clear trend.")

if st.button("🔄 Refresh Data"):
    st.rerun()
