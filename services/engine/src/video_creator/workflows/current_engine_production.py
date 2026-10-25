"""Hardcoded composition using distinct real human and policy Engine ports.

The trusted Backend host installs this factory. No caller/model chooses a
module, driver or admission callback here. Policy execution has its own direct
typed consumer; it is never a ReviewDecision.
"""
from __future__ import annotations

from types import MethodType

from video_creator.application.bundles import BundleService
from video_creator.application.engine import EngineService
from video_creator.application.executor import OperationExecutor
from video_creator.application.production_admissions import PolicyExecutionPorts
from video_creator.application.production_ports import ProductionPorts
from video_creator.application.worker import WorkerService
from video_creator.domain.affected_repair import ForcedAlignmentRegistration
from video_creator.domain.errors import EngineError
from video_creator.domain.registered_production import PROFILE, AutonomousRegistration
from video_creator.providers.component_diagnosis import (
    create_component_diagnostic_ports,
)
from video_creator.providers.local_alignment import create_alignment_builder
from video_creator.workflows.autonomous_production import (
    AutonomousServices,
    CurrentPolicyServices,
)
from video_creator.workflows.production_drivers import (
    create_registered_production_drivers,
)


def _plan_target_port(bundle, original, diagnostic_ports):
    """Select existing catalog preparation only from verified diagnostic resources."""
    if diagnostic_ports is None:
        return original
    if diagnostic_ports.resources.recipe_resources.format != "registered-production-driver-resources-v3-diagnostic-v1":
        raise EngineError("production_plan_catalog_source_invalid", "The complete installed diagnostic catalog is required for this branch.", 503)
    actual = bundle.prepare_plan_repair_targets_v2
    if (type(actual) is not MethodType or actual.__self__ is not original.__self__
            or actual.__self__ is not bundle or actual.__func__ is not BundleService.prepare_plan_repair_targets_v2):
        raise EngineError("production_plan_catalog_port_missing", "Retain the actual same BundleService's existing catalog preparation method, never a callback or inferred binding.", 503)
    return actual


def create_current_engine_services(
    *, engine: EngineService, worker: WorkerService, bundle: BundleService,
    executor: OperationExecutor, production_ports: ProductionPorts,
    registration: AutonomousRegistration, subject: str, storage_root, runtime_root,
    decoder, resource_manifest_path, resource_manifest_sha256,
    runtime_manifest_sha256, alignment_registration=None,
    prepare_plan_repair_targets=None,
) -> AutonomousServices:
    """Compose installed code; does not create a Run, lease, approval or authority.

    Driver resources are checked by the existing fixed factory. Backend still
    owns registered binding, current Owner, ordinary lease, queue dispatch,
    per-operation permissions and final Bundle authorization.
    """
    if alignment_registration is not None and type(alignment_registration) is not ForcedAlignmentRegistration:
        raise EngineError("alignment_registration_invalid", "Only the sole installed typed alignment declaration is supported; it is not actual qualification.", 503)
    if (type(prepare_plan_repair_targets) is not MethodType
            or prepare_plan_repair_targets.__self__ is not bundle
            or prepare_plan_repair_targets.__func__ is not BundleService.prepare_plan_repair_targets):
        raise EngineError("production_plan_targets_port_missing", "Retain the original registered BundleService bound method; a callback cannot define or authorize finite plan targets.", 503)
    if type(production_ports) is not ProductionPorts:
        raise EngineError(
            "production_current_admission_port_required",
            "This consumer requires the actual current ordinary human-review ports; policy cannot impersonate a review.",
            503,
        )
    if (not isinstance(registration, AutonomousRegistration)
            or production_ports.engine is not engine or production_ports.worker is not worker
            or worker.engine is not engine or worker.workflow_version != PROFILE
            or bundle.engine is not engine or executor.engine is not engine
            or production_ports.declaration != registration.rights_declaration):
        raise EngineError(
            "production_current_service_binding_conflict",
            "Current registered declaration and service objects must belong to one owned Engine instance.",
            409,
        )
    if (type(subject) is not str or subject != registration.rights_declaration.declaring_subject
            or not callable(decoder)):
        raise EngineError(
            "production_current_constructor_invalid",
            "The trusted host must supply its actual subject and full-decode media validator.",
            503,
        )
    drivers = create_registered_production_drivers(
        engine=engine, worker=worker, bundle=bundle,
        storage_root=storage_root, runtime_root=runtime_root, decoder=decoder,
        resource_manifest_path=resource_manifest_path,
        resource_manifest_sha256=resource_manifest_sha256,
        runtime_manifest_sha256=runtime_manifest_sha256,
        narration_route_id=registration.narration_route_id,
        picture_route_id=registration.picture_route_id,
        edit_route_id=registration.edit_route_id,
    )
    diagnostic_ports = create_component_diagnostic_ports(resource_manifest_path=resource_manifest_path,
        resource_manifest_sha256=resource_manifest_sha256, runtime_manifest_sha256=runtime_manifest_sha256,
        storage_root=storage_root)
    services = AutonomousServices(
        engine=engine, worker=worker, bundle=bundle, executor=executor,
        media_validator=decoder, subject=subject,
        text_route_id=registration.text_route_id,
        narration_route_id=registration.narration_route_id,
        picture_route_id=registration.picture_route_id,
        edit_route_id=registration.edit_route_id,
        master_index_route_id=registration.master_index_route_id,
        narration_driver=drivers.narration, picture_driver=drivers.picture,
        edit_driver=drivers.edit,
        declare_rights=production_ports.production_rights,
        admit_revision=production_ports.admit_revision,
        max_duration_us=registration.max_duration_us,
        rights_proposal=production_ports.rights_proposal,
        current_admission=production_ports.current_production_admission,
        current_rights=production_ports.current_production_rights,
        registration_sha256=production_ports.registration_sha256,
        execution_ports=production_ports, alignment_registration=alignment_registration,
        alignment_driver=None if alignment_registration is None else create_alignment_builder(
            engine=engine, worker=worker, bundle=bundle, storage_root=storage_root,
            resource_manifest_path=resource_manifest_path, resource_manifest_sha256=resource_manifest_sha256,
            runtime_manifest_sha256=runtime_manifest_sha256, registration=alignment_registration),
        prepare_plan_repair_targets=_plan_target_port(bundle, prepare_plan_repair_targets, diagnostic_ports),
        component_diagnostic_ports=diagnostic_ports,
    )
    if diagnostic_ports is not None:
        diagnostic_ports.bind_services(services)
    return services


