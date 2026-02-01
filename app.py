from flask import Flask, request, redirect, render_template
import requests
import pandas as pd
from routes import main_routes

app = Flask(__name__)
app.register_blueprint(main_routes)

# ACS 5-year endpoint
ACS_URL = "https://api.census.gov/data/2023/acs/acs5"

try:
    df_fips = pd.read_excel("all-geocodes-v2023.xlsx", header=None, dtype=str)
    df_fips.columns = ["Summary Level", "State Code (FIPS)", "County Code", "Tract Code", "Place/County Code", "Block Code", "Area Name"]

    STATE_FIPS = df_fips[df_fips['Summary Level'] == '040'][['State Code (FIPS)', 'Area Name']].set_index('Area Name')['State Code (FIPS)'].to_dict()

    GEO_LOOKUP = {}
    for _, row in df_fips.iterrows():
        s_level = str(row['Summary Level'])
        state_fips = str(row['State Code (FIPS)'])
        name = str(row['Area Name']).strip().lower()
        if s_level not in ["050", "162", "160"]:
            continue
        
        geo_code = str(row['County Code']) if s_level == "050" else str(row['Place/County Code'])
        if state_fips not in GEO_LOOKUP:
            GEO_LOOKUP[state_fips] = {}
        GEO_LOOKUP[state_fips][name] = {"code": geo_code, "level": s_level}
except Exception as e:
    print(f"Error loading Excel: {e}")

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/paygap")
def paygap_form():
    state_input = request.args.get("state", "").strip().title()
    place_input = request.args.get("county", "").strip().lower()
    
    state_fips = STATE_FIPS.get(state_input) or state_input
    if state_fips not in GEO_LOOKUP:
        return "State not found."

    match = next((info for name, info in GEO_LOOKUP[state_fips].items() if place_input in name), None)
    if not match:
        return "Location not found."

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

    return f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <script src="https://cdn.tailwindcss.com"></script>
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap" rel="stylesheet">
        <style>
            body {{ font-family: 'Inter', sans-serif; }}
            @keyframes grow {{
                from {{ width: 0%; }}
                to {{ width: {pay_gap*100}%; }}
            }}
            .animate-bar {{
                animation: grow 1.5s ease-out forwards;
            }}
        </style>
        <style>
        body {{ font-family: 'Inter', sans-serif; }}
        .glass {{ background: rgba(255, 255, 255, 0.95); backdrop-filter: blur(10px); }}
    </style>
    </head>
    <body class="bg-slate-50 min-h-screen flex items-center justify-center p-4 bg-[radial-gradient(#008000_1px,transparent_1px)] [background-size:16px_16px]" style="background-color:#C9E4DE">
        <nav class="fixed top-1 left-1/2 -translate-x-1/2 w-full flex items-center justify-between px-6 py-4 glass border border-white shadow-lg rounded-2xl z-50">
            <div class="text-xl font-bold">
                Negotiation Help Center
            </div>

            <div class="flex gap-6 text-sm font-semibold">
                <a href="/" class="hover:underline">Home</a>
                <a href="/about" class="hover:underline">About</a>
            </div>
        </nav>
        <div class="max-w-xl w-full bg-white shadow-2xl rounded-3xl overflow-hidden border border-slate-100">
            <div class="bg-[#FBEC5D] p-8 text-white">
                <p class="text-stone-200 text-xs font-bold uppercase tracking-widest mb-1">
                    Gender Pay Gap Report
                </p>
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
                        <span class="text-2xl font-black text-[#FBEC5D]">{pay_gap*100:.1f}%</span>
                    </div>
                    <div class="w-full bg-slate-100 h-4 rounded-full overflow-hidden">
                        <div class="bg-[#FBEC5D] h-full rounded-full animate-bar" style="width: 0%"></div>
                    </div>
                </div>

                <p class="text-sm text-slate-500 mb-6 leading-relaxed italic text-center">
                    Women in this region earn <strong>{100-(pay_gap*100):.1f} cents</strong> for every dollar earned by men.
                </p>

                <a href="/ai-chat"
                   class="block w-full text-center py-3 mb-4 bg-[#FBEC5D] text-white rounded-xl font-semibold hover:bg-red-950 transition-all">
                    Go to AI Chat
                </a>

                <a href="/"
                   class="block w-full text-center py-3 bg-[#FBEC5D] text-white rounded-xl font-semibold hover:bg-red-950 transition-all">
                    New Search
                </a>
            </div>
        </div>
    </body>
    </html>
    """

@app.route("/ai-chat")
def ai_chat():
    return render_template("aichat.html")

@app.route("/about")
def about():
    return render_template("missionStatement.html")

if __name__ == "__main__":
    app.run(debug=True)
