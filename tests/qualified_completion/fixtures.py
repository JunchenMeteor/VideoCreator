"""Literal type/fault fixtures, never installation or production authority."""

import hashlib
from types import SimpleNamespace

from video_creator.domain import contracts as c
from video_creator.domain.affected_recipe import RecipeSourceRef
from video_creator.domain.bundle import MaterialReceipt
from video_creator.domain.component_diagnosis import (
    ComponentDiagnosticCheckV1,
    ComponentDiagnosticMethodRefV1,
    ComponentDiagnosticObservationV1,
    DiagnosticMetadataRef,
    DiagnosticSourceMediaRefV1,
)
from video_creator.domain.diagnostic_recovery import (
    DiagnosticFeedbackCompletion,
    DiagnosticMaterialCompletion,
    DiagnosticResourceCompletion,
)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def revision(kind="feedback"):
    return c.RevisionRef(revision_id="fixture." + kind, kind=kind, content_sha256="a" * 64)


def material(raw, media_type="text/plain"):
    return MaterialReceipt(preparation_id="fixture.preparation", artifact_id="fixture.artifact",
        material_id="fixture.material", sha256=sha(raw), size=len(raw), media_type=media_type,
        schema_kind="fixture.unverified")


def metadata(raw=b'{"fixture":"unqualified"}'):
    return DiagnosticMetadataRef(record_id="fixture.resource", content_sha256=sha(raw), size=len(raw))


def completions(raw=b'{"fixture":"unqualified"}'):
    # Merely well-formed serialized fixtures. Their names do not mint qualification.
    return (
        DiagnosticFeedbackCompletion(kind="feedback", ref=revision()),
        DiagnosticMaterialCompletion(kind="ready_material", ref=material(raw)),
        DiagnosticResourceCompletion(kind="qualified_resource", ref=metadata(raw)),
    )


def source_media():
    return DiagnosticSourceMediaRefV1(artifact_id="fixture.cover", asset_id="fixture.asset",
        role="cover", sha256="b" * 64, size=17, media_type="image/png", probe=None,
        source_operation_ids=("fixture.operation",), intrinsic_range=None, timeline_range=None,
        mapping_refs=(), shot_ids=())


def method():
    return ComponentDiagnosticMethodRefV1(method_id="fixture.method", version="fixture.v1",
        implementation_source_refs=(RecipeSourceRef(resource_name="Fixture/Decoder.py", sha256="c" * 64),),
        rule_template_sha256="d" * 64,
        route=c.CapabilityRoute(route_id="fixture.route", capability="media_diagnosis",
            source="owned_local", destination="local:fixture-not-a-runtime", credential_ref=None,
            max_operation_cost=c.Money(amount="0"), cost_rule_version="fixture.zero", verified=False),
        model_binding=None, check_kinds=("cover_frame",), resource_manifest_sha256="e" * 64,
        runtime_manifest_sha256="f" * 64)


def check(extra_refs=()):
    source = source_media()
    return ComponentDiagnosticCheckV1(check_id="fixture.check", check_kind="cover_frame", component="cover",
        source_refs=(source,) + tuple(extra_refs), shot_ids=(), intrinsic_range=None, timeline_range=None,
        expected_ref=source, observed_ref=source, observed_result="matches", assertion_status="supported",
        evidence_strength="deterministic_observation", limitations=("Unqualified type fixture only",),
        uncertainty_codes=())


def observation(checks):
    return ComponentDiagnosticObservationV1(format="current-component-diagnostic-observation-v1",
        input_key_sha256="1" * 64, method_ref=method(), analysis_operation_ids=("fixture.operation",),
        checks=tuple(checks), limitations=("Not a real authenticated observation",))


def predicate_inputs(completion_refs=()):
    # Only the field shape consumed by the original local predicate. This is
    # deliberately NOT RegisteredComponentDiagnosisInputsV2 or a held source.
    return SimpleNamespace(source_media_refs=(source_media(),),
        parent=SimpleNamespace(assembly=SimpleNamespace(creative_revision_refs=(), quality_ref=revision("quality")),
            materials=()), completion_source_refs=tuple(completion_refs), precision_report_ref=None,
        input_key_sha256="1" * 64)
