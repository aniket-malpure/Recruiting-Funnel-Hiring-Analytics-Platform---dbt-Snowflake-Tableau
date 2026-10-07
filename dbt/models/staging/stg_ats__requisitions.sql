with source as (
    select * from {{ source('ats', 'requisitions') }}
)

select
    req_id,
    trim(job_title)                         as job_title,
    trim(department)                        as department,
    upper(trim(job_level))                  as job_level,
    trim(location)                          as location,
    employment_type,
    hiring_manager_id,
    recruiter_id,
    cast(headcount as integer)              as headcount,
    cast(opened_date as date)               as opened_date,
    cast(closed_date as date)               as closed_date,
    cast(target_days_to_fill as integer)    as target_days_to_fill,
    req_status,
    _loaded_at
from source
