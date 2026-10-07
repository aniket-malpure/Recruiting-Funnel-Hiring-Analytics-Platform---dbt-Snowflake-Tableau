-- Within any slice, a later funnel stage can never have more applications than the one before it.
select *
from {{ ref('mart_recruiting_funnel') }}
where previous_stage_reached is not null
  and applications_reached > previous_stage_reached
