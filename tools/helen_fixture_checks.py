"""Synthetic Helen snapshot/replay/quarantine checks in the invocation's test database."""

import hashlib
import json
import shutil
import tempfile
from pathlib import Path

import psycopg

from ingestion.helen import intake_settings, load_source


def check_helen(connection, loader_connection=None):
    worker=loader_connection if loader_connection is not None else connection
    with tempfile.TemporaryDirectory() as directory:
        root=Path(directory).resolve()
        raw=root/"data/raw/source-documents";raw.mkdir(parents=True)
        manifests=root/"experiments/source-audit";manifests.mkdir(parents=True)
        (root/"config").mkdir()
        shutil.copy2("config/helen-ingestion.json",root/"config/helen-ingestion.json")
        def save(payload,name):
            digest=hashlib.sha256(payload).hexdigest()
            path=raw/(name+".csv");path.write_bytes(payload)
            url="https://www.helen.fi/contentassets/synthetic-"+name+".csv"
            manifest=manifests/(name+".json")
            manifest.write_text(json.dumps({"sha256":digest,"bytes":len(payload),
                "raw_file":path.relative_to(root).as_posix(),"url":url,"retrieved_at_utc":"2026-10-16T12:00:00Z"}))
            foundation={"source":"HELEN","source_id":"HELEN_DISTRICT_HEATING","raw_directory":raw,
                "contract":{"snapshot_sha256":digest,"licence_and_acquisition":{"verified_current_download_url":url},
                    "semantic_contract":{"timestamp_timezone":"UTC","interval_convention":"interval_end","interval_duration_hours":1,
                        "accepted_utc_mapping":True,"accepted_interval_label_mapping":True}},
                "configuration_identity":{"synthetic":name},"configuration_sha256":digest}
            return manifest,intake_settings(root,foundation)
        payload=b"datetime_utc;dh_MWh\n30.03.2025 00:00;1,50\n30.03.2025 01:00;-2\ninvalid;NaN\n30.03.2025 02:00;3\n30.03.2025 02:00;4\n"
        manifest,settings=save(payload,"base")
        first=load_source(worker,root,settings,manifest)
        if tuple(first["counts"][k] for k in ("source_rows","valid_rows","quarantined_rows","negative_rows"))!=(5,2,3,1):
            raise AssertionError("Helen source/quarantine accounting failed")
        results=["helen_exact_source_rows_and_exhaustive_quarantine"]
        replay=load_source(worker,root,settings,manifest)
        if replay["counts"]["inserted_rows"] or replay["counts"]["replayed_rows"]!=5 or replay["run_id"]==first["run_id"]:
            raise AssertionError("Helen replay identity/count mismatch")
        results.append("helen_snapshot_replay_has_zero_insertions")
        changed,changed_settings=save(payload.replace(b"1,50",b"2,75"),"revision")
        revised=load_source(worker,root,changed_settings,changed)
        if revised["snapshot_id"]==first["snapshot_id"] or connection.execute("SELECT count(*) FROM silver.helen_source_record").fetchone()[0]!=10:
            raise AssertionError("Helen corrected content replaced prior history")
        results.append("helen_distinct_revision_preserves_prior_source_history")
        corrupt=manifests/"corrupt.json"
        value=json.loads(manifest.read_text());value["bytes"]+=1;corrupt.write_text(json.dumps(value))
        try: load_source(worker,root,settings,corrupt)
        except ValueError: pass
        else: raise AssertionError("Corrupt Helen manifest accepted")
        failed=connection.execute("""SELECT r.error_code,(SELECT count(*) FROM ops.run_input i WHERE i.run_id=r.run_id)
            FROM ops.pipeline_run r WHERE r.purpose='ingest_helen_source' AND r.status='failed'""").fetchall()
        if failed!=[("HELEN_SOURCE_INGESTION_FAILED",0)]: raise AssertionError("Helen failed input left partial links")
        results.append("helen_invalid_manifest_failure_is_atomic_and_durable")
        connection.execute("UPDATE silver.helen_source_record SET source_measurement=99 WHERE snapshot_id=%s AND source_record_index=1",(first["snapshot_id"],))
        try: load_source(worker,root,settings,manifest)
        except ValueError: pass
        else: raise AssertionError("Corrupted stored Helen value accepted on replay")
        results.append("helen_replay_detects_stored_record_corruption")
        return results
