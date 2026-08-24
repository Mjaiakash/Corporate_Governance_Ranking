from pathlib import Path
import io
import pandas as pd
import plotly.express as px
import streamlit as st
import plotly.graph_objects as go

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
    return score_data(pd.read_csv(path)) if path.exists() else pd.DataFrame()

def excel_bytes(data):
    out = io.BytesIO()
    with pd.ExcelWriter(out, engine="openpyxl") as writer:
        data.to_excel(writer, index=False, sheet_name="Governance Ranking")
    return out.getvalue()

def risk_counts(data):
    order = ["Low Risk", "Moderate Risk", "High Risk", "Very High Risk", "Incomplete data"]
    x = data["Risk_Level"].value_counts().reindex(order, fill_value=0).reset_index()
    x.columns = ["Risk Level", "Companies"]
    return x[x["Companies"] > 0]


def header(active="Home"):
    links = ["Home", "Dashboard", "Company Explorer", "Analytics", "Methodology", "About"]
    items = "".join(f'<a class="{"active" if x==active else ""}" href="#{x.lower().replace(" ","-")}">{x}</a>' for x in links)
    st.markdown(f'''<div class="top-nav"><div class="brand"><span class="brand-mark">🛡</span><span><b>GovernX AI</b><small>Governance. Transparency. Trust.</small></span></div><div class="nav-links">{items}</div><div class="nav-actions">☼</div></div>''', unsafe_allow_html=True)


def sidebar_filters(df):
    with st.sidebar:
        st.markdown("# GovernX AI")
        st.caption("NIFTY 100 Corporate Governance Intelligence")
        st.markdown('<div class="sidebar-title-row"><h2>Filters</h2><span>☷</span></div>', unsafe_allow_html=True)
        search_text = st.text_input("⌕  Search company", placeholder="e.g. Reliance Industries", key="company_search")
        order = ["Low Risk", "Moderate Risk", "High Risk", "Very High Risk", "Incomplete data"]
        levels = [x for x in order if x in df["Risk_Level"].dropna().unique()]
        selected = st.multiselect("Risk level", levels, default=levels, placeholder="Choose options", key="risk_filter")
        lo, hi = st.slider("Governance score range", 0, 100, (0, 100), key="score_filter")
        st.markdown('<div class="sidebar-tip"><span class="tip-icon">💡</span><div><b>Tip: Use filters to</b><br>narrow down companies<br>and uncover insights.</div></div>', unsafe_allow_html=True)
        st.markdown('<div class="download-panel"><h3>Download data</h3><p>Download current view</p></div>', unsafe_allow_html=True)
    return search_text, selected, lo, hi


def apply_filters(df, search_text, selected, lo, hi):
    filtered = df.copy()
    if selected:
        filtered = filtered[filtered["Risk_Level"].isin(selected)]
    if search_text.strip():
        filtered = filtered[filtered["Company"].astype(str).str.contains(search_text.strip(), case=False, na=False)]
    return filtered[(filtered["Governance_Score"].fillna(-1) >= lo) & (filtered["Governance_Score"].fillna(-1) <= hi)]


