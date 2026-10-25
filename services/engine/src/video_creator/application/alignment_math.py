"""One exact whole-unit criterion, shared by old strict and versioned evidence."""

from video_creator.domain.contracts import (
    AlignmentUnit,
    PrecisionBoundaryPair,
    PrecisionReferenceUnit,
)
from video_creator.domain.errors import EngineError

CRITERION = "alignment-unit-max-p95-200ms-v1"
LIMIT_US = 200_000


def unit_errors(predicted: tuple[AlignmentUnit, ...], reference: tuple[PrecisionReferenceUnit, ...],
                comparisons: tuple[PrecisionBoundaryPair, ...], duration_us: int) -> list[int]:
    # Validate original complete arrays BEFORE indexing; duplicates never fold.
    arrays = (predicted, reference, comparisons)
    identities = []
    for values in arrays:
        ids = [item.transcript_unit_id for item in values]
        if not ids or len(ids) != len(set(ids)):
            raise EngineError("precision_evidence_invalid", "Complete precision units must be nonempty and distinct", 422)
        identities.append(set(ids))
    if not identities[0] == identities[1] == identities[2]:
        raise EngineError("precision_evidence_invalid", "Alignment, reference and report must match every original unit", 422)
    if len({item.unit_id for item in predicted}) != len(predicted):
        raise EngineError("precision_evidence_invalid", "Alignment unit identities are distinct", 422)
    for item in predicted:
        if item.intrinsic_range.end_us > duration_us:
            raise EngineError("precision_evidence_invalid", "Predicted unit exceeds actual audio", 422)
    for item in reference:
        if item.reference_range.end_us > duration_us:
            raise EngineError("precision_evidence_invalid", "Reference unit exceeds actual audio", 422)
    predictions = {item.transcript_unit_id: item.intrinsic_range for item in predicted}
    references = {item.transcript_unit_id: item.reference_range for item in reference}
    errors = []
    for item in comparisons:
        if item.predicted_range != predictions[item.transcript_unit_id] or item.reference_range != references[item.transcript_unit_id]:
            raise EngineError("precision_evidence_invalid", "Report changed an original predicted or reference boundary", 422)
        errors.append(max(abs(item.predicted_range.start_us - item.reference_range.start_us),
                          abs(item.predicted_range.end_us - item.reference_range.end_us)))
    return errors


def nearest_rank(errors: list[int]) -> tuple[int, int]:
    if not errors or any(type(value) is not int or value < 0 for value in errors):
        raise EngineError("precision_evidence_invalid", "An exact nonempty whole-unit measurement is required", 422)
    count = len(errors)
    rank = (95 * count + 99) // 100
    return count, sorted(errors)[rank - 1]
