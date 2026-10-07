{# Day difference between two timestamps, as a decimal (hours / 24), portable across Snowflake and DuckDB. #}
{% macro days_between(start_ts, end_ts) -%}
    round({{ dbt.datediff(start_ts, end_ts, 'hour') }} / 24.0, 1)
{%- endmacro %}
