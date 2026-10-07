-- Monthly time-to-hire and time-to-fill KPIs by department and source channel.
with hires as (
    select * from {{ ref('fct_hires') }}
)

select
    start_month,
    department,
    source_channel,
    count(*)                         as hires,
    round(avg(days_to_hire), 1)      as avg_days_to_hire,
    round(median(days_to_hire), 1)   as median_days_to_hire,
    round(avg(days_to_fill), 1)      as avg_days_to_fill,
    round(median(days_to_fill), 1)   as median_days_to_fill,
    min(days_to_hire)                as min_days_to_hire,
    max(days_to_hire)                as max_days_to_hire
from hires
group by 1, 2, 3
