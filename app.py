from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, send_file
from functools import wraps
from io import BytesIO
import csv

app = Flask(__name__)
app.secret_key = "governx-ai-demo-secret-key"

# Demo login credentials requested by the project owner.
DEMO_EMAIL = "m.jaiakash@gmail.com"
DEMO_PASSWORD = "Admin@123"

COMPANIES = [
    {"rank": 1, "name": "HCL Technologies", "industry": "IT Services", "score": 100.0, "risk": "Low", "pledge": 0.00, "auditor": "Excellent", "rpt": "Low", "independent": 66.7, "esg": "High", "trend": 3.1},
    {"rank": 2, "name": "Axis Bank", "industry": "Financial Services", "score": 98.7, "risk": "Low", "pledge": 0.00, "auditor": "Excellent", "rpt": "Low", "independent": 60.0, "esg": "High", "trend": 2.8},
    {"rank": 3, "name": "Kotak Mahindra Bank", "industry": "Financial Services", "score": 97.3, "risk": "Low", "pledge": 0.00, "auditor": "Excellent", "rpt": "Low", "independent": 60.0, "esg": "High", "trend": 2.6},
    {"rank": 4, "name": "ITC", "industry": "FMCG", "score": 96.4, "risk": "Low", "pledge": 0.00, "auditor": "Excellent", "rpt": "Low", "independent": 57.1, "esg": "High", "trend": 2.4},
    {"rank": 5, "name": "Hindustan Unilever", "industry": "FMCG", "score": 95.1, "risk": "Low", "pledge": 0.00, "auditor": "Excellent", "rpt": "Low", "independent": 58.3, "esg": "High", "trend": 2.1},
    {"rank": 6, "name": "ICICI Bank", "industry": "Financial Services", "score": 94.2, "risk": "Low", "pledge": 0.00, "auditor": "Excellent", "rpt": "Low", "independent": 55.6, "esg": "High", "trend": 2.0},
    {"rank": 7, "name": "HDFC Bank", "industry": "Financial Services", "score": 93.8, "risk": "Low", "pledge": 0.00, "auditor": "Excellent", "rpt": "Low", "independent": 55.6, "esg": "High", "trend": 1.9},
    {"rank": 8, "name": "Tata Consultancy Services", "industry": "IT Services", "score": 93.2, "risk": "Low", "pledge": 0.00, "auditor": "Excellent", "rpt": "Low", "independent": 60.0, "esg": "High", "trend": 1.7},
    {"rank": 9, "name": "Infosys", "industry": "IT Services", "score": 92.6, "risk": "Low", "pledge": 0.00, "auditor": "Excellent", "rpt": "Low", "independent": 60.0, "esg": "High", "trend": 1.6},
    {"rank": 10, "name": "Reliance Industries", "industry": "Oil & Gas", "score": 91.9, "risk": "Low", "pledge": 0.00, "auditor": "Excellent", "rpt": "Low", "independent": 58.3, "esg": "High", "trend": 4.2},
    {"rank": 11, "name": "ONGC", "industry": "Oil & Gas", "score": 85.3, "risk": "Low", "pledge": 0.00, "auditor": "Stable", "rpt": "Low", "independent": 50.0, "esg": "High", "trend": 1.5},
    {"rank": 12, "name": "Oil India", "industry": "Oil & Gas", "score": 78.6, "risk": "Moderate", "pledge": 0.00, "auditor": "Stable", "rpt": "Moderate", "independent": 44.4, "esg": "Medium", "trend": 0.9},
    {"rank": 13, "name": "Bharat Petroleum", "industry": "Oil & Gas", "score": 75.2, "risk": "Moderate", "pledge": 1.23, "auditor": "Stable", "rpt": "Moderate", "independent": 42.9, "esg": "Medium", "trend": 0.4},
    {"rank": 14, "name": "Hindustan Petroleum", "industry": "Oil & Gas", "score": 72.1, "risk": "Moderate", "pledge": 0.58, "auditor": "Stable", "rpt": "Moderate", "independent": 40.0, "esg": "Medium", "trend": -0.8},
]

PILLARS = [
    {"name": "Promoter Pledge", "weight": 30, "average": 86.2},
    {"name": "Auditor Stability", "weight": 20, "average": 88.7},
    {"name": "Related Party Transactions", "weight": 20, "average": 85.1},
    {"name": "Independent Directors", "weight": 15, "average": 89.3},
    {"name": "ESG / BRSR Disclosure", "weight": 15, "average": 87.5},
]

