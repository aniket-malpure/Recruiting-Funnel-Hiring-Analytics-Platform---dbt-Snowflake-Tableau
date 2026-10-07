# Local end-to-end run on DuckDB. For Snowflake: set -a; source .env; set +a; make all TARGET=snowflake
TARGET ?= duckdb
PY ?= python

.PHONY: install data load build freshness test docs analyze export all gaps clean

install:
	pip install -r requirements-dev.txt

data:
	$(PY) data_generator/generate_ats_data.py --out-dir data/raw --candidates 50000

load:
	$(PY) ingestion/load_raw.py --target $(TARGET)

build:
	cd dbt && DBT_TARGET=$(TARGET) dbt build --profiles-dir .

freshness:
	cd dbt && DBT_TARGET=$(TARGET) dbt source freshness --profiles-dir .

test:
	$(PY) -m pytest -q tests

docs:
	cd dbt && DBT_TARGET=$(TARGET) dbt docs generate --profiles-dir . && dbt docs serve --profiles-dir .

analyze:
	$(PY) analysis/hiring_stats.py --target $(TARGET)

export:
	$(PY) tableau/export_marts.py --target $(TARGET)

all: data load build freshness analyze export

# Demo: inject unmapped stage labels + orphan events and watch dbt tests block the build
gaps:
	$(PY) data_generator/generate_ats_data.py --out-dir data/raw_gaps --candidates 3000 --requisitions 100 --inject-gaps
	$(PY) ingestion/load_raw.py --raw-dir data/raw_gaps --duckdb-path data/gaps.duckdb
	cd dbt && DUCKDB_PATH=../data/gaps.duckdb dbt build --profiles-dir . || echo "Expected failure: dbt caught the upstream gaps above."

clean:
	rm -rf data/raw data/raw_gaps data/*.duckdb dbt/target dbt/logs tableau/extracts reports
