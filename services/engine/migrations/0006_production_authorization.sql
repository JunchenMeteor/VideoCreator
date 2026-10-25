CREATE TABLE production_authorization_policies (
    policy_id TEXT NOT NULL,
    revision INTEGER NOT NULL CHECK(revision > 0),
    owner TEXT NOT NULL,
    body TEXT NOT NULL,
    content_sha256 TEXT NOT NULL,
    installation_action_json TEXT NOT NULL,
    installation_action_sha256 TEXT NOT NULL,
    current INTEGER NOT NULL CHECK(current IN (0,1)),
    revoked INTEGER NOT NULL DEFAULT 0 CHECK(revoked IN (0,1)),
    revocation_action_json TEXT,
    revocation_action_sha256 TEXT,
    installed_at_us INTEGER NOT NULL,
    registry_revision INTEGER NOT NULL UNIQUE,
    PRIMARY KEY(policy_id,revision),
    CHECK((revoked=0 AND revocation_action_json IS NULL AND revocation_action_sha256 IS NULL)
        OR (revoked=1 AND revocation_action_json IS NOT NULL AND revocation_action_sha256 IS NOT NULL))
);
CREATE UNIQUE INDEX production_policy_current ON production_authorization_policies(policy_id) WHERE current=1;
CREATE TABLE production_admissions (
    id TEXT PRIMARY KEY,
    production_id TEXT NOT NULL REFERENCES productions(id),
    run_id TEXT NOT NULL REFERENCES runs(id),
    phase TEXT NOT NULL CHECK(phase IN ('request','plan','quality')),
    action TEXT NOT NULL CHECK(action IN ('bind_request','begin_execution','execute_plan','continue_bundle_validation','finalize_bundle')),
    target_kind TEXT NOT NULL CHECK(target_kind IN ('request','creative_revision','final_manifest')),
    target_id TEXT NOT NULL,
    target_sha256 TEXT NOT NULL,
    policy_id TEXT NOT NULL,
    policy_revision INTEGER NOT NULL,
    fencing_token INTEGER,
    body TEXT NOT NULL,
    content_sha256 TEXT NOT NULL,
    issued_at_us INTEGER NOT NULL,
    FOREIGN KEY(policy_id,policy_revision) REFERENCES production_authorization_policies(policy_id,revision),
    CHECK((action='bind_request' AND fencing_token IS NULL)
        OR (action!='bind_request' AND fencing_token IS NOT NULL AND fencing_token>0))
);
CREATE UNIQUE INDEX production_admission_identity ON production_admissions(
    production_id,run_id,target_kind,target_id,phase,action,policy_id,policy_revision,COALESCE(fencing_token,0)
);
INSERT INTO metadata(key,value) VALUES('production_authorization_registry_revision','0');
PRAGMA user_version=6;
