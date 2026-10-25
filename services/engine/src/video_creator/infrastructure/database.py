"""Short SQLite transactions. No provider or filesystem processing inside them."""

import hashlib
import json
import os
import shutil
import sqlite3
import uuid
from contextlib import contextmanager
from pathlib import Path

from video_creator.domain.errors import EngineError

CURRENT_SCHEMA_VERSION = 12

class _Connection(sqlite3.Connection):
    def __exit__(self, *args):
        try:
            return super().__exit__(*args)
        finally:
            self.close()


class Database:
    def __init__(self, data_dir: Path):
        if not data_dir.is_absolute() or str(data_dir).startswith(("\\\\", "//")):
            raise EngineError("invalid_data_dir", "DataDir must be an absolute local directory", 400)
        self.data_dir = data_dir.resolve()
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.path = self.data_dir / "Metadata.sqlite"
        migrations = Path(os.environ.get("VIDEO_CREATOR_MIGRATIONS_DIR", Path(__file__).parents[3] / "migrations"))
        with self.connect() as connection:
            connection.execute("PRAGMA journal_mode=WAL")
            version = connection.execute("PRAGMA user_version").fetchone()[0]
        if version in {3, 4, 5, 6, 7, 8, 9, 10}:
            # SQLite's backup API includes committed WAL pages. Query file
            # references from that snapshot, never from a later live database.
            self.snapshot_backup()
        # The first version read, initial schema and every upgrade share one writer transaction.
        # executescript is intentionally avoided: it implicitly commits an existing transaction.
        with self.transaction() as connection:
            version = connection.execute("PRAGMA user_version").fetchone()[0]
            if version > CURRENT_SCHEMA_VERSION:
                raise EngineError("schema_too_new", "Instance schema is newer than this engine", 503)
            for target, filename in ((1, "0001_ledger.sql"), (2, "0002_cancellation_and_commands.sql"),
                                     (3, "0003_local_worker.sql"), (4, "0004_bundles.sql"),
                                     (5, "0005_alignment_admissions.sql"),
                                     (6, "0006_production_authorization.sql"),
                                     (7, "0007_local_copy_input_scopes.sql"),
                                     (8, "0008_installed_execution_registrations.sql"),
                                     (9, "0009_daily_project_authorizations.sql"),
                                     (10, "0010_owner_setup_journals.sql"),
                                     (11, "0011_installation_qualification.sql"),
                                     (12, "0012_asset_created_at.sql")):
                if version < target:
                    self._apply_migration(connection, migrations / filename)
                    actual = connection.execute("PRAGMA user_version").fetchone()[0]
                    if actual != target:
                        raise EngineError("migration_version_mismatch", "Migration did not produce its declared schema version", 503)
                    version = actual

    def snapshot_backup(self) -> Path:
        """Consistent metadata plus its known immutable files; no downgrade in place.

        Stop the old host before restoring this separate snapshot. Pending files
        retain their observed bytes/state, not a fabricated completed result.
        OS credential stores and installed runtime resources remain external.
        """
        root = self.data_dir / "Backups"
        if root.is_symlink() or not root.resolve().is_relative_to(self.data_dir):
            raise EngineError("backup_path_denied", "Backup root escaped installation storage", 503)
        destination = root / ("SchemaSnapshot-" + uuid.uuid4().hex)
        destination.mkdir(parents=True)
        target = destination / "Metadata.sqlite"
        with self.connect() as source, sqlite3.connect(target) as snapshot:
            source.backup(snapshot)
        records = []
        def copy_file(folder, key, expected=None):
            if not key or key != Path(key).name or any(value in key for value in (":", "/", "\\")):
                raise EngineError("backup_path_denied", "Snapshot contains an invalid controlled file identity", 503)
            original = self.data_dir / folder / key
            if original.is_symlink() or (self.data_dir / folder).is_symlink() or not original.resolve().is_relative_to(self.data_dir):
                raise EngineError("backup_path_denied", "Snapshot reference escaped installation storage", 503)
            if not original.is_file():
                records.append({"path": folder + "/" + key, "state": "originally_missing"})
                return
            stat = original.stat()
            copied = destination / folder / key
            copied.parent.mkdir(exist_ok=True)
            shutil.copyfile(original, copied)
            with copied.open("rb") as stream:
                sha = hashlib.file_digest(stream, "sha256").hexdigest()
            after = original.stat()
            with original.open("rb") as stream:
                source_sha = hashlib.file_digest(stream, "sha256").hexdigest()
            if (stat.st_size, stat.st_mtime_ns, stat.st_ino) != (after.st_size, after.st_mtime_ns, after.st_ino) or source_sha != sha or (expected and sha != expected):
                raise EngineError("backup_source_changed", "Referenced file changed or was corrupted during snapshot", 503)
            records.append({"path": folder + "/" + key, "state": "copied", "sha256": sha, "size": copied.stat().st_size})
        with sqlite3.connect(target) as snapshot:
            version = snapshot.execute("PRAGMA user_version").fetchone()[0]
            if version not in {3, 4, 5, 6, 7, 8, 9, 10, 11, CURRENT_SCHEMA_VERSION}:
                raise EngineError("backup_schema_unsupported", "Snapshot requires a known installation schema", 503)
            for row in snapshot.execute("SELECT DISTINCT sha256 FROM assets"):
                copy_file("Objects", row[0], row[0])
            for row in snapshot.execute("SELECT id,status,sha256 FROM staging"):
                copy_file("Staging", row[0], row[2] if row[1] in {"ready", "imported"} else None)
                if (self.data_dir / "Staging" / (row[0] + ".partial")).is_file():
                    copy_file("Staging", row[0] + ".partial")
            if version >= 4:
                for row in snapshot.execute("SELECT material_id,sha256 FROM bundle_items WHERE material_id IS NOT NULL AND status='ready'"):
                    copy_file("BundleMaterials", row[0], row[1])
                for row in snapshot.execute("SELECT manifest_file_key,manifest_sha256 FROM bundle_revisions WHERE manifest_file_key IS NOT NULL"):
                    copy_file("BundleManifests", row[0], row[1])
                for row in snapshot.execute("SELECT archive_file_key,archive_sha256 FROM bundle_exports WHERE archive_file_key IS NOT NULL"):
                    copy_file("BundleExports", row[0], row[1])
                for row in snapshot.execute("SELECT manifest_file_key,mapping_json FROM bundle_imports"):
                    copy_file("BundleManifests", row[0])
                    for binding in json.loads(row[1]).values():
                        if binding.get("material_id"):
                            copy_file("BundleMaterials", binding["material_id"])
            trust_identity = dict(snapshot.execute("SELECT key,value FROM metadata WHERE key IN ('evidence_configuration_sha256','evidence_registry_revision','production_authorization_registry_revision','local_copy_input_registry_revision')"))
            knowledge = {
                "production_spent_units": snapshot.execute("SELECT COALESCE(SUM(spent_units),0) FROM productions").fetchone()[0],
                "production_reserved_units": snapshot.execute("SELECT COALESCE(SUM(reserved_units),0) FROM productions").fetchone()[0],
                "unknown_operation_ids": [row[0] for row in snapshot.execute("SELECT id FROM operations WHERE settled=0 ORDER BY id")],
            }
        # Flow checkpoints are a separate fixed SQLite store, not execution fact.
        flow = self.data_dir / "WorkflowState" / "LocalRender.sqlite"
        if flow.is_file():
            if flow.is_symlink() or (self.data_dir / "WorkflowState").is_symlink():
                raise EngineError("backup_path_denied", "Flow checkpoint escaped installation storage", 503)
            (destination / "WorkflowState").mkdir(exist_ok=True)
            with sqlite3.connect(flow) as source, sqlite3.connect(destination / "WorkflowState" / "LocalRender.sqlite") as snapshot:
                source.backup(snapshot)
        with target.open("rb") as stream:
            metadata_sha = hashlib.file_digest(stream, "sha256").hexdigest()
        document = {"schema_version": version, "state": "complete", "metadata_sha256": metadata_sha,
                    "all_referenced_files_present": all(value["state"] == "copied" for value in records), "files": records,
                    "restoration": "Stop host; restore separately; never lower user_version. Reload current externally trusted revocation floor and reconcile all newer cost facts before execution.",
                    "trust_configuration_identity": trust_identity, "cost_knowledge_at_snapshot": knowledge,
                    "rollback_compatibility_verified": False,
                    "external_dependencies": ["OS credential vault", "installed resource manifests and binaries", "current trusted issuer roots, configuration identity and revocation high-water mark", "newer external cost/acceptance facts"]}
        (destination / "Snapshot.json").write_text(json.dumps(document, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
        return destination

    @staticmethod
    def _apply_migration(connection: sqlite3.Connection, path: Path):
        statement = ""
        for line in path.read_text(encoding="utf-8").splitlines(keepends=True):
            statement += line
            if sqlite3.complete_statement(statement):
                connection.execute(statement)
                statement = ""
        if statement.strip():
            raise EngineError("migration_incomplete", "Migration SQL is incomplete", 503)

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=5, isolation_level=None, factory=_Connection)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute("PRAGMA busy_timeout=5000")
        return connection

    def connect_readonly(self) -> sqlite3.Connection:
        # URI escaping binds the original target; mode=ro cannot create a
        # missing database. Do not use immutable=1: committed WAL facts matter.
        connection = sqlite3.connect(self.path.absolute().as_uri() + '?mode=ro', uri=True,
            timeout=5, isolation_level=None, factory=_Connection)
        try:
            connection.row_factory = sqlite3.Row
            connection.execute('PRAGMA query_only=ON')
            connection.execute('PRAGMA foreign_keys=ON')
            connection.execute('PRAGMA busy_timeout=5000')
        except sqlite3.Error:
            connection.close()
            raise
        return connection

    @contextmanager
    def transaction(self):
        connection = self.connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            yield connection
            connection.commit()
        except BaseException:
            connection.rollback()
            raise
        finally:
            connection.close()
