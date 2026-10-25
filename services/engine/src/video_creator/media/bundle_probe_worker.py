"""Fixed offline audio-clock/final-frame observer for the isolated AV runtime."""
import hashlib
import json
import sys
from fractions import Fraction
from pathlib import Path


def rounded_us(value):
    value *= 1_000_000
    sign = -1 if value < 0 else 1
    return sign * ((2 * abs(value.numerator) + value.denominator) // (2 * value.denominator))


def observe(request):
    path, root = Path(request["path"]), Path(request["storage_root"])
    if (path.is_symlink() or not path.is_file() or not path.resolve().is_relative_to(root.resolve())
        or hashlib.sha256(path.read_bytes()).hexdigest() != request["sha256"]):
        raise ValueError("input denied")
    with path.open("rb") as source:
        header = source.read(16)
    if header[:4] == b"RIFF" and header[8:12] == b"WAVE":
        demuxer = "wav"
    elif header[4:8] == b"ftyp":
        demuxer = "mov"
    else:
        raise ValueError("unsupported input")
    import av

    options = {"protocol_whitelist": "file", "enable_drefs": "0", "use_absolute_path": "0"}
    with av.open(str(path), format=demuxer, options=options) as container:
        if request["mode"] == "clock":
            if len(container.streams.audio) != 1:
                raise ValueError("one actual audio stream required")
            stream = container.streams.audio[0]
            count, rate, first, base, first_pts = 0, None, None, None, None
            for frame in container.decode(stream):
                if not frame.sample_rate or frame.pts is None or frame.time_base is None:
                    raise ValueError("missing clock")
                if rate is None:
                    rate, first_pts, base = frame.sample_rate, frame.pts, Fraction(frame.time_base)
                    first = Fraction(first_pts) * base
                if rate != frame.sample_rate or Fraction(frame.pts) * Fraction(frame.time_base) != first + Fraction(count, rate):
                    raise ValueError("discontinuous clock")
                count += frame.samples
                if count > rate * 600:
                    raise ValueError("duration limit")
            if not count:
                raise ValueError("no audio")
            result = {"clock": {"sample_rate": rate, "decoded_sample_count": count, "stream_index": stream.index,
                                  "timebase_num": base.numerator, "timebase_den": base.denominator, "origin_pts": first_pts},
                      "duration_us": rounded_us(Fraction(count, rate)), "pts_continuity": "verified_exact"}
        elif request["mode"] == "frame":
            wanted = request["at_us"]
            if type(wanted) is not int or not 0 <= wanted <= 600_000_000 or len(container.streams.video) != 1:
                raise ValueError("frame request denied")
            exact = request.get("exact_frame")
            if exact is not None:
                if (type(exact) is not dict or any(type(exact.get(key)) is not int for key in ("pts", "num", "den"))
                    or exact["num"] <= 0 or exact["den"] <= 0):
                    raise ValueError("exact frame denied")
                wanted_time = Fraction(exact["pts"] * exact["num"], exact["den"])
            else:
                wanted_time = Fraction(wanted, 1_000_000)
            stream = container.streams.video[0]
            if not 0 < stream.width <= 4096 or not 0 < stream.height <= 4096 or stream.width * stream.height > 8_294_400:
                raise ValueError("dimensions denied")
            for frame in container.decode(stream):
                if frame.pts is None or frame.time_base is None:
                    raise ValueError("missing frame clock")
                time_base = Fraction(frame.time_base)
                at = Fraction(frame.pts) * time_base
                if at >= wanted_time:
                    if exact is not None and at != wanted_time:
                        raise ValueError("original frame unavailable")
                    pixels = frame.to_ndarray(format="rgb24")
                    result = {"at_us": rounded_us(at), "actual_pts": frame.pts,
                              "timebase_num": time_base.numerator, "timebase_den": time_base.denominator,
                              "decoded_frame_sha256": hashlib.sha256(pixels.tobytes()).hexdigest(),
                              "pixel_format": "rgb24", "width": frame.width, "height": frame.height}
                    break
            else:
                raise ValueError("frame unavailable")
        else:
            raise ValueError("fixed mode required")
    if hashlib.sha256(path.read_bytes()).hexdigest() != request["sha256"]:
        raise ValueError("input changed")
    return dict(result, input_sha256=request["sha256"], tool_version=av.__version__)


if __name__ == "__main__":
    try:
        raw = sys.stdin.buffer.read(16385)
        if len(raw) > 16384:
            raise ValueError("request too large")
        result = observe(json.loads(raw))
        sys.stdout.buffer.write(json.dumps(result, allow_nan=False).encode("utf-8"))
    except Exception:
        sys.stdout.buffer.write(b'{"error_code":"actual_media_observation_failed"}')
        raise SystemExit(1) from None
