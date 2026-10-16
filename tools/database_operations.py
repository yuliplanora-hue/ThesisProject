"""Snapshot backup, isolated restore verification and a read-only query/index comparison."""

import argparse
import hashlib
import json
import os
import platform
import re
import secrets
import statistics
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import UUID, uuid4

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import psycopg
from psycopg import sql

from ingestion.database import apply_migrations, connection_settings
from ingestion.permissions import provision_model_role, provision_roles
from tools.time_model_checks import verify_time_models

SCHEMAS=('ops','silver','publication','reporting','dbt_weather')


def digest_file(path):
    result=hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda:stream.read(1024*1024),b''):result.update(block)
    return result.hexdigest()


def checked_target(name,source):
    if name==source or not re.fullmatch(r'energy_restore_test_[0-9a-f]{32}',name):
        raise ValueError('Restore target must be this invocation\'s isolated UUID database')
    return name


def fingerprint(connection):
    """Stable full-row multiset hashes, including all audit tables and candidate views."""
    connection.execute("SET LOCAL TimeZone='UTC'")
    connection.execute("SET LOCAL DateStyle='ISO, YMD'")
    connection.execute('SET LOCAL extra_float_digits=3')
    relations=connection.execute('''SELECT n.nspname,c.relname,c.relkind
        FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
        WHERE n.nspname=ANY(%s) AND c.relkind IN ('r','v','m','p') ORDER BY 1,2''',(list(SCHEMAS),)).fetchall()
    result={}
    for schema,name,kind in relations:
        columns=connection.execute('''SELECT a.attname,format_type(a.atttypid,a.atttypmod),a.attnotnull
            FROM pg_attribute a WHERE a.attrelid=%s::regclass AND a.attnum>0 AND NOT a.attisdropped
            ORDER BY a.attnum''',(f'{schema}.{name}',)).fetchall()
        constraints=connection.execute('''SELECT conname,pg_get_constraintdef(oid)
            FROM pg_constraint WHERE conrelid=%s::regclass ORDER BY conname''',(f'{schema}.{name}',)).fetchall()
        indexes=connection.execute('''SELECT indexname,indexdef FROM pg_indexes
            WHERE schemaname=%s AND tablename=%s ORDER BY indexname''',(schema,name)).fetchall()
        definition=connection.execute('SELECT pg_get_viewdef(%s::regclass,true)',(f'{schema}.{name}',)).fetchone()[0] if kind in ('v','m') else None
        rows=0;digest=hashlib.sha256()
        statement=sql.SQL('COPY (SELECT payload FROM (SELECT row_to_json(t)::text AS payload FROM {} t) q ORDER BY payload COLLATE "C") TO STDOUT').format(sql.Identifier(schema,name))
        with connection.cursor().copy(statement) as stream:
            for chunk in stream:
                block=bytes(chunk);digest.update(block);rows+=block.count(b'\n')
        result[f'{schema}.{name}']={'kind':kind,'columns':columns,'constraints':constraints,
                                  'indexes':indexes,'view_definition':definition,'rows':rows,'rows_sha256':digest.hexdigest()}
    if not result:raise ValueError('No project relations to back up')
    return result


def client_command(mode,program,settings):
    if mode=='docker':
        return ['docker','compose','exec','-T','postgres',program,'--username',settings['user']]
    return [program,'--host',settings['host'],'--port',str(settings['port']),'--username',settings['user']]


def run_client(command,settings,*,stdin=None,stdout=None):
    environment={**os.environ,'PGPASSWORD':settings['password'],'PGCONNECT_TIMEOUT':'5'}
    result=subprocess.run(command,stdin=stdin,stdout=stdout if stdout is not None else subprocess.PIPE,
                          stderr=subprocess.PIPE,env=environment,timeout=300)
    if result.returncode:
        # Do not print raw connection diagnostics or database contents.
        raise ValueError('PostgreSQL client failed: '+Path(command[0]).name)
    if result.stderr:
        raise ValueError('PostgreSQL client emitted diagnostics; refusing an unreviewed backup/restore')
    return result.stdout


def plan_summary(plan):
    return {'planning_ms':plan['Planning Time'],'execution_ms':plan['Execution Time'],
            'root_node':plan['Plan']['Node Type'],
            'shared_hit_blocks':plan['Plan'].get('Shared Hit Blocks',0),
            'shared_read_blocks':plan['Plan'].get('Shared Read Blocks',0)}


