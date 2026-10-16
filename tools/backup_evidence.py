"""Copy source evidence to a new snapshot and verify hashes and representative restores."""

import argparse
import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4


def digest(path: Path) -> str:
    checksum = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            checksum.update(block)
    return checksum.hexdigest()


def backup_evidence(destination: Path) -> dict:
    root = Path(__file__).resolve().parents[1]
    source_roots = [root / name for name in ("data/raw", "experiments/source-audit", "config", "tests/fixtures/wp1")]
    destination = destination.resolve()
    for source in source_roots:
        if destination.is_relative_to(source.resolve()):
            raise ValueError("Backup destination must be outside the source directories")
    if destination.is_relative_to(root) and not destination.is_relative_to((root / "backup").resolve()):
        raise ValueError("In-project evidence backups must remain in the ignored backup directory")
    files = []
    for source in source_roots:
        if not source.is_dir():
            raise ValueError("Required evidence directory is missing")
        for path in sorted(source.rglob("*")):
            if path.is_symlink() or path.is_junction():
                raise ValueError("Evidence links require explicit handling before backup")
            if path.is_file():
                if not path.resolve().is_relative_to(source.resolve()):
                    raise ValueError("Evidence path leaves its source directory")
                files.append(path)
    snapshot = destination / ("evidence-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid4().hex)
    snapshot.mkdir(parents=True, exist_ok=False)
    report = {"created_at_utc": datetime.now(timezone.utc).isoformat(), "status": "in_progress",
              "snapshot_directory": str(snapshot), "scope": "raw files, acquisition/audit evidence, nonsecret contracts and synthetic reference inputs; no database backup",
              "independent_storage_verified": False, "files": [], "restore_checks": []}
    manifest_path = snapshot / "manifest.json"
    try:
        for path in files:
            relative = path.relative_to(root)
            before = digest(path)
            copied = snapshot / "files" / relative
            copied.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, copied)
            if digest(copied) != before or digest(path) != before:
                raise ValueError("Evidence changed or copy checksum did not match")
            report["files"].append({"path": relative.as_posix(), "bytes": copied.stat().st_size, "sha256": before})
        for suffix in (".csv", ".xml", ".json"):
            entry = next((item for item in report["files"] if Path(item["path"]).suffix == suffix), None)
            if entry is None:
                raise ValueError("Required representative restore format is missing")
            restored = snapshot / "restore-check" / entry["path"]
            restored.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(snapshot / "files" / entry["path"], restored)
            if digest(restored) != entry["sha256"]:
                raise ValueError("Restored sample checksum did not match")
            report["restore_checks"].append({"path": entry["path"], "sha256": entry["sha256"], "status": "pass"})
        report["status"] = "pass"
        report["copied_files"] = len(report["files"])
        report["source_bytes"] = sum(item["bytes"] for item in report["files"])
        report["completed_at_utc"] = datetime.now(timezone.utc).isoformat()
    except (OSError, ValueError):
        report["status"] = "failed"
        raise
    finally:
        manifest_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--destination", type=Path, required=True)
    args = parser.parse_args()
    try:
        report = backup_evidence(args.destination)
    except (OSError, ValueError) as exc:
        parser.exit(2, f"Evidence backup failed ({type(exc).__name__}); inspect the snapshot manifest.\n")
    print(f"Verified {report['copied_files']} copied files and {len(report['restore_checks'])} sample restores")
    print(f"Manifest: {Path(report['snapshot_directory']) / 'manifest.json'}")
    print("Storage independence remains unverified; a local snapshot is not a database restore test.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