def create_current_policy_engine_services(
    *, engine: EngineService, worker: WorkerService, bundle: BundleService,
    executor: OperationExecutor, policy_execution_ports: PolicyExecutionPorts,
    registration: AutonomousRegistration, subject: str, storage_root, runtime_root,
    decoder, resource_manifest_path, resource_manifest_sha256,
    runtime_manifest_sha256, alignment_registration=None,
    prepare_plan_repair_targets=None,
) -> CurrentPolicyServices:
    """Compose the original installed policy issuer, never its identity or grants.

    The compatible registration declaration does not authorize policy projects.
    Actual begin/plan/quality rights and current checks stay in Backend ports.
    """
    if alignment_registration is not None and type(alignment_registration) is not ForcedAlignmentRegistration:
        raise EngineError("alignment_registration_invalid", "Only the sole installed typed alignment declaration is supported; it is not actual qualification.", 503)
    if (type(prepare_plan_repair_targets) is not MethodType
            or prepare_plan_repair_targets.__self__ is not bundle
            or prepare_plan_repair_targets.__func__ is not BundleService.prepare_plan_repair_targets):
        raise EngineError("production_plan_targets_port_missing", "Retain the original registered BundleService bound method; a callback cannot define or authorize finite plan targets.", 503)
    if type(policy_execution_ports) is not PolicyExecutionPorts:
        raise EngineError("production_current_policy_port_required", "Install the actual policy ports; a human callback cannot grant unattended execution.", 503)
    if (not isinstance(registration, AutonomousRegistration)
            or policy_execution_ports.issuer.engine is not engine
            or worker.engine is not engine or worker.workflow_version != PROFILE
            or bundle.engine is not engine or executor.engine is not engine):
        raise EngineError("production_current_service_binding_conflict", "Actual issuer and registered services must belong to one Engine and original Worker profile.", 409)
    if type(subject) is not str or not subject or not callable(decoder):
        raise EngineError("production_current_constructor_invalid", "The trusted host must supply its actual subject and full-decode media validator.", 503)
    drivers = create_registered_production_drivers(
        engine=engine, worker=worker, bundle=bundle,
        storage_root=storage_root, runtime_root=runtime_root, decoder=decoder,
        resource_manifest_path=resource_manifest_path,
        resource_manifest_sha256=resource_manifest_sha256,
        runtime_manifest_sha256=runtime_manifest_sha256,
        narration_route_id=registration.narration_route_id,
        picture_route_id=registration.picture_route_id,
        edit_route_id=registration.edit_route_id,
    )
    diagnostic_ports = create_component_diagnostic_ports(resource_manifest_path=resource_manifest_path,
        resource_manifest_sha256=resource_manifest_sha256, runtime_manifest_sha256=runtime_manifest_sha256,
        storage_root=storage_root)
    services = CurrentPolicyServices(
        engine=engine, worker=worker, bundle=bundle, executor=executor,
        media_validator=decoder, subject=subject, text_route_id=registration.text_route_id,
        narration_route_id=registration.narration_route_id,
        picture_route_id=registration.picture_route_id, edit_route_id=registration.edit_route_id,
        master_index_route_id=registration.master_index_route_id,
        narration_driver=drivers.narration, picture_driver=drivers.picture,
        edit_driver=drivers.edit, policy_execution_ports=policy_execution_ports,
        registration_sha256=policy_execution_ports.registered.registration_sha256,
        max_duration_us=registration.max_duration_us,
        alignment_registration=alignment_registration,
        alignment_driver=None if alignment_registration is None else create_alignment_builder(
            engine=engine, worker=worker, bundle=bundle, storage_root=storage_root,
            resource_manifest_path=resource_manifest_path, resource_manifest_sha256=resource_manifest_sha256,
            runtime_manifest_sha256=runtime_manifest_sha256, registration=alignment_registration),
        prepare_plan_repair_targets=_plan_target_port(bundle, prepare_plan_repair_targets, diagnostic_ports),
        component_diagnostic_ports=diagnostic_ports,
    )
    if diagnostic_ports is not None:
        diagnostic_ports.bind_services(services)
    return services