def benchmark(connection,root,release_id,directory):
    """One warm-up + five measured reads per variant; data remain frozen throughout."""
    info=connection.execute('SELECT station_id,parameter_id,start_utc,end_utc_exclusive FROM ops.release WHERE release_id=%s',(release_id,)).fetchone()
    day=connection.execute("SELECT date_trunc('day',min(hour_start_utc)) FROM dbt_weather.int_weather_hour WHERE finite_sample_count<6").fetchone()[0]
    start=max(info[2],day or info[2]);end=min(start+timedelta(hours=24),info[3])
    parameters={'release_id':release_id,'station_id':info[0],'parameter_id':info[1],'start':start,'end':end}
    query=(root/'sql/operations/weather_hour_lookup.sql').read_text(encoding='utf-8')
    connection.execute('ANALYZE dbt_weather.int_weather_hour')
    results={};reference=None
    for variant in ('baseline','indexed'):
        if variant=='indexed':
            before=time.perf_counter()
            connection.execute('CREATE INDEX wp34_weather_hour_lookup ON dbt_weather.int_weather_hour (release_id,station_id,parameter_id,hour_start_utc)')
            results['index_build_ms']=(time.perf_counter()-before)*1000
            results['index_bytes']=connection.execute("SELECT pg_relation_size('dbt_weather.wp34_weather_hour_lookup')").fetchone()[0]
            connection.execute('ANALYZE dbt_weather.int_weather_hour')
        warm=connection.execute(query,parameters).fetchall()
        if reference is None:reference=warm
        if not warm or warm!=reference:raise AssertionError('Warm-up result differs')
        measured=[];plans=[]
        for repetition in range(5):
            began=time.perf_counter();rows=connection.execute(query,parameters).fetchall()
            elapsed=(time.perf_counter()-began)*1000
            if rows!=reference:raise AssertionError('Optimisation changed query values/keys')
            plan=connection.execute('EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) '+query,parameters).fetchone()[0][0]
            if plan['Plan']['Actual Rows']!=len(reference):raise AssertionError('Explain row count differs')
            measured.append({'repetition':repetition+1,'client_ms':elapsed,**plan_summary(plan)})
            plans.append(plan)
        (directory/f'{variant}-plans.json').write_text(json.dumps(plans,indent=2)+'\n',encoding='utf-8')
        results[variant]={'repetitions':measured,'client_median_ms':statistics.median(r['client_ms'] for r in measured),
                          'client_range_ms':[min(r['client_ms'] for r in measured),max(r['client_ms'] for r in measured)],
                          'server_median_ms':statistics.median(r['execution_ms'] for r in measured),
                          'server_range_ms':[min(r['execution_ms'] for r in measured),max(r['execution_ms'] for r in measured)]}
    results.update({'parameters':{k:str(v) for k,v in parameters.items()},'rows':len(reference),
        'null_temperature_rows':sum(r[1] is None for r in reference),'result_sha256':hashlib.sha256(json.dumps(reference,default=str).encode()).hexdigest(),
        'query_sha256':hashlib.sha256(query.encode()).hexdigest(),'identical_results_all_repetitions':True,
        'server_median_ratio':results['baseline']['server_median_ms']/results['indexed']['server_median_ms'],
        'policy':'One unmeasured warm-up per variant; five measured SELECT/fetches and five separate EXPLAIN ANALYZE probes. Warm shared caches, no cache flush, baseline then indexed. Read-only queries share one frozen restored snapshot; only index DDL differs. Timings exclude dump/restore, index creation, ANALYZE, result validation and EXPLAIN probes. Server timings are EXPLAIN instrumented execution; client timings include local roundtrip/fetch. Development lookup microbenchmark, not final E4 full/incremental load experiments.'})
    return results


