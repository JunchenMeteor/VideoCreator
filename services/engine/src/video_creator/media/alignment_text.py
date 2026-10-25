"""Auditable NFC/CTC character mapping; no phonetic guesses or time estimates."""
from __future__ import annotations

import unicodedata


def character_map(text, vocabulary):
    """Retain original scalar spans while mapping only observed vocabulary.

    Punctuation and whitespace do not acquire invented speech intervals. NFC
    combining clusters and lowercase expansion retain their original span.
    Unknown spoken characters reject the input instead of being interpolated.
    """
    if type(text) is not str or not 0 < len(text) <= 500_000:
        raise ValueError("alignment_text_invalid")
    if (type(vocabulary) is not dict or not vocabulary
            or any(type(key) is not str or type(value) is not int or value < 0
                   for key, value in vocabulary.items())):
        raise ValueError("alignment_vocabulary_invalid")
    result, ignored = [], []
    start = 0
    while start < len(text):
        end = start + 1
        while end < len(text) and unicodedata.combining(text[end]):
            end += 1
        original = text[start:end]
        normalized = unicodedata.normalize("NFC", original).lower()
        if all(unicodedata.category(value)[0] in {"P", "Z"} or value.isspace() for value in normalized):
            ignored.append({"start": start, "end": end, "text": original, "reason": "unvoiced_punctuation_or_space"})
        else:
            for value in normalized:
                if value not in vocabulary:
                    raise ValueError("alignment_character_out_of_vocabulary")
                result.append({"character": value, "token": vocabulary[value], "start": start, "end": end})
        start = end
    if not result:
        raise ValueError("alignment_text_without_spoken_characters")
    return {"text": text, "characters": result, "ignored": ignored,
            "normalization": "nfc-lower-cluster-original-scalar-span-v1"}


def map_units(utterance, units, vocabulary):
    """Match original ordered unit texts to exact acoustic characters.

    Chinese words come from their original unit IDs and text, never an English
    space tokenizer. Normalized acoustic characters must cover the utterance
    exactly; reordered, missing or silently substituted text is rejected.
    """
    mapped = character_map(utterance, vocabulary)
    if type(units) not in {list, tuple} or not units:
        raise ValueError("alignment_units_invalid")
    identities, spans, offset = set(), [], 0
    whole = "".join(value["character"] for value in mapped["characters"])
    for unit in units:
        if type(unit) is not dict or set(unit) != {"unit_id", "text"}:
            raise ValueError("alignment_units_invalid")
        identity = unit["unit_id"]
        if type(identity) is not str or not identity or identity in identities:
            raise ValueError("alignment_units_invalid")
        identities.add(identity)
        mapped_unit = character_map(unit["text"], vocabulary)
        content = "".join(value["character"] for value in mapped_unit["characters"])
        end = offset + len(content)
        if whole[offset:end] != content:
            raise ValueError("alignment_unit_text_mismatch")
        spans.append({"unit_id": identity, "text": unit["text"], "character_start": offset,
                      "character_end": end, "character_mapping": mapped_unit})
        offset = end
    if offset != len(whole):
        raise ValueError("alignment_units_incomplete")
    return {**mapped, "units": spans}


def aggregate_units(mapped, observed_characters, duration_us):
    """Aggregate only actual complete character boundaries, preserving unit IDs."""
    if type(duration_us) is not int or not 0 < duration_us <= 600_000_000:
        raise ValueError("alignment_duration_invalid")
    if type(observed_characters) not in {list, tuple} or len(observed_characters) != len(mapped["characters"]):
        raise ValueError("alignment_character_coverage_incomplete")
    previous = 0
    for index, value in enumerate(observed_characters):
        if (type(value) is not dict or set(value) != {"character", "start_us", "end_us"}
                or value["character"] != mapped["characters"][index]["character"]
                or type(value["start_us"]) is not int or type(value["end_us"]) is not int
                or not previous <= value["start_us"] < value["end_us"] <= duration_us):
            raise ValueError("alignment_character_boundary_invalid")
        previous = value["end_us"]
    return [{"unit_id": value["unit_id"], "text": value["text"],
             "start_us": observed_characters[value["character_start"]]["start_us"],
             "end_us": observed_characters[value["character_end"] - 1]["end_us"]}
            for value in mapped["units"]]
