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
    df["RPT_Score"] = df.get("Related_Party_Transactions", pd.Series(index=df.index, dtype="object")).map(lambda x: {"low":20,"medium":10,"high":0}.get(str(x).strip().lower(), pd.NA))
    df["Independent_Director_Score"] = pd.to_numeric(df.get("Independent_Director_Percentage"), errors="coerce").map(lambda x: pd.NA if pd.isna(x) else 15 if x >= 50 else 10 if x >= 33 else 0)
    df["ESG_Score"] = df.get("ESG_Disclosure", pd.Series(index=df.index, dtype="object")).map(lambda x: {"high":15,"medium":8,"low":0}.get(str(x).strip().lower(), pd.NA))
    score_cols=["Pledge_Score","Auditor_Score","RPT_Score","Independent_Director_Score","ESG_Score"]
    df["Governance_Score"]=df[score_cols].apply(pd.to_numeric,errors="coerce").sum(axis=1,min_count=5)
    df["Risk_Level"]=df["Governance_Score"].map(lambda x:"Incomplete data" if pd.isna(x) else "Low Risk" if x>=80 else "Moderate Risk" if x>=60 else "High Risk" if x>=40 else "Very High Risk")
    df["Rank"]=df["Governance_Score"].rank(method="min",ascending=False).where(df["Governance_Score"].notna()).astype("Int64")
    return df

@st.cache_data(ttl=300)
def load_data():
    path=DATA if DATA.exists() else RAW
    return score_data(pd.read_csv(path)) if path.exists() else pd.DataFrame()

def excel_bytes(data):
    out=io.BytesIO()
    with pd.ExcelWriter(out,engine="openpyxl") as writer:
        data.to_excel(writer,index=False,sheet_name="Governance Ranking")
    return out.getvalue()

def risk_counts(data):
    order=["Low Risk","Moderate Risk","High Risk","Very High Risk"]
    x=data["Risk_Level"].value_counts().reindex(order,fill_value=0).reset_index()
    x.columns=["Risk Level","Companies"]
    return x[x["Companies"]>0]

df=load_data()
if df.empty:
    st.error("No governance dataset was found.")
    st.stop()

st.markdown('''<div class="top-nav"><div class="brand"><span class="brand-mark">🛡</span><span><b>GovernX AI</b><small>Governance. Transparency. Trust.</small></span></div><div class="nav-links"><a href="#home">Home</a><a href="#dashboard">Dashboard</a><a href="#explorer">Company Explorer</a><a href="#analytics">Analytics</a><a href="#methodology">Methodology</a><a href="#about">About</a></div><div class="nav-actions">☼</div></div><div id="home"></div>''',unsafe_allow_html=True)

with st.sidebar:
    st.markdown("# GovernX AI")
    st.caption("NIFTY 100 Corporate Governance Intelligence")
    st.markdown('<div class="sidebar-title-row"><h2>Filters</h2><span>☷</span></div>',unsafe_allow_html=True)
    search_text=st.text_input("⌕  Search company",placeholder="e.g. Reliance Industries",key="company_search")
    order=["Low Risk","Moderate Risk","High Risk","Very High Risk","Incomplete data"]
    levels=[x for x in order if x in df["Risk_Level"].dropna().unique()]
    selected=st.multiselect("Risk level",levels,default=levels,placeholder="Choose options",key="risk_filter")
    lo,hi=st.slider("Governance score range",0,100,(0,100),key="score_filter")
    st.markdown('<div class="sidebar-tip"><span class="tip-icon">💡</span><div><b>Tip: Use filters to</b><br>narrow down companies<br>and uncover insights.</div></div>',unsafe_allow_html=True)
    st.markdown('<div class="download-panel"><h3>Download data</h3><p>Download current view</p></div>',unsafe_allow_html=True)

filtered=df.copy()
if selected: filtered=filtered[filtered["Risk_Level"].isin(selected)]
if search_text.strip(): filtered=filtered[filtered["Company"].astype(str).str.contains(search_text.strip(),case=False,na=False)]
filtered=filtered[(filtered["Governance_Score"].fillna(-1)>=lo)&(filtered["Governance_Score"].fillna(-1)<=hi)]
complete=filtered[filtered["Governance_Score"].notna()].copy()
avg=complete["Governance_Score"].mean() if len(complete) else None
low=int((filtered["Risk_Level"]=="Low Risk").sum())
high=int(filtered["Risk_Level"].isin(["High Risk","Very High Risk"]).sum())

