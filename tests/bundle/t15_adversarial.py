"""Own bounded protocol/ZIP material constructors; none starts a decoder."""
from __future__ import annotations

import copy
import io
import zipfile


def asr_output_mutations(original):
    """Each expected rejection needs a future true driver/raw capture case."""
    variants = {}
    for name, field, value in (
        ("bool_pts", "origin_pts", True),
        ("language_type", "language", ["zh"]),
        ("invented_compute", "compute_type", "unverified_superfloat"),
    ):
        item = copy.deepcopy(original)
        item[field] = value
        variants[name] = item
    item = copy.deepcopy(original)
    item["decoded_sample_count"] *= 2
    item["duration_us"] *= 2
    variants["paired_sample_duration"] = item
    item = copy.deepcopy(original)
    item["origin_pts"] += 1
    item["video_audio_offset_us"] += 1
    variants["paired_offset"] = item
    return variants


def zip_bytes(entries):
    """Construct small attack fixtures only; no extraction or huge zip bomb."""
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, content in entries:
            archive.writestr(name, content)
    return stream.getvalue()


def dangerous_zips():
    return {
        "parent_path": zip_bytes([("../Marker.txt", b"owned marker")]),
        "absolute_path": zip_bytes([("/Marker.txt", b"owned marker")]),
        "windows_drive": zip_bytes([("C:/Marker.txt", b"owned marker")]),
        "case_duplicate": zip_bytes([("Text/A.json", b"{}"), ("text/a.json", b"{}")]),
        "exact_duplicate": zip_bytes([("Text/A.json", b"{}"), ("Text/A.json", b"{}")]),
        "missing_manifest": zip_bytes([("Text/A.json", b"{}")]),
        "duplicate_json_key": zip_bytes([("bundle.manifest.json", b'{"a":1,"a":2}')]),
        "nonfinite_json": zip_bytes([("bundle.manifest.json", b'{"a":NaN}')]),
        "projection_as_full": zip_bytes([("delivery.manifest.json",
                                        b'{"delivery_profile":"projection"}')]),
    }
