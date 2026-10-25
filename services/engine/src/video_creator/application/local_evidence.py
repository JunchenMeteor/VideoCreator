"""Local self-issued evidence admission (ADR0082 B').

One installation, one self-issued issuer, one OS-vault key, one bounded policy:

* the product authorization channel only approves a ``local_evidence_policy``
  *range* (instance, owner, project, method profile, validity) and writes an
  audit plus a one-shot receipt;
* this module's ``evidence_admin_install`` runs in a short-lived child process
  that never assembles Owner services, never starts a listener and never holds an
  execution identity. It reads a genuine settled ASR observation from the
  instance ledger, copies that child-observed ``execution_identity`` verbatim,
  and installs the policy/qualification/not-performed declaration with HMAC
  signatures from the OS vault key;
* the normal API/worker processes re-open the same key from the OS vault at
  trusted startup, so a restarted process resolves the policy. No request body,
  environment value or configuration file can supply the key.

The policy is explicitly weaker evidence: ``precision=not_measured``, no
corpus/P95/listener/arbitration fields, fixed limitations and a disclosure hash.
It never installs a ``MethodBenchmarkReport`` and never claims a measurement.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
from pathlib import Path

from pydantic import ValidationError

from video_creator.application.bundles import strict_json
from video_creator.application.engine import EngineService
from video_creator.application.evidence import (
    PersistentEvidenceRegistry,
    check_evidence_record,
    validate_self_issued_benchmark,
)
from video_creator.domain import contracts as c
from video_creator.domain.errors import EngineError
from video_creator.domain.evidence import EvidenceApproval
from video_creator.infrastructure.credentials import CredentialVault
from video_creator.infrastructure.owner_identity import inspect_owner_directory

ISSUER_PREFIX = 'local-selfissued-'
AUTHORITY_PREFIX = 'local-selfissued-authority-'
PROFILE_ID = 'whisper-word-estimate-local-v1'
PROFILE_REVISION = 1
KEY_ID = 'local-evidence-key-v1'
TIMESTAMP_METHOD = 'whisper_word_estimate_not_forced_alignment'
REQUIRED_CHECKS = ('local_transcript_observation', 'local_alignment_method_scope',
                   'local_subtitle_serialization')
POLICY_FILENAME = 'LocalEvidenceIssuance.json'
INSTALLATION_FILENAME = 'LocalEvidenceInstallation.json'
RECEIPT_FORMAT = 'local-evidence-issuance-v1'
INSTALLATION_FORMAT = 'local-evidence-installation-v1'
RECEIPT_CREDENTIAL_PREFIX = 'evidence_local_issuer:'
RECEIPT_CONSUMED_METADATA_PREFIX = 'local_evidence_receipt:'
RESOURCE_MANIFEST_METADATA_KEY = 'local_evidence_resource_manifest'
DISCLOSURE_FORMAT = 'local-selfissued-disclosure-v1'
DISCLOSURE_LINES = (
    '本地自签、未做精度实测',
    '时间戳来自 whisper 词级估计，非强制对齐',
    '不构成第三方认证或官方合规',
    '此证据仅本机实例有效，不跨实例复用',
    '未启用时语音作品会被拒绝（alignment_required），静音作品不受影响',
)
_MAX_FILE_BYTES = 64 * 1024
_POLICY_LIFETIME_US = 30 * 86400_000_000
_INSTALL_WINDOW_US = 10 * 60_000_000
_DURATION_MARGIN_US = 300_000_000
_AUTHORIZATION_TABLES = ('production_authorization_policies', 'production_admissions',
                         'daily_project_authorizations', 'execution_registrations')


def _canonical(value) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode('utf-8')).hexdigest()


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _denied(code: str, message: str, status: int) -> EngineError:
    return EngineError(code, message, status)


def issuer_for(instance_id: str) -> str:
    return ISSUER_PREFIX + instance_id


def authority_for(instance_id: str) -> str:
    return AUTHORITY_PREFIX + instance_id


def disclosure_sha256() -> str:
    return _sha256(_canonical({'format': DISCLOSURE_FORMAT, 'lines': list(DISCLOSURE_LINES)}))


DISCLOSURE_SHA256 = disclosure_sha256()


def local_evidence_scope(*, instance_id: str, owner_subject: str, project_id: str,
                         expires_at_us: int) -> dict:
    """The exact approved range; it carries no document bytes and no secret."""
    return {
        'kind': 'local_evidence_policy',
        'instance_id': instance_id,
        'owner_subject': owner_subject,
        'project_id': project_id,
        'method_profile': PROFILE_ID,
        'issuer': issuer_for(instance_id),
        'authority_ref': authority_for(instance_id),
        'expires_at_us': expires_at_us,
    }


def local_evidence_configuration_sha256(instance_id: str, issuer: str, key: bytes) -> str:
    return _sha256(_canonical({'format': 'local-selfissued-evidence-config-v1',
                               'instance_id': instance_id, 'issuer': issuer,
                               'key_fingerprint': _sha256_bytes(key)[:16]}))


# --------------------------------------------------------------------- OS vault key


def _key_identifier(instance_id: str) -> str:
    return RECEIPT_CREDENTIAL_PREFIX + instance_id


def load_local_evidence_key(instance_id: str, *, create: bool = False) -> tuple[str, bytes] | None:
    """Read (and optionally create once) the 256-bit issuer key from the OS vault."""
    vault = CredentialVault()
    identifier = _key_identifier(instance_id)
    stored = vault.load_secret(identifier)
    if stored is None and create:
        key = secrets.token_bytes(32)
        vault.store_secret(identifier, key.hex())
        return issuer_for(instance_id), key
    if stored is None:
        return None
    try:
        key = bytes.fromhex(stored)
    except (TypeError, ValueError):
        raise _denied('local_evidence_key_invalid',
                      'The local evidence issuer key is not a hexadecimal secret', 503) from None
    if len(key) < 32:
        raise _denied('local_evidence_key_invalid',
                      'The local evidence issuer key is shorter than 256 bits', 503)
    return issuer_for(instance_id), key


def _rooted_registry(engine: EngineService, issuer: str, key: bytes) -> PersistentEvidenceRegistry:
    return PersistentEvidenceRegistry(
        engine, trust_roots={issuer: key},
        trusted_configuration_sha256=local_evidence_configuration_sha256(engine.instance_id, issuer, key),
        minimum_registry_revision=0)


def install_local_evidence_trust(engine: EngineService) -> bool:
    """Trusted startup hook: root this process only when the OS vault holds the key.

    A weak/unavailable OS vault or an absent key keeps today's unconfigured
    registry (`alignment_required`), never a permissive fallback.
    """
    try:
        found = load_local_evidence_key(engine.instance_id)
    except EngineError as error:
        if error.code in {'secure_vault_unavailable', 'credential_unavailable'}:
            return False
        raise
    if found is None:
        return False
    issuer, key = found
    engine.configure_evidence_registry(_rooted_registry(engine, issuer, key))
    return True


def local_evidence_resource_manifest_hashes(engine: EngineService) -> frozenset[str]:
    """The exact child-observed ASR resource manifest admitted by a signed policy.

    This is what a publication validator needs in its trusted set. The value is
    never read from configuration, argv, environment or a request: it comes from
    the qualification rows this installation signed, and is accepted only while
    the admitted qualification still matches the recorded content hash.
    """
    try:
        with engine.db.connect_readonly() as connection:
            row = connection.execute('SELECT value FROM metadata WHERE key=?',
                                     (RESOURCE_MANIFEST_METADATA_KEY,)).fetchone()
            if row is None or type(row[0]) is not str:
                return frozenset()
            record = json.loads(row[0])
            if type(record) is not dict or set(record) != {
                    'resource_manifest_sha256', 'qualification_content_sha256', 'qualification_id',
                    'qualification_revision', 'issuer', 'policy_ref', 'recorded_at_us'}:
                return frozenset()
            admitted = connection.execute(
                "SELECT body FROM alignment_admissions WHERE kind='qualification' "
                'AND admission_id=? AND revision=?',
                (record['qualification_id'], record['qualification_revision'])).fetchone()
    except (OSError, TypeError, ValueError, EngineError):
        return frozenset()
    if admitted is None:
        return frozenset()
    try:
        document = c.MethodQualificationRef.model_validate_json(admitted[0])
    except (ValidationError, TypeError):
        return frozenset()
    resource_sha256 = record['resource_manifest_sha256']
    if (type(resource_sha256) is not str or len(resource_sha256) != 64
            or any(character not in '0123456789abcdef' for character in resource_sha256)
            or type(record['issuer']) is not str
            or not record['issuer'].startswith(ISSUER_PREFIX)
            or document.issuer != record['issuer']
            or document.content_sha256 != record['qualification_content_sha256']
            or document.execution_identity.resource_manifest_sha256 != resource_sha256):
        return frozenset()
    return frozenset({resource_sha256})


# ------------------------------------------------------------------ receipt / completion


def _control_folder(engine: EngineService) -> Path:
    folder = Path(engine.db.data_dir) / 'Control'
    if folder.is_symlink() or folder.is_junction() or not folder.is_dir():
        raise _denied('local_evidence_receipt_unwritten',
                      'The protected Control directory is unavailable', 503)
    return folder


def receipt_path(engine: EngineService) -> Path:
    return _control_folder(engine) / POLICY_FILENAME


def _pending_receipt_path(engine: EngineService) -> Path:
    return _control_folder(engine) / (POLICY_FILENAME + '.pending')


def installation_path(engine: EngineService) -> Path:
    return _control_folder(engine) / INSTALLATION_FILENAME


def _canonical_file(body: dict) -> bytes:
    data = _canonical(body).encode('utf-8') + b'\n'
    if len(data) > _MAX_FILE_BYTES:
        raise _denied('local_evidence_receipt_unwritten',
                      'The local evidence receipt exceeds its fixed document bound', 503)
    return data


def build_receipt(*, request_scope: dict, authorization_id: str, scope_sha256: str,
                  audit_sha256: str, receipt_id: str, approved_at_us: int,
                  install_by_us: int, origin: str, nonce_fingerprint: str,
                  session_secret_fingerprint: str) -> dict:
    return {
        'format': RECEIPT_FORMAT,
        'receipt_id': receipt_id,
        'authorization_id': authorization_id,
        'instance_id': request_scope['instance_id'],
        'issuer': request_scope['issuer'],
        'authority_ref': request_scope['authority_ref'],
        'owner_subject': request_scope['owner_subject'],
        'project_id': request_scope['project_id'],
        'method_profile': request_scope['method_profile'],
        'scope': request_scope,
        'scope_sha256': scope_sha256,
        'approved_at_us': approved_at_us,
        'expires_at_us': request_scope['expires_at_us'],
        'install_by_us': install_by_us,
        'audit_sha256': audit_sha256,
        'origin': origin,
        'nonce_fingerprint': nonce_fingerprint,
        'session_secret_fingerprint': session_secret_fingerprint,
    }


def _validated_receipt(raw: bytes) -> dict:
    if len(raw) > _MAX_FILE_BYTES:
        raise _denied('local_evidence_receipt_invalid', 'The receipt exceeds its fixed bound', 403)
    try:
        body = strict_json(raw)
    except (EngineError, TypeError):
        raise _denied('local_evidence_receipt_invalid', 'The receipt is not canonical JSON', 403) from None
    required = {'format', 'receipt_id', 'authorization_id', 'instance_id', 'issuer', 'authority_ref',
                'owner_subject', 'project_id', 'method_profile', 'scope', 'scope_sha256',
                'approved_at_us', 'expires_at_us', 'install_by_us', 'audit_sha256', 'origin',
                'nonce_fingerprint', 'session_secret_fingerprint'}
    if type(body) is not dict or set(body) != required or body.get('format') != RECEIPT_FORMAT:
        raise _denied('local_evidence_receipt_invalid', 'The receipt fields are not the fixed issuance grammar', 403)
    scope = body.get('scope')
    if (type(scope) is not dict or _sha256(_canonical(scope)) != body.get('scope_sha256')
            or scope.get('kind') != 'local_evidence_policy' or scope != {
                'kind': 'local_evidence_policy', 'instance_id': body['instance_id'],
                'owner_subject': body['owner_subject'], 'project_id': body['project_id'],
                'method_profile': body['method_profile'], 'issuer': body['issuer'],
                'authority_ref': body['authority_ref'], 'expires_at_us': body['expires_at_us']}):
        raise _denied('local_evidence_receipt_invalid', 'The receipt scope differs from its approved range', 403)
    return body


def read_receipt(path: str | Path) -> tuple[dict, bytes]:
    candidate = Path(path)
    if (not candidate.is_absolute() or candidate.is_symlink() or candidate.is_junction()
            or not candidate.is_file()):
        raise _denied('local_evidence_receipt_invalid', 'The receipt must be one fixed local file', 403)
    raw = candidate.read_bytes()
    return _validated_receipt(raw), raw


def _consumed_record(engine: EngineService, receipt_id: str) -> dict | None:
    with engine.db.connect_readonly() as connection:
        row = connection.execute('SELECT value FROM metadata WHERE key=?',
                                 (RECEIPT_CONSUMED_METADATA_PREFIX + receipt_id,)).fetchone()
    return json.loads(row[0]) if row else None


def _read_completion(engine: EngineService, receipt_id: str) -> dict | None:
    path = installation_path(engine)
    if not path.is_file() or path.is_symlink() or path.is_junction():
        return None
    try:
        body = strict_json(path.read_bytes())
    except (EngineError, TypeError):
        return None
    return body if isinstance(body, dict) and body.get('receipt_id') == receipt_id else None


# ------------------------------------------------------------------ observation facts


def _identifier(value: str) -> str:
    """A bounded contract identifier from a real observed codec/container token."""
    cleaned = ''.join(character if character.isalnum() or character in '_.:-' else '-'
                      for character in str(value))
    return cleaned[:128] or 'unknown'


def _settled_observation(engine: EngineService, *, owner_subject: str, project_id: str) -> dict:
    with engine.db.connect_readonly() as connection:
        rows = connection.execute(
            'SELECT o.id, o.observation_json FROM operations o '
            'JOIN productions p ON p.id=o.production_id '
            "WHERE o.status='succeeded' AND o.settled=1 AND p.owner=? AND p.project_id=? "
            'ORDER BY o.created_at_us DESC, o.id DESC', (owner_subject, project_id)).fetchall()
    for operation_id, raw in rows:
        if type(raw) is not str:
            continue
        try:
            observation = c.OperationObservation.model_validate_json(raw)
        except ValidationError:
            continue
        result = observation.result_json
        if not isinstance(result, dict) or result.get('kind') != 'actual_transcript':
            continue
        if result.get('timestamp_method') != TIMESTAMP_METHOD:
            continue
        runtime = result.get('runtime')
        identity = runtime.get('execution_identity') if isinstance(runtime, dict) else None
        if not isinstance(identity, dict):
            continue
        try:
            execution = c.AlignmentExecutionIdentity.model_validate(identity)
        except ValidationError:
            continue
        language = result.get('language')
        duration = result.get('duration_us')
        audio_sha256 = result.get('input_audio_sha256')
        provenance = result.get('audio_provenance')
        if (type(language) is not str or not language or type(duration) is not int or duration <= 0
                or type(audio_sha256) is not str or len(audio_sha256) != 64
                or not isinstance(provenance, dict)):
            continue
        with engine.db.connect_readonly() as connection:
            asset = connection.execute(
                'SELECT media_type FROM assets WHERE owner=? AND sha256=? ORDER BY id LIMIT 1',
                (owner_subject, audio_sha256)).fetchone()
        if asset is None or type(asset[0]) is not str or not asset[0]:
            continue
        container = provenance.get('container_format')
        codec = provenance.get('audio_codec')
        rate = provenance.get('resampled_sample_rate')
        transformations = tuple(item for item in (
            'local_decode:' + _identifier(container) if container else None,
            'local_decode_codec:' + _identifier(codec) if codec else None,
            'local_resample:' + _identifier(rate) + '-mono' if rate else None,
            'local_asr:faster-whisper',
        ) if item)
        try:
            applicability = c.AlignmentApplicability(
                languages=(language,), input_media_types=(asset[0],),
                transformations=transformations, maximum_duration_us=duration + _DURATION_MARGIN_US,
                units='utterance')
        except ValidationError:
            continue
        return {'operation_id': operation_id, 'execution_identity': execution,
                'applicability': applicability, 'language': language, 'duration_us': duration,
                'input_audio_sha256': audio_sha256, 'media_type': asset[0]}
    raise _denied('local_evidence_observation_missing',
                  'No real settled local whisper observation exists for this owner/project; '
                  'run one real transcription before installing self-issued evidence', 409)


# ------------------------------------------------------------------ document construction


def _profile_sha256(issuer: str) -> str:
    return _sha256(_canonical({
        'format': 'local-selfissued-profile-v1', 'profile_id': PROFILE_ID,
        'profile_revision': PROFILE_REVISION, 'issuer': issuer,
        'timestamp_method': TIMESTAMP_METHOD, 'units': 'utterance',
        'precision': 'not_measured', 'criterion_version_ref': 'alignment-unit-max-p95-200ms-v1'}))


def _record(model_body: dict) -> dict:
    body = dict(model_body)
    body.pop('content_sha256', None)
    body['content_sha256'] = _sha256(_canonical(body))
    return body


def _sign(key: bytes, approval_body: dict) -> str:
    unsigned = dict(approval_body)
    unsigned.pop('signature', None)
    return hmac.new(key, _canonical(unsigned).encode('utf-8'), hashlib.sha256).hexdigest()


def _approval(key: bytes, *, issuer: str, approval_id: str, document_sha256: str,
              benchmark_sha256: str) -> EvidenceApproval:
    body = {'issuer': issuer, 'approval_id': approval_id, 'document_sha256': document_sha256,
            'benchmark_content_sha256': benchmark_sha256}
    body['signature'] = _sign(key, body)
    return EvidenceApproval.model_validate(body)


def _next_revision(engine: EngineService, section: str) -> int:
    with engine.db.connect_readonly() as connection:
        row = connection.execute(
            "SELECT MAX(CAST(revision AS INTEGER)) FROM alignment_admissions "
            "WHERE kind='policy' AND admission_id LIKE ?",
            ('local-selfissued-policy-' + section + '-%',)).fetchone()
    return 1 if row is None or row[0] is None else int(row[0]) + 1


def _operation_reference_count(engine: EngineService) -> int:
    with engine.db.connect_readonly() as connection:
        return int(connection.execute('SELECT COUNT(*) FROM operations').fetchone()[0])


def _build_documents(engine: EngineService, *, issuer: str, authority: str, key: bytes,
                     owner_subject: str, project_id: str, facts: dict,
                     valid_from_us: int, expires_at_us: int) -> dict:
    section = project_id
    revision = _next_revision(engine, section)
    benchmark_id = ('local-selfissued-benchmark-not-performed-' + engine.instance_id
                    + '-' + str(revision))
    benchmark = c.LocalSelfIssuedBenchmarkV1.model_validate(_record({
        'schema_version': c.V03_SCHEMA_VERSION,
        'evaluation_scope': 'capability_benchmark_not_performed',
        'report_id': benchmark_id,
        'execution_identity': facts['execution_identity'].model_dump(mode='json'),
        'applicability': facts['applicability'].model_dump(mode='json'),
        'authority_ref': authority,
        'precision_claim': 'not_measured',
        'independent_reference': 'none',
        'limitations': list(c.LOCAL_SELF_ISSUED_BENCHMARK_LIMITATIONS),
        'disclosure_sha256': DISCLOSURE_SHA256,
    }))
    validate_self_issued_benchmark(benchmark)

    qualification_id = 'local-selfissued-qualification-' + section + '-' + str(revision)
    qualification_approval_id = ('local-selfissued-approval-' + section + '-' + str(revision)
                                 + '-qualification')
    qualification = c.MethodQualificationRef.model_validate(_record({
        'qualification_id': qualification_id,
        'revision': revision,
        'profile_id': PROFILE_ID,
        'profile_revision': PROFILE_REVISION,
        'profile_sha256': _profile_sha256(issuer),
        'execution_identity': facts['execution_identity'].model_dump(mode='json'),
        'applicability': facts['applicability'].model_dump(mode='json'),
        'benchmark_report_ref': c.EvidenceReportRef(
            report_id=benchmark.report_id, schema_version=c.V03_SCHEMA_VERSION,
            evaluation_scope='capability_benchmark_not_performed',
            content_sha256=benchmark.content_sha256).model_dump(mode='json'),
        'criterion_version_ref': 'alignment-unit-max-p95-200ms-v1',
        'authority_ref': authority,
        'issuer': issuer,
        'approval_refs': [_sha256(issuer + ':' + qualification_approval_id)],
        'valid_from_us': valid_from_us,
        'expires_at_us': expires_at_us,
    }))
    check_evidence_record(qualification)
    qualification_approval = _approval(key, issuer=issuer,
                                       approval_id=qualification_approval_id,
                                       document_sha256=qualification.content_sha256,
                                       benchmark_sha256=benchmark.content_sha256)

    policy_id = 'local-selfissued-policy-' + section + '-' + str(revision)
    policy_approval_id = 'local-selfissued-approval-' + section + '-' + str(revision) + '-policy'
    policy = c.EvidencePolicyRevision.model_validate(_record({
        'policy_id': policy_id,
        'revision': revision,
        'owner_subject': owner_subject,
        'project_id': project_id,
        'alignment_evidence_policy': 'qualified_method_runtime_v1',
        'alignment_requirement': 'utterance_verified',
        'qualification_ref': qualification.model_dump(mode='json'),
        'required_checks': list(REQUIRED_CHECKS),
        'preauthorized': True,
        'issuer': issuer,
        'approval_refs': [_sha256(issuer + ':' + policy_approval_id)],
        'valid_from_us': valid_from_us,
        'expires_at_us': expires_at_us,
    }))
    check_evidence_record(policy)
    policy_approval = _approval(key, issuer=issuer, approval_id=policy_approval_id,
                                document_sha256=policy.content_sha256,
                                benchmark_sha256=benchmark.content_sha256)
    return {'revision': revision, 'benchmark': benchmark, 'qualification': qualification,
            'policy': policy, 'qualification_approval': qualification_approval,
            'policy_approval': policy_approval}


# ------------------------------------------------------------------ evidence-admin install


def evidence_admin_install(*, data_dir: str | Path, receipt: str | Path) -> dict:
    """One-shot install: receipt -> real observation -> three documents -> install/preauthorize."""
    engine = EngineService(data_dir)
    receipt_body, receipt_raw = read_receipt(receipt)
    receipt_sha256 = _sha256_bytes(receipt_raw)
    if receipt_body['instance_id'] != engine.instance_id:
        raise _denied('local_evidence_instance_conflict',
                      'The receipt belongs to another installation instance', 409)
    now = engine.clock()
    if receipt_body['expires_at_us'] <= now:
        raise _denied('local_evidence_receipt_expired',
                      'The approved local evidence policy window already ended', 409)
    if receipt_body['install_by_us'] <= now:
        raise _denied('local_evidence_receipt_expired',
                      'The receipt install window already ended', 409)
    consumed = _consumed_record(engine, receipt_body['receipt_id'])
    if consumed is not None:
        if consumed.get('receipt_sha256') == receipt_sha256:
            completion = _read_completion(engine, receipt_body['receipt_id']) or {}
            return {'event': 'evidence_admin', 'status': 'already_installed',
                    'receipt_id': receipt_body['receipt_id'],
                    'policy_ref': consumed.get('policy_ref'),
                    'sequences': completion.get('sequences')}
        raise _denied('local_evidence_receipt_consumed',
                      'This receipt identity was already consumed by another issuance', 409)

    # The audit must be the actual approval of this exact scope and receipt.
    audit_path = _control_folder(engine) / 'LocalEvidenceAuthorization.json'
    if not audit_path.is_file() or audit_path.is_symlink() or audit_path.is_junction():
        raise _denied('local_evidence_receipt_invalid', 'The approval audit is unavailable', 403)
    audit_raw = audit_path.read_bytes()
    if _sha256_bytes(audit_raw) != receipt_body['audit_sha256']:
        raise _denied('local_evidence_receipt_invalid', 'The receipt does not bind the current approval audit', 403)
    try:
        audit = strict_json(audit_raw)
    except (EngineError, TypeError):
        raise _denied('local_evidence_receipt_invalid', 'The approval audit is not canonical JSON', 403) from None
    if (type(audit) is not dict or audit.get('format') != 'product-authorization-audit-v1'
            or audit.get('authorization_id') != receipt_body['authorization_id']
            or audit.get('kind') != 'local_evidence_policy'
            or audit.get('decision') != 'approve'
            or audit.get('scope_sha256') != receipt_body['scope_sha256']
            or audit.get('scope') != receipt_body['scope']
            or audit.get('instance_id') != engine.instance_id):
        raise _denied('local_evidence_receipt_invalid',
                      'The approval audit does not describe this receipt range', 403)
    with engine.db.connect_readonly() as connection:
        committed = connection.execute("SELECT value FROM metadata WHERE key=?",
                                       ('local_evidence_authorization_audit',)).fetchone()
    if committed is None or committed[0] != receipt_body['audit_sha256']:
        raise _denied('local_evidence_receipt_invalid',
                      'The approval audit digest is not the committed local evidence digest', 403)

    found = load_local_evidence_key(engine.instance_id, create=True)
    if found is None:  # pragma: no cover - create=True raises or returns a key
        raise _denied('local_evidence_key_unavailable', 'The local evidence issuer key is unavailable', 503)
    issuer, key = found
    if issuer != receipt_body['issuer'] or authority_for(engine.instance_id) != receipt_body['authority_ref']:
        raise _denied('local_evidence_receipt_invalid', 'The receipt names another issuer/authority', 403)
    engine.configure_evidence_registry(_rooted_registry(engine, issuer, key))
    registry = engine.evidence_registry
    capability = registry.administration_capability()

    owner_subject = receipt_body['owner_subject']
    project_id = receipt_body['project_id']
    facts = _settled_observation(engine, owner_subject=owner_subject, project_id=project_id)
    valid_from_us = int(receipt_body['approved_at_us'])
    expires_at_us = min(int(receipt_body['expires_at_us']), valid_from_us + _POLICY_LIFETIME_US)
    if expires_at_us <= now:
        raise _denied('local_evidence_receipt_expired',
                      'The approved policy validity already ended', 409)
    documents = _build_documents(engine, issuer=issuer,
                                 authority=receipt_body['authority_ref'], key=key,
                                 owner_subject=owner_subject, project_id=project_id, facts=facts,
                                 valid_from_us=valid_from_us, expires_at_us=expires_at_us)
    qualification = documents['qualification']
    policy = documents['policy']
    benchmark = documents['benchmark']

    sequences = {}
    sequences['qualification'] = registry.install(capability, qualification, benchmark,
                                                  documents['qualification_approval'])
    sequences['policy'] = registry.install(capability, policy, benchmark,
                                          documents['policy_approval'])
    policy_ref = c.EvidencePolicyRevisionRef(policy_id=policy.policy_id, revision=policy.revision,
                                             content_sha256=policy.content_sha256)
    registry.preauthorize(capability, owner_subject, project_id, policy_ref)
    installed_at_us = engine.clock()
    completion = {
        'format': INSTALLATION_FORMAT,
        'receipt_id': receipt_body['receipt_id'],
        'receipt_sha256': receipt_sha256,
        'audit_sha256': receipt_body['audit_sha256'],
        'instance_id': engine.instance_id,
        'issuer': issuer,
        'authority_ref': receipt_body['authority_ref'],
        'owner_subject': owner_subject,
        'project_id': project_id,
        'method_profile': PROFILE_ID,
        'execution_identity': facts['execution_identity'].model_dump(mode='json'),
        'operation_id': facts['operation_id'],
        'policy_ref': policy_ref.model_dump(mode='json'),
        'qualification_id': qualification.qualification_id,
        'qualification_content_sha256': qualification.content_sha256,
        'benchmark_report_id': benchmark.report_id,
        'benchmark_content_sha256': benchmark.content_sha256,
        'benchmark_evaluation_scope': benchmark.evaluation_scope,
        'precision_claim': benchmark.precision_claim,
        'disclosure_sha256': benchmark.disclosure_sha256,
        'valid_from_us': valid_from_us,
        'expires_at_us': expires_at_us,
        'installed_at_us': installed_at_us,
        'sequences': sequences,
    }
    _write_completion(engine, completion)
    with engine.db.transaction() as connection:
        connection.execute(
            'INSERT INTO metadata(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value',
            (RECEIPT_CONSUMED_METADATA_PREFIX + receipt_body['receipt_id'],
             _canonical({'receipt_sha256': receipt_sha256,
                         'policy_ref': policy_ref.model_dump(mode='json'),
                         'installed_at_us': installed_at_us})))
        # Bind the exact child-observed ASR resource manifest to this signed
        # qualification. Trusted startup reads this only after re-checking the
        # admitted qualification row; the sha never comes from config, argv or a
        # request, and it is never hardcoded.
        connection.execute(
            'INSERT INTO metadata(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value',
            (RESOURCE_MANIFEST_METADATA_KEY,
             _canonical({'resource_manifest_sha256': facts['execution_identity'].resource_manifest_sha256,
                         'qualification_content_sha256': qualification.content_sha256,
                         'qualification_id': qualification.qualification_id,
                         'qualification_revision': qualification.revision,
                         'issuer': issuer,
                         'policy_ref': policy_ref.model_dump(mode='json'),
                         'recorded_at_us': installed_at_us})))
    return {'event': 'evidence_admin', 'status': 'installed',
            'receipt_id': receipt_body['receipt_id'],
            'policy_ref': policy_ref.model_dump(mode='json'),
            'qualification_id': qualification.qualification_id,
            'benchmark_report_id': benchmark.report_id,
            'evaluation_scope': benchmark.evaluation_scope,
            'precision_claim': benchmark.precision_claim,
            'sequences': sequences}


def _write_completion(engine: EngineService, completion: dict) -> None:
    folder = _control_folder(engine)
    target = folder / INSTALLATION_FILENAME
    payload = json.dumps(completion, ensure_ascii=False, sort_keys=True, separators=(',', ':'),
                         allow_nan=False).encode('utf-8') + b'\n'
    if len(payload) > _MAX_FILE_BYTES:
        raise _denied('local_evidence_install_unwritten',
                      'The installation record exceeds its fixed document bound', 503)
    try:
        if target.is_symlink() or target.is_junction():
            raise OSError('The installation record cannot cross links')
        if target.exists():
            existing = target.read_bytes()
            if existing == payload:
                return
            if len(existing) > _MAX_FILE_BYTES:
                raise OSError('The previous installation record exceeds its fixed bound')
            aborted = folder / ('LocalEvidenceInstallation.aborted-'
                                + hashlib.sha256(existing).hexdigest() + '.json')
            if aborted.exists():
                raise OSError('The retained aborted installation record already exists')
            target.rename(aborted)
        temporary = folder / (INSTALLATION_FILENAME + '.pending')
        if temporary.exists():
            raise OSError('An earlier incomplete installation record must be resolved first')
        with temporary.open('xb') as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, target)
    except OSError as error:
        raise _denied('local_evidence_install_unwritten',
                      'The installation record could not be written; evidence rows remain unchanged',
                      503) from error


# ------------------------------------------------------------------ receipt issuance (channel side)


def prepare_receipt(engine: EngineService, *, receipt: dict) -> tuple[Path, bytes, str]:
    """Stage the one-shot receipt; the caller commits the audit before finalizing it.

    An existing unconsumed receipt blocks a second approval
    (`local_evidence_receipt_pending`); a consumed one is retained under an
    aborted name rather than silently overwritten.
    """
    folder = _control_folder(engine)
    inspect_owner_directory(Path(engine.db.data_dir))
    inspect_owner_directory(folder)
    payload = _canonical_file(receipt)
    digest = _sha256_bytes(payload)
    target = folder / POLICY_FILENAME
    pending = folder / (POLICY_FILENAME + '.pending')
    try:
        if target.is_symlink() or target.is_junction():
            raise OSError('The receipt path cannot cross filesystem links')
        if target.exists():
            existing = target.read_bytes()
            try:
                previous = strict_json(existing)
            except (EngineError, TypeError):
                previous = None
            if type(previous) is not dict or type(previous.get('receipt_id')) is not str:
                raise _denied('local_evidence_receipt_unwritten',
                              'The previous receipt is damaged and requires explicit cleanup', 503)
            if _consumed_record(engine, previous['receipt_id']) is None:
                raise _denied('local_evidence_receipt_pending',
                              'An earlier approved receipt is still waiting for evidence-admin', 409)
            aborted = folder / ('LocalEvidenceIssuance.aborted-'
                                + hashlib.sha256(existing).hexdigest() + '.json')
            if aborted.exists():
                raise OSError('The retained aborted receipt name already exists')
            target.rename(aborted)
        if pending.exists():
            raise OSError('An earlier incomplete receipt must be resolved first')
        with pending.open('xb') as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
    except EngineError:
        raise
    except OSError as error:
        raise _denied('local_evidence_receipt_unwritten',
                      'The receipt could not be written; no evidence was approved', 503) from error
    return target, payload, digest


def finalize_receipt(engine: EngineService, *, target: Path) -> None:
    pending = target.with_name(POLICY_FILENAME + '.pending')
    try:
        os.replace(pending, target)
    except OSError as error:
        raise _denied('local_evidence_receipt_unwritten',
                      'The audited receipt could not be finalized', 503) from error


def discard_pending_receipt(engine: EngineService) -> None:
    pending = _control_folder(engine) / (POLICY_FILENAME + '.pending')
    try:
        pending.unlink(missing_ok=True)
    except OSError:
        pass


def local_evidence_audit_filename() -> str:
    return 'LocalEvidenceAuthorization.json'


def local_evidence_audit_metadata_key() -> str:
    return 'local_evidence_authorization_audit'
