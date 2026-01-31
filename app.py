from flask import Flask, request, redirect
import requests
import pandas as pd

app = Flask(__name__)

# ACS 5-year endpoint
ACS_URL = "https://api.census.gov/data/2023/acs/acs5"

# Load Excel without headers, assign column names
df_fips = pd.read_excel(
    "all-geocodes-v2023.xlsx",
    header=None,  # no headers in file
    dtype=str     # read everything as string
)

# Assign column names based on Census all-geocodes
df_fips.columns = [
    "Summary Level",       # e.g., 162
    "State Code (FIPS)",   # e.g., 05
    "County Code",         # e.g., 000
    "Tract Code",          # e.g., 00000
    "Place/County Code",   # e.g., 01270
    "Block Code",          # e.g., 00000
    "Area Name"            # e.g., Amagon town
]

# Create state lookup dictionary: Area Name -> State FIPS
STATE_FIPS = df_fips[['State Code (FIPS)', 'Area Name']].drop_duplicates().set_index('Area Name')['State Code (FIPS)'].to_dict()

# Create place lookup dictionary nested by state FIPS
PLACE_FIPS = {}
for _, row in df_fips.iterrows():
    state_fips = str(row['State Code (FIPS)'])
    place_name = str(row['Area Name']).strip().lower()  # safe even if numeric
    place_code = str(row['Place/County Code'])
    
    if state_fips not in PLACE_FIPS:
        PLACE_FIPS[state_fips] = {}
    PLACE_FIPS[state_fips][place_name] = place_code

@app.route("/")
def home():
    return """
    <h1>Gender Pay Gap Lookup</h1>
    <form action="/paygap" method="get">
        <label>State name or FIPS: <input name="state"></label><br>
        <label>County / Place name: <input name="county"></label><br>
        <button type="submit">Get Pay Gap</button>
    </form>
    <p>Example: State=51 or Virginia, County/Place=Blacksburg</p>
    """

@app.route("/paygap")
def paygap_form():
    state_input = request.args.get("state", "").strip()
    place_input = request.args.get("county", "").strip().lower()

    if not state_input or not place_input:
        return "<p>Please provide both state and county/place names.</p>"

    # Allow user to input state FIPS or name
    state_fips = STATE_FIPS.get(state_input) or state_input
    if state_fips not in PLACE_FIPS:
        return f"<p>State '{state_input}' not found in FIPS data.</p>"

    # Use startswith matching for place/county names
    place_fips = None
    for name, code in PLACE_FIPS[state_fips].items():
        if name.startswith(place_input):
            place_fips = code
            break

    if not place_fips:
        return f"<p>County/Place '{place_input}' not found in state '{state_input}'.</p>"

    # Redirect to API route
    return redirect(f"/api/paygap/{state_fips}/{place_fips}")

@app.route("/api/paygap/<state_fips>/<place_fips>")
def place_paygap(state_fips, place_fips):
    params = {
        "get": "NAME,B20017_003E,B20017_006E",  # male/female full-time earnings
        "for": f"place:{place_fips}",
        "in": f"state:{state_fips}"
    }

    try:
        response = requests.get(ACS_URL, params=params)
        response.raise_for_status()
        data = response.json()
    except Exception as e:
        return f"<p>Error fetching ACS data: {e}</p>"

    headers = data[0]
    values = data[1]
    result = dict(zip(headers, values))

    try:
        male = float(result["B20017_003E"])
        female = float(result["B20017_006E"])
        pay_gap = 1 - (female / male)
    except ValueError:
        return "<p>Data unavailable or suppressed for this location.</p>"

    return f"""
    <h1>Gender Pay Gap for {result['NAME']}</h1>
    <p>Male Median Earnings: ${male:,.0f}</p>
    <p>Female Median Earnings: ${female:,.0f}</p>
    <p><strong>Gender Pay Gap:</strong> {pay_gap*100:.2f}% favoring men</p>
    <p>Methodology: U.S. Census Bureau ACS 5-Year Estimates (Pew-style calculation)</p>
    """

if __name__ == "__main__":
    app.run(debug=True)
