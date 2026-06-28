"""
FIFA World Cup 2026 — Player Performance Analysis
==================================================
Author  : Rushikesh Waje
GitHub  : github.com/RushikeshWaje-9220
LinkedIn: linkedin.com/in/rushikesh-waje

Description:
    Full EDA pipeline on 54,600 match records from FIFA World Cup 2026.
    Covers scoring analysis, xG vs actual goals, clutch performance by stage,
    market value correlation, physical metrics, and team-level comparisons.
    Outputs clean JSON used to power the interactive dashboard.

Usage:
    python scripts/analysis.py

Output:
    data/dashboard_data.json   — aggregated chart data for the dashboard
    (Run dashboard/index.html in any browser to view the full dashboard)
"""

import pandas as pd
import json
import os

# ── CONFIG ────────────────────────────────────────────────────────────────────
DATA_PATH   = "data/fifa_world_cup_2026_player_performance.csv"
OUTPUT_PATH = "data/dashboard_data.json"

# ── LOAD DATA ─────────────────────────────────────────────────────────────────
def load_data(path: str) -> pd.DataFrame:
    print(f"Loading dataset from: {path}")
    df = pd.read_csv(path)
    print(f"  Shape : {df.shape[0]:,} rows × {df.shape[1]} columns")
    print(f"  Nulls : {df.isnull().sum().sum()} missing values")
    return df


# ── ANALYSIS FUNCTIONS ────────────────────────────────────────────────────────

def top_scorers(df: pd.DataFrame, n: int = 10) -> list:
    """Top N players by tournament goals."""
    return (
        df.groupby("player_name")
        .agg(goals=("total_goals_tournament", "max"),
             team=("team", "first"),
             nationality=("nationality", "first"))
        .reset_index()
        .sort_values("goals", ascending=False)
        .head(n)
        .to_dict(orient="records")
    )


def top_assisters(df: pd.DataFrame, n: int = 10) -> list:
    """Top N players by tournament assists."""
    return (
        df.groupby("player_name")
        .agg(assists=("total_assists_tournament", "max"),
             team=("team", "first"))
        .reset_index()
        .sort_values("assists", ascending=False)
        .head(n)
        .to_dict(orient="records")
    )


def team_goals(df: pd.DataFrame, n: int = 10) -> list:
    """Top N teams by total goals scored."""
    result = (
        df.groupby("team")["goals"]
        .sum()
        .sort_values(ascending=False)
        .head(n)
        .reset_index()
    )
    result.columns = ["team", "goals"]
    return result.to_dict(orient="records")


def rating_by_position(df: pd.DataFrame) -> list:
    """Average player rating per position (active appearances only)."""
    result = (
        df[df["player_rating"] > 0]
        .groupby("position")["player_rating"]
        .mean()
        .round(2)
        .reset_index()
    )
    result.columns = ["position", "avg_rating"]
    return result.to_dict(orient="records")


def clutch_by_stage(df: pd.DataFrame) -> list:
    """Average clutch performance score per tournament stage (ordered)."""
    stage_order = [
        "Group Stage", "Round of 32", "Round of 16",
        "Quarter Finals", "Semi Finals", "Third Place Match", "Final"
    ]
    result = (
        df.groupby("tournament_stage")["clutch_performance_score"]
        .mean()
        .round(2)
        .reset_index()
    )
    result.columns = ["stage", "clutch_score"]
    result["stage"] = pd.Categorical(result["stage"], categories=stage_order, ordered=True)
    result = result.sort_values("stage")
    return result.to_dict(orient="records")


def xg_vs_actual(df: pd.DataFrame, min_goals: int = 8, n: int = 12) -> list:
    """Players who significantly outperformed or underperformed their xG."""
    result = (
        df.groupby("player_name")
        .agg(actual_goals=("goals", "sum"),
             xg=("expected_goals_xg", "sum"))
        .reset_index()
    )
    result = result[result["actual_goals"] >= min_goals].sort_values(
        "actual_goals", ascending=False
    ).head(n)
    result["actual_goals"] = result["actual_goals"].round(1)
    result["xg"] = result["xg"].round(2)
    return result.to_dict(orient="records")


def physical_by_position(df: pd.DataFrame) -> list:
    """Avg distance covered, top speed, and stamina score per position."""
    result = (
        df.groupby("position")
        .agg(distance=("distance_covered_km", "mean"),
             speed=("top_speed_kmh", "mean"),
             stamina=("stamina_score", "mean"))
        .reset_index()
        .round(2)
    )
    return result.to_dict(orient="records")


