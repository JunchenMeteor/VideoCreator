"""RV16 narrow pure fixtures; synthetic precision is not human ground truth."""
from __future__ import annotations

import copy
import json
import unittest

from t15_evidence import digest, strict_json
from t15_oracles import precision


def hashed(record):
    result = copy.deepcopy(record)
    result.pop("content_sha256", None)
    result["content_sha256"] = digest(json.dumps(
        result, ensure_ascii=False, sort_keys=True, allow_nan=False,
        separators=(",", ":")).encode("utf-8"))
    return result


def specimen(errors=(0,)):
    references = {f"U{i}": {"start_us": 1_000_000 + i * 2_000_000,
                             "end_us": 2_000_000 + i * 2_000_000}
                  for i in range(len(errors))}
    ranges = {key: {"start_us": value["start_us"] + errors[i],
                    "end_us": value["end_us"] + errors[i]}
              for i, (key, value) in enumerate(references.items())}
    transcript = hashed({"input_audio_sha256": "a" * 64,
                         "duration_us": 100_000_000})
    p95 = sorted(errors)[(95 * len(errors) + 99) // 100 - 1]
    alignment = hashed({
        "alignment_revision_id": "synthetic-alignment", "units": "utterance",
        "boundaries": [{"unit_id": f"A{i}", "transcript_unit_id": key,
                        "intrinsic_range": span} for i, (key, span) in enumerate(ranges.items())],
        "precision": {"status": "measured", "sample_count": len(errors),
                      "p95_error_us": p95, "criterion_version_ref": "synthetic-criterion",
                      "evaluation_material_id": "synthetic-report"}})
    report = {
        "authority_ref": "synthetic-authority",
        "reference_material_id": "synthetic-reference",
        "criterion_version_ref": "synthetic-criterion",
        "input_audio_sha256": "a" * 64, "units": "utterance",
        "boundaries": [{"transcript_unit_id": key, "predicted_range": ranges[key],
                        "reference_range": span} for key, span in references.items()]}
    reference = {"sha256": "b" * 64, "human_annotation_verified": True,
                 "adjudication_receipt_sha256": "c" * 64,
                 "input_audio_sha256": "a" * 64, "ranges_by_unit": references}
    authority = {"authority_ref": "synthetic-authority",
                 "registered_by_trusted_configuration": True,
                 "model_or_payload_supplied": False, "reference_sha256": "b" * 64,
                 "reference_material_id": "synthetic-reference",
                 "criterion_version_ref": "synthetic-criterion",
                 "report_material_id": "synthetic-report"}
    return rehash({"alignment": alignment, "transcript": transcript},
                  report, reference, authority)


def rehash(document, report, reference, authority):
    document = copy.deepcopy(document)
    document["alignment"] = hashed(document["alignment"])
    report = copy.deepcopy(report)
    report["alignment_revision_id"] = document["alignment"]["alignment_revision_id"]
    report["alignment_content_sha256"] = document["alignment"]["content_sha256"]
    return hashed(report), document, copy.deepcopy(reference), copy.deepcopy(authority)


class RevisionTwoSanity(unittest.TestCase):
    def test_json_positive_negative_and_nested_exponent_overflow(self):
        for raw in (b'{"x":1e999}', b'{"x":-1e999}',
                    b'{"x":[1,{"y":1e999}]}', b'{"x":[{"y":-1e999}]}',
                    b'[1e999]', b'[-1e999]'):
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                strict_json(raw)
        self.assertEqual(strict_json(b'{"x":[1e3,-2.5,1e-3]}'),
                         {"x": [1000.0, -2.5, 0.001]})

    def test_bad_first_good_last_cannot_disappear(self):
        report, document, reference, authority = specimen()
        bad = copy.deepcopy(document["alignment"]["boundaries"][0])
        bad["intrinsic_range"] = {"start_us": 1_500_000, "end_us": 2_500_000}
        document["alignment"]["boundaries"].insert(0, bad)
        with self.assertRaises(AssertionError):
            precision(*rehash(document, report, reference, authority))

    def test_good_first_bad_last_duplicate_is_rejected(self):
        report, document, reference, authority = specimen()
        bad = copy.deepcopy(document["alignment"]["boundaries"][0])
        bad["intrinsic_range"] = {"start_us": 1_500_000, "end_us": 2_500_000}
        document["alignment"]["boundaries"].append(bad)
        with self.assertRaises(AssertionError):
            precision(*rehash(document, report, reference, authority))

    def test_equal_duplicate_is_rejected(self):
        report, document, reference, authority = specimen()
        document["alignment"]["boundaries"].append(
            copy.deepcopy(document["alignment"]["boundaries"][0]))
        with self.assertRaises(AssertionError):
            precision(*rehash(document, report, reference, authority))

    def test_missing_and_extra_ids_rejected(self):
        for kind in ("missing", "extra", "replace"):
            report, document, reference, authority = specimen((0, 0))
            boundaries = document["alignment"]["boundaries"]
            if kind == "missing":
                boundaries.pop()
            elif kind == "extra":
                boundaries.append({"unit_id": "AX", "transcript_unit_id": "UX",
                                   "intrinsic_range": {"start_us": 7_000_000, "end_us": 8_000_000}})
            else:
                boundaries[1]["transcript_unit_id"] = "UX"
            with self.subTest(kind=kind), self.assertRaises(AssertionError):
                precision(*rehash(document, report, reference, authority))

    def test_strict_ids_before_mapping(self):
        for field in ("unit_id", "transcript_unit_id"):
            for invalid in (True, 1, "", None, ["U0"]):
                report, document, reference, authority = specimen()
                document["alignment"]["boundaries"][0][field] = invalid
                with self.subTest(field=field, invalid=invalid), self.assertRaises(AssertionError):
                    precision(*rehash(document, report, reference, authority))

    def test_duplicate_alignment_own_unit_ids_rejected(self):
        report, document, reference, authority = specimen((0, 0))
        document["alignment"]["boundaries"][1]["unit_id"] = "A0"
        with self.assertRaises(AssertionError):
            precision(*rehash(document, report, reference, authority))

    def test_all_original_ranges_checked_before_mapping(self):
        for invalid in ({"start_us": False, "end_us": 2_000_000},
                        {"start_us": -1, "end_us": 2_000_000},
                        {"start_us": 1_000_000, "end_us": 100_000_001}):
            report, document, reference, authority = specimen()
            bad = {"unit_id": "ABad", "transcript_unit_id": "U0", "intrinsic_range": invalid}
            document["alignment"]["boundaries"].insert(0, bad)
            with self.subTest(invalid=invalid), self.assertRaises(AssertionError):
                precision(*rehash(document, report, reference, authority))

    def test_report_duplicate_and_omission_rejected(self):
        for kind in ("duplicate", "missing", "extra"):
            report, document, reference, authority = specimen((0, 0))
            if kind == "duplicate":
                report["boundaries"][1] = copy.deepcopy(report["boundaries"][0])
            elif kind == "missing":
                report["boundaries"].pop()
            else:
                report["boundaries"][1]["transcript_unit_id"] = "UX"
            with self.subTest(kind=kind), self.assertRaises(AssertionError):
                precision(*rehash(document, report, reference, authority))

    def test_exact_200000us_passes_without_threshold_change(self):
        report, document, reference, authority = specimen((200_000,))
        result = precision(report, document, reference, authority)
        self.assertEqual(result["p95_error_us"], 200_000)
        self.assertEqual(result["sample_count"], 1)

    def test_200001us_fails(self):
        with self.assertRaises(AssertionError):
            precision(*specimen((200_001,)))

    def test_nearest_rank_p95_complete_twenty_units(self):
        result = precision(*specimen(tuple(range(10_000, 200_001, 10_000))))
        self.assertEqual(result["p95_error_us"], 190_000)
        self.assertEqual(result["sample_count"], 20)


if __name__ == "__main__":
    unittest.main()
