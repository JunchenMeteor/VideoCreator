"""The hardcoded registered production factory; no model-selected adapters."""
from __future__ import annotations

from video_creator.domain import contracts as c
from video_creator.domain.errors import EngineError
from video_creator.domain.registered_production import ProductionDriverBuilders
from video_creator.media.ffmpeg import FFmpegRuntime
from video_creator.media.production_edit import FfmpegEditDriver
from video_creator.providers.local_piper import PiperNarrationDriver
from video_creator.providers.production_common import output_scope
from video_creator.providers.production_resources import ProductionResources
from video_creator.providers.wan_video import WanVideoDriver
from video_creator.workflows.autonomous_production import BoundProductionDriver


def create_registered_production_drivers(*, engine, worker, bundle, storage_root, runtime_root, decoder,
        resource_manifest_path, resource_manifest_sha256, runtime_manifest_sha256,
        narration_route_id, picture_route_id, edit_route_id) -> ProductionDriverBuilders:
    if not callable(decoder):
        raise EngineError("production_decoder_missing", "A trusted full-decode MIME validator is required.", 503)
    resources = ProductionResources(resource_manifest_path, resource_manifest_sha256, runtime_manifest_sha256)

    def narration(request_data, ordered_output_reservations, *, ordinary_lease, cancel, deadline_monotonic):
        outputs = output_scope(ordered_output_reservations, ordinary_lease, storage_root)
        if len(outputs) != 1 or not isinstance(request_data, dict):
            raise EngineError("production_narration_input_invalid", "Approved actual script and one narration output are required.", 422)
        text = request_data.get("text")
        if type(text) is not str or not 0 < len(text) <= 4000:
            raise EngineError("production_narration_input_invalid", "Approved narration text exceeds the actual TTS bound.", 422)
        resources.section("narration", "piper")
        driver = PiperNarrationDriver(engine=engine, worker=worker, decoder=decoder, resources=resources,
            route_id=narration_route_id, lease=ordinary_lease, output=outputs[0], storage_root=storage_root,
            text=text, cancel=cancel, deadline_monotonic=deadline_monotonic)
        return BoundProductionDriver(driver)

    def picture(request_data, ordered_output_reservations, *, ordinary_lease, cancel, deadline_monotonic):
        outputs = output_scope(ordered_output_reservations, ordinary_lease, storage_root)
        if len(outputs) != 1:
            raise EngineError("production_picture_input_invalid", "One original shot output is required.", 422)
        shot = c.StoryboardShot.model_validate(request_data)
        request = engine.get_request(ordinary_lease)
        ratio = request.brief.aspect_ratio if request.brief is not None else "9:16"
        driver = WanVideoDriver(engine=engine, worker=worker, decoder=decoder, resources=resources,
            route_id=picture_route_id, lease=ordinary_lease, output=outputs[0], shot=shot, ratio=ratio,
            cancel=cancel, deadline_monotonic=deadline_monotonic)
        return BoundProductionDriver(driver, driver.payload)

    def edit(request_data, ordered_output_reservations, *, ordinary_lease, cancel, deadline_monotonic):
        outputs = output_scope(ordered_output_reservations, ordinary_lease, storage_root)
        if not isinstance(request_data, dict):
            raise EngineError("production_edit_input_invalid", "Actual clip/narration references and three ordered masters are required.", 422)
        changed = request_data.get("changed_media_roles")
        if changed is None:
            if len(outputs) != 3:
                raise EngineError("production_edit_input_invalid", "The original full edit requires its three ordered masters.", 422)
        elif (type(changed) is not list or not changed or changed != [role for role in ("video", "mixed_audio", "cover") if role in changed]
                or len(outputs) != len(changed) or "mixed_audio" in changed and "video" not in changed):
            raise EngineError("production_edit_input_invalid", "Only the exact ordered affected edit output subset is supported.", 422)
        config = resources.section("edit", "ffmpeg")
        recipe_id = request_data.get("recipe_id")
        if recipe_id is not None:
            from pathlib import Path

            from video_creator.providers.production_resources import file_sha256
            actual = resources.recipe_resources
            recipe = None if actual is None else next((item for item in actual.recipes if item.recipe_id == recipe_id), None)
            expected_roles = tuple(request_data.get("changed_master_roles", ("video", "narration_audio", "mixed_audio", "cover")))
            if recipe is None or expected_roles not in recipe.allowed_output_variants:
                raise EngineError("production_recipe_not_installed", "Only the actual indexed recipe's exact output variant may be rendered.", 503)
            code = (Path(__file__), Path(__file__).parents[1] / "media" / "production_edit.py")
            if not {file_sha256(path) for path in code} <= {ref.sha256 for ref in recipe.producer_source_refs}:
                raise EngineError("production_recipe_source_changed", "The actual running edit producer must match its original indexed recipe sources.", 503)
            if (recipe_id == "visual-preserve-mix-v1" and "mixed_audio" in expected_roles
                    or recipe_id in {"audio-remix-preserved-clips-v1", "cover-from-preserved-video-v1"} and request_data.get("regenerated_shot_ids")):
                raise EngineError("production_recipe_input_invalid", "Preserved recipe inputs cannot be regenerated or remixed through another output shape.", 403)
        runtime = FFmpegRuntime(resources.resource(config["ffmpeg"]), resources.resource(config["ffprobe"]), storage_root)
        driver = FfmpegEditDriver(engine=engine, worker=worker, bundle=bundle, decoder=decoder, runtime=runtime,
            route_id=edit_route_id, lease=ordinary_lease, outputs=outputs, request_data=request_data,
            cancel=cancel, deadline_monotonic=deadline_monotonic)
        return BoundProductionDriver(driver)

    # No provider uses runtime_root to choose arbitrary modules or inputs.
    return ProductionDriverBuilders(narration=narration, picture=picture, edit=edit)