def dashboard_page(df, active="Dashboard"):
    search_text, selected, lo, hi = sidebar_filters(df)
    filtered = apply_filters(df, search_text, selected, lo, hi)
    complete = filtered[filtered["Governance_Score"].notna()].copy()
    avg = complete["Governance_Score"].mean() if len(complete) else None
    low = int((filtered["Risk_Level"] == "Low Risk").sum())
    high = int(filtered["Risk_Level"].isin(["High Risk", "Very High Risk"]).sum())
    header(active)
    st.markdown('<div id="dashboard"></div><div class="dashboard-title"><span class="accent-bar"></span><div><h2>Governance Dashboard</h2><p>An overview of governance quality and risk across NIFTY 100 companies.</p></div><span class="as-of">▣ &nbsp; Data from loaded research inputs</span></div>', unsafe_allow_html=True)
    pledge = pd.to_numeric(filtered.get("Promoter_Pledge"), errors="coerce").mean() if "Promoter_Pledge" in filtered else None
    cards = st.columns(5)
    specs = [("👥", f"{len(filtered):,}", "Companies in view", "teal"), ("↗", f"{avg:.1f}" if avg is not None else "—", "Average governance score", "blue"), ("🛡", str(low), "Low risk companies", "amber"), ("⚠", str(high), "High / very high risk", "red"), ("▣", f"{pledge:.2f}" if pledge is not None else "—", "Average promoter pledge (%)", "violet")]
    for col, (icon, val, label, theme) in zip(cards, specs):
        col.markdown(f'<div class="dash-kpi {theme}"><div class="dash-kpi-icon">{icon}</div><div class="dash-kpi-value">{val}</div><div class="dash-kpi-label">{label}</div></div>', unsafe_allow_html=True)
    a,b,c = st.columns(3)
    with a:
        rc = risk_counts(filtered)
        fig = px.pie(rc, names="Risk Level", values="Companies", hole=.62, title="Risk classification")
        fig.update_layout(margin=dict(l=8,r=8,t=46,b=8), paper_bgcolor="white")
        st.plotly_chart(fig, use_container_width=True)
    with b:
        bins=[0,20,40,60,80,100]; labels=["0–20","20–40","40–60","60–80","80–100"]
        tmp=pd.cut(complete["Governance_Score"],bins=bins,labels=labels,include_lowest=True).value_counts().reindex(labels,fill_value=0).reset_index(); tmp.columns=["Range","Companies"]
        fig=px.bar(tmp,x="Range",y="Companies",text="Companies",title="Governance score distribution")
        fig.update_traces(textposition="outside"); fig.update_layout(margin=dict(l=8,r=8,t=46,b=8),paper_bgcolor="white")
        st.plotly_chart(fig,use_container_width=True)
    with c:
        sector=complete.groupby("Industry")["Governance_Score"].mean().reset_index().sort_values("Governance_Score",ascending=False).head(7).sort_values("Governance_Score") if "Industry" in complete and len(complete) else pd.DataFrame()
        if len(sector):
            fig=px.bar(sector,x="Governance_Score",y="Industry",orientation="h",text_auto=".1f",title="Average governance score by industry")
            fig.update_layout(margin=dict(l=8,r=8,t=46,b=8),paper_bgcolor="white"); st.plotly_chart(fig,use_container_width=True)
    p,q=st.columns([1.35,1])
    with p:
        st.markdown("### Top 10 companies by governance score")
        top=complete.sort_values(["Governance_Score","Company"],ascending=[False,True]).head(10).copy(); top["Trend"]="↗"
        cols=[c for c in ["Rank","Company","Industry","Governance_Score","Risk_Level","Trend"] if c in top.columns]
        st.dataframe(top[cols],use_container_width=True,hide_index=True,column_config={"Governance_Score":st.column_config.ProgressColumn("Governance Score",min_value=0,max_value=100,format="%.1f")})
    with q:
        st.markdown("### Score by governance pillar (average)")
        pillars=[("Promoter Pledge","Pledge_Score",30),("Auditor Stability","Auditor_Score",20),("Related Party Transactions","RPT_Score",20),("Independent Directors","Independent_Director_Score",15),("ESG / BRSR Disclosure","ESG_Score",15)]
        names=[]; vals=[]
        for name,col,maxv in pillars:
            if col in complete and complete[col].notna().any(): names.append(name); vals.append(float(complete[col].mean())/maxv*100)
        if vals:
            radar=go.Figure(go.Scatterpolar(r=vals+[vals[0]],theta=names+[names[0]],fill="toself",name="Average Score")); radar.update_layout(polar=dict(radialaxis=dict(visible=True,range=[0,100])),showlegend=False,margin=dict(l=20,r=20,t=20,b=20),paper_bgcolor="white"); st.plotly_chart(radar,use_container_width=True)
    return filtered


def explorer_page(df):
    search_text, selected, lo, hi = sidebar_filters(df)
    filtered=apply_filters(df,search_text,selected,lo,hi)
    header("Company Explorer")
    st.markdown('<div id="company-explorer"></div><div class="dashboard-title"><span class="accent-bar"></span><div><h2>Company Explorer</h2><p>Search, view and analyze governance performance of NIFTY 100 companies.</p></div></div>', unsafe_allow_html=True)
    query=st.text_input("Search for a company...",value=search_text,placeholder="Search for a company")
    company=filtered[filtered["Company"].str.contains(query,case=False,na=False)] if query else filtered
    st.markdown("### Company ranking")
    cols=[c for c in ["Rank","Company","Industry","Governance_Score","Risk_Level","Promoter_Pledge","Auditor_Changes","Related_Party_Transactions","Independent_Director_Percentage","ESG_Disclosure"] if c in company.columns]
    st.dataframe(company.sort_values(["Governance_Score","Company"],ascending=[False,True],na_position="last")[cols],use_container_width=True,hide_index=True,column_config={"Governance_Score":st.column_config.ProgressColumn("Governance score",min_value=0,max_value=100,format="%.1f")})


