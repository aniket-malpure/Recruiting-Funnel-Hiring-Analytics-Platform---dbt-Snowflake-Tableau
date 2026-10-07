"""
Generate a realistic, simulated Applicant Tracking System (ATS) + HRIS dataset.

Outputs (CSV, written to --out-dir):
    requisitions.csv     open/closed job requisitions
    candidates.csv       candidate profiles with source channel
    applications.csv     one row per candidate x requisition application
    stage_events.csv     every stage transition an application went through
    offers.csv           offers extended, with accept / decline outcome
    employees.csv        HRIS records for hired candidates (incl. terminations)

The generator deliberately reproduces upstream ATS messiness so the dbt layer
has real work to do:
    * stage labels arrive in inconsistent casing / naming ("Phone Screen",
      "phone_screen", "Recruiter Screen") and are normalized through a seed
    * source channel labels vary ("LinkedIn", "linkedin_ads", "LI")
    * optional --inject-gaps adds unmapped stage labels and orphan events so
      the dbt tests can be shown catching upstream gaps

Usage:
    python data_generator/generate_ats_data.py --out-dir data/raw --candidates 50000
"""

from __future__ import annotations

import argparse
import os
from datetime import date, datetime, timedelta

import numpy as np
import pandas as pd

SEED = 42

DEPARTMENTS = {
    "Engineering": ["Software Engineer", "Data Engineer", "Firmware Engineer", "QA Engineer"],
    "Manufacturing": ["Production Associate", "Process Technician", "Quality Inspector"],
    "Sales": ["Sales Advisor", "Delivery Specialist", "Inside Sales Rep"],
    "Operations": ["Supply Chain Analyst", "Logistics Coordinator", "Program Manager"],
    "People": ["Recruiter", "HR Partner", "People Analyst"],
    "Service": ["Service Technician", "Service Advisor", "Mobile Technician"],
}
LOCATIONS = ["Austin, TX", "Fremont, CA", "Palo Alto, CA", "Reno, NV", "Buffalo, NY", "Orlando, FL"]
LEVELS = ["L1", "L2", "L3", "L4", "L5"]

# canonical source -> (raw label variants, applicant share, speed multiplier,
#                      quality multiplier on pass-through, 1st-year attrition prob)
SOURCES = {
    "Employee Referral": (["Employee Referral", "referral", "REFERRAL"], 0.12, 0.79, 1.16, 0.10),
    "Internal Mobility": (["Internal Transfer", "internal_mobility"], 0.05, 0.80, 1.20, 0.06),
    "University Recruiting": (["Campus", "university", "University Recruiting"], 0.09, 0.79, 1.06, 0.14),
    "LinkedIn": (["LinkedIn", "linkedin_ads", "LI"], 0.22, 1.00, 1.00, 0.17),
    "Career Site": (["Careers Page", "career_site", "Company Website"], 0.28, 1.04, 0.95, 0.19),
    "Job Board": (["Indeed", "job_board", "Glassdoor"], 0.16, 1.10, 0.90, 0.24),
    "Agency": (["Agency", "staffing_agency"], 0.05, 0.98, 1.02, 0.21),
    "Event": (["Career Fair", "event", "Hiring Event"], 0.03, 1.02, 0.95, 0.18),
}

# canonical stage -> raw label variants emitted by the "ATS"
STAGE_LABELS = {
    "Applied": ["Applied", "APPLIED", "New Applicant"],
    "Recruiter Screen": ["Phone Screen", "phone_screen", "Recruiter Screen", "PHONE SCREEN"],
    "Hiring Manager Review": ["HM Review", "Hiring Manager Review", "hm_review"],
    "Technical Assessment": ["Assessment", "Technical Assessment", "take_home"],
    "Onsite Interview": ["Onsite", "Onsite Interview", "Panel Interview", "final_round"],
    "Offer": ["Offer", "Offer Extended", "OFFER"],
    "Hired": ["Hired", "HIRED", "Offer Accepted"],
    "Rejected": ["Rejected", "Not Selected", "rejected"],
    "Withdrawn": ["Withdrawn", "Candidate Withdrew", "withdrawn"],
}
FUNNEL = ["Applied", "Recruiter Screen", "Hiring Manager Review", "Technical Assessment",
          "Onsite Interview", "Offer"]
