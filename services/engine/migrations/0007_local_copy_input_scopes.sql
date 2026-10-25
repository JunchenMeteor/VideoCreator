CREATE TABLE local_copy_input_scopes (
    scope_id TEXT NOT NULL,
    revision INTEGER NOT NULL CHECK(revision > 0),
    owner TEXT NOT NULL,
    project_id TEXT NOT NULL REFERENCES projects(id),
    policy_id TEXT NOT NULL,
    policy_revision INTEGER NOT NULL,
    body TEXT NOT NULL,
    content_sha256 TEXT NOT NULL,
    installation_action_json TEXT NOT NULL,
    installation_action_sha256 TEXT NOT NULL,
    current INTEGER NOT NULL CHECK(current IN (0,1)),
    revoked INTEGER NOT NULL DEFAULT 0 CHECK(revoked IN (0,1)),
    revocation_action_json TEXT,
    revocation_action_sha256 TEXT,
    registry_revision INTEGER NOT NULL UNIQUE CHECK(registry_revision > 0),
    installed_at_us INTEGER NOT NULL CHECK(installed_at_us > 0),
    PRIMARY KEY(scope_id,revision),
    FOREIGN KEY(policy_id,policy_revision) REFERENCES production_authorization_policies(policy_id,revision),
    CHECK((revoked=0 AND revocation_action_json IS NULL AND revocation_action_sha256 IS NULL)
        OR (revoked=1 AND revocation_action_json IS NOT NULL AND revocation_action_sha256 IS NOT NULL))
);
CREATE UNIQUE INDEX local_copy_input_scope_current ON local_copy_input_scopes(scope_id) WHERE current=1;
CREATE TABLE local_copy_input_bindings (
    id TEXT PRIMARY KEY,
    production_id TEXT NOT NULL REFERENCES productions(id),
    run_id TEXT NOT NULL REFERENCES runs(id),
    request_revision_id TEXT NOT NULL,
    request_sha256 TEXT NOT NULL,
    owner TEXT NOT NULL,
    project_id TEXT NOT NULL REFERENCES projects(id),
    executing_principal_id TEXT NOT NULL,
    registration_sha256 TEXT NOT NULL,
    scope_id TEXT NOT NULL,
    scope_revision INTEGER NOT NULL,
    policy_id TEXT NOT NULL,
    policy_revision INTEGER NOT NULL,
    source_set_sha256 TEXT NOT NULL,
    selection_action_json TEXT NOT NULL,
    selection_action_sha256 TEXT NOT NULL,
    body TEXT NOT NULL,
    content_sha256 TEXT NOT NULL,
    current INTEGER NOT NULL CHECK(current IN (0,1)),
    bound_at_us INTEGER NOT NULL CHECK(bound_at_us > 0),
    registry_revision INTEGER NOT NULL CHECK(registry_revision > 0),
    FOREIGN KEY(scope_id,scope_revision) REFERENCES local_copy_input_scopes(scope_id,revision),
    FOREIGN KEY(policy_id,policy_revision) REFERENCES production_authorization_policies(policy_id,revision)
);
CREATE UNIQUE INDEX local_copy_input_binding_current ON local_copy_input_bindings(
    production_id,run_id,request_revision_id,request_sha256,executing_principal_id,registration_sha256
) WHERE current=1;
INSERT INTO metadata(key,value) VALUES('local_copy_input_registry_revision','0');
PRAGMA user_version=7;
