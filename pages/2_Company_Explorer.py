from pathlib import Path
import pandas as pd
import streamlit as st
import plotly.express as px

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "corporate_governance_ranking.csv"
RAW = ROOT / "data" / "nifty100_governance_data.csv"
CSS = ROOT / "assets" / "custom.css"

st.set_page_config(page_title="GovernX AI | Company Explorer", page_icon="🏢", layout="wide", initial_sidebar_state="expanded")
if CSS.exists():
    st.markdown(CSS.read_text(encoding="utf-8"), unsafe_allow_html=True)

@st.cache_data(ttl=300)
def load():
    path = DATA if DATA.exists() else RAW
    return pd.read_csv(path) if path.exists() else pd.DataFrame()

def score(df):
    df=df.copy()
    df["Pledge_Score"]=pd.to_numeric(df["Promoter_Pledge"],errors="coerce").map(lambda x: pd.NA if pd.isna(x) else 30 if x==0 else 20 if x<=10 else 10 if x<=25 else 0)
    df["Auditor_Score"]=pd.to_numeric(df["Auditor_Changes"],errors="coerce").map(lambda x: pd.NA if pd.isna(x) else 20 if x==0 else 10 if x==1 else 0)
    df["RPT_Score"]=df["Related_Party_Transactions"].map(lambda x:{"low":20,"medium":10,"high":0}.get(str(x).lower(),pd.NA))
    df["Independent_Director_Score"]=pd.to_numeric(df["Independent_Director_Percentage"],errors="coerce").map(lambda x: pd.NA if pd.isna(x) else 15 if x>=50 else 10 if x>=33 else 0)
    df["ESG_Score"]=df["ESG_Disclosure"].map(lambda x:{"high":15,"medium":8,"low":0}.get(str(x).lower(),pd.NA))
    cols=["Pledge_Score","Auditor_Score","RPT_Score","Independent_Director_Score","ESG_Score"]
    df["Governance_Score"]=df[cols].apply(pd.to_numeric,errors="coerce").sum(axis=1,min_count=5)
    df["Risk_Level"]=df["Governance_Score"].map(lambda x:"Incomplete data" if pd.isna(x) else "Low Risk" if x>=80 else "Moderate Risk" if x>=60 else "High Risk" if x>=40 else "Very High Risk")
    df["Rank"]=df["Governance_Score"].rank(method="min",ascending=False).where(df["Governance_Score"].notna()).astype("Int64")
    return df

df=score(load())
with st.sidebar:
    st.markdown("# GovernX AI")
    st.caption("NIFTY 100 Corporate Governance Intelligence")
    st.markdown("### Filters")
    q=st.text_input("⌕ Search company",placeholder="e.g. Reliance Industries")
    risks=[r for r in ["Low Risk","Moderate Risk","High Risk","Very High Risk"] if r in df["Risk_Level"].unique()]
    selected=st.multiselect("Risk level",risks,default=risks,placeholder="Choose options")
    lo,hi=st.slider("Governance score range",0,100,(0,100))

filtered=df[df["Risk_Level"].isin(selected)]
if q: filtered=filtered[filtered["Company"].str.contains(q,case=False,na=False)]
filtered=filtered[(filtered["Governance_Score"].fillna(-1)>=lo)&(filtered["Governance_Score"].fillna(-1)<=hi)]

st.markdown('<div class="dashboard-title"><span class="accent-bar"></span><div><h2>Company Explorer</h2><p>Search, view and compare governance performance across NIFTY 100 companies.</p></div></div>',unsafe_allow_html=True)
if filtered.empty:
    st.warning("No companies match the current filters.")
    st.stop()

company=st.selectbox("Select company",sorted(filtered["Company"].dropna().unique()))
row=filtered[filtered["Company"]==company].iloc[0]
c1,c2,c3,c4,c5=st.columns(5)
c1.metric("Governance score",f"{row['Governance_Score']:.1f}")
c2.metric("Risk level",row["Risk_Level"])
c3.metric("NIFTY 100 rank",str(int(row["Rank"])))
c4.metric("Promoter pledge",f"{float(row['Promoter_Pledge']):.2f}%")
c5.metric("Independent directors",f"{float(row['Independent_Director_Percentage']):.1f}%")

a,b=st.columns(2)
pillars=pd.DataFrame({"Pillar":["Promoter pledge","Auditor stability","Related-party transactions","Independent directors","ESG / BRSR"],"Score":[row["Pledge_Score"],row["Auditor_Score"],row["RPT_Score"],row["Independent_Director_Score"],row["ESG_Score"]]})
with a:
    st.plotly_chart(px.bar(pillars,x="Score",y="Pillar",orientation="h",title="Governance pillar scores"),use_container_width=True)
with b:
    peers=filtered[filtered["Industry"]==row["Industry"]].sort_values("Governance_Score",ascending=False).head(10)
    st.plotly_chart(px.bar(peers,x="Governance_Score",y="Company",orientation="h",title=f"Industry peers — {row['Industry']}"),use_container_width=True)

st.markdown("### Company details")
detail_cols=[c for c in ["Company","Industry","Governance_Score","Risk_Level","Promoter_Pledge","Auditor_Changes","Related_Party_Transactions","Independent_Director_Percentage","ESG_Disclosure"] if c in filtered.columns]
st.dataframe(pd.DataFrame([row[detail_cols].to_dict()]),use_container_width=True,hide_index=True)
