"""Deterministic capability-source visibility and route decisions."""

from __future__ import annotations

import json

from video_creator.application import credentials as credential_store
from video_creator.domain import contracts as c
from video_creator.domain.errors import EngineError


def _credential_refs(data_dir) -> dict[str, dict]:
    return {item["credential_ref"]: item for item in credential_store.list_credentials(data_dir)}


def capabilities(engine) -> c.CapabilityListV1:
    with engine.db.connect_readonly() as connection:
        routes = [c.CapabilityRoute.model_validate(json.loads(row["body"]))
                  for row in connection.execute("SELECT body FROM routes ORDER BY id")]
    credentials = _credential_refs(engine.db.data_dir)
    items = []
    seen_official = False
    seen_byok_route = False
    for route in routes:
        if route.source == "owned_local":
            items.append(c.CapabilitySourceV1(kind="owned_local", route_id=route.route_id,
                                              available=True, reason="installed_zero_cost_local_route"))
        elif route.source == "official":
            seen_official = True
            items.append(c.CapabilitySourceV1(kind="official", route_id=route.route_id, available=False,
                                              reason="official_gateway_not_configured"))
        elif route.credential_ref:
            seen_byok_route = True
            installed = route.credential_ref in credentials
            items.append(c.CapabilitySourceV1(kind="byok", route_id=route.route_id,
                                              credential_ref=route.credential_ref, available=installed,
                                              reason="installed_byok_route" if installed else "byok_credential_missing"))
    if not seen_byok_route:
        for ref in credentials:
            items.append(c.CapabilitySourceV1(kind="byok", credential_ref=ref, available=False,
                                              reason="byok_route_not_installed"))
    if not seen_official:
        items.append(c.CapabilitySourceV1(kind="official", available=False,
                                          reason="official_gateway_not_configured"))
    return c.CapabilityListV1(capabilities=tuple(items))


def route_decisions(engine, request) -> tuple[c.RouteDecisionV1, ...]:
    credentials = _credential_refs(engine.db.data_dir)
    decisions = []
    for route_id in request.policy.allowed_provider_routes:
        try:
            route = engine.configured_route(route_id)
        except EngineError:
            if route_id.startswith("official"):
                decisions.append(c.RouteDecisionV1(capability=route_id, route_id=route_id,
                                                   source_kind="official", reason="official_gateway_not_configured"))
            else:
                decisions.append(c.RouteDecisionV1(capability=route_id, route_id=route_id,
                                                   source_kind="unavailable", reason="capability_unavailable"))
            continue
        if route.source == "owned_local":
            decisions.append(c.RouteDecisionV1(capability=route.capability, route_id=route.route_id,
                                               source_kind="owned_local", reason="installed_zero_cost_local_route"))
        elif route.source == "official":
            decisions.append(c.RouteDecisionV1(capability=route.capability, route_id=route.route_id,
                                               source_kind="official", reason="official_gateway_not_configured"))
        else:
            installed = bool(route.credential_ref and route.credential_ref in credentials)
            decisions.append(c.RouteDecisionV1(capability=route.capability, route_id=route.route_id,
                                               source_kind="byok", reason="installed_byok_route" if installed
                                               else "byok_credential_missing"))
    return tuple(decisions)


def assert_decisions_available(decisions: tuple[c.RouteDecisionV1, ...]) -> None:
    for decision in decisions:
        if decision.source_kind == "official":
            raise EngineError("official_unavailable",
                              "Official gateway is not configured; configure a supported official gateway", 503)
        if decision.source_kind == "byok" and decision.reason != "installed_byok_route":
            raise EngineError("byok_route_not_installed",
                              "BYOK route is not installed; install the model route", 503)
        if decision.source_kind == "unavailable":
            raise EngineError("capability_unavailable",
                              "Requested capability source is unavailable; configure or install a route", 503)
