from flask import Flask, jsonify
import requests

app = Flask(__name__)

# ACS 5-year endpoint (best for small cities)
ACS_URL = "https://api.census.gov/data/2023/acs/acs5"

# Blacksburg, VA identifiers
STATE_VA = "51"
PLACE_BLACKSBURG = "07784"

@app.route("/")
def home():
    return {
        "message": "Gender Pay Gap API",
        "example": "/api/paygap/blacksburg"
    }

@app.route("/api/paygap/blacksburg")
def blacksburg_paygap():
    params = {
        "get": "NAME,B20017_003E,B20017_006E",
        "for": f"place:{PLACE_BLACKSBURG}",
        "in": f"state:{STATE_VA}"
    }

    response = requests.get(ACS_URL, params=params)
    response.raise_for_status()

    data = response.json()

    headers = data[0]
    values = data[1]
    result = dict(zip(headers, values))

    male = float(result["B20017_003E"])
    female = float(result["B20017_006E"])

    pay_gap = 1 - (female / male)

    return jsonify({
        "location": result["NAME"],
        "male_median_earnings": male,
        "female_median_earnings": female,
        "gender_pay_gap": round(pay_gap, 4),
        "methodology": "U.S. Census Bureau ACS 5-Year Estimates (Pew-style calculation)"
    })

if __name__ == "__main__":
    app.run(debug=True)