# baseline probability of passing *into* each next stage
BASE_PASS = {
    "Recruiter Screen": 0.38,
    "Hiring Manager Review": 0.62,
    "Technical Assessment": 0.70,
    "Onsite Interview": 0.58,
    "Offer": 0.42,
}
# median days spent before moving to the next stage
BASE_DAYS = {
    "Recruiter Screen": 5,
    "Hiring Manager Review": 4,
    "Technical Assessment": 6,
    "Onsite Interview": 7,
    "Offer": 5,
    "Hired": 6,
}
TERMINATION_REASONS = ["Voluntary - Career Growth", "Voluntary - Compensation", "Voluntary - Relocation",
                       "Voluntary - Manager", "Involuntary - Performance", "Involuntary - Restructure"]

FIRST_NAMES = ["Alex", "Jordan", "Taylor", "Morgan", "Casey", "Riley", "Avery", "Jamie", "Priya", "Arjun",
               "Mei", "Wei", "Sofia", "Lucas", "Mateo", "Aisha", "Omar", "Elena", "Noah", "Emma",
               "Liam", "Olivia", "Ethan", "Maya", "Diego", "Hana", "Ken", "Zara", "Ivan", "Nina"]
LAST_NAMES = ["Smith", "Johnson", "Lee", "Garcia", "Patel", "Nguyen", "Kim", "Brown", "Martinez", "Chen",
              "Singh", "Lopez", "Davis", "Wilson", "Khan", "Rossi", "Silva", "Mueller", "Sato", "Ali"]


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--out-dir", default="data/raw")
    p.add_argument("--candidates", type=int, default=50_000)
    p.add_argument("--requisitions", type=int, default=900)
    p.add_argument("--start", default="2023-01-01")
    p.add_argument("--end", default="2026-06-30")
    p.add_argument("--as-of", default="2026-09-30", help="snapshot date for HRIS status / attrition")
    p.add_argument("--inject-gaps", action="store_true",
                   help="add unmapped stage labels + orphan events to demo dbt test failures")
    p.add_argument("--seed", type=int, default=SEED)
    return p.parse_args()


def rand_dates(rng, start: date, end: date, n: int) -> np.ndarray:
    span = (end - start).days
    return np.array([start + timedelta(days=int(d)) for d in rng.integers(0, span, n)])


def build_requisitions(rng, n: int, start: date, end: date) -> pd.DataFrame:
    depts = rng.choice(list(DEPARTMENTS), n, p=[0.30, 0.25, 0.14, 0.12, 0.05, 0.14])
    titles = [rng.choice(DEPARTMENTS[d]) for d in depts]
    opened = rand_dates(rng, start, end - timedelta(days=60), n)
    status = rng.choice(["Open", "Filled", "Cancelled", "On Hold"], n, p=[0.18, 0.68, 0.08, 0.06])
    target_days = rng.choice([30, 45, 60], n, p=[0.3, 0.5, 0.2])
    return pd.DataFrame({
        "req_id": [f"REQ-{i:05d}" for i in range(1, n + 1)],
        "job_title": titles,
        "department": depts,
        "job_level": rng.choice(LEVELS, n, p=[0.30, 0.30, 0.22, 0.13, 0.05]),
        "location": rng.choice(LOCATIONS, n, p=[0.30, 0.25, 0.15, 0.12, 0.10, 0.08]),
        "employment_type": rng.choice(["Full-Time", "Contract", "Intern"], n, p=[0.85, 0.08, 0.07]),
        "hiring_manager_id": [f"EMP-HM{int(x):04d}" for x in rng.integers(1, 260, n)],
        "recruiter_id": [f"RC-{int(x):03d}" for x in rng.integers(1, 45, n)],
        "headcount": rng.choice([1, 1, 1, 2, 3, 5, 10], n),
        "opened_date": opened,
        "target_days_to_fill": target_days,
        "req_status": status,
    })