st.sidebar.download_button("↓  Download CSV",filtered.to_csv(index=False).encode(),"governx_governance_filtered.csv","text/csv",use_container_width=True)
st.sidebar.download_button("▥  Download Excel",excel_bytes(filtered),"governx_governance_filtered.xlsx","application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",use_container_width=True)

st.markdown('<div class="hero"><div class="eyebrow">NIFTY 100 • GOVERNANCE RESEARCH</div><h1>GovernX AI</h1><h2>Corporate Governance Intelligence Platform</h2><p>A content-led analytics experience for comparing governance quality, risk signals and disclosure strength across NIFTY 100 companies.</p><div class="hero-buttons"><a class="hero-btn primary" href="#dashboard">Explore Dashboard →</a><a class="hero-btn secondary" href="#methodology">View Methodology</a></div></div>',unsafe_allow_html=True)
st.markdown('<div class="section-title">Why corporate governance matters</div><div class="section-sub">Governance quality can influence transparency, accountability, capital allocation and long-term stakeholder confidence.</div>',unsafe_allow_html=True)
cards=st.columns(3)
for col,title,text in zip(cards,["🛡 Accountability","📊 Transparency","🌱 Sustainable value"],["Strong oversight helps align management decisions with shareholder and stakeholder interests.","Clear disclosures make governance risks easier to identify and compare across companies.","Board quality, controls and ESG practices can support resilient long-term business decisions."]):
    col.markdown(f'<div class="info-card"><h3>{title}</h3><p>{text}</p></div>',unsafe_allow_html=True)

# ADVANCED DASHBOARD
st.markdown('<div id="dashboard"></div><div class="dashboard-title"><span class="accent-bar"></span><div><h2>Governance Dashboard</h2><p>An overview of governance quality and risk across NIFTY 100 companies.</p></div><span class="as-of">▣ &nbsp; Data as of latest disclosed inputs</span></div>',unsafe_allow_html=True)
pledge=pd.to_numeric(filtered.get("Promoter_Pledge"),errors="coerce").mean() if "Promoter_Pledge" in filtered else None
kpi=st.columns(5)
for col,icon,val,label,theme in [
(kpi[0],"👥",f"{len(filtered):,}","Companies in view","teal"),
(kpi[1],"↗",f"{avg:.1f}" if avg is not None else "—","Average governance score","blue"),
(kpi[2],"🛡",str(low),"Low risk companies","amber"),
(kpi[3],"⚠",str(high),"High / very high risk","red"),
(kpi[4],"▣",f"{pledge:.2f}" if pledge is not None else "—","Average promoter pledge (%)","violet")]:
    col.markdown(f'<div class="dash-kpi {theme}"><div class="dash-kpi-icon">{icon}</div><div class="dash-kpi-value">{val}</div><div class="dash-kpi-label">{label}</div></div>',unsafe_allow_html=True)

a,b,c=st.columns(3)
with a:
    rc=risk_counts(filtered)
    fig=px.pie(rc,names="Risk Level",values="Companies",hole=.62,title="Risk classification")
    fig.update_traces(textinfo="percent",hovertemplate="%{label}: %{value}<extra></extra>")
    fig.update_layout(margin=dict(l=8,r=8,t=46,b=8),paper_bgcolor="white")
    st.plotly_chart(fig,use_container_width=True)
with b:
    bins=[0,20,40,60,80,100]; labels=["0–20","20–40","40–60","60–80","80–100"]
    tmp=pd.cut(complete["Governance_Score"],bins=bins,labels=labels,include_lowest=True).value_counts().reindex(labels,fill_value=0).reset_index(); tmp.columns=["Range","Companies"]
    fig=px.bar(tmp,x="Range",y="Companies",text="Companies",title="Governance score distribution"); fig.update_traces(textposition="outside"); fig.update_layout(margin=dict(l=8,r=8,t=46,b=8),paper_bgcolor="white")
    st.plotly_chart(fig,use_container_width=True)
