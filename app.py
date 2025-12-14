import streamlit as st
from fredapi import Fred
import pandas as pd
import datetime

# --- 1. CONFIGURATION ---
# ⚠️ REPLACE THIS with your actual API Key from https://fred.stlouisfed.org/
API_KEY = 'e9c0ff93e863850792b45ad43f8fbf0e' 

st.set_page_config(page_title="EUR/USD Fundamental Cheat Sheet", page_icon="💶")

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

def get_yoy_growth(series_id, is_quarterly=False):
    """Calculates Year-over-Year growth %."""
    try:
        data = fred.get_series(series_id)
        if is_quarterly:
            # Compare current quarter to same quarter last year (4 periods back)
            current = data.iloc[-1]
            prev = data.iloc[-5]
        else:
            # Compare current month to same month last year (12 periods back)
            current = data.iloc[-1]
            prev = data.iloc[-13]
        
        return ((current - prev) / prev) * 100
    except:
        return None

# --- 4. FETCH DATA (THE ENGINE) ---
with st.spinner('Fetching live economic data from the Fed...'):
    
    # A. INTEREST RATES
    us_rate = get_latest('FEDFUNDS') # Fed Funds Rate
    eu_rate = get_latest('ECBDFR')   # ECB Deposit Facility Rate
    # Fallback if ECBDFR fails (sometimes ticker changes)
    if eu_rate is None: 
        eu_rate = get_latest('IRSTCB01EZM156N') # Main Refinancing Rate

    # B. INFLATION (CPI YoY)
    # US CPI (CPIAUCSL)
    us_cpi_val = get_yoy_growth('CPIAUCSL')
    # Euro CPI (CP0000EZ19M086NEST - Harmonized Index)
    eu_cpi_val = get_yoy_growth('CP0000EZ19M086NEST')

    # C. GDP GROWTH (Real GDP YoY)
    # US Real GDP (GDPC1)
    us_gdp_val = get_yoy_growth('GDPC1', is_quarterly=True)
    # Euro Real GDP (CLVMNACSCAB1GQEA19)
    eu_gdp_val = get_yoy_growth('CLVMNACSCAB1GQEA19', is_quarterly=True)

    # D. UNEMPLOYMENT RATE
    us_unemp = get_latest('UNRATE')
    eu_unemp = get_latest('LRHUTTTTEZM156S') # Harmonized Unemployment for Euro Area

    # E. MANUFACTURING HEALTH (Proxy for PMI)
    # Using Industrial Production Index (YoY Growth)
    us_manuf = get_yoy_growth('INDPRO')
    eu_manuf = get_yoy_growth('PRMNTO01EZQ661S') # Total Manuf. Euro Area

# --- 5. LOGIC: WHO WINS? ---
def judge(us, eu, metric):
    if us is None or eu is None: return "No Data"
    
    diff = us - eu
    
    if metric == 'higher_is_better': # Rates, GDP, Manufacturing
        if diff > 0.2: return "USD 🇺🇸"
        elif diff < -0.2: return "EUR 🇪🇺"
        else: return "Tie ⚪"
        
    elif metric == 'lower_is_better': # Unemployment
        if diff < -0.2: return "USD 🇺🇸" # US lower = Better
        elif diff > 0.2: return "EUR 🇪🇺" # EU lower = Better
        else: return "Tie ⚪"
        
    elif metric == 'inflation': # Complex logic
        # High inflation usually means rate hikes (Bullish) UNLESS it's hyperinflation.
        # Generally, higher inflation = higher rates = currency UP.
        if diff > 0.2: return "USD 🇺🇸 (Hikes Likely)"
        elif diff < -0.2: return "EUR 🇪🇺 (Hikes Likely)"
        else: return "Neutral"

# --- 6. DETERMINE STANCE (ALGORITHMIC) ---
def get_stance(inflation, unemployment):
    if inflation is None: return "Unknown"
    if inflation > 2.5:
        return "🦅 HAWKISH (Fighting Inflation)"
    elif unemployment > 5.0 and inflation < 2.0:
        return "🕊️ DOVISH (Stimulating Econ)"
    else:
        return "😐 NEUTRAL"

us_stance = get_stance(us_cpi_val, us_unemp)
eu_stance = get_stance(eu_cpi_val, eu_unemp)
stance_winner = "USD 🇺🇸" if "HAWKISH" in us_stance and "DOVISH" in eu_stance else "Dependent"

# --- 7. DISPLAY WEBSITE ---
st.title("🇪🇺 vs 🇺🇸 Fundamental Cheat Sheet")
st.markdown("### Live Economic Data Analysis")

# Create DataFrame
data = {
    "Indicator": [
        "Interest Rates (Central Bank)", 
        "Inflation (CPI YoY)", 
        "GDP Growth (Real YoY)", 
        "Unemployment Rate", 
        "Manufacturing (Ind. Prod. YoY)",
        "Central Bank Stance (Est.)"
    ],
    "🇺🇸 United States (USD)": [
        f"{us_rate:.2f}%", 
        f"{us_cpi_val:.1f}%", 
        f"{us_gdp_val:.1f}%", 
        f"{us_unemp:.1f}%", 
        f"{us_manuf:.1f}%",
        us_stance
    ],
    "🇪🇺 Eurozone (EUR)": [
        f"{eu_rate:.2f}%", 
        f"{eu_cpi_val:.1f}%", 
        f"{eu_gdp_val:.1f}%", 
        f"{eu_unemp:.1f}%", 
        f"{eu_manuf:.1f}%",
        eu_stance
    ],
    "Winner 🏆": [
        judge(us_rate, eu_rate, 'higher_is_better'),
        judge(us_cpi_val, eu_cpi_val, 'inflation'),
        judge(us_gdp_val, eu_gdp_val, 'higher_is_better'),
        judge(us_unemp, eu_unemp, 'lower_is_better'),
        judge(us_manuf, eu_manuf, 'higher_is_better'),
        stance_winner
    ]
}

df = pd.DataFrame(data)
st.table(df)

# Final Verdict
usd_points = df['Winner 🏆'].str.contains("USD").sum()
eur_points = df['Winner 🏆'].str.contains("EUR").sum()

st.divider()
st.subheader("🤖 Final Verdict")
if usd_points > eur_points:
    st.error(f"BEARISH EUR/USD (Stronger USD: {usd_points} wins)")
    st.write("The US Economy is outperforming Europe. Traders favor selling EUR/USD.")
elif eur_points > usd_points:
    st.success(f"BULLISH EUR/USD (Stronger Euro: {eur_points} wins)")
    st.write("The Eurozone is outperforming the US. Traders favor buying EUR/USD.")
else:
    st.warning("NEUTRAL / CHOPPY")
    st.write("The economies are balanced. Expect range-bound trading.")

st.caption("Data Source: Federal Reserve Economic Data (FRED). Updates automatically on page refresh.")