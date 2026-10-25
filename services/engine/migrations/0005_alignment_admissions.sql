CREATE TABLE alignment_admissions (
    kind TEXT NOT NULL CHECK(kind IN ('policy','qualification','reference_issuer')),
    admission_id TEXT NOT NULL,
    revision INTEGER NOT NULL CHECK(revision > 0),
    body TEXT NOT NULL,
    content_sha256 TEXT NOT NULL,
    issuer TEXT NOT NULL,
    approval_json TEXT NOT NULL,
    benchmark_json TEXT NOT NULL,
    benchmark_sha256 TEXT NOT NULL,
    installation_sequence INTEGER NOT NULL UNIQUE,
    installed_at_us INTEGER NOT NULL,
    PRIMARY KEY(kind,admission_id,revision)
);
CREATE TABLE alignment_revocations (
    issuer TEXT NOT NULL,
    dedupe_key TEXT NOT NULL,
    target_kind TEXT NOT NULL CHECK(target_kind IN ('policy','qualification','reference_issuer')),
    target_id TEXT NOT NULL,
    target_revision INTEGER NOT NULL CHECK(target_revision > 0),
    effective_at_us INTEGER NOT NULL,
    reason TEXT NOT NULL,
    body TEXT NOT NULL,
    registry_revision INTEGER NOT NULL UNIQUE,
    PRIMARY KEY(issuer,dedupe_key)
);
CREATE INDEX alignment_revocation_target ON alignment_revocations(target_kind,target_id,target_revision,effective_at_us);
INSERT INTO metadata(key,value) VALUES('evidence_registry_revision','0');
PRAGMA user_version=5;
