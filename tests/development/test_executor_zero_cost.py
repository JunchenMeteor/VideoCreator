"""Zero-cost operation failures must never swallow a real dispatch error.

Only an `owned_local`, credential-free, `local:`-destination, zero-cost route can
be proven not to have dispatched. Every other route - including a zero-cost
`owned_remote` one, an `owned_local` route carrying a credential or an HTTPS
destination, and any non-zero-cost route - may already have transmitted the
request, so its driver failure must stay `OperationObservation(status="unknown")`
with one recorded observation and no retry.

This is a process-internal seam on the real `OperationExecutor` with a fake engine
and route; it invokes no provider and no network. The P1 review (`RV-LocalChainRealRunFixes`)
asked for exactly these four reverse conditions after the executor fix.
"""

from __future__ import annotations

import json
from types import SimpleNamespace

import pytest
from video_creator.application.executor import OperationExecutor
from video_creator.domain.contracts import Money, OperationIntent, OperationObservation
from video_creator.domain.errors import EngineError


class FakeEngine:
    def __init__(self, route):
        self.route = route
        self.observed = []
        self.claimed = 0

    def configured_route(self, route_id):
        return self.route

    def prepare_operation(self, lease, intent):
        return {'id': 'operation-zero-cost-fixture', 'settled': False, 'status': 'prepared'}

    def heartbeat(self, lease, lease_seconds=300):
        return lease

    def claim_operation(self, lease, operation_id):
        self.claimed += 1
        return SimpleNamespace(route=self.route)

    def observe_operation(self, lease, operation_id, observation):
        self.observed.append(observation)


def route(*, source='owned_local', credential_ref=None,
          destination='local:ffmpeg-owned-edit', cost='0'):
    return SimpleNamespace(cost_rule_version='local-zero-cost-v1', source=source,
                           credential_ref=credential_ref, destination=destination,
                           max_operation_cost=Money(amount=cost))


def failure(permit, secret):
    raise EngineError('media_path_denied', 'Media path is outside controlled instance.', 403)


def success(permit, secret):
    return OperationObservation(status='succeeded')


def execute(route_value, driver):
    engine = FakeEngine(route_value)
    executor = OperationExecutor(engine, vault=SimpleNamespace(resolve=lambda ref: None))
    lease = SimpleNamespace(run_id='run-zero-cost-fixture')
    intent = OperationIntent(step_key='production-local-shot-1', dedupe_key='zero-cost-fixture',
                             input_sha256='a' * 64, route_id='fixture-route',
                             reserved_cost=Money(amount='0'))
    try:
        observation = executor.execute(lease, intent, driver)
        outcome = {'outcome': 'returned', 'status': observation.status,
                   'observed_rows': len(engine.observed)}
    except EngineError as error:
        outcome = {'outcome': 'raised', 'code': error.code, 'status_code': error.status_code,
                   'observed_rows': len(engine.observed)}
    outcome['observed_statuses'] = [row.status for row in engine.observed]
    return outcome


def test_local_zero_cost_failure_reraises_the_original_error() -> None:
    observed = execute(route(), failure)
    assert observed['outcome'] == 'raised', json.dumps(observed)
    assert observed['code'] == 'media_path_denied'
    assert observed['status_code'] == 403
    assert observed['observed_rows'] == 0, (
        'a provably local zero-cost failure must not fabricate an unknown reconciliation')
    assert execute(route(), success)['status'] == 'succeeded'


@pytest.mark.parametrize(('label', 'route_value'), [
    ('zero_cost_owned_remote', route(source='owned_remote',
                                     destination='https://provider.example', cost='0')),
    ('owned_local_with_credential', route(credential_ref='credential-1')),
    ('owned_local_with_https_destination', route(destination='https://remote.example')),
    ('non_zero_local_cost', route(cost='1')),
])
def test_only_provably_local_zero_cost_failures_reraise(label, route_value) -> None:
    observed = execute(route_value, failure)
    assert observed['outcome'] == 'returned', (
        f'{label}: the failure must stay unknown, not re-raise: ' + json.dumps(observed))
    assert observed['status'] == 'unknown', json.dumps(observed)
    assert observed['observed_rows'] == 1, json.dumps(observed)
    assert observed['observed_statuses'] == ['unknown']
