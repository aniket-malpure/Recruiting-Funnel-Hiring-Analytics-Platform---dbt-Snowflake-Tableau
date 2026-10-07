{# Project-level generic tests. Kept local (no dbt_utils dependency) so CI runs offline. #}

{% test not_negative(model, column_name) %}
    select {{ column_name }}
    from {{ model }}
    where {{ column_name }} < 0
{% endtest %}


{% test accepted_range(model, column_name, min_value=none, max_value=none) %}
    select {{ column_name }}
    from {{ model }}
    where {{ column_name }} is not null
      and (
        1 = 0
        {% if min_value is not none %} or {{ column_name }} < {{ min_value }} {% endif %}
        {% if max_value is not none %} or {{ column_name }} > {{ max_value }} {% endif %}
      )
{% endtest %}


{% test expression_is_true(model, expression) %}
    select *
    from {{ model }}
    where not ({{ expression }})
{% endtest %}


{% test unique_combination_of_columns(model, combination_of_columns) %}
    select {{ combination_of_columns | join(', ') }}, count(*) as n
    from {{ model }}
    group by {{ combination_of_columns | join(', ') }}
    having count(*) > 1
{% endtest %}


{% test row_count_at_least(model, min_rows) %}
    select n
    from (select count(*) as n from {{ model }}) t
    where n < {{ min_rows }}
{% endtest %}
