import subprocess
import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def raw(tmp_path_factory):
    out = tmp_path_factory.mktemp("raw")
    subprocess.run([sys.executable, str(ROOT / "data_generator" / "generate_ats_data.py"),
                    "--out-dir", str(out), "--candidates", "2000", "--requisitions", "80"], check=True)
    return {p.stem: pd.read_csv(p) for p in out.glob("*.csv")}


def test_all_tables_written(raw):
    assert set(raw) == {"requisitions", "candidates", "applications", "stage_events", "offers", "employees"}


def test_primary_keys_unique(raw):
    for table, key in [("requisitions", "req_id"), ("candidates", "candidate_id"),
                       ("applications", "application_id"), ("stage_events", "event_id"),
                       ("offers", "offer_id"), ("employees", "employee_id")]:
        assert raw[table][key].is_unique, table


def test_every_application_has_an_applied_event(raw):
    applied = raw["stage_events"][raw["stage_events"]["stage_raw"].str.lower().isin(
        ["applied", "new applicant"])]
    assert set(raw["applications"]["application_id"]) == set(applied["application_id"])


def test_hires_match_hris(raw):
    hired = raw["applications"][raw["applications"]["application_status"] == "Hired"]
    assert len(hired) == len(raw["employees"])


def test_simulation_columns_not_leaked(raw):
    assert "_source_canonical" not in raw["candidates"].columns


def test_seed_covers_every_generated_label(raw):
    seed = pd.read_csv(ROOT / "dbt" / "seeds" / "stage_mapping.csv")
    labels = set(raw["stage_events"]["stage_raw"].str.strip().str.lower())
    assert labels <= set(seed["raw_label"])
    src_seed = pd.read_csv(ROOT / "dbt" / "seeds" / "source_channel_mapping.csv")
    assert set(raw["candidates"]["source_raw"].str.strip().str.lower()) <= set(src_seed["raw_source"])
