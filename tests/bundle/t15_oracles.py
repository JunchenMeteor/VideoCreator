"""Independent assertions over captured evidence, not a second public schema."""
from __future__ import annotations

import math
from fractions import Fraction

from t15_evidence import controlled_file, digest, strict_json

DEFAULT_OUTPUTS = frozenset({
    "video", "narration_audio", "mixed_audio", "approved_script",
    "actual_transcript", "subtitles", "semantic_manifest", "rag_chunks",
})


def integer(value):
    assert type(value) is int, "strict integer excludes bool/float/string"
    return value


def interval(value, duration):
    start, end = integer(value["start_us"]), integer(value["end_us"])
    assert 0 <= start < end <= integer(duration)
    return start, end


def record_hash(record):
    """ADR0013 hash of already JSON-serialized public values, no normalization."""
    import json
    data = {key: value for key, value in record.items() if key != "content_sha256"}
    raw = json.dumps(data, ensure_ascii=False, allow_nan=False, sort_keys=True,
                     separators=(",", ":")).encode("utf-8")
    assert record["content_sha256"] == digest(raw)


def independent_baseline(root, admission):
    """Pins come from approved test baseline, never candidate Bundle JSON."""
    assert admission["review_approved"] is True
    assert admission["corpus_kind"] == "independent_human_reference"
    files = {}
    for role in ("reference", "adjudication", "authority_registration"):
        pin = admission["files"][role]
        actual = controlled_file(root, pin["relative_path"])
        assert actual["sha256"] == pin["sha256"] and actual["size"] == pin["size"]
        files[role] = strict_json(actual["bytes"])
    assert files["reference"]["input_audio_sha256"] == admission["input_audio_sha256"]
    assert files["adjudication"]["reference_sha256"] == admission["files"]["reference"]["sha256"]
    assert files["authority_registration"]["authority_ref"] == admission["authority_ref"]
    assert files["authority_registration"]["criterion_version_ref"] == admission["criterion_version_ref"]
    return files


def artifact_bytes(manifest, package_root, expected_ref):
    """Exact origin/hash/role and every controlled material/media byte."""
    assert expected_ref["manifest_sha256"] == digest(expected_ref["manifest_bytes"])
    assert strict_json(expected_ref["manifest_bytes"]) == manifest
    for key in ("instance_id", "bundle_id", "bundle_revision_id",
                "schema_version", "bundle_format_version"):
        assert manifest[key] == expected_ref[key]
    assert set(manifest["requested_outputs"]) == DEFAULT_OUTPUTS
    outputs = manifest["outputs"]
    assert len(outputs) == 8 and {item["role"] for item in outputs} == DEFAULT_OUTPUTS
    indexed = {}
    paths = set()
    for artifact in manifest["artifacts"]:
        key = artifact["artifact_id"]
        assert key not in indexed
        assert artifact["relative_path"].casefold() not in paths
        paths.add(artifact["relative_path"].casefold())
        actual = controlled_file(package_root, artifact["relative_path"])
        assert actual["sha256"] == artifact["sha256"]
        assert actual["size"] == integer(artifact["size"]) > 0
        assert bool(artifact.get("asset_id")) != bool(artifact.get("material_id"))
        indexed[key] = artifact
    for output in outputs:
        assert output["status"] == "present" and output["artifact_ids"]
        assert len(set(output["artifact_ids"])) == len(output["artifact_ids"])
        for key in output["artifact_ids"]:
            assert key in indexed and output["role"] in indexed[key]["roles"]
    return indexed


