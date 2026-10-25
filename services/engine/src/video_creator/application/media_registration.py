"""Trusted fixed bundle producer registration on the existing execution ledger."""

import hashlib
import json
import time
import threading
from collections.abc import Callable
from pathlib import Path, PurePosixPath
from typing import Literal

from pydantic import BaseModel, ConfigDict

from video_creator.application.asr_result_journal import (
    AsrResultJournal,
    RegisteredOperationExecutor,
)
from video_creator.application.bundles import BundleService, strict_json
from video_creator.application.engine import EngineService, canonical, digest, identity
from video_creator.application.current_final_evidence_runtime import CurrentFinalEvidenceRuntime
from video_creator.application.current_production_blockers import bound_context
from video_creator.application.worker import (
    HEARTBEAT_SECONDS,
    RUN_LEASE_SECONDS,
    WorkerService,
)
from video_creator.domain import contracts as c
from video_creator.domain.bundle import TrustedBundleValidators
from video_creator.domain.affected_repair import ForcedAlignmentRegistration
from video_creator.domain.errors import EngineError
from video_creator.domain.local_material_production import (
    RegistrationConfigLocalV1, parse_local_registration_config,
    parse_local_material_resources,
)
from video_creator.domain.registered_production import (
    AutonomousRegistration,
    CurrentProductionBlockerJournal,
    CurrentProductionUpstreamResult,
    ProductionBinding,
)

PROFILE = "registered-media-bundle-v1"
PACKAGE_ROOT = Path(__file__).resolve().parents[1]
RESOURCE_WAIT_CODES = frozenset({
    "production_resource_missing", "production_resource_changed", "production_resource_invalid",
    "production_configuration_changed", "production_driver_resources_missing",
    "production_narration_not_configured", "production_picture_not_configured", "production_edit_not_configured",
    "production_video_not_configured", "production_video_download_scope_missing", "production_tts_code_changed",
    "production_current_policy_consumer_missing", "credential_missing", "credential_unavailable", "secure_vault_unavailable",
    "route_unavailable", "production_installation_binding_invalid", "qualification_unavailable",
    "production_asr_resource_required", "production_local_resources_missing",
    "asr_resource_changed", "asr_code_changed", "asr_model_changed",
    "production_local_final_consumer_missing",
})


class RegistrationConfig(BaseModel):
    """Private installer input, never a task/tool argument or public Contract."""
    model_config = ConfigDict(extra="forbid", frozen=True)
    format: Literal["registered-media-config-v1"]
    engine_source_sha256: dict[str, c.Sha256]
    asr_resource_manifest: str
    asr_resource_manifest_sha256: c.Sha256
    asr_runtime_manifest_sha256: c.Sha256
    ffmpeg: str
    ffmpeg_sha256: c.Sha256
    ffprobe: str
    ffprobe_sha256: c.Sha256
    asr_route_id: c.Identifier


class RegistrationConfigV2(RegistrationConfig):
    """Installer-only complete upstream registration; v1 stays ASR-only."""
    format: Literal["registered-media-config-v2"]
    autonomous_registration: AutonomousRegistration
    production_resource_manifest: str
    production_resource_manifest_sha256: c.Sha256
    production_runtime_manifest_sha256: c.Sha256
    upstream_profile: Literal["current-registered-autonomous-upstream-v1"]


class RegistrationConfigV3(RegistrationConfigV2):
    format: Literal['registered-media-config-v3']
    alignment_registration: ForcedAlignmentRegistration | None


def _hash(path):
    hasher = hashlib.sha256()
    with path.open("rb") as stream:
        while block := stream.read(1024 * 1024):
            hasher.update(block)
    return hasher.hexdigest()


def _local_file(root, relative):
    name = PurePosixPath(relative)
    if (not isinstance(relative, str) or not name.parts or name.is_absolute()
            or any(part in {".", ".."} or ":" in part or "\\" in part for part in name.parts)):
        raise EngineError("production_resource_denied", "Trusted resources require fixed local relative paths", 403)
    target = root.joinpath(*name.parts)
    for parent in (target, *target.parents):
        if parent == root.parent:
            break
        if parent.is_symlink() or parent.is_junction():
            raise EngineError("production_resource_denied", "Trusted resources cannot cross links or junctions", 403)
    if not target.is_file() or not target.resolve().is_relative_to(root):
        raise EngineError("production_resource_missing", "Required installed production resource is unavailable", 503)
    return target


def _package_sources(root):
    # No rglob through Windows junctions. A full package map cannot omit a module
    # then present an ASR-only stage as an installed engine.
    pending, files = [root], set()
    while pending:
        parent = pending.pop()
        for child in parent.iterdir():
            if child.is_symlink() or child.is_junction():
                raise EngineError("production_resource_denied", "Installed package sources cannot contain directory links", 403)
            if child.is_dir() and child.name != "__pycache__":
                pending.append(child)
            elif child.is_file() and child.suffix == ".py":
                files.add(child.relative_to(root).as_posix())
    return files


