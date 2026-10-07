-- Normalizes inconsistent ATS stage labels ("Phone Screen", "phone_screen", "PHONE SCREEN")
-- to one canonical stage via the stage_mapping seed. Any label missing from the seed
-- surfaces as a null canonical_stage and fails the not_null test, which is how new
-- upstream workflow stages get caught before they silently drop out of the funnel.
with source as (
    select * from {{ source('ats', 'stage_events') }}
),

stage_map as (
    select * from {{ ref('stage_mapping') }}
)

select
    e.event_id,
    e.application_id,
    e.stage_raw,
    m.canonical_stage,
    m.stage_order,
    m.stage_group,
    m.is_terminal,
    cast(e.stage_entered_at as {{ dbt.type_timestamp() }}) as stage_entered_at,
    e.changed_by,
    e._loaded_at
from source e
left join stage_map m
    on lower(trim(e.stage_raw)) = m.raw_label
