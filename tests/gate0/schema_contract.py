"""Derive the expected installation schema contract from production sources.

Test-only helper. The expected migration catalog, migration count and current
schema version are read from the engine and from ``services/engine/migrations``
on every run instead of being frozen as literals, so a newly added migration
cannot silently drift past the gate0 persistence checks.
"""

from pathlib import Path

from video_creator.infrastructure.database import CURRENT_SCHEMA_VERSION

REPO = Path(__file__).resolve().parents[2]
MIGRATIONS_DIR = REPO / "services/engine/migrations"
__all__ = ["CURRENT_SCHEMA_VERSION", "MIGRATIONS_DIR", "assert_migration_catalog_matches_engine",
           "migration_files", "migration_versions"]


def migration_files():
    return sorted(path.name for path in MIGRATIONS_DIR.glob("[0-9][0-9][0-9][0-9]_*.sql"))


def migration_versions():
    return [int(name.split("_", 1)[0]) for name in migration_files()]


def assert_migration_catalog_matches_engine():
    """Every on-disk migration is applied in order up to CURRENT_SCHEMA_VERSION."""
    versions = migration_versions()
    assert versions == list(range(1, CURRENT_SCHEMA_VERSION + 1)), (
        "Migration catalog and CURRENT_SCHEMA_VERSION disagree: "
        f"versions={versions} CURRENT_SCHEMA_VERSION={CURRENT_SCHEMA_VERSION}")