def analytics_page(df):
    search_text, selected, lo, hi=sidebar_filters(df)
    filtered=apply_filters(df,search_text,selected,lo,hi)
    complete=filtered[filtered["Governance_Score"].notna()].copy()
    header("Analytics")
    st.markdown('<div id="analytics"></div><div class="dashboard-title"><span class="accent-bar"></span><div><h2>Governance Analytics</h2><p>Deep insights into governance quality, risk and performance across NIFTY 100 companies.</p></div></div>', unsafe_allow_html=True)
    a,b,c=st.columns(3)
    with a:
        st.plotly_chart(px.pie(risk_counts(filtered),names="Risk Level",values="Companies",hole=.6,title="Governance score distribution"),use_container_width=True)
    with b:
        sector=complete.groupby("Industry")["Governance_Score"].mean().reset_index().sort_values("Governance_Score",ascending=False).head(8).sort_values("Governance_Score") if "Industry" in complete and len(complete) else pd.DataFrame()
        if len(sector): st.plotly_chart(px.bar(sector,x="Governance_Score",y="Industry",orientation="h",text_auto=".1f",title="Average governance score by sector"),use_container_width=True)
    with c:
        esg=complete.get("ESG_Disclosure",pd.Series(dtype=str)).value_counts().reset_index()
        if len(esg):
            esg.columns=["ESG Level","Companies"]; st.plotly_chart(px.pie(esg,names="ESG Level",values="Companies",hole=.6,title="ESG / BRSR disclosure"),use_container_width=True)
    st.markdown("### Risk vs governance score")
    if len(complete):
        plot=complete.copy(); plot["Risk Value"]=plot["Risk_Level"].map({"Low Risk":10,"Moderate Risk":40,"High Risk":70,"Very High Risk":90})
        st.plotly_chart(px.scatter(plot,x="Risk Value",y="Governance_Score",color="Risk_Level",hover_name="Company",title="Risk vs governance score"),use_container_width=True)
    st.markdown("### Governance pillar averages")
    bars=[]
    for label,col,maxv in [("Promoter Pledge","Pledge_Score",30),("Auditor Stability","Auditor_Score",20),("RPT","RPT_Score",20),("Independent Directors","Independent_Director_Score",15),("ESG / BRSR","ESG_Score",15)]:
        if col in complete: bars.append({"Pillar":label,"Average %":float(complete[col].mean())/maxv*100})
    if bars: st.plotly_chart(px.bar(pd.DataFrame(bars),x="Pillar",y="Average %",text_auto=".1f",title="Governance pillar contribution"),use_container_width=True)


def methodology_page(df):
    sidebar_filters(df); header("Methodology")
    st.markdown('<div id="methodology"></div><div class="dashboard-title"><span class="accent-bar"></span><div><h2>Our Methodology</h2><p>A transparent, rules-based governance scoring model designed to evaluate governance quality across NIFTY 100 companies.</p></div></div>',unsafe_allow_html=True)
    cols=st.columns(5)
    data=[("30%","Promoter Pledge","Lower pledge indicates lower governance risk."),("20%","Auditor Changes","Frequent changes may indicate governance concerns."),("20%","Related Party Transactions","Lower material RPT exposure supports stronger governance."),("15%","Independent Directors","Greater independence strengthens board oversight."),("15%","ESG / BRSR Disclosure","More comprehensive disclosure improves transparency.")]
    for col,(pct,title,body) in zip(cols,data): col.markdown(f'<div class="method-card"><b>{pct}</b><h3>{title}</h3><p>{body}</p></div>',unsafe_allow_html=True)
    st.markdown('''<div class="formula-card"><h3>How the Governance Score is Calculated</h3><p><b>Pillar 1 (30%) + Pillar 2 (20%) + Pillar 3 (20%) + Pillar 4 (15%) + Pillar 5 (15%) = Governance Score / 100</b></p><p>Each pillar is normalized within its own scoring rule before the weight is applied.</p></div>''',unsafe_allow_html=True)
    st.markdown('''<div class="about-card"><h3>Data Sources</h3><p>Annual reports · Corporate governance reports · BSE / NSE filings · Company websites · BRSR reports · Other public disclosures</p><h3>Important notes</h3><p>This is an independent comparative research model. It is not an official rating and should not be used as the sole basis for investment decisions.</p></div>''',unsafe_allow_html=True)


