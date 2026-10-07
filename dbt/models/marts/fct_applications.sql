-- Application-grain fact: funnel flags plus elapsed days between stages.
with e as (
    select * from {{ ref('int_applications_enriched') }}
)

select
    application_id,
    candidate_id,
    req_id,
    applied_at,
    application_month,
    application_status,
    source_channel,
    source_category,
    department,
    job_title,
    job_level,
    location,
    recruiter_id,
    furthest_stage,
    max_stage_order,

    max_stage_order >= 2 as reached_screen,
    max_stage_order >= 3 as reached_hm_review,
    max_stage_order >= 4 as reached_assessment,
    max_stage_order >= 5 as reached_onsite,
    max_stage_order >= 6 as reached_offer,
    max_stage_order >= 7 as is_hired,

    {{ days_between('applied_at', 'screened_at') }}       as days_to_screen,
    {{ days_between('screened_at', 'onsite_at') }}        as days_screen_to_onsite,
    {{ days_between('onsite_at', 'offer_extended_at') }}  as days_onsite_to_offer,
    {{ days_between('offer_extended_at', 'offer_responded_at') }} as days_offer_to_response,
    {{ days_between('applied_at', 'hired_at') }}          as days_to_hire,
    {{ days_between('applied_at', 'exited_at') }}         as days_in_pipeline,

    offer_id,
    offer_status,
    offer_accepted,
    decline_reason,
    base_salary_usd
from e
