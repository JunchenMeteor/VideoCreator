"""Pure fixture checks only; no production, ASR, SQL, sockets or child process."""
from __future__ import annotations

import tempfile
import unittest
import os
from pathlib import Path

from t15_adversarial import asr_output_mutations, dangerous_zips
from t15_evidence import Journal, controlled_file, digest, strict_json
from t15_oracles import atomic_visible, expected_no_publication, interval, permissions, retrieval


class FixtureSanity(unittest.TestCase):
    def test_strict_json_rejects_duplicate_and_nonfinite(self):
        for raw in (b'{"a":1,"a":2}', b'{"x":NaN}', b'{"x":Infinity}',
                    b'{"x":-Infinity}', b'{"outer":{"a":1,"a":2}}'):
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                strict_json(raw)
        self.assertEqual(strict_json(b'{"a":[1,2]}'), {"a": [1, 2]})

    def test_bool_and_negative_time_not_accepted(self):
        for span in ({"start_us": False, "end_us": 3},
                     {"start_us": -1, "end_us": 3},
                     {"start_us": 1, "end_us": 4},
                     {"start_us": 1, "end_us": 1}):
            with self.subTest(span=span), self.assertRaises(AssertionError):
                interval(span, 3)
        self.assertEqual(interval({"start_us": 0, "end_us": 3}, 3), (0, 3))

    def test_exact_byte_reader_rejects_escape(self):
        with tempfile.TemporaryDirectory(prefix="T15Fixture-", dir=os.environ["T15_SANITY_DIR"]) as directory:
            root = Path(directory)
            (root / "Text").mkdir()
            (root / "Text/Marker.txt").write_bytes(b"own fixture")
            actual = controlled_file(root, "Text/Marker.txt")
            self.assertEqual(actual["sha256"], digest(b"own fixture"))
            for path in ("../Marker.txt", "/Marker.txt", "C:/Marker.txt",
                         "Text\\Marker.txt", "Text/../Marker.txt"):
                with self.subTest(path=path), self.assertRaises(AssertionError):
                    controlled_file(root, path)

    def test_journal_chain_is_original_byte_hash(self):
        with tempfile.TemporaryDirectory(prefix="T15Journal-", dir=os.environ["T15_SANITY_DIR"]) as directory:
            journal = Journal(Path(directory) / "Events")
            first = journal.record("fixture", {"not_product": True})
            second = journal.record("fixture", {"not_product": True})
            self.assertEqual(strict_json(second.read_bytes())["previous_sha256"],
                             digest(first.read_bytes()))

    def test_atomicity_rejects_half_success(self):
        keys = ("bundle_published", "delivery_step_succeeded", "run_succeeded",
                "production_succeeded", "bundle_ready_outbox", "production_success_outbox")
        before = dict.fromkeys(keys, False)
        atomic_visible(before)
        for key in keys:
            partial = before | {key: True}
            with self.subTest(key=key), self.assertRaises(AssertionError):
                atomic_visible(partial)
        full = dict.fromkeys(keys, True) | {
            "all_exact_files_persisted_and_hash_verified": True,
            "outbox_duplicates": 0, "fence_valid_at_commit": True,
            "cancelled_at_commit": False}
        atomic_visible(full)

    def test_no_publish_rejects_premature_bundle(self):
        before = {key: [] for key in ("visible_bundle_refs", "success_events",
                  "delivery_steps", "successful_runs", "successful_productions")}
        expected_no_publication(before, before.copy())
        with self.assertRaises(AssertionError):
            expected_no_publication(before, before | {"visible_bundle_refs": ["fake"]})

    def test_permission_rejects_304_and_data(self):
        denied = {"request_completed": True, "unauthorized": True, "status": 403,
                  "content_bytes": 0, "semantic_records": 0,
                  "principal_from_payload": False}
        permissions([denied])
        for change in ({"status": 304}, {"content_bytes": 1},
                       {"semantic_records": 1}, {"principal_from_payload": True}):
            with self.subTest(change=change), self.assertRaises(AssertionError):
                permissions([denied | change])

    def test_all_rejects_cannot_pass_retrieval(self):
        topics = [f"topic-{i}" for i in range(30)]
        candidates = [f"candidate-{i}" for i in range(60)]
        labels = {"topics": topics, "candidates": candidates,
                  "independently_human_reviewed": True,
                  "relevant_by_topic": {topic: [candidates[i]] for i, topic in enumerate(topics)}}
        with self.assertRaises(AssertionError):
            retrieval(labels, dict.fromkeys(topics, []))
        # Synthetic oracle sanity only, never a real MM05 labelled corpus.
        result = retrieval(labels, {topic: [candidates[i]] for i, topic in enumerate(topics)})
        self.assertEqual(result["precision"], 1)

    def test_mutations_and_small_archives_do_not_touch_product(self):
        original = {"origin_pts": 0, "language": "zh", "compute_type": "int8_float32",
                    "decoded_sample_count": 10, "duration_us": 500,
                    "video_audio_offset_us": 0}
        variants = asr_output_mutations(original)
        self.assertEqual(len(variants), 5)
        self.assertEqual(original["decoded_sample_count"], 10)
        self.assertTrue(all(item != original for item in variants.values()))
        archives = dangerous_zips()
        self.assertEqual(len(archives), 9)
        self.assertTrue(all(len(data) < 4096 for data in archives.values()))


if __name__ == "__main__":
    unittest.main()
