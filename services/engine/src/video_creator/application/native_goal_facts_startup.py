"""UNAPPLIED B42/RV82-P02 candidate; syntax/static review only.

Proposed target: video_creator.application.native_goal_facts_startup.
Only the fixed indexed native entry calls this composition. No global Owner,
issuer current guard, setup recovery or normal acceptance hook is changed.
"""

import threading
from dataclasses import dataclass

from video_creator.application.accepted_goal_facts import (
    AcceptedGoalFactContext,
    _FactReader,
    _owner_command,
)
from video_creator.application.engine import digest
from video_creator.application.execution_registration import (
    ExecutionRegistrationStore,
)
from video_creator.application.native_installation import (
    NativeInstallationAuthority,
)
from video_creator.application.owner_fact_sources import (
    assert_local_owner_fact_source,
)
from video_creator.cli.native_startup_record import NativeStartupRecord
from video_creator.domain.errors import EngineError
from video_creator.domain.native_execution_registration import (
    ExecutionRegistrationRef,
)
from video_creator.infrastructure.held_authority import OwnedAuthorityConnection
from video_creator.infrastructure.qualified_authority import OwnedQualifiedAuthorityConnection


def _invalid(message):
    return EngineError('native_startup_fact_invalid', message, 422)


@dataclass(frozen=True, eq=False, repr=False)
class _NativeStartupFactBinding:
    """Original context member, not a current identity or serializable ticket."""

    record: object
    startup_record: object
    anchor: str
    root: object
    bundle: object
    authority: object
    thread_id: int
    _context: object
    _store: object
    _epoch: object


def _source_owner(reader, store, root, selected):
    """Reconstruct the actual historical Owner command for this installation.

    Generation/action/authentication IDs come from the independently parsed
    persisted record, not the carrier. _owner_command verifies the original
    request/command/canonical body and the current actual OS directory lineage.
    No secret resolution, current() or management capability is involved.
    """
    installed, body = selected.installed_record, selected.registration
    expected = (installed.owner_binding_generation, installed.owner_binding_action_id,
        installed.authentication_binding_id)
    rows = reader.execute("SELECT * FROM commands WHERE owner=? AND scope IN ('owner.bootstrap.initialize','owner.bootstrap.renew','owner.bootstrap.revoke')",
        (root.owner_binding.principal.owner_subject,)).fetchall()
    owners = []
    for row in rows:
        # A damaged Owner-history body is not an authenticated alternative.
        if type(row['result_json']) is not str:
            raise _invalid('Installed source Owner history is not canonical SQL TEXT')
        owner = store.bootstrap._decode(row['result_json'])
        if (owner.generation, owner.action_id, owner.principal.authentication_binding_id) == expected:
            owners.append(_owner_command(reader, store.bootstrap,
                root.owner_binding.principal.owner_subject, digest(row['result_json'])))
    if len(owners) != 1:
        raise _invalid('Installed source lacks one exact original Owner action')
    owner = owners[0]
    principal, actual = owner.principal, root.owner_binding
    if ((owner.os_subject, owner.directory_device, owner.directory_inode) != (
            actual.os_subject, actual.directory_device, actual.directory_inode)
            or owner.generation > actual.generation or owner.revoked
            or (body.instance_id, body.owner_subject, body.executing_principal_id) != (
                store.engine.instance_id, principal.owner_subject, principal.owner_subject)
            or (body.owner_binding_generation, body.owner_binding_action_id, body.authentication_binding_id) != expected
            or (installed.os_subject, installed.directory_device, installed.directory_inode) != (
                owner.os_subject, owner.directory_device, owner.directory_inode)
            or (selected.installation_action.administrator_id, selected.installation_action.authentication_source) != (
                principal.administrator_id, principal.authentication_source)
            or not set(body.project_ids) <= set(principal.project_ids)
            or body.expires_at_us > principal.expires_at_us):
        raise _invalid('Installed source differs from its real historical OS Owner/action/scope')
    # The Owner and registration may now be expired/revoked/noncurrent. This
    # function proves past authenticity only and deliberately never calls _active.


def _select_source(reader, store, root, context, startup_record):
    """Closed anchors: actual current role, or exact original pending role.

    A new legitimate source need not equal the old Goal references. A historical
    fallback cannot choose an arbitrary row/hash/ref from the caller. Corrupt
    current source proofs are never swallowed to try a different candidate.
    """
    owner, role = root.owner_binding.principal.owner_subject, startup_record.context.role
    revision = store.authorization._revision(reader)
    rows = reader.execute('SELECT registration_id,revision,content_sha256 FROM execution_registrations '
        'WHERE instance_id=? AND owner=? AND role=? AND current=1',
        (store.engine.instance_id, owner, role)).fetchall()
    if len(rows) > 1:
        raise _invalid('Native role has conflicting actual current registration rows')
    if rows:
        selected, _row, _installed = store._record(reader,
            ExecutionRegistrationRef(registration_id=rows[0][0], revision=rows[0][1], content_sha256=rows[0][2]),
            owner, revision, [])
        _source_owner(reader, store, root, selected)
        try:
            store._startup(selected, startup_record)
        except EngineError as error:
            if error.code != 'execution_registration_startup_conflict' or error.status_code != 409:
                raise
        else:
            return selected, 'actual_current_role'
    # Only the already authenticated, protected pending intent can identify
    # the older source. This does not edit its parent/refs or restore execution.
    parent, _row = store._fact_daily._record(reader, context.intent.authorization_ref, owner)
    refs = tuple(item.registration_ref for item in parent.authorization.execution_refs if item.role == role)
    if len(refs) != 1:
        raise _invalid('Original pending Goal has no one exact installed role source')
    selected, _row, _installed = store._record(reader, refs[0], owner, revision, [])
    store._startup(selected, startup_record)
    _source_owner(reader, store, root, selected)
    return selected, 'original_pending_role'


