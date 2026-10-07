"""
Statistical analysis of hiring speed, offer acceptance and first-year attrition by source of hire.

Reads the dbt marts (DuckDB locally, Snowflake in production) and answers:
    1. Does time-to-hire differ across source channels?          (Kruskal-Wallis)
    2. Which channels hire significantly faster than the rest?   (Mann-Whitney U, Benjamini-Hochberg)
    3. Does offer acceptance differ by source?                   (chi-square test of independence)
    4. Does first-year attrition differ by source?               (chi-square + per-channel two-proportion z-test)

Outputs (to --out-dir):
    hiring_insights.md               plain-language summary for a non-technical reader
    time_to_hire_by_source.csv       per-channel stats + test results
    attrition_by_source.csv
    offer_acceptance_by_source.csv
    charts/*.png

Usage:
    python analysis/hiring_stats.py --target duckdb
    python analysis/hiring_stats.py --target snowflake
"""

from __future__ import annotations

import argparse
import os

import numpy as np
import pandas as pd
from scipy import stats

ALPHA = 0.05

# Chart tokens (light surface). One series per chart, so no legend; the highlight
# is also carried by the bar label text, never by color alone.
SURFACE = "#fcfcfb"
HIGHLIGHT = "#2a78d6"
BASE = "#c3c2b7"
INK = "#0b0b0b"
INK_2 = "#52514e"
MUTED = "#898781"
GRID = "#e1e0d9"


