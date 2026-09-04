from pathlib import Path
import io
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "corporate_governance_ranking.csv"
RAW = ROOT / "data" / "nifty100_governance_data.csv"
CSS = ROOT / "assets" / "custom.css"

st.set_page_config(page_title="GovernX AI | Dashboard", page_icon="📊", layout="wide", initial_sidebar_state="expanded")
if CSS.exists():
    st.markdown(CSS.read_text(encoding="utf-8"), unsafe_allow_html=True)

@st.cache_data(ttl=300)
def load_data():
    path = DATA if DATA.exists() else RAW
    if not path.exists():
        return pd.DataFrame()
    df = pd.read_csv(path)
    df["Pledge_Score"] = pd.to_numeric(df.get("Promoter_Pledge"), errors="coerce").map(lambda x: pd.NA if pd.isna(x) else 30 if x == 0 else 20 if x <= 10 else 10 if x <= 25 else 0)
    df["Auditor_Score"] = pd.to_numeric(df.get("Auditor_Changes"), errors="coerce").map(lambda x: pd.NA if pd.isna(x) else 20 if x == 0 else 10 if x == 1 else 0)
    df["RPT_Score"] = df.get("Related_Party_Transactions", pd.Series(index=df.index, dtype="object")).map(lambda x: {"low":20,"medium":10,"high":0}.get(str(x).strip().lower(), pd.NA))
    df["Independent_Director_Score"] = pd.to_numeric(df.get("Independent_Director_Percentage"), errors="coerce").map(lambda x: pd.NA if pd.isna(x) else 15 if x >= 50 else 10 if x >= 33 else 0)
    df["ESG_Score"] = df.get("ESG_Disclosure", pd.Series(index=df.index, dtype="object")).map(lambda x: {"high":15,"medium":8,"low":0}.get(str(x).strip().lower(), pd.NA))
    cols=["Pledge_Score","Auditor_Score","RPT_Score","Independent_Director_Score","ESG_Score"]
    df["Governance_Score"] = df[cols].apply(pd.to_numeric, errors="coerce").sum(axis=1, min_count=5)
    df["Risk_Level"] = df["Governance_Score"].map(lambda x: "Incomplete data" if pd.isna(x) else "Low Risk" if x>=80 else "Moderate Risk" if x>=60 else "High Risk" if x>=40 else "Very High Risk")
    df["Rank"] = df["Governance_Score"].rank(method="min", ascending=False).where(df["Governance_Score"].notna()).astype("Int64")
    return df

def apply_filters(df):
    st.sidebar.markdown("# GovernX AI")
    st.sidebar.caption("NIFTY 100 Corporate Governance Intelligence")
    st.sidebar.markdown('<div class="sidebar-title-row"><h2>Filters</h2><span>☷</span></div>', unsafe_allow_html=True)
    search=st.sidebar.text_input("⌕  Search company", placeholder="e.g. Reliance Industries")
    order=["Low Risk","Moderate Risk","High Risk","Very High Risk","Incomplete data"]
    levels=[x for x in order if x in df["Risk_Level"].dropna().unique()]
    selected=st.sidebar.multiselect("Risk level", levels, default=levels, placeholder="Choose options")
    lo,hi=st.sidebar.slider("Governance score range",0,100,(0,100))
    out=df.copy()
    if selected: out=out[out["Risk_Level"].isin(selected)]
    if search: out=out[out["Company"].astype(str).str.contains(search,case=False,na=False)]
    return out[(out["Governance_Score"].fillna(-1)>=lo)&(out["Governance_Score"].fillna(-1)<=hi)]

def excel_bytes(data):
    out=io.BytesIO()
    with pd.ExcelWriter(out,engine="openpyxl") as writer:
        data.to_excel(writer,index=False,sheet_name="Governance Dashboard")
    return out.getvalue()

df=load_data()
if df.empty: st.error("No governance dataset was found."); st.stop()
filtered=apply_filters(df)
complete=filtered[filtered["Governance_Score"].notna()].copy()
avg=complete["Governance_Score"].mean() if len(complete) else None
low=int((filtered["Risk_Level"]=="Low Risk").sum()); high=int(filtered["Risk_Level"].isin(["High Risk","Very High Risk"]).sum())
pledge=pd.to_numeric(filtered.get("Promoter_Pledge"),errors="coerce").mean()

st.markdown('<div class="dashboard-title"><span class="accent-bar"></span><div><h2>Governance Dashboard</h2><p>An overview of governance quality and risk across NIFTY 100 companies.</p></div><span class="as-of">▣ &nbsp; Data from loaded research inputs</span></div>',unsafe_allow_html=True)

