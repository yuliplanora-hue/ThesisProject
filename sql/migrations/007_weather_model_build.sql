-- dbt candidate workspace only. Accepted publication/reporting objects are unchanged.
CREATE SCHEMA dbt_weather;
REVOKE ALL ON SCHEMA dbt_weather FROM PUBLIC;
