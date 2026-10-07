-- One row per application with the first time it entered each canonical funnel stage.
-- A later stage only counts if every earlier funnel stage is also present, so a skipped
-- stage in the ATS can't inflate conversion at the next step.
with events as (
    select * from {{ ref('stg_ats__stage_events') }}
),

pivoted as (
    select
        application_id,
        min(case when canonical_stage = 'Applied'               then stage_entered_at end) as applied_stage_at,
        min(case when canonical_stage = 'Recruiter Screen'      then stage_entered_at end) as screened_at,
        min(case when canonical_stage = 'Hiring Manager Review' then stage_entered_at end) as hm_review_at,
        min(case when canonical_stage = 'Technical Assessment'  then stage_entered_at end) as assessment_at,
        min(case when canonical_stage = 'Onsite Interview'      then stage_entered_at end) as onsite_at,
        min(case when canonical_stage = 'Offer'                 then stage_entered_at end) as offer_stage_at,
        min(case when canonical_stage = 'Hired'                 then stage_entered_at end) as hired_at,
        min(case when canonical_stage = 'Rejected'              then stage_entered_at end) as rejected_at,
        min(case when canonical_stage = 'Withdrawn'             then stage_entered_at end) as withdrawn_at,
        max(case when stage_group = 'Funnel' then stage_order end)                         as max_stage_order,
        count(*)                                                                           as stage_event_count
    from events
    group by application_id
)

select
    p.*,
    case p.max_stage_order
        when 1 then 'Applied'
        when 2 then 'Recruiter Screen'
        when 3 then 'Hiring Manager Review'
        when 4 then 'Technical Assessment'
        when 5 then 'Onsite Interview'
        when 6 then 'Offer'
        when 7 then 'Hired'
    end as furthest_stage,
    coalesce(p.hired_at, p.rejected_at, p.withdrawn_at) as exited_at
from pivoted p
