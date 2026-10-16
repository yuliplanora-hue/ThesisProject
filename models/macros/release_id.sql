{% macro selected_weather_release() -%}
'{{ var("weather_release_id") | string | replace("'", "''") }}'::uuid
{%- endmacro %}
