"""ADR0075 integer frame boundaries; this is timing, never source authority."""
from video_creator.domain.errors import EngineError
from video_creator.domain.local_bundle import local_frame_time_us


def frame_time_us(frame, fps_num, fps_den):
    return local_frame_time_us(frame, fps_num, fps_den)


def frame_index(time_us, fps_num, fps_den):
    if type(time_us) is not int or time_us < 0:
        raise EngineError('local_frame_grid_invalid', 'Frame boundaries use nonnegative integer microseconds.', 422)
    # Rates in this profile are at most 60fps: nearest-frame inversion has one
    # candidate. Validate the exact rounded boundary, never mutate a saved plan.
    frame_time_us(0, fps_num, fps_den)
    frame = (2 * time_us * fps_num + 1_000_000 * fps_den) // (2 * 1_000_000 * fps_den)
    if frame_time_us(frame, fps_num, fps_den) != time_us:
        raise EngineError('local_frame_grid_invalid', 'The saved plan boundary is not on its declared integer frame grid.', 422)
    return frame


def range_frame_count(media_range, timeline):
    start = frame_index(media_range.start_us, timeline.fps_num, timeline.fps_den)
    end = frame_index(media_range.end_us, timeline.fps_num, timeline.fps_den)
    if end <= start:
        raise EngineError('local_frame_grid_invalid', 'Each shot occupies at least one actual planned frame.', 422)
    return end - start