def market_value_scatter(df: pd.DataFrame, n: int = 400) -> list:
    """Sample of players for market value vs rating scatter chart."""
    result = (
        df[df["player_rating"] > 0]
        .groupby("player_name")
        .agg(market_value=("market_value_eur", "first"),
             avg_rating=("player_rating", "mean"),
             position=("position", "first"),
             team=("team", "first"))
        .reset_index()
    )
    result["avg_rating"]    = result["avg_rating"].round(2)
    result["market_value_m"] = (result["market_value"] / 1_000_000).round(1)
    return (
        result.sample(n=min(n, len(result)), random_state=42)
        [["player_name", "market_value_m", "avg_rating", "position", "team"]]
        .to_dict(orient="records")
    )


def country_rating(df: pd.DataFrame, n: int = 10) -> list:
    """Top N nations by average tournament rating."""
    result = (
        df.groupby("team")["tournament_rating"]
        .mean()
        .sort_values(ascending=False)
        .head(n)
        .round(3)
        .reset_index()
    )
    result.columns = ["team", "avg_rating"]
    return result.to_dict(orient="records")


def potm_winners(df: pd.DataFrame, n: int = 10) -> list:
    """Top N Player of the Match award winners."""
    return (
        df[df["player_of_match_awards"] > 0]
        .groupby("player_name")
        .agg(awards=("player_of_match_awards", "max"),
             team=("team", "first"))
        .reset_index()
        .sort_values("awards", ascending=False)
        .head(n)
        .to_dict(orient="records")
    )


def kpi_summary(df: pd.DataFrame, scorers: list, assisters: list) -> dict:
    """High-level KPI summary for dashboard header cards."""
    return {
        "total_players"     : int(df["player_name"].nunique()),
        "total_teams"       : int(df["team"].nunique()),
        "total_matches"     : int(df["match_id"].nunique()),
        "total_goals"       : int(df["goals"].sum()),
        "avg_player_rating" : round(float(df[df["player_rating"] > 0]["player_rating"].mean()), 2),
        "top_scorer"        : scorers[0]["player_name"],
        "top_scorer_goals"  : int(scorers[0]["goals"]),
        "top_assister"      : assisters[0]["player_name"],
        "top_assister_assists": int(assisters[0]["assists"]),
    }


# ── MAIN ──────────────────────────────────────────────────────────────────────
def main():
    df = load_data(DATA_PATH)

    print("\nRunning analysis...")

    scorers   = top_scorers(df)
    assisters = top_assisters(df)

    output = {
        "kpis"           : kpi_summary(df, scorers, assisters),
        "top_scorers"    : scorers,
        "top_assisters"  : assisters,
        "team_goals"     : team_goals(df),
        "avg_rating_pos" : rating_by_position(df),
        "clutch"         : clutch_by_stage(df),
        "xg_data"        : xg_vs_actual(df),
        "phys"           : physical_by_position(df),
        "scatter"        : market_value_scatter(df),
        "country_rating" : country_rating(df),
        "potm"           : potm_winners(df),
    }

    os.makedirs("data", exist_ok=True)
    with open(OUTPUT_PATH, "w") as f:
        json.dump(output, f, indent=2)

    print(f"\n✅ Analysis complete! Output saved to: {OUTPUT_PATH}")
    print(f"   Open dashboard/index.html in your browser to view the dashboard.")

    # ── PRINT KEY FINDINGS ────────────────────────────────────────────────────
    kpis = output["kpis"]
    print("\n── Key Findings ─────────────────────────────────────────────────────")
    print(f"  Total players  : {kpis['total_players']:,}")
    print(f"  Total teams    : {kpis['total_teams']}")
    print(f"  Total matches  : {kpis['total_matches']:,}")
    print(f"  Total goals    : {kpis['total_goals']:,}")
    print(f"  Avg rating     : {kpis['avg_player_rating']}")
    print(f"  Top scorer     : {kpis['top_scorer']} ({kpis['top_scorer_goals']} goals)")
    print(f"  Top assister   : {kpis['top_assister']} ({kpis['top_assister_assists']} assists)")

    clutch = output["clutch"]
    group_clutch = next(c["clutch_score"] for c in clutch if c["stage"] == "Group Stage")
    final_clutch = next(c["clutch_score"] for c in clutch if c["stage"] == "Final")
    rise = round(((final_clutch - group_clutch) / group_clutch) * 100, 1)
    print(f"\n  Clutch score rise (Group → Final) : {group_clutch} → {final_clutch} (+{rise}%)")


if __name__ == "__main__":
    main()
