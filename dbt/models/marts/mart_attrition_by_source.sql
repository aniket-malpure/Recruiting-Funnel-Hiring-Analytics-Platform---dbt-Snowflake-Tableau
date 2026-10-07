-- First-year attrition by source of hire and department, limited to hires
-- with a full year of tenure opportunity (see fct_hires.is_first_year_cohort).
with cohort as (
    select * from {{ ref('fct_hires') }}
    where is_first_year_cohort
)

select
    source_channel,
    department,
    count(*)                                                       as cohort_hires,
    sum(case when left_within_first_year then 1 else 0 end)        as first_year_exits,
    sum(case when left_within_first_year and termination_type = 'Voluntary' then 1 else 0 end)   as voluntary_exits,
    sum(case when left_within_first_year and termination_type = 'Involuntary' then 1 else 0 end) as involuntary_exits,
    round(sum(case when left_within_first_year then 1 else 0 end) * 1.0 / count(*), 4)        as first_year_attrition_rate,
    round(avg(days_to_hire), 1)                                    as avg_days_to_hire
from cohort
group by 1, 2
