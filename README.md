# Corporate Governance Risk Score — Nifty 100

A research project that ranks Nifty 100 companies using a transparent Corporate Governance Risk Score (CGRS).

## Framework

| Factor | Weight |
|---|---:|
| Promoter pledge | 30 |
| Auditor changes | 20 |
| Related-party transactions | 20 |
| Independent directors | 15 |
| ESG / BRSR disclosures | 15 |

### Risk bands

- 80–100: Low Risk
- 60–79: Moderate Risk
- 40–59: High Risk
- 0–39: Very High Risk

## Project structure

- `data/nifty100_governance_data.csv` — input dataset
- `src/calculate_score.py` — scoring and ranking script
- `src/app.py` — Streamlit dashboard
- `requirements.txt` — Python dependencies
- `docs/methodology.md` — methodology and limitations

## Important research note

Governance inputs must be sourced from company filings and exchange disclosures. The scoring model is a comparative screening framework, not an official rating and not investment advice.

## Run locally

```bash
pip install -r requirements.txt
python src/calculate_score.py
streamlit run src/app.py
```
