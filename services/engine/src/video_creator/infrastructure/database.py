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
            version = connection.execute("PRAGMA user_version").fetchone()[0]
            if version > 2:
                raise EngineError("schema_too_new", "Instance schema is newer than this engine", 503)
            connection.execute("PRAGMA journal_mode=WAL")
            if version == 0:
                connection.executescript((migrations / "0001_ledger.sql").read_text(encoding="utf-8"))
        # Recheck under a writer lock: another process may have migrated while this one opened.
        with self.transaction() as connection:
            if connection.execute("PRAGMA user_version").fetchone()[0] == 1:
                migration = (migrations / "0002_cancellation_and_commands.sql").read_text(encoding="utf-8")
                for statement in migration.split(";"):
                    if statement.strip():
                        connection.execute(statement)

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
