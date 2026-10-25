"""Expose real SQLite migration boundaries; the parent controls or kills the process."""

import argparse
import importlib.util
import json
import os
import time
from pathlib import Path


def emit(**value):
    print(json.dumps(value, ensure_ascii=False), flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("data_dir", type=Path)
    parser.add_argument("mode", choices=["paused-first", "contender", "kill-create", "kill-alter"])
    parser.add_argument("release", type=Path)
    args = parser.parse_args()
    source = os.environ.get("TEST_DATABASE_SOURCE_FILE")
    if source:
        spec = importlib.util.spec_from_file_location("test_database_source", source)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    else:
        from video_creator.infrastructure import database as module

    original = module._Connection
    announced = False

    def boundary(connection, phase):
        nonlocal announced
        if announced:
            return
        announced = True
        emit(phase=phase, in_transaction=connection.in_transaction, mode=args.mode)
        if args.mode != "contender":
            deadline = time.monotonic() + 25
            while not args.release.is_file():
                if time.monotonic() >= deadline:
                    raise TimeoutError("Parent did not release the controlled boundary")
                time.sleep(0.01)

    class ProbeConnection(original):
        def execute(self, sql, parameters=()):
            normalized = sql.strip().upper()
            if args.mode == "contender" and normalized == "BEGIN IMMEDIATE":
                boundary(self, "writer_attempt")
            if args.mode == "paused-first" and normalized.startswith("CREATE TABLE IF NOT EXISTS METADATA"):
                boundary(self, "initial_schema_before_write")
            cursor = super().execute(sql, parameters)
            if args.mode == "kill-create" and normalized.startswith("CREATE TABLE IF NOT EXISTS METADATA"):
                boundary(self, "initial_ddl_uncommitted")
            if args.mode == "kill-alter" and normalized.startswith("ALTER TABLE RUNS ADD COLUMN"):
                boundary(self, "alter_uncommitted")
            return cursor

        def executescript(self, sql):
            if args.mode == "paused-first":
                boundary(self, "initial_schema_before_write")
            return super().executescript(sql)

    module._Connection = ProbeConnection
    try:
        database = module.Database(args.data_dir)
        with database.connect() as connection:
            version = connection.execute("PRAGMA user_version").fetchone()[0]
            columns = [row["name"] for row in connection.execute("PRAGMA table_info(runs)")]
        emit(phase="completed", version=version, cancellation_columns=columns.count("cancellation_requested"))
    except Exception as error:
        emit(phase="failed", error_type=type(error).__name__, error=str(error))
        raise


if __name__ == "__main__":
    main()