def precision(report, document, independent_reference, authority_receipt):
    """Candidate nearest-rank max-boundary metric; trusted input is out of band."""
    record_hash(report)
    alignment = document["alignment"]
    transcript = document["transcript"]
    record_hash(alignment)
    record_hash(transcript)
    assert report["authority_ref"] == authority_receipt["authority_ref"]
    assert authority_receipt["registered_by_trusted_configuration"] is True
    assert authority_receipt["model_or_payload_supplied"] is False
    assert authority_receipt["reference_sha256"] == independent_reference["sha256"]
    assert authority_receipt["reference_material_id"] == report["reference_material_id"]
    assert authority_receipt["criterion_version_ref"] == report["criterion_version_ref"]
    assert independent_reference["human_annotation_verified"] is True
    assert independent_reference["adjudication_receipt_sha256"]
    assert report["input_audio_sha256"] == independent_reference["input_audio_sha256"]
    assert report["input_audio_sha256"] == transcript["input_audio_sha256"]
    assert report["alignment_revision_id"] == alignment["alignment_revision_id"]
    assert report["alignment_content_sha256"] == alignment["content_sha256"]
    assert report["units"] == alignment["units"] == "utterance"
    # Set membership must be exact; a model cannot cherry-pick favorable units.
    expected = independent_reference["ranges_by_unit"]
    assert type(expected) is dict and expected
    for key, span in expected.items():
        assert type(key) is str and key
        interval(span, transcript["duration_us"])
    # Validate every original entry before constructing any ID->range map.
    raw_boundaries = alignment["boundaries"]
    assert type(raw_boundaries) in (list, tuple)
    assert len(raw_boundaries) == len(expected)
    unit_ids, transcript_ids = set(), set()
    for unit in raw_boundaries:
        assert type(unit) is dict
        own_id, transcript_id = unit["unit_id"], unit["transcript_unit_id"]
        assert type(own_id) is str and own_id
        assert type(transcript_id) is str and transcript_id
        assert own_id not in unit_ids and transcript_id not in transcript_ids
        interval(unit["intrinsic_range"], transcript["duration_us"])
        unit_ids.add(own_id)
        transcript_ids.add(transcript_id)
    assert transcript_ids == set(expected)
    pairs = report["boundaries"]
    assert type(pairs) in (list, tuple) and len(pairs) == len(expected)
    report_ids = set()
    for pair in pairs:
        assert type(pair) is dict
        key = pair["transcript_unit_id"]
        assert type(key) is str and key and key not in report_ids
        interval(pair["predicted_range"], transcript["duration_us"])
        interval(pair["reference_range"], transcript["duration_us"])
        report_ids.add(key)
    assert report_ids == transcript_ids == set(expected)
    predicted = {unit["transcript_unit_id"]: unit["intrinsic_range"]
                 for unit in raw_boundaries}
    errors = []
    for pair in pairs:
        key = pair["transcript_unit_id"]
        assert pair["predicted_range"] == predicted[key]
        assert pair["reference_range"] == expected[key]
        actual = interval(pair["predicted_range"], transcript["duration_us"])
        reference = interval(pair["reference_range"], transcript["duration_us"])
        errors.append(max(abs(a - b) for a, b in zip(actual, reference)))
    p95 = sorted(errors)[math.ceil(Fraction(95, 100) * len(errors)) - 1]
    assessment = alignment["precision"]
    assert assessment["status"] == "measured"
    assert assessment["sample_count"] == len(errors)
    assert integer(assessment["p95_error_us"]) == p95 <= 200_000
    assert assessment["criterion_version_ref"] == report["criterion_version_ref"]
    assert assessment["evaluation_material_id"] == authority_receipt["report_material_id"]
    return {"sample_count": len(errors), "p95_error_us": p95, "per_unit": errors}


def expected_no_publication(before, after):
    """Snapshots supplied by a true runtime observer, never a fixture DB writer."""
    for key in ("visible_bundle_refs", "success_events", "delivery_steps",
                "successful_runs", "successful_productions"):
        assert before[key] == after[key], f"premature success changed {key}"


def permissions(observations):
    assert observations
    for item in observations:
        assert item["request_completed"] is True
        assert item["unauthorized"] is True
        assert item["status"] in {401, 403, 404}
        assert item["content_bytes"] == 0 and item["semantic_records"] == 0
        assert item["status"] not in {200, 206, 304}
        assert item["principal_from_payload"] is False


def atomic_visible(snapshot):
    facts = [snapshot[key] for key in ("bundle_published", "delivery_step_succeeded",
                                      "run_succeeded", "production_succeeded",
                                      "bundle_ready_outbox", "production_success_outbox")]
    assert all(type(value) is bool for value in facts)
    assert all(facts) or not any(facts), "half-committed visibility"
    if all(facts):
        assert snapshot["all_exact_files_persisted_and_hash_verified"] is True
        assert snapshot["outbox_duplicates"] == 0
        assert snapshot["fence_valid_at_commit"] is True
        assert snapshot["cancelled_at_commit"] is False


def retrieval(labels, responses):
    """Metrics alone do not prove labels are independent/human reviewed."""
    topics = labels["topics"]
    candidates = labels["candidates"]
    assert len(set(topics)) == len(topics) >= 30
    assert len(set(candidates)) == len(candidates) >= 60
    assert labels["independently_human_reviewed"] is True
    expected = labels["relevant_by_topic"]
    assert set(expected) == set(topics) == set(responses)
    tp = fp = relevant = refusals = 0
    for topic in topics:
        good = set(expected[topic])
        got = responses[topic]
        assert len(set(got)) == len(got) and set(got) <= set(candidates)
        assert good <= set(candidates)
        relevant += len(good)
        tp += len(good & set(got))
        fp += len(set(got) - good)
        refusals += not bool(got)
    assert tp + fp > 0, "all refusals cannot meet MM05"
    result = {"precision": Fraction(tp, tp + fp),
              "recall": Fraction(tp, relevant) if relevant else Fraction(0),
              "refusal_rate": Fraction(refusals, len(topics)),
              "tp": tp, "fp": fp, "labelled_relevant": relevant}
    assert result["precision"] >= Fraction(9, 10)
    return result
