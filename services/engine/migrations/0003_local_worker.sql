CREATE TABLE execution_bindings (
 run_id TEXT PRIMARY KEY REFERENCES runs(id), body TEXT NOT NULL, content_sha256 TEXT NOT NULL
);
CREATE TABLE worker_presence (
 slot TEXT PRIMARY KEY, worker_id TEXT NOT NULL, pid INTEGER NOT NULL,
 workflow_version TEXT NOT NULL, resource_sha256 TEXT NOT NULL, engine_version TEXT NOT NULL,
 heartbeat_us INTEGER NOT NULL, expires_us INTEGER NOT NULL, state TEXT NOT NULL,
 active_run_id TEXT REFERENCES runs(id)
);
CREATE TABLE generated_attempts (
 id TEXT PRIMARY KEY, run_id TEXT NOT NULL REFERENCES runs(id), step_key TEXT NOT NULL,
 input_sha256 TEXT NOT NULL, output_key TEXT NOT NULL, staging_id TEXT NOT NULL UNIQUE REFERENCES staging(id),
 allocation_fence INTEGER NOT NULL, source TEXT NOT NULL, rights TEXT NOT NULL,
 UNIQUE(run_id,step_key,output_key)
);
PRAGMA user_version=3;
