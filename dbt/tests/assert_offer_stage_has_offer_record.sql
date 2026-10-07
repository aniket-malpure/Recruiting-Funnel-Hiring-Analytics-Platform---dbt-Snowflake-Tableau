-- Applications that reached the Offer stage should have an offer record (upstream gap check).
select application_id
from {{ ref('fct_applications') }}
where reached_offer and offer_id is null
