from flask import Flask, request, redirect, render_template
import requests
import pandas as pd

app = Flask(__name__)

# ACS 5-year endpoint
ACS_URL = "https://api.census.gov/data/2023/acs/acs5"

# Load Excel without headers
df_fips = pd.read_excel(
    "all-geocodes-v2023.xlsx",
    header=None,
    dtype=str
)

df_fips.columns = [
    "Summary Level",      # Col A
    "State Code (FIPS)",  # Col B
    "County Code",         # Col C
    "Tract Code",         # Col D
    "Place/County Code",  # Col E
    "Block Code",         # Col F
    "Area Name"           # Col G
]

# Create a state lookup: Name -> FIPS
STATE_FIPS = df_fips[df_fips['Summary Level'] == '040'][['State Code (FIPS)', 'Area Name']].set_index('Area Name')['State Code (FIPS)'].to_dict()

# Nested Dictionary: { state_fips: { "place name": {"code": "123", "level": "050"} } }
GEO_LOOKUP = {}

for _, row in df_fips.iterrows():
    s_level = str(row['Summary Level'])
    state_fips = str(row['State Code (FIPS)'])
    name = str(row['Area Name']).strip().lower()
    
    # We only care about Counties (050) and Places (162/160)
    if s_level not in ["050", "162", "160"]:
        continue
        
    # For Counties, the code is in 'County Code'. For Places, it's in 'Place/County Code'
    geo_code = str(row['County Code']) if s_level == "050" else str(row['Place/County Code'])

    if state_fips not in GEO_LOOKUP:
        GEO_LOOKUP[state_fips] = {}
    
    GEO_LOOKUP[state_fips][name] = {"code": geo_code, "level": s_level}

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/paygap")
def paygap_form():
    state_input = request.args.get("state", "").strip()
    place_input = request.args.get("county", "").strip().lower()

    if not state_input or not place_input:
        return "<p>Please provide both state and county/place names.</p>"

    # 1. Resolve State
    state_fips = STATE_FIPS.get(state_input) or state_input
    if state_fips not in GEO_LOOKUP:
        return f"<p>State '{state_input}' not found.</p>"

    # 2. Resolve Geography (Search for partial matches like 'Fairfax' in 'Fairfax County')
    match = None
    for full_name, info in GEO_LOOKUP[state_fips].items():
        if place_input in full_name:
            match = info
            break

    if not match:
        return f"<p>Location '{place_input}' not found in state FIPS {state_fips}.</p>"

    # 3. Redirect with the specific Summary Level
    return redirect(f"/api/paygap/{state_fips}/{match['code']}/{match['level']}")

@app.route("/api/paygap/<state_fips>/<geo_code>/<level>")
def place_paygap(state_fips, geo_code, level):
    # Determine if we are querying a 'place' or a 'county'
    geo_type = "county" if level == "050" else "place"
    
    params = {
        "get": "NAME,B20017_003E,B20017_006E",
        "for": f"{geo_type}:{geo_code}",
        "in": f"state:{state_fips}"
    }

    try:
        response = requests.get(ACS_URL, params=params)
        response.raise_for_status()
        data = response.json()
    except Exception as e:
        return f"<p>Error fetching ACS data: {e}<br>URL tried: {response.url if 'response' in locals() else 'N/A'}</p>"

    headers = data[0]
    values = data[1]
    result = dict(zip(headers, values))

    try:
        male = float(result["B20017_003E"])
        female = float(result["B20017_006E"])
        pay_gap = 1 - (female / male)
    except (ValueError, TypeError, ZeroDivisionError):
        return f"<h1>{result['NAME']}</h1><p>Data unavailable or suppressed for this specific location.</p>"

    return f"""
    <h1>Gender Pay Gap for {result['NAME']}</h1>
    <p><strong>Geography Type:</strong> {'County' if level == '050' else 'City/Place'}</p>
    <hr>
    <p>Male Median Earnings: ${male:,.0f}</p>
    <p>Female Median Earnings: ${female:,.0f}</p>
    <p><strong>Gender Pay Gap:</strong> {pay_gap*100:.2f}% favoring men</p>
    <br>
    <small>Source: U.S. Census Bureau ACS 2023 5-Year Estimates</small>
    """

if __name__ == "__main__":
    app.run(debug=True)