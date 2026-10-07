with source as (
    select * from {{ source('ats', 'applications') }}
)

select
    application_id,
    candidate_id,
    req_id,
    cast(applied_at as {{ dbt.type_timestamp() }})      as applied_at,
    application_status,
    cast(last_updated_at as {{ dbt.type_timestamp() }}) as last_updated_at,
    cast(is_internal as boolean)                        as is_internal,
    _loaded_at
from source
