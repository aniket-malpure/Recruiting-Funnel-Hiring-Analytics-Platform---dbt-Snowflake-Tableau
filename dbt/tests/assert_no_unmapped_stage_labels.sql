-- Lists every raw ATS stage label with no entry in seeds/stage_mapping.csv.
-- When this fails, add the new label to the seed (or raise it with the ATS admin
-- if the stage was created by mistake) before the funnel drops those candidates.
select
    stage_raw,
    count(*) as events
from {{ ref('stg_ats__stage_events') }}
where canonical_stage is null
group by stage_raw
