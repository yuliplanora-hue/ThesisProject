"""dbt graph checks with manufactured reporting inputs in one disposable database."""

import json
import secrets
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

import psycopg
from psycopg import sql
from psycopg.types.json import Jsonb

from ingestion.database import apply_migrations, connect, connection_settings
from ingestion.modeling import execute_dbt, model_identity
from ingestion.permissions import provision_model_role
from tools.time_model_checks import verify_time_models


def check_models():
    root=Path.cwd().resolve()
    model_identity(root,uuid4())  # Fail early if the optional modelling tools are absent.
    check_id=uuid4().hex
    database='energy_models_test_'+check_id
    role='energy_model_test_'+check_id
    login='energy_model_login_'+check_id
    directory=root/'experiments/source-audit/model-checks'/check_id
    directory.mkdir(parents=True,exist_ok=False)
    created_database=False
    created_roles=[]
    checks=[]
    attempts=[]
    with connect() as admin:
        try:
            admin.execute(sql.SQL('CREATE DATABASE {}').format(sql.Identifier(database)))
            created_database=True
            with connect(database) as connection:
                assert connection.info.dbname==database and database.startswith('energy_models_test_')
                apply_migrations(connection)
                # Manufactured, intentionally mutable copies of the reporting shape.
                # These replacements are confined to this newly created test database.
                for table in ('weather_release','weather_point'):
                    connection.execute(sql.SQL('CREATE TABLE reporting.{} AS TABLE reporting.{} WITH NO DATA').format(sql.Identifier(table+'_fixture'),sql.Identifier(table)))
                    connection.execute(sql.SQL('DROP VIEW reporting.{}').format(sql.Identifier(table)))
                    connection.execute(sql.SQL('ALTER TABLE reporting.{} RENAME TO {}').format(sql.Identifier(table+'_fixture'),sql.Identifier(table)))
                result=provision_model_role(connection,role)
                if result['created']:created_roles.append(role)
                password=secrets.token_hex(24)
                connection.execute(sql.SQL('CREATE ROLE {} LOGIN INHERIT NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS PASSWORD {}').format(sql.Identifier(login),sql.Literal(password)))
                created_roles.append(login)
                connection.execute(sql.SQL('GRANT {} TO {}').format(sql.Identifier(role),sql.Identifier(login)))
                connection.execute(sql.SQL('GRANT CONNECT ON DATABASE {} TO {}').format(sql.Identifier(database),sql.Identifier(login)))
                options={**connection_settings(),'dbname':database,'user':login,'password':password}

                def seed(start,end,missing=False):
                    release=uuid4();snapshot=uuid4();count=int((end-start).total_seconds()/600)
                    connection.execute('''INSERT INTO reporting.weather_release
                        (release_id,stream_id,station_id,parameter_id,start_utc,end_utc_exclusive,content_sha256,plan_sha256,counts,completed_at_utc,is_current)
                        VALUES (%s,'synthetic-dbt','100971','t2m',%s,%s,%s,%s,%s,now(),true)''',
                        (release,start,end,'a'*64,'b'*64,Jsonb({'synthetic':True})))
                    values=[]
                    for index in range(count):
                        t=start+timedelta(minutes=index*10)
                        value=Decimal((index%6)*2);quality='observed';source=snapshot;point=index+1
                        if missing and index==6:
                            value=None;quality='source_nan'
                        if missing and index==12:
                            value=None;quality='source_absent';source=point=None
                        values.append(('synthetic-dbt',release,'100971','t2m',t,value,quality,source,point))
                    with connection.cursor() as cursor:
                        cursor.executemany('INSERT INTO reporting.weather_point VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)',values)
                    return release

                spring_start=datetime(2025,3,29,22,tzinfo=timezone.utc)
                spring=seed(spring_start,spring_start+timedelta(hours=23),missing=True)
                fall_start=datetime(2025,10,25,21,tzinfo=timezone.utc)
                fall=seed(fall_start,fall_start+timedelta(hours=25))
                leap_start=datetime(2024,2,28,22,tzinfo=timezone.utc)
                leap=seed(leap_start,leap_start+timedelta(hours=24))
                partial_start=datetime(2025,10,26,1,tzinfo=timezone.utc)
                partial=seed(partial_start,partial_start+timedelta(hours=2))
                iso_start=datetime(2024,12,29,22,tzinfo=timezone.utc)
                iso=seed(iso_start,iso_start+timedelta(hours=24))

                def build(release,name,expected_failure=False):
                    result=execute_dbt(root,str(release),directory/name,options=options,role=role)
                    attempts.append({'name':name,**result})
                    failures=[r for r in result['results'] if r['status'] in ('fail','error')]
                    if expected_failure:
                        if result['exit_code']==0 or not failures:
                            raise AssertionError('Deliberate model corruption did not produce failed tests')
                    elif result['exit_code']!=0:
                        raise AssertionError('Synthetic dbt build failed; inspect its retained private console/results')
                    return result

                spring_build=build(spring,'spring')
                rows=connection.execute('''SELECT hour_start_utc,temperature_c,finite_sample_count,source_nan_count,source_absent_count,is_complete
                    FROM dbt_weather.fct_weather_hour ORDER BY hour_start_utc''').fetchall()
                if len(rows)!=23 or rows[0][1]!=Decimal(5) or rows[1][1] is not None or rows[2][1] is not None:
                    raise AssertionError('Spring manual hourly mean/NULL/count controls differ')
                if rows[1][2:]!=(5,1,0,False) or rows[2][2:]!=(5,0,1,False):
                    raise AssertionError('Source NaN and absence were conflated')
                if connection.execute('SELECT count(*) FROM dbt_weather.weather_hour_lineage').fetchone()[0]!=138:
                    raise AssertionError('Source-point lineage accounting differs')
                checks.extend(['dbt_manual_mean_and_distinct_nan_absent_states','dbt_spring_23_hour_spine_and_complete_lineage'])
                spring_time=verify_time_models(connection,spring_start,spring_start+timedelta(hours=23))
                if spring_time['complete_weather_days']!=0:
                    raise AssertionError('Incomplete spring day received a daily temperature')
                checks.append('helsinki_spring_labels_and_incomplete_day_null')
                build(fall,'fall')
                result=connection.execute('SELECT count(*),min(temperature_c),max(temperature_c),count(*) FILTER(WHERE is_complete) FROM dbt_weather.fct_weather_hour').fetchone()
                if result!=(25,Decimal(5),Decimal(5),25):
                    raise AssertionError('Fall independent 25-hour/mean controls differ')
                if connection.execute('SELECT count(*) FROM dbt_weather.fct_weather_hour WHERE release_id<>%s',(fall,)).fetchone()[0]:
                    raise AssertionError('dbt mixed accepted revisions')
                checks.extend(['dbt_fall_25_hour_control','dbt_explicit_uuid_prevents_revision_mixing'])
                fall_time=verify_time_models(connection,fall_start,fall_start+timedelta(hours=25))
                if fall_time['complete_weather_days']!=1 or fall_time['repeated_second_hours']!=1:
                    raise AssertionError('Fall repeated hour or complete daily mean differs')
                checks.append('helsinki_fall_offset_fold_and_daily_mean')
                # Duplicate source key: generic unique test must fail visibly.
                connection.execute('INSERT INTO reporting.weather_point SELECT * FROM reporting.weather_point WHERE release_id=%s AND observed_at_utc=%s',(fall,fall_start))
                red=build(fall,'duplicate-key',expected_failure=True)
                if not any('unique_stg_weather_point' in r['unique_id'] and r['status']=='fail' for r in red['results']):
                    raise AssertionError('Duplicate failed for an unexpected reason')
                connection.execute('''DELETE FROM reporting.weather_point WHERE ctid=(SELECT ctid
                    FROM reporting.weather_point WHERE release_id=%s AND observed_at_utc=%s ORDER BY ctid DESC LIMIT 1)''',(fall,fall_start))
                checks.append('dbt_deliberate_duplicate_fails_key_test')
                # Missing published row is processing loss, not an invented source absence.
                connection.execute('DELETE FROM reporting.weather_point WHERE release_id=%s AND observed_at_utc=%s',(fall,fall_start))
                red=build(fall,'missing-published-slot',expected_failure=True)
                if not any('hour_accounting' in r['unique_id'] and r['status']=='fail' for r in red['results']):
                    raise AssertionError('Missing published slot was silently hidden')
                connection.execute("INSERT INTO reporting.weather_point VALUES ('synthetic-dbt',%s,'100971','t2m',%s,0,'observed',%s,1)",(fall,fall_start,uuid4()))
                checks.append('dbt_missing_published_slot_fails_processing_loss_test')
                build(fall,'recovered')
                checks.append('dbt_recovery_after_fixture_repair_is_green')
                build(leap,'leap-day')
                verify_time_models(connection,leap_start,leap_start+timedelta(hours=24))
                checks.append('helsinki_leap_day_calendar_and_one_to_one_report')
                build(iso,'iso-year-boundary')
                verify_time_models(connection,iso_start,iso_start+timedelta(hours=24))
                checks.append('helsinki_iso_week_year_boundary')
                build(partial,'partial-fall-day')
                partial_time=verify_time_models(connection,partial_start,partial_start+timedelta(hours=2))
                if partial_time['partial_days']!=1 or partial_time['complete_weather_days']!=0 or partial_time['repeated_second_hours']!=1:
                    raise AssertionError('Partial day was accepted or first retained fold was mislabelled')
                checks.append('partial_release_day_excluded_even_with_all_hours_finite')
                # Civil labels and eligibility must not depend on a client's/session's TimeZone.
                baseline=connection.execute('SELECT * FROM dbt_weather.weather_report_day ORDER BY local_date').fetchall()
                for zone in ('America/New_York','Asia/Kathmandu'):
                    connection.execute('SELECT set_config(\'TimeZone\',%s,false)',(zone,))
                    verify_time_models(connection,partial_start,partial_start+timedelta(hours=2))
                    if connection.execute('SELECT * FROM dbt_weather.weather_report_day ORDER BY local_date').fetchall()!=baseline:
                        raise AssertionError('Session timezone changed report values')
                connection.execute("SET TimeZone='UTC'")
                checks.append('calendar_and_reporting_independent_of_session_timezone')
                docs=execute_dbt(root,str(fall),directory/'documentation',options=options,role=role,command='docs')
                if docs['exit_code'] or not (directory/'documentation/target/catalog.json').is_file():
                    raise AssertionError('dbt model documentation/catalog generation failed')
                checks.append('dbt_manifest_and_documentation_catalog_generated')
                if provision_model_role(connection,role)['created']:
                    raise AssertionError('Transformer reprovisioning failed after it owned models')
                with psycopg.connect(**options,autocommit=True) as restricted:
                    restricted.execute(sql.SQL('SET ROLE {}').format(sql.Identifier(role)))
                    for statement in ('SELECT * FROM ops.pipeline_run LIMIT 0',
                                      'UPDATE reporting.weather_point SET temperature_c=0 WHERE false',
                                      'CREATE TABLE public.forbidden_model(id integer)',
                                      'CREATE TEMP TABLE forbidden_model(id integer)'):
                        try: restricted.execute(statement)
                        except psycopg.errors.InsufficientPrivilege: pass
                        else: raise AssertionError('Transformer escaped its candidate/schema boundary')
                checks.append('transformer_real_login_ddl_read_scope_and_reprovision')
                report={'status':'pass','test_database':database,'checks':checks,'attempts':attempts,
                        'model_count':sum(r['unique_id'].startswith('model.') for r in spring_build['results']),
                        'test_count':sum(r['unique_id'].startswith('test.') for r in spring_build['results']),
                        'scope':'Synthetic dbt candidate graph; not final E1-E7 or Gold acceptance'}
                (directory/'summary.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
                return report
        finally:
            if created_database:
                # First remove only this invocation's UUID database, then its exact roles.
                admin.execute(sql.SQL('DROP DATABASE {}').format(sql.Identifier(database)))
            for name in reversed(created_roles):
                admin.execute(sql.SQL('DROP ROLE {}').format(sql.Identifier(name)))
