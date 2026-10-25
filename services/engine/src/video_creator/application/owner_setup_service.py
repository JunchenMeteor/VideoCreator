"""One real first Goal, original Owner actions and exact bounded recovery."""

import json
import os
import threading
from contextlib import contextmanager

from video_creator.application.bundles import strict_json
from video_creator.application.engine import canonical, digest, identity
from video_creator.application.native_execution_observer import (
    NativeExecutionObserverFactory,
)
from video_creator.application.owner_bootstrap import OwnerBootstrapStore
from video_creator.application.owner_services import assemble_owner_services
from video_creator.application.owner_setup_confirmation import (
    NativeOwnerConfirmationConsumer,
    OwnerSetupPreparationSource,
)
from video_creator.application.owner_setup_sources import (
    AcceptedOwnerSetupSource,
    OwnerActionConfirmationSource,
    OwnerSetupGoalSource,
)
from video_creator.domain import contracts as c
from video_creator.domain.daily_project_authorization import (
    DailyExecutionRef,
    DailyProjectActionReceipt,
    InstallDailyProjectAuthorization,
    ProjectGoalAccepted,
)
from video_creator.domain.errors import EngineError
from video_creator.domain.native_execution_registration import (
    InstallExecutionRegistration,
    InstallNativeExecution,
)
from video_creator.domain.owner_setup import (
    AcceptedOwnerSetupIntent,
    ExpectedSetupOwner,
    OwnerSetupIntent,
    OwnerSetupStatus,
    SetupContinueGoal,
    SetupCreationInstall,
    SetupDirectoryIdentity,
    SetupDraftIdentity,
    SetupExecutionInstall,
    SetupExecutionReceiptDependency,
    SetupOwnerInitialize,
    setup_bytes,
    setup_sha256,
    step_proposal_sha256,
)
from video_creator.domain.owner_setup_journal import (
    AcceptedSetupJournal,
    AcceptedSetupRef,
    DraftOrigin,
    PreparedSetupJournal,
    SetupPreparationOptions,
    SetupPreparationRequest,
)

_retained_services = {}


def _step(model, **values):
    # Only a temporary constructor value; never persist an unverified proposal.
    first = model.model_construct(proposal_sha256='0' * 64, **values)
    return model.model_validate({**first.model_dump(mode='json'), 'proposal_sha256': step_proposal_sha256(first)})


def _command_body(command):
    return canonical(command) if hasattr(command, 'model_dump') else json.dumps(command, ensure_ascii=False,
        sort_keys=True, separators=(',', ':'), allow_nan=False)


