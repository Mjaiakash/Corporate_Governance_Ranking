from pathlib import Path
import io
import pandas as pd
import plotly.express as px
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "corporate_governance_ranking.csv"
RAW = ROOT / "data" / "nifty100_governance_data.csv"
CSS = ROOT / "assets" / "custom.css"

st.set_page_config(page_title="GovernX AI | NIFTY 100", page_icon="⚖️", layout="wide", initial_sidebar_state="expanded")

if CSS.exists():
    st.markdown(CSS.read_text(encoding="utf-8"), unsafe_allow_html=True)


def score_data(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["Pledge_Score"] = pd.to_numeric(df.get("Promoter_Pledge"), errors="coerce").map(lambda x: pd.NA if pd.isna(x) else 30 if x == 0 else 20 if x <= 10 else 10 if x <= 25 else 0)
    df["Auditor_Score"] = pd.to_numeric(df.get("Auditor_Changes"), errors="coerce").map(lambda x: pd.NA if pd.isna(x) else 20 if x == 0 else 10 if x == 1 else 0)
    df["RPT_Score"] = df.get("Related_Party_Transactions", pd.Series(index=df.index, dtype="object")).map(lambda x: {"low": 20, "medium": 10, "high": 0}.get(str(x).strip().lower(), pd.NA))
    df["Independent_Director_Score"] = pd.to_numeric(df.get("Independent_Director_Percentage"), errors="coerce").map(lambda x: pd.NA if pd.isna(x) else 15 if x >= 50 else 10 if x >= 33 else 0)
    df["ESG_Score"] = df.get("ESG_Disclosure", pd.Series(index=df.index, dtype="object")).map(lambda x: {"high": 15, "medium": 8, "low": 0}.get(str(x).strip().lower(), pd.NA))
    score_cols = ["Pledge_Score", "Auditor_Score", "RPT_Score", "Independent_Director_Score", "ESG_Score"]
    df["Governance_Score"] = df[score_cols].apply(pd.to_numeric, errors="coerce").sum(axis=1, min_count=5)
    df["Risk_Level"] = df["Governance_Score"].map(lambda x: "Incomplete data" if pd.isna(x) else "Low Risk" if x >= 80 else "Moderate Risk" if x >= 60 else "High Risk" if x >= 40 else "Very High Risk")
    df["Rank"] = df["Governance_Score"].rank(method="min", ascending=False).where(df["Governance_Score"].notna()).astype("Int64")
    return df


@st.cache_data(ttl=300)
def load_data():
    path = DATA if DATA.exists() else RAW
    if not path.exists():
        return pd.DataFrame()
    return score_data(pd.read_csv(path))


def risk_label_counts(data):
    order = ["Low Risk", "Moderate Risk", "High Risk", "Very High Risk", "Incomplete data"]
    counts = data["Risk_Level"].value_counts().reindex(order, fill_value=0).reset_index()
    counts.columns = ["Risk Level", "Companies"]
    return counts[counts["Companies"] > 0]


def excel_bytes(data: pd.DataFrame) -> bytes:
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        data.to_excel(writer, index=False, sheet_name="Governance Ranking")
    return output.getvalue()


df = load_data()
if df.empty:
    st.error("No governance dataset was found.")
    st.stop()

# Top website navigation
st.markdown("""
<div class="top-nav">
  <div class="brand"><span class="brand-mark">🛡</span><span><b>GovernX AI</b><small>Governance. Transparency. Trust.</small></span></div>
  <div class="nav-links">
    <a href="#home">Home</a><a href="#dashboard">Dashboard</a><a href="#explorer">Company Explorer</a><a href="#analytics">Analytics</a><a href="#methodology">Methodology</a><a href="#about">About</a>
  </div>
  <div class="nav-actions">☼</div>
</div>
<div id="home"></div>
""", unsafe_allow_html=True)

# Reference-style functional sidebar
with st.sidebar:
    st.markdown("# GovernX AI")
    st.caption("NIFTY 100 Corporate Governance Intelligence")
    st.markdown('<div class="sidebar-title-row"><h2>Filters</h2><span>☷</span></div>', unsafe_allow_html=True)

    search_text = st.text_input("⌕  Search company", placeholder="e.g. Reliance Industries", key="company_search")

    risk_order = ["Low Risk", "Moderate Risk", "High Risk", "Very High Risk", "Incomplete data"]
    levels = [x for x in risk_order if x in df["Risk_Level"].dropna().unique()]
    selected_levels = st.multiselect("Risk level", levels, default=levels, placeholder="Choose options", key="risk_filter")

    min_score, max_score = st.slider("Governance score range", 0, 100, (0, 100), key="score_filter")

    st.markdown('<div class="sidebar-tip"><span class="tip-icon">💡</span><div><b>Tip: Use filters to</b><br>narrow down companies<br>and uncover insights.</div></div>', unsafe_allow_html=True)

    st.markdown('<div class="download-panel"><h3>Download data</h3><p>Download current view</p></div>', unsafe_allow_html=True)

filtered = df.copy()
if selected_levels:
    filtered = filtered[filtered["Risk_Level"].isin(selected_levels)]
if search_text.strip():
    filtered = filtered[filtered["Company"].astype(str).str.contains(search_text.strip(), case=False, na=False)]
filtered = filtered[(filtered["Governance_Score"].fillna(-1) >= min_score) & (filtered["Governance_Score"].fillna(-1) <= max_score)]

complete = filtered[filtered["Governance_Score"].notna()].copy()
avg = complete["Governance_Score"].mean() if len(complete) else None
low = int((filtered["Risk_Level"] == "Low Risk").sum())
high = int(filtered["Risk_Level"].isin(["High Risk", "Very High Risk"]).sum())

st.sidebar.download_button("↓  Download CSV", filtered.to_csv(index=False).encode("utf-8"), "governx_governance_filtered.csv", "text/csv", use_container_width=True)
st.sidebar.download_button("▥  Download Excel", excel_bytes(filtered), "governx_governance_filtered.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)

st.markdown('<div class="hero"><div class="eyebrow">NIFTY 100 • GOVERNANCE RESEARCH</div><h1>GovernX AI</h1><h2>Corporate Governance Intelligence Platform</h2><p>A content-led analytics experience for comparing governance quality, risk signals and disclosure strength across NIFTY 100 companies.</p><div class="hero-buttons"><a class="hero-btn primary" href="#dashboard">Explore Dashboard →</a><a class="hero-btn secondary" href="#methodology">View Methodology</a></div></div>', unsafe_allow_html=True)

st.markdown('<div class="section-title">Why corporate governance matters</div><div class="section-sub">Governance quality can influence transparency, accountability, capital allocation and long-term stakeholder confidence.</div>', unsafe_allow_html=True)
cards = st.columns(3)
for col, title, text in zip(cards, ["🛡 Accountability", "📊 Transparency", "🌱 Sustainable value"], ["Strong oversight helps align management decisions with shareholder and stakeholder interests.", "Clear disclosures make governance risks easier to identify and compare across companies.", "Board quality, controls and ESG practices can support resilient long-term business decisions."]):
    col.markdown(f'<div class="info-card"><h3>{title}</h3><p>{text}</p></div>', unsafe_allow_html=True)

st.markdown('<div id="dashboard"></div><div class="section-title">Governance snapshot</div>', unsafe_allow_html=True)
c1, c2, c3, c4 = st.columns(4)
c1.markdown(f'<div class="feature feature-teal"><div class="num">{len(filtered):,}</div><div class="label">Companies in view</div></div>', unsafe_allow_html=True)
c2.markdown(f'<div class="feature feature-violet"><div class="num">{avg:.1f}</div><div class="label">Average governance score</div></div>' if avg is not None else '<div class="feature feature-violet"><div class="num">—</div><div class="label">Average governance score</div></div>', unsafe_allow_html=True)
c3.markdown(f'<div class="feature feature-amber"><div class="num">{low}</div><div class="label">Low risk companies</div></div>', unsafe_allow_html=True)
c4.markdown(f'<div class="feature feature-coral"><div class="num">{high}</div><div class="label">High / very high risk</div></div>', unsafe_allow_html=True)

st.markdown('<div id="methodology"></div><div class="section-title">Scoring methodology</div><div class="section-sub">A transparent 100-point comparative research model. Higher scores indicate stronger governance characteristics within this framework.</div>', unsafe_allow_html=True)
mcols = st.columns(5)
for col, num, label in zip(mcols, ["30%", "20%", "20%", "15%", "15%"], ["Promoter pledge", "Auditor changes", "Related-party transactions", "Independent directors", "ESG / BRSR"]):
    col.markdown(f'<div class="kpi-wrap"><b>{num}</b><br><span class="small-note">{label}</span></div>', unsafe_allow_html=True)

st.markdown('<div id="analytics"></div><div class="section-title">Governance analytics</div>', unsafe_allow_html=True)
a, b = st.columns(2)
with a:
    if len(complete):
        rc = risk_label_counts(filtered)
        fig = px.pie(rc, names="Risk Level", values="Companies", hole=.62, title="Risk classification")
        fig.update_layout(margin=dict(l=10, r=10, t=55, b=10), paper_bgcolor="white", plot_bgcolor="white")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Complete governance scores are required for analytics.")
with b:
    if len(complete):
        top = complete.nlargest(10, "Governance_Score").sort_values("Governance_Score")
        fig = px.bar(top, x="Governance_Score", y="Company", orientation="h", text="Governance_Score", title="Top 10 governance scores")
        fig.update_traces(textposition="outside")
        fig.update_layout(margin=dict(l=10, r=40, t=55, b=10), xaxis_title="Score", yaxis_title="", paper_bgcolor="white", plot_bgcolor="white")
        st.plotly_chart(fig, use_container_width=True)

st.markdown('<div id="explorer"></div><div class="section-title">NIFTY 100 company explorer</div><div class="section-sub">Search and compare the governance universe using the filters in the sidebar.</div>', unsafe_allow_html=True)
show = [c for c in ["Rank", "Company", "Governance_Score", "Risk_Level", "Promoter_Pledge", "Auditor_Changes", "Related_Party_Transactions", "Independent_Director_Percentage", "ESG_Disclosure"] if c in filtered.columns]
view = filtered.sort_values(["Governance_Score", "Company"], ascending=[False, True], na_position="last")
st.dataframe(view[show], use_container_width=True, hide_index=True, column_config={"Governance_Score": st.column_config.ProgressColumn("Governance score", min_value=0, max_value=100, format="%d")})

st.markdown('<div id="about"></div><div class="section-title">About GovernX AI</div><div class="section-sub">An independent research platform for comparative corporate governance screening across the NIFTY 100 universe.</div>', unsafe_allow_html=True)
st.markdown('<div class="about-card"><b>Technology</b><br>Python · Pandas · Streamlit · Plotly<br><br><b>Purpose</b><br>Turn governance disclosures into a transparent, repeatable comparative score.<br><br><b>Research note</b><br>This framework is an independent research model, not an official rating or investment advice.</div>', unsafe_allow_html=True)
st.markdown('<div class="footer"><b>GovernX AI</b><br>Corporate Governance Intelligence Platform · NIFTY 100 Comparative Research Model</div>', unsafe_allow_html=True)
