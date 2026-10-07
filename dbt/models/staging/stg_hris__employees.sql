with source as (
    select * from {{ source('hris', 'employees') }}
)

select
    employee_id,
    candidate_id,
    application_id,
    req_id,
    department,
    job_title,
    upper(job_level)                    as job_level,
    location,
    cast(hire_date as date)             as hire_date,
    cast(termination_date as date)      as termination_date,
    termination_reason,
    case when termination_reason like 'Voluntary%' then 'Voluntary'
         when termination_reason like 'Involuntary%' then 'Involuntary' end as termination_type,
    employment_status,
    _loaded_at
from source
