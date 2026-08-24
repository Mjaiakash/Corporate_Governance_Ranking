from pathlib import Path
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st


def render_dashboard(filtered: pd.DataFrame) -> None:
    st.markdown('<div id="dashboard"></div>', unsafe_allow_html=True)
    st.markdown('<div class="dashboard-title"><span class="accent-bar"></span><div><h2>Governance Dashboard</h2><p>An overview of governance quality and risk across NIFTY 100 companies.</p></div><span class="as-of">▣ &nbsp; Data as of latest disclosed inputs</span></div>', unsafe_allow_html=True)

    complete = filtered[filtered["Governance_Score"].notna()].copy()
    avg = complete["Governance_Score"].mean() if len(complete) else None
    low = int((filtered["Risk_Level"] == "Low Risk").sum())
    high = int(filtered["Risk_Level"].isin(["High Risk", "Very High Risk"]).sum())
    avg_pledge = pd.to_numeric(filtered.get("Promoter_Pledge"), errors="coerce").mean() if "Promoter_Pledge" in filtered else None

    c1,c2,c3,c4,c5 = st.columns(5)
    cards=[
        (c1, "👥", f"{len(filtered):,}", "Companies in view", "teal"),
        (c2, "↗", f"{avg:.1f}" if avg is not None else "—", "Average governance score", "blue"),
        (c3, "🛡", str(low), "Low risk companies", "amber"),
        (c4, "⚠", str(high), "High / very high risk", "red"),
        (c5, "▣", f"{avg_pledge:.2f}" if avg_pledge is not None else "—", "Average promoter pledge (%)", "violet"),
    ]
    for col, icon, value, label, theme in cards:
        col.markdown(f'<div class="dash-kpi {theme}"><div class="dash-kpi-icon">{icon}</div><div class="dash-kpi-value">{value}</div><div class="dash-kpi-label">{label}</div></div>', unsafe_allow_html=True)

    a,b,c = st.columns(3)
    with a:
        rc=filtered["Risk_Level"].value_counts().reindex(["Low Risk","Moderate Risk","High Risk","Very High Risk"],fill_value=0).reset_index()
        rc.columns=["Risk Level","Companies"]
        rc=rc[rc["Companies"]>0]
        fig=px.pie(rc,names="Risk Level",values="Companies",hole=.62,title="Risk classification")
        fig.update_traces(textinfo="percent",hovertemplate="%{label}: %{value}<extra></extra>")
        fig.update_layout(margin=dict(l=8,r=8,t=46,b=8),legend=dict(orientation="v"),paper_bgcolor="white",plot_bgcolor="white")
        st.plotly_chart(fig,use_container_width=True)
    with b:
        bins=[0,20,40,60,80,100]
        labels=["0–20","20–40","40–60","60–80","80–100"]
        temp=pd.cut(complete["Governance_Score"],bins=bins,labels=labels,include_lowest=True,right=True).value_counts().reindex(labels,fill_value=0).reset_index()
        temp.columns=["Range","Companies"]
        fig=px.bar(temp,x="Range",y="Companies",text="Companies",title="Governance score distribution")
        fig.update_traces(textposition="outside")
        fig.update_layout(margin=dict(l=8,r=8,t=46,b=8),xaxis_title="Governance score range",yaxis_title="Companies",paper_bgcolor="white",plot_bgcolor="white")
        st.plotly_chart(fig,use_container_width=True)
    with c:
        if "Industry" in complete.columns and len(complete):
            sector=complete.groupby("Industry",dropna=False)["Governance_Score"].mean().reset_index().sort_values("Governance_Score",ascending=False).head(7).sort_values("Governance_Score")
            fig=px.bar(sector,x="Governance_Score",y="Industry",orientation="h",text_auto=".1f",title="Average governance score by industry")
            fig.update_layout(margin=dict(l=8,r=12,t=46,b=8),xaxis_title="Average score",yaxis_title="",paper_bgcolor="white",plot_bgcolor="white")
            st.plotly_chart(fig,use_container_width=True)

    d,e = st.columns([1.35,1])
    with d:
        st.markdown("### Top 10 companies by governance score")
        top=complete.sort_values(["Governance_Score","Company"],ascending=[False,True]).head(10).copy()
        table_cols=[c for c in ["Rank","Company","Industry","Governance_Score","Risk_Level"] if c in top.columns]
        top["Trend"]="↗"
        table_cols += ["Trend"]
        st.dataframe(top[table_cols],use_container_width=True,hide_index=True,column_config={"Governance_Score":st.column_config.ProgressColumn("Governance Score",min_value=0,max_value=100,format="%.1f")})
    with e:
        st.markdown("### Score by governance pillar (average)")
        pillars=[("Promoter Pledge","Pledge_Score",30),("Auditor Stability","Auditor_Score",20),("Related Party Transactions","RPT_Score",20),("Independent Directors","Independent_Director_Score",15),("ESG / BRSR Disclosure","ESG_Score",15)]
        names=[];vals=[]
        for name,col,maxv in pillars:
            if col in complete.columns and complete[col].notna().any():
                names.append(name); vals.append(float(complete[col].mean()) / maxv * 100)
        radar=go.Figure(go.Scatterpolar(r=vals+[vals[0]] if vals else [],theta=names+[names[0]] if names else [],fill="toself",name="Average Score"))
        radar.update_layout(polar=dict(radialaxis=dict(visible=True,range=[0,100])),showlegend=False,margin=dict(l=20,r=20,t=20,b=20),paper_bgcolor="white")
        st.plotly_chart(radar,use_container_width=True)

    st.markdown('<div class="dashboard-note">The dashboard updates automatically with the active sidebar filters. Scores are calculated from the project’s five governance pillars.</div>', unsafe_allow_html=True)
