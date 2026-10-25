"""ADR17 byte/hash/identity predicates only, not issuer or real authority."""
import hashlib
import json

from t15_evidence import strict_json
from t16_assertions import _units


def reference_dispatch(version, role, kind):
    assert (version, role, kind) == (
        "0.3.0-candidate", "precision_reference", "precision_reference_v03")


def reference_units(units, entries, actual_transcript_ids, duration_us):
    assert type(units) in (list, tuple) and units
    assert all(type(key) is str and key for key in units)
    assert len(units) == len(set(units))
    assert units == actual_transcript_ids
    validated = _units(entries, duration_us)
    assert len(validated) == len(units)
    assert {key for key, _, _ in validated} == set(units)


def reference_hash_layers(document, raw_bytes, actual_receipt_sha256):
    assert strict_json(raw_bytes) == document
    signature = document["signature"]
    assert set(signature) == {"algorithm", "key_id", "digest"}
    assert signature["algorithm"] == "HMAC-SHA256"
    assert type(signature["key_id"]) is str and signature["key_id"]
    assert type(signature["digest"]) is str and len(signature["digest"]) == 64
    int(signature["digest"], 16)
    canonical = lambda value: json.dumps(
        value, sort_keys=True, ensure_ascii=False, allow_nan=False,
        separators=(",", ":")).encode("utf-8")
    unsigned = {key: value for key, value in document.items()
                if key not in {"signature", "content_sha256"}}
    signed_record = {key: value for key, value in document.items()
                     if key != "content_sha256"}
    internal_sha = hashlib.sha256(canonical(signed_record)).hexdigest()
    file_sha = hashlib.sha256(raw_bytes).hexdigest()
    assert document["content_sha256"] == internal_sha
    assert actual_receipt_sha256 == file_sha
    return {"signature_input_bytes": canonical(unsigned),
            "internal_content_sha256": internal_sha, "complete_file_sha256": file_sha,
            "HMAC_or_issuer_trust_verified": False}
