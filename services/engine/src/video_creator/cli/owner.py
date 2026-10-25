"""Local Owner-only terminal commands; no credential arguments or --yes."""

import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from video_creator.application.native_execution_installation import (
        NativeExecutionInstallationObserver,
    )


class OwnerInstallationObserverFactory(Protocol):
    """Trusted fixed in-process installation source, never an argv selector.

    Construction retains its own partial resources before OS contact. Returning
    the observer performs no action or qualification; observe opens the actual
    held host/receipt/payload. Public tokens and proposals do not configure it.
    """
    def __call__(self, *, engine, bootstrap, authorization) -> 'NativeExecutionInstallationObserver': ...


_installation_attempts = {}


class _OwnerInstallationAttempt:
    def __init__(self, factory):
        self.factory, self.observer, self.observation = factory, None, None
        self.cleanup_failure = None
        # The factory itself owns any construction that fails before return.
        _installation_attempts[id(self)] = self

    def close(self):
        if self.observer is not None:
            self.observer.close(self.observation)
            del _installation_attempts[id(self)]


def add_owner_parsers(commands):
    bootstrap = commands.add_parser('owner-init', help='Explicit local OS Owner initialization, renewal or revocation')
    bootstrap.add_argument('--data-dir', required=True, type=Path)
    bootstrap.add_argument('--action', choices=('initialize', 'renew', 'revoke'), default='initialize')
    bootstrap.add_argument('--action-key', required=True, help='Stable idempotency identity for this explicit Owner action')
    bootstrap.add_argument('--owner-subject', help='Domain Owner confirmed in the actual OS session, required for initialize/renew')
    bootstrap.add_argument('--project-id', action='append', help='Explicit actual owned project, repeat for a finite scope')
    bootstrap.add_argument('--expires-at', help='Explicit timezone-qualified ISO8601 management expiry; required for initialize/renew')
    policy = commands.add_parser('owner-policy', help='Authenticated local Owner policy management; ordinary API tokens are never accepted')
    policy.add_argument('--data-dir', required=True, type=Path)
    policy.add_argument('action', choices=('install', 'select', 'revoke', 'get', 'reauthorize'))
    policy.add_argument('--proposal', required=True, type=Path, help='Existing exact typed command JSON, never authentication')
    policy.add_argument('--idempotency-key', help='Required original command key for mutations, omitted for get')
    execution = commands.add_parser('owner-execution', help='Explicit actual OS Owner installed execution registration management')
    execution.add_argument('--data-dir', required=True, type=Path)
    execution.add_argument('action', choices=('install', 'select', 'revoke', 'get'))
    execution.add_argument('--proposal', required=True, type=Path, help='Exact private installation proposal or original registration reference; never authentication')
    execution.add_argument('--idempotency-key', help='Required stable Owner mutation key, omitted for get')
    creation = commands.add_parser('owner-project-creation', help='One actual Owner action installs bounded daily project creation')
    creation.add_argument('--data-dir', required=True, type=Path)
    creation.add_argument('action', choices=('install', 'revoke', 'get'))
    creation.add_argument('--proposal', required=True, type=Path, help='Exact creation template/role references, never authentication')
    creation.add_argument('--idempotency-key', help='Original mutation key; omitted for read-only get')


def _expiry(value):
    if not value:
        raise ValueError('Explicit expiry required')
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        raise ValueError('Timezone required')
    delta = parsed.astimezone(UTC) - datetime(1970, 1, 1, tzinfo=UTC)
    return (delta.days * 86400 + delta.seconds) * 1_000_000 + delta.microseconds