# ---------------------------------------------------------------- data access
def read_marts(target: str, duckdb_path: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    apps_sql = """
        select application_id, source_channel, department, job_level,
               reached_offer, offer_accepted, is_hired, days_to_hire
        from marts.fct_applications
    """
    hires_sql = """
        select employee_id, source_channel, department, days_to_hire,
               is_first_year_cohort, left_within_first_year, termination_type
        from marts.fct_hires
    """
    if target == "duckdb":
        import duckdb

        con = duckdb.connect(duckdb_path, read_only=True)
        apps, hires = con.execute(apps_sql).df(), con.execute(hires_sql).df()
        con.close()
    else:
        import snowflake.connector

        con = snowflake.connector.connect(
            account=os.environ["SNOWFLAKE_ACCOUNT"], user=os.environ["SNOWFLAKE_USER"],
            password=os.environ.get("SNOWFLAKE_PASSWORD"),
            authenticator=os.environ.get("SNOWFLAKE_AUTHENTICATOR", "snowflake"),
            role=os.environ.get("SNOWFLAKE_ROLE", "TRANSFORMER"),
            warehouse=os.environ.get("SNOWFLAKE_WAREHOUSE", "PEOPLE_ANALYTICS_WH"),
            database=os.environ.get("SNOWFLAKE_DATABASE", "PEOPLE_ANALYTICS"),
        )
        apps = pd.read_sql(apps_sql, con)
        hires = pd.read_sql(hires_sql, con)
        con.close()
        apps.columns = [c.lower() for c in apps.columns]
        hires.columns = [c.lower() for c in hires.columns]
    return apps, hires


# ---------------------------------------------------------------- statistics
def bh_adjust(p: np.ndarray) -> np.ndarray:
    """Benjamini-Hochberg false discovery rate adjustment."""
    p = np.asarray(p, dtype=float)
    n = len(p)
    order = np.argsort(p)
    ranked = p[order] * n / np.arange(1, n + 1)
    ranked = np.minimum.accumulate(ranked[::-1])[::-1]
    out = np.empty(n)
    out[order] = np.clip(ranked, 0, 1)
    return out


def time_to_hire_tests(hires: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    groups = {s: g["days_to_hire"].dropna().values for s, g in hires.groupby("source_channel")}
    h_stat, h_p = stats.kruskal(*groups.values())

    rows = []
    for src, vals in groups.items():
        rest = hires.loc[hires["source_channel"] != src, "days_to_hire"].dropna().values
        u, p = stats.mannwhitneyu(vals, rest, alternative="two-sided")
        rows.append({
            "source_channel": src,
            "hires": len(vals),
            "median_days_to_hire": round(float(np.median(vals)), 1),
            "median_days_other_channels": round(float(np.median(rest)), 1),
            "pct_faster_than_other_channels": round((1 - np.median(vals) / np.median(rest)) * 100, 1),
            # rank-biserial correlation: effect size for Mann-Whitney (-1..1)
            "effect_size_rank_biserial": round(1 - 2 * u / (len(vals) * len(rest)), 3),
            "p_value": p,
        })
    df = pd.DataFrame(rows)
    df["p_value_bh"] = bh_adjust(df["p_value"].values)
    df["significantly_faster"] = (df["p_value_bh"] < ALPHA) & (df["pct_faster_than_other_channels"] > 0)
    df = df.sort_values("median_days_to_hire").reset_index(drop=True)
    return df, {"kruskal_h": h_stat, "kruskal_p": h_p}


def offer_acceptance_tests(apps: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    offers = apps[apps["reached_offer"] & apps["offer_accepted"].notna()].copy()
    offers["offer_accepted"] = offers["offer_accepted"].astype(bool)
    table = pd.crosstab(offers["source_channel"], offers["offer_accepted"])
    chi2, p, dof, _ = stats.chi2_contingency(table)
    summary = (offers.groupby("source_channel")["offer_accepted"]
               .agg(offers_extended="count", offers_accepted="sum").reset_index())
    summary["acceptance_rate"] = (summary["offers_accepted"] / summary["offers_extended"]).round(4)
    return summary.sort_values("acceptance_rate", ascending=False), {"chi2": chi2, "p": p, "dof": dof}


def attrition_tests(hires: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    cohort = hires[hires["is_first_year_cohort"].astype(bool)].copy()
    cohort["left"] = cohort["left_within_first_year"].astype(bool)
    table = pd.crosstab(cohort["source_channel"], cohort["left"])
    chi2, p, dof, _ = stats.chi2_contingency(table)

    overall = cohort["left"].mean()
    rows = []
    for src, g in cohort.groupby("source_channel"):
        rest = cohort[cohort["source_channel"] != src]["left"]
        n1, n2 = len(g), len(rest)
        p1, p2 = g["left"].mean(), rest.mean()
        pooled = (g["left"].sum() + rest.sum()) / (n1 + n2)
        se = np.sqrt(pooled * (1 - pooled) * (1 / n1 + 1 / n2))
        z = (p1 - p2) / se if se > 0 else 0.0
        rows.append({
            "source_channel": src, "cohort_hires": n1, "first_year_exits": int(g["left"].sum()),
            "attrition_rate": round(p1, 4), "attrition_rate_other_channels": round(p2, 4),
            "z_score": round(z, 2), "p_value": 2 * (1 - stats.norm.cdf(abs(z))),
        })
    df = pd.DataFrame(rows)
    df["p_value_bh"] = bh_adjust(df["p_value"].values)
    df["significantly_different"] = df["p_value_bh"] < ALPHA
    return df.sort_values("attrition_rate").reset_index(drop=True), {
        "chi2": chi2, "p": p, "dof": dof, "overall_rate": overall, "cohort_size": len(cohort)}


# ---------------------------------------------------------------- charts
def bar_chart(df: pd.DataFrame, value_col: str, highlight_col: str, title: str, subtitle: str,
              xlabel: str, fmt: str, path: str, highlight_note: str) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    df = df.sort_values(value_col, ascending=True)
    colors = [HIGHLIGHT if h else BASE for h in df[highlight_col]]
    fig, ax = plt.subplots(figsize=(8, 4.6), dpi=160)
    fig.patch.set_facecolor(SURFACE)
    ax.set_facecolor(SURFACE)
    bars = ax.barh(df["source_channel"], df[value_col], color=colors, height=0.55, edgecolor=SURFACE,
                   linewidth=2)
    for bar, val, hl in zip(bars, df[value_col], df[highlight_col]):
        label = fmt.format(val) + (f"  {highlight_note}" if hl else "")
        ax.text(bar.get_width(), bar.get_y() + bar.get_height() / 2, "  " + label,
                va="center", ha="left", fontsize=8.5, color=INK if hl else INK_2)
    ax.set_xlim(0, df[value_col].max() * 1.45)
    ax.xaxis.grid(True, color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color(BASE)
    ax.tick_params(colors=MUTED, labelsize=8.5, length=0)
    ax.set_yticks(range(len(df)))
    ax.set_yticklabels(df["source_channel"], color=INK_2)
    ax.set_xlabel(xlabel, color=MUTED, fontsize=8.5)
    fig.text(0.01, 0.97, title, fontsize=12, color=INK, weight="bold", va="top")
    fig.text(0.01, 0.91, subtitle, fontsize=8.5, color=INK_2, va="top")
    fig.tight_layout(rect=(0, 0, 1, 0.86))
    fig.savefig(path, facecolor=SURFACE)
    plt.close(fig)


# ---------------------------------------------------------------- report
def write_report(path: str, tth: pd.DataFrame, tth_meta: dict, oa: pd.DataFrame, oa_meta: dict,
                 attr: pd.DataFrame, attr_meta: dict, n_apps: int, hires: pd.DataFrame) -> None:
    n_hires = len(hires)
    fast = tth[tth["significantly_faster"]]
    slow = tth[(tth["p_value_bh"] < ALPHA) & (tth["pct_faster_than_other_channels"] < 0)]
    fast_hires = fast["hires"].sum()
    in_fast = hires["source_channel"].isin(fast["source_channel"])
    fast_median = hires.loc[in_fast, "days_to_hire"].median() if len(fast) else None
    rest_median = hires.loc[~in_fast, "days_to_hire"].median()
    best_attr = attr.iloc[0]
    worst_attr = attr.iloc[-1]

    lines = [
        "# Hiring Insights: Speed, Offers and Retention by Source of Hire",
        "",
        f"Based on **{n_apps:,} applications** and **{n_hires:,} hires**. All differences below are "
        f"tested for statistical significance (p < {ALPHA}, adjusted for multiple comparisons).",
        "",
        "## Headline",
        "",
    ]
    if len(fast):
        lines.append(
            f"- **{len(fast)} source channels hire faster than the rest:** "
            f"{', '.join(fast['source_channel'])}. Together they produced {fast_hires:,} hires with a typical "
            f"time to hire of **{fast_median:.0f} days** versus **{rest_median:.0f} days** for other channels "
            f"(about **{(1 - fast_median / rest_median) * 100:.0f}% faster**).")
    if len(slow):
        lines.append(f"- **Slowest:** {', '.join(slow['source_channel'])} take noticeably longer than average.")
    lines += [
        f"- **Retention:** {best_attr['source_channel']} hires leave in their first year at "
        f"{best_attr['attrition_rate']:.0%}, compared with {worst_attr['attrition_rate']:.0%} for "
        f"{worst_attr['source_channel']} hires (company-wide: {attr_meta['overall_rate']:.0%}).",
        f"- **Offer acceptance** ranges from {oa['acceptance_rate'].min():.0%} to "
        f"{oa['acceptance_rate'].max():.0%} by channel "
        f"({'a real difference' if oa_meta['p'] < ALPHA else 'not a statistically meaningful difference'}).",
        "",
        "## What this means",
        "",
        "Channels where candidates arrive with context (referrals, internal moves, campus pipelines) move "
        "through interviews faster and stay longer. Shifting sourcing effort toward these channels should "
        "shorten time to hire without hurting quality of hire. Job boards bring volume but slower, "
        "less durable hires, so they work best for high-volume roles where speed matters less than reach.",
        "",
        "## Time to hire by source",
        "",
        "| Source | Hires | Median days | vs. other channels | Significant? |",
        "|---|---:|---:|---:|---|",
    ]
    for r in tth.itertuples():
        sig = "Yes" if r.p_value_bh < ALPHA else "No"
        lines.append(f"| {r.source_channel} | {r.hires:,} | {r.median_days_to_hire} | "
                     f"{r.pct_faster_than_other_channels:+.1f}% faster | {sig} |")
    lines += [
        "",
        f"Across all channels: Kruskal-Wallis H = {tth_meta['kruskal_h']:.1f}, p = {tth_meta['kruskal_p']:.2e}.",
        "",
        "## First-year attrition by source",
        "",
        f"Cohort: {attr_meta['cohort_size']:,} hires with at least one year of tenure opportunity.",
        "",
        "| Source | Cohort hires | Left in year one | Rate | Significant vs. others? |",
        "|---|---:|---:|---:|---|",
    ]
    for r in attr.itertuples():
        lines.append(f"| {r.source_channel} | {r.cohort_hires:,} | {r.first_year_exits:,} | "
                     f"{r.attrition_rate:.1%} | {'Yes' if r.significantly_different else 'No'} |")
    lines += [
        "",
        f"Chi-square test of independence: chi2 = {attr_meta['chi2']:.1f}, dof = {attr_meta['dof']}, "
        f"p = {attr_meta['p']:.2e}.",
        "",
        "## Offer acceptance by source",
        "",
        "| Source | Offers | Accepted | Acceptance rate |",
        "|---|---:|---:|---:|",
    ]
    for r in oa.itertuples():
        lines.append(f"| {r.source_channel} | {r.offers_extended:,} | {int(r.offers_accepted):,} | "
                     f"{r.acceptance_rate:.1%} |")
    lines += [
        "",
        f"Chi-square: chi2 = {oa_meta['chi2']:.1f}, p = {oa_meta['p']:.2e}.",
        "",
        "## Method notes",
        "",
        "- Time to hire is skewed (a few very long searches), so channels are compared on medians with "
        "non-parametric tests (Kruskal-Wallis, Mann-Whitney U) rather than means and t-tests.",
        "- Each channel is compared against all other channels combined; p-values are adjusted with the "
        "Benjamini-Hochberg procedure because eight comparisons are run at once.",
        "- Attrition only counts hires who started at least 365 days before the snapshot date, so recent "
        "hires don't make retention look better than it is.",
        "- Data is simulated ATS / HRIS data produced by data_generator/generate_ats_data.py.",
    ]
    with open(path, "w") as f:
        f.write("\n".join(lines) + "\n")


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--target", choices=["duckdb", "snowflake"], default="duckdb")
    p.add_argument("--duckdb-path", default=os.environ.get("DUCKDB_PATH", "data/people_analytics.duckdb"))
    p.add_argument("--out-dir", default="reports")
    args = p.parse_args()

    os.makedirs(os.path.join(args.out_dir, "charts"), exist_ok=True)
    apps, hires = read_marts(args.target, args.duckdb_path)

    tth, tth_meta = time_to_hire_tests(hires)
    oa, oa_meta = offer_acceptance_tests(apps)
    attr, attr_meta = attrition_tests(hires)

    tth.to_csv(os.path.join(args.out_dir, "time_to_hire_by_source.csv"), index=False)
    oa.to_csv(os.path.join(args.out_dir, "offer_acceptance_by_source.csv"), index=False)
    attr.to_csv(os.path.join(args.out_dir, "attrition_by_source.csv"), index=False)

    bar_chart(tth, "median_days_to_hire", "significantly_faster",
              "Median time to hire by source of hire",
              "Blue bars hire significantly faster than all other channels combined (BH-adjusted p < 0.05)",
              "Median days from application to accepted offer", "{:.0f} days",
              os.path.join(args.out_dir, "charts", "time_to_hire_by_source.png"), "faster")
    attr_plot = attr.assign(low=lambda d: d["significantly_different"] &
                            (d["attrition_rate"] < d["attrition_rate_other_channels"]))
    bar_chart(attr_plot, "attrition_rate", "low",
              "First-year attrition by source of hire",
              "Blue bars retain significantly better than other channels (BH-adjusted p < 0.05)",
              "Share of hires who left within 12 months", "{:.0%}",
              os.path.join(args.out_dir, "charts", "attrition_by_source.png"), "lower")

    write_report(os.path.join(args.out_dir, "hiring_insights.md"), tth, tth_meta, oa, oa_meta,
                 attr, attr_meta, len(apps), hires)

    print(tth[["source_channel", "hires", "median_days_to_hire", "pct_faster_than_other_channels",
               "p_value_bh", "significantly_faster"]].to_string(index=False))
    print(f"\nreport -> {os.path.join(args.out_dir, 'hiring_insights.md')}")


if __name__ == "__main__":
    main()
