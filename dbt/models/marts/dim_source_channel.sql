select distinct
    source_channel,
    source_category,
    is_paid_channel
from {{ ref('source_channel_mapping') }}
