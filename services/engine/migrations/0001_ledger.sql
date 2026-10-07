PRAGMA foreign_keys=ON;
CREATE TABLE IF NOT EXISTS metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS projects (id TEXT PRIMARY KEY, owner TEXT NOT NULL,
 body TEXT NOT NULL DEFAULT '{"name":"未命名项目","goal":"","source_text":""}', revision INTEGER NOT NULL DEFAULT 1,
 saved_at_us INTEGER NOT NULL DEFAULT 0);
CREATE TABLE IF NOT EXISTS budget_groups (
 id TEXT PRIMARY KEY, owner TEXT NOT NULL, currency TEXT NOT NULL CHECK(currency='CNY'), cap_units INTEGER NOT NULL CHECK(cap_units>=0),
 spent_units INTEGER NOT NULL DEFAULT 0 CHECK(spent_units>=0), reserved_units INTEGER NOT NULL DEFAULT 0 CHECK(reserved_units>=0)
);
CREATE TABLE IF NOT EXISTS routes (id TEXT PRIMARY KEY, body TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS productions (
 id TEXT PRIMARY KEY, project_id TEXT NOT NULL REFERENCES projects(id), owner TEXT NOT NULL,
 idempotency_key TEXT NOT NULL, request_sha256 TEXT NOT NULL, request_revision_id TEXT NOT NULL,
 request_json TEXT NOT NULL, status TEXT NOT NULL, budget_group_id TEXT REFERENCES budget_groups(id),
 cap_units INTEGER NOT NULL, spent_units INTEGER NOT NULL DEFAULT 0, reserved_units INTEGER NOT NULL DEFAULT 0,
 revision_cycles INTEGER NOT NULL DEFAULT 0, created_at_us INTEGER NOT NULL, UNIQUE(owner,idempotency_key)
);
CREATE TABLE IF NOT EXISTS runs (
 id TEXT PRIMARY KEY, production_id TEXT NOT NULL REFERENCES productions(id), status TEXT NOT NULL,
 worker_id TEXT, lease_until_us INTEGER NOT NULL DEFAULT 0, fencing_token INTEGER NOT NULL DEFAULT 0,
 attempt INTEGER NOT NULL DEFAULT 0, paused INTEGER NOT NULL DEFAULT 0, waiting_revision_id TEXT
);
CREATE TABLE IF NOT EXISTS steps (
 run_id TEXT NOT NULL REFERENCES runs(id), step_key TEXT NOT NULL, input_sha256 TEXT NOT NULL,
 status TEXT NOT NULL, fencing_token INTEGER NOT NULL, result_json TEXT, PRIMARY KEY(run_id,step_key)
);
CREATE TABLE IF NOT EXISTS operations (
 id TEXT PRIMARY KEY, production_id TEXT NOT NULL REFERENCES productions(id), run_id TEXT NOT NULL REFERENCES runs(id),
 step_key TEXT NOT NULL, dedupe_key TEXT NOT NULL, input_sha256 TEXT NOT NULL, route_json TEXT NOT NULL,
 status TEXT NOT NULL, reserved_units INTEGER NOT NULL, settled INTEGER NOT NULL DEFAULT 0,
 actual_units INTEGER, cost_evidence TEXT NOT NULL DEFAULT 'unknown', external_id TEXT,
 observation_json TEXT, claimed_fence INTEGER, created_at_us INTEGER NOT NULL, UNIQUE(production_id,dedupe_key)
);
CREATE TABLE IF NOT EXISTS staging (
 id TEXT PRIMARY KEY, owner TEXT NOT NULL, media_type TEXT NOT NULL, sha256 TEXT NOT NULL,
 size INTEGER NOT NULL, status TEXT NOT NULL, asset_id TEXT
);
CREATE TABLE IF NOT EXISTS assets (
 id TEXT PRIMARY KEY, owner TEXT NOT NULL, sha256 TEXT NOT NULL, size INTEGER NOT NULL,
 media_type TEXT NOT NULL, source TEXT NOT NULL, rights TEXT NOT NULL, probe_json TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS decisions (
 run_id TEXT NOT NULL REFERENCES runs(id), idempotency_key TEXT NOT NULL, request_sha256 TEXT NOT NULL,
 body TEXT NOT NULL, result_json TEXT NOT NULL, PRIMARY KEY(run_id,idempotency_key)
);
CREATE TABLE IF NOT EXISTS creative_revisions (
 id TEXT PRIMARY KEY, production_id TEXT NOT NULL REFERENCES productions(id), run_id TEXT NOT NULL REFERENCES runs(id),
 kind TEXT NOT NULL, body TEXT NOT NULL, content_sha256 TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS feedback_revisions (
 id TEXT PRIMARY KEY, production_id TEXT NOT NULL REFERENCES productions(id), new_run_id TEXT NOT NULL REFERENCES runs(id), body TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS events (
 sequence INTEGER PRIMARY KEY AUTOINCREMENT, id TEXT NOT NULL UNIQUE,
 production_id TEXT NOT NULL REFERENCES productions(id), run_id TEXT NOT NULL REFERENCES runs(id),
 event_type TEXT NOT NULL, status TEXT NOT NULL, occurred_at_us INTEGER NOT NULL, entity_revision_id TEXT,
 delivered INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS runs_dispatch ON runs(status,paused,lease_until_us);
CREATE INDEX IF NOT EXISTS operations_recovery ON operations(run_id,status);
CREATE INDEX IF NOT EXISTS events_run_sequence ON events(run_id,sequence);
PRAGMA user_version=1;
