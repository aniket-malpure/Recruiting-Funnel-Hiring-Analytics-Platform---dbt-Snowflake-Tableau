-- Long-format funnel for Tableau: one row per month x department x level x source x stage,
-- with stage-to-stage and overall conversion already computed.
with apps as (
    select * from {{ ref('fct_applications') }}
),

stages as (
    {% set stages = [
        (1, 'Applied', 'true'),
        (2, 'Recruiter Screen', 'reached_screen'),
        (3, 'Hiring Manager Review', 'reached_hm_review'),
        (4, 'Technical Assessment', 'reached_assessment'),
        (5, 'Onsite Interview', 'reached_onsite'),
        (6, 'Offer', 'reached_offer'),
        (7, 'Hired', 'is_hired'),
    ] %}
    {% for order, name, flag in stages %}
    select
        application_month,
        department,
        job_level,
        source_channel,
        {{ order }}      as stage_order,
        '{{ name }}'     as stage_name,
        sum(case when {{ flag }} then 1 else 0 end) as applications_reached
    from apps
    group by 1, 2, 3, 4
    {% if not loop.last %}union all{% endif %}
    {% endfor %}
)

select
    application_month,
    department,
    job_level,
    source_channel,
    stage_order,
    stage_name,
    applications_reached,
    first_value(applications_reached) over (
        partition by application_month, department, job_level, source_channel
        order by stage_order
    ) as applications_total,
    lag(applications_reached) over (
        partition by application_month, department, job_level, source_channel
        order by stage_order
    ) as previous_stage_reached,
    round(
        applications_reached * 1.0 / nullif(lag(applications_reached) over (
            partition by application_month, department, job_level, source_channel
            order by stage_order), 0), 4
    ) as stage_conversion_rate
from stages
