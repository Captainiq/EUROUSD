import streamlit as st
from fredapi import Fred
import pandas as pd
import datetime

# --- 1. CONFIGURATION ---
# ⚠️ PASTE YOUR API KEY INSIDE THE QUOTES BELOW
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
    """Fetches the absolute latest daily value."""
    try:
        data = fred.get_series(series_id)
        return data.iloc[-1], data.index[-1]
    except:
        return None, None

def get_yoy_growth(series_id, is_quarterly=False):
    """Calculates Year-over-Year growth %."""
    try:
        data = fred.get_series(series_id)
        if is_quarterly:
            current = data.iloc[-1]
            prev = data.iloc[-5] 
        else:
            current = data.iloc[-1]
            prev = data.iloc[-13] 
        
        return ((current - prev) / prev) * 100
    except:
        return None

def get_trend(series_id):
    try:
        data = fred.get_series(series_id)
        current = data.iloc[-1]
        prev = data.iloc[-2]
        if current > prev: return "Rising ↗️"
        elif current < prev: return "Falling ↘️"
        else: return "Flat ➡️"
    except:
        return "Unknown"

# --- 4. FETCH DATA ---
with st.spinner('Fetching live economic data...'):
    
    # A. RATES & YIELDS (Crucial for the "Smart" logic)
    us_rate, _ = get_latest('DFEDTARU') 
    if us_rate is None: us_rate, _ = get_latest('DFF')
    eu_rate, _ = get_latest('ECBDFR')   
    if eu_rate is None: eu_rate = 3.25
    
    us_2y_yield, _ = get_latest('DGS2')
    us_10y_yield, _ = get_latest('DGS10')

    # B. INFLATION (CPI YoY)
    us_cpi_val = get_yoy_growth('CPIAUCSL')
    eu_cpi_val = get_yoy_growth('CP0000EZ19M086NEST')

    # C. GDP GROWTH (Real GDP YoY)
    us_gdp_val = get_yoy_growth('GDPC1', is_quarterly=True)
    eu_gdp_val = get_yoy_growth('CLVMNACSCAB1GQEA19', is_quarterly=True)

    # D. UNEMPLOYMENT RATE
    us_unemp, _ = get_latest('UNRATE')
    eu_unemp, _ = get_latest('LRHUTTTTEZM156S') 

    # E. SENTIMENT
    us_sent, _ = get_latest('UMCSENT') 
    eu_sent, _ = get_latest('CSCICP02EZM460S') 
    us_sent_trend = get_trend('UMCSENT')
    eu_sent_trend = get_trend('CSCICP02EZM460S')

    # F. CRUDE OIL
    oil_price, _ = get_latest('DCOILWTICO')

# --- 5. SMART LOGIC (THE FIX) ---
def judge(us, eu, metric):
    if us is None or eu is None: return "No Data"
    diff = us - eu
    
    if metric == 'higher_is_better': 
        if diff > 0.25: return "USD 🇺🇸"
        elif diff < -0.25: return "EUR 🇪🇺"
        else: return "Tie ⚪"
    elif metric == 'lower_is_better': 
        if diff < -0.25: return "USD 🇺🇸" 
        elif diff > 0.25: return "EUR 🇪🇺" 
        else: return "Tie ⚪"
    elif metric == 'inflation': 
        if diff > 0.5: return "USD 🇺🇸 (Hikes?)"
        elif diff < -0.5: return "EUR 🇪🇺 (Hikes?)"
        else: return "Neutral"

def judge_smart_rates(us_rate, eu_rate, us_2y):
    """
    NEW LOGIC: Ignores the current rate if the Market (2Y Yield) expects cuts.
    """
    if us_rate is None or eu_rate is None or us_2y is None: return "No Data"
    
    # 1. Check the Spread (Forward Looking)
    expectation_spread = us_2y - us_rate
    
    if expectation_spread < -0.20:
        # Market expects cuts. Even if US rate is high, it's a "Fake" high.
        return "Neutral ⚪ (Cuts Priced In)"
    
    # 2. If no aggressive cuts expected, use standard comparison
    diff = us_rate - eu_rate
    if diff > 0.50: return "USD 🇺🇸"
    elif diff < -0.50: return "EUR 🇪🇺"
    else: return "Tie ⚪"