class RegisteredMediaRuntime(CurrentFinalEvidenceRuntime):
    def __init__(self, engine: EngineService, configuration_path: Path, expected_sha256: str):
        c.AssetCandidate(staging_id="trusted-config", sha256=expected_sha256, size=1, media_type="application/json", source="installed", rights="local")
        path = Path(configuration_path)
        if not path.is_absolute() or str(path).startswith(("\\\\", "//")) or path.is_symlink() or path.is_junction():
            raise EngineError("production_resource_denied", "Production registration requires trusted local installer configuration", 403)
        if not path.is_file() or path.stat().st_size > 1024 * 1024 or _hash(path) != expected_sha256:
            raise EngineError("production_configuration_missing", "Installed production configuration is missing or changed", 503)
        payload = strict_json(path.read_bytes())
        config_type = (RegistrationConfigV3 if isinstance(payload, dict) and payload.get('format') == 'registered-media-config-v3'
                       else RegistrationConfigV2 if isinstance(payload, dict) and payload.get("format") == "registered-media-config-v2" else RegistrationConfig)
        self.config = (parse_local_registration_config(path.read_bytes())
                       if isinstance(payload, dict) and payload.get('format') == 'registered-media-config-local-v1'
                       else config_type.model_validate(payload))
        self.path, self.sha256, self.engine = path.resolve(), expected_sha256, engine
        source_names = _package_sources(PACKAGE_ROOT)
        if set(self.config.engine_source_sha256) != source_names:
            raise EngineError("production_engine_incomplete", "Registration must cover the complete current engine package, not an ASR-only stage", 503)
        for relative, sha in self.config.engine_source_sha256.items():
            if _hash(_local_file(PACKAGE_ROOT, relative)) != sha:
                raise EngineError("production_code_changed", "Installed engine code differs from the trusted registration", 503)
        root = self.path.parent
        if type(self.config) is RegistrationConfigLocalV1:
            self._initialize_local_runtime(root)
            return
        asr = _local_file(root, self.config.asr_resource_manifest)
        self.production_manifest = None
        if isinstance(self.config, RegistrationConfigV2):
            self.production_manifest = _local_file(root, self.config.production_resource_manifest)
            if _hash(self.production_manifest) != self.config.production_resource_manifest_sha256:
                raise EngineError("production_resource_changed", "Complete installed upstream manifest changed", 503)
        tools = [_local_file(root, value) for value in (self.config.ffmpeg, self.config.ffprobe)]
        if any(_hash(tool) != sha for tool, sha in zip(tools, (self.config.ffmpeg_sha256, self.config.ffprobe_sha256), strict=True)):
            raise EngineError("production_resource_changed", "Configured media tool bytes changed", 503)
        from video_creator.media.bundle_evidence import BundleMediaEvidence
        from video_creator.media.ffmpeg import FFmpegRuntime
        from video_creator.providers.asr_resources import load_asr_resources
        from video_creator.workflows.bundle_producer import (
            create_registered_media_producer,
        )

        resources = load_asr_resources(asr, self.config.asr_resource_manifest_sha256, self.config.asr_runtime_manifest_sha256)
        staging = engine.db.data_dir / "Staging"
        staging.mkdir(exist_ok=True)
        decoder = FFmpegRuntime(*tools, staging)
        self.decoder = lambda file, mime: decoder.probe(file, decode=True)
        media = BundleMediaEvidence(resources.python, engine.db.data_dir)
        self.bundle = BundleService(engine, TrustedBundleValidators(media_validator=lambda file, mime: decoder.probe(file, decode=True),
            frame_validator=media.frame_validator), audio_clock_authority=media.audio_clock_authority)
        self.worker = WorkerService(engine, workflow_version=PROFILE)
        self.journal = AsrResultJournal(engine, self.worker, registration_sha256=self.sha256,
            resource_manifest_sha256=self.config.asr_resource_manifest_sha256,
            runtime_manifest_sha256=self.config.asr_runtime_manifest_sha256, asr_route_id=self.config.asr_route_id,
            original_source_sha256=self.config.engine_source_sha256)
        self.bundle._original_asr_journal = self.journal
        self.executor = RegisteredOperationExecutor(engine, self.journal)
        runtime = engine.db.data_dir / "ProductionRuntime"
        runtime.mkdir(exist_ok=True)
        if runtime.is_symlink() or runtime.is_junction() or not runtime.resolve().is_relative_to(engine.db.data_dir):
            raise EngineError("production_resource_denied", "Production child runtime must remain in its owned instance", 403)
        self.runtime_root = runtime
        self._active_final_ports = {}
        self.bundle._production_services_runtime = self
        self.engine._registered_plan_source = self.bundle
        self.bundle._production_services_held = {}
        self.bundle._affected_execution_held = {}
        self.bundle._affected_observation_held = {}
        self.produce = create_registered_media_producer(engine=engine, bundle=self.bundle, executor=self.executor,
            resource_manifest_path=asr, resource_manifest_sha256=self.config.asr_resource_manifest_sha256,
            runtime_manifest_sha256=self.config.asr_runtime_manifest_sha256, storage_root=engine.db.data_dir, runtime_root=runtime)
        route = engine.configured_route(self.config.asr_route_id)
        if route.source != "owned_local" or route.capability != "transcription" or route.credential_ref or route.max_operation_cost.units():
            raise EngineError("production_asr_route_invalid", "Registered ASR route must be an existing credential-free zero-cost local transcription capability", 503)

    def _initialize_local_runtime(self, root):
        """Build actual local services without importing/loading ASR model resources."""
        import sys
        from video_creator.media.bundle_evidence import BundleMediaEvidence
        from video_creator.media.ffmpeg import FFmpegRuntime

        self.production_manifest = _local_file(root, self.config.production_resource_manifest)
        if _hash(self.production_manifest) != self.config.production_resource_manifest_sha256:
            raise EngineError('production_resource_changed', 'Installed local resource manifest changed', 503)
        self.local_resources = parse_local_material_resources(self.production_manifest.read_bytes())
        runtime_index = _local_file(self.production_manifest.parent, self.local_resources.runtime_manifest)
        if _hash(runtime_index) != self.config.production_runtime_manifest_sha256:
            raise EngineError('production_resource_changed', 'Installed local runtime index changed', 503)
        tools = [_local_file(root, value) for value in (self.config.ffmpeg, self.config.ffprobe)]
        if any(_hash(tool) != sha for tool, sha in zip(tools,
                (self.config.ffmpeg_sha256, self.config.ffprobe_sha256), strict=True)):
            raise EngineError('production_resource_changed', 'Installed local media tools changed', 503)
        for route_id in (self.config.local_registration.input_audio_route_id,
                         self.config.local_registration.input_visual_route_id,
                         self.config.local_registration.edit_route_id,
                         self.config.local_registration.master_index_route_id):
            route = self.engine.configured_route(route_id)
            if (route.source != 'owned_local' or route.credential_ref or route.max_operation_cost.units()
                    or not route.destination.startswith('local:')):
                raise EngineError('production_local_route_invalid', 'Local material routes are credentialless, zero cost and have no remote destination', 503)
        engine = self.engine
        staging = engine.db.data_dir / 'Staging'
        staging.mkdir(exist_ok=True)
        decoder = FFmpegRuntime(*tools, staging)
        self.decoder = lambda file, mime: decoder.probe(file, decode=True)
        # This is the same already-launched protected Engine interpreter. The
        # actual native full-map observation covers it; not an ASR Python/model.
        media = BundleMediaEvidence(Path(sys.executable), engine.db.data_dir)
        self.bundle = BundleService(engine, TrustedBundleValidators(media_validator=self.decoder,
            frame_validator=media.frame_validator), audio_clock_authority=media.audio_clock_authority)
        self.worker = WorkerService(engine, workflow_version=PROFILE)
        self.journal = AsrResultJournal(engine, self.worker, registration_sha256=self.sha256,
            resource_manifest_sha256=self.config.asr_resource_manifest_sha256,
            runtime_manifest_sha256=self.config.asr_runtime_manifest_sha256,
            asr_route_id=self.config.asr_route_id, original_source_sha256=self.config.engine_source_sha256)
        self.bundle._original_asr_journal = self.journal
        self.executor = RegisteredOperationExecutor(engine, self.journal)
        runtime = engine.db.data_dir / 'ProductionRuntime'
        runtime.mkdir(exist_ok=True)
        if runtime.is_symlink() or runtime.is_junction() or not runtime.resolve().is_relative_to(engine.db.data_dir):
            raise EngineError('production_resource_denied', 'Local runtime must remain in its actual instance', 403)
        self.runtime_root, self._active_final_ports = runtime, {}
        self.bundle._production_services_runtime = self
        self.engine._registered_plan_source = self.bundle
        self.bundle._production_services_held = {}
        self.bundle._affected_execution_held = {}
        self.bundle._affected_observation_held = {}
        self.produce = None  # The actual final factory is invoked only after real upstream masters.
        from video_creator.application.local_material_sources import LocalMaterialSourceService
        self.local_plan_sources = LocalMaterialSourceService(self)
        self.engine._local_material_plan_source = self.local_plan_sources

    def _require_selected_asr(self):
        if self.config.asr_resource_manifest is None:
            raise EngineError('production_asr_resource_required', 'Actual final transcript/subtitle/RAG requires installed ASR resources', 503)
        manifest = _local_file(self.path.parent, self.config.asr_resource_manifest)
        if _hash(manifest) != self.config.asr_resource_manifest_sha256:
            raise EngineError('production_resource_changed', 'Selected original ASR manifest changed', 503)
        route = self.engine.configured_route(self.config.asr_route_id)
        if route.source != 'owned_local' or route.capability != 'transcription' or route.credential_ref or route.max_operation_cost.units():
            raise EngineError('production_asr_route_invalid', 'Actual zero-cost owned ASR route required', 503)
        from video_creator.providers.asr_resources import load_asr_resources
        return load_asr_resources(manifest, self.config.asr_resource_manifest_sha256,
                                  self.config.asr_runtime_manifest_sha256)

    def _preflight_local_resources(self, request):
        """Read/hash original indexed local bytes; no driver, ASR or network work."""
        if _hash(self.path) != self.sha256 or self.production_manifest is None:
            raise EngineError('production_configuration_changed', 'Original local registration changed', 503)
        if _hash(self.production_manifest) != self.config.production_resource_manifest_sha256:
            raise EngineError('production_resource_changed', 'Original local resource manifest changed', 503)
        from video_creator.providers.local_material_resources import LocalMaterialResources
        resources = LocalMaterialResources(manifest_path=self.production_manifest,
            manifest_sha256=self.config.production_resource_manifest_sha256,
            runtime_manifest_sha256=self.config.production_runtime_manifest_sha256)
        resources.resource(resources.config.edit.ffmpeg)
        resources.resource(resources.config.edit.ffprobe)
        registration = self.config.local_registration
        for route_id in (registration.input_audio_route_id, registration.input_visual_route_id,
                         registration.edit_route_id, registration.master_index_route_id):
            route = self.engine.configured_route(route_id)
            if (route_id not in request.policy.allowed_provider_routes or route.source != 'owned_local'
                    or route.credential_ref or route.max_operation_cost.units()
                    or not route.destination.startswith('local:')):
                raise EngineError('production_route_scope_denied', 'Actual request must include original zero-cost local route', 403)

    def _final_producer(self, lease, *, production_services, execution_ports):
        if type(self.config) is RegistrationConfigLocalV1:
            context = self.local_plan_sources.final_context(lease, execution_ports,
                policy=self.engine.get_request(lease).automation.mode == 'unattended')
            if 'mixed_audio' in context.selection.master_roles:
                self._require_selected_asr()
            return super()._final_producer(lease, production_services=production_services,
                execution_ports=execution_ports, local_material_context=context)
        return super()._final_producer(lease, production_services=production_services, execution_ports=execution_ports)

    def _remember_current_services_check(self, lease, execution_ports, policy):
        with self.bundle._lock:
            values = [value for value in self.bundle._production_services_held.values()
                if value[1] is execution_ports and value[2] == lease]
        if (len(values) != 1 or values[0][3] != threading.get_ident() or values[0][5] != policy
                or values[0][6:] != self.installation_resource_identity[1:]):
            raise EngineError('local_final_services_denied', 'Original held same-fence/thread/mode services required.', 403)
        with self.engine.db.connect_readonly() as connection:
            self.engine._lease(connection, lease)
            _run, _production, _request, binding = bound_context(self.engine, connection, lease.run_id, self.sha256)
        if binding != values[0][4]:
            raise EngineError('local_final_services_conflict', 'Original service request binding changed.', 409)

    @property
    def installation_resource_identity(self):
        if isinstance(self.config, (RegistrationConfigV2, RegistrationConfigLocalV1)):
            return (self.sha256, self.config.production_resource_manifest_sha256,
                    self.config.production_runtime_manifest_sha256)
        return (self.sha256, self.config.asr_resource_manifest_sha256,
                self.config.asr_runtime_manifest_sha256)

    def bind(self, lease, worker):
        if _hash(self.path) != self.sha256:
            raise EngineError("production_configuration_changed", "Trusted registration changed after Worker startup", 503)
        request = self.engine.get_request(lease)
        context = self.bundle.context(lease)
        assets = []
        for identifier in request.inputs.asset_ids:
            record = self.bundle.asset(lease, identifier)
            self.bundle.content_path(lease, identifier)
            assets.append((identifier, record.sha256))
        binding = ProductionBinding(instance_id=self.engine.instance_id, production_id=context.production_id,
            run_id=lease.run_id, request_revision_id=context.request_revision_id, request_sha256=digest(canonical(request)),
            registration_sha256=self.sha256, input_assets=tuple(assets))
        body = canonical(binding)
        with self.engine.db.transaction() as connection:
            worker._presence(connection, lease.worker_id)
            self.engine._lease(connection, lease)
            previous = connection.execute("SELECT * FROM execution_bindings WHERE run_id=?", (lease.run_id,)).fetchone()
            if previous and (previous["body"] != body or previous["content_sha256"] != digest(body)):
                raise EngineError("execution_binding_conflict", "Run retains a different original workflow or resource binding", 409)
            connection.execute("INSERT OR IGNORE INTO execution_bindings VALUES(?,?,?)", (lease.run_id, body, digest(body)))
            connection.execute("UPDATE worker_presence SET state='executing',active_run_id=? WHERE worker_id=?", (lease.run_id, lease.worker_id))
        return binding

    def master_assets(self, lease, *, selection=None):
        if selection is not None:
            from video_creator.domain.local_bundle import LocalMasterSelectionV1
            if (type(selection) is not LocalMasterSelectionV1
                    or not isinstance(self.config, RegistrationConfigLocalV1)
                    or selection.request_ref.run_id != lease.run_id):
                raise EngineError('local_master_selection_invalid', 'Local masters require the original same-Run selection.', 409)
            self.local_plan_sources.assert_selection_current(lease, selection)
        step = self.engine.read_step(lease, "media-master")
        if not step or step["status"] != "succeeded":
            raise EngineError("production_media_capability_missing", "Upstream registered media production must create actual video, independent narration, mix and cover", 503)
        result = strict_json(step["result_json"].encode())
        payload = result.get("result") if isinstance(result, dict) else None
        roles = payload.get("media_roles") if isinstance(payload, dict) else None
        required = set(selection.master_roles) if selection is not None else {"video", "narration_audio", "mixed_audio", "cover"}
        if not isinstance(roles, dict) or set(roles) != required or any(not isinstance(value, str) for value in roles.values()):
            raise EngineError("production_media_roles_invalid", "Committed media-master must bind all four exact registered output roles", 422)
        committed = result.get("asset_ids")
        if (not isinstance(committed, list) or len(set(committed)) != len(committed)
                or set(roles.values()) != set(committed) or len(set(roles.values())) != len(required)):
            raise EngineError("production_media_roles_invalid", "Media master role IDs must be distinct actual committed Step assets", 422)
        with self.engine.db.connect() as connection:
            self.engine._lease(connection, lease)
            operations = connection.execute("SELECT status,settled FROM operations WHERE run_id=? AND step_key='media-master'", (lease.run_id,)).fetchall()
        if any(not row["settled"] or row["status"] in {"submitting", "pending", "unknown"} for row in operations):
            raise EngineError("media_master_evidence_pending", "Original media-master Operations require reconciliation before their assets can be consumed", 409, "reconcile")
        if not operations or any(row["status"] != "succeeded" for row in operations):
            raise EngineError("media_master_evidence_missing", "Actual media-master requires its original successful settled Operations", 409)
        for role, identifier in roles.items():
            record = self.bundle.asset(lease, identifier)
            self.bundle.content_path(lease, identifier)
            if (not record.probe.decoded or role == "video" and not record.probe.has_video
                    or role in {"narration_audio", "mixed_audio"} and not record.probe.has_audio
                    or role == "cover" and not record.media_type.startswith("image/")):
                raise EngineError("production_media_roles_invalid", "Actual registered media does not satisfy its committed output role", 422)
        return roles

    def invoke(self, lease, *, cancel=None, deadline_monotonic=None):
        if isinstance(self.config, (RegistrationConfigV2, RegistrationConfigLocalV1)):
            return self._invoke_current(lease, cancel=cancel, deadline_monotonic=deadline_monotonic)
        revisions = self.bundle.creative_revisions(lease)
        if not {"insight", "brief", "plan", "script", "storyboard", "quality"} <= {value.kind for value in revisions}:
            raise EngineError("production_creative_capability_missing", "Upstream Agent must create immutable creative versions; caller-written drafts are not required inputs", 503)
        roles = self.master_assets(lease)
        return self.produce(lease, video_asset_id=roles["video"], narration_asset_id=roles["narration_audio"],
            mixed_asset_id=roles["mixed_audio"], cover_asset_id=roles["cover"], asr_route_id=self.config.asr_route_id,
            cancel=cancel, deadline_monotonic=deadline_monotonic)

    def _current_services(self, lease):
        """Bind only the actual installed identity, after original Worker startup."""
        from video_creator.application.production_ports import ProductionPorts

        request = self.engine.get_request(lease)
        with self.engine.db.connect() as connection:
            run = self.engine._lease(connection, lease)
            production = self.engine._production(connection, run["production_id"])
        registered = self.engine._authorization_identity(production["owner"])
        issuer = self.engine.production_admissions
        expected = self.installation_resource_identity
        if ((registered.registration_sha256, registered.resource_manifest_sha256,
                registered.runtime_manifest_sha256) != expected):
            raise EngineError("production_installation_binding_invalid", "Current upstream requires this original installed registration and project scope", 503)
        # This concrete guard verifies the complete held installation partition,
        # current qualification and registry. No config JSON installs an issuer.
        with issuer.current_guard(registered) as guard:
            observed = guard.installation
            if (observed.instance_id != self.engine.instance_id
                    or (observed.registration_sha256, observed.resource_manifest_sha256,
                        observed.runtime_manifest_sha256) != expected):
                raise EngineError("production_installation_binding_invalid", "Current actual resources differ from the upstream registration", 503)
            with self.engine.db.connect() as connection:
                current_run = self.engine._lease(connection, lease)
                current_production = self.engine._production(connection, current_run["production_id"])
                issuer._guard(connection, guard)
                issuer._request(connection, current_production, current_run, registered)
        if (_hash(self.path) != self.sha256 or self.production_manifest is None
                or _hash(self.production_manifest) != self.config.production_resource_manifest_sha256):
            raise EngineError("production_resource_changed", "Original registered upstream resources changed", 503)
        local = type(self.config) is RegistrationConfigLocalV1
        registration = self.config.local_registration if local else self.config.autonomous_registration
        arguments = dict(engine=self.engine, worker=self.worker, bundle=self.bundle,
            executor=self.executor, registration=registration, subject=production["owner"],
            storage_root=self.engine.db.data_dir, runtime_root=self.runtime_root,
            decoder=self.decoder, resource_manifest_path=self.production_manifest,
            resource_manifest_sha256=self.config.production_resource_manifest_sha256,
            runtime_manifest_sha256=self.config.production_runtime_manifest_sha256)
        if not local:
            arguments['prepare_plan_repair_targets'] = self.bundle.prepare_plan_repair_targets
        if isinstance(self.config, (RegistrationConfigV3, RegistrationConfigLocalV1)):
            arguments['alignment_registration'] = self.config.alignment_registration
        if request.automation.mode == "unattended":
            ports = issuer.execution_ports(registered)
            begin = ports.begin_execution(lease)
            if begin.state != "allowed":
                raise EngineError(begin.blocker_code or "production_authorization_required", "Actual same-fence begin_execution is required before upstream work", 403)
            # Ensure this committed action can produce only a request-bound
            # declaration. It is not an approval of a future plan.
            ports.rights_proposal(lease)
            try:
                if local:
                    from video_creator.workflows.local_material_production import (
                        create_local_policy_engine_services as create_current_policy_engine_services,
                        run_local_material_policy_upstream as run_current_policy_upstream,
                    )
                else:
                    from video_creator.workflows.current_engine_production import create_current_policy_engine_services
                    from video_creator.workflows.autonomous_production import run_current_policy_upstream
            except ImportError:
                raise EngineError("production_current_policy_consumer_missing", "The fixed current policy Media consumer is not installed", 503) from None
            services = create_current_policy_engine_services(policy_execution_ports=ports, **arguments)
            self._remember_current_services(lease, services, ports, True)
            return services, ports, run_current_policy_upstream, True
        ports = ProductionPorts(self.engine, self.worker, registration.rights_declaration, self.sha256)
        ports.rights_proposal(lease)
        if local:
            from video_creator.workflows.local_material_production import (
                create_local_engine_services as create_current_engine_services,
                run_local_material_upstream as run_autonomous_upstream,
            )
        else:
            from video_creator.workflows.current_engine_production import create_current_engine_services
            from video_creator.workflows.autonomous_production import run_autonomous_upstream

        services = create_current_engine_services(production_ports=ports, **arguments)
        self._remember_current_services(lease, services, ports, False)
        return services, ports, run_autonomous_upstream, False

    def _remember_current_services(self, lease, services, ports, policy):
        """Only the immediately preceding original fixed factories call this source boundary."""
        from video_creator.workflows.autonomous_production import AutonomousServices, CurrentPolicyServices
        expected_type = CurrentPolicyServices if policy else AutonomousServices
        local = type(self.config) is RegistrationConfigLocalV1
        if local:
            from video_creator.workflows.local_material_production import LocalMaterialServices, LocalMaterialPolicyServices
            expected_type = LocalMaterialPolicyServices if policy else LocalMaterialServices
        if (type(services) is not expected_type or services.engine is not self.engine
                or services.worker is not self.worker or services.bundle is not self.bundle
                or services.executor is not self.executor or services.registration_sha256 != self.sha256
                or (policy and services.policy_execution_ports is not ports)
                or (not policy and getattr(services, 'production_ports' if local else 'execution_ports', None) is not ports)):
            raise EngineError('production_services_source_invalid', 'Original actual registered factory objects required', 403)
        with self.engine.db.connect_readonly() as connection:
            run = self.engine._lease(connection, lease)
            _run, production, request, binding = bound_context(self.engine, connection, lease.run_id, self.sha256)
        registered = self.engine._authorization_identity(production['owner'])
        issuer = self.engine.production_admissions
        with issuer.current_guard(registered) as guard:
            with self.engine.db.connect_readonly() as connection:
                issuer._guard(connection, guard)
                issuer._request(connection, production, run, registered)
                if (request.automation.mode == 'unattended') != policy:
                    raise EngineError('production_services_mode_invalid', 'Actual human/policy mode changed', 403)
        source = (services, ports, lease, threading.get_ident(), binding, policy,
                  self.config.production_resource_manifest_sha256, self.config.production_runtime_manifest_sha256)
        with self.bundle._lock:
            self.bundle._production_services_held[(lease.run_id, id(services))] = source

    def _checked_upstream_result(self, lease, result, *, policy):
        if type(self.config) is RegistrationConfigLocalV1:
            from video_creator.domain.local_bundle import CurrentProductionUpstreamResultV2
            if type(result) is not CurrentProductionUpstreamResultV2:
                raise EngineError('production_upstream_result_invalid', 'Local runner must return the sole versioned applicable-master result.', 422)
            checked = result
        elif policy:
            if type(result) is not CurrentProductionUpstreamResult:
                raise EngineError("production_upstream_result_invalid", "Current policy runner must return the sole typed Backend result", 422)
            checked = result
        else:
            from video_creator.workflows.autonomous_production import AutonomousUpstreamResult

            if type(result) is not AutonomousUpstreamResult or result.state not in {"masters_ready", "waiting_user", "needs_reconciliation"}:
                raise EngineError("production_upstream_result_invalid", "Original human runner returned an unsupported result", 422)
            checked = CurrentProductionUpstreamResult(run_id=lease.run_id, fencing_token=lease.fencing_token,
                state=result.state, media_roles=result.media_roles or {}, blocker_code=result.blocker_code)
        if (checked.run_id, checked.fencing_token) != (lease.run_id, lease.fencing_token):
            raise EngineError("production_upstream_binding_conflict", "Upstream result differs from the original Run and attempt fence", 409)
        if checked.state == "waiting_user":
            with self.engine.db.connect() as connection:
                run = self.engine._run(connection, lease.run_id)
                waiting = connection.execute("SELECT id FROM creative_revisions WHERE id=? AND production_id=? AND run_id=?",
                    (run["waiting_revision_id"], run["production_id"], run["id"])).fetchone()
            if (run["fencing_token"] != lease.fencing_token or run["status"] != "waiting_user"
                    or run["worker_id"] is not None or run["lease_until_us"] != 0 or not waiting):
                raise EngineError("production_upstream_wait_invalid", "Human wait must already retain its real same-Run version and release its lease", 409)
        elif checked.state == "needs_reconciliation":
            with self.engine.db.connect() as connection:
                run = self.engine._run(connection, lease.run_id)
                unknown = connection.execute("SELECT 1 FROM operations WHERE run_id=? AND (settled=0 OR status IN ('submitting','pending','unknown')) LIMIT 1",
                    (lease.run_id,)).fetchone()
            if run["fencing_token"] != lease.fencing_token or not unknown:
                raise EngineError("production_upstream_reconciliation_invalid", "A result label cannot replace original unresolved Operations", 409)
            raise EngineError(checked.blocker_code or "production_upstream_reconciliation_pending", "Original Operations require reconciliation before any further generation", 409, "reconcile")
        return checked

    def _invoke_current(self, lease, *, cancel=None, deadline_monotonic=None):
        from video_creator.workflows.attempt_control import attempt_control

        with attempt_control(cancel, deadline_monotonic).activate() as control:
            services, ports, runner, policy = self._current_services(lease)
            final_checkpoint = self._final_checkpoint(lease.run_id)
            if final_checkpoint is not None:
                control.check()
                self._current_final_execution_facts(lease, ports, policy)
                continuation = self.claim_current_final_evidence(lease)
                producer, final_ports = self._final_producer(lease, production_services=services, execution_ports=ports)
                self._active_final_ports[lease.run_id] = final_ports
                resume = getattr(producer, 'continue_current_final_evidence', None)
                if not callable(resume):
                    raise EngineError('final_evidence_consumer_missing', 'Original bound final continuation is not installed', 503)
                source=final_ports.read_current_final_diagnostic_source(continuation)
                if source is not None and source.source.resume_context is not None:
                    import inspect
                    if 'diagnostic_source' not in inspect.signature(resume).parameters:
                        raise EngineError('diagnostic_recovery_consumer_missing','Bound Media consumer must explicitly consume the actual committed diagnostic work context',503)
                    return resume(ordinary_lease=lease,continuation=continuation,diagnostic_source=source,
                        policy_execution_ports=ports,control=control)
                return resume(ordinary_lease=lease, continuation=continuation,
                    policy_execution_ports=ports, control=control)
            checkpoint = self.runtime_root / ("CurrentProduction-" + digest(lease.run_id) + ".sqlite")
            upstream = runner(services, lease, checkpoint_path=checkpoint,
                cancel=cancel, deadline_monotonic=deadline_monotonic)
            result = self._checked_upstream_result(lease, upstream, policy=policy)
            if result.state != "masters_ready":
                return result
            control.check()
            with self.engine.db.connect() as connection:
                run = self.engine._lease(connection, lease)
                rows = connection.execute("SELECT * FROM creative_revisions WHERE production_id=? AND run_id=? ORDER BY rowid",
                    (run["production_id"], lease.run_id)).fetchall()
            same_run = {}
            for row in rows:
                if digest(row["body"]) != row["content_sha256"]:
                    raise EngineError("production_creative_evidence_invalid", "Original same-Run creative bytes changed", 422)
                value = c.CreativeRevision.model_validate(strict_json(row["body"].encode("utf-8")))
                if (value.revision_id, value.kind) != (row["id"], row["kind"]):
                    raise EngineError("production_creative_evidence_invalid", "Original creative row and typed body differ", 422)
                same_run[value.kind] = value
            required = ({'script', 'plan', 'quality'} if type(self.config) is RegistrationConfigLocalV1
                        else {"insight", "brief", "plan", "script", "storyboard", "quality"})
            if not required <= set(same_run):
                raise EngineError("production_creative_capability_missing", "Current same-Run upstream did not commit all six creative versions", 503)
            local_context = None
            if type(self.config) is RegistrationConfigLocalV1:
                local_context = self.local_plan_sources.final_context(lease, ports, policy=policy)
                if result.selection != local_context.selection:
                    raise EngineError('local_master_selection_invalid', 'Upstream selection differs from the actual current approved plan.', 409)
            roles = self.master_assets(lease, selection=local_context.selection if local_context is not None else None)
            if roles != result.media_roles:
                raise EngineError("production_upstream_binding_conflict", "Upstream master claims differ from the original committed and decoded assets", 409)
            admission = ports.production_admission if policy else ports.current_production_admission
            plan = admission(lease, same_run["plan"].revision_id, phase="plan", action="execute_plan")
            quality = admission(lease, same_run["quality"].revision_id, phase="quality", action="continue_bundle_validation")
            for fact in (plan, quality):
                if (fact.state != "allowed" or fact.run_id != lease.run_id
                        or fact.fencing_token != lease.fencing_token or fact.registration_sha256 != self.sha256):
                    raise EngineError(fact.blocker_code or "production_current_admission_required", "Current committed plan and quality need their actual current execution facts", 403)
            rights = ports.production_rights(lease, same_run["plan"].revision_id) if policy else ports.current_production_rights(lease, same_run["plan"].revision_id)
            control.check()
            producer, final_ports = self._final_producer(lease, production_services=services, execution_ports=ports)
            self._active_final_ports[lease.run_id] = final_ports
            if local_context is not None:
                return producer(lease, selection=local_context.selection, media_roles=roles, asr_route_id=self.config.asr_route_id,
                    cancel=cancel, deadline_monotonic=deadline_monotonic, plan_admission=plan, production_rights_fact=rights)
            return producer(lease, video_asset_id=roles["video"], narration_asset_id=roles["narration_audio"],
                mixed_asset_id=roles["mixed_audio"], cover_asset_id=roles["cover"], asr_route_id=self.config.asr_route_id,
                cancel=cancel, deadline_monotonic=deadline_monotonic, plan_admission=plan, production_rights_fact=rights)

    def park(self, lease, code):
        request = self.engine.get_request(lease)
        revision = c.CreativeRevision(revision_id=identity("production-blocker"), kind="quality", body={"code": code,
            "workflow_version": PROFILE, "message": "Configured production capability or actual release evidence is not ready"})
        self.engine.commit_creative_revision(lease, revision)
        with self.engine.db.transaction() as connection:
            run = self.engine._lease(connection, lease)
            self.engine._evidence_execution_guard(connection, self.engine._production(connection, run["production_id"]), request)
            connection.execute("UPDATE runs SET status='waiting_user',waiting_revision_id=?,worker_id=NULL,lease_until_us=0 WHERE id=?", (revision.revision_id, lease.run_id))
            connection.execute("UPDATE productions SET status='waiting_user' WHERE id=?", (run["production_id"],))
            self.engine._event(connection, self.engine._run(connection, lease.run_id), "production.blocked", revision.revision_id)

    def _current_stop_result(self, lease, result, states):
        from video_creator.domain.local_bundle import CurrentProductionUpstreamResultV2
        expected = CurrentProductionUpstreamResultV2 if type(self.config) is RegistrationConfigLocalV1 else CurrentProductionUpstreamResult
        if (not isinstance(self.config, (RegistrationConfigV2, RegistrationConfigLocalV1)) or type(result) is not expected
                or result.state not in states or result.media_roles or not result.blocker_code
                or (result.run_id, result.fencing_token) != (lease.run_id, lease.fencing_token)):
            raise EngineError("production_blocker_result_invalid", "Only the trusted original v2 same-fence result can stop this Run", 422)

    def park_current_upstream(self, ordinary_lease, result):
        from video_creator.application.current_production_blockers import (
            PREFIX, bound_context, parse_journal, require_settled, require_wait,
        )

        lease = ordinary_lease
        self._current_stop_result(lease, result, {"waiting_authorization", "resource_not_ready"})
        with self.engine.db.transaction() as connection:
            run, production, _request, binding = bound_context(self.engine, connection, lease.run_id, self.sha256)
            previous = connection.execute("SELECT value FROM metadata WHERE key=?", (PREFIX + lease.run_id,)).fetchone()
            if previous is not None:
                journal = parse_journal(previous[0], now=self.engine.clock())
                if journal.binding != binding or journal.result != result:
                    raise EngineError("production_blocker_changed", "A different original blocker cannot be replaced", 409)
                require_wait(run, journal)
                require_settled(connection, lease.run_id)
                return
            self.engine._lease(connection, lease)
            require_settled(connection, lease.run_id)
            if type(self.config) is RegistrationConfigLocalV1:
                from video_creator.domain.local_bundle import CurrentProductionBlockerJournalV2
                journal = CurrentProductionBlockerJournalV2(binding=binding, result=result, blocked_at_us=self.engine.clock())
            else:
                journal = CurrentProductionBlockerJournal(format="current-production-blocker-v1", binding=binding,
                    result=result, blocked_at_us=self.engine.clock())
            body = canonical(journal)
            connection.execute("INSERT INTO metadata(key,value) VALUES(?,?)", (PREFIX + lease.run_id, body))
            connection.execute("UPDATE runs SET status='waiting_user',waiting_revision_id=NULL,worker_id=NULL,lease_until_us=0 WHERE id=?", (lease.run_id,))
            connection.execute("UPDATE productions SET status='waiting_user' WHERE id=?", (production["id"],))
            self.engine._event(connection, self.engine._run(connection, lease.run_id), "production.capability_blocked", digest(body))

    def finish_current_upstream_denied(self, ordinary_lease, result):
        from video_creator.application.current_production_blockers import bound_context, require_settled

        lease = ordinary_lease
        self._current_stop_result(lease, result, {"denied"})
        with self.engine.db.transaction() as connection:
            run, production, _request, _binding = bound_context(self.engine, connection, lease.run_id, self.sha256)
            if (run["status"] == "failed" and run["fencing_token"] == lease.fencing_token
                    and run["worker_id"] is None and run["lease_until_us"] == 0 and not run["cancellation_requested"]):
                previous = connection.execute("SELECT 1 FROM events WHERE run_id=? AND event_type='production.capability_denied' AND entity_revision_id=?",
                    (lease.run_id, result.blocker_code)).fetchone()
                require_settled(connection, lease.run_id)
                if previous is not None:
                    return
            self.engine._lease(connection, lease)
            require_settled(connection, lease.run_id)
            connection.execute("UPDATE runs SET status='failed',waiting_revision_id=NULL,worker_id=NULL,lease_until_us=0 WHERE id=?", (lease.run_id,))
            connection.execute("UPDATE productions SET status='failed' WHERE id=?", (production["id"],))
            self.engine._event(connection, self.engine._run(connection, lease.run_id), "production.capability_denied", result.blocker_code)

    def _declaration_resume_current(self, production, request):
        if request.automation.mode != "interactive":
            return
        registration = (self.config.local_registration if type(self.config) is RegistrationConfigLocalV1
                        else self.config.autonomous_registration)
        declaration = registration.rights_declaration
        now = self.engine.clock()
        if (declaration.declaring_subject != production["owner"] or production["project_id"] not in declaration.project_ids
                or declaration.expires_at_us is not None and declaration.expires_at_us <= now
                or any(right.valid_from_us is not None and right.valid_from_us > now
                    or right.expires_at_us is not None and right.expires_at_us <= now for right in declaration.rights)):
            raise EngineError("production_rights_policy_missing", "Original finite Owner declaration is no longer current", 403)

    def _preflight_blocker_resources(self, request):
        """Only local files/routes/handles; never a provider or executable probe."""
        if type(self.config) is RegistrationConfigLocalV1:
            return self._preflight_local_resources(request)
        from video_creator.providers.production_resources import ProductionResources
        from video_creator.providers.wan_video import SYNTHESIS_PATH, download_hosts, endpoint
        from video_creator.workflows.production_drivers import create_registered_production_drivers

        if self.production_manifest is None or _hash(self.path) != self.sha256:
            raise EngineError("production_configuration_changed", "Original installed v2 registration changed", 503)
        resources = ProductionResources(self.production_manifest, self.config.production_resource_manifest_sha256,
            self.config.production_runtime_manifest_sha256)
        piper = resources.section("narration", "piper")
        if type(piper.get("version")) is not str or not piper["version"]:
            raise EngineError("production_narration_not_configured", "Original Piper runtime version is not indexed", 503)
        for name in ("python", "worker", "model", "model_config", "license_document"):
            if type(piper.get(name)) is not str:
                raise EngineError("production_narration_not_configured", "Original Piper resources are incomplete", 503)
            resources.resource(piper[name])
        if _hash(resources.resource(piper["worker"])) != _hash(PACKAGE_ROOT / "media/piper_worker.py"):
            raise EngineError("production_tts_code_changed", "Original installed Piper worker differs from current source", 503)
        picture = resources.section("picture", "wan2.7")
        video_destination = endpoint(picture) + SYNTHESIS_PATH
        download_hosts(picture)
        if picture.get("resolution") not in {"720P", "1080P"}:
            raise EngineError("production_video_not_configured", "Original video output profile is unavailable", 503)
        edit = resources.section("edit", "ffmpeg")
        for name in ("ffmpeg", "ffprobe"):
            if type(edit.get(name)) is not str:
                raise EngineError("production_edit_not_configured", "Original indexed editor resources are incomplete", 503)
            resources.resource(edit[name])
        registration = self.config.autonomous_registration
        routes = ((registration.text_route_id, "text", None),
            (registration.narration_route_id, "speech", "local:piper-tts-v1"),
            (registration.picture_route_id, "video", video_destination),
            (registration.edit_route_id, "render", "local:ffmpeg-production-edit-v1"),
            (registration.master_index_route_id, "video", "local:registered-master-index-v1"))
        for route_id, capability, destination in routes:
            route = self.engine.configured_route(route_id)
            if route_id not in request.policy.allowed_provider_routes or route.capability != capability or destination is not None and route.destination != destination:
                raise EngineError("production_route_scope_denied", "Original current request does not include the fixed production route", 403)
            if destination is not None and destination.startswith("local:") and (
                    route.source != "owned_local" or route.credential_ref or route.max_operation_cost.units()):
                raise EngineError("production_route_scope_denied", "Original local route must remain credential-free and zero-cost", 403)
            if route.source != "owned_local" and not request.policy.external_transfer_allowed:
                raise EngineError("external_transfer_denied", "Original request has no external production transfer permission", 403)
            if destination == video_destination and not route.credential_ref:
                raise EngineError("credential_missing", "Original registered video route has no usable credential handle", 503)
            if route.credential_ref:
                handle = self.executor.vault.resolve(route.credential_ref)
                del handle  # local availability only; never reveal/export or retain a secret
        create_registered_production_drivers(engine=self.engine, worker=self.worker, bundle=self.bundle,
            storage_root=self.engine.db.data_dir, runtime_root=self.runtime_root, decoder=self.decoder,
            resource_manifest_path=self.production_manifest,
            resource_manifest_sha256=self.config.production_resource_manifest_sha256,
            runtime_manifest_sha256=self.config.production_runtime_manifest_sha256,
            narration_route_id=registration.narration_route_id, picture_route_id=registration.picture_route_id,
            edit_route_id=registration.edit_route_id)

    def resume_current_blocker(self, run_id):
        from video_creator.application.current_production_blockers import PREFIX, bound_context, parse_journal, require_wait

        c.SourceBinding(system=run_id, namespace="current-production-resume")
        if not isinstance(self.config, (RegistrationConfigV2, RegistrationConfigLocalV1)):
            raise EngineError("production_blocker_registration_denied", "A v1 runtime cannot promote an original blocked binding", 403)
        with self.engine.db.connect_readonly() as connection:
            row = connection.execute("SELECT value FROM metadata WHERE key=?", (PREFIX + run_id,)).fetchone()
            if row is None:
                return "not_blocked", None
            raw = row[0]
            journal = parse_journal(raw, now=self.engine.clock())
            run, production, request, binding = bound_context(self.engine, connection, run_id, self.sha256)
            if journal.binding != binding:
                raise EngineError("production_blocker_binding_invalid", "Original full journal differs from the retained binding", 422)
            require_wait(run, journal)
        try:
            registered = self.engine._authorization_identity(production["owner"])
            if (registered.registration_sha256, registered.resource_manifest_sha256, registered.runtime_manifest_sha256) != self.installation_resource_identity:
                raise EngineError("production_installation_binding_invalid", "Original actual installation differs from the blocker", 503)
            issuer = self.engine.production_admissions
            with issuer.current_guard(registered) as guard:
                self._declaration_resume_current(production, request)
                self._preflight_blocker_resources(request)
                if (type(self.config) is RegistrationConfigLocalV1
                        and journal.result.blocker_code in {'production_asr_resource_required',
                            'asr_resource_changed', 'asr_code_changed', 'asr_model_changed'}):
                    # All-null is immutable absence, never a same-binding ASR
                    # installation. Selected missing bytes must actually exist
                    # and hash to this original configured resource set.
                    self._require_selected_asr()
                from video_creator.workflows.attempt_control import current_attempt

                current_attempt().check()
                return self._resume_current_writer(issuer, guard, run_id, raw)
        except EngineError as error:
            if error.status_code in {403, 503}:
                return "still_blocked", error.code
            raise
        except OSError:
            return "still_blocked", "production_resource_missing"

    def _resume_current_writer(self, issuer, guard, run_id, raw):
        from video_creator.application.current_production_blockers import PREFIX, bound_context, parse_journal, require_wait, unsettled

        with self.engine.db.transaction() as connection:
            current = connection.execute("SELECT value FROM metadata WHERE key=?", (PREFIX + run_id,)).fetchone()
            if current is None or current[0] != raw:
                raise EngineError("production_blocker_changed", "Original blocker changed during local preflight", 409)
            checked = parse_journal(current[0], now=self.engine.clock())
            run, production, request, binding = bound_context(self.engine, connection, run_id, self.sha256)
            if checked.binding != binding:
                raise EngineError("production_blocker_binding_invalid", "Original request/binding changed during local preflight", 422)
            require_wait(run, checked)
            issuer.assert_blocker_resume_current(connection, guard, run_id=run_id, binding=binding, blocker_sha256=digest(raw))
            self._declaration_resume_current(production, request)
            if unsettled(connection, run_id):
                connection.execute("UPDATE runs SET status='needs_reconciliation' WHERE id=?", (run_id,))
                connection.execute("UPDATE productions SET status='needs_reconciliation' WHERE id=?", (production["id"],))
                self.engine._event(connection, self.engine._run(connection, run_id), "production.capability_reconciliation_required", digest(raw))
                issuer._guard(connection, guard)
                return "needs_reconciliation", "production_blocker_reconciliation_required"
            cursor = connection.execute("DELETE FROM metadata WHERE key=? AND value=?", (PREFIX + run_id, raw))
            if cursor.rowcount != 1:
                raise EngineError("production_blocker_changed", "Original blocker deletion lost its compare-and-swap", 409)
            connection.execute("UPDATE runs SET status='queued',waiting_revision_id=NULL WHERE id=?", (run_id,))
            connection.execute("UPDATE productions SET status='queued' WHERE id=?", (production["id"],))
            self.engine._event(connection, self.engine._run(connection, run_id), "production.capability_resumed", digest(raw))
            issuer._guard(connection, guard)
            return "queued", None


