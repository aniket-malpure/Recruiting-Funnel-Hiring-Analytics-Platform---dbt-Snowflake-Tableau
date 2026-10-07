{% docs fct_applications %}
Application-grain fact table. One row per candidate application to a requisition, with
boolean flags for every funnel stage reached and elapsed days between key stages.
Use this table for any ad hoc funnel question; the other marts are pre-aggregated views of it.
{% enddocs %}

{% docs time_to_hire %}
**Time to hire (days):** elapsed time from the candidate applying to the candidate
accepting the offer (the "Hired" stage in the ATS). Measured in hours / 24, rounded to
one decimal. Only populated for hired applications.
{% enddocs %}

{% docs time_to_fill %}
**Time to fill (days):** elapsed time from the requisition open date to the new hire's
start date. Differs from time to hire because it includes sourcing time before the
candidate applied and notice period after acceptance.
{% enddocs %}

{% docs stage_conversion_rate %}
**Stage conversion rate:** applications that reached this stage divided by applications
that reached the previous funnel stage, within the same month / department / level /
source slice. Null for the first stage (Applied).
{% enddocs %}

{% docs offer_acceptance_rate %}
**Offer acceptance rate:** offers accepted / offers extended, grouped by the month the
candidate applied. Decline reasons come from the ATS offer record.
{% enddocs %}

{% docs first_year_attrition %}
**First-year attrition:** true when a hire's termination date falls within 365 days of
their start date. Rates are only reported for the cohort of hires who started at least
365 days before the `as_of_date` variable, so recent hires don't bias the rate downward.
{% enddocs %}
