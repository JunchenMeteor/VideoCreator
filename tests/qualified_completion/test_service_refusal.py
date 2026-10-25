"""Original service denial and damaged-record tests, not authenticated positives."""

import sqlite3
import threading
import unittest
from types import SimpleNamespace

from video_creator.application.component_diagnosis_service import ComponentDiagnosisService
from video_creator.application.diagnostic_selection import DiagnosticSelectionService
from video_creator.application.diagnostic_resume import DiagnosticResumeRuntime
from video_creator.domain.component_diagnosis import ComponentDiagnosisRefV1
from video_creator.domain.errors import EngineError

from qualified_completion.fixtures import check, completions, observation, predicate_inputs, sha


class DenialOnlyService(ComponentDiagnosisService, DiagnosticSelectionService):
    """Original methods, no overrides; only EMPTY custody maps are installed."""


class ServiceRefusalTests(unittest.TestCase):
    def setUp(self):
        self.service = DenialOnlyService()
        self.service._lock = threading.RLock()
        self.service._final_evidence_ports = {}
        self.inputs = predicate_inputs(completions())
        self.lease = SimpleNamespace(run_id="fixture.run", fencing_token=1)

    def assert_error(self, code, status, call):
        with self.assertRaises(EngineError) as caught:
            call()
        self.assertEqual((caught.exception.code, caught.exception.status_code), (code, status))

    def test_normal_record_refuses_unheld_input_before_any_database(self):
        actual = observation((check(tuple(v.ref for v in completions())),))
        self.assert_error("diagnostic_source_denied", 403,
            lambda: self.service.record_component_diagnosis(self.lease, self.inputs, actual))
        self.assertFalse(hasattr(self.service, "engine"))

    def test_append_record_refuses_same_unheld_input(self):
        actual = observation((check(tuple(v.ref for v in completions())),))
        self.assert_error("diagnostic_source_denied", 403,
            lambda: self.service.append_component_diagnosis(self.lease, self.inputs, actual))

    def test_completion_reader_does_not_mint_custody_from_typed_ref(self):
        self.assert_error("diagnostic_source_denied", 403,
            lambda: self.service.read_diagnostic_completion(self.lease, self.inputs, completions()[2]))

    def test_explicit_current_reader_rejects_foreign_continuation_before_issuer(self):
        self.assert_error("final_evidence_claim_required", 409,
            lambda: self.service.read_component_diagnosis(self.lease, SimpleNamespace()))
        self.assertFalse(hasattr(self.service, "_production_authorization"))

    def test_wrong_observation_type_does_not_enter_custody_or_database(self):
        self.assert_error("diagnostic_source_invalid", 422,
            lambda: self.service.record_component_diagnosis(self.lease, self.inputs, SimpleNamespace()))

    def test_no_lease_qualified_observer_remains_not_ready(self):
        # Original explicit 503 boundary. No issuer/observer callback is added.
        runtime = DiagnosticResumeRuntime()
        self.assert_error("diagnostic_resource_observer_not_ready", 503,
            lambda: runtime._diagnostic_completion_bytes_no_lease(completions()[2], {}, {}))

    def test_missing_immutable_record_is_unavailable(self):
        with sqlite3.connect(":memory:") as connection:
            connection.execute("CREATE TABLE metadata(key TEXT PRIMARY KEY,value TEXT NOT NULL)")
            ref = ComponentDiagnosisRefV1(format="current-component-diagnosis-ref-v1", record_id="fixture.missing",
                content_sha256="a" * 64, size=2, input_key_sha256="1" * 64)
            self.assert_error("diagnostic_record_unavailable", 503,
                lambda: self.service._read_diagnosis_ref_writer(connection, self.lease, ref, self.inputs))

    def test_wrong_record_hash_or_size_is_rejected_before_fact_use(self):
        raw = '{"not":"an authorized diagnostic fact"}'
        with sqlite3.connect(":memory:") as connection:
            # This table contains ONLY a malformed fault row, never an approval.
            connection.execute("CREATE TABLE metadata(key TEXT PRIMARY KEY,value TEXT NOT NULL)")
            connection.execute("INSERT INTO metadata(key,value) VALUES(?,?)", ("fixture.corrupt", raw))
            for digest, size in (("a" * 64, len(raw.encode())), (sha(raw.encode()), len(raw.encode()) + 1)):
                with self.subTest(digest=digest, size=size):
                    ref = ComponentDiagnosisRefV1(format="current-component-diagnosis-ref-v1", record_id="fixture.corrupt",
                        content_sha256=digest, size=size, input_key_sha256="1" * 64)
                    self.assert_error("diagnostic_source_invalid", 422,
                        lambda: self.service._read_diagnosis_ref_writer(connection, self.lease, ref, self.inputs))

    def test_matching_hash_does_not_validate_a_damaged_fact(self):
        raw = '{"not":"an authorized diagnostic fact"}'
        with sqlite3.connect(":memory:") as connection:
            connection.execute("CREATE TABLE metadata(key TEXT PRIMARY KEY,value TEXT NOT NULL)")
            connection.execute("INSERT INTO metadata(key,value) VALUES(?,?)", ("fixture.corrupt", raw))
            ref = ComponentDiagnosisRefV1(format="current-component-diagnosis-ref-v1", record_id="fixture.corrupt",
                content_sha256=sha(raw.encode()), size=len(raw.encode()), input_key_sha256="1" * 64)
            self.assert_error("diagnostic_source_invalid", 422,
                lambda: self.service._read_diagnosis_ref_writer(connection, self.lease, ref, self.inputs))
