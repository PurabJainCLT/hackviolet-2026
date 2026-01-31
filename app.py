from flask import Flask, request, redirect, render_template, render_template_string
import requests
import pandas as pd

app = Flask(__name__)

# ACS 5-year endpoint
ACS_URL = "https://api.census.gov/data/2023/acs/acs5"

try:
    df_fips = pd.read_excel("all-geocodes-v2023.xlsx", header=None, dtype=str)
    df_fips.columns = ["Summary Level", "State Code (FIPS)", "County Code", "Tract Code", "Place/County Code", "Block Code", "Area Name"]

    # State lookup
    STATE_FIPS = df_fips[df_fips['Summary Level'] == '040'][['State Code (FIPS)', 'Area Name']].set_index('Area Name')['State Code (FIPS)'].to_dict()

    # Geo lookup {state_fips: {name: {code, level}}}
    GEO_LOOKUP = {}
    for _, row in df_fips.iterrows():
        s_level = str(row['Summary Level'])
        state_fips = str(row['State Code (FIPS)'])
        name = str(row['Area Name']).strip().lower()
        if s_level not in ["050", "162", "160"]: continue
        
        geo_code = str(row['County Code']) if s_level == "050" else str(row['Place/County Code'])
        if state_fips not in GEO_LOOKUP: GEO_LOOKUP[state_fips] = {}
        GEO_LOOKUP[state_fips][name] = {"code": geo_code, "level": s_level}
except Exception as e:
    print(f"Error loading Excel: {e}")

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/paygap")
def paygap_form():
    state_input = request.args.get("state", "").strip()
    place_input = request.args.get("county", "").strip().lower()
    
    state_fips = STATE_FIPS.get(state_input) or state_input
    if state_fips not in GEO_LOOKUP:
        return "State not found. Use full name like 'Virginia' or FIPS like '51'."

    match = next((info for name, info in GEO_LOOKUP[state_fips].items() if place_input in name), None)
    if not match:
        return "Location not found in that state."

    return redirect(f"/api/paygap/{state_fips}/{match['code']}/{match['level']}")

@app.route("/api/paygap/<state_fips>/<geo_code>/<level>")
def place_paygap(state_fips, geo_code, level):
    geo_type = "county" if level == "050" else "place"
    params = {"get": "NAME,B20017_003E,B20017_006E", "for": f"{geo_type}:{geo_code}", "in": f"state:{state_fips}"}

    try:
        r = requests.get(ACS_URL, params=params)
        data = r.json()
        headers, values = data[0], data[1]
        res = dict(zip(headers, values))
        male, female = float(res["B20017_003E"]), float(res["B20017_006E"])
        pay_gap = 1 - (female / male)
    except:
        return "<div style='font-family:sans-serif; padding:50px;'><h1>Data Unavailable</h1></div>"

    # MAROON THEME + ANIMATION
    return f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <script src="https://cdn.tailwindcss.com"></script>
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap" rel="stylesheet">
        <style>
            body {{ font-family: 'Inter', sans-serif; }}
            /* Animation for the bar */
            @keyframes grow {{
                from {{ width: 0%; }}
                to {{ width: {pay_gap*100}%; }}
            }}
            .animate-bar {{
                animation: grow 1.5s ease-out forwards;
            }}
        </style>
    </head>
    <body class="bg-slate-50 min-h-screen flex items-center justify-center p-4">
        <div class="max-w-xl w-full bg-white shadow-2xl rounded-3xl overflow-hidden border border-slate-100">
            <div class="bg-[#800000] p-8 text-white"> <p class="text-red-200 text-xs font-bold uppercase tracking-widest mb-1">Gender Pay Gap Report</p>
                <h1 class="text-3xl font-bold italic">{res['NAME']}</h1>
            </div>
            <div class="p-8">
                <div class="grid grid-cols-2 gap-4 mb-8">
                    <div class="bg-slate-50 p-4 rounded-2xl border border-slate-100 text-center">
                        <p class="text-slate-500 text-[10px] font-bold uppercase mb-1">Male Median</p>
                        <p class="text-xl font-bold text-slate-800">${male:,.0f}</p>
                    </div>
                    <div class="bg-slate-50 p-4 rounded-2xl border border-slate-100 text-center">
                        <p class="text-slate-500 text-[10px] font-bold uppercase mb-1">Female Median</p>
                        <p class="text-xl font-bold text-slate-800">${female:,.0f}</p>
                    </div>
                </div>
                <div class="mb-6">
                    <div class="flex justify-between items-end mb-2">
                        <h3 class="font-semibold text-slate-700">Calculated Gap</h3>
                        <span class="text-2xl font-black text-[#800000]">{pay_gap*100:.1f}%</span>
                    </div>
                    <div class="w-full bg-slate-100 h-4 rounded-full overflow-hidden">
                        <div class="bg-[#800000] h-full rounded-full animate-bar" style="width: 0%"></div>
                    </div>
                </div>
                <p class="text-sm text-slate-500 mb-8 leading-relaxed italic text-center">
                    Women in this region earn <strong>{100-(pay_gap*100):.1f} cents</strong> for every dollar earned by men.
                </p>
                <a href="/" class="block w-full text-center py-3 bg-[#800000] text-white rounded-xl font-semibold hover:bg-red-950 transition-all">New Search</a>
            </div>
        </div>
    </body>
    </html>
    """

if __name__ == "__main__":
    app.run(debug=True)