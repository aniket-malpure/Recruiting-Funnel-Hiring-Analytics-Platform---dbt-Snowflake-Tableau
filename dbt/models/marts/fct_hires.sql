-- One row per hire: time-to-hire, time-to-fill and first-year retention outcome.
{% set as_of = "cast('" ~ var('as_of_date') ~ "' as date)" %}
{% set window = var('attrition_window_days') %}

with apps as (
    select * from {{ ref('fct_applications') }} where is_hired
),
emps as (
    select * from {{ ref('stg_hris__employees') }}
),
reqs as (
    select req_id, opened_date from {{ ref('stg_ats__requisitions') }}
),
enriched as (
    select application_id, hired_at from {{ ref('int_applications_enriched') }}
)

select
    emp.employee_id,
    a.application_id,
    a.candidate_id,
    a.req_id,
    a.source_channel,
    a.source_category,
    a.department,
    a.job_title,
    a.job_level,
    a.location,
    a.recruiter_id,
    en.hired_at                                   as offer_accepted_at,
    emp.hire_date                                 as start_date,
    cast({{ dbt.date_trunc('month', 'emp.hire_date') }} as date) as start_month,
    a.days_to_hire,
    {{ dbt.datediff('r.opened_date', 'emp.hire_date', 'day') }} as days_to_fill,
    a.base_salary_usd,
    emp.employment_status,
    emp.termination_date,
    emp.termination_type,
    emp.termination_reason,
    {{ dbt.datediff('emp.hire_date', "coalesce(emp.termination_date, " ~ as_of ~ ")", 'day') }} as tenure_days,

    -- only hires with a full year of tenure opportunity enter the attrition cohort
    emp.hire_date <= {{ dbt.dateadd('day', -window, as_of) }}  as is_first_year_cohort,
    case
        when emp.termination_date is not null
         and emp.termination_date < {{ dbt.dateadd('day', window, 'emp.hire_date') }}
        then true else false
    end                                           as left_within_first_year
from apps a
join emps emp      on a.application_id = emp.application_id
left join reqs r   on a.req_id = r.req_id
left join enriched en on a.application_id = en.application_id
