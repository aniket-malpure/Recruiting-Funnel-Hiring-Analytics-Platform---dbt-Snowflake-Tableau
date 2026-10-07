-- Ad hoc: recruiter-level pipeline scorecard for the last 12 months of applications.
-- Compile with `dbt compile --select recruiter_scorecard` and run the SQL in target/compiled.
{% set as_of = "cast('" ~ var('as_of_date') ~ "' as date)" %}

select
    recruiter_id,
    count(*)                                                    as applications,
    sum(case when reached_screen then 1 else 0 end)             as screens,
    sum(case when reached_onsite then 1 else 0 end)             as onsites,
    sum(case when reached_offer then 1 else 0 end)              as offers,
    sum(case when is_hired then 1 else 0 end)                   as hires,
    round(sum(case when is_hired then 1 else 0 end) * 1.0
          / nullif(sum(case when reached_onsite then 1 else 0 end), 0), 3) as onsite_to_hire_rate,
    round(median(days_to_hire), 1)                              as median_days_to_hire
from {{ ref('fct_applications') }}
where applied_at >= {{ dbt.dateadd('month', -12, as_of) }}
group by recruiter_id
order by hires desc
