"""
Load the raw ATS / HRIS CSVs into the warehouse RAW schema.

Targets:
    snowflake  production path; uses snowflake-connector-python write_pandas
    duckdb     local / CI path; same table names so dbt runs unchanged

Every table gets a _loaded_at timestamp, which dbt source freshness checks use.

Usage:
    python ingestion/load_raw.py --target duckdb
    python ingestion/load_raw.py --target snowflake   # reads SNOWFLAKE_* env vars
"""

from __future__ import annotations

import argparse
import os
from datetime import datetime, timezone

import pandas as pd

TABLES = {
    "requisitions": ["opened_date", "closed_date"],
    "candidates": ["created_at"],
    "applications": ["applied_at", "last_updated_at"],
    "stage_events": ["stage_entered_at"],
    "offers": ["offer_extended_at", "offer_responded_at"],
    "employees": ["hire_date", "termination_date"],
}


def read_tables(raw_dir: str) -> dict[str, pd.DataFrame]:
    loaded_at = datetime.now(timezone.utc).replace(tzinfo=None)
    frames = {}
    for name, date_cols in TABLES.items():
        df = pd.read_csv(os.path.join(raw_dir, f"{name}.csv"), parse_dates=date_cols)
        df["_loaded_at"] = loaded_at
        frames[name] = df
    return frames


def load_duckdb(frames: dict[str, pd.DataFrame], path: str, schema: str) -> None:
    import duckdb

    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    con = duckdb.connect(path)
    con.execute(f"create schema if not exists {schema}")
    for name, df in frames.items():
        con.register("df_view", df)
        con.execute(f"create or replace table {schema}.{name} as select * from df_view")
        con.unregister("df_view")
        n = con.execute(f"select count(*) from {schema}.{name}").fetchone()[0]
        print(f"duckdb  {schema}.{name:<14} {n:>9,} rows")
    con.close()


def load_snowflake(frames: dict[str, pd.DataFrame], schema: str) -> None:
    import snowflake.connector
    from snowflake.connector.pandas_tools import write_pandas

    con = snowflake.connector.connect(
        account=os.environ["SNOWFLAKE_ACCOUNT"],
        user=os.environ["SNOWFLAKE_USER"],
        password=os.environ.get("SNOWFLAKE_PASSWORD"),
        authenticator=os.environ.get("SNOWFLAKE_AUTHENTICATOR", "snowflake"),
        role=os.environ.get("SNOWFLAKE_ROLE", "TRANSFORMER"),
        warehouse=os.environ.get("SNOWFLAKE_WAREHOUSE", "PEOPLE_ANALYTICS_WH"),
        database=os.environ.get("SNOWFLAKE_DATABASE", "PEOPLE_ANALYTICS"),
    )
    con.cursor().execute(f"create schema if not exists {schema.upper()}")
    for name, df in frames.items():
        out = df.copy()
        out.columns = [c.upper() for c in out.columns]
        # date-only columns: keep them as DATE in Snowflake
        for col in out.columns:
            if col.endswith("_DATE"):
                out[col] = pd.to_datetime(out[col]).dt.date
        ok, _, nrows, _ = write_pandas(
            con, out, table_name=name.upper(), schema=schema.upper(),
            auto_create_table=True, overwrite=True, quote_identifiers=False, use_logical_type=True,
        )
        print(f"snowflake {schema.upper()}.{name.upper():<14} {nrows:>9,} rows  ok={ok}")
    con.close()


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--target", choices=["duckdb", "snowflake"], default="duckdb")
    p.add_argument("--raw-dir", default="data/raw")
    p.add_argument("--schema", default="raw")
    p.add_argument("--duckdb-path", default=os.environ.get("DUCKDB_PATH", "data/people_analytics.duckdb"))
    args = p.parse_args()

    frames = read_tables(args.raw_dir)
    if args.target == "duckdb":
        load_duckdb(frames, args.duckdb_path, args.schema)
    else:
        load_snowflake(frames, args.schema)


if __name__ == "__main__":
    main()
