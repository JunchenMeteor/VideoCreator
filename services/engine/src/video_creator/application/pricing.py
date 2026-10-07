"""Versioned conservative CNY rules. Usage calculation is not a provider bill receipt."""

import json
from collections.abc import Mapping
from decimal import ROUND_CEILING, Decimal

from video_creator.domain.contracts import Money, OperationObservation
from video_creator.domain.errors import EngineError

DEEPSEEK_FLASH_RULE = "deepseek-flash-peak-20261007-v1"
MAX_REQUEST_BYTES = 65_536
MAX_OUTPUT_TOKENS = 8_192
KIMI_K26_RULE = "kimi-k2.6-cn-20261007-v1"
KIMI_CONTEXT_TOKENS = 262_144
KIMI_MAX_OUTPUT_TOKENS = 512
KIMI_MAX_REQUEST_BYTES = 20 * 1024 * 1024


def estimate_reserved(request_bytes: int, max_tokens: int,
                      rule_version: str = DEEPSEEK_FLASH_RULE) -> Money:
    _supported(rule_version)
    if rule_version == KIMI_K26_RULE:
        if not isinstance(request_bytes, int) or isinstance(request_bytes, bool) or not 0 < request_bytes <= KIMI_MAX_REQUEST_BYTES:
            raise EngineError("model_request_bound_exceeded", "Kimi validation payload exceeds the configured byte limit", 400)
        return estimate_kimi_reserved(max_tokens)
    if not isinstance(request_bytes, int) or not isinstance(max_tokens, int) or isinstance(request_bytes, bool) or isinstance(max_tokens, bool) or not 0 < request_bytes <= MAX_REQUEST_BYTES or not 0 < max_tokens <= MAX_OUTPUT_TOKENS:
        raise EngineError("model_request_bound_exceeded", "Validation request exceeds the configured byte or output-token bound", 400)
    # UTF-8 byte count is a conservative text-token bound; extra framing is covered separately.
    prompt_bound = request_bytes + 1024
    return _money(Decimal(prompt_bound) * 2 + Decimal(max_tokens) * 8)


def estimate_kimi_reserved(max_tokens: int = KIMI_MAX_OUTPUT_TOKENS) -> Money:
    """Reserve the entire context window; vision tokens are never estimated from base64 size."""
    if not isinstance(max_tokens, int) or isinstance(max_tokens, bool) or not 0 < max_tokens <= KIMI_MAX_OUTPUT_TOKENS:
        raise EngineError("model_request_bound_exceeded", "Kimi validation output must be bounded at 512 tokens", 400)
    return _money(Decimal(KIMI_CONTEXT_TOKENS) * Decimal("6.5") + Decimal(max_tokens) * 27)


def validate_kimi_request(payload: Mapping[str, object]) -> Money:
    """Validate the exact driver payload before dispatch; does not authorize tools or image/video generation."""
    if payload.get("model") != "kimi-k2.6":
        raise EngineError("model_denied", "This price rule only permits kimi-k2.6", 403)
    if payload.get("thinking") != {"type": "disabled"}:
        raise EngineError("thinking_mode_denied", "Validation requires explicit non-thinking mode", 403)
    if type(payload.get("n", 1)) is not int or payload.get("n", 1) != 1 or payload.get("stream", False) is not False:
        raise EngineError("generation_mode_denied", "Validation requires one non-streaming completion", 403)
    if payload.get("tools") or payload.get("tool_choice") not in (None, "none"):
        raise EngineError("tools_denied", "Additional Kimi tools are not authorized by this price rule", 403)
    size = len(json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))
    return estimate_reserved(size, payload.get("max_tokens"), KIMI_K26_RULE)


def calculate_usage_cost(usage: dict[str, int], rule_version: str = DEEPSEEK_FLASH_RULE) -> Money:
    _supported(rule_version)
    if not all(key in usage for key in ("prompt_tokens", "completion_tokens")):
        raise EngineError("usage_incomplete", "Provider usage is incomplete; cost remains unknown", 409, "reconcile")
    for value in usage.values():
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            raise EngineError("usage_invalid", "Provider usage is invalid; cost remains unknown", 409, "reconcile")
    total, output = usage["prompt_tokens"], usage["completion_tokens"]
    hits = usage.get("prompt_cache_hit_tokens", usage.get("cached_tokens", 0))
    misses = usage.get("prompt_cache_miss_tokens", total - hits)
    if hits > total or misses < 0 or hits + misses != total:
        raise EngineError("usage_invalid", "Cache usage does not match the input total", 409, "reconcile")
    if rule_version == KIMI_K26_RULE:
        if total > KIMI_CONTEXT_TOKENS or output > KIMI_MAX_OUTPUT_TOKENS:
            raise EngineError("usage_bound_exceeded", "Kimi usage exceeded the configured validation bound", 409, "reconcile")
        return _money(Decimal(hits) * Decimal("1.1") + Decimal(misses) * Decimal("6.5") + Decimal(output) * 27)
    # Peak-rate maximum intentionally covers off-peak price variation. This is an upper calculation.
    return _money(Decimal(hits) * Decimal("0.04") + Decimal(misses) * 2 + Decimal(output) * 8)


def normalize_observation(observation: OperationObservation, rule_version: str) -> OperationObservation:
    if rule_version not in {DEEPSEEK_FLASH_RULE, KIMI_K26_RULE}:
        return observation
    if observation.actual_cost is not None and observation.cost_evidence == "provider_receipt":
        raise EngineError("receipt_verifier_missing", "A provider bill receipt requires a verified receipt adapter", 409, "reconcile")
    if observation.status in {"succeeded", "failed"} and observation.usage:
        cost = calculate_usage_cost(observation.usage, rule_version)
        if observation.actual_cost is not None and observation.actual_cost != cost:
            raise EngineError("cost_calculation_conflict", "Driver cost does not match the controlled price rule", 409, "reconcile")
        return observation.model_copy(update={"actual_cost": cost, "cost_evidence": "usage_price_calculation"})
    if observation.status in {"succeeded", "failed"} and observation.actual_cost is not None:
        raise EngineError("cost_evidence_missing", "No verified usage or bill receipt supports the charge", 409, "reconcile")
    return observation


def _money(micro_units: Decimal) -> Money:
    return Money.from_units(int(micro_units.to_integral_value(rounding=ROUND_CEILING)))


def _supported(version: str):
    if version not in {DEEPSEEK_FLASH_RULE, KIMI_K26_RULE}:
        raise EngineError("price_rule_unavailable", "Price rule is not configured", 503)
