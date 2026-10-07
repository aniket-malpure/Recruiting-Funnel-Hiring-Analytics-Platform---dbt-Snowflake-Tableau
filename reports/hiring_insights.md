# Hiring Insights: Speed, Offers and Retention by Source of Hire

Based on **63,339 applications** and **1,493 hires**. All differences below are tested for statistical significance (p < 0.05, adjusted for multiple comparisons).

## Headline

- **3 source channels hire faster than the rest:** University Recruiting, Employee Referral, Internal Mobility. Together they produced 694 hires with a typical time to hire of **31 days** versus **40 days** for other channels (about **23% faster**).
- **Slowest:** LinkedIn, Agency, Event, Career Site, Job Board take noticeably longer than average.
- **Retention:** Internal Mobility hires leave in their first year at 5%, compared with 33% for Agency hires (company-wide: 16%).
- **Offer acceptance** ranges from 77% to 83% by channel (not a statistically meaningful difference).

## What this means

Channels where candidates arrive with context (referrals, internal moves, campus pipelines) move through interviews faster and stay longer. Shifting sourcing effort toward these channels should shorten time to hire without hurting quality of hire. Job boards bring volume but slower, less durable hires, so they work best for high-volume roles where speed matters less than reach.

## Time to hire by source

| Source | Hires | Median days | vs. other channels | Significant? |
|---|---:|---:|---:|---|
| University Recruiting | 156 | 30.9 | +14.8% faster | Yes |
| Employee Referral | 351 | 31.0 | +17.3% faster | Yes |
| Internal Mobility | 187 | 31.8 | +12.2% faster | Yes |
| LinkedIn | 270 | 38.9 | -11.5% faster | Yes |
| Agency | 73 | 39.5 | -11.6% faster | Yes |
| Event | 29 | 40.4 | -13.8% faster | Yes |
| Career Site | 299 | 42.0 | -22.6% faster | Yes |
| Job Board | 128 | 42.4 | -21.1% faster | Yes |

Across all channels: Kruskal-Wallis H = 339.2, p = 2.49e-69.

## First-year attrition by source

Cohort: 1,089 hires with at least one year of tenure opportunity.

| Source | Cohort hires | Left in year one | Rate | Significant vs. others? |
|---|---:|---:|---:|---|
| Internal Mobility | 133 | 6 | 4.5% | Yes |
| Event | 20 | 2 | 10.0% | No |
| Employee Referral | 261 | 29 | 11.1% | Yes |
| University Recruiting | 109 | 16 | 14.7% | No |
| LinkedIn | 193 | 33 | 17.1% | No |
| Career Site | 223 | 40 | 17.9% | No |
| Job Board | 96 | 31 | 32.3% | Yes |
| Agency | 54 | 18 | 33.3% | Yes |

Chi-square test of independence: chi2 = 50.0, dof = 7, p = 1.43e-08.

## Offer acceptance by source

| Source | Offers | Accepted | Acceptance rate |
|---|---:|---:|---:|
| Internal Mobility | 225 | 187 | 83.1% |
| Employee Referral | 428 | 351 | 82.0% |
| LinkedIn | 332 | 270 | 81.3% |
| University Recruiting | 193 | 156 | 80.8% |
| Event | 36 | 29 | 80.6% |
| Agency | 93 | 73 | 78.5% |
| Career Site | 381 | 299 | 78.5% |
| Job Board | 166 | 128 | 77.1% |

Chi-square: chi2 = 4.2, p = 7.56e-01.

## Method notes

- Time to hire is skewed (a few very long searches), so channels are compared on medians with non-parametric tests (Kruskal-Wallis, Mann-Whitney U) rather than means and t-tests.
- Each channel is compared against all other channels combined; p-values are adjusted with the Benjamini-Hochberg procedure because eight comparisons are run at once.
- Attrition only counts hires who started at least 365 days before the snapshot date, so recent hires don't make retention look better than it is.
- Data is simulated ATS / HRIS data produced by data_generator/generate_ats_data.py.
