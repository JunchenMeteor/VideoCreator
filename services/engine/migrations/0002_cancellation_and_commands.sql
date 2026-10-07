ALTER TABLE runs ADD COLUMN cancellation_requested INTEGER NOT NULL DEFAULT 0;
CREATE TABLE commands (
 owner TEXT NOT NULL, scope TEXT NOT NULL, idempotency_key TEXT NOT NULL,
 request_sha256 TEXT NOT NULL, result_json TEXT NOT NULL,
 PRIMARY KEY(owner,scope,idempotency_key)
);
PRAGMA user_version=2;
