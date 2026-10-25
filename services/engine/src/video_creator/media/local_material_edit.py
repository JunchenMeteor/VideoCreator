"""Explicit owned-material recipe; uploaded inputs are never model-generated shots."""
from __future__ import annotations

from decimal import Decimal
from fractions import Fraction

from video_creator.domain import contracts as c
from video_creator.domain.errors import EngineError
from video_creator.domain.local_material_production import (
    LocalInputBindingV1,
    LocalTimelineV1,
    validate_local_timeline_bindings,
)
from video_creator.media.local_frame_grid import frame_index, range_frame_count
from video_creator.providers.production_common import (
    install_output,
    local_observation,
    permit_scope,
)
from video_creator.providers.production_resources import file_sha256
from video_creator.workflows.attempt_control import attempt_control

AUDIO_DESTINATION = 'local:ffmpeg-owned-audio-v1'
VISUAL_DESTINATION = 'local:ffmpeg-owned-visual-v1'
EDIT_DESTINATION = 'local:ffmpeg-owned-edit-v1'
SAMPLE_RATE = 48000
MAX_SHOTS = 64
MAX_AUDIO_TRACKS = 32


def seconds(value):
    return format(Decimal(value) / 1_000_000, 'f')


def samples(value):
    result = Fraction(value * SAMPLE_RATE, 1_000_000)
    if result.denominator != 1:
        raise EngineError('local_audio_grid_invalid', 'Audio ranges must fit the exact 48kHz sample grid.', 422)
    return result.numerator


def frames(value, timeline):
    return frame_index(value, timeline.fps_num, timeline.fps_den)


def validate_timeline(bindings, timeline, max_duration_us, *, content_kind='video'):
    if (type(bindings) is not tuple or not bindings or len(bindings) > 96
            or any(type(value) is not LocalInputBindingV1 for value in bindings)
            or type(timeline) is not LocalTimelineV1):
        raise EngineError('local_edit_input_invalid', 'Only the sole current-plan bindings and timeline are accepted.', 422)
    validate_local_timeline_bindings(bindings, timeline)
    if (not 0 < timeline.duration_us <= max_duration_us
            or (timeline.width, timeline.height) not in {(1080, 1920), (1920, 1080)}
            or timeline.fps_num > 60000 or timeline.fps_den > 1001
            or not Fraction(1) <= Fraction(timeline.fps_num, timeline.fps_den) <= 60
            or content_kind not in {'video', 'audio'}
            or not (1 <= len(timeline.shots) <= MAX_SHOTS if content_kind == 'video' else not timeline.shots)
            or content_kind == 'audio' and not timeline.audio_tracks
            or len(timeline.audio_tracks) > MAX_AUDIO_TRACKS):
        raise EngineError('local_timeline_profile_invalid', 'The installed local profile bounds duration, 1080p frames and item counts.', 422)
    if content_kind == 'video':
        frames(timeline.duration_us, timeline)
    samples(timeline.duration_us)
    cursor = 0
    by_id = {value.binding_id: value for value in bindings}
    for shot in timeline.shots:
        if shot.timeline_range.start_us != cursor:
            raise EngineError('local_visual_coverage_invalid', 'Approved shots must cover the full timeline once, in their original order.', 422)
        for boundary in (shot.timeline_range.start_us, shot.timeline_range.end_us):
            frames(boundary, timeline)
        if shot.source_range.end_us - shot.source_range.start_us != shot.timeline_range.end_us - shot.timeline_range.start_us:
            raise EngineError('local_source_range_invalid', 'This profile preserves playback speed and never guesses an unapproved retiming.', 422)
        binding = by_id[shot.input_binding_id]
        if binding.media_type in {'image/jpeg', 'image/png'} and (
                binding.probe.has_video or binding.probe.has_audio or binding.probe.duration_us is not None
                or not binding.probe.width or not binding.probe.height or shot.source_range.start_us != 0):
            raise EngineError('local_static_source_invalid', 'A decoded static image uses a display hold from zero, never intrinsic media time.', 422)
        range_frame_count(shot.timeline_range, timeline)
        cursor = shot.timeline_range.end_us
    if content_kind == 'video' and cursor != timeline.duration_us:
        raise EngineError('local_visual_coverage_invalid', 'Approved shots must reach the exact final frame.', 422)
    for track in timeline.audio_tracks:
        for boundary in (track.source_range.start_us, track.source_range.end_us,
                         track.timeline_range.start_us, track.timeline_range.end_us):
            samples(boundary)
        if (track.source_range.end_us - track.source_range.start_us
                != track.timeline_range.end_us - track.timeline_range.start_us):
            raise EngineError('local_audio_range_invalid', 'Audio preserves its approved duration; the sole timeline validates finite nonnegative gain.', 422)


