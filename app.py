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
            prev = data.iloc[-5] # Compare to 4 quarters ago
        else:
            current = data.iloc[-1]
            prev = data.iloc[-13] # Compare to 12 months ago
        
        return ((current - prev) / prev) * 100
    except:
        return None

# --- 4. FETCH DATA (THE ENGINE) ---
with st.spinner('Fetching live economic data and market expectations...'):
    
    # A. INTEREST RATES (FIXED: Uses Daily Target)
    # US: Target Range Upper Limit (DFEDTARU) - Captures cuts instantly
    us_rate, us_date = get_latest('DFEDTARU') 
    if us_rate is None: us_rate, _ = get_latest('DFF') # Backup: Effective Rate
        
    eu_rate, _ = get_latest('ECBDFR')   # ECB Deposit Facility Rate
    if eu_rate is None: eu_rate = 3.25 # Manual Fallback if API glitch

    # B. INFLATION (CPI YoY)
    us_cpi_val = get_yoy_growth('CPIAUCSL')
    eu_cpi_val = get_yoy_growth('CP0000EZ19M086NEST')

    # C. GDP GROWTH (Real GDP YoY)
    us_gdp_val = get_yoy_growth('GDPC1', is_quarterly=True)
    eu_gdp_val = get_yoy_growth('CLVMNACSCAB1GQEA19', is_quarterly=True)

    # D. UNEMPLOYMENT RATE
    us_unemp, _ = get_latest('UNRATE')
    eu_unemp, _ = get_latest('LRHUTTTTEZM156S') 

    # E. MANUFACTURING (Industrial Production)
    us_manuf = get_yoy_growth('INDPRO')
    eu_manuf = get_yoy_growth('PRMNTO01EZQ661S') 

    # F. MARKET EXPECTATIONS (The Predictor)
    # We use US 2-Year Treasury Yield (DGS2) vs Fed Funds Rate
    us_2y_yield, _ = get_latest('DGS2')

# --- 5. LOGIC & WINNER CALCULATION ---
def judge(us, eu, metric):
    if us is None or eu is None: return "No Data"
    diff = us - eu
    
    if metric == 'higher_is_better': # Rates, GDP
        if diff > 0.25: return "USD 🇺🇸"
        elif diff < -0.25: return "EUR 🇪🇺"
        else: return "Tie ⚪"
        
    elif metric == 'lower_is_better': # Unemployment
        if diff < -0.25: return "USD 🇺🇸" 
        elif diff > 0.25: return "EUR 🇪🇺" 
        else: return "Tie ⚪"
        
    elif metric == 'inflation': 
        # High inflation generally forces hikes (Bullish)
        if diff > 0.5: return "USD 🇺🇸 (Hikes?)"
        elif diff < -0.5: return "EUR 🇪🇺 (Hikes?)"
        else: return "Neutral"

# --- 6. PREDICTOR LOGIC ---
def predict_fed_move(current_rate, market_yield_2y):
    if market_yield_2y is None or current_rate is None: return "Unknown"
    
    spread = market_yield_2y - current_rate
    
    if spread < -0.50:
        return "📉 Market expects AGGRESSIVE CUTS (Bearish USD)"
    elif spread < -0.10:
        return "↘️ Market expects Small Cuts"
    elif spread > 0.10:
        return "↗️ Market expects RATE HIKES (Bullish USD)"
    else:
        return "➡️ Market expects PAUSE (Rates Hold)"

prediction = predict_fed_move(us_rate, us_2y_yield)

# --- 7. DISPLAY WEBSITE ---
st.title("🇪🇺 EUR/USD Fundamental Command Center")
st.markdown("### 📊 Macro Economic Cheat Sheet")

# Create DataFrame
data = {
    "Indicator": [
        "Interest Rates (Daily Target)", 
        "Inflation (CPI YoY)", 
        "GDP Growth (Real YoY)", 
        "Unemployment Rate", 
        "Manufacturing Health"
    ],
    "🇺🇸 United States (USD)": [
        f"{us_rate:.2f}%", 
        f"{us_cpi_val:.2f}%", 
        f"{us_gdp_val:.2f}%", 
        f"{us_unemp:.1f}%", 
        f"{us_manuf:.1f}%"
    ],
    "🇪🇺 Eurozone (EUR)": [
        f"{eu_rate:.2f}%", 
        f"{eu_cpi_val:.2f}%", 
        f"{eu_gdp_val:.2f}%", 
        f"{eu_unemp:.1f}%", 
        f"{eu_manuf:.1f}%"
    ],
    "Bias / Winner": [
        judge(us_rate, eu_rate, 'higher_is_better'),
        judge(us_cpi_val, eu_cpi_val, 'inflation'),
        judge(us_gdp_val, eu_gdp_val, 'higher_is_better'),
        judge(us_unemp, eu_unemp, 'lower_is_better'),
        judge(us_manuf, eu_manuf, 'higher_is_better')
    ]
}

df = pd.DataFrame(data)
st.table(df)

# --- 8. PREDICTION SECTION ---
st.divider()
st.subheader("🔮 Future Rate Predictor (FedWatch Proxy)")

col1, col2, col3 = st.columns(3)
col1.metric(label="Current Fed Rate", value=f"{us_rate:.2f}%")
col2.metric(label="US 2-Year Treasury Yield", value=f"{us_2y_yield:.2f}%")
col3.metric(label="Spread (Yield - Rate)", value=f"{(us_2y_yield - us_rate):.2f}%")

st.info(f"**Prediction Model:** {prediction}")
st.caption("Logic: If the 2-Year Yield is significantly lower than the Fed Rate, the smart money is betting on Rate Cuts.")

# --- 9. FINAL VERDICT ---
usd_wins = df['Bias / Winner'].str.contains("USD").sum()
eur_wins = df['Bias / Winner'].str.contains("EUR").sum()

st.divider()
if usd_wins > eur_wins:
    st.error(f"### 🐻 BEARISH BIAS for EUR/USD (Score: USD {usd_wins} - {eur_wins} EUR)")
elif eur_wins > usd_wins:
    st.success(f"### 🐮 BULLISH BIAS for EUR/USD (Score: EUR {eur_wins} - {usd_wins} USD)")
else:
    st.warning("### ⚖️ NEUTRAL BIAS (Market is Balanced)")

if st.button("Refresh Data"):
    st.rerun()
