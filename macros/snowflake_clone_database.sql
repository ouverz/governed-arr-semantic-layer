{% macro clone_snowflake_database(source_database, target_database) %}
    {% set sql %}
        create or replace database {{ target_database }} clone {{ source_database }}
    {% endset %}

    {% do run_query(sql) %}
{% endmacro %}

{% macro drop_snowflake_database(database_name) %}
    {% set sql %}
        drop database if exists {{ database_name }}
    {% endset %}

    {% do run_query(sql) %}
{% endmacro %}
