"""T18 candidate: real B11/W11 construction after separately approved preflight.

No product import occurs at module scope. This is not an admission record or an
authority. The old T16 guard/adapter remain byte-identical historical inputs.
"""
from pathlib import Path

from t16_guard import NotReadyForExecution


def create_bundle_service(target_module, admission):
    """Called ONLY by the reviewed ServiceAdapter after complete admission.

    The resource profile belongs to the externally pinned admission, not a
    production request. A final parent service environment is still required.
    Empty roots intentionally retain the real unconfigured registry blocker.
    """
    profile = admission.get("t18_trusted_resource_profile")
    if type(profile) is not dict:
        raise NotReadyForExecution("final independently bound T18 resource profile is missing")
    required = ("service_python", "asr_python", "ffmpeg", "ffprobe",
                "asr_manifest_path", "asr_manifest_sha256", "asr_index_sha256")
    if any(not profile.get(name) for name in required):
        raise NotReadyForExecution("complete service/ASR/media resources are required")
    import sys

    if Path(sys.executable).resolve() != Path(profile["service_python"]).resolve():
        raise NotReadyForExecution("service interpreter differs from approved closure")
    resources = admission["runtime_resources"]
    for name in ("service_python", "asr_python", "ffmpeg", "ffprobe", "asr_manifest_path"):
        if str(Path(profile[name]).resolve()) not in resources:
            raise NotReadyForExecution("resource profile contains an unbound path")
    instance = Path(admission["own_data_dir"]).resolve()
    # Actual imports follow the outer complete source/resource/body preflight.
    from video_creator.application.engine import EngineService
    from video_creator.application.executor import OperationExecutor
    from video_creator.cli.main import configured_media_validator
    from video_creator.domain.bundle import TrustedBundleValidators
    from video_creator.media.bundle_evidence import BundleMediaEvidence
    from video_creator.workflows.bundle_producer import create_registered_media_producer

    engine = EngineService(instance)
    validator = configured_media_validator(engine, Path(profile["ffmpeg"]), Path(profile["ffprobe"]))
    if validator is None:
        raise NotReadyForExecution("actual paired media decoder is unavailable")
    media = BundleMediaEvidence(Path(profile["asr_python"]), instance)
    validators = TrustedBundleValidators(
        media_validator=validator,
        precision_authorities={},
        frame_validator=media.frame_validator,
        resource_manifest_hashes=frozenset({profile["asr_manifest_sha256"]}),
        word_degradation_allowed=False,
    )
    bundle = target_module.BundleService(
        engine, validators=validators, rights_authority=None,
        audio_clock_authority=media.audio_clock_authority,
    )
    executor = OperationExecutor(engine, vault=None)
    runtime_root = instance / "BundleRuntime-T18"
    runtime_root.mkdir(exist_ok=True)
    producer = create_registered_media_producer(
        engine=engine, bundle=bundle, executor=executor,
        resource_manifest_path=Path(profile["asr_manifest_path"]),
        resource_manifest_sha256=profile["asr_manifest_sha256"],
        runtime_manifest_sha256=profile["asr_index_sha256"],
        storage_root=instance, runtime_root=runtime_root,
    )
    # Test-only handles to the real objects, no replacement DTO or business SQL.
    bundle._t18_runtime_handles = {"executor": executor, "media": media, "producer": producer}
    return bundle
