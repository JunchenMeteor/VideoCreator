CREATE TABLE bundle_revisions (
 id TEXT PRIMARY KEY, bundle_id TEXT NOT NULL, revision_id TEXT NOT NULL UNIQUE,
 owner TEXT NOT NULL, project_id TEXT NOT NULL REFERENCES projects(id),
 production_id TEXT NOT NULL REFERENCES productions(id), run_id TEXT NOT NULL REFERENCES runs(id),
 request_revision_id TEXT NOT NULL, input_sha256 TEXT NOT NULL, intent_json TEXT NOT NULL,
 status TEXT NOT NULL CHECK(status IN ('prepared','published')), prepared_fence INTEGER NOT NULL,
 manifest_json TEXT, manifest_sha256 TEXT, manifest_file_key TEXT,
 created_at_us INTEGER NOT NULL, published_at_us INTEGER
);
CREATE TABLE bundle_items (
 preparation_id TEXT NOT NULL REFERENCES bundle_revisions(id), artifact_id TEXT NOT NULL,
 asset_id TEXT REFERENCES assets(id), material_id TEXT UNIQUE, relative_path TEXT NOT NULL,
 media_type TEXT NOT NULL, schema_kind TEXT, sha256 TEXT, size INTEGER,
 status TEXT NOT NULL CHECK(status IN ('allocated','writing','ready')), allocation_fence INTEGER NOT NULL,
 PRIMARY KEY(preparation_id,artifact_id), UNIQUE(preparation_id,relative_path),
 CHECK((asset_id IS NULL) != (material_id IS NULL))
);
CREATE TABLE bundle_exports (
 id TEXT PRIMARY KEY, owner TEXT NOT NULL, registration_id TEXT,
 preparation_id TEXT REFERENCES bundle_revisions(id), import_id TEXT,
 input_sha256 TEXT NOT NULL, request_json TEXT NOT NULL, actor_json TEXT NOT NULL,
 status TEXT NOT NULL CHECK(status IN ('queued','building','ready','failed')),
 worker_id TEXT, lease_until_us INTEGER NOT NULL DEFAULT 0, fencing_token INTEGER NOT NULL DEFAULT 0,
 archive_file_key TEXT, archive_sha256 TEXT, size INTEGER, error_code TEXT, created_at_us INTEGER NOT NULL,
 CHECK((preparation_id IS NULL) != (import_id IS NULL))
);
CREATE TABLE bundle_grants (
 id TEXT PRIMARY KEY, preparation_id TEXT NOT NULL REFERENCES bundle_revisions(id),
 owner TEXT NOT NULL, recipient_id TEXT NOT NULL, body TEXT NOT NULL,
 expires_at_us INTEGER NOT NULL, revoked_at_us INTEGER
);
CREATE TABLE bundle_imports (
 id TEXT PRIMARY KEY, owner TEXT NOT NULL, project_id TEXT NOT NULL REFERENCES projects(id),
 origin_key TEXT NOT NULL, origin_ref_json TEXT NOT NULL, manifest_json TEXT NOT NULL,
 manifest_file_key TEXT NOT NULL, mapping_json TEXT NOT NULL, created_at_us INTEGER NOT NULL,
 index_state TEXT NOT NULL DEFAULT 'not_built', UNIQUE(owner,project_id,origin_key)
);
CREATE INDEX bundle_revisions_visible ON bundle_revisions(owner,project_id,status,revision_id);
CREATE INDEX bundle_exports_dispatch ON bundle_exports(status,lease_until_us);
CREATE INDEX bundle_grants_recipient ON bundle_grants(preparation_id,recipient_id,expires_at_us);
PRAGMA user_version=4;
