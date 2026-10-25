"""Future full DTO and original local predicate tests; fixtures confer no rights."""

import unittest
from pydantic import TypeAdapter, ValidationError

from video_creator.application.component_diagnosis_service import ComponentDiagnosisService
from video_creator.domain import component_diagnosis as d
from video_creator.domain import diagnostic_recovery as r
from video_creator.domain.affected_recipe import RecipeSourceRef
from video_creator.domain import contracts as c
from video_creator.domain.errors import EngineError

from qualified_completion.fixtures import check, completions, material, metadata, observation, predicate_inputs, revision, source_media


class StrictReferenceTests(unittest.TestCase):
    def setUp(self):
        self.service = ComponentDiagnosisService()

    def predicate(self, inputs, checks):
        return self.service._diagnostic_check_refs(inputs, observation(checks), ())

    def assert_refusal(self, inputs, checks):
        with self.assertRaises(EngineError) as caught:
            self.predicate(inputs, checks)
        self.assertEqual((caught.exception.code, caught.exception.status_code), ("diagnostic_source_invalid", 422))

    def test_metadata_reexport_is_sole_original_class(self):
        self.assertIs(r.DiagnosticMetadataRef, d.DiagnosticMetadataRef)
        self.assertIs(r.RegisteredDiagnosticInputRef.__mro__[1], d.DiagnosticMetadataRef)
        self.assertIsInstance(r.DiagnosticResourceCompletion(kind="qualified_resource", ref=metadata()).ref,
            d.DiagnosticMetadataRef)

    def test_union_retains_all_five_prior_members_and_adds_metadata(self):
        prior = (
            revision(), material(b"literal"), source_media(),
            d.DiagnosticOperationOutputRefV1(format="component-diagnostic-operation-output-v1",
                operation_id="fixture.operation", input_sha256="a" * 64, observation_sha256="b" * 64,
                output_sha256="c" * 64),
            d.DiagnosticSampleRefV1(format="component-diagnostic-decoded-sample-v1", asset_id="fixture.asset",
                source_sha256="b" * 64, source_range=c.MediaRange(start_us=0, end_us=10), sample_sha256="c" * 64,
                sample_size=3, decoder_ref=RecipeSourceRef(resource_name="Fixture/Decoder.py", sha256="d" * 64)),
        )
        adapter = TypeAdapter(d.DiagnosticEvidenceRef)
        for value in prior + (metadata(),):
            with self.subTest(type=type(value).__name__):
                roundtrip = adapter.validate_json(value.model_dump_json())
                self.assertIs(type(roundtrip), type(value))
                self.assertEqual(roundtrip, value)

    def test_strict_metadata_rejects_extra_mime_and_bad_hash_size(self):
        base = metadata().model_dump()
        for patch in ({"media_type": "text/plain"}, {"size": True}, {"size": "2"}, {"size": 0},
                      {"size": 2 * 1024 * 1024 + 1}, {"content_sha256": "A" * 64}, {"record_id": ""}):
            with self.subTest(patch=patch), self.assertRaises(ValidationError):
                d.DiagnosticMetadataRef.model_validate({**base, **patch})

    def test_literal_qualified_membership_passes_only_local_predicate(self):
        value = completions()[2]
        self.assertIsNone(self.predicate(predicate_inputs((value,)), (check((value.ref,)),)))

    def test_equal_serialized_qualified_reference_remains_exact_value(self):
        value = completions()[2]
        copied = d.DiagnosticMetadataRef.model_validate_json(value.ref.model_dump_json())
        self.assertIsNot(copied, value.ref)
        self.assertIsNone(self.predicate(predicate_inputs((value,)), (check((copied,)),)))

    def test_undeclared_qualified_reference_rejected(self):
        self.assert_refusal(predicate_inputs(), (check((metadata(),)),))

    def test_different_record_hash_or_size_rejected_individually(self):
        value = completions()[2]
        for patch in ({"record_id": "fixture.other"}, {"content_sha256": "9" * 64}, {"size": value.ref.size + 1}):
            with self.subTest(patch=patch):
                altered = d.DiagnosticMetadataRef.model_validate({**value.ref.model_dump(), **patch})
                self.assert_refusal(predicate_inputs((value,)), (check((altered,)),))

    def test_equal_metadata_under_wrong_completion_kind_rejected(self):
        value = completions()[2]
        wrong = value.model_copy(update={"kind": "feedback"})
        self.assert_refusal(predicate_inputs((wrong,)), (check((value.ref,)),))

    def test_each_original_completion_must_be_consumed(self):
        values = completions()
        for omitted in range(len(values)):
            with self.subTest(omitted=values[omitted].kind):
                used = tuple(value.ref for index, value in enumerate(values) if index != omitted)
                self.assert_refusal(predicate_inputs(values), (check(used),))

    def test_all_three_consumed_sources_keep_original_refs(self):
        values = completions()
        self.assertIsNone(self.predicate(predicate_inputs(values), (check(tuple(v.ref for v in values)),)))

    def test_metadata_cannot_replace_actual_component_media(self):
        value = completions()[2]
        typed = check((value.ref,)).model_copy(update={"source_refs": (value.ref,),
            "expected_ref": value.ref, "observed_ref": value.ref})
        self.assert_refusal(predicate_inputs((value,)), (typed,))

    def test_undeclared_ready_receipt_or_feedback_rejected(self):
        values = completions()
        for value in values[:2]:
            with self.subTest(kind=value.kind):
                self.assert_refusal(predicate_inputs(), (check((value.ref,)),))

    def test_unavailable_cannot_claim_supported_even_with_typed_ref(self):
        data = check((metadata(),)).model_dump()
        with self.assertRaises(ValidationError):
            d.ComponentDiagnosticCheckV1.model_validate({**data, "observed_result": "unavailable"})