def run_registered_worker(runtime: RegisteredMediaRuntime, *, control, on_ready: Callable[[str], None],
                          run_id=None, once=False, max_seconds=300):
    """Continuously dispatch the same durable queue; each attempt remains bounded."""
    import threading

    engine = runtime.engine
    worker = runtime.worker
    worker_id = worker.register_presence(runtime.sha256)
    failed = False
    reported_reconciliation = set()
    last_blocker_probe, blocker_cursor = float("-inf"), 0
    try:
        worker.heartbeat_presence(worker_id)
        on_ready(worker_id)
        while not control.stop_requested:
            worker.heartbeat_presence(worker_id)
            engine.recover()
            # Provider-specific reconciliation is not silently skipped or fed
            # into the incompatible legacy fixed-render binding parser.
            with engine.db.connect() as connection:
                unresolved = connection.execute("SELECT r.id FROM runs r JOIN execution_bindings b ON b.run_id=r.id WHERE r.status IN ('needs_reconciliation','waiting_provider','cancel_requested','failed','cancelled') AND EXISTS (SELECT 1 FROM operations o WHERE o.run_id=r.id AND (o.settled=0 OR o.status IN ('submitting','unknown','pending')))").fetchall()
                for row in unresolved:
                    binding = connection.execute("SELECT body FROM execution_bindings WHERE run_id=?", (row[0],)).fetchone()
                    if strict_json(binding[0].encode()).get("workflow_version") == PROFILE and row[0] not in reported_reconciliation:
                        reported_reconciliation.add(row[0])
                        sys_event("worker_reconciliation_pending", run_id=row[0], code="registered_provider_reconciliation_missing")
            if isinstance(runtime.config, (RegistrationConfigV2, RegistrationConfigLocalV1)) and not control.stop_requested and time.monotonic() - last_blocker_probe >= 5:
                from video_creator.application.current_production_blockers import PREFIX, parse_journal
                from video_creator.application.current_final_evidence_journal import PREFIX as FINAL_PREFIX, parse_journal as parse_final_journal
                from video_creator.application.production_probe_presence import hold_probe_presence
                from video_creator.workflows.attempt_control import attempt_control

                with engine.db.connect_readonly() as connection:
                    if run_id is not None:
                        candidate = connection.execute("SELECT rowid,key,value FROM metadata WHERE key IN (?,?) ORDER BY rowid LIMIT 1", (PREFIX + run_id, FINAL_PREFIX + run_id)).fetchone()
                    else:
                        candidate = connection.execute("SELECT m.rowid,m.key,m.value FROM metadata m JOIN runs r ON m.key IN (?||r.id,?||r.id) WHERE (r.status='waiting_user' OR (r.status='succeeded' AND m.key LIKE 'current_production_final_evidence:%')) AND r.waiting_revision_id IS NULL ORDER BY CASE WHEN m.rowid>? THEN 0 ELSE 1 END,m.rowid LIMIT 1",
                            (PREFIX, FINAL_PREFIX, blocker_cursor)).fetchone()
                last_blocker_probe = time.monotonic()
                if candidate is not None:
                    blocker_cursor = candidate[0]
                    final_probe = candidate[1].startswith(FINAL_PREFIX)
                    journal = (parse_final_journal if final_probe else parse_journal)(candidate[2], now=engine.clock())
                    if journal.binding.registration_sha256 == runtime.sha256:
                        try:
                            probe_deadline = time.monotonic() + max_seconds
                            with hold_probe_presence(worker, worker_id, control, probe_deadline) as probe_cancelled:
                                with attempt_control(probe_cancelled, probe_deadline).activate():
                                    resumed, reason = (runtime.resume_current_final_evidence if final_probe else runtime.resume_current_blocker)(journal.binding.run_id)
                            if reason:
                                sys_event("worker_capability_probe", run_id=journal.binding.run_id, state=resumed, code=reason)
                        except EngineError as error:
                            if control.stop_requested:
                                break
                            if error.code == 'worker_presence_lost':
                                raise
                            if error.status_code != 409:
                                raise
                            # Original CAS/paused/cancelled/owned state wins;
                            # this poll never steals it or acquires a new lease.
                            sys_event("worker_capability_probe", run_id=journal.binding.run_id, state="still_blocked", code=error.code)
            if control.stop_requested:
                break
            lease = engine.acquire_run(worker_id, lease_seconds=RUN_LEASE_SECONDS, run_id=run_id)
            if lease is None:
                if once:
                    break
                control.wait(0.25)
                continue
            finished, errors = threading.Event(), []
            deadline = time.monotonic() + max_seconds
            def renew(finished=finished, errors=errors, lease=lease, deadline=deadline):
                while not finished.wait(HEARTBEAT_SECONDS):
                    try:
                        worker.heartbeat_presence(worker_id)
                        if time.monotonic() >= deadline:
                            errors.append("worker_attempt_deadline")
                            return
                        with engine.db.connect() as connection:
                            current = engine._run(connection, lease.run_id)
                        if current["status"] in {"waiting_user", "succeeded", "cancelled", "failed", "needs_reconciliation"}:
                            continue
                        engine.heartbeat(lease, lease_seconds=RUN_LEASE_SECONDS)
                    except EngineError as error:
                        errors.append(error.code)
                        return
            heartbeat = threading.Thread(target=renew, name="production-worker-heartbeat")
            heartbeat.start()
            def attempt_cancelled(lease=lease, deadline=deadline, errors=errors):
                # EOF does not set control.stop_requested. This only stops the
                # current attempt and never authorizes review or clears costs.
                if control.stop_requested or errors or time.monotonic() >= deadline:
                    return True
                with engine.db.connect() as connection:
                    current = engine._run(connection, lease.run_id)
                return (current["cancellation_requested"] or current["worker_id"] != lease.worker_id
                    or current["fencing_token"] != lease.fencing_token or current["lease_until_us"] <= engine.clock())
            try:
                runtime.bind(lease, worker)
                result = runtime.invoke(lease, cancel=attempt_cancelled, deadline_monotonic=deadline)
                if isinstance(result, CurrentProductionUpstreamResult):
                    if result.state in {"waiting_authorization", "resource_not_ready"}:
                        runtime.park_current_upstream(lease, result)
                    elif result.state == "denied":
                        runtime.finish_current_upstream_denied(lease, result)
                    elif result.state != "waiting_user":
                        raise EngineError("worker_outcome_invalid", "Current upstream did not publish or stop through an actual original ledger path", 503)
                    # waiting_user was already persisted/released by the
                    # trusted human adapter; no second park/release here.
                elif result.state in {'waiting_evidence', 'repair_required', 'waiting_diagnosis'} and isinstance(runtime.config, (RegistrationConfigV2, RegistrationConfigLocalV1)):
                    assessment = getattr(result, 'final_evidence', None)
                    if (assessment is None or result.bundle_ref is not None
                            or assessment.snapshot is None or result.state != assessment.snapshot.state
                            or result.preparation_id != assessment.snapshot.preparation_id
                            or tuple(result.materials) != assessment.snapshot.ready_material_refs):
                        raise EngineError('worker_outcome_invalid', 'Actual same-service final evidence result required', 503)
                    # Selection, effective finite cap and final live checks
                    # belong to the original atomic park, never a pre-read.
                    runtime.park_current_final_evidence(lease, assessment)
                elif result.state == "waiting_user" and not isinstance(runtime.config, (RegistrationConfigV2, RegistrationConfigLocalV1)):
                    runtime.park(lease, result.blocker_code or "production_evidence_missing")
                elif result.state != "published" or result.bundle_ref is None:
                    raise EngineError("worker_outcome_invalid", "Only actual BundleService publication is production success", 503)
                else:
                    if getattr(result, 'final_evidence', None) is not None:
                        raise EngineError('worker_outcome_invalid', 'Published result cannot claim a waiting assessment', 503)
                    runtime.observe_current_final_publication(result)
                if errors or time.monotonic() >= deadline:
                    raise EngineError("worker_attempt_deadline", "Production attempt exceeded its bounded execution window", 503)
            except EngineError as error:
                with engine.db.connect() as connection:
                    current = engine._run(connection, lease.run_id)
                if current["status"] == "needs_reconciliation" or error.retryability == "reconcile":
                    if current["worker_id"] == worker_id:
                        engine.release_run(lease)
                    with engine.db.connect() as connection:
                        recovered = engine._run(connection, lease.run_id)
                    if recovered["status"] not in {"needs_reconciliation", "waiting_provider", "cancel_requested", "failed", "cancelled"}:
                        # An error label alone cannot manufacture uncertain
                        # dispatch or silently turn a known failure into retries.
                        raise
                elif isinstance(runtime.config, (RegistrationConfigV2, RegistrationConfigLocalV1)):
                    from video_creator.application.production_reauthorization import AUTHORIZATION_WAIT_CODES, WAIT_PREFIX, AuthorizationWait

                    if (current["status"] == "waiting_user" and current["worker_id"] is None
                            and current["lease_until_us"] == 0):
                        with engine.db.connect() as connection:
                            saved = connection.execute("SELECT value FROM metadata WHERE key=?", (WAIT_PREFIX + lease.run_id,)).fetchone()
                            production = engine._production(connection, current["production_id"])
                        if saved is None:
                            raise
                        wait = AuthorizationWait.model_validate_json(saved[0])
                        if (wait.instance_id, wait.production_id, wait.run_id, wait.request_revision_id, wait.request_sha256) != (
                                engine.instance_id, production["id"], lease.run_id, production["request_revision_id"], production["request_sha256"]):
                            raise EngineError("production_authorization_wait_invalid", "Original explicit Owner authorization wait differs", 422)
                        # The original operation guard already suspended and
                        # released; do not create or clear a second journal.
                    elif error.code in AUTHORIZATION_WAIT_CODES or error.code in RESOURCE_WAIT_CODES:
                        blocked = CurrentProductionUpstreamResult(run_id=lease.run_id, fencing_token=lease.fencing_token,
                            state="waiting_authorization" if error.code in AUTHORIZATION_WAIT_CODES else "resource_not_ready",
                            media_roles={}, blocker_code=error.code)
                        runtime.park_current_upstream(lease, blocked)
                    else:
                        if current["worker_id"] == worker_id:
                            engine.release_run(lease)
                        raise
                elif not isinstance(runtime.config, (RegistrationConfigV2, RegistrationConfigLocalV1)) and error.code in {"production_creative_capability_missing", "production_media_capability_missing",
                        "media_master_evidence_missing", "alignment_required", "rights_preflight_admission_required", "bundle_rights_unverified", "creative_versions_missing"}:
                    runtime.park(lease, error.code)
                else:
                    if current["worker_id"] == worker_id:
                        engine.release_run(lease)
                    raise
            finally:
                finished.set()
                heartbeat.join()
                final_ports = runtime._active_final_ports.pop(lease.run_id, None)
                if final_ports is not None:
                    final_ports.close()
                with runtime.bundle._lock:
                    for source_key, source in tuple(runtime.bundle._production_services_held.items()):
                        if source[2] == lease:
                            del runtime.bundle._production_services_held[source_key]
                with engine.db.transaction() as connection:
                    worker._presence(connection, worker_id)
                    connection.execute("UPDATE worker_presence SET state='idle',active_run_id=NULL WHERE worker_id=?", (worker_id,))
            if once:
                break
        control.assert_drain_completed()
    except BaseException:
        failed = True
        raise
    finally:
        with runtime.bundle._lock:
            runtime.bundle._production_services_held.clear()
            runtime.bundle._affected_execution_held.clear()
            runtime.bundle._affected_observation_held.clear()
        worker.close_presence(worker_id, failed=failed)


def sys_event(event, **values):
    import sys
    print(json.dumps({"event": event, "scope": "worker", **values}), file=sys.stderr, flush=True)