def judge_sentiment(us_trend, eu_trend):
    if "Rising" in us_trend and "Falling" in eu_trend: return "USD 🇺🇸"
    elif "Falling" in us_trend and "Rising" in eu_trend: return "EUR 🇪🇺"
    elif "Rising" in us_trend and "Rising" in eu_trend: return "Tie (Both Strong) ⚪"
    elif "Falling" in us_trend and "Falling" in eu_trend: return "Tie (Both Weak) ⚪"
    else: return "Neutral"

def judge_oil(price):
    if price is None: return "No Data"
    if price > 85: return "USD 🇺🇸 (EU Pain)"
    elif price < 75: return "EUR 🇪🇺 (Relief)"
    else: return "Neutral"

# --- 6. DISPLAY WEBSITE ---
st.title("🇪🇺 EUR/USD Fundamental Command Center")
st.markdown("### 📊 Macro Economic Cheat Sheet (Forward Looking)")

data = {
    "Indicator": [
        "Interest Rates (Daily Target)", 
        "Inflation (CPI YoY)", 
        "GDP Growth (Real YoY)", 
        "Unemployment Rate", 
        "Consumer Sentiment (Trend)",
        f"WTI Crude Oil (${oil_price:.2f})" if oil_price else "WTI Crude Oil"
    ],
    "🇺🇸 United States (USD)": [
        f"{us_rate:.2f}% (Expect: {us_2y_yield:.2f}%)", # Show expectation here
        f"{us_cpi_val:.2f}%", 
        f"{us_gdp_val:.2f}%", 
        f"{us_unemp:.1f}%", 
        f"{us_sent:.1f} ({us_sent_trend})",
        "Net Producer"
    ],
    "🇪🇺 Eurozone (EUR)": [
        f"{eu_rate:.2f}%", 
        f"{eu_cpi_val:.2f}%", 
        f"{eu_gdp_val:.2f}%", 
        f"{eu_unemp:.1f}%", 
        f"{eu_sent:.1f} ({eu_sent_trend})",
        "Net Importer"
    ],
    "Bias / Winner": [
        # USE THE NEW SMART LOGIC HERE
        judge_smart_rates(us_rate, eu_rate, us_2y_yield), 
        judge(us_cpi_val, eu_cpi_val, 'inflation'),
        judge(us_gdp_val, eu_gdp_val, 'higher_is_better'),
        judge(us_unemp, eu_unemp, 'lower_is_better'),
        judge_sentiment(us_sent_trend, eu_sent_trend),
        judge_oil(oil_price)
    ]
}

df = pd.DataFrame(data)
st.table(df)

# --- SCORE CALCULATION ---
usd_wins = df['Bias / Winner'].str.contains("USD").sum()
eur_wins = df['Bias / Winner'].str.contains("EUR").sum()

# --- PREDICTOR & RECESSION WATCH ---
st.divider()
col1, col2 = st.columns(2)

with col1:
    st.subheader("🔮 Rate Expectation")
    spread_val = (us_2y_yield - us_rate)
    st.metric("Spread (Yield - Rate)", f"{spread_val:.2f}%")
    if spread_val < -0.20:
        st.warning("⚠️ Market expects CUTS. The USD 'Rate Advantage' is disappearing.")
    else:
        st.info("Stable Expectations.")

with col2:
    st.subheader("⚠️ Recession Watch")
    curve_spread = us_10y_yield - us_2y_yield
    st.metric("10Y - 2Y Curve", f"{curve_spread:.2f}%")
    if curve_spread < 0:
        st.error("INVERTED: Recession Risk High.")

# --- FINAL VERDICT ---
st.divider()
if usd_wins > eur_wins:
    st.error(f"### 🐻 BEARISH EUR/USD (Score: USD {usd_wins} - {eur_wins} EUR)")
elif eur_wins > usd_wins:
    st.success(f"### 🐮 BULLISH EUR/USD (Score: EUR {eur_wins} - {usd_wins} USD)")
else:
    st.warning("### ⚖️ NEUTRAL BIAS (Market is Balanced)")

if st.button("Refresh Data"):
    st.rerun()
