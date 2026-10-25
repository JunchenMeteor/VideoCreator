"""Future whole-module P01 consumer tests. Present status: NOT_EXECUTED."""

import unittest
from types import SimpleNamespace

from video_creator.domain.diagnostic_recovery import DiagnosticFeedbackCompletion, DiagnosticMaterialCompletion
from video_creator.domain.errors import EngineError
from video_creator.providers.component_diagnosis import _completion_text_body

from qualified_completion.fixtures import completions, material, revision


class MediaRepresentationTests(unittest.TestCase):
    def assert_error(self, code, value, raw):
        with self.assertRaises(EngineError) as caught:
            _completion_text_body(value, raw)
        self.assertEqual((caught.exception.code, caught.exception.status_code), (code, 422))

    def test_all_three_kinds_retain_complete_utf8_and_original_reference(self):
        text = "完整中文\n" * 12000 + "END-OF-ORIGINAL-BODY"
        raw = text.encode("utf-8")
        for value in completions(raw):
            with self.subTest(kind=value.kind):
                reference = value.ref
                before = value.model_dump(mode="json")
                self.assertEqual(_completion_text_body(value, raw), text)
                self.assertIs(value.ref, reference)
                self.assertEqual(value.model_dump(mode="json"), before)
                self.assertEqual(raw.decode("utf-8"), text)

    def test_qualified_resource_has_no_invented_media_type(self):
        raw = b'{"full":"body","tail":[1,2,3]}'
        value = completions(raw)[2]
        self.assertFalse(hasattr(value.ref, "media_type"))
        self.assertEqual(_completion_text_body(value, raw), raw.decode("utf-8"))

    def test_ready_material_text_and_json_are_exact_text(self):
        raw = "{\"中文\":\"完整\"}\n".encode("utf-8")
        for mime in ("text/plain", "text/srt", "text/vtt", "application/json"):
            with self.subTest(mime=mime):
                value = DiagnosticMaterialCompletion(kind="ready_material", ref=material(raw, mime))
                self.assertEqual(_completion_text_body(value, raw), raw.decode("utf-8"))

    def test_nontext_ready_material_preserves_binary_upload_boundary(self):
        raw = b"\x00\xff\x80WHOLE-BINARY-TAIL"
        for mime in ("image/png", "video/mp4", "audio/wav", "application/octet-stream", "application/x-ndjson"):
            with self.subTest(mime=mime):
                value = DiagnosticMaterialCompletion(kind="ready_material", ref=material(raw, mime))
                self.assertIsNone(_completion_text_body(value, raw))
                self.assertEqual(raw, b"\x00\xff\x80WHOLE-BINARY-TAIL")

    def test_invalid_utf8_rejected_for_each_textual_kind(self):
        raw = b"valid-prefix\xffhidden-tail"
        for value in completions(raw):
            with self.subTest(kind=value.kind):
                self.assert_error("diagnostic_completion_encoding_invalid", value, raw)

    def test_unknown_kind_does_not_infer_mime(self):
        raw = b"original"
        for value in completions(raw):
            with self.subTest(kind=value.kind):
                self.assert_error("diagnostic_completion_invalid", value.model_copy(update={"kind": "other"}), raw)

    def test_foreign_completion_with_same_fields_rejected(self):
        value = SimpleNamespace(kind="feedback", ref=revision())
        self.assert_error("diagnostic_completion_invalid", value, b"body")

    def test_ready_material_cannot_use_duck_typed_receipt(self):
        original = DiagnosticMaterialCompletion(kind="ready_material", ref=material(b"body"))
        forged = original.model_copy(update={"ref": SimpleNamespace(media_type="text/plain")})
        self.assert_error("diagnostic_completion_invalid", forged, b"body")

    def test_completion_subclass_is_not_original_type(self):
        class ForeignFeedback(DiagnosticFeedbackCompletion):
            pass
        foreign = ForeignFeedback(kind="feedback", ref=revision())
        self.assert_error("diagnostic_completion_invalid", foreign, b"body")