def about_page(df):
    sidebar_filters(df); header("About")
    st.markdown('<div id="about"></div><div class="dashboard-title"><span class="accent-bar"></span><div><h2>About GovernX AI</h2><p>Empowering investors, analysts and organizations with governance intelligence for better decisions and a stronger corporate ecosystem.</p></div></div>',unsafe_allow_html=True)
    st.markdown('<div class="about-hero-copy"><h3>About the Platform</h3><p>GovernX AI is a content-led analytics platform that evaluates and ranks NIFTY 100 companies based on governance quality, risk signals and disclosure strength. Our 100-point scoring model is transparent, rules-based and designed to promote accountability, transparency and sustainable value creation.</p></div>',unsafe_allow_html=True)
    cols=st.columns(4)
    for col,title,body in zip(cols,["Objective & Data-Driven","Transparent Methodology","Risk-Oriented","Actionable Insights"],["Quantitative metrics and public data.","A clear 100-point framework.","Identifies governance risks early.","Supports comparative analysis."]): col.markdown(f'<div class="info-card"><h3>{title}</h3><p>{body}</p></div>',unsafe_allow_html=True)
    x,y=st.columns(2)
    x.markdown('<div class="about-card"><h3>Our Mission</h3><p>Make governance data accessible, comparable and actionable for everyone.</p></div>',unsafe_allow_html=True)
    y.markdown('<div class="about-card"><h3>Our Vision</h3><p>A corporate ecosystem where transparency and accountability drive trust, sustainability and long-term value creation.</p></div>',unsafe_allow_html=True)
    st.markdown('<div class="about-card"><h3>What We Cover</h3><p>NIFTY 100 universe · Governance pillars · Risk classification · Trend analysis · Peer comparison.</p></div>',unsafe_allow_html=True)


def home_page(df):
    sidebar_filters(df); header("Home")
    st.markdown('<div id="home"></div><div class="hero"><div class="eyebrow">NIFTY 100 • GOVERNANCE RESEARCH</div><h1>GovernX AI</h1><h2>Corporate Governance Intelligence Platform</h2><p>A content-led analytics experience for comparing governance quality, risk signals and disclosure strength across NIFTY 100 companies.</p><div class="hero-buttons"><a class="hero-btn primary" href="#dashboard">Explore Dashboard →</a><a class="hero-btn secondary" href="#methodology">View Methodology</a></div></div>',unsafe_allow_html=True)
    st.markdown('<div class="section-title">Why corporate governance matters</div><div class="section-sub">Governance quality can influence transparency, accountability, capital allocation and long-term stakeholder confidence.</div>',unsafe_allow_html=True)
    cards=st.columns(3)
    for col,title,text in zip(cards,["🛡 Accountability","📊 Transparency","🌱 Sustainable value"],["Strong oversight helps align management decisions with shareholder and stakeholder interests.","Clear disclosures make governance risks easier to identify and compare across companies.","Board quality, controls and ESG practices can support resilient long-term business decisions."]): col.markdown(f'<div class="info-card"><h3>{title}</h3><p>{text}</p></div>',unsafe_allow_html=True)
    st.markdown('<div class="section-title">Governance snapshot</div>',unsafe_allow_html=True)
    full=apply_filters(df,st.session_state.get("company_search", ""),st.session_state.get("risk_filter", []),*st.session_state.get("score_filter",(0,100)))
    comp=full[full["Governance_Score"].notna()]; avg=comp["Governance_Score"].mean() if len(comp) else None
    k=st.columns(4)
    k[0].metric("Companies",len(full)); k[1].metric("Average score",f"{avg:.1f}" if avg is not None else "—"); k[2].metric("Low risk",int((full["Risk_Level"]=="Low Risk").sum())); k[3].metric("High / very high",int(full["Risk_Level"].isin(["High Risk","Very High Risk"]).sum()))


df = load_data()
if df.empty:
    st.error("No governance dataset was found.")
    st.stop()

# Simple query-parameter navigation. Every top tab opens a focused view while preserving the single-page Streamlit deployment.
page = st.query_params.get("page", "Home")
if page not in {"Home","Dashboard","Company Explorer","Analytics","Methodology","About"}:
    page = "Home"

if page == "Home":
    home_page(df)
elif page == "Dashboard":
    dashboard_page(df)
elif page == "Company Explorer":
    explorer_page(df)
elif page == "Analytics":
    analytics_page(df)
elif page == "Methodology":
    methodology_page(df)
elif page == "About":
    about_page(df)

# Footer
st.markdown('<div class="footer"><b>GovernX AI</b><br>Corporate Governance Intelligence Platform · NIFTY 100 Comparative Research Model<br><span class="small-note">Independent research model; not official investment advice.</span></div>',unsafe_allow_html=True)