class OwnerSetupService:
    def __init__(self, *, engine, bundle, confirmation, options, installation_observer_factory,
                 installation_authority=None, installation_session_guard=None):
        if (type(confirmation) is not NativeOwnerConfirmationConsumer or confirmation.engine is not engine
                or confirmation.bundle is not bundle or type(options) is not SetupPreparationOptions
                or type(installation_observer_factory) is not NativeExecutionObserverFactory):
            raise EngineError('owner_setup_configuration_conflict', 'Setup requires original same-instance trusted services', 503)
        self.engine, self.bundle, self.confirmation = engine, bundle, confirmation
        self.options, self.observer_factory = options, installation_observer_factory
        self.installation_authority, self.session_guard = installation_authority, installation_session_guard
        self.bootstrap = OwnerBootstrapStore(engine)
        self._lock, self._epoch, self._closed = threading.RLock(), object(), False
        self._accepted, self._accepted_facts, self._actions, self._goals = {}, {}, {}, {}
        self._services = self._observer = self._observation = None
        _retained_services[id(self)] = self

    @property
    def owner(self):
        return self.bundle.principals.owner_subject

    @staticmethod
    def _model(model, body):
        if type(body) is not str:
            raise EngineError('owner_setup_journal_invalid', 'Setup journal must be canonical SQLite TEXT', 422)
        try:
            value = model.model_validate(strict_json(body.encode('utf-8')))
        except (ValueError, TypeError, UnicodeError) as error:
            raise EngineError('owner_setup_journal_invalid', 'Exact setup journal is damaged', 422) from error
        if canonical(value) != body:
            raise EngineError('owner_setup_journal_invalid', 'Setup journal canonical fields differ', 422)
        return value

    def _row(self, connection, setup_id, *, local=False):
        row = connection.execute('SELECT * FROM owner_setup_journals WHERE setup_id=? AND instance_id=? AND owner=?',
            (setup_id, self.engine.instance_id, self.owner)).fetchone()
        if row is None:
            raise EngineError('owner_setup_not_found', 'This actual Owner has no such setup', 404)
        for body, sha in (('preparation_json', 'preparation_sha256'), ('accepted_json', 'accepted_sha256'),
                          ('goal_result_json', 'goal_result_sha256')):
            if ((row[body] is None) != (row[sha] is None)
                    or not local and row[body] is not None and digest(row[body]) != row[sha]):
                raise EngineError('owner_setup_journal_invalid', 'Setup bytes differ from their exact stored identity', 422)
        return row

    def _draft(self, connection, origin):
        draft = origin.project_draft
        row = connection.execute('SELECT * FROM projects WHERE id=? AND owner=?', (draft.project_id, self.owner)).fetchone()
        command = connection.execute("SELECT request_sha256,result_json FROM commands WHERE owner=? AND scope='project.create' AND idempotency_key=?",
            (self.owner, draft.create_command_key)).fetchone()
        snapshot = c.ProjectDraft(**draft.draft.model_dump(), project_id=draft.project_id,
            revision=draft.revision, saved_at_us=draft.saved_at_us)
        if (row is None or command is None or (row['revision'], row['saved_at_us'], row['body']) != (
                draft.revision, draft.saved_at_us, canonical(draft.draft))
                or (command['request_sha256'], command['result_json']) != (draft.create_request_sha256, canonical(snapshot))
                or digest(command['result_json']) != draft.create_receipt_sha256):
            raise EngineError('owner_setup_draft_changed', 'Original real draft or create receipt changed', 409)

    def _directory(self):
        self.bootstrap.assert_current_directory(require_control=self.bootstrap._control_identity is not None)

    def prepare_first_goal(self, key, goal, *, preparation: OwnerSetupPreparationSource) -> OwnerSetupIntent:
        c.SourceBinding(system=key, namespace='owner-setup-prepare')
        self.confirmation.assert_preparation(preparation)
        request = SetupPreparationRequest(idempotency_key=key, goal=goal, options=self.options)
        request_sha = setup_sha256(request)
        project_key = 'owner-setup-draft.' + digest(self.owner + ':' + key)
        with self._lock:
            if self._closed or not self.engine.clock() < self.options.setup_expires_at_us:
                raise EngineError('owner_setup_expired', 'Current prepared scope expired', 403)
            with self.engine.db.transaction() as connection:
                self.confirmation.assert_preparation(preparation, local=True, connection=connection)
                row = connection.execute('SELECT * FROM owner_setup_journals WHERE instance_id=? AND owner=? AND preparation_key=?',
                    (self.engine.instance_id, self.owner, key)).fetchone()
                if row is not None:
                    row = self._row(connection, row['setup_id'])
                    if row['request_sha256'] != request_sha or row['project_create_key'] != project_key:
                        raise EngineError('idempotency_conflict', 'Preparation key belongs to another complete Goal/options', 409)
                    if row['preparation_json'] is not None:
                        prepared = self._model(PreparedSetupJournal, row['preparation_json'])
                        self._draft(connection, prepared.origin)
                        return prepared.intent
                    setup_id, created_at = row['setup_id'], row['created_at_us']
                else:
                    if connection.execute("SELECT 1 FROM owner_setup_journals WHERE instance_id=? AND owner=? AND phase NOT IN ('completed','aborted')",
                            (self.engine.instance_id, self.owner)).fetchone():
                        raise EngineError('owner_setup_pending', 'Another real first Goal needs explicit resolution', 409)
                    setup_id, created_at = identity('owner-setup'), self.engine.clock()
                    connection.execute('INSERT INTO owner_setup_journals(setup_id,instance_id,owner,preparation_key,request_sha256,project_create_key,phase,created_at_us) '
                        "VALUES(?,?,?,?,?,?,'preparing',?)", (setup_id, self.engine.instance_id, self.owner, key, request_sha, project_key, created_at))
                self.confirmation.assert_preparation(preparation, local=True, connection=connection)
            self.confirmation.assert_preparation(preparation)
            project = c.ProjectInput(name=goal.name, goal=goal.goal, source_text=goal.inputs.source_text)
            actual = self.confirmation.create_prepared_project(preparation, project, project_key)
            draft = SetupDraftIdentity(project_id=actual.project_id, revision=actual.revision,
                saved_at_us=actual.saved_at_us, draft=project, body_sha256=setup_sha256(project),
                project_draft_sha256=setup_sha256(actual), create_command_key=project_key,
                create_request_sha256=setup_sha256(project), create_receipt_sha256=setup_sha256(actual))
            intent = self._intent(setup_id, created_at, goal, draft, preparation)
            origin = DraftOrigin(instance_id=self.engine.instance_id, owner_subject=self.owner, project_draft=draft,
                goal=goal, goal_sha256=setup_sha256(goal), preparation_key=key, setup_id=setup_id,
                intent_revision=1, intent_sha256=setup_sha256(intent))
            prepared = PreparedSetupJournal(request=request, intent=intent, origin=origin)
            self.confirmation.assert_preparation(preparation)
            with self.engine.db.transaction() as connection:
                self.confirmation.assert_preparation(preparation, local=True, connection=connection)
                row = self._row(connection, setup_id)
                self._draft(connection, origin)
                if row['preparation_json'] is not None and row['preparation_json'] != canonical(prepared):
                    raise EngineError('owner_setup_preparation_changed', 'Original prepared intent changed', 409)
                connection.execute("UPDATE owner_setup_journals SET preparation_json=?,preparation_sha256=?,project_id=?,phase='prepared' WHERE setup_id=?",
                    (canonical(prepared), setup_sha256(prepared), actual.project_id, setup_id))
                self.confirmation.assert_preparation(preparation, local=True, connection=connection)
            return intent

    def _intent(self, setup_id, created_at, goal, draft, preparation):
        with self.engine.db.connect() as connection:
            owner = self.bootstrap._read(connection)
        expected = ExpectedSetupOwner(generation=owner.generation if owner else 0,
            action_id=owner.action_id if owner else None, binding_body_sha256=setup_sha256(owner) if owner else None)
        # First setup does not silently replace an existing installation.
        if owner is not None:
            raise EngineError('owner_setup_existing_owner', 'Existing Owner uses explicit existing-current setup actions', 409)
        prefix, expiry = setup_id + '.', self.options.management_expires_at_us
        owner_step = _step(SetupOwnerInitialize, step_id=prefix + 'owner', idempotency_key=prefix + 'owner',
            owner_subject=self.owner, project_ids=(draft.project_id,), expires_at_us=expiry)
        namespaces = tuple((item.system, item.namespace) for item in self.options.template.allowed_sources)
        command = InstallNativeExecution(record_id=prefix + 'installation', installation=self.confirmation.startup.installation,
            registrations=tuple(InstallExecutionRegistration(registration_id=prefix + role, role=role,
                project_ids=(draft.project_id,), allowed_source_namespaces=namespaces,
                expires_at_us=self.options.template.expires_at_us) for role in ('api', 'mcp', 'worker')))
        execution = _step(SetupExecutionInstall, step_id=prefix + 'execution', idempotency_key=prefix + 'execution',
            proposal=command, owner_from_step=owner_step.step_id)
        creation = _step(SetupCreationInstall, step_id=prefix + 'creation', idempotency_key=prefix + 'creation',
            authorization_id=prefix + 'creation', previous_ref=None,
            execution_source=SetupExecutionReceiptDependency(step_id=execution.step_id),
            allowed_entries=self.options.allowed_entries, expires_at_us=self.options.template.expires_at_us,
            max_created_projects=self.options.max_created_projects, max_active_productions=self.options.max_active_productions,
            template=self.options.template)
        continuation = _step(SetupContinueGoal, step_id=prefix + 'goal', idempotency_key=prefix + 'goal',
            creation_from_step=creation.step_id, goal_sha256=setup_sha256(goal))
        directory = preparation.directory
        startup = self.confirmation.startup
        return OwnerSetupIntent(setup_id=setup_id, instance_id=self.engine.instance_id, owner_subject=self.owner,
            directory=SetupDirectoryIdentity(path=str(self.engine.db.data_dir), os_subject=directory.os_subject,
                administrator_id=directory.administrator_id, device=directory.directory_device, inode=directory.directory_inode),
            expected_owner=expected, goal=goal, goal_sha256=setup_sha256(goal), project_draft=draft,
            installation=startup.installation, external_receipt_path=startup.external_receipt_path,
            expected_host_image=startup.expected_host_image, expected_host_sha256=startup.expected_host_sha256,
            source_manifest_sha256=self.options.source_manifest_sha256, created_at_us=created_at,
            expires_at_us=self.options.setup_expires_at_us, steps=(owner_step, execution, creation, continuation))

    def _file(self, journal):
        return self.engine.db.data_dir / 'Control' / ('AcceptedOwnerSetup-' + setup_sha256(journal) + '.json')

    def _retain(self, journal):
        self._directory()
        path, data = self._file(journal), setup_bytes(journal)
        path.parent.mkdir(mode=0o700, exist_ok=True)
        from video_creator.infrastructure.owner_identity import inspect_owner_directory

        inspect_owner_directory(path.parent)
        if path.exists():
            self._read_file(journal)
            return
        with path.open('xb') as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        self._directory()

    def _read_file(self, journal):
        path, expected = self._file(journal), setup_bytes(journal)
        if (path.is_symlink() or path.is_junction() or not path.is_file() or path.stat().st_size != len(expected)):
            raise EngineError('owner_setup_journal_invalid', 'Original protected accepted setup file is unavailable', 422)
        with path.open('rb') as stream:
            if stream.read(32 * 1024 * 1024 + 1) != expected:
                raise EngineError('owner_setup_journal_invalid', 'Original accepted setup bytes changed', 422)

    def accept(self, confirmation, *, preparation) -> AcceptedOwnerSetupSource:
        self.confirmation.assert_current(confirmation)
        self.confirmation.assert_preparation(preparation)
        with self.engine.db.connect() as connection:
            row = self._row(connection, confirmation.intent.setup_id)
            prepared = self._model(PreparedSetupJournal, row['preparation_json'])
            self._draft(connection, prepared.origin)
            owner = self.bootstrap._read(connection)
            if owner is not None or prepared.intent is not confirmation.intent and prepared.intent != confirmation.intent:
                raise EngineError('owner_setup_generation_changed', 'Original Owner/prepared intent changed before acceptance', 409)
        journal = AcceptedSetupJournal(prepared=prepared, accepted=AcceptedOwnerSetupIntent(intent=prepared.intent,
            intent_sha256=setup_sha256(prepared.intent), source=confirmation._original.source,
            accepted_at_us=self.engine.clock()))
        self._retain(journal)
        with self.engine.db.transaction() as connection:
            self.confirmation.assert_local_current(confirmation, connection=connection)
            self.confirmation.assert_preparation(preparation, local=True, connection=connection)
            self._draft(connection, prepared.origin)
            row = self._row(connection, prepared.intent.setup_id)
            if row['accepted_json'] is not None and row['accepted_json'] != canonical(journal):
                raise EngineError('owner_setup_already_accepted', 'Setup has another original confirmation', 409)
            connection.execute("UPDATE owner_setup_journals SET accepted_json=?,accepted_sha256=?,phase='accepted' WHERE setup_id=?",
                (canonical(journal), setup_sha256(journal), prepared.intent.setup_id))
            self.confirmation.assert_local_current(confirmation, connection=connection)
            self.confirmation.assert_preparation(preparation, local=True, connection=connection)
        return self._issue(journal, preparation)

    def _issue(self, journal, preparation):
        source = AcceptedOwnerSetupSource(journal, self, self.engine, self._epoch, threading.get_ident(), preparation)
        self._accepted[id(source)] = source
        self._accepted_facts[id(source)] = (canonical(journal), setup_sha256(journal))
        return source

    def recover(self, setup_id, *, preparation) -> AcceptedOwnerSetupSource:
        self.confirmation.assert_preparation(preparation)
        with self.engine.db.connect() as connection:
            row = self._row(connection, setup_id)
            journal = self._model(AcceptedSetupJournal, row['accepted_json'])
            if row['phase'] not in ('accepted', 'running', 'blocked', 'completed'):
                raise EngineError('owner_setup_recovery_denied', 'Only the original accepted setup can recover', 403)
        self._read_file(journal)
        source = self._issue(journal, preparation)
        try:
            if row['goal_result_json'] is None:
                self.assert_accepted_current(source)
            return source
        except BaseException:
            self._accepted.pop(id(source), None)
            self._accepted_facts.pop(id(source), None)
            raise

    def _accepted_member(self, source):
        if (self._closed or type(source) is not AcceptedOwnerSetupSource or source._service is not self
                or source._engine is not self.engine or source._epoch is not self._epoch
                or source._thread_id != threading.get_ident() or self._accepted.get(id(source)) is not source):
            raise EngineError('owner_setup_source_denied', 'Original accepted setup source/thread is required', 403)

    def _accepted_local(self, source, connection):
        self._accepted_member(source)
        self.confirmation.assert_preparation(source._preparation, local=True, connection=connection)
        journal = source.journal
        if self.engine.clock() >= journal.prepared.intent.expires_at_us:
            raise EngineError('owner_setup_expired', 'Accepted setup does not extend its original expiry', 403)
        row = self._row(connection, journal.prepared.intent.setup_id, local=True)
        if (row['accepted_json'], row['accepted_sha256']) != self._accepted_facts[id(source)]:
            raise EngineError('owner_setup_journal_invalid', 'Accepted setup no longer matches the actual original journal', 422)
        self._owner_state(connection, source)

    def _owner_state(self, connection, source):
        intent = source.journal.prepared.intent
        actual = self.bootstrap._read(connection)
        if actual is None:
            if intent.expected_owner.generation:
                raise EngineError('owner_setup_generation_changed', 'Original expected Owner disappeared', 403)
            return
        first = intent.steps[0]
        command = connection.execute("SELECT result_json FROM commands WHERE owner=? AND scope='owner.bootstrap.initialize' AND idempotency_key=?",
            (self.owner, first.idempotency_key)).fetchone()
        if (command is None or command[0] != canonical(actual) or actual.revoked
                or actual.principal.authentication_source != 'native_owner_session'
                or actual.principal.expires_at_us <= self.engine.clock()):
            raise EngineError('owner_setup_generation_changed', 'Accepted setup cannot revive a replaced/revoked Owner', 403)

    def assert_accepted_current(self, source):
        self._accepted_member(source)
        self.confirmation.assert_preparation(source._preparation)
        self._directory()
        self._read_file(source.journal)
        with self.engine.db.connect() as connection:
            self._accepted_local(source, connection)
            row = self._row(connection, source.journal.prepared.intent.setup_id)
            if row['goal_result_json'] is None:
                self._draft(connection, source.journal.prepared.origin)

    @contextmanager
    def _action(self, accepted, step, command):
        self.assert_accepted_current(accepted)
        source = OwnerActionConfirmationSource(accepted, step, digest(_command_body(command)), self, self._epoch, threading.get_ident())
        self._actions[id(source)] = source
        try:
            yield source
        finally:
            self._actions.pop(id(source), None)

    def assert_action_current(self, source):
        self.assert_accepted_current(source.accepted)
        with self.engine.db.connect() as connection:
            self.assert_action_local(source, connection)

    def assert_action_local(self, source, connection):
        if (type(source) is not OwnerActionConfirmationSource or source._service is not self or source._epoch is not self._epoch
                or source._thread_id != threading.get_ident() or self._actions.get(id(source)) is not source):
            raise EngineError('owner_setup_action_denied', 'Original current exact setup action is required', 403)
        self._accepted_local(source.accepted, connection)
        row = connection.execute('SELECT original_proposal_sha256,command_sha256 FROM owner_setup_steps WHERE setup_id=? AND step_id=?',
            (source.accepted.journal.prepared.intent.setup_id, source.step.step_id)).fetchone()
        if row is None or tuple(row) != (source.step.proposal_sha256, source.final_command_sha256):
            raise EngineError('owner_setup_action_changed', 'Original finalized command or dependency changed', 409)

    def assert_bootstrap_action(self, source, bootstrap, proposal):
        self.assert_action_current(source)
        self._bootstrap_proposal(source, bootstrap, proposal)

    def assert_bootstrap_action_local(self, source, bootstrap, proposal, connection):
        self.assert_action_local(source, connection)
        self._bootstrap_proposal(source, bootstrap, proposal)

    def _bootstrap_proposal(self, source, bootstrap, proposal):
        step = source.step
        if (bootstrap is not self.bootstrap or type(step) is not SetupOwnerInitialize or proposal != self._bootstrap_command(step)):
            raise EngineError('owner_setup_action_denied', 'Native confirmation covers this exact original Owner action only', 403)

    def _bootstrap_command(self, step):
        os_identity = self.bootstrap.os_identity
        return {'action': 'initialize', 'action_key': step.idempotency_key, 'instance_id': self.engine.instance_id,
            'owner_subject': self.owner, 'project_ids': step.project_ids, 'expires_at_us': step.expires_at_us,
            'scope': 'production.authorization.manage', 'os_subject': os_identity.os_subject,
            'directory_device': os_identity.directory_device, 'directory_inode': os_identity.directory_inode}

    def _stage_step(self, accepted, step, command, dependencies=()):
        body = _command_body(command)
        sha = digest(body)
        dependency = json.dumps(dependencies, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)
        with self.engine.db.transaction() as connection:
            self._accepted_local(accepted, connection)
            connection.execute("UPDATE owner_setup_journals SET phase='running' WHERE setup_id=? AND goal_result_json IS NULL",
                (accepted.journal.prepared.intent.setup_id,))
            row = connection.execute('SELECT * FROM owner_setup_steps WHERE setup_id=? AND step_id=?',
                (accepted.journal.prepared.intent.setup_id, step.step_id)).fetchone()
            if row is not None:
                if (row['original_proposal_sha256'], row['command_json'], row['command_sha256'], row['dependency_json']) != (
                        step.proposal_sha256, body, sha, dependency):
                    raise EngineError('owner_setup_action_changed', 'Exact finalized setup step changed', 409)
                self._accepted_local(accepted, connection)
                return row['receipt_json']
            connection.execute('INSERT INTO owner_setup_steps(setup_id,step_id,original_proposal_sha256,command_json,command_sha256,dependency_json) VALUES(?,?,?,?,?,?)',
                (accepted.journal.prepared.intent.setup_id, step.step_id, step.proposal_sha256, body, sha, dependency))
            self._accepted_local(accepted, connection)
        return None

    def _save_step(self, accepted, step, receipt):
        body = canonical(receipt)
        sha = digest(body)
        scopes = {'owner_initialize': 'owner.bootstrap.initialize', 'execution_install': 'owner.execution.install',
                  'creation_install': 'daily.project.install'}
        with self.engine.db.transaction() as connection:
            self._accepted_local(accepted, connection)
            original = connection.execute('SELECT request_sha256,result_json FROM commands WHERE owner=? AND scope=? AND idempotency_key=?',
                (self.owner, scopes[step.type], step.idempotency_key)).fetchone()
            if original is None or original['result_json'] != body:
                raise EngineError('owner_setup_receipt_invalid', 'Setup must retain the actual original mutator command and receipt', 422)
            row = connection.execute('SELECT receipt_json FROM owner_setup_steps WHERE setup_id=? AND step_id=?',
                (accepted.journal.prepared.intent.setup_id, step.step_id)).fetchone()
            if row is None or row[0] is not None and row[0] != body:
                raise EngineError('owner_setup_receipt_changed', 'Original step receipt changed', 422)
            connection.execute('UPDATE owner_setup_steps SET receipt_json=?,receipt_sha256=?,original_request_sha256=? WHERE setup_id=? AND step_id=?',
                (body, sha, original['request_sha256'], accepted.journal.prepared.intent.setup_id, step.step_id))
            self._accepted_local(accepted, connection)

    def execute(self, accepted):
        self._accepted_member(accepted)
        with self.engine.db.connect() as connection:
            row = self._row(connection, accepted.journal.prepared.intent.setup_id)
            if row['goal_result_json'] is not None:
                # Read an immutable original receipt before acquiring any new
                # execution permission. Later draft edits never reconsume it.
                if row['accepted_json'] != canonical(accepted.journal):
                    raise EngineError('owner_setup_journal_invalid', 'Historical accepted setup changed', 422)
                return self._model(ProjectGoalAccepted, row['goal_result_json'])
        self.assert_accepted_current(accepted)
        try:
            return self._execute_current(accepted)
        except EngineError as error:
            # Preserve original receipts, floor, planned IDs and budgets. This
            # progress marker is neither a denied Goal nor a fee settlement.
            try:
                with self.engine.db.transaction() as connection:
                    self._accepted_member(accepted)
                    self.confirmation.assert_initialization_local_current(connection)
                    row = self._row(connection, accepted.journal.prepared.intent.setup_id, local=True)
                    if row['accepted_json'] == self._accepted_facts[id(accepted)][0] and row['goal_result_json'] is None:
                        connection.execute("UPDATE owner_setup_journals SET phase='blocked' WHERE setup_id=?", (row['setup_id'],))
                        connection.execute('INSERT INTO metadata VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value',
                            ('owner_setup_block:' + row['setup_id'], error.code))
                    self.confirmation.assert_initialization_local_current(connection)
            except BaseException as marker_error:
                # Failed diagnostics must not replace the original failure.
                raise error from marker_error
            raise

    def _execute_current(self, accepted):
        for step in accepted.journal.prepared.intent.steps:
            if type(step) is SetupContinueGoal:
                self._configure_execution(accepted)
                with self.goal_source(accepted) as source:
                    return self._services.daily_projects.accept_owner_setup_goal(source)
            command, dependencies = self._command(accepted, step)
            self._stage_step(accepted, step, command, dependencies)
            with self._action(accepted, step, command) as action:
                if type(step) is SetupOwnerInitialize:
                    receipt = self.bootstrap.change(action='initialize', action_key=step.idempotency_key,
                        owner_subject=self.owner, project_ids=step.project_ids, expires_at_us=step.expires_at_us,
                        confirmation_source=action)
                else:
                    self._management_services()
                    with self._services.bootstrap.current() as owner:
                        secret = self._services.bootstrap.secrets.resolve(owner.principal.authentication_binding_id)
                    capability = self._services.registry.authenticate(secret, self.engine.clock())
                    with self._services.authorization.confirmed_setup_action(action):
                        if type(step) is SetupExecutionInstall:
                            if self._observer is None:
                                self._observer = self.observer_factory(engine=self.engine, bootstrap=self.bootstrap,
                                    authorization=self._services.authorization)
                                with self.bootstrap.current() as binding:
                                    self._observation = self._observer.observe(command.installation, owner_binding=binding)
                            receipt = self._services.daily_projects.registrations.install(capability, step.idempotency_key,
                                command, observer=self._observer, observation=self._observation)
                            self._install_local_production_authority()
                        else:
                            receipt = self._services.daily_projects.install(capability, step.idempotency_key, command)
            self._save_step(accepted, step, receipt)
        raise EngineError('owner_setup_intent_invalid', 'Prepared setup has no exact Goal continuation', 422)

    def _management_services(self):
        if self._services is None:
            self._services = assemble_owner_services(self.engine, self.owner, bundle=self.bundle, for_management=True,
                installation_authority=self.installation_authority, installation_session_guard=self.session_guard,
                owner_setup_bootstrap=self.bootstrap)

    def _install_local_production_authority(self):
        if self.installation_authority is not None:
            return  # Explicit qualified startup retains its original source.
        if self._observer is None or self._observation is None or self._services is None:
            raise EngineError('installation_observation_denied', 'Actual setup observation is required', 409)
        authority = self._observer.production_authority(self._observation)
        issuer = self._services.admissions
        if issuer.installation_authority is not None or issuer.installation_session_guard is not None:
            authority.close()
            raise EngineError('owner_setup_configuration_conflict', 'Installation authority was already assigned', 409)
        self.installation_authority = self.session_guard = authority
        issuer.installation_authority = issuer.installation_session_guard = authority

    def _command(self, accepted, step):
        if type(step) is SetupOwnerInitialize:
            return self._bootstrap_command(step), ()
        if type(step) is SetupExecutionInstall:
            return step.proposal, ()
        previous = next(item for item in accepted.journal.prepared.intent.steps if item.step_id == step.execution_source.step_id)
        self._management_services()
        with self.engine.db.connect() as connection:
            row = connection.execute('SELECT receipt_json,receipt_sha256 FROM owner_setup_steps WHERE setup_id=? AND step_id=?',
                (accepted.journal.prepared.intent.setup_id, previous.step_id)).fetchone()
            if row is None or row[0] is None or digest(row[0]) != row[1]:
                raise EngineError('owner_setup_dependency_missing', 'Creation needs the actual original execution receipt', 503)
            from video_creator.domain.native_execution_registration import (
                ExecutionRegistrationActionReceipt,
            )

            receipt = self._model(ExecutionRegistrationActionReceipt, row[0])
            refs = []
            for ref in receipt.execution_refs:
                record, _row, _installed = self._services.daily_projects.registrations._record(connection,
                    ref, self.owner, self._services.authorization._revision(connection), [])
                refs.append(DailyExecutionRef(role=record.registration.role, registration_ref=ref))
        command = InstallDailyProjectAuthorization(**step.model_dump(exclude={'type', 'step_id', 'idempotency_key',
            'proposal_sha256', 'execution_source'}), installed_record_ref=receipt.installed_record_ref,
            execution_refs=tuple(refs))
        return command, ({'step_id': previous.step_id, 'receipt_sha256': row[1]},)

    def _configure_execution(self, accepted):
        self._management_services()
        if self._services.execution_identity is not None:
            return
        if self.installation_authority is None:
            raise EngineError('production_installation_authority_unconfigured', 'Actual held installation authority is required for the first Goal', 503)
        from video_creator.cli.native_startup_record import NativeStartupRecord

        installation = accepted.journal.prepared.intent.installation
        raw = installation.model_dump(mode='json')
        carrier = {'format': 'native-startup-binding-v1', 'instance_id': self.engine.instance_id, 'role': 'api',
            **{key: raw[key] for key in ('installed_native_image', 'installed_native_image_sha256',
                'registration_sha256', 'resource_manifest_sha256', 'runtime_manifest_sha256', 'expected_files', 'engine_file_names')}}
        startup = NativeStartupRecord.parse(json.dumps(carrier, ensure_ascii=False, sort_keys=True,
            separators=(',', ':'), allow_nan=False).encode('utf-8'))
        store = self._services.daily_projects.registrations
        current = store.current(self.owner, 'api', startup)
        issuer = self._services.admissions
        registered = issuer.register_execution_identity(**store.original_projection(current))
        try:
            issuer.bind_native_registration(registered, store=store, current=current)
            self.engine.configure_production_authorization(issuer, subject_identities={self.owner: registered})
            self._services.execution_identity = registered
            self._services.native_registration_store, self._services.native_current_registration = store, current
            self._services.daily_projects.configure_owner_setup(self)
            self.engine.configure_daily_projects(self._services.daily_projects)
        except BaseException:
            issuer.unregister_execution_identity(registered)
            store.release(current)
            raise

    @contextmanager
    def goal_source(self, accepted):
        self.assert_accepted_current(accepted)
        self._configure_execution(accepted)
        with self.engine.db.connect() as connection:
            row = self._row(connection, accepted.journal.prepared.intent.setup_id)
            prepared = accepted.journal.prepared
            continuation = prepared.intent.steps[-1]
            creation = next(item for item in prepared.intent.steps if item.step_id == continuation.creation_from_step)
            step_row = connection.execute('SELECT receipt_json,receipt_sha256 FROM owner_setup_steps WHERE setup_id=? AND step_id=?',
                (prepared.intent.setup_id, creation.step_id)).fetchone()
            if step_row is None or step_row[0] is None or digest(step_row[0]) != step_row[1]:
                raise EngineError('owner_setup_dependency_missing', 'Goal requires the actual current creation receipt', 503)
            receipt = self._model(DailyProjectActionReceipt, step_row[0])
            # Goal body remains the exact displayed input. Creation ref is a
            # separately bound dependency, never written into that immutable Goal.
            if (prepared.intent.goal.creation_authorization_ref is not None
                    and prepared.intent.goal.creation_authorization_ref != receipt.authorization_ref):
                raise EngineError('owner_setup_dependency_changed', 'Displayed Goal names another creation authority', 409)
            ids_key = 'owner_setup_goal_ids:' + prepared.intent.setup_id
            original = connection.execute('SELECT value FROM metadata WHERE key=?', (ids_key,)).fetchone()
        if original is None:
            ids = tuple(identity(kind) for kind in ('production', 'run', 'request', 'project-scope', 'project-derivation'))
            with self.engine.db.transaction() as connection:
                self._accepted_local(accepted, connection)
                actual = connection.execute('SELECT value FROM metadata WHERE key=?', (ids_key,)).fetchone()
                if actual is None:
                    connection.execute('INSERT INTO metadata VALUES(?,?)', (ids_key, json.dumps(ids, separators=(',', ':'))))
                else:
                    ids = tuple(strict_json(actual[0].encode('utf-8')))
                self._accepted_local(accepted, connection)
        else:
            ids = tuple(strict_json(original[0].encode('utf-8')))
        if len(ids) != 5 or len(set(ids)) != 5 or any(type(item) is not str for item in ids):
            raise EngineError('owner_setup_journal_invalid', 'Original Goal planned identities are damaged', 422)
        source = OwnerSetupGoalSource(accepted, prepared.origin, prepared.intent.goal, continuation.idempotency_key,
            AcceptedSetupRef(setup_id=prepared.intent.setup_id, content_sha256=row['accepted_sha256']),
            self._services.execution_identity, ids, self, self.engine, self._services.daily_projects,
            self._epoch, threading.get_ident())
        self._goals[id(source)] = (source, receipt.authorization_ref)
        try:
            self.assert_goal_current(source)
            yield source
        finally:
            self.close_goal_source(source)

    def assert_goal_local_current(self, source, connection):
        if (type(source) is not OwnerSetupGoalSource or source._service is not self or source._engine is not self.engine
                or source._epoch is not self._epoch or source._thread_id != threading.get_ident()
                or self._goals.get(id(source), (None,))[0] is not source or source._daily is not self._services.daily_projects):
            raise EngineError('owner_setup_goal_source_denied', 'Only the original current setup Goal context is admitted', 403)
        self._accepted_local(source.accepted, connection)
        row = self._row(connection, source.accepted_setup_ref.setup_id, local=True)
        if row['accepted_sha256'] != source.accepted_setup_ref.content_sha256:
            raise EngineError('owner_setup_goal_source_changed', 'Original accepted setup reference changed', 409)
        if row['goal_result_json'] is None:
            self._draft(connection, source.draft_origin)

    def assert_goal_current(self, source):
        self.assert_accepted_current(source.accepted)
        with self.engine.db.connect() as connection:
            self.assert_goal_local_current(source, connection)

    def goal_authorization_ref(self, source):
        with self.engine.db.connect() as connection:
            self.assert_goal_local_current(source, connection)
        return self._goals[id(source)][1]

    @contextmanager
    def recovery_goal_source(self, intent):
        """Only this setup entry's current original accepted source can resume.

        General API/MCP carriers cannot supply a serialized recovery ticket.
        Their startup must use the fixed setup recovery assembly when needed.
        """
        source = next((item for item in self._accepted.values()
            if item.journal.prepared.intent.setup_id == intent.accepted_setup_ref.setup_id), None)
        if source is None:
            raise EngineError('owner_setup_recovery_source_required', 'Original current setup recovery source is required before Ready', 503)
        with self.goal_source(source) as goal_source:
            if (goal_source.draft_origin != intent.draft_origin or goal_source.accepted_setup_ref != intent.accepted_setup_ref
                    or goal_source.idempotency_key != intent.idempotency_key or goal_source.goal != intent.goal
                    or goal_source.planned_ids != (intent.production_id, intent.run_id, intent.request_revision_id,
                        intent.derivation_id, intent.receipt_id)):
                raise EngineError('owner_setup_recovery_changed', 'Original accepted Goal and fixed planned identities differ', 422)
            yield goal_source

    def close_goal_source(self, source):
        if type(source) is not OwnerSetupGoalSource or source._service is not self:
            raise EngineError('owner_setup_goal_source_denied', 'Cannot close another issuer Goal source', 403)
        self._goals.pop(id(source), None)

    def commit_goal(self, connection, source, result: ProjectGoalAccepted):
        self.assert_goal_local_current(source, connection)
        row = self._row(connection, source.accepted_setup_ref.setup_id, local=True)
        if row['goal_result_json'] is not None and row['goal_result_json'] != canonical(result):
            raise EngineError('owner_setup_goal_already_consumed', 'This real first draft was consumed by another Goal', 409)
        connection.execute("UPDATE owner_setup_journals SET goal_result_json=?,goal_result_sha256=?,phase='completed' WHERE setup_id=?",
            (canonical(result), setup_sha256(result), source.accepted_setup_ref.setup_id))
        self.assert_goal_local_current(source, connection)

    def abort_preparation(self, key, *, preparation):
        self.confirmation.assert_preparation(preparation)
        with self.engine.db.transaction() as connection:
            self.confirmation.assert_preparation(preparation, local=True, connection=connection)
            row = connection.execute('SELECT setup_id,accepted_json FROM owner_setup_journals WHERE instance_id=? AND owner=? AND preparation_key=?',
                (self.engine.instance_id, self.owner, key)).fetchone()
            if row is None or row['accepted_json'] is not None:
                raise EngineError('owner_setup_abort_denied', 'Only the original unaccepted preparation may be aborted', 409)
            connection.execute("UPDATE owner_setup_journals SET phase='aborted' WHERE setup_id=?", (row['setup_id'],))
            self.confirmation.assert_preparation(preparation, local=True, connection=connection)
        # Keep the actual honest draft and original project.create command.

    def status(self, setup_id):
        with self.engine.db.connect() as connection:
            row = self._row(connection, setup_id)
            prepared = self._model(PreparedSetupJournal, row['preparation_json'])
            committed = tuple(item[0] for item in connection.execute('SELECT step_id FROM owner_setup_steps WHERE setup_id=? AND receipt_json IS NOT NULL', (setup_id,)))
            error = connection.execute('SELECT value FROM metadata WHERE key=?', ('owner_setup_block:' + setup_id,)).fetchone()
        if row['goal_result_json'] is not None:
            committed += (prepared.intent.steps[-1].step_id,)
        next_step = next((item.step_id for item in prepared.intent.steps if item.step_id not in committed), None)
        return OwnerSetupStatus(setup_id=setup_id, intent_sha256=setup_sha256(prepared.intent), phase=row['phase'],
            current_step_id=next_step, committed_step_ids=committed,
            code=error[0] if row['phase'] == 'blocked' and error is not None else 'owner_setup_' + row['phase'])

    def close(self):
        self._goals.clear()
        self._actions.clear()
        self._accepted.clear()
        self._accepted_facts.clear()
        primary = None
        try:
            from video_creator.application.local_installation_authority import LocalInstallationAuthority
            if type(self.installation_authority) is LocalInstallationAuthority:
                self.installation_authority.close()
            if self._observer is not None:
                self._observer.close(self._observation)
        except BaseException as error:  # noqa: BLE001 -- Attempt both closes, then rethrow the original exception.
            primary = error
        try:
            self.confirmation.close(None)
        except BaseException:
            if primary is None:
                raise
        if primary is not None:
            raise primary
        self._closed = True
        _retained_services.pop(id(self), None)
