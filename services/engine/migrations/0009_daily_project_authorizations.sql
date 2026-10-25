CREATE TABLE daily_project_authorizations (
    authorization_id TEXT NOT NULL,
    revision INTEGER NOT NULL CHECK(revision>0),
    instance_id TEXT NOT NULL,
    owner TEXT NOT NULL,
    body TEXT NOT NULL,
    content_sha256 TEXT NOT NULL,
    creation_action_json TEXT NOT NULL,
    creation_action_sha256 TEXT NOT NULL,
    current INTEGER NOT NULL CHECK(current IN (0,1)),
    revoked INTEGER NOT NULL DEFAULT 0 CHECK(revoked IN (0,1)),
    revocation_action_json TEXT,
    revocation_action_sha256 TEXT,
    created_projects INTEGER NOT NULL DEFAULT 0 CHECK(created_projects>=0),
    registry_revision INTEGER NOT NULL CHECK(registry_revision>0),
    PRIMARY KEY(authorization_id,revision),
    CHECK((revoked=0 AND revocation_action_json IS NULL AND revocation_action_sha256 IS NULL)
       OR (revoked=1 AND revocation_action_json IS NOT NULL AND revocation_action_sha256 IS NOT NULL))
);
CREATE UNIQUE INDEX daily_project_authorization_current ON daily_project_authorizations(instance_id,owner,authorization_id) WHERE current=1;
CREATE TABLE project_scope_derivations (
    derivation_id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL UNIQUE REFERENCES projects(id),
    instance_id TEXT NOT NULL,
    owner TEXT NOT NULL,
    authorization_id TEXT NOT NULL,
    authorization_revision INTEGER NOT NULL,
    production_id TEXT NOT NULL UNIQUE REFERENCES productions(id),
    run_id TEXT NOT NULL UNIQUE REFERENCES runs(id),
    body TEXT NOT NULL,
    content_sha256 TEXT NOT NULL,
    receipt_json TEXT NOT NULL,
    receipt_sha256 TEXT NOT NULL,
    revoked INTEGER NOT NULL DEFAULT 0 CHECK(revoked IN (0,1)),
    revocation_action_json TEXT,
    revocation_action_sha256 TEXT,
    registry_revision INTEGER NOT NULL CHECK(registry_revision>0),
    FOREIGN KEY(authorization_id,authorization_revision) REFERENCES daily_project_authorizations(authorization_id,revision),
    CHECK((revoked=0 AND revocation_action_json IS NULL AND revocation_action_sha256 IS NULL)
       OR (revoked=1 AND revocation_action_json IS NOT NULL AND revocation_action_sha256 IS NOT NULL))
);
PRAGMA user_version=9;
