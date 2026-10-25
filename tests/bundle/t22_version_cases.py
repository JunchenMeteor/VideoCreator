"""New omitted-version identity and immutable old stored identity are distinct."""
from __future__ import annotations

import copy
import json
import sqlite3

from t21_runtime import CaseBlocked


def expected_new_legacy_version(schema_version):
    assert schema_version == "0.2.0-candidate"
    return schema_version


def stored_request_row(ctx, production_id):
    with sqlite3.connect(ctx.engine.db.path.as_uri() + "?mode=ro", uri=True) as connection:
        row = connection.execute("SELECT id,idempotency_key,request_revision_id,request_sha256,request_json FROM productions WHERE id=?", (production_id,)).fetchone()
    if row is None:
        raise CaseBlocked("genuine_historical_omitted_version_identity", "old stored request must already exist through an approved real historical instance/bootstrap")
    return row


def fixed_request_versions(ctx):
    fixture = ctx.fixture("V03-01")
    body = copy.deepcopy(fixture["legacy_request"])
    body.pop("request_format_version", None)  # Mandatory real omission, not a masking explicit-version fixture.
    omitted = ctx.c.parse_production_request(body)
    assert omitted.request_format_version is None
    first = ctx.engine.accept_production("local-user", "T22-new-omitted-version", omitted)
    assert ctx.engine.accept_production("local-user", "T22-new-omitted-version", omitted) == first
    detail = ctx.engine.get_production("local-user", first.production_id)
    assert detail.request.request_format_version == expected_new_legacy_version(ctx.c.SCHEMA_VERSION)
    new_row = stored_request_row(ctx, first.production_id)
    assert json.loads(new_row[4])["request_format_version"] == ctx.c.SCHEMA_VERSION
    modern = ctx.c.parse_production_request(fixture["v03_request"])
    assert modern.request_format_version == "0.3.0-candidate"
    conflict = ctx.error("idempotency_conflict", ctx.engine.accept_production, "local-user", "T22-new-omitted-version", modern)
    assert stored_request_row(ctx, first.production_id) == new_row
    if not fixture.get("historical_request_origin"):
        raise CaseBlocked("genuine_historical_omitted_version_identity", "new default-version result does not replace old immutable body/hash coverage")
    origin = ctx.bound_json(fixture["historical_request_origin"])
    old_before = stored_request_row(ctx, origin["production_id"])
    assert list(old_before) == origin["original_stored_row"]
    old_request = ctx.c.parse_production_request(old_before[4])
    assert old_request.request_format_version is None
    old = ctx.engine.accept_production("local-user", old_before[1], old_request)
    assert old.production_id == old_before[0]
    assert stored_request_row(ctx, old.production_id) == old_before
    old_detail = ctx.engine.get_production("local-user", old.production_id)
    assert old_detail.request.request_format_version is None
    return {"new_production_id": first.production_id, "new_resolved_version": ctx.c.SCHEMA_VERSION,
            "version_conflict": conflict, "old_production_id": old.production_id,
            "old_body_hash_unchanged": True}
