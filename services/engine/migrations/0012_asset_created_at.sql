ALTER TABLE assets ADD COLUMN created_at_us INTEGER NOT NULL DEFAULT 0 CHECK(typeof(created_at_us)='integer' AND created_at_us BETWEEN 0 AND 9223372036854775807);
PRAGMA user_version=12;
