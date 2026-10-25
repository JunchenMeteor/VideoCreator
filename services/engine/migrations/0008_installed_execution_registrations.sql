CREATE TABLE installed_native_records (
    record_id TEXT NOT NULL,
    revision INTEGER NOT NULL CHECK(revision>0),
    instance_id TEXT NOT NULL,
    owner TEXT NOT NULL,
    composition_root TEXT NOT NULL,
    body TEXT NOT NULL,
    content_sha256 TEXT NOT NULL,
    installation_action_json TEXT NOT NULL,
    installation_action_sha256 TEXT NOT NULL,
    current INTEGER NOT NULL CHECK(current IN (0,1)),
    revoked INTEGER NOT NULL DEFAULT 0 CHECK(revoked IN (0,1)),
    revocation_action_json TEXT,
    revocation_action_sha256 TEXT,
    registry_revision INTEGER NOT NULL CHECK(registry_revision>0),
    PRIMARY KEY(record_id,revision),
    CHECK((revoked=0 AND revocation_action_json IS NULL AND revocation_action_sha256 IS NULL)
        OR (revoked=1 AND revocation_action_json IS NOT NULL AND revocation_action_sha256 IS NOT NULL))
);
CREATE UNIQUE INDEX installed_native_current ON installed_native_records(instance_id,owner,composition_root) WHERE current=1;
CREATE TABLE execution_registrations (
    registration_id TEXT NOT NULL,
    revision INTEGER NOT NULL CHECK(revision>0),
    instance_id TEXT NOT NULL,
    owner TEXT NOT NULL,
    role TEXT NOT NULL CHECK(role IN ('api','mcp','worker')),
    installed_record_id TEXT NOT NULL,
    installed_record_revision INTEGER NOT NULL,
    body TEXT NOT NULL,
    content_sha256 TEXT NOT NULL,
    installation_action_json TEXT NOT NULL,
    installation_action_sha256 TEXT NOT NULL,
    selection_action_json TEXT,
    selection_action_sha256 TEXT,
    current INTEGER NOT NULL CHECK(current IN (0,1)),
    revoked INTEGER NOT NULL DEFAULT 0 CHECK(revoked IN (0,1)),
    revocation_action_json TEXT,
    revocation_action_sha256 TEXT,
    registry_revision INTEGER NOT NULL CHECK(registry_revision>0),
    PRIMARY KEY(registration_id,revision),
    FOREIGN KEY(installed_record_id,installed_record_revision) REFERENCES installed_native_records(record_id,revision),
    CHECK((selection_action_json IS NULL AND selection_action_sha256 IS NULL)
        OR (selection_action_json IS NOT NULL AND selection_action_sha256 IS NOT NULL)),
    CHECK((revoked=0 AND revocation_action_json IS NULL AND revocation_action_sha256 IS NULL)
        OR (revoked=1 AND revocation_action_json IS NOT NULL AND revocation_action_sha256 IS NOT NULL))
);
CREATE UNIQUE INDEX execution_registration_current ON execution_registrations(instance_id,owner,role) WHERE current=1;
PRAGMA user_version=8;
