# GovernX AI — Corporate Governance Intelligence Platform

A content-led NIFTY 100 corporate governance analytics application built with Streamlit, Pandas and Plotly.

## Features
- Governance research landing page with corporate imagery
- 100-point scoring framework
- Searchable company explorer
- Risk and industry filters
- Score range filter
- Governance KPI cards
- Risk classification chart
- Top 10 governance ranking
- Industry-level comparison
- CSV download
- Streamlit Cloud deployment ready

## Scoring framework
| Factor | Weight |
|---|---:|
| Promoter pledge | 30 |
| Auditor changes | 20 |
| Related-party transactions | 20 |
| Independent directors | 15 |
| ESG / BRSR disclosures | 15 |

## Risk bands
- 80–100: Low Risk
- 60–79: Moderate Risk
- 40–59: High Risk
- 0–39: Very High Risk

This is an independent comparative research model and is not an official rating or investment advice.

## Run locally
```bash
pip install -r requirements.txt
python src/calculate_score.py
streamlit run src/app.py
```

## Deployment
Connect this repository to Streamlit Community Cloud and set the entrypoint to `src/app.py`. Commits pushed to the connected branch can trigger redeployment.
