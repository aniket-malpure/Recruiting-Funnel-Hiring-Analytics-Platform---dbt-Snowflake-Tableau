-- A hire can't happen before the application was submitted.
select application_id, applied_at, hired_at
from {{ ref('int_applications_enriched') }}
where hired_at is not null
  and hired_at < applied_at
