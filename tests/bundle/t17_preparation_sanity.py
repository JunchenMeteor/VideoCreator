"""Own bounded guard/loader sentinel and reference predicates, no producer."""
import copy
import hashlib
import json
import os
import tempfile
import unittest
from pathlib import Path

from t16_guard import NotReadyForExecution, file_hash, identity_then_loader
from t17_reference_assertions import reference_dispatch, reference_hash_layers, reference_units


class PreparationSanity(unittest.TestCase):
    def fixture(self, root):
        source_root = root / "Sources"
        source_root.mkdir()
        source = source_root / "OwnGuard.py"
        source.write_bytes(b"VALUE = 1\n")  # File identity only, never imported.
        body = root / "OriginalBody.py"
        body.write_bytes(source.read_bytes())
        resource = root / "OwnResource.bin"
        resource.write_bytes(b"bounded own resource marker")
        sources = {str(source.resolve()): file_hash(source)}
        resources = {str(resource.resolve()): file_hash(resource)}
        binding = {"source_root": str(source_root), "target_module": "OwnGuard",
                   "target_path": str(source.resolve()), "required_sources": sources,
                   "required_resources": resources,
                   "module_chain": [{"module": "OwnGuard", "path": str(source.resolve())}]}
        admission = {"production_and_test_sources": copy.deepcopy(sources),
                     "runtime_resources": copy.deepcopy(resources)}
        records = [{"source_path": str(source.resolve()), "body_copy": str(body.resolve())}]
        return binding, admission, records

    def denied(self, change):
        with tempfile.TemporaryDirectory(prefix="T17Guard-", dir=os.environ["T17_SANITY_DIR"]) as directory:
            binding, admission, bodies = self.fixture(Path(directory))
            change(binding, admission, bodies)
            entries = []
            def sentinel(checked):
                entries.append("loader entered")
            with self.assertRaises(NotReadyForExecution):
                identity_then_loader(binding, admission, bodies, sentinel)
            self.assertEqual(entries, [], "loader must not execute on rejection")

    def test_empty_or_missing_target_source_denied_before_loader(self):
        self.denied(lambda b, a, r: b.update(required_sources={}))
        self.denied(lambda b, a, r: a.update(production_and_test_sources={}))
        self.denied(lambda b, a, r: b.update(target_path=str(Path(b["source_root"]) / "Other.py")))

    def test_empty_or_missing_resources_denied_before_loader(self):
        self.denied(lambda b, a, r: b.update(required_resources={}))
        self.denied(lambda b, a, r: a.update(runtime_resources={}))
        def missing(b, a, r):
            Path(next(iter(b["required_resources"]))).unlink()
        self.denied(missing)

    def test_wrong_target_module_chain_denied_before_loader(self):
        self.denied(lambda b, a, r: b["module_chain"][0].update(path=str(Path(b["source_root"]) / "Else.py")))

    def test_bad_source_or_resource_hash_denied_before_loader(self):
        def source_drift(b, a, r):
            Path(b["target_path"]).write_bytes(b"changed own source\n")
        self.denied(source_drift)
        def resource_drift(b, a, r):
            Path(next(iter(b["required_resources"]))).write_bytes(b"changed marker")
        self.denied(resource_drift)

    def test_missing_bad_or_duplicate_bodies_denied_before_loader(self):
        self.denied(lambda b, a, r: r.clear())
        def missing_body(b, a, r):
            Path(r[0]["body_copy"]).unlink()
        self.denied(missing_body)
        def bad_body(b, a, r):
            Path(r[0]["body_copy"]).write_bytes(b"wrong body\n")
        self.denied(bad_body)
        self.denied(lambda b, a, r: r.append(copy.deepcopy(r[0])))

    def test_valid_own_identity_only_enters_sentinel_once(self):
        with tempfile.TemporaryDirectory(prefix="T17Guard-", dir=os.environ["T17_SANITY_DIR"]) as directory:
            binding, admission, records = self.fixture(Path(directory))
            entries = []
            result = identity_then_loader(binding, admission, records,
                                          lambda value: entries.append("own sentinel"))
            self.assertEqual(entries, ["own sentinel"])
            self.assertIsNone(result)  # No fake service returned; no actual module load.

    def test_reference_report_grammar_is_not_union(self):
        reference_dispatch("0.3.0-candidate", "precision_reference", "precision_reference_v03")
        for values in (("0.2.0-candidate", "precision_reference", "precision_reference_v03"),
                       ("0.3.0-candidate", "precision_reference", "precision_report_v03"),
                       ("0.3.0-candidate", "precision_report", "precision_reference_v03")):
            with self.subTest(values=values), self.assertRaises(AssertionError):
                reference_dispatch(*values)

    def test_reference_population_keeps_full_transcript(self):
        entries = [("U0", 0, 1_000_000), ("U1", 2_000_000, 3_000_000)]
        reference_units(["U0", "U1"], entries, ["U0", "U1"], 4_000_000)
        for bad in (entries[:1], [entries[0], entries[0]],
                    [entries[0], ("UX", 2_000_000, 3_000_000)],
                    [("U0", False, 1_000_000), entries[1]]):
            with self.subTest(bad=bad), self.assertRaises(AssertionError):
                reference_units(["U0", "U1"], bad, ["U0", "U1"], 4_000_000)
        for bad_ids in ([["U0"], "U1"], [True, "U1"], ["U0", "U0"], []):
            with self.subTest(bad_ids=bad_ids), self.assertRaises(AssertionError):
                reference_units(bad_ids, entries, ["U0", "U1"], 4_000_000)

    def test_signature_input_internal_record_and_file_hash_are_distinct(self):
        document = {"units": ["U0"], "input_audio_sha256": "a" * 64,
                    "issuer": "synthetic-no-authority",
                    "signature": {"algorithm": "HMAC-SHA256",
                                  "key_id": "public-test-id", "digest": "b" * 64}}
        raw_signed = json.dumps(document, sort_keys=True, ensure_ascii=False,
                                separators=(",", ":")).encode()
        document["content_sha256"] = hashlib.sha256(raw_signed).hexdigest()
        raw = (json.dumps(document, sort_keys=True, ensure_ascii=False, indent=2) + "\n").encode()
        sha = hashlib.sha256(raw).hexdigest()
        facts = reference_hash_layers(document, raw, sha)
        self.assertNotEqual(facts["internal_content_sha256"], facts["complete_file_sha256"])
        self.assertNotIn(b"signature", facts["signature_input_bytes"])
        self.assertIn(b"units", facts["signature_input_bytes"])
        self.assertFalse(facts["HMAC_or_issuer_trust_verified"])
        with self.assertRaises(AssertionError):
            reference_hash_layers(document, raw, document["content_sha256"])
