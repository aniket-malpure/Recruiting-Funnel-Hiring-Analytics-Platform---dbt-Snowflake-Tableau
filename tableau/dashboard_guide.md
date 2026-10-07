# Tableau Dashboard Build Guide

Three dashboards on top of the dbt marts. Build time is about 60 to 90 minutes.

## 1. Connect

**Tableau Desktop (live):** Connect > Snowflake > server `<account>.snowflakecomputing.com`,
role `REPORTER`, warehouse `PEOPLE_ANALYTICS_WH`, database `PEOPLE_ANALYTICS`, schema `MARTS`.

**Tableau Public (free):** run `python tableau/export_marts.py`, then Connect > Text file and add
every CSV in `tableau/extracts/` as its own data source.

Data sources to add:

| Data source | Grain | Used on |
|---|---|---|
| `mart_recruiting_funnel` | month x dept x level x source x stage | Funnel |
| `mart_time_to_hire` | start month x dept x source | Speed & Offers |
| `mart_offer_acceptance` | month x dept x level x source | Speed & Offers |
| `mart_attrition_by_source` | source x dept | Quality of Hire |
| `mart_requisition_health` | requisition | Funnel (req table) |
| `fct_hires` | hire | Quality of Hire (distribution) |

## 2. Calculated fields

Create these on the data source named in brackets. Aggregate in Tableau rather than
averaging pre-computed rates, so totals stay correct when filters change.

```
// [mart_recruiting_funnel] Stage Conversion %
SUM([Applications Reached]) / SUM([Previous Stage Reached])

// [mart_recruiting_funnel] Overall Conversion %   (share of applicants reaching this stage)
SUM([Applications Reached]) / SUM([Applications Total])

// [mart_recruiting_funnel] Drop-off
SUM([Previous Stage Reached]) - SUM([Applications Reached])

// [mart_offer_acceptance] Offer Acceptance %
SUM([Offers Accepted]) / SUM([Offers Extended])

// [mart_time_to_hire] Weighted Avg Days to Hire
SUM([Avg Days To Hire] * [Hires]) / SUM([Hires])

// [mart_attrition_by_source] First-Year Attrition %
SUM([First Year Exits]) / SUM([Cohort Hires])

// [mart_attrition_by_source] Attrition vs Company
[First-Year Attrition %] - WINDOW_SUM(SUM([First Year Exits])) / WINDOW_SUM(SUM([Cohort Hires]))

// [mart_requisition_health] Over SLA Flag
IF [Sla Status] = "Over Target" THEN 1 ELSE 0 END
```

## 3. Dashboards

### Dashboard 1: Recruiting Funnel

- **KPI row (4 tiles):** Applications, Offers, Hires, Overall Applied-to-Hire %.
  Each tile is a single big number with last-90-days comparison as small text.
- **Funnel bar chart:** Rows = `Stage Name` sorted by `Stage Order`; Columns = `SUM(Applications Reached)`.
  Label each bar with the count and `Stage Conversion %`. One color for all bars.
- **Conversion heatmap:** Rows = `Source Channel`, Columns = `Stage Name`, Color = `Stage Conversion %`
  (single blue sequential ramp). Spots the stage where each channel leaks.
- **Open requisitions table** from `mart_requisition_health`, filtered to `Req Status = Open`,
  sorted by `Days Open` descending, with `Sla Status` shown as text plus an icon.
- **Filters (one row, top):** Application Month (range), Department, Job Level, Source Channel.
  Apply to all worksheets using related data sources (`Department`, `Source Channel` relationships).

### Dashboard 2: Speed & Offers

- **Line chart:** `Start Month` (continuous month) vs `Weighted Avg Days to Hire`, one line.
  Add a reference line at the target (30 days).
- **Bar chart:** median days to hire by `Source Channel`, sorted ascending. Highlight the channels
  flagged `significantly_faster` in `reports/time_to_hire_by_source.csv` (add the CSV and join on
  `Source Channel`), and say "significantly faster" in the label, not only with color.
- **Offer acceptance bar:** `Offer Acceptance %` by `Department`.
- **Decline reasons:** stacked bar of the four `Declined *` columns by `Job Level`
  (use Measure Names / Measure Values), 2px white borders between segments.

### Dashboard 3: Quality of Hire

- **Bar chart:** `First-Year Attrition %` by `Source Channel` with a reference line at the
  company rate.
- **Scatter:** x = median days to hire, y = first-year attrition %, one mark per source channel,
  labeled. The bottom-left quadrant is "fast and sticky."
- **Tenure distribution:** histogram of `Tenure Days` from `fct_hires` (bin size 30),
  colored by `Termination Type` only where terminated.

## 4. Publish

Tableau Public: File > Save to Tableau Public. Paste the URL into
`dbt/models/marts/_exposures.yml` (`url:`) so `dbt docs` links the lineage graph to the live
dashboard, and add it to the README.

## 5. Keep it trustworthy

Publish only after `dbt build` passes. In CI, a failed test stops the marts from rebuilding, so
the dashboard keeps showing the last good data instead of a broken refresh.