def binding_asset(bundle, lease, binding, decoder):
    """Real controlled Asset read, byte identity and independent full decode."""
    asset = bundle.asset(lease, binding.asset_id)
    path = bundle.content_path(lease, binding.asset_id)
    if (type(asset) is not c.AssetRecord
            or (asset.asset_id, asset.sha256, asset.size, asset.media_type, asset.source, asset.probe)
            != (binding.asset_id, binding.sha256, binding.size, binding.media_type, binding.source_ref, binding.probe)
            or path.stat().st_size != binding.size or file_sha256(path) != binding.sha256):
        raise EngineError('local_input_changed', 'The plan binding differs from its actual admitted input Asset.', 409)
    actual = decoder(path, binding.media_type)
    if (type(actual) is not c.MediaProbe or not actual.decoded or actual != asset.probe
            or path.stat().st_size != binding.size or file_sha256(path) != binding.sha256):
        raise EngineError('local_input_decode_invalid', 'Actual input bytes must fully decode to their original registered evidence.', 422)
    return asset, path, actual


def _fit(width, height, fit):
    if fit == 'contain':
        return (f'scale={width}:{height}:force_original_aspect_ratio=decrease,'
                f'pad={width}:{height}:(ow-iw)/2:(oh-ih)/2')
    if fit == 'cover':
        return f'scale={width}:{height}:force_original_aspect_ratio=increase,crop={width}:{height}'
    raise EngineError('local_fit_invalid', 'Only the sole contain/cover selection is accepted.', 422)


def _input(runtime, argv, path):
    argv.extend([*runtime._input_args(runtime._input_format(path)), '-i', str(path)])


def _audio_filter(index, track, label):
    length = samples(track.timeline_range.end_us - track.timeline_range.start_us)
    # The original approved microsecond range is used before resampling. The
    # output sample count is exact; no source timing is inferred from text.
    return (f'[{index}:a:0]asetpts=PTS-STARTPTS,atrim=start={seconds(track.source_range.start_us)}:'
            f'end={seconds(track.source_range.end_us)},asetpts=PTS-STARTPTS,'
            f'aresample={SAMPLE_RATE},aformat=channel_layouts=mono,'
            f'atrim=end_sample={length},volume={track.gain},'
            f'adelay={samples(track.timeline_range.start_us)}S:all=1[{label}]')


