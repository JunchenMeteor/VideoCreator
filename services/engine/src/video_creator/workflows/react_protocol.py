"""Separate model-authored control from complete JSON payload data."""

import json
import re

from video_creator.domain.errors import EngineError

_CONTROL = re.compile(
    r"(?<!\w)(?P<kind>Action(?:\s+\d+)?\s*Input(?:\s+\d+)?"
    r"|Action(?:\s+\d+)?|Observation(?:\s+\d+)?|Final Answer)\s*:"
)


def _json_region(content: str) -> tuple[int, object] | None:
    # Only complete JSON documents are data. Quoted prose in the Thought prefix
    # cannot hide forged controls, and trailing controls invalidate JSON payloads.
    try:
        return 0, json.loads(content)
    except ValueError:
        pass
    for marker in _CONTROL.finditer(content):
        kind = marker.group("kind")
        if "Input" not in kind and kind != "Final Answer":
            continue
        try:
            return marker.end(), json.loads(content[marker.end() :])
        except ValueError:
            continue
    return None


def _controls(content: str):
    region = _json_region(content)
    prefix = content[: region[0]] if region is not None else content
    return list(_CONTROL.finditer(prefix)), region


def validate_react_turn(content: str) -> str:
    markers, region = _controls(content)
    actions = [
        m
        for m in markers
        if m.group("kind").startswith("Action") and "Input" not in m.group("kind")
    ]
    inputs = [m for m in markers if "Input" in m.group("kind")]
    finals = [m for m in markers if m.group("kind") == "Final Answer"]
    observations = [m for m in markers if m.group("kind").startswith("Observation")]
    if observations or len(actions) > 1 or len(finals) > 1 or (actions and finals):
        raise EngineError(
            "model_react_protocol_invalid",
            "Return one Action and Action Input, or a Final Answer. Tool Observations must come from execution.",
            422,
        )
    if actions:
        if (
            len(inputs) != 1
            or actions[0].start() >= inputs[0].start()
            or not content[actions[0].end() : inputs[0].start()].strip()
            or region is None
            or region[0] != inputs[0].end()
            or not isinstance(region[1], dict)
        ):
            raise EngineError(
                "model_react_protocol_invalid",
                "One tool action requires exactly one JSON object input.",
                422,
            )
    elif inputs:
        raise EngineError(
            "model_react_protocol_invalid", "Tool input is missing its action.", 422
        )
    return content


def final_response_content(content: str) -> str:
    """Extract actual final content, never a marker inside JSON string data."""
    validate_react_turn(content)
    markers, _ = _controls(content)
    if any(m.group("kind").startswith("Action") for m in markers):
        raise ValueError("model response is a tool action, not a final result")
    final = next((m for m in markers if m.group("kind") == "Final Answer"), None)
    return content[final.end() :].strip() if final is not None else content.strip()


def crewai_safe_turn(content: str) -> str:
    """Escape data literals that the locked CrewAI parser scans as controls.

    JSON unicode escapes retain the data's exact decoded value. The original
    response remains in the Operation ledger and is used for source auditing.
    """
    validate_react_turn(content)
    region = _json_region(content)
    if region is None:
        return content
    start, value = region
    encoded = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    encoded = encoded.replace("Final Answer:", "Final Answer\\u003a")
    # A complete bare JSON document is a final result, not an implicit tool
    # instruction. Give the locked parser its explicit final control wrapper.
    prefix = "Final Answer: " if start == 0 else content[:start]
    return prefix + encoded
