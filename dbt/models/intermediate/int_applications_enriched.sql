-- Application grain, joined to candidate source, requisition attributes,
-- stage timestamps and offer outcome. Feeds every mart downstream.
with apps as (
    select * from {{ ref('stg_ats__applications') }}
),
cands as (
    select * from {{ ref('stg_ats__candidates') }}
),
reqs as (
    select * from {{ ref('stg_ats__requisitions') }}
),
prog as (
    select * from {{ ref('int_application_stage_progression') }}
),
offers as (
    select * from {{ ref('stg_ats__offers') }}
)

select
    a.application_id,
    a.candidate_id,
    a.req_id,
    a.applied_at,
    cast({{ dbt.date_trunc('month', 'a.applied_at') }} as date) as application_month,
    a.application_status,
    a.is_internal,

    c.source_channel,
    c.source_category,
    c.is_paid_channel,
    c.years_experience,
    c.highest_education,
    c.is_veteran,

    r.department,
    r.job_title,
    r.job_level,
    r.location,
    r.employment_type,
    r.recruiter_id,
    r.hiring_manager_id,
    r.opened_date as req_opened_date,

    p.screened_at,
    p.hm_review_at,
    p.assessment_at,
    p.onsite_at,
    p.offer_stage_at,
    p.hired_at,
    p.rejected_at,
    p.withdrawn_at,
    p.exited_at,
    p.furthest_stage,
    coalesce(p.max_stage_order, 1) as max_stage_order,

    o.offer_id,
    o.offer_extended_at,
    o.offer_responded_at,
    o.offer_status,
    o.is_accepted as offer_accepted,
    o.decline_reason,
    o.base_salary_usd

from apps a
left join cands  c on a.candidate_id = c.candidate_id
left join reqs   r on a.req_id = r.req_id
left join prog   p on a.application_id = p.application_id
left join offers o on a.application_id = o.application_id
