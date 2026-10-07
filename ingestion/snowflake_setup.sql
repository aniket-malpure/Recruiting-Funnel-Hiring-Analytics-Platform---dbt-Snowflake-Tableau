-- One-time Snowflake setup for the Recruiting Funnel & Hiring Analytics Platform.
-- Run as ACCOUNTADMIN (or SYSADMIN + SECURITYADMIN) in a Snowsight worksheet.

use role sysadmin;

create warehouse if not exists people_analytics_wh
    warehouse_size = 'XSMALL'
    auto_suspend = 60
    auto_resume = true
    initially_suspended = true;

create database if not exists people_analytics;
create schema if not exists people_analytics.raw;        -- landing zone (load_raw.py)
create schema if not exists people_analytics.analytics;  -- dbt builds here (staging / intermediate / marts)

use role securityadmin;

create role if not exists transformer;   -- dbt + loader
create role if not exists reporter;      -- Tableau service account

grant usage on warehouse people_analytics_wh to role transformer;
grant usage on warehouse people_analytics_wh to role reporter;

grant usage, create schema on database people_analytics to role transformer;
grant all on schema people_analytics.raw to role transformer;
grant all on schema people_analytics.analytics to role transformer;

grant usage on database people_analytics to role reporter;
grant usage on all schemas in database people_analytics to role reporter;
grant usage on future schemas in database people_analytics to role reporter;
grant select on future tables in database people_analytics to role reporter;
grant select on future views in database people_analytics to role reporter;

-- Replace with your own users
-- create user dbt_svc password = '...' default_role = transformer default_warehouse = people_analytics_wh;
-- create user tableau_svc password = '...' default_role = reporter default_warehouse = people_analytics_wh;
-- grant role transformer to user dbt_svc;
-- grant role reporter to user tableau_svc;
grant role transformer to role sysadmin;
grant role reporter to role sysadmin;

-- Candidate PII masking: recruiters & analysts see hashed emails, People Ops admins see raw.
use role sysadmin;
create masking policy if not exists people_analytics.raw.mask_email as (val string) returns string ->
    case when current_role() in ('PEOPLE_OPS_ADMIN', 'SYSADMIN') then val
         else sha2(lower(val)) end;
-- After the first load:
-- alter table people_analytics.raw.candidates modify column email set masking policy people_analytics.raw.mask_email;