def rehearse(root,release_id,mode='docker'):
    release_id=str(UUID(str(release_id)))
    if os.environ.get('ENERGY_DB_ROLE'):raise ValueError('Use the setup connection with ENERGY_DB_ROLE unset')
    settings=connection_settings();identifier=uuid4().hex
    database=checked_target('energy_restore_test_'+identifier,settings['dbname'])
    roles=['energy_restore_loader_'+identifier,'energy_restore_reporter_'+identifier,
           'energy_restore_model_'+identifier,'energy_restore_login_'+identifier]
    directory=root/'experiments/source-audit/database-operations'/identifier
    backup=root/'backup'/('database-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'-'+identifier)
    directory.mkdir(parents=True,exist_ok=False);backup.mkdir(parents=True,exist_ok=False)
    archive=backup/'database.dump';created=False;created_roles=[]
    report={'operation_id':identifier,'status':'running','source_database':settings['dbname'],'restore_database':database,
            'client_mode':mode,'started_at_utc':datetime.now(timezone.utc).isoformat(),'release_id':release_id,
            'backup_path':archive.relative_to(root).as_posix(),'scope':'Local candidate development rehearsal, not final E4 or disaster recovery; no source database mutation',
            'code_sha256':{name:digest_file(root/name) for name in ('tools/database_operations.py','tools/time_model_checks.py','ingestion/permissions.py','sql/operations/weather_hour_lookup.sql')},
            'environment':{'python':platform.python_version(),'client_platform':platform.platform(),'client_machine':platform.machine(),'client_cpu_count':os.cpu_count()}}
    for name in report['code_sha256']:
        target=directory/'code'/name;target.parent.mkdir(parents=True,exist_ok=True)
        target.write_bytes((root/name).read_bytes())
    try:
        with psycopg.connect(**settings,autocommit=True) as source:
            source.execute("SET statement_timeout='120s'")
            report['server_version']=source.execute('SHOW server_version').fetchone()[0]
            server=source.execute('SELECT system_identifier::text FROM pg_control_system()').fetchone()[0]
            check=client_command(mode,'psql',settings)+['--dbname',settings['dbname'],'-X','-At','-c','SELECT system_identifier::text FROM pg_control_system()']
            if run_client(check,settings).decode().strip()!=server:raise ValueError('Client tools and Python connection point to different servers')
            for program in ('pg_dump','pg_restore'):
                command=(['docker','compose','exec','-T','postgres',program] if mode=='docker' else [program])+['--version']
                report[program+'_version']=run_client(command,settings).decode().strip()
            with source.transaction():
                source.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY')
                snapshot=source.execute('SELECT pg_export_snapshot()').fetchone()[0]
                accepted=source.execute("SELECT start_utc,end_utc_exclusive FROM ops.release WHERE release_id=%s AND status='accepted'",(release_id,)).fetchone()
                if not accepted:raise ValueError('Pin an existing accepted weather UUID')
                if source.execute('SELECT release_id FROM dbt_weather.stg_weather_release').fetchall()!=[(UUID(release_id),)]:
                    raise ValueError('Build the candidate graph for this exact release before rehearsal')
                if source.execute("SELECT count(*) FROM ops.pipeline_run WHERE status='running'").fetchone()[0]:raise ValueError('Wait for in-progress pipeline work before rehearsal')
                report['exported_snapshot']=snapshot
                dump=client_command(mode,'pg_dump',settings)+['--dbname',settings['dbname'],'--format=custom','--snapshot',snapshot,'--no-acl']
                report['dump_command']=dump
                began=time.perf_counter()
                with archive.open('xb') as out:run_client(dump,settings,stdout=out)
                report['dump_seconds']=time.perf_counter()-began
                report['source_fingerprint']=fingerprint(source)
                report['backup_sha256']=digest_file(archive);report['backup_bytes']=archive.stat().st_size
            source.execute(sql.SQL('CREATE DATABASE {} TEMPLATE template0').format(sql.Identifier(database)));created=True
            source.execute(sql.SQL('REVOKE ALL ON DATABASE {} FROM PUBLIC').format(sql.Identifier(database)))
            restore=client_command(mode,'pg_restore',settings)+['--dbname',database,'--no-owner','--no-acl','--exit-on-error','--single-transaction']
            report['restore_command']=restore
            if digest_file(archive)!=report['backup_sha256']:raise ValueError('Archive changed before restore')
            began=time.perf_counter()
            with archive.open('rb') as stream:run_client(restore,settings,stdin=stream)
            report['restore_seconds']=time.perf_counter()-began
            with psycopg.connect(**{**settings,'dbname':database},autocommit=True) as restored:
                restored.execute("SET statement_timeout='120s'")
                with restored.transaction():
                    if fingerprint(restored)!=report['source_fingerprint']:raise AssertionError('Restored schema/rows/audit/views differ')
                report['restore_fingerprint_matches']=True
                if apply_migrations(restored):raise AssertionError('Restored migration ledger did not replay unchanged')
                # Portable dumps omit cluster users, original owners and ACL bindings.
                # Bind fresh test groups to this destination only, never repurpose source roles.
                created_roles.extend(provision_roles(restored,roles[0],roles[1])['created_roles'])
                if provision_model_role(restored,roles[2])['created']:created_roles.append(roles[2])
                # --no-owner initially gives the setup account every object. Hand
                # candidate ownership to the destination's transformer, so future
                # replacements do not depend on the source cluster's role names.
                for relation,identity in report['source_fingerprint'].items():
                    schema,name=relation.split('.')
                    if schema=='dbt_weather':
                        kind='VIEW' if identity['kind']=='v' else 'TABLE'
                        restored.execute(sql.SQL('ALTER {} {} OWNER TO {}').format(sql.SQL(kind),sql.Identifier(schema,name),sql.Identifier(roles[2])))
                if provision_model_role(restored,roles[2])['created']:
                    raise AssertionError('Restored transformer failed ownership reprovisioning')
                restored.execute(sql.SQL('SET ROLE {}').format(sql.Identifier(roles[2])))
                try:
                    model_rows=restored.execute('SELECT count(*) FROM dbt_weather.weather_report_day').fetchone()[0]
                    if model_rows!=report['source_fingerprint']['dbt_weather.weather_report_day']['rows']:
                        raise AssertionError('Restored candidate owner cannot read its graph')
                finally:restored.execute('RESET ROLE')
                report['candidate_ownership_rebound']=True
                password=secrets.token_hex(24)
                restored.execute(sql.SQL('CREATE ROLE {} LOGIN INHERIT NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS PASSWORD {}').format(sql.Identifier(roles[3]),sql.Literal(password)))
                created_roles.append(roles[3])
                restored.execute(sql.SQL('GRANT {} TO {}').format(sql.Identifier(roles[1]),sql.Identifier(roles[3])))
                restored.execute(sql.SQL('GRANT CONNECT ON DATABASE {} TO {}').format(sql.Identifier(database),sql.Identifier(roles[3])))
                with psycopg.connect(**{**settings,'dbname':database,'user':roles[3],'password':password},autocommit=True) as reporter:
                    reporter.execute(sql.SQL('SET ROLE {}').format(sql.Identifier(roles[1])))
                    if reporter.execute('SELECT count(*) FROM reporting.weather_point').fetchone()[0]!=report['source_fingerprint']['reporting.weather_point']['rows']:
                        raise AssertionError('Restored reporter reads differ')
                    if any(reporter.execute('SELECT has_table_privilege(current_user,\'reporting.weather_point\',%s)',(privilege,)).fetchone()[0] for privilege in ('INSERT','UPDATE','DELETE')):
                        raise AssertionError('Restored reporter has a reporting write grant')
                    denied=[]
                    for statement in ('UPDATE reporting.weather_point SET temperature_c=0 WHERE false','UPDATE publication.weather_point SET temperature_c=0 WHERE false','SELECT * FROM ops.pipeline_run LIMIT 0','SELECT * FROM silver.helen_source_record LIMIT 0','SELECT * FROM dbt_weather.weather_report_day LIMIT 0','CREATE TEMP TABLE forbidden_restore(id integer)'):
                        try:reporter.execute(statement)
                        except psycopg.errors.InsufficientPrivilege as exc:denied.append({'statement':statement,'sqlstate':exc.sqlstate})
                        except psycopg.errors.ObjectNotInPrerequisiteState as exc:
                            if not statement.startswith('UPDATE reporting.weather_point '):raise
                            denied.append({'statement':statement,'sqlstate':exc.sqlstate,'reason':'Join view is not updatable; write ACLs also explicitly checked absent'})
                        else:raise AssertionError('Restored reporter escaped its scope')
                report['reporter_denied_statements']=denied
                with restored.transaction():
                    restored.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ')
                    restored.execute("SET LOCAL TimeZone='UTC'")
                    report['restored_calendar']=verify_time_models(restored,*accepted)
                    report['benchmark']=benchmark(restored,root,release_id,directory)
                report['migration_replay_unchanged']=True
                with source.transaction():
                    source.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY')
                    if fingerprint(source)!=report['source_fingerprint']:
                        raise AssertionError('Source changed during rehearsal; snapshot is valid but live equality is unverified')
                report['source_unchanged_after_rehearsal']=True
                report['status']='pass'
    except BaseException as exc:
        report.update(status='failed',error_type=type(exc).__name__,error_sqlstate=getattr(exc,'sqlstate',None))
        raise
    finally:
        try:
            with psycopg.connect(**settings,autocommit=True) as cleanup:
                if created:
                    checked_target(database,settings['dbname'])
                    cleanup.execute(sql.SQL('DROP DATABASE {}').format(sql.Identifier(database)))
                for name in reversed(created_roles):cleanup.execute(sql.SQL('DROP ROLE {}').format(sql.Identifier(name)))
                report['isolated_resources_removed']=True
        except BaseException:
            report['isolated_resources_removed']=False;report['status']='failed'
            raise
        finally:
            report['completed_at_utc']=datetime.now(timezone.utc).isoformat()
            for path in (directory/'summary.json',backup/'manifest.json'):
                path.write_text(json.dumps(report,default=str,indent=2)+'\n',encoding='utf-8')
    return report


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--release-id',required=True)
    parser.add_argument('--client-mode',choices=('docker','local'),default='docker')
    args=parser.parse_args()
    try:result=rehearse(Path.cwd().resolve(),args.release_id,args.client_mode)
    except (ValueError,AssertionError,OSError,psycopg.Error,subprocess.SubprocessError) as exc:
        print('Database rehearsal failed ('+type(exc).__name__+'); inspect its private manifest.',file=sys.stderr)
        return 2
    print(json.dumps({k:result[k] for k in ('operation_id','status','backup_bytes','restore_fingerprint_matches','isolated_resources_removed')},indent=2))
    print('Query server median ratio:',round(result['benchmark']['server_median_ratio'],2))
    return 0


if __name__=='__main__':raise SystemExit(main())
