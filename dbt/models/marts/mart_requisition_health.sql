-- Requisition-level pipeline health: applicants, hires, days open and SLA status.
{% set as_of = "cast('" ~ var('as_of_date') ~ "' as date)" %}

with reqs as (
    select * from {{ ref('stg_ats__requisitions') }}
),
apps as (
    select
        req_id,
        count(*)                                                   as applicants,
        sum(case when reached_onsite then 1 else 0 end)            as onsite_interviews,
        sum(case when reached_offer then 1 else 0 end)             as offers,
        sum(case when is_hired then 1 else 0 end)                  as hires,
        max(applied_at)                                            as last_application_at
    from {{ ref('fct_applications') }}
    group by 1
)

select
    r.req_id,
    r.job_title,
    r.department,
    r.job_level,
    r.location,
    r.recruiter_id,
    r.hiring_manager_id,
    r.req_status,
    r.headcount,
    r.opened_date,
    r.closed_date,
    r.target_days_to_fill,
    coalesce(a.applicants, 0)        as applicants,
    coalesce(a.onsite_interviews, 0) as onsite_interviews,
    coalesce(a.offers, 0)            as offers,
    coalesce(a.hires, 0)             as hires,
    {{ dbt.datediff('r.opened_date', 'coalesce(r.closed_date, ' ~ as_of ~ ')', 'day') }} as days_open,
    case
        when r.req_status in ('Cancelled') then 'Cancelled'
        when {{ dbt.datediff('r.opened_date', 'coalesce(r.closed_date, ' ~ as_of ~ ')', 'day') }}
             > r.target_days_to_fill then 'Over Target'
        else 'Within Target'
    end as sla_status
from reqs r
left join apps a on r.req_id = a.req_id