def run_owner_command(args, *, installed_services_factory=None, installation_observer_factory=None):
    # All OS/secret/DB work is lazy and occurs only in these selected commands.
    from video_creator.application.bundles import (
        BundleService,
        InstancePrincipalRegistry,
        strict_json,
    )
    from video_creator.application.engine import EngineService, canonical
    from video_creator.application.owner_bootstrap import (
        OwnerBootstrapStore,
        PersistentOwnerManagementRegistry,
        confirm_local_action,
    )
    from video_creator.application.owner_services import (
        OwnerServices,
        assemble_owner_services,
    )
    from video_creator.application.production_reauthorization import (
        ReauthorizeOriginalProduction,
    )
    from video_creator.domain.errors import EngineError
    from video_creator.domain.production_authorization import (
        InstallProductionPolicy,
        ProductionPolicyRef,
        RevokeProductionPolicy,
        SelectProductionPolicy,
    )
    from video_creator.infrastructure.owner_identity import inspect_owner_directory

    inspect_owner_directory(args.data_dir)
    engine = EngineService(args.data_dir)
    if args.command == 'owner-init':
        store = OwnerBootstrapStore(engine)
        if args.action == 'revoke':
            if args.owner_subject or args.project_id or args.expires_at:
                raise EngineError('owner_action_invalid', 'Revocation takes its scope from the actual existing Owner binding', 422)
            previous = store.revocation_target()
            owner, projects, expiry = previous.principal.owner_subject, previous.principal.project_ids, previous.principal.expires_at_us
        else:
            owner, projects, expiry = args.owner_subject, tuple(args.project_id or ()), _expiry(args.expires_at)
        record = store.change(action=args.action, action_key=args.action_key, owner_subject=owner,
                              project_ids=projects, expires_at_us=expiry)
        print(canonical(record))
        return
    store = OwnerBootstrapStore(engine)
    with store.current() as binding:
        owner = binding.principal.owner_subject
    bundle = BundleService(engine, principals=InstancePrincipalRegistry(engine.instance_id, owner))
    services = (installed_services_factory(engine, owner, bundle) if installed_services_factory is not None
                else assemble_owner_services(engine, owner, bundle=bundle, for_management=True))
    if (not isinstance(services, OwnerServices) or not isinstance(services.registry, PersistentOwnerManagementRegistry)
            or services.bootstrap.engine is not engine or services.authorization.engine is not engine
            or services.admissions.engine is not engine or services.copy_inputs.bundle is not bundle
            or services.registry is None or services.registry.owner_subject != owner):
        raise EngineError('owner_configuration_conflict', 'Trusted installation factory must return this same actual Owner/Engine/Bundle assembly', 503)
    with services.bootstrap.current() as current:
        credential = services.bootstrap.secrets.resolve(current.principal.authentication_binding_id)
    capability = services.registry.authenticate(credential, engine.clock())
    del credential
    if args.command == 'owner-execution':
        return _run_execution_command(args, services, capability,
                                      installation_observer_factory=installation_observer_factory)
    if args.command == 'owner-project-creation':
        from video_creator.domain.daily_project_authorization import (
            DailyProjectAuthorizationRef,
            InstallDailyProjectAuthorization,
            RevokeDailyProjectAuthorization,
        )

        models = {'install': InstallDailyProjectAuthorization, 'revoke': RevokeDailyProjectAuthorization,
            'get': DailyProjectAuthorizationRef}
        if (args.proposal.is_symlink() or args.proposal.is_junction() or not args.proposal.is_file()
                or not 0 < args.proposal.stat().st_size <= 2 * 1024 * 1024):
            raise EngineError('owner_proposal_invalid', 'Creation proposal must be one bounded regular local file', 422)
        size = args.proposal.stat().st_size
        with args.proposal.open('rb') as stream:
            raw = stream.read(2 * 1024 * 1024 + 1)
        if len(raw) != size or len(raw) > 2 * 1024 * 1024:
            raise EngineError('owner_proposal_changed', 'Actual bounded creation proposal changed while reading', 409)
        proposal = models[args.action].model_validate(strict_json(raw))
        if args.action == 'get':
            if args.idempotency_key:
                raise EngineError('owner_action_invalid', 'Creation get takes no mutation key', 422)
            result = services.daily_projects.get(capability, proposal)
        else:
            if not args.idempotency_key:
                raise EngineError('owner_action_invalid', 'Creation mutation requires its original command key', 422)
            confirm_local_action(engine.instance_id, 'project-creation-' + args.action, proposal.model_dump(mode='json'))
            callback = {'install': services.daily_projects.install, 'revoke': services.daily_projects.revoke}[args.action]
            result = callback(capability, args.idempotency_key, proposal)
        print(json.dumps(result.model_dump(mode='json'), ensure_ascii=False))
        return
    models = {'install': InstallProductionPolicy, 'select': SelectProductionPolicy,
              'revoke': RevokeProductionPolicy, 'get': ProductionPolicyRef, 'reauthorize': ReauthorizeOriginalProduction}
    if args.proposal.stat().st_size > 2 * 1024 * 1024:
        raise EngineError('owner_proposal_invalid', 'Policy proposal exceeds the finite input limit', 422)
    proposal = models[args.action].model_validate(strict_json(args.proposal.read_bytes()))
    if args.action == 'get':
        if args.idempotency_key:
            raise EngineError('owner_action_invalid', 'Read-only policy get takes no mutation key', 422)
        result = services.authorization.get_policy(capability, proposal)
    else:
        if not args.idempotency_key:
            raise EngineError('owner_action_invalid', 'An original management idempotency key is required', 422)
        confirm_local_action(engine.instance_id, 'policy-' + args.action, proposal.model_dump(mode='json'))
        callback = {'install': services.authorization.install_policy, 'select': services.authorization.select_policy,
                    'revoke': services.authorization.revoke_policy, 'reauthorize': services.reauthorization.reauthorize}[args.action]
        result = callback(capability, args.idempotency_key, proposal)
    print(json.dumps(result.model_dump(mode='json'), ensure_ascii=False))


