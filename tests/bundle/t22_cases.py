"""Scoped overrides: inherited 68 IDs/field meanings stay unchanged."""
from __future__ import annotations

from t21_cases import CASE_ROWS as INHERITED_ROWS, dispatch as inherited_dispatch

OVERRIDES = {"T15-36": "contract_transports", "V03-01": "fixed_request_versions", "V03-18": "transports_detached"}


def contract_transports(ctx):
    from t22_process_cases import actual_mcp_host, actual_missing_mcp_token_startup
    # Keep real HTTP/OpenAPI checking without calling the old MCP client.
    fixture = ctx.fixture("T15-36")
    driver = ctx.http()
    actual = driver.request("GET", "/openapi.json")
    assert actual.status == 200 and actual.json() == ctx.bound_json(fixture["generated_openapi"])
    assert "ErrorEnvelope" in actual.json()["components"]["schemas"]
    # No direct handler, mock server or owner result substitutes for stdio.
    return {"actual_HTTP_contract": "exact_frozen_document", "actual_MCP": actual_mcp_host(ctx),
            "actual_missing_MCP_startup_token": actual_missing_mcp_token_startup(ctx)}


def fixed_request_versions(ctx):
    from t22_version_cases import fixed_request_versions as actual_driver
    return actual_driver(ctx)


def transports_detached(ctx):
    from t21_bundle_cases import autonomous_once
    from t21_process_cases import same_worker_second_run, actual_worker_stop_new_claims
    from t22_process_cases import actual_mcp_host, actual_worker_control_boundaries
    return {"actual_HTTP_goal": autonomous_once(ctx), "actual_MCP_stdio": actual_mcp_host(ctx),
            "actual_persistent_worker": same_worker_second_run(ctx),
            "actual_private_pipe": actual_worker_control_boundaries(ctx), "actual_stop_new_claims": actual_worker_stop_new_claims(ctx)}


def dispatch(ctx, case_id):
    if case_id in OVERRIDES:
        return globals()[OVERRIDES[case_id]](ctx)
    return inherited_dispatch(ctx, case_id)
