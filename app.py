from flask import Flask, request, redirect, jsonify
import requests

app = Flask(__name__)

# ACS 5-year endpoint
ACS_URL = "https://api.census.gov/data/2023/acs/acs5"

# Minimal state FIPS mapping
STATE_FIPS = {
    "alabama": "01",
    "virginia": "51",
    "california": "06",
    # Add more states as needed
}

# Example county FIPS mapping for Virginia
COUNTY_FIPS_VA = {
    "montgomery": "061",
    "fairfax": "059",
    "blacksburg": "07784",  # if treating as place
    # Add more counties/places as needed
}

@app.route("/")
def home():
    return """
    <h1>Gender Pay Gap Lookup</h1>
    <form action="/paygap" method="get">
        <label>State name: <input name="state"></label><br>
        <label>County name: <input name="county"></label><br>
        <button type="submit">Get Pay Gap</button>
    </form>
    <p>Example: State=Virginia, County=Montgomery</p>
    """

@app.route("/paygap")
def paygap_form():
    state_name = request.args.get("state", "").strip().lower()
    county_name = request.args.get("county", "").strip().lower()

    if not state_name or not county_name:
        return "<p>Please provide both state and county names.</p>"

    state_fips = STATE_FIPS.get(state_name)
    if not state_fips:
        return f"<p>State '{state_name}' not found. Try full state name.</p>"

    # Currently supporting only VA counties in example
    if state_name == "virginia":
        county_fips = COUNTY_FIPS_VA.get(county_name)
        if not county_fips:
            return f"<p>County '{county_name}' not found in Virginia.</p>"
    else:
        return "<p>Currently only Virginia counties are supported.</p>"

    # Redirect to API route
    return redirect(f"/api/paygap/{state_fips}/{county_fips}")

@app.route("/api/paygap/<state_fips>/<county_fips>")
def county_paygap(state_fips, county_fips):
    params = {
        "get": "NAME,B20017_001E,B20017_002E",
        "for": f"county:{county_fips}" if len(county_fips) == 3 else f"place:{county_fips}",
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
        male = float(result["B20017_001E"])
        female = float(result["B20017_002E"])
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
