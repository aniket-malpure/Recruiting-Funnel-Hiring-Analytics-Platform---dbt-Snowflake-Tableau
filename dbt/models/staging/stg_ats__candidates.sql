-- Candidate PII is minimized here: names are dropped and email is hashed so marts
-- and Tableau never expose personal contact details.
with source as (
    select * from {{ source('ats', 'candidates') }}
),

channel_map as (
    select * from {{ ref('source_channel_mapping') }}
)

select
    s.candidate_id,
    {{ dbt.hash("lower(trim(s.email))") }}      as email_hash,
    s.source_raw,
    m.source_channel,
    m.source_category,
    m.is_paid_channel,
    cast(s.years_experience as {{ dbt.type_float() }}) as years_experience,
    s.highest_education,
    cast(s.is_veteran as boolean)               as is_veteran,
    cast(s.created_at as {{ dbt.type_timestamp() }}) as created_at,
    s._loaded_at
from source s
left join channel_map m
    on lower(trim(s.source_raw)) = m.raw_source