def _run_execution_command(args, services, capability, *, installation_observer_factory):
    from video_creator.application.bundles import strict_json
    from video_creator.application.engine import canonical
    from video_creator.application.execution_registration import (
        ExecutionRegistrationStore,
    )
    from video_creator.application.owner_bootstrap import confirm_local_action
    from video_creator.domain.errors import EngineError
    from video_creator.domain.native_execution_registration import (
        ExecutionRegistrationRef,
        InstallNativeExecution,
        NativeInstallationInputs,
        RevokeNativeExecution,
        SelectNativeExecution,
    )
    from video_creator.infrastructure.held_authority import FRAME_LIMIT

    engine = services.authorization.engine
    models = {'install': InstallNativeExecution, 'select': SelectNativeExecution,
              'revoke': RevokeNativeExecution, 'get': ExecutionRegistrationRef}
    size = args.proposal.stat().st_size
    if not 0 < size <= FRAME_LIMIT:
        raise EngineError('owner_proposal_invalid', 'Full private installation proposal exceeds the finite input limit', 422)
    data = args.proposal.read_bytes()
    if len(data) != size:
        raise EngineError('owner_proposal_changed', 'Actual installation proposal changed while reading', 409)
    proposal = models[args.action].model_validate(strict_json(data))
    store = ExecutionRegistrationStore(engine, bootstrap=services.bootstrap, authorization=services.authorization)
    if args.action == 'get':
        if args.idempotency_key:
            raise EngineError('owner_action_invalid', 'Read-only original registration get takes no mutation key', 422)
        record = store.get(capability, proposal)
        print(canonical({'registration_ref': record.registration_ref.model_dump(mode='json'),
            'installed_record_ref': record.installed_record_ref.model_dump(mode='json'),
            'role': record.registration.role, 'project_ids': record.registration.project_ids,
            'expires_at_us': record.registration.expires_at_us, 'current': record.current, 'revoked': record.revoked}))
        return
    if not args.idempotency_key:
        raise EngineError('owner_action_invalid', 'Original execution management idempotency key is required', 422)
    if args.action in ('install', 'select') and installation_observer_factory is None:
        raise EngineError('native_installation_observer_unconfigured', 'Trusted concrete retained installation observer is required', 503)
    confirm_local_action(engine.instance_id, 'execution-' + args.action, proposal.model_dump(mode='json'))
    if args.action == 'revoke':
        result = store.revoke(capability, args.idempotency_key, proposal)
    else:
        installation = proposal.installation if args.action == 'install' else NativeInstallationInputs.model_validate(
            {name: getattr(store.get(capability, proposal.registration_ref).installed_record, name)
             for name in NativeInstallationInputs.model_fields})
        attempt = _OwnerInstallationAttempt(installation_observer_factory)
        try:
            attempt.observer = installation_observer_factory(engine=engine, bootstrap=services.bootstrap,
                                                            authorization=services.authorization)
            with services.bootstrap.current() as owner_binding:
                # Capture the real original Owner record, then release its
                # Control before hash/RPC. Mutation rechecks that generation.
                original_owner = owner_binding
            attempt.observation = attempt.observer.observe(installation, owner_binding=original_owner)
            callback = store.install if args.action == 'install' else store.select
            result = callback(capability, args.idempotency_key, proposal,
                              observer=attempt.observer, observation=attempt.observation)
        except BaseException as original_failure:
            try:
                attempt.close()
            finally:
                # Cleanup failure leaves the original attempt strongly held;
                # the primary action failure retains priority, never success.
                cleanup_failure = sys.exception()
                if cleanup_failure is not original_failure:
                    attempt.cleanup_failure = cleanup_failure
                    raise original_failure from None
            raise
        else:
            attempt.close()
    print(canonical({'action_id': result.action_id, 'action': result.action,
        'installed_record_ref': result.installed_record_ref.model_dump(mode='json'),
        'execution_refs': [ref.model_dump(mode='json') for ref in result.execution_refs],
        'registry_revision': result.registry_revision}))
