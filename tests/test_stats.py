import numpy as np
import pandas as pd

from hiring_stats import attrition_tests, bh_adjust, time_to_hire_tests


def test_bh_adjust_matches_reference():
    p = np.array([0.01, 0.04, 0.03, 0.20])
    # reference values from statsmodels.multipletests(method="fdr_bh")
    expected = np.array([0.04, 0.0533333, 0.0533333, 0.20])
    assert np.allclose(bh_adjust(p), expected, atol=1e-6)


def test_bh_adjust_is_monotone_and_bounded():
    p = np.random.default_rng(0).random(50)
    adj = bh_adjust(p)
    assert (adj >= p - 1e-12).all() and (adj <= 1).all()
    order = np.argsort(p)
    assert (np.diff(adj[order]) >= -1e-12).all()


def _hires(rng, n=300):
    fast = pd.DataFrame({"source_channel": "Fast", "days_to_hire": rng.normal(25, 4, n)})
    slow_a = pd.DataFrame({"source_channel": "SlowA", "days_to_hire": rng.normal(40, 4, n)})
    slow_b = pd.DataFrame({"source_channel": "SlowB", "days_to_hire": rng.normal(41, 4, n)})
    return pd.concat([fast, slow_a, slow_b], ignore_index=True)


def test_time_to_hire_flags_only_the_fast_channel():
    df, meta = time_to_hire_tests(_hires(np.random.default_rng(1)))
    assert meta["kruskal_p"] < 0.001
    assert df.loc[df["significantly_faster"], "source_channel"].tolist() == ["Fast"]


def test_attrition_detects_high_attrition_channel():
    rng = np.random.default_rng(2)
    rows = []
    for src, rate in [("Sticky", 0.05), ("Normal", 0.15), ("Leaky", 0.40)]:
        for left in rng.random(400) < rate:
            rows.append({"source_channel": src, "is_first_year_cohort": True, "left_within_first_year": left})
    df, meta = attrition_tests(pd.DataFrame(rows))
    assert meta["p"] < 0.001
    leaky = df.set_index("source_channel").loc["Leaky"]
    assert leaky["significantly_different"] and leaky["z_score"] > 0