cards=st.columns(5)
items=[("👥",f"{len(filtered):,}","Companies in view","teal"),("↗",f"{avg:.1f}" if avg is not None else "—","Average governance score","blue"),("🛡",str(low),"Low risk companies","amber"),("⚠",str(high),"High / very high risk","red"),("▣",f"{pledge:.2f}" if pd.notna(pledge) else "—","Average promoter pledge (%)","violet")]
for c,(icon,val,label,theme) in zip(cards,items):
    c.markdown(f'<div class="dash-kpi {theme}"><div class="dash-kpi-icon">{icon}</div><div class="dash-kpi-value">{val}</div><div class="dash-kpi-label">{label}</div></div>',unsafe_allow_html=True)

a,b,c=st.columns(3)
with a:
    risk=filtered["Risk_Level"].value_counts().reindex(["Low Risk","Moderate Risk","High Risk","Very High Risk"],fill_value=0).rename_axis("Risk Level").reset_index(name="Companies")
    fig=px.pie(risk,names="Risk Level",values="Companies",hole=.62,title="Risk classification",color_discrete_sequence=["#16a34a","#3b82f6","#f59e0b","#ef4444"])
    fig.update_layout(margin=dict(l=8,r=8,t=46,b=8),paper_bgcolor="white",plot_bgcolor="white")
    st.plotly_chart(fig,use_container_width=True)
with b:
    bins=[0,20,40,60,80,100]; labels=["0–20","20–40","40–60","60–80","80–100"]
    dist=pd.cut(complete["Governance_Score"],bins=bins,labels=labels,include_lowest=True).value_counts().reindex(labels,fill_value=0).reset_index(); dist.columns=["Range","Companies"]
    fig=px.bar(dist,x="Range",y="Companies",text="Companies",title="Governance score distribution")
    fig.update_traces(textposition="outside"); fig.update_layout(margin=dict(l=8,r=8,t=46,b=8),paper_bgcolor="white",plot_bgcolor="white")
    st.plotly_chart(fig,use_container_width=True)
with c:
    sector=complete.groupby("Industry")["Governance_Score"].mean().reset_index().sort_values("Governance_Score",ascending=False).head(7).sort_values("Governance_Score") if "Industry" in complete and len(complete) else pd.DataFrame()
    if len(sector):
        fig=px.bar(sector,x="Governance_Score",y="Industry",orientation="h",text_auto=".1f",title="Average governance score by industry")
        fig.update_layout(margin=dict(l=8,r=8,t=46,b=8),paper_bgcolor="white",plot_bgcolor="white")
        st.plotly_chart(fig,use_container_width=True)

p,q=st.columns([1.35,1])
with p:
    st.markdown("### Top 10 companies by governance score")
    top=complete.sort_values(["Governance_Score","Company"],ascending=[False,True]).head(10)
    cols=[x for x in ["Rank","Company","Industry","Governance_Score","Risk_Level"] if x in top.columns]
    st.dataframe(top[cols],use_container_width=True,hide_index=True,column_config={"Governance_Score":st.column_config.ProgressColumn("Governance Score",min_value=0,max_value=100,format="%.1f")})
with q:
    st.markdown("### Score by governance pillar (average)")
    specs=[("Promoter Pledge","Pledge_Score",30),("Auditor Stability","Auditor_Score",20),("Related Party Transactions","RPT_Score",20),("Independent Directors","Independent_Director_Score",15),("ESG / BRSR Disclosure","ESG_Score",15)]
    names=[]; vals=[]
    for name,col,maxv in specs:
        if col in complete and complete[col].notna().any(): names.append(name); vals.append(float(complete[col].mean())/maxv*100)
    if vals:
        fig=go.Figure(go.Scatterpolar(r=vals+[vals[0]],theta=names+[names[0]],fill="toself",name="Average Score"))
        fig.update_layout(polar=dict(radialaxis=dict(visible=True,range=[0,100])),showlegend=False,margin=dict(l=20,r=20,t=20,b=20),paper_bgcolor="white",plot_bgcolor="white")
        st.plotly_chart(fig,use_container_width=True)

st.markdown("### Download current dashboard data")
d1,d2=st.columns(2)
with d1: st.download_button("⬇ Download CSV",filtered.to_csv(index=False).encode("utf-8"),"governx_dashboard.csv","text/csv",use_container_width=True)
with d2: st.download_button("▥ Download Excel",excel_bytes(filtered),"governx_dashboard.xlsx","application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",use_container_width=True)