def build_candidates(rng, n: int, start: date, end: date) -> pd.DataFrame:
    canon = list(SOURCES)
    shares = np.array([SOURCES[s][1] for s in canon])
    src = rng.choice(canon, n, p=shares / shares.sum())
    raw_src = [rng.choice(SOURCES[s][0]) for s in src]
    created = rand_dates(rng, start, end, n)
    cid = [f"CAND-{i:06d}" for i in range(1, n + 1)]
    first = rng.choice(FIRST_NAMES, n)
    last = rng.choice(LAST_NAMES, n)
    email = [f"{f.lower()}.{l.lower()}{i}@example.com" for i, (f, l) in enumerate(zip(first, last))]
    # ~1.5% duplicate-email candidate records (re-applicants) - realistic ATS noise
    dup_idx = rng.choice(n, int(n * 0.015), replace=False)
    for i in dup_idx:
        email[i] = email[(i + 1) % n].upper()
    return pd.DataFrame({
        "candidate_id": cid,
        "first_name": first,
        "last_name": last,
        "email": email,
        "source_raw": raw_src,
        "_source_canonical": src,  # dropped before writing; used for simulation only
        "years_experience": np.clip(rng.gamma(2.2, 2.4, n).round(1), 0, 35),
        "highest_education": rng.choice(["High School", "Associate", "Bachelor", "Master", "PhD"], n,
                                        p=[0.22, 0.12, 0.43, 0.19, 0.04]),
        "is_veteran": rng.random(n) < 0.06,
        "created_at": [datetime.combine(d, datetime.min.time()) + timedelta(minutes=int(m))
                       for d, m in zip(created, rng.integers(0, 1440, n))],
    })


def simulate(rng, cands: pd.DataFrame, reqs: pd.DataFrame, as_of: date, inject_gaps: bool):
    apps, events, offers, employees = [], [], [], []
    req_arr = reqs.to_dict("records")
    req_open = np.array([r["opened_date"] for r in req_arr])
    app_seq = event_seq = offer_seq = emp_seq = 0

    for c in cands.itertuples(index=False):
        src = c._5  # _source_canonical
        _, _, speed, quality, attr_p = SOURCES[src]
        n_apps = 1 if rng.random() < 0.82 else int(rng.integers(2, 4))
        cdate = c.created_at.date()
        eligible = np.where(req_open <= cdate)[0]
        if len(eligible) == 0:
            eligible = np.arange(len(req_arr))
        for req_idx in rng.choice(eligible, size=min(n_apps, len(eligible)), replace=False):
            req = req_arr[req_idx]
            app_seq += 1
            app_id = f"APP-{app_seq:07d}"
            applied_at = datetime.combine(max(cdate, req["opened_date"]), datetime.min.time()) + \
                timedelta(hours=int(rng.integers(6, 22)), minutes=int(rng.integers(0, 60)))
            level_penalty = 1 + 0.12 * LEVELS.index(req["job_level"])
            ts = applied_at
            seq = 1
            path = [("Applied", ts)]
            final_status = "Rejected"
            reached_offer = False
            for stage in FUNNEL[1:]:
                p = min(0.97, BASE_PASS[stage] * quality / (1 + 0.05 * LEVELS.index(req["job_level"])))
                # withdrawals happen more on slow pipelines
                if rng.random() < 0.035 * speed:
                    final_status = "Withdrawn"
                    ts = ts + timedelta(days=float(rng.gamma(2, 2)))
                    path.append(("Withdrawn", ts))
                    break
                if rng.random() > p:
                    ts = ts + timedelta(days=float(rng.gamma(2, 1.6)))
                    path.append(("Rejected", ts))
                    final_status = "Rejected"
                    break
                days = rng.gamma(3.0, BASE_DAYS[stage] / 3.0) * speed * level_penalty
                ts = ts + timedelta(days=float(days), hours=int(rng.integers(0, 9)))
                path.append((stage, ts))
                if stage == "Offer":
                    reached_offer = True
            offer_outcome = None
            if reached_offer:
                offer_seq += 1
                offer_id = f"OFR-{offer_seq:06d}"
                accept_p = min(0.95, 0.78 * (0.85 + 0.15 * quality))
                accepted = rng.random() < accept_p
                base = {"L1": 62000, "L2": 85000, "L3": 118000, "L4": 152000, "L5": 195000}[req["job_level"]]
                salary = round(base * rng.normal(1.0, 0.08), -2)
                responded = ts + timedelta(days=float(rng.gamma(2.0, 1.6) * speed))
                offer_outcome = "Accepted" if accepted else rng.choice(
                    ["Declined - Compensation", "Declined - Competing Offer", "Declined - Location",
                     "Declined - Role Fit"], p=[0.38, 0.34, 0.16, 0.12])
                offers.append({
                    "offer_id": offer_id, "application_id": app_id, "offer_extended_at": ts,
                    "offer_responded_at": responded, "offer_status": offer_outcome,
                    "base_salary_usd": salary, "sign_on_bonus_usd": float(rng.choice([0, 0, 2500, 5000, 10000])),
                })
                if accepted:
                    hired_ts = responded + timedelta(days=float(rng.gamma(2, BASE_DAYS["Hired"] / 2) * speed))
                    path.append(("Hired", hired_ts))
                    final_status = "Hired"
                    ts = hired_ts
                    emp_seq += 1
                    start_date = (hired_ts + timedelta(days=int(rng.integers(10, 35)))).date()
                    term_date, term_reason = None, None
                    if start_date < as_of:
                        tenure_days = (as_of - start_date).days
                        # exponential-ish hazard calibrated so ~attr_p leave in year one
                        lam = -np.log(1 - attr_p) / 365
                        leave_after = rng.exponential(1 / lam)
                        if leave_after < tenure_days:
                            term_date = start_date + timedelta(days=int(max(14, leave_after)))
                            term_reason = rng.choice(TERMINATION_REASONS, p=[0.28, 0.22, 0.12, 0.14, 0.16, 0.08])
                    employees.append({
                        "employee_id": f"EMP-{emp_seq:06d}", "candidate_id": c.candidate_id,
                        "application_id": app_id, "req_id": req["req_id"], "department": req["department"],
                        "job_title": req["job_title"], "job_level": req["job_level"], "location": req["location"],
                        "hire_date": start_date, "termination_date": term_date,
                        "termination_reason": term_reason,
                        "employment_status": "Terminated" if term_date else
                        ("Active" if start_date <= as_of else "Pre-Start"),
                    })
                else:
                    ts = responded
                    path.append(("Rejected", ts))
                    final_status = "Offer Declined"
            if final_status not in ("Hired", "Offer Declined", "Withdrawn") and len(path) == 1:
                path.append(("Rejected", ts + timedelta(days=float(rng.gamma(2, 2)))))
            for stage, at in path:
                event_seq += 1
                events.append({
                    "event_id": f"EVT-{event_seq:08d}", "application_id": app_id,
                    "stage_raw": rng.choice(STAGE_LABELS[stage]), "stage_entered_at": at,
                    "changed_by": req["recruiter_id"],
                })
            apps.append({
                "application_id": app_id, "candidate_id": c.candidate_id, "req_id": req["req_id"],
                "applied_at": applied_at, "application_status": final_status,
                "last_updated_at": path[-1][1], "is_internal": src == "Internal Mobility",
            })

    if inject_gaps:
        sample = rng.choice(len(events), 40, replace=False)
        for i in sample:
            events[i]["stage_raw"] = rng.choice(["Exec Review", "Background Check", "ref_check"])
        for k in range(15):
            events.append({"event_id": f"EVT-X{k:06d}", "application_id": f"APP-9{k:06d}",
                           "stage_raw": "Applied", "stage_entered_at": datetime(2026, 1, 5), "changed_by": "RC-000"})

    return (pd.DataFrame(apps), pd.DataFrame(events), pd.DataFrame(offers), pd.DataFrame(employees))


