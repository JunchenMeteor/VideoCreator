"""Actual clip/narration edit, mix and cover with a fixed FFmpeg graph."""
from __future__ import annotations

from decimal import Decimal

from video_creator.domain.errors import EngineError
from video_creator.providers.production_common import (
    install_output,
    local_observation,
    permit_scope,
)
from video_creator.workflows.attempt_control import attempt_control

DESTINATION = "local:ffmpeg-production-edit-v1"
FRAME_US = 40000  # This implementation's fixed 25fps edit profile, not guessed timecodes.


def _seconds(microseconds):
    return format(Decimal(microseconds) / 1000000, "f")


class FfmpegEditDriver:
    def __init__(self, *, engine, worker, bundle, decoder, runtime, route_id, lease,
                 outputs, request_data, cancel, deadline_monotonic):
        self.engine, self.worker, self.bundle = engine, worker, bundle
        self.decoder, self.runtime, self.route_id = decoder, runtime, route_id
        self.lease, self.outputs, self.data = lease, outputs, request_data
        self.control = attempt_control(cancel, deadline_monotonic)

    def __call__(self, permit, secret):
        with self.control.activate():
            permit_scope(self.engine, permit, self.lease, self.route_id, "render", DESTINATION, local=True, secret=secret)
            if self.data.get("changed_media_roles") is not None:
                return self._affected()
            clips = self.data.get("clips")
            shots = self.data.get("storyboard", {}).get("shots")
            if not isinstance(clips, list) or not isinstance(shots, list) or len(clips) != 3 or len(shots) != 3:
                raise EngineError("production_edit_input_invalid", "Actual three clips and approved three-shot storyboard are required.", 422)
            durations = [shot["duration_us"] for shot in shots]
            if any(type(value) is not int or not 0 < value <= 15_000_000 or value % FRAME_US for value in durations):
                raise EngineError("production_edit_timeline_invalid", "Each approved shot must fit the 25fps bounded production timeline.", 422)
            duration = sum(durations)
            assets = [self.bundle.asset(self.lease, asset_id) for asset_id in clips]
            narration = self.bundle.asset(self.lease, self.data["narration_audio"])
            paths = [self.bundle.content_path(self.lease, value.asset_id) for value in assets]
            speech_path = self.bundle.content_path(self.lease, narration.asset_id)
            if (len({value.asset_id for value in assets} | {narration.asset_id}) != 4
                    or narration.media_type != "audio/wav"):
                raise EngineError("production_edit_input_invalid", "Original clips and independent narration must be distinct actual registered media.", 422)
            probes = [self.decoder(path, "video/mp4") for path in paths]
            speech = self.decoder(speech_path, "audio/wav")
            if (not speech.decoded or not speech.has_audio or speech.has_video
                    or speech.duration_us is None or speech.duration_us > duration):
                raise EngineError("production_narration_exceeds_plan", "Actual narration is missing or exceeds the approved work; do not truncate spoken words.", 422)
            if any(not probe.decoded or not probe.has_video or probe.duration_us is None
                   or probe.duration_us < planned for probe, planned in zip(probes, durations, strict=True)):
                raise EngineError("production_edit_source_invalid", "Actual generated clip is shorter than its approved shot.", 422)
            request = self.engine.get_request(self.lease)
            ratio = request.brief.aspect_ratio if request.brief is not None else "9:16"
            width, height = (720, 1280) if ratio == "9:16" else (1280, 720)
            argv, graph = ["-nostdin", "-v", "error", "-y"], []
            for path in (*paths, speech_path):
                self.runtime._input_format(path)  # Existing container/reference checks before parsing.
                argv.extend([*self.runtime._input_args(self.runtime._input_format(path)), "-i", str(path)])
            for index, (probe, planned) in enumerate(zip(probes, durations, strict=True)):
                seconds = _seconds(planned)
                graph.append(f"[{index}:v:0]trim=duration={seconds},setpts=PTS-STARTPTS,fps=25,"
                             f"scale={width}:{height}:force_original_aspect_ratio=decrease,"
                             f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2,setsar=1,format=yuv420p[v{index}]")
                if probe.has_audio:
                    graph.append(f"[{index}:a:0]atrim=duration={seconds},asetpts=PTS-STARTPTS,"
                                 f"aresample=48000,aformat=channel_layouts=mono,apad,atrim=duration={seconds}[a{index}]")
                else:
                    # Silence fills only an actually silent generated clip's
                    # soundtrack; it is never a substitute for the real narration.
                    graph.append(f"anullsrc=r=48000:cl=mono,atrim=duration={seconds},asetpts=PTS-STARTPTS[a{index}]")
            graph.append("[v0][v1][v2]concat=n=3:v=1:a=0[v]")
            graph.append("[a0][a1][a2]concat=n=3:v=0:a=1,volume=0.18[bed]")
            samples = duration * 48000 // 1_000_000
            graph.append(f"[3:a:0]aresample=48000,aformat=channel_layouts=mono,asetpts=PTS-STARTPTS,"
                         f"apad,atrim=end_sample={samples}[speech]")
            graph.append(f"[speech][bed]amix=inputs=2:duration=longest:normalize=0,alimiter=limit=0.95:latency=1,"
                         f"atrim=end_sample={samples},asplit=2[encoded_audio][mix]")
            video, mixed, cover = self.outputs
            argv.extend(["-filter_complex", ";".join(graph), "-map", "[v]", "-map", "[encoded_audio]",
                         "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-ar", "48000",
                         "-movflags", "+faststart", "-t", _seconds(duration), "-f", "mp4", str(video.partial_path),
                         "-map", "[mix]", "-c:a", "pcm_s16le", "-ar", "48000", "-ac", "1", "-f", "wav", str(mixed.partial_path)])
            self.runtime._run(self.runtime.ffmpeg, argv, timeout=self.control.remaining(120))
            self.runtime._run(self.runtime.ffmpeg, ["-nostdin", "-v", "error", "-y",
                *self.runtime._input_args("mov"), "-i", str(video.partial_path), "-map", "0:v:0",
                "-frames:v", "1", "-q:v", "3", "-update", "1", "-f", "image2", str(cover.partial_path)],
                timeout=self.control.remaining(30))
            files, observed = [], []
            for output, media_type in zip(self.outputs, ("video/mp4", "audio/wav", "image/jpeg"), strict=True):
                file, probe = install_output(self.engine, self.worker, self.lease, output, self.decoder, media_type)
                files.append(file)
                observed.append(probe.model_dump(mode="json"))
            if observed[0]["duration_us"] != duration or observed[1]["duration_us"] != duration:
                raise EngineError("production_edit_duration_mismatch", "Actual video/mix duration differs from the approved discrete timeline.", 422)
            if (observed[0]["width"], observed[0]["height"]) != (width, height) or observed[2]["has_audio"]:
                raise EngineError("production_edit_output_invalid", "Actual masters do not match the requested frame and static cover.", 422)
            return local_observation(tuple(files), {"actual_probes": observed, "source_clip_asset_ids": clips,
                "source_narration_asset_id": narration.asset_id, "timeline_duration_us": duration,
                "scope": "real generated clips and neural narration edited/mixed; cover decoded from final video"})

    def _affected(self):
        """Render precisely the admitted subset, keeping an unchanged mix intact.

        This request describes outputs; the original Operation permit and held
        affected command are the authority. No missing role becomes a new master.
        """
        roles = self.data.get("changed_media_roles")
        if (type(roles) is not list or not roles or len(roles) != len(self.outputs)
                or roles != [role for role in ("video", "mixed_audio", "cover") if role in roles]
                or "mixed_audio" in roles and "video" not in roles):
            raise EngineError("production_edit_input_invalid", "Affected outputs retain their exact original order and dependency subset.", 422)
        outputs = dict(zip(roles, self.outputs, strict=True))
        recipe = self.data.get("recipe_id")
        if (recipe == "cover-from-preserved-video-v1" and roles != ["cover"]
                or recipe == "visual-preserve-mix-v1" and "mixed_audio" in roles
                or recipe in {"audio-remix-preserved-clips-v1", "cover-from-preserved-video-v1"} and self.data.get("regenerated_shot_ids")):
            raise EngineError("production_recipe_input_invalid", "Actual recipe output and preserved input boundaries must remain exact.", 403)
        if roles == ["cover"]:
            asset = self.bundle.asset(self.lease, self.data["preserved_video"])
            path = self.bundle.content_path(self.lease, asset.asset_id)
            probe = self.decoder(path, "video/mp4")
            if asset.media_type != "video/mp4" or not probe.decoded or not probe.has_video or probe != asset.probe:
                raise EngineError("production_edit_source_invalid", "The preserved original video must still decode to its registered evidence.", 422)
            self._cover(path, outputs["cover"])
            file, observed = install_output(self.engine, self.worker, self.lease, outputs["cover"], self.decoder, "image/jpeg")
            return local_observation((file,), {"actual_probes": [observed.model_dump(mode="json")],
                        "source_preserved_video_asset_id": asset.asset_id, "changed_media_roles": roles})
        if "video" not in roles:
            raise EngineError("production_edit_input_invalid", "This fixed adapter does not synthesize an independent unsupported edit role.", 422)
        clips = self.data.get("clips")
        shots = self.data.get("storyboard", {}).get("shots")
        if type(clips) is not list or type(shots) is not list or len(clips) != 3 or len(shots) != 3:
            raise EngineError("production_edit_input_invalid", "Actual registered three-shot sources are required.", 422)
        durations = [shot["duration_us"] for shot in shots]
        if any(type(value) is not int or not 0 < value <= 15_000_000 or value % FRAME_US for value in durations):
            raise EngineError("production_edit_timeline_invalid", "Affected shots retain the actual bounded 25fps timeline.", 422)
        duration = sum(durations)
        assets = [self.bundle.asset(self.lease, identity) for identity in clips]
        paths = [self.bundle.content_path(self.lease, asset.asset_id) for asset in assets]
        probes = [self.decoder(path, "video/mp4") for path in paths]
        if len(set(clips)) != 3 or any(asset.media_type != "video/mp4" or not probe.decoded or not probe.has_video
                or probe != asset.probe or probe.duration_us is None or probe.duration_us < planned
                for asset, probe, planned in zip(assets, probes, durations, strict=True)):
            raise EngineError("production_edit_source_invalid", "Each real source clip retains its original evidence and planned duration.", 422)
        remix = "mixed_audio" in roles
        audio_id = self.data["narration_audio"] if remix else self.data["preserved_mixed_audio"]
        audio = self.bundle.asset(self.lease, audio_id)
        audio_path = self.bundle.content_path(self.lease, audio.asset_id)
        audio_probe = self.decoder(audio_path, "audio/wav")
        if (audio.media_type != "audio/wav" or not audio_probe.decoded or not audio_probe.has_audio
                or audio_probe.has_video or audio_probe != audio.probe or audio_probe.duration_us is None
                or (audio_probe.duration_us > duration if remix else audio_probe.duration_us != duration)):
            raise EngineError("production_edit_audio_invalid", "The real narration or preserved mix must satisfy its exact timeline and source evidence.", 422)
        request = self.engine.get_request(self.lease)
        ratio = request.brief.aspect_ratio if request.brief is not None else "9:16"
        width, height = (720, 1280) if ratio == "9:16" else (1280, 720)
        if recipe == "audio-remix-preserved-clips-v1":
            return self._audio_remix(paths, probes, durations, duration, audio, audio_path, outputs, clips, width, height)
        argv, graph = ["-nostdin", "-v", "error", "-y"], []
        for path in (*paths, audio_path):
            argv.extend([*self.runtime._input_args(self.runtime._input_format(path)), "-i", str(path)])
        for index, (probe, planned) in enumerate(zip(probes, durations, strict=True)):
            seconds = _seconds(planned)
            graph.append(f"[{index}:v:0]trim=duration={seconds},setpts=PTS-STARTPTS,fps=25,"
                         f"scale={width}:{height}:force_original_aspect_ratio=decrease,"
                         f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2,setsar=1,format=yuv420p[v{index}]")
            if remix:
                if probe.has_audio:
                    graph.append(f"[{index}:a:0]atrim=duration={seconds},asetpts=PTS-STARTPTS,"
                                 f"aresample=48000,aformat=channel_layouts=mono,apad,atrim=duration={seconds}[a{index}]")
                else:
                    graph.append(f"anullsrc=r=48000:cl=mono,atrim=duration={seconds},asetpts=PTS-STARTPTS[a{index}]")
        graph.append("[v0][v1][v2]concat=n=3:v=1:a=0[v]")
        samples = duration * 48000 // 1_000_000
        if remix:
            graph.append("[a0][a1][a2]concat=n=3:v=0:a=1,volume=0.18[bed]")
            graph.append(f"[3:a:0]aresample=48000,aformat=channel_layouts=mono,asetpts=PTS-STARTPTS,"
                         f"apad,atrim=end_sample={samples}[speech]")
            graph.append(f"[speech][bed]amix=inputs=2:duration=longest:normalize=0,alimiter=limit=0.95:latency=1,"
                         f"atrim=end_sample={samples},asplit=2[encoded_audio][mix]")
        else:
            graph.append("[3:a:0]asetpts=PTS-STARTPTS[encoded_audio]")
        argv.extend(["-filter_complex", ";".join(graph), "-map", "[v]", "-map", "[encoded_audio]",
                     "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-ar", "48000",
                     "-movflags", "+faststart", "-t", _seconds(duration), "-f", "mp4", str(outputs["video"].partial_path)])
        if remix:
            argv.extend(["-map", "[mix]", "-c:a", "pcm_s16le", "-ar", "48000", "-ac", "1", "-f", "wav", str(outputs["mixed_audio"].partial_path)])
        self.runtime._run(self.runtime.ffmpeg, argv, timeout=self.control.remaining(120))
        if "cover" in outputs:
            self._cover(outputs["video"].partial_path, outputs["cover"])
        files, observed = [], {}
        for role, output in outputs.items():
            media_type = {"video": "video/mp4", "mixed_audio": "audio/wav", "cover": "image/jpeg"}[role]
            file, probe = install_output(self.engine, self.worker, self.lease, output, self.decoder, media_type)
            files.append(file)
            observed[role] = probe
        if (observed["video"].duration_us != duration or (observed["video"].width, observed["video"].height) != (width, height)
                or remix and observed["mixed_audio"].duration_us != duration
                or "cover" in observed and observed["cover"].has_audio):
            raise EngineError("production_edit_output_invalid", "Every changed output must retain the exact approved timeline and media role.", 422)
        return local_observation(tuple(files), {"actual_probes": [value.model_dump(mode="json") for value in observed.values()],
                    "source_clip_asset_ids": clips, "source_audio_asset_id": audio.asset_id,
                    "changed_media_roles": roles, "timeline_duration_us": duration,
                    "preserved_mixed_audio_asset_id": None if remix else audio.asset_id})

    def _cover(self, source, output):
        self.runtime._run(self.runtime.ffmpeg, ["-nostdin", "-v", "error", "-y",
            *self.runtime._input_args(self.runtime._input_format(source)), "-i", str(source), "-map", "0:v:0",
            "-frames:v", "1", "-q:v", "3", "-update", "1", "-f", "image2", str(output.partial_path)],
            timeout=self.control.remaining(30))

    def _audio_remix(self, paths, probes, durations, duration, audio, speech_path, outputs, clips, width, height):
        """Keep the original video stream; change only its admitted soundtrack."""
        video = self.bundle.asset(self.lease, self.data["preserved_video"])
        path = self.bundle.content_path(self.lease, video.asset_id)
        probe = self.decoder(path, "video/mp4")
        if (tuple(outputs) != ("video", "mixed_audio") or video.media_type != "video/mp4" or not probe.decoded
                or probe != video.probe or not probe.has_video or probe.duration_us != duration
                or (probe.width, probe.height) != (width, height)):
            raise EngineError("production_recipe_source_invalid", "Audio repair must preserve the actual full parent video stream and exact two output roles.", 422)
        argv, graph = ["-nostdin", "-v", "error", "-y"], []
        for source in (*paths, speech_path, path):
            argv.extend([*self.runtime._input_args(self.runtime._input_format(source)), "-i", str(source)])
        for index, (source_probe, planned) in enumerate(zip(probes, durations, strict=True)):
            seconds = _seconds(planned)
            if source_probe.has_audio:
                graph.append(f"[{index}:a:0]atrim=duration={seconds},asetpts=PTS-STARTPTS,aresample=48000,"
                             f"aformat=channel_layouts=mono,apad,atrim=duration={seconds}[a{index}]")
            else:
                graph.append(f"anullsrc=r=48000:cl=mono,atrim=duration={seconds},asetpts=PTS-STARTPTS[a{index}]")
        samples = duration * 48000 // 1_000_000
        graph.append("[a0][a1][a2]concat=n=3:v=0:a=1,volume=0.18[bed]")
        graph.append(f"[3:a:0]aresample=48000,aformat=channel_layouts=mono,asetpts=PTS-STARTPTS,apad,atrim=end_sample={samples}[speech]")
        graph.append(f"[speech][bed]amix=inputs=2:duration=longest:normalize=0,alimiter=limit=0.95:latency=1,atrim=end_sample={samples},asplit=2[encoded_audio][mix]")
        argv.extend(["-filter_complex", ";".join(graph), "-map", "4:v:0", "-map", "[encoded_audio]",
                     "-c:v", "copy", "-c:a", "aac", "-ar", "48000", "-movflags", "+faststart",
                     "-t", _seconds(duration), "-f", "mp4", str(outputs["video"].partial_path),
                     "-map", "[mix]", "-c:a", "pcm_s16le", "-ar", "48000", "-ac", "1", "-f", "wav", str(outputs["mixed_audio"].partial_path)])
        self.runtime._run(self.runtime.ffmpeg, argv, timeout=self.control.remaining(120))
        files, actual = [], {}
        for role, output in outputs.items():
            file, observed = install_output(self.engine, self.worker, self.lease, output, self.decoder,
                "video/mp4" if role == "video" else "audio/wav")
            if observed.duration_us != duration:
                raise EngineError("production_recipe_timeline_invalid", "Actual remixed outputs retain the exact original full duration.", 422)
            files.append(file)
            actual[role] = observed.model_dump(mode="json")
        return local_observation(tuple(files), {"recipe_id": "audio-remix-preserved-clips-v1",
            "actual_probes": actual, "source_clip_asset_ids": clips, "source_narration_asset_id": audio.asset_id,
            "source_preserved_video_asset_id": video.asset_id, "changed_media_roles": list(outputs),
            "timeline_duration_us": duration, "video_stream_copied": True})
