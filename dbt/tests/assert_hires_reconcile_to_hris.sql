-- Every application marked Hired in the ATS must have exactly one HRIS employee record.
with ats as (
    select count(*) as n from {{ ref('fct_applications') }} where is_hired
),
hris as (
    select count(*) as n from {{ ref('stg_hris__employees') }}
)
select ats.n as ats_hires, hris.n as hris_employees
from ats cross join hris
where ats.n <> hris.n
