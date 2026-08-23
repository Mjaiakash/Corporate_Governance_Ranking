from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "data" / "nifty100_governance_data.csv"
OUTPUT = ROOT / "data" / "corporate_governance_ranking.csv"


def score_pledge(x):
    if pd.isna(x): return pd.NA
    if x == 0: return 30
    if x <= 10: return 20
    if x <= 25: return 10
    return 0


def score_auditor(x):
    if pd.isna(x): return pd.NA
    if x == 0: return 20
    if x == 1: return 10
    return 0


def score_rpt(x):
    if pd.isna(x): return pd.NA
    v = str(x).strip().lower()
    return {"low": 20, "medium": 10, "high": 0}.get(v, pd.NA)


def score_independent(x):
    if pd.isna(x): return pd.NA
    if x >= 50: return 15
    if x >= 33: return 10
    return 0


def score_esg(x):
    if pd.isna(x): return pd.NA
    v = str(x).strip().lower()
    return {"high": 15, "medium": 8, "low": 0}.get(v, pd.NA)


def classify(score):
    if pd.isna(score): return "Incomplete data"
    if score >= 80: return "Low Risk"
    if score >= 60: return "Moderate Risk"
    if score >= 40: return "High Risk"
    return "Very High Risk"


def main():
    df = pd.read_csv(INPUT)
    required = [
        "Company", "Promoter_Pledge", "Auditor_Changes",
        "Related_Party_Transactions", "Independent_Director_Percentage",
        "ESG_Disclosure"
    ]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"Missing columns: {missing}")

    df["Pledge_Score"] = df["Promoter_Pledge"].apply(score_pledge)
    df["Auditor_Score"] = df["Auditor_Changes"].apply(score_auditor)
    df["RPT_Score"] = df["Related_Party_Transactions"].apply(score_rpt)
    df["Independent_Director_Score"] = df["Independent_Director_Percentage"].apply(score_independent)
    df["ESG_Score"] = df["ESG_Disclosure"].apply(score_esg)

    score_cols = ["Pledge_Score", "Auditor_Score", "RPT_Score", "Independent_Director_Score", "ESG_Score"]
    df["Governance_Score"] = df[score_cols].sum(axis=1, min_count=len(score_cols))
    df["Risk_Level"] = df["Governance_Score"].apply(classify)
    df["Rank"] = df["Governance_Score"].rank(method="min", ascending=False).where(df["Governance_Score"].notna())
    df["Rank"] = df["Rank"].astype("Int64")
    df = df.sort_values(["Governance_Score", "Company"], ascending=[False, True], na_position="last")
    OUTPUT.parent.mkdir(exist_ok=True)
    df.to_csv(OUTPUT, index=False)
    print(df[["Rank", "Company", "Governance_Score", "Risk_Level"]].to_string(index=False))
    print(f"\nSaved to {OUTPUT}")


if __name__ == "__main__":
    main()