def _bind_startup(store, bundle, startup_record, authority, context):
    root = context.root
    state = store._goal_facts.get(context)
    if (type(store) is not ExecutionRegistrationStore or type(context) is not AcceptedGoalFactContext
            or context._store is not store or context._epoch is not store._fact_epoch
            or context._daily is not store._fact_daily or state is None or state.get('native_startup') is not None
            or context.thread_id != threading.get_ident() or bundle.engine is not store.engine
            or bundle.principals.owner_subject != root.owner_binding.principal.owner_subject
            or type(startup_record) is not NativeStartupRecord or type(authority) is not NativeInstallationAuthority
            or type(authority.connection) not in (OwnedAuthorityConnection, OwnedQualifiedAuthorityConnection)
            or root.native_connection is not authority.connection or root.native_observation is None
            or authority.connection.context != startup_record.context
            or startup_record.context.instance_id != store.engine.instance_id):
        raise EngineError('native_startup_fact_source_denied', 'Exact Bundle Owner and original native Store/root/peer/context are required', 403)
    assert_local_owner_fact_source(store.bootstrap, root)
    with store.engine.db.connect() as connection:
        reader = _FactReader(connection)
        selected, anchor = _select_source(reader, store, root, context, startup_record)
        # Merge only after every original proof/map/image/role/Owner check.
        # Repeated query snapshots must agree, including between the two reads.
        for key, rows in reader.queries.items():
            if key in state['queries'] and state['queries'][key] != rows:
                raise _invalid('Native source changed between complete historical reads')
        queries = dict(state['queries'])
        queries.update(reader.queries)
        binding = _NativeStartupFactBinding(selected, startup_record, anchor, root, bundle, authority,
            threading.get_ident(), context, store, store._fact_epoch)
        state['queries'], state['native_startup'] = queries, binding
        assert_native_startup_fact_writer(store, connection, context)
    assert_local_owner_fact_source(store.bootstrap, root)


def assert_native_startup_fact_writer(store, connection, context):
    """Same original context/object/local observation, then real cached rows.

    No _active/current, OS calls, file hashing, qualification or RPC occurs in
    this hook. The original generic facts guard separately verifies all cached
    rows at writer start/final and immediately before the exact floor complete.
    """
    state = store._goal_facts.get(context)
    binding = state.get('native_startup') if state is not None else None
    root = context.root
    if (type(binding) is not _NativeStartupFactBinding or binding._context is not context
            or binding._store is not store or binding._epoch is not store._fact_epoch
            or binding.root is not root or binding.thread_id != threading.get_ident()
            or binding.bundle.engine is not store.engine
            or binding.bundle.principals.owner_subject != root.owner_binding.principal.owner_subject
            or binding.authority.connection is not root.native_connection
            or binding.authority.connection.context != binding.startup_record.context
            or binding.anchor not in ('actual_current_role', 'original_pending_role')):
        raise EngineError('native_startup_fact_source_denied', 'Original live authenticated native startup member is required before facts completion', 403)
    assert_local_owner_fact_source(store.bootstrap, root, connection=connection)
    store._startup(binding.record, binding.startup_record)


def native_pending_goal_store(*, engine, bundle, record, authority):
    """Proposed exact native entry only: authenticate before any fact writer."""
    from video_creator.application.daily_projects import DailyProjectService
    from video_creator.application.owner_bootstrap import OwnerBootstrapStore
    from video_creator.application.production_admissions import ProductionAdmissions
    from video_creator.application.production_authorization import (
        ProductionAuthorizationService,
    )
    from video_creator.application.production_management import (
        ProductionAuthorizationControl,
    )

    if (type(record) is not NativeStartupRecord or type(authority) is not NativeInstallationAuthority
            or type(authority.connection) not in (OwnedAuthorityConnection, OwnedQualifiedAuthorityConnection)
            or authority.connection.context != record.context
            or record.context.instance_id != engine.instance_id or bundle.engine is not engine):
        raise EngineError('owner_fact_source_denied', 'Exact original indexed native connection and instance are required', 403)
    authority.connection.assert_local_current()
    bootstrap = OwnerBootstrapStore(engine)
    control = ProductionAuthorizationControl(engine.db.data_dir / 'Control' / 'ProductionAuthorizationControl.json', engine.instance_id)
    authorization = ProductionAuthorizationService(engine, None, control)
    store = ExecutionRegistrationStore(engine, bootstrap=bootstrap, authorization=authorization)
    issuer = ProductionAdmissions(authorization)
    daily = DailyProjectService(engine, bootstrap=bootstrap, authorization=authorization, registrations=store, issuer=issuer)
    if control.path.exists():
        store._fact_daily = daily
        with bootstrap.local_fact_source(native_connection=authority.connection) as root:
            if bundle.principals.owner_subject != root.owner_binding.principal.owner_subject:
                raise EngineError('execution_registration_owner_denied', 'Actual Bundle Owner differs from the authenticated local OS Owner', 403)
            with store.accepted_goal_facts(root) as context:
                if context is not None:
                    _bind_startup(store, bundle, record, authority, context)
                    daily.resolve_accepted_goal_fact(context)
    return store