class _LocalDriver:
    def __init__(self, *, engine, worker, bundle, decoder, runtime, route_id, lease,
                 outputs, bindings, timeline, max_duration_us, cancel, deadline_monotonic):
        request = engine.get_request(lease)
        self.content_kind = 'video' if 'video' in request.outputs else 'audio'
        validate_timeline(bindings, timeline, max_duration_us, content_kind=self.content_kind)
        self.engine, self.worker, self.bundle = engine, worker, bundle
        self.decoder, self.runtime, self.route_id = decoder, runtime, route_id
        self.lease, self.outputs, self.bindings, self.timeline = lease, outputs, bindings, timeline
        self.by_id = {value.binding_id: value for value in bindings}
        self.control = attempt_control(cancel, deadline_monotonic)

    def _binding(self, identity):
        binding = self.by_id[identity]
        return binding, *binding_asset(self.bundle, self.lease, binding, self.decoder)

    def _input_audio(self, binding, path, probe, source_range):
        if (binding.usage not in {'narration', 'background_audio'} or not probe.has_audio
                or probe.duration_us is None or source_range.end_us > probe.duration_us):
            raise EngineError('local_audio_source_invalid', 'Actual selected source must contain the entire approved audio range.', 422)
        self.runtime._input_format(path)

    def _check_inputs(self, bindings):
        for binding in bindings:
            binding_asset(self.bundle, self.lease, binding, self.decoder)

    def _complete(self, kinds, *, video_duration=None, audio_duration=None, video_has_audio=None):
        actual = []
        # Check every output before completing even the first handle. A partial
        # or wrongly timed file remains reconciliation evidence, not a master.
        for output, kind in zip(self.outputs, kinds, strict=True):
            probe = self.decoder(output.partial_path, kind)
            if type(probe) is not c.MediaProbe or not probe.decoded or probe.media_type != kind:
                raise EngineError('local_output_decode_invalid', 'Every complete local output must independently decode.', 422)
            if kind == 'video/mp4' and (not probe.has_video or probe.duration_us != video_duration
                    or video_has_audio is not None and probe.has_audio is not video_has_audio
                    or (probe.width, probe.height) != (self.timeline.width, self.timeline.height)):
                raise EngineError('local_output_timeline_invalid', 'Actual video must match the exact approved frame timeline.', 422)
            if kind == 'audio/wav' and (not probe.has_audio or probe.has_video or probe.duration_us != audio_duration):
                raise EngineError('local_output_timeline_invalid', 'Actual independent audio must match its exact approved sample timeline.', 422)
            if kind == 'image/jpeg' and (probe.has_video or probe.has_audio or probe.duration_us is not None
                    or (probe.width, probe.height) != (self.timeline.width, self.timeline.height)):
                raise EngineError('local_cover_invalid', 'Actual cover is a static decoded frame, without invented audio or duration.', 422)
            actual.append(probe)
        files = []
        for output, kind, previous in zip(self.outputs, kinds, actual, strict=True):
            file, observed = install_output(self.engine, self.worker, self.lease, output, self.decoder, kind)
            if observed != previous:
                raise EngineError('local_output_changed', 'The completed output changed during controlled registration.', 409, 'reconcile')
            files.append(file)
        return tuple(files), [value.model_dump(mode='json') for value in actual]


class LocalAudioNormalizeDriver(_LocalDriver):
    """Actual selected narration tracks → distinct PCM WAV, including mapped gaps."""
    def __call__(self, permit, secret):
        with self.control.activate():
            permit_scope(self.engine, permit, self.lease, self.route_id, 'render', AUDIO_DESTINATION, local=True, secret=secret)
            tracks = tuple(track for track in self.timeline.audio_tracks if self.by_id[track.input_binding_id].usage == 'narration')
            if len(self.outputs) != 1 or not tracks:
                raise EngineError('local_narration_missing', 'This selected narration output requires actual admitted narration tracks.', 422)
            argv, graph, used = ['-nostdin', '-v', 'error', '-n'], [], []
            for index, track in enumerate(tracks):
                binding, _asset, path, probe = self._binding(track.input_binding_id)
                self._input_audio(binding, path, probe, track.source_range)
                _input(self.runtime, argv, path)
                graph.append(_audio_filter(index, track, f'a{index}'))
                used.append(binding)
            labels = ''.join(f'[a{index}]' for index in range(len(tracks)))
            graph.append(f'{labels}amix=inputs={len(tracks)}:duration=longest:normalize=0,'
                         f'apad,atrim=end_sample={samples(self.timeline.duration_us)},alimiter=limit=0.95:latency=1[out]')
            argv.extend(['-filter_complex', ';'.join(graph), '-map', '[out]', '-c:a', 'pcm_s16le',
                         '-ar', str(SAMPLE_RATE), '-ac', '1', '-f', 'wav', str(self.outputs[0].partial_path)])
            self.runtime._run(self.runtime.ffmpeg, argv, timeout=self.control.remaining(300))
            self._check_inputs(used)
            files, observed = self._complete(('audio/wav',), audio_duration=self.timeline.duration_us)
            return local_observation(files, {'profile': 'local-owned-assets-v1', 'provenance': 'normalized_uploaded_narration',
                'actual_probes': observed, 'source_bindings': [value.model_dump(mode='json') for value in used],
                'audio_mappings': [value.model_dump(mode='json') for value in tracks],
                'timeline_duration_us': self.timeline.duration_us, 'sample_rate': SAMPLE_RATE})