def main() -> None:
    args = parse_args()
    rng = np.random.default_rng(args.seed)
    start, end, as_of = (date.fromisoformat(x) for x in (args.start, args.end, args.as_of))
    os.makedirs(args.out_dir, exist_ok=True)

    reqs = build_requisitions(rng, args.requisitions, start, end)
    cands = build_candidates(rng, args.candidates, start, end)
    apps, events, offers, emps = simulate(rng, cands, reqs, as_of, args.inject_gaps)

    # requisitions with zero hires shouldn't be marked Filled
    filled = set(emps["req_id"]) if len(emps) else set()
    reqs.loc[(reqs["req_status"] == "Filled") & (~reqs["req_id"].isin(filled)), "req_status"] = "Open"
    first_hire = emps.groupby("req_id")["hire_date"].min() if len(emps) else pd.Series(dtype="object")
    reqs["closed_date"] = reqs.apply(
        lambda r: first_hire.get(r["req_id"]) if r["req_status"] == "Filled" else None, axis=1)

    cands = cands.drop(columns=["_source_canonical"])
    outputs = {"requisitions": reqs, "candidates": cands, "applications": apps,
               "stage_events": events, "offers": offers, "employees": emps}
    for name, df in outputs.items():
        path = os.path.join(args.out_dir, f"{name}.csv")
        df.to_csv(path, index=False)
        print(f"wrote {len(df):>8,} rows -> {path}")


if __name__ == "__main__":
    main()
