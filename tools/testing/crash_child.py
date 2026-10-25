"""Pause at real persistence boundaries so the test parent can kill this child."""

import argparse
import json
import os
import time
from pathlib import Path

from video_creator.application.assets import AssetService
from video_creator.application.engine import EngineService, digest
from video_creator.domain.contracts import (
    AssetCandidate,
    CapabilityRoute,
    ExecutionPolicy,
    Money,
    OperationIntent,
    ProductionRequest,
)


def pause(**receipt):
    print(json.dumps(receipt, ensure_ascii=False), flush=True)
    while True:
        time.sleep(0.1)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("phase", choices=["dispatch", "step", "object"])
    parser.add_argument("data_dir", type=Path)
    args = parser.parse_args()
    engine = EngineService(args.data_dir, clock=lambda: 1_000_000)
    if args.phase == "object":
        assets = AssetService(engine)
        staged = assets.stage_bytes("local-user", b'{"public":true}', "application/json")
        candidate = AssetCandidate(**staged, source="test-self-created", rights="owned")
        original_replace = os.replace

        def boundary_replace(source, target):
            original_replace(source, target)
            if Path(target).parent.name == "Objects":
                pause(phase="object", candidate=candidate.model_dump(mode="json"), boundary="actual object committed before asset database")

        os.replace = boundary_replace
        assets.import_asset("local-user", candidate)
        raise AssertionError("Parent must kill at object commit before this returns")
    engine.authorize_budget_group("test-shared", Money(amount="0.2"))
    engine.register_route(CapabilityRoute(route_id="nonbillable-test", capability="text", source="owned_local",
                          destination="local:synthetic", verified=True, max_operation_cost=Money(amount="0.2"), cost_rule_version="synthetic-v1"))
    accepted = engine.accept_production("local-user", "one", ProductionRequest(goal="public test", policy=ExecutionPolicy(
        budget_group_id="test-shared", max_cost=Money(amount="0.2"), allowed_provider_routes=("nonbillable-test",))))
    lease = engine.acquire_run("child", lease_seconds=1, run_id=accepted.run_id)
    engine.begin_step(lease, "creative", digest("public input"))
    if args.phase == "dispatch":
        operation = engine.prepare_operation(lease, OperationIntent(step_key="creative", dedupe_key="one",
                                             input_sha256=digest("public prompt"), route_id="nonbillable-test", reserved_cost=Money(amount="0.2")))
        engine.claim_operation(lease, operation["id"])
        pause(phase="dispatch", run_id=accepted.run_id, production_id=accepted.production_id,
              boundary="actual persisted dispatch intent; upstream acceptance only simulated; no network")
    engine.complete_step(lease, "creative", result_json={"revision_ref": "synthetic-not-generated"})
    pause(phase="step", run_id=accepted.run_id, production_id=accepted.production_id,
          boundary="actual Step success before nonexistent Flow checkpoint")


if __name__ == "__main__":
    main()
