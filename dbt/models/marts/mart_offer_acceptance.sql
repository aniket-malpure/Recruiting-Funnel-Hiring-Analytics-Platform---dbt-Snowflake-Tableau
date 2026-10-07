-- Offer acceptance rate and decline reasons by month, department, level and source.
with offers as (
    select * from {{ ref('fct_applications') }}
    where offer_id is not null
)

select
    application_month,
    department,
    job_level,
    source_channel,
    count(*)                                                        as offers_extended,
    sum(case when offer_accepted then 1 else 0 end)                 as offers_accepted,
    round(sum(case when offer_accepted then 1 else 0 end) * 1.0 / count(*), 4) as offer_acceptance_rate,
    sum(case when decline_reason = 'Compensation' then 1 else 0 end)       as declined_compensation,
    sum(case when decline_reason = 'Competing Offer' then 1 else 0 end)    as declined_competing_offer,
    sum(case when decline_reason = 'Location' then 1 else 0 end)           as declined_location,
    sum(case when decline_reason = 'Role Fit' then 1 else 0 end)           as declined_role_fit,
    round(avg(days_offer_to_response), 1)                           as avg_days_offer_to_response,
    round(avg(base_salary_usd), 0)                                  as avg_offer_base_salary_usd
from offers
group by 1, 2, 3, 4
