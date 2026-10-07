"""Short SQLite transactions. No provider or filesystem processing inside them."""

import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path

from video_creator.domain.errors import EngineError


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
        # The first version read, initial schema and every upgrade share one writer transaction.
        # executescript is intentionally avoided: it implicitly commits an existing transaction.
        with self.transaction() as connection:
            version = connection.execute("PRAGMA user_version").fetchone()[0]
            if version > 2:
                raise EngineError("schema_too_new", "Instance schema is newer than this engine", 503)
            for target, filename in ((1, "0001_ledger.sql"), (2, "0002_cancellation_and_commands.sql")):
                if version < target:
                    self._apply_migration(connection, migrations / filename)
                    actual = connection.execute("PRAGMA user_version").fetchone()[0]
                    if actual != target:
                        raise EngineError("migration_version_mismatch", "Migration did not produce its declared schema version", 503)
                    version = actual

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
