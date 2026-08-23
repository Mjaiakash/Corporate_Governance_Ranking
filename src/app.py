from pathlib import Path
import pandas as pd
import plotly.express as px
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "corporate_governance_ranking.csv"
RAW = ROOT / "data" / "nifty100_governance_data.csv"

st.set_page_config(page_title="Nifty 100 Governance Risk", page_icon="⚖️", layout="wide")

@st.cache_data
def load_data():
    path = DATA if DATA.exists() else RAW
    return pd.read_csv(path)

df = load_data()

st.title("Corporate Governance Risk Score")
st.caption("Nifty 100 comparative governance screening dashboard")

st.sidebar.header("Filters")
levels = sorted(df.get("Risk_Level", pd.Series(dtype=str)).dropna().unique().tolist())
selected_levels = st.sidebar.multiselect("Risk level", levels, default=levels)
search = st.sidebar.text_input("Search company")

filtered = df.copy()
if selected_levels and "Risk_Level" in filtered:
    filtered = filtered[filtered["Risk_Level"].isin(selected_levels)]
if search:
    filtered = filtered[filtered["Company"].str.contains(search, case=False, na=False)]

complete = filtered[filtered["Governance_Score"].notna()].copy() if "Governance_Score" in filtered else filtered.iloc[0:0]

c1, c2, c3, c4 = st.columns(4)
c1.metric("Companies", len(filtered))
c2.metric("Average score", f"{complete['Governance_Score'].mean():.1f}" if len(complete) else "—")
c3.metric("Low risk", int((filtered.get("Risk_Level", pd.Series(dtype=str)) == "Low Risk").sum()))
c4.metric("High / very high", int(filtered.get("Risk_Level", pd.Series(dtype=str)).isin(["High Risk", "Very High Risk"]).sum()))

st.subheader("Governance ranking")
show_cols = [c for c in ["Rank", "Company", "Governance_Score", "Risk_Level", "Promoter_Pledge", "Auditor_Changes", "Related_Party_Transactions", "Independent_Director_Percentage", "ESG_Disclosure"] if c in filtered.columns]
st.dataframe(filtered[show_cols], use_container_width=True, hide_index=True)

if len(complete):
    top = complete.sort_values("Governance_Score", ascending=False).head(10)
    fig = px.bar(top.sort_values("Governance_Score"), x="Governance_Score", y="Company", orientation="h", title="Top 10 governance scores", text="Governance_Score")
    fig.update_layout(yaxis_title="", xaxis_title="Score")
    st.plotly_chart(fig, use_container_width=True)

    risk_counts = filtered["Risk_Level"].value_counts().reset_index()
    risk_counts.columns = ["Risk_Level", "Count"]
    fig2 = px.pie(risk_counts, names="Risk_Level", values="Count", title="Risk classification")
    st.plotly_chart(fig2, use_container_width=True)

    if "Industry" in filtered.columns:
        sector = filtered.groupby("Industry", dropna=False)["Governance_Score"].mean().reset_index().sort_values("Governance_Score")
        fig3 = px.bar(sector, x="Governance_Score", y="Industry", orientation="h", title="Average score by industry")
        st.plotly_chart(fig3, use_container_width=True)
else:
    st.info("Enter governance inputs and run the scoring script to populate rankings.")

st.divider()
st.caption("Methodology: Promoter pledge 30; auditor changes 20; RPT 20; independent directors 15; ESG/BRSR disclosure 15. This is a comparative research model, not an official rating or investment advice.")
