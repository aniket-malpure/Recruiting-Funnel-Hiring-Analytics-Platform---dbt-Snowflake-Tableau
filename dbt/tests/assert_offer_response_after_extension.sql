select offer_id, offer_extended_at, offer_responded_at
from {{ ref('stg_ats__offers') }}
where offer_responded_at < offer_extended_at