class LocalVisualMaterialDriver(_LocalDriver):
    """A real image hold/motion or video range → silent, normalized derivative."""
    def __init__(self, *, shot_id, **kwargs):
        super().__init__(**kwargs)
        self.shot = next((shot for shot in self.timeline.shots if shot.shot_id == shot_id), None)
        if self.shot is None:
            raise EngineError('local_shot_missing', 'The selected shot is absent from the sole current plan.', 422)

    def __call__(self, permit, secret):
        with self.control.activate():
            permit_scope(self.engine, permit, self.lease, self.route_id, 'render', VISUAL_DESTINATION, local=True, secret=secret)
            if len(self.outputs) != 1:
                raise EngineError('local_shot_output_invalid', 'A derived shot uses exactly one original output reservation.', 422)
            binding, _asset, path, probe = self._binding(self.shot.input_binding_id)
            still = binding.media_type in {'image/jpeg', 'image/png'}
            if (binding.usage != 'visual' or probe.media_type != binding.media_type
                    or not probe.width or not probe.height
                    or (still and (probe.has_video or probe.has_audio or probe.duration_us is not None))
                    or (not still and (binding.media_type != 'video/mp4' or not probe.has_video))):
                raise EngineError('local_visual_source_invalid', 'Use the actual decoded static-image or video stream evidence, without an invented image duration.', 422)
            duration = self.shot.timeline_range.end_us - self.shot.timeline_range.start_us
            count = range_frame_count(self.shot.timeline_range, self.timeline)
            rate = f'{self.timeline.fps_num}/{self.timeline.fps_den}'
            fit = _fit(self.timeline.width, self.timeline.height, self.shot.fit)
            if still:
                if (probe.duration_us is not None or probe.has_audio or self.shot.source_range.start_us != 0
                        or self.shot.source_range.end_us != duration):
                    raise EngineError('local_static_source_invalid', 'A static input has no intrinsic audio/video time or nonzero seek.', 422)
                # source_range in the approved still plan is a DISPLAY HOLD
                # extent, never the source image's measured duration. The result
                # preserves source_media_range=None and the actual static probe.
                graph = (f'loop=loop=-1:size=1:start=0,{fit},setsar=1,'
                         f'fps={rate}:start_time=0,'
                         f'trim=end_frame={count},setpts=PTS-STARTPTS,format=yuv420p')
                source_media_range = None
            else:
                if binding.media_type != 'video/mp4' or probe.duration_us is None or self.shot.source_range.end_us > probe.duration_us:
                    raise EngineError('local_video_source_invalid', 'The actual source video must cover the complete approved range.', 422)
                graph = (f'setpts=PTS-STARTPTS,trim=start={seconds(self.shot.source_range.start_us)}:end={seconds(self.shot.source_range.end_us)},'
                         f'setpts=PTS-STARTPTS,fps={rate}:start_time=0,{fit},setsar=1,'
                         f'trim=end_frame={count},format=yuv420p')
                source_media_range = self.shot.source_range.model_dump(mode='json')
            argv = ['-nostdin', '-v', 'error', '-n']
            _input(self.runtime, argv, path)
            argv.extend(['-map', '0:v:0', '-an', '-vf', graph, '-frames:v', str(count),
                         '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-r', rate, '-movflags', '+faststart',
                         '-f', 'mp4', str(self.outputs[0].partial_path)])
            self.runtime._run(self.runtime.ffmpeg, argv, timeout=self.control.remaining(300))
            self._check_inputs((binding,))
            files, observed = self._complete(('video/mp4',), video_duration=duration, video_has_audio=False)
            return local_observation(files, {'profile': 'local-owned-assets-v1', 'provenance': 'derived_from_owned_material',
                'actual_probes': observed, 'source_binding': binding.model_dump(mode='json'),
                'shot_id': self.shot.shot_id, 'source_media_range': source_media_range,
                'source_kind': 'static_image' if still else 'video', 'display_range': self.shot.timeline_range.model_dump(mode='json'),
                'planned_source_range': self.shot.source_range.model_dump(mode='json'),
                'derived_duration_us': duration, 'target_frame_count': count, 'target_fps_num': self.timeline.fps_num,
                'target_fps_den': self.timeline.fps_den, 'implicit_source_audio': False, 'model_generated': False})