with c:
    if "Industry" in complete.columns and len(complete):
        sector=complete.groupby("Industry")["Governance_Score"].mean().reset_index().sort_values("Governance_Score",ascending=False).head(7).sort_values("Governance_Score")
        fig=px.bar(sector,x="Governance_Score",y="Industry",orientation="h",text_auto=".1f",title="Average governance score by industry"); fig.update_layout(margin=dict(l=8,r=8,t=46,b=8),paper_bgcolor="white")
        st.plotly_chart(fig,use_container_width=True)

p,q=st.columns([1.35,1])
with p:
    st.markdown("### Top 10 companies by governance score")
    top=complete.sort_values(["Governance_Score","Company"],ascending=[False,True]).head(10).copy(); top["Trend"]="↗"
    cols=[c for c in ["Rank","Company","Industry","Governance_Score","Risk_Level","Trend"] if c in top.columns]
    st.dataframe(top[cols],use_container_width=True,hide_index=True,column_config={"Governance_Score":st.column_config.ProgressColumn("Governance Score",min_value=0,max_value=100,format="%.1f")})
with q:
    st.markdown("### Score by governance pillar (average)")
    pillars=[("Promoter Pledge","Pledge_Score",30),("Auditor Stability","Auditor_Score",20),("Related Party Transactions","RPT_Score",20),("Independent Directors","Independent_Director_Score",15),("ESG / BRSR Disclosure","ESG_Score",15)]
    names=[];vals=[]
    for name,col,maxv in pillars:
        if col in complete and complete[col].notna().any(): names.append(name); vals.append(float(complete[col].mean())/maxv*100)
    if vals:
        import plotly.graph_objects as go
        radar=go.Figure(go.Scatterpolar(r=vals+[vals[0]],theta=names+[names[0]],fill="toself",name="Average Score")); radar.update_layout(polar=dict(radialaxis=dict(visible=True,range=[0,100])),showlegend=False,margin=dict(l=20,r=20,t=20,b=20),paper_bgcolor="white"); st.plotly_chart(radar,use_container_width=True)

st.markdown('<div class="dashboard-note">The dashboard updates automatically with the active sidebar filters.</div>',unsafe_allow_html=True)

st.markdown('<div id="methodology"></div><div class="section-title">Scoring methodology</div><div class="section-sub">A transparent 100-point comparative research model.</div>',unsafe_allow_html=True)
m=st.columns(5)
for col,num,label in zip(m,["30%","20%","20%","15%","15%"],["Promoter pledge","Auditor changes","Related-party transactions","Independent directors","ESG / BRSR"]): col.markdown(f'<div class="kpi-wrap"><b>{num}</b><br><span class="small-note">{label}</span></div>',unsafe_allow_html=True)

st.markdown('<div id="explorer"></div><div class="section-title">NIFTY 100 company explorer</div><div class="section-sub">Search and compare the governance universe using the filters in the sidebar.</div>',unsafe_allow_html=True)
show=[c for c in ["Rank","Company","Industry","Governance_Score","Risk_Level","Promoter_Pledge","Auditor_Changes","Related_Party_Transactions","Independent_Director_Percentage","ESG_Disclosure"] if c in filtered.columns]
view=filtered.sort_values(["Governance_Score","Company"],ascending=[False,True],na_position="last")
st.dataframe(view[show],use_container_width=True,hide_index=True,column_config={"Governance_Score":st.column_config.ProgressColumn("Governance score",min_value=0,max_value=100,format="%d")})

st.markdown('<div id="about"></div><div class="section-title">About GovernX AI</div><div class="section-sub">An independent research platform for comparative corporate governance screening across the NIFTY 100 universe.</div>',unsafe_allow_html=True)
st.markdown('<div class="about-card"><b>Technology</b><br>Python · Pandas · Streamlit · Plotly<br><br><b>Purpose</b><br>Turn governance disclosures into a transparent, repeatable comparative score.<br><br><b>Research note</b><br>This framework is an independent research model, not an official rating or investment advice.</div>',unsafe_allow_html=True)
st.markdown('<div class="footer"><b>GovernX AI</b><br>Corporate Governance Intelligence Platform · NIFTY 100 Comparative Research Model</div>',unsafe_allow_html=True)
