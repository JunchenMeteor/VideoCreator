"""P1-3 observation commitment: sign/verify, no key creation on verify, tamper/replay."""
import json

import pytest

from video_creator.application.asr_observation_signature import (
    METADATA_PREFIX,
    commitment,
    sign_observation,
    verify_observation,
)
from video_creator.application.engine import EngineService
from video_creator.domain import contracts as c
from video_creator.domain.contracts import Money
from video_creator.domain.errors import EngineError
from video_creator.domain.registered_production import AsrResultAllocation


def _allocation(operation_id='operation-test'):
    return AsrResultAllocation(
        operation_id=operation_id, run_id='run-test', step_key='bundle-actual-asr',
        input_sha256='a' * 64, dedupe_key='bundle-asr-run-test', route_sha256='b' * 64,
        attempt_id='attempt-test', staging_id='staging-test', binding_sha256='c' * 64,
        resource_manifest_sha256='d' * 64, runtime_manifest_sha256='e' * 64)


def _observation():
    identity = c.AlignmentExecutionIdentity(
        method_id='local.asr.test', tool='faster-whisper', tool_version='test',
        model_id='model-test', model_file_sha256={'model.bin': 'f' * 64},
        resource_manifest_sha256='d' * 64, configuration_sha256='1' * 64,
        compute_type='cpu', device='cpu', operating_system='windows', architecture='x86_64')
    return c.OperationObservation(status='succeeded', actual_cost=Money(amount='0'),
                                  cost_evidence='confirmed_no_charge',
                                  result_json={'runtime': {'execution_identity': identity.model_dump(mode='json')}})


def test_signed_observation_is_accepted(tmp_path):
    engine = EngineService(tmp_path)
    allocation, observation = _allocation(), _observation()
    sign_observation(engine, allocation=allocation, staging_sha256='2' * 64,
                     staging_size=10, observation=observation)
    verify_observation(engine, operation_id=allocation.operation_id, allocation=allocation,
                       staging_sha256='2' * 64, staging_size=10, observation=observation)


def test_missing_and_tampered_commitment_are_rejected(tmp_path):
    engine = EngineService(tmp_path)
    allocation, observation = _allocation(), _observation()
    sign_observation(engine, allocation=allocation, staging_sha256='2' * 64,
                     staging_size=10, observation=observation)
    with pytest.raises(EngineError) as missing:
        verify_observation(engine, operation_id='operation-other', allocation=allocation,
                           staging_sha256='2' * 64, staging_size=10, observation=observation)
    assert missing.value.code == 'asr_observation_signature_missing'

    with pytest.raises(EngineError) as tampered:
        verify_observation(engine, operation_id=allocation.operation_id, allocation=allocation,
                           staging_sha256='3' * 64, staging_size=10, observation=observation)
    assert tampered.value.code == 'asr_observation_signature_invalid'


def test_verify_never_creates_a_key(tmp_path):
    engine = EngineService(tmp_path)
    allocation, observation = _allocation(), _observation()
    matching = commitment(allocation=allocation, staging_sha256='2' * 64,
                          staging_size=10, observation=observation)
    with engine.db.transaction() as connection:
        connection.execute('INSERT INTO metadata(key,value) VALUES(?,?)',
                           (METADATA_PREFIX + allocation.operation_id,
                            json.dumps({'format': 'asr-observation-commitment-v1',
                                        'commitment': matching, 'signature': '0' * 64})))
    with pytest.raises(EngineError) as unavailable:
        verify_observation(engine, operation_id=allocation.operation_id, allocation=allocation,
                           staging_sha256='2' * 64, staging_size=10, observation=observation)
    assert unavailable.value.code == 'asr_observation_signature_unavailable'
    from video_creator.infrastructure.owner_secret import OwnerSecretStore
    with pytest.raises(EngineError):
        # The verification attempt must not have created the signing secret.
        OwnerSecretStore(engine.db.data_dir, engine.instance_id).resolve('asr-observation')