class LocalMaterialEditDriver(_LocalDriver):
    """Only applicable actual masters; source audio is always explicit."""
    def __init__(self, *, clips, narration_audio, **kwargs):
        super().__init__(**kwargs)
        if (type(clips) is not tuple or len(clips) != len(self.timeline.shots)
                or any(type(item) is not tuple or len(item) != 2 or any(type(value) is not str for value in item) for item in clips)
                or tuple(item[0] for item in clips) != tuple(shot.shot_id for shot in self.timeline.shots)
                or len({item[1] for item in clips}) != len(clips)
                or narration_audio is not None and type(narration_audio) is not str
                or narration_audio in {item[1] for item in clips}):
            raise EngineError('local_master_sources_invalid', 'Use the actual ordered per-shot derivatives and separate normalized narration.', 422)
        has_narration = any(self.by_id[track.input_binding_id].usage == 'narration' for track in self.timeline.audio_tracks)
        if has_narration != (narration_audio is not None):
            raise EngineError('local_narration_source_conflict', 'A normalized narration Asset exists exactly when the approved timeline has narration tracks.', 422)
        self.clips, self.narration_audio = clips, narration_audio

    def _derived(self, asset_id, kind):
        asset = self.bundle.asset(self.lease, asset_id)
        path = self.bundle.content_path(self.lease, asset_id)
        if (type(asset) is not c.AssetRecord or asset.media_type != kind
                or asset_id in {value.asset_id for value in self.bindings}
                or path.stat().st_size != asset.size or file_sha256(path) != asset.sha256):
            raise EngineError('local_derivative_changed', 'A derivative must be a distinct real registered Asset with intact bytes.', 409)
        probe = self.decoder(path, kind)
        if type(probe) is not c.MediaProbe or not probe.decoded or probe != asset.probe:
            raise EngineError('local_derivative_decode_invalid', 'Actual derivative must still fully decode to its registered evidence.', 422)
        return asset, path, probe

    def __call__(self, permit, secret):
        with self.control.activate():
            permit_scope(self.engine, permit, self.lease, self.route_id, 'render', EDIT_DESTINATION, local=True, secret=secret)
            has_audio = bool(self.timeline.audio_tracks)
            roles = (('video', 'video/mp4'),) if self.content_kind == 'video' else ()
            if has_audio:
                roles += (('mixed_audio', 'audio/wav'),)
            if self.content_kind == 'video':
                roles += (('cover', 'image/jpeg'),)
            if not roles or len(self.outputs) != len(roles):
                raise EngineError('local_edit_output_invalid', 'Reserve exactly the applicable actual video, mix and cover in their original order.', 422)
            outputs = {role: output for (role, _mime), output in zip(roles, self.outputs, strict=True)}
            argv, graph, used_assets = ['-nostdin', '-v', 'error', '-n'], [], []
            rate = f'{self.timeline.fps_num}/{self.timeline.fps_den}'
            for index, ((_shot_id, identity), shot) in enumerate(zip(self.clips, self.timeline.shots, strict=True)):
                asset, path, probe = self._derived(identity, 'video/mp4')
                duration = shot.timeline_range.end_us - shot.timeline_range.start_us
                if (not probe.has_video or probe.has_audio or probe.duration_us != duration
                        or (probe.width, probe.height) != (self.timeline.width, self.timeline.height)):
                    raise EngineError('local_derivative_timeline_invalid', 'Each silent real derivative must match its approved shot duration and frame.', 422)
                _input(self.runtime, argv, path)
                graph.append(f'[{index}:v:0]setpts=PTS-STARTPTS,fps={rate}:start_time=0,'
                             f'trim=end_frame={range_frame_count(shot.timeline_range, self.timeline)},setsar=1,format=yuv420p[v{index}]')
                used_assets.append(asset)
            audio_labels, input_index, speech = [], len(self.clips), None
            if self.narration_audio is not None:
                speech, speech_path, speech_probe = self._derived(self.narration_audio, 'audio/wav')
                if (not speech_probe.has_audio or speech_probe.has_video or speech_probe.duration_us != self.timeline.duration_us):
                    raise EngineError('local_narration_timeline_invalid', 'Normalized independent narration must retain the exact whole timeline.', 422)
                _input(self.runtime, argv, speech_path)
                graph.append(f'[{input_index}:a:0]aresample={SAMPLE_RATE},aformat=channel_layouts=mono,'
                             f'asetpts=PTS-STARTPTS,atrim=end_sample={samples(self.timeline.duration_us)}[speech]')
                audio_labels.append('[speech]')
                input_index += 1
            tracks = tuple(track for track in self.timeline.audio_tracks if self.by_id[track.input_binding_id].usage == 'background_audio')
            used_bindings = []
            for offset, track in enumerate(tracks):
                binding, _asset, path, probe = self._binding(track.input_binding_id)
                self._input_audio(binding, path, probe, track.source_range)
                _input(self.runtime, argv, path)
                graph.append(_audio_filter(input_index + offset, track, f'bed{offset}'))
                audio_labels.append(f'[bed{offset}]')
                used_bindings.append(binding)
            if self.clips:
                visual_labels = ''.join(f'[v{index}]' for index in range(len(self.clips)))
                graph.append(f'{visual_labels}concat=n={len(self.clips)}:v=1:a=0[v]')
            if audio_labels:
                mix = (f'{"".join(audio_labels)}amix=inputs={len(audio_labels)}:duration=longest:normalize=0,'
                       if len(audio_labels) > 1 else audio_labels[0] + 'anull,')
                split = 'asplit=2[encoded_audio][mixed]' if self.content_kind == 'video' else 'anull[mixed]'
                graph.append(f'{mix}apad,atrim=end_sample={samples(self.timeline.duration_us)},'
                             f'alimiter=limit=0.95:latency=1,{split}')
            argv.extend(['-filter_complex', ';'.join(graph)])
            if self.content_kind == 'video':
                argv.extend(['-map', '[v]'])
                argv.extend(['-map', '[encoded_audio]'] if has_audio else ['-an'])
                argv.extend([
                         '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-r', rate, '-c:a', 'aac', '-ar', str(SAMPLE_RATE),
                         '-movflags', '+faststart', '-t', seconds(self.timeline.duration_us), '-f', 'mp4', str(outputs['video'].partial_path)])
            if has_audio:
                argv.extend(['-map', '[mixed]', '-c:a', 'pcm_s16le', '-ar', str(SAMPLE_RATE), '-ac', '1', '-f', 'wav', str(outputs['mixed_audio'].partial_path)])
            self.runtime._run(self.runtime.ffmpeg, argv, timeout=self.control.remaining(300))
            if self.content_kind == 'video':
                self.runtime._run(self.runtime.ffmpeg, ['-nostdin', '-v', 'error', '-n',
                *self.runtime._input_args(self.runtime._input_format(outputs['video'].partial_path)), '-i', str(outputs['video'].partial_path),
                '-map', '0:v:0', '-frames:v', '1', '-q:v', '3', '-update', '1', '-f', 'image2', str(outputs['cover'].partial_path)],
                timeout=self.control.remaining(30))
            for asset in (*used_assets, *((speech,) if speech is not None else ())):
                self._derived(asset.asset_id, asset.media_type)
            self._check_inputs(used_bindings)
            files, observed = self._complete(tuple(mime for _role, mime in roles),
                video_duration=self.timeline.duration_us, audio_duration=self.timeline.duration_us, video_has_audio=has_audio)
            return local_observation(files, {'profile': 'local-owned-assets-v1', 'provenance': 'edited_owned_material',
                'actual_probes': observed, 'source_clip_asset_ids': [value.asset_id for value in used_assets],
                'source_narration_asset_id': None if speech is None else speech.asset_id,
                'source_background_bindings': [value.model_dump(mode='json') for value in used_bindings],
                'content_kind': self.content_kind, 'applicable_edit_roles': [role for role, _mime in roles],
                'audio_mappings': [value.model_dump(mode='json') for value in tracks],
                'background_policy': 'explicit_selected_tracks' if tracks else 'explicit_no_background',
                'timeline': self.timeline.model_dump(mode='json'), 'sample_rate': SAMPLE_RATE,
                'model_generated_shots': False, 'scope': 'actual variable owned-material edit; not autonomous model creation or ASR'})