SECTOR_SCORES = {
    "IT Services": 93.4,
    "Financial Services": 91.2,
    "Pharma": 88.6,
    "Automobile": 87.1,
    "FMCG": 86.0,
    "Oil & Gas": 85.3,
    "Metals": 82.7,
}


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("user"):
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapped


def filtered_companies(query="", risk="", min_score=0, max_score=100):
    q = (query or "").strip().lower()
    return [
        c for c in COMPANIES
        if (not q or q in c["name"].lower() or q in c["industry"].lower())
        and (not risk or c["risk"].lower() == risk.lower())
        and min_score <= c["score"] <= max_score
    ]


@app.route("/", methods=["GET", "POST"])
def login():
    if session.get("user"):
        return redirect(url_for("home"))

    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        if email == DEMO_EMAIL and password == DEMO_PASSWORD:
            session["user"] = email
            return redirect(url_for("home"))
        flash("Invalid email address or password.", "error")

    return render_template("login.html", demo_email=DEMO_EMAIL)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/home")
@login_required
def home():
    return render_template("home.html", stats=dashboard_stats())


@app.route("/dashboard")
@login_required
def dashboard():
    query = request.args.get("search", "")
    risk = request.args.get("risk", "")
    try:
        min_score = float(request.args.get("min_score", 0))
        max_score = float(request.args.get("max_score", 100))
    except ValueError:
        min_score, max_score = 0, 100
    rows = filtered_companies(query, risk, min_score, max_score)
    return render_template(
        "dashboard.html",
        stats=dashboard_stats(rows),
        companies=rows,
        sector_scores=SECTOR_SCORES,
        pillars=PILLARS,
        filters={"search": query, "risk": risk, "min_score": min_score, "max_score": max_score},
    )


@app.route("/company-explorer")
@login_required
def company_explorer():
    query = request.args.get("search", "")
    rows = filtered_companies(query)
    company = rows[0] if rows else COMPANIES[-1]
    peers = [c for c in COMPANIES if c["industry"] == company["industry"]][:5]
    trend = {str(y): round(min(100, company["score"] - (2025-y)*3.1), 1) for y in range(2021, 2026)}
    if company["name"] == "Reliance Industries":
        trend = {"2021": 78.6, "2022": 82.1, "2023": 85.7, "2024": 88.9, "2025": 91.9}
    return render_template("explorer.html", company=company, peers=peers, trend=trend, pillars=PILLARS)


@app.route("/analytics")
@login_required
def analytics():
    return render_template("analytics.html", companies=COMPANIES, sector_scores=SECTOR_SCORES, pillars=PILLARS)


@app.route("/methodology")
@login_required
def methodology():
    return render_template("methodology.html", pillars=PILLARS)


@app.route("/about")
@login_required
def about():
    return render_template("about.html")


@app.route("/api/companies")
@login_required
def api_companies():
    query = request.args.get("search", "")
    risk = request.args.get("risk", "")
    return jsonify(filtered_companies(query, risk))


@app.route("/download/csv")
@login_required
def download_csv():
    output = BytesIO()
    text = output
    rows = filtered_companies(request.args.get("search", ""), request.args.get("risk", ""))
    wrapper = BytesIO()
    content = []
    headers = ["Rank", "Company", "Industry", "Governance Score", "Risk Level", "Promoter Pledge %", "Independent Directors %", "ESG Disclosure", "Trend"]
    content.append(",".join(headers))
    for c in rows:
        content.append(",".join(str(x) for x in [c["rank"], c["name"], c["industry"], c["score"], c["risk"], c["pledge"], c["independent"], c["esg"], c["trend"]]))
    wrapper.write(("\n".join(content)).encode("utf-8"))
    wrapper.seek(0)
    return send_file(wrapper, mimetype="text/csv", as_attachment=True, download_name="governx_ai_governance_data.csv")


def dashboard_stats(rows=None):
    rows = rows if rows is not None else COMPANIES
    if not rows:
        return {"companies": 0, "average": 0, "low": 0, "high_very_high": 0, "avg_pledge": 0}
    average = sum(c["score"] for c in rows) / len(rows)
    low = sum(c["risk"] == "Low" for c in rows)
    high_very_high = sum(c["risk"] in {"High", "Very High"} for c in rows)
    pledge = sum(c["pledge"] for c in rows) / len(rows)
    return {
        "companies": len(rows),
        "average": round(average, 1),
        "low": low,
        "high_very_high": high_very_high,
        "avg_pledge": round(pledge, 2),
    }


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
