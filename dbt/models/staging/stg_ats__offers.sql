with source as (
    select * from {{ source('ats', 'offers') }}
)

select
    offer_id,
    application_id,
    cast(offer_extended_at as {{ dbt.type_timestamp() }})  as offer_extended_at,
    cast(offer_responded_at as {{ dbt.type_timestamp() }}) as offer_responded_at,
    offer_status,
    case when offer_status = 'Accepted' then true else false end as is_accepted,
    case when offer_status like 'Declined%'
         then trim(replace(offer_status, 'Declined -', '')) end as decline_reason,
    cast(base_salary_usd as {{ dbt.type_numeric() }})      as base_salary_usd,
    cast(sign_on_bonus_usd as {{ dbt.type_numeric() }})    as sign_on_bonus_usd,
    _loaded_at
from source
