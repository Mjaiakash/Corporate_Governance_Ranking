from pathlib import Path
import pandas as pd
import plotly.express as px
import streamlit as st

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/"data"/"corporate_governance_ranking.csv"
RAW=ROOT/"data"/"nifty100_governance_data.csv"
CSS=ROOT/"assets"/"custom.css"

st.set_page_config(page_title="GovernX AI | Analytics",page_icon="📊",layout="wide",initial_sidebar_state="expanded")
if CSS.exists(): st.markdown(CSS.read_text(encoding="utf-8"),unsafe_allow_html=True)

@st.cache_data(ttl=300)
def load():
    path=DATA if DATA.exists() else RAW
    return pd.read_csv(path) if path.exists() else pd.DataFrame()

def score(df):
    df=df.copy()
    df["Pledge_Score"]=pd.to_numeric(df["Promoter_Pledge"],errors="coerce").map(lambda x:pd.NA if pd.isna(x) else 30 if x==0 else 20 if x<=10 else 10 if x<=25 else 0)
    df["Auditor_Score"]=pd.to_numeric(df["Auditor_Changes"],errors="coerce").map(lambda x:pd.NA if pd.isna(x) else 20 if x==0 else 10 if x==1 else 0)
    df["RPT_Score"]=df["Related_Party_Transactions"].map(lambda x:{"low":20,"medium":10,"high":0}.get(str(x).strip().lower(),pd.NA))
    df["Independent_Director_Score"]=pd.to_numeric(df["Independent_Director_Percentage"],errors="coerce").map(lambda x:pd.NA if pd.isna(x) else 15 if x>=50 else 10 if x>=33 else 0)
    df["ESG_Score"]=df["ESG_Disclosure"].map(lambda x:{"high":15,"medium":8,"low":0}.get(str(x).strip().lower(),pd.NA))
    cols=["Pledge_Score","Auditor_Score","RPT_Score","Independent_Director_Score","ESG_Score"]
    df["Governance_Score"]=df[cols].apply(pd.to_numeric,errors="coerce").sum(axis=1,min_count=5)
    df["Risk_Level"]=df["Governance_Score"].map(lambda x:"Incomplete data" if pd.isna(x) else "Low Risk" if x>=80 else "Moderate Risk" if x>=60 else "High Risk" if x>=40 else "Very High Risk")
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
complete=filtered[filtered["Governance_Score"].notna()].copy()

st.markdown('<div class="dashboard-title"><span class="accent-bar"></span><div><h2>Governance Analytics</h2><p>Deep insights into governance quality, risk and performance across NIFTY 100 companies.</p></div></div>',unsafe_allow_html=True)
if complete.empty:
    st.info("No completed governance scores match the current filters."); st.stop()

a,b,c=st.columns(3)
with a:
    rc=complete["Risk_Level"].value_counts().rename_axis("Risk Level").reset_index(name="Companies")
    st.plotly_chart(px.pie(rc,names="Risk Level",values="Companies",hole=.6,title="Governance score distribution"),use_container_width=True)
with b:
    sector=complete.groupby("Industry")["Governance_Score"].mean().reset_index().sort_values("Governance_Score",ascending=False).head(8).sort_values("Governance_Score")
    st.plotly_chart(px.bar(sector,x="Governance_Score",y="Industry",orientation="h",text_auto=".1f",title="Average governance score by sector"),use_container_width=True)
with c:
    esg=complete["ESG_Disclosure"].value_counts().rename_axis("ESG Level").reset_index(name="Companies")
    st.plotly_chart(px.pie(esg,names="ESG Level",values="Companies",hole=.6,title="ESG / BRSR disclosure"),use_container_width=True)

st.markdown("### Risk vs governance score")
risk_value={"Low Risk":10,"Moderate Risk":40,"High Risk":70,"Very High Risk":90}
plot=complete.copy(); plot["Risk Value"]=plot["Risk_Level"].map(risk_value)
st.plotly_chart(px.scatter(plot,x="Risk Value",y="Governance_Score",color="Risk_Level",hover_name="Company",title="Risk vs governance score"),use_container_width=True)

st.markdown("### Governance pillar averages")
pillars=[]
for label,col,maxv in [("Promoter Pledge","Pledge_Score",30),("Auditor Stability","Auditor_Score",20),("Related Party Transactions","RPT_Score",20),("Independent Directors","Independent_Director_Score",15),("ESG / BRSR","ESG_Score",15)]:
    pillars.append({"Pillar":label,"Average %":float(complete[col].mean())/maxv*100})
st.plotly_chart(px.bar(pd.DataFrame(pillars),x="Pillar",y="Average %",text_auto=".1f",title="Governance pillar contribution"),use_container_width=True)
