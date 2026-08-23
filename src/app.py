from pathlib import Path
import pandas as pd
import plotly.express as px
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "corporate_governance_ranking.csv"
RAW = ROOT / "data" / "nifty100_governance_data.csv"

st.set_page_config(page_title="NIFTY 100 Governance Risk", page_icon="⚖️", layout="wide")

st.markdown("""
<style>
.block-container{padding-top:1.2rem;padding-bottom:2rem}
.hero{padding:24px;border-radius:18px;background:linear-gradient(135deg,#0f172a,#1e3a8a);color:white;margin-bottom:18px}
.hero h1{margin:0;font-size:2.15rem}.hero p{margin:.35rem 0 0;color:#dbeafe}
[data-testid="stSidebar"]{border-right:1px solid #e2e8f0}
</style>
""", unsafe_allow_html=True)

@st.cache_data(ttl=300)
def load_data():
    path = DATA if DATA.exists() else RAW
    if not path.exists(): return pd.DataFrame()
    df = pd.read_csv(path)
    if "Governance_Score" not in df.columns or df["Governance_Score"].isna().all():
        def pledge(x):
            if pd.isna(x): return pd.NA
            x=float(x); return 30 if x==0 else 20 if x<=10 else 10 if x<=25 else 0
        def auditor(x):
            if pd.isna(x): return pd.NA
            x=float(x); return 20 if x==0 else 10 if x==1 else 0
        def rpt(x):
            if pd.isna(x): return pd.NA
            return {"low":20,"medium":10,"high":0}.get(str(x).strip().lower(),pd.NA)
        def independent(x):
            if pd.isna(x): return pd.NA
            x=float(x); return 15 if x>=50 else 10 if x>=33 else 0
        def esg(x):
            if pd.isna(x): return pd.NA
            return {"high":15,"medium":8,"low":0}.get(str(x).strip().lower(),pd.NA)
        df["Pledge_Score"]=df["Promoter_Pledge"].apply(pledge)
        df["Auditor_Score"]=df["Auditor_Changes"].apply(auditor)
        df["RPT_Score"]=df["Related_Party_Transactions"].apply(rpt)
        df["Independent_Director_Score"]=df["Independent_Director_Percentage"].apply(independent)
        df["ESG_Score"]=df["ESG_Disclosure"].apply(esg)
        cols=["Pledge_Score","Auditor_Score","RPT_Score","Independent_Director_Score","ESG_Score"]
        df["Governance_Score"]=df[cols].sum(axis=1,min_count=5)
        df["Risk_Level"]=df["Governance_Score"].apply(lambda x:"Incomplete data" if pd.isna(x) else "Low Risk" if x>=80 else "Moderate Risk" if x>=60 else "High Risk" if x>=40 else "Very High Risk")
        df["Rank"]=df["Governance_Score"].rank(method="min",ascending=False).where(df["Governance_Score"].notna()).astype("Int64")
    return df

df=load_data()
st.markdown('<div class="hero"><h1>Corporate Governance Risk Score</h1><p>NIFTY 100 comparative governance screening dashboard</p></div>',unsafe_allow_html=True)
if df.empty:
    st.error("No governance dataset was found."); st.stop()

st.sidebar.markdown("## Filters")
search=st.sidebar.text_input("🔎 Search company",placeholder="Search company name")
levels=[x for x in ["Low Risk","Moderate Risk","High Risk","Very High Risk","Incomplete data"] if x in df["Risk_Level"].dropna().unique()]
selected=st.sidebar.multiselect("Risk level",levels,default=levels)
industries=sorted(df["Industry"].dropna().astype(str).unique()) if "Industry" in df else []
selected_industry=st.sidebar.multiselect("Industry",industries,placeholder="All industries")
min_score,max_score=st.sidebar.slider("Governance score",0,100,(0,100))
sort_by=st.sidebar.selectbox("Sort by",["Governance Score","Company","Industry"])
ascending=st.sidebar.checkbox("Ascending",False)

filtered=df.copy()
if selected: filtered=filtered[filtered["Risk_Level"].isin(selected)]
if search: filtered=filtered[filtered["Company"].astype(str).str.contains(search,case=False,na=False)]
if selected_industry: filtered=filtered[filtered["Industry"].isin(selected_industry)]
filtered=filtered[(filtered["Governance_Score"].fillna(-1)>=min_score)&(filtered["Governance_Score"].fillna(-1)<=max_score)]
sort_col={"Governance Score":"Governance_Score","Company":"Company","Industry":"Industry"}[sort_by]
filtered=filtered.sort_values(sort_col,ascending=ascending,na_position="last")
complete=filtered[filtered["Governance_Score"].notna()]

avg=complete["Governance_Score"].mean() if len(complete) else None
low=int((filtered["Risk_Level"]=="Low Risk").sum())
high=int(filtered["Risk_Level"].isin(["High Risk","Very High Risk"]).sum())
c1,c2,c3,c4=st.columns(4)
c1.metric("Companies",len(filtered)); c2.metric("Average score",f"{avg:.1f}" if avg is not None else "—"); c3.metric("Low risk",low); c4.metric("High / very high",high)

st.subheader("Governance overview")
a,b=st.columns(2)
with a:
    if len(complete):
        rc=filtered["Risk_Level"].value_counts().rename_axis("Risk Level").reset_index(name="Companies")
        fig=px.pie(rc,names="Risk Level",values="Companies",hole=.58,title="Risk classification")
        st.plotly_chart(fig,use_container_width=True)
    else: st.info("No completed scores match the current filters.")
with b:
    if len(complete):
        top=complete.sort_values("Governance_Score",ascending=False).head(10)
        fig=px.bar(top.sort_values("Governance_Score"),x="Governance_Score",y="Company",orientation="h",text="Governance_Score",title="Top 10 governance scores")
        fig.update_traces(textposition="outside")
        fig.update_layout(xaxis_title="Score",yaxis_title="")
        st.plotly_chart(fig,use_container_width=True)

if "Industry" in filtered and len(complete):
    sector=complete.groupby("Industry",dropna=False)["Governance_Score"].mean().reset_index().sort_values("Governance_Score")
    fig=px.bar(sector,x="Governance_Score",y="Industry",orientation="h",text_auto=".1f",title="Average governance score by industry")
    fig.update_layout(xaxis_title="Average score",yaxis_title="")
    st.plotly_chart(fig,use_container_width=True)

st.subheader("NIFTY 100 governance ranking")
show=[c for c in ["Rank","Company","Industry","Governance_Score","Risk_Level","Promoter_Pledge","Auditor_Changes","Related_Party_Transactions","Independent_Director_Percentage","ESG_Disclosure"] if c in filtered.columns]
st.dataframe(filtered[show],use_container_width=True,hide_index=True,column_config={"Governance_Score":st.column_config.NumberColumn("Score",format="%.0f")})
st.download_button("⬇ Download filtered CSV",filtered.to_csv(index=False).encode("utf-8"),"corporate_governance_filtered.csv","text/csv")
st.divider(); st.caption("Comparative research model: pledge 30, auditor changes 20, related-party transactions 20, independent directors 15, ESG/BRSR disclosure 15. Not an official rating or investment advice.")
