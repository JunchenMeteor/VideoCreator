CREATE TABLE owner_setup_journals (
    setup_id TEXT PRIMARY KEY,
    instance_id TEXT NOT NULL,
    owner TEXT NOT NULL,
    preparation_key TEXT NOT NULL,
    request_sha256 TEXT NOT NULL,
    project_create_key TEXT NOT NULL,
    preparation_json TEXT,
    preparation_sha256 TEXT,
    accepted_json TEXT,
    accepted_sha256 TEXT,
    project_id TEXT UNIQUE REFERENCES projects(id),
    phase TEXT NOT NULL CHECK(phase IN ('preparing','prepared','accepted','running','blocked','completed','aborted')),
    created_at_us INTEGER NOT NULL CHECK(created_at_us>0),
    goal_result_json TEXT,
    goal_result_sha256 TEXT,
    UNIQUE(instance_id,owner,preparation_key),
    CHECK((preparation_json IS NULL AND preparation_sha256 IS NULL) OR
          (preparation_json IS NOT NULL AND preparation_sha256 IS NOT NULL)),
    CHECK((accepted_json IS NULL AND accepted_sha256 IS NULL) OR
          (accepted_json IS NOT NULL AND accepted_sha256 IS NOT NULL)),
    CHECK((goal_result_json IS NULL AND goal_result_sha256 IS NULL) OR
          (goal_result_json IS NOT NULL AND goal_result_sha256 IS NOT NULL))
);
CREATE UNIQUE INDEX owner_setup_one_pending ON owner_setup_journals(instance_id,owner)
    WHERE phase NOT IN ('completed','aborted');
CREATE TABLE owner_setup_steps (
    setup_id TEXT NOT NULL REFERENCES owner_setup_journals(setup_id),
    step_id TEXT NOT NULL,
    original_proposal_sha256 TEXT NOT NULL,
    command_json TEXT NOT NULL,
    command_sha256 TEXT NOT NULL,
    dependency_json TEXT NOT NULL,
    receipt_json TEXT,
    receipt_sha256 TEXT,
    original_request_sha256 TEXT,
    PRIMARY KEY(setup_id,step_id),
    CHECK((receipt_json IS NULL AND receipt_sha256 IS NULL AND original_request_sha256 IS NULL) OR
          (receipt_json IS NOT NULL AND receipt_sha256 IS NOT NULL AND original_request_sha256 IS NOT NULL))
);
PRAGMA user_version=10;
