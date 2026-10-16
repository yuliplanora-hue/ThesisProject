"""Bounded dbt builds against an explicit accepted weather UUID; no publication."""

import hashlib
import importlib.metadata
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID, uuid4

import psycopg

from ingestion.database import begin_run, connection_settings, finish_run
from ingestion.permissions import role_name
from ingestion.provenance import code_identity, project_path


def model_identity(root, release_id):
    release_id=str(UUID(str(release_id)))
    directory=project_path(root,"models")
    files=sorted(p for p in directory.rglob('*') if p.suffix in ('.sql','.yml') and p.is_file()
                 and 'target' not in p.relative_to(directory).parts and 'logs' not in p.relative_to(directory).parts
                 and not p.name.startswith('.'))
    if not files or not (directory/'dbt_project.yml').is_file():
        raise ValueError("dbt project is absent")
    try:
        versions={name:importlib.metadata.version(name) for name in ('dbt-core','dbt-postgres')}
    except importlib.metadata.PackageNotFoundError:
        raise ValueError("Install requirements-models.txt first") from None
    files+=sorted(p for p in root.glob('requirements*.txt') if p.is_file())
    identity={'release_id':release_id,'versions':versions,
              'files_sha256':{p.relative_to(root).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in files}}
    return identity,hashlib.sha256(json.dumps(identity,sort_keys=True).encode()).hexdigest()


def execute_dbt(root, release_id, directory, *, options=None, role='energy_transformer', command='build'):
    release_id=str(UUID(str(release_id)))
    role=role_name(role)
    if command not in ('build','docs'):
        raise ValueError("Unsupported dbt operation")
    options=connection_settings() if options is None else options
    directory.mkdir(parents=True,exist_ok=False)
    environment={**os.environ,'DBT_ENV_SECRET_PASSWORD':options['password'],
        'ENERGY_DB_HOST':options['host'],'ENERGY_DB_PORT':str(options['port']),
        'ENERGY_DB_NAME':options['dbname'],'ENERGY_DB_USER':options['user'],'ENERGY_MODEL_ROLE':role,
        'DBT_SEND_ANONYMOUS_USAGE_STATS':'false','DBT_USE_COLORS':'false','DO_NOT_TRACK':'1',
        'PGOPTIONS':'-c statement_timeout=120000 -c lock_timeout=5000'}
    environment.pop('POSTGRES_PASSWORD',None)
    arguments=['build'] if command=='build' else ['docs','generate']
    arguments+=['--project-dir',str(root/'models'),'--profiles-dir',str(root/'models'),
        '--target-path',str(directory/'target'),'--log-path',str(directory/'logs'),
        '--vars',json.dumps({'weather_release_id':release_id})]
    script="from dbt.cli.main import dbtRunner; import sys; result=dbtRunner().invoke(sys.argv[1:]); sys.exit(0 if result.success else 1)"
    try:
        child=subprocess.run([sys.executable,'-c',script,*arguments],cwd=root,env=environment,
                             capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=300)
        # dbt masks DBT_ENV_SECRET_*; additionally redact before retaining console output.
        (directory/'console.txt').write_text((child.stdout+'\n'+child.stderr).replace(options['password'],'*****'),encoding='utf-8')
        path=directory/'target/run_results.json'
        result=json.loads(path.read_text(encoding='utf-8')) if path.exists() else {}
        return {'exit_code':child.returncode,'invocation_id':result.get('metadata',{}).get('invocation_id'),
                'results':[{'unique_id':r['unique_id'],'status':r['status'],'failures':r.get('failures')} for r in result.get('results',[])]}
    except subprocess.TimeoutExpired:
        return {'exit_code':2,'error_code':'DBT_CHILD_TIMEOUT','results':[]}


def build_weather_models(connection, root, release_id, *, role='energy_transformer'):
    identity,digest=model_identity(root,release_id)
    release_id=identity['release_id']
    if not connection.autocommit:
        raise ValueError("Model coordinator requires autocommit")
    source=connection.execute("SELECT content_sha256 FROM ops.release WHERE release_id=%s AND status='accepted'",(release_id,)).fetchone()
    if not source:
        raise ValueError("Models require an existing accepted weather release")
    code=code_identity(root)
    run=begin_run(connection,'build_weather_models',digest,json.dumps(code,sort_keys=True))
    directory=project_path(root,'experiments/source-audit/model-runs')/str(run)
    result=None
    try:
        # Candidate object names are shared; coordinate entire build/docs and never run two graphs together.
        with connection.transaction():
            connection.execute("SET LOCAL lock_timeout='5s'")
            connection.execute("SELECT pg_advisory_xact_lock(hashtext('weather_dbt_build'))")
            result=execute_dbt(root,release_id,directory,role=role)
            if result['exit_code']!=0:
                raise ValueError("dbt build failed; inspect its retained test results")
            documentation=execute_dbt(root,release_id,directory/'documentation',role=role,command='docs')
            if documentation['exit_code']!=0:
                raise ValueError("dbt documentation generation failed")
            counts={'models':sum(r['unique_id'].startswith('model.') for r in result['results']),
                    'tests':sum(r['unique_id'].startswith('test.') for r in result['results']),
                    'release_id':release_id,'source_content_sha256':source[0],
                    'dbt_invocation_id':result['invocation_id'],'model_identity':identity}
            connection.execute("""INSERT INTO ops.run_input (run_id,snapshot_id)
                SELECT DISTINCT %s,snapshot_id FROM ops.release_source WHERE release_id=%s
                ON CONFLICT DO NOTHING""",(run,release_id))
            finish_run(connection,run,counts)
    except (ValueError,OSError,TypeError,KeyError,psycopg.Error,KeyboardInterrupt) as exc:
        finish_run(connection,run,{'error_type':type(exc).__name__,
                   'dbt_exit_code':result.get('exit_code') if result else None},'WEATHER_MODEL_BUILD_FAILED')
        raise
    report={'run_id':str(run),'status':'succeeded','release_id':release_id,'source_content_sha256':source[0],
            'configuration_sha256':digest,'model_identity':identity,'code_identity':code,'dbt':result,'counts':counts,
            'completed_at_utc':datetime.now(timezone.utc).isoformat(),
            'scope':'dbt_weather candidate models only; no Gold/accepted pointer/reporting change'}
    (directory/'summary.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    return report
