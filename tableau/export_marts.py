"""
Export dbt marts to CSV for Tableau Public (which can't connect live to Snowflake).

Tableau Desktop / Server users should connect live to PEOPLE_ANALYTICS.MARTS instead
(see tableau/dashboard_guide.md); this script is for the free Tableau Public path.

Usage:
    python tableau/export_marts.py --target duckdb
"""

from __future__ import annotations

import argparse
import os

MARTS = [
    "mart_recruiting_funnel",
    "mart_time_to_hire",
    "mart_offer_acceptance",
    "mart_attrition_by_source",
    "mart_requisition_health",
    "fct_hires",
]


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--target", choices=["duckdb", "snowflake"], default="duckdb")
    p.add_argument("--duckdb-path", default=os.environ.get("DUCKDB_PATH", "data/people_analytics.duckdb"))
    p.add_argument("--out-dir", default="tableau/extracts")
    args = p.parse_args()
    os.makedirs(args.out_dir, exist_ok=True)

    if args.target == "duckdb":
        import duckdb

        con = duckdb.connect(args.duckdb_path, read_only=True)
        fetch = lambda t: con.execute(f"select * from marts.{t}").df()  # noqa: E731
    else:
        import pandas as pd
        import snowflake.connector

        con = snowflake.connector.connect(
            account=os.environ["SNOWFLAKE_ACCOUNT"], user=os.environ["SNOWFLAKE_USER"],
            password=os.environ.get("SNOWFLAKE_PASSWORD"),
            role=os.environ.get("SNOWFLAKE_ROLE", "REPORTER"),
            warehouse=os.environ.get("SNOWFLAKE_WAREHOUSE", "PEOPLE_ANALYTICS_WH"),
            database=os.environ.get("SNOWFLAKE_DATABASE", "PEOPLE_ANALYTICS"),
        )
        fetch = lambda t: pd.read_sql(f"select * from marts.{t}", con).rename(columns=str.lower)  # noqa: E731

    for table in MARTS:
        df = fetch(table)
        path = os.path.join(args.out_dir, f"{table}.csv")
        df.to_csv(path, index=False)
        print(f"{table:<28} {len(df):>8,} rows -> {path}")
    con.close()


if __name__ == "__main__":
    main()
