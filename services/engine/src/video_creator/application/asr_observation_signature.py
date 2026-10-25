"""OS-vault-keyed commitment for one real settled ASR observation.

Threat model: this authenticates the journal facts against a key held in the OS
vault. A process that can read that key (same OS user) can still forge evidence;
this prevents DB/file-only tampering and application mistakes, not a compromised
installation account. The signature is not a remote attestation.
"""

import hashlib
import hmac
import json

from video_creator.application.engine import digest
from video_creator.domain.errors import EngineError
from video_creator.infrastructure.owner_secret import OwnerSecretStore

BINDING = 'asr-observation'
METADATA_PREFIX = 'asr_observation_signature:'
FORMAT = 'asr-observation-commitment-v1'


def _secret(engine, *, create: bool) -> bytes:
    store = OwnerSecretStore(engine.db.data_dir, engine.instance_id)
    try:
        return store.resolve(BINDING)
    except (EngineError, OSError) as error:
        if isinstance(error, EngineError) and error.code not in {'owner_secret_unavailable', 'owner_secret_denied'}:
            raise
        if not create:
            raise EngineError('asr_observation_signature_unavailable',
                              'The ASR observation signing key is unavailable', 503) from error
        try:
            store.create(BINDING)
        except EngineError as failure:
            raise EngineError('asr_observation_signature_unavailable',
                              'The ASR observation signing key is unavailable', 503) from failure
        return store.resolve(BINDING)


def commitment(*, allocation, staging_sha256: str, staging_size: int, observation) -> str:
    execution = observation.result_json['runtime']['execution_identity']
    body = {
        'format': FORMAT,
        'operation_id': allocation.operation_id,
        'run_id': allocation.run_id,
        'step_key': allocation.step_key,
        'input_sha256': allocation.input_sha256,
        'dedupe_key': allocation.dedupe_key,
        'route_sha256': allocation.route_sha256,
        'binding_sha256': allocation.binding_sha256,
        'resource_manifest_sha256': allocation.resource_manifest_sha256,
        'runtime_manifest_sha256': allocation.runtime_manifest_sha256,
        'staging_sha256': staging_sha256,
        'staging_size': staging_size,
        'result_sha256': digest(json.dumps(observation.result_json, ensure_ascii=False, sort_keys=True, separators=(',', ':'))),
        'execution_identity_sha256': digest(json.dumps(execution, ensure_ascii=False, sort_keys=True,
                                                       separators=(',', ':'))),
    }
    return json.dumps(body, ensure_ascii=False, sort_keys=True, separators=(',', ':'))


def sign_observation(engine, *, allocation, staging_sha256: str, staging_size: int, observation) -> None:
    body = commitment(allocation=allocation, staging_sha256=staging_sha256,
                      staging_size=staging_size, observation=observation)
    signature = hmac.new(_secret(engine, create=True), body.encode('utf-8'), hashlib.sha256).hexdigest()
    record = json.dumps({'format': FORMAT, 'commitment': body, 'signature': signature},
                        ensure_ascii=False, sort_keys=True, separators=(',', ':'))
    with engine.db.transaction() as connection:
        old = connection.execute('SELECT value FROM metadata WHERE key=?',
                                 (METADATA_PREFIX + allocation.operation_id,)).fetchone()
        if old is not None and old[0] != record:
            raise EngineError('asr_observation_signature_conflict',
                              'Original ASR observation commitment is immutable', 409)
        connection.execute('INSERT OR IGNORE INTO metadata(key,value) VALUES(?,?)',
                           (METADATA_PREFIX + allocation.operation_id, record))


def verify_observation(engine, *, operation_id: str, allocation, staging_sha256: str,
                       staging_size: int, observation) -> None:
    with engine.db.connect_readonly() as connection:
        row = connection.execute('SELECT value FROM metadata WHERE key=?',
                                 (METADATA_PREFIX + operation_id,)).fetchone()
    if row is None or type(row[0]) is not str:
        raise EngineError('asr_observation_signature_missing',
                          'No OS-vault-keyed commitment exists for this settled ASR observation', 409)
    try:
        record = json.loads(row[0])
        if (type(record) is not dict or set(record) != {'format', 'commitment', 'signature'}
                or record['format'] != FORMAT or type(record['commitment']) is not str
                or type(record['signature']) is not str or len(record['signature']) != 64):
            raise ValueError('shape')
        expected = commitment(allocation=allocation, staging_sha256=staging_sha256,
                              staging_size=staging_size, observation=observation)
        if not hmac.compare_digest(record['commitment'], expected):
            raise ValueError('commitment')
        signature = hmac.new(_secret(engine, create=False), expected.encode('utf-8'), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(record['signature'], signature):
            raise ValueError('signature')
    except EngineError:
        raise
    except (ValueError, TypeError, KeyError):
        raise EngineError('asr_observation_signature_invalid',
                          'ASR observation commitment or OS-vault signature is invalid', 409) from None
