CREATE TABLE installation_qualification_trust (
    admission_id TEXT PRIMARY KEY NOT NULL,
    revision INTEGER NOT NULL UNIQUE CHECK(typeof(revision)='integer' AND revision BETWEEN 1 AND 9223372036854775807),
    action_id TEXT NOT NULL UNIQUE,
    issuer_id TEXT NOT NULL,
    trust_mode TEXT NOT NULL CHECK(trust_mode IN ('publisher','local_verifier')),
    public_key_hex TEXT NOT NULL CHECK(length(public_key_hex)=64 AND public_key_hex NOT GLOB '*[^0-9a-f]*'),
    materials_json TEXT NOT NULL CHECK(length(CAST(materials_json AS BLOB))<=1048576),
    host_build_receipt_sha256 TEXT NOT NULL,
    intent_sha256 TEXT NOT NULL,
    accepted_at_us INTEGER NOT NULL CHECK(typeof(accepted_at_us)='integer' AND accepted_at_us BETWEEN 1 AND 9223372036854775807),
    source_receipt_json TEXT NOT NULL CHECK(length(CAST(source_receipt_json AS BLOB))<=1048576)
);
CREATE TABLE installation_qualification_records (
    record_id TEXT NOT NULL,
    revision INTEGER NOT NULL CHECK(typeof(revision)='integer' AND revision BETWEEN 1 AND 9223372036854775807),
    record_sha256 TEXT NOT NULL UNIQUE,
    record_json TEXT NOT NULL CHECK(length(CAST(record_json AS BLOB))<=1048576),
    trust_admission_id TEXT NOT NULL REFERENCES installation_qualification_trust(admission_id),
    PRIMARY KEY(record_id,revision)
);
CREATE TABLE installation_qualification_events (
    registry_revision INTEGER PRIMARY KEY NOT NULL CHECK(typeof(registry_revision)='integer' AND registry_revision BETWEEN 1 AND 9223372036854775807),
    kind TEXT NOT NULL CHECK(kind IN ('trust_admit','record_admit','replace','revoke','trust_revoke')),
    action_id TEXT NOT NULL UNIQUE,
    request_sha256 TEXT NOT NULL,
    trust_admission_id TEXT REFERENCES installation_qualification_trust(admission_id),
    record_id TEXT,
    record_revision INTEGER CHECK(record_revision IS NULL OR (typeof(record_revision)='integer' AND record_revision BETWEEN 1 AND 9223372036854775807)),
    receipt_json TEXT NOT NULL CHECK(length(CAST(receipt_json AS BLOB))<=4194304),
    occurred_at_us INTEGER NOT NULL CHECK(typeof(occurred_at_us)='integer' AND occurred_at_us BETWEEN 1 AND 9223372036854775807),
    CHECK((record_id IS NULL)=(record_revision IS NULL)),
    FOREIGN KEY(record_id,record_revision) REFERENCES installation_qualification_records(record_id,revision)
);
CREATE TABLE installation_qualification_current (
    singleton INTEGER PRIMARY KEY CHECK(typeof(singleton)='integer' AND singleton=1),
    registry_revision INTEGER NOT NULL REFERENCES installation_qualification_events(registry_revision),
    trust_admission_id TEXT REFERENCES installation_qualification_trust(admission_id),
    record_id TEXT,
    record_revision INTEGER CHECK(record_revision IS NULL OR (typeof(record_revision)='integer' AND record_revision BETWEEN 1 AND 9223372036854775807)),
    state TEXT NOT NULL CHECK(state IN ('not_ready','qualified','revoked')),
    CHECK((record_id IS NULL)=(record_revision IS NULL)),
    CHECK(state!='qualified' OR (trust_admission_id IS NOT NULL AND record_id IS NOT NULL)),
    FOREIGN KEY(record_id,record_revision) REFERENCES installation_qualification_records(record_id,revision)
);
CREATE TRIGGER installation_qualification_trust_immutable_update BEFORE UPDATE ON installation_qualification_trust BEGIN SELECT RAISE(ABORT,'qualification trust is immutable'); END;
CREATE TRIGGER installation_qualification_trust_immutable_delete BEFORE DELETE ON installation_qualification_trust BEGIN SELECT RAISE(ABORT,'qualification trust is immutable'); END;
CREATE TRIGGER installation_qualification_record_immutable_update BEFORE UPDATE ON installation_qualification_records BEGIN SELECT RAISE(ABORT,'qualification record is immutable'); END;
CREATE TRIGGER installation_qualification_record_immutable_delete BEFORE DELETE ON installation_qualification_records BEGIN SELECT RAISE(ABORT,'qualification record is immutable'); END;
CREATE TRIGGER installation_qualification_event_immutable_update BEFORE UPDATE ON installation_qualification_events BEGIN SELECT RAISE(ABORT,'qualification event is immutable'); END;
CREATE TRIGGER installation_qualification_event_immutable_delete BEFORE DELETE ON installation_qualification_events BEGIN SELECT RAISE(ABORT,'qualification event is immutable'); END;
PRAGMA user_version=11;
