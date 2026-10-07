"""Bounded CN Open Platform multimodal-to-text driver.

Only backend-admitted chat completions. Kimi Coding, other regions, tools,
media generation, URL fetching, retries and implicit mode changes are absent.
"""

from __future__ import annotations

import base64
import binascii
import json
import re

import httpx

from video_creator.application.pricing import KIMI_K26_RULE, validate_kimi_request
from video_creator.domain.contracts import ExecutionPermit, OperationObservation
from video_creator.domain.errors import EngineError
from video_creator.infrastructure.credentials import SecretHandle

KIMI_ENDPOINT = "https://api.moonshot.cn/v1/chat/completions"
KIMI_MODEL = "kimi-k2.6"
_DATA_MEDIA = re.compile(
    r"^data:(image/(?:png|jpeg|webp)|video/mp4);base64,([A-Za-z0-9+/=]+)$"
)
_ALLOWED_ERROR_TYPES = {
    "invalid_authentication_error",
    "authentication_error",
    "invalid_api_key",
    "invalid_request_error",
    "permission_denied",
    "rate_limit_error",
    "insufficient_quota",
    "insufficient_balance",
    "model_not_found",
}


def kimi_payload(messages: list[dict], *, max_tokens: int = 512) -> dict:
    if not messages or len(messages) > 32:
        raise EngineError("kimi_input_denied", "Invalid message count.", 422)
    for message in messages:
        if set(message) != {"role", "content"} or message["role"] not in {
            "system",
            "user",
            "assistant",
        }:
            raise EngineError(
                "kimi_input_denied", "Only bounded chat messages are supported.", 422
            )
        content = message["content"]
        if isinstance(content, str):
            continue
        if (
            not isinstance(content, list)
            or message["role"] != "user"
            or not 1 <= len(content) <= 4
        ):
            raise EngineError("kimi_input_denied", "Invalid multimodal content.", 422)
        for part in content:
            kind = part.get("type") if isinstance(part, dict) else None
            if (
                kind == "text"
                and set(part) == {"type", "text"}
                and isinstance(part["text"], str)
            ):
                continue
            if kind not in {"image_url", "video_url"} or set(part) != {"type", kind}:
                raise EngineError(
                    "kimi_input_denied",
                    "Only text and controlled inline media are supported.",
                    422,
                )
            media = part[kind]
            match = (
                _DATA_MEDIA.fullmatch(media.get("url", ""))
                if isinstance(media, dict) and set(media) == {"url"}
                else None
            )
            if match is None or (kind == "video_url") != match.group(1).startswith(
                "video/"
            ):
                raise EngineError(
                    "kimi_media_denied",
                    "Media must be an allowed inline data URL.",
                    422,
                )
            try:
                decoded = base64.b64decode(match.group(2), validate=True)
            except (ValueError, binascii.Error):
                raise EngineError(
                    "kimi_media_denied", "Inline media is malformed.", 422
                ) from None
            if not decoded:
                raise EngineError("kimi_media_denied", "Inline media is empty.", 422)
    payload = {
        "model": KIMI_MODEL,
        "messages": messages,
        "thinking": {"type": "disabled"},
        "stream": False,
        "n": 1,
        "max_tokens": max_tokens,
    }
    validate_kimi_request(payload)
    return json.loads(json.dumps(payload, ensure_ascii=False))


class KimiChatDriver:
    def __init__(self, payload: dict):
        validate_kimi_request(payload)
        # Snapshot once; caller mutation cannot change the admitted request.
        self._wire = json.dumps(
            payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")

    @property
    def request_payload(self) -> dict:
        return json.loads(self._wire)

    def __call__(
        self, permit: ExecutionPermit, secret: SecretHandle | None
    ) -> OperationObservation:
        if (
            secret is None
            or permit.route.destination != KIMI_ENDPOINT
            or permit.route.capability != "text"
            or permit.route.cost_rule_version != KIMI_K26_RULE
        ):
            raise EngineError(
                "kimi_route_denied",
                "The admitted platform, output capability or price rule is unavailable.",
                403,
            )
        try:
            transport = httpx.HTTPTransport(retries=0)
            with (
                httpx.Client(
                    transport=transport,
                    timeout=httpx.Timeout(120, connect=15),
                    trust_env=False,
                    follow_redirects=False,
                ) as client,
                client.stream(
                    "POST",
                    KIMI_ENDPOINT,
                    content=self._wire,
                    headers={
                        "Authorization": "Bearer " + secret.reveal(),
                        "Content-Type": "application/json",
                        "User-Agent": "VideoCreator/0.1 (Gate0 validation; httpx/0.28.1)",
                    },
                ) as response,
            ):
                chunks, size = [], 0
                for chunk in response.iter_bytes():
                    size += len(chunk)
                    if size > 2 * 1024 * 1024:
                        return OperationObservation(
                            status="unknown",
                            result_json={"error_code": "kimi_response_too_large"},
                        )
                    chunks.append(chunk)
                body = json.loads(b"".join(chunks))
                if response.status_code != 200:
                    raw_kind = (
                        body.get("error", {}).get("type")
                        if isinstance(body, dict)
                        and isinstance(body.get("error"), dict)
                        else None
                    )
                    return OperationObservation(
                        status="unknown",
                        result_json={
                            "error_code": "kimi_upstream_http_status",
                            "http_status": response.status_code,
                            "upstream_error_type": raw_kind
                            if raw_kind in _ALLOWED_ERROR_TYPES
                            else "unclassified",
                        },
                    )
        except (httpx.HTTPError, OSError, ValueError):
            return OperationObservation(
                status="unknown", result_json={"error_code": "kimi_transport_uncertain"}
            )
        usage = {}
        external_id = (
            body.get("id")
            if isinstance(body, dict) and isinstance(body.get("id"), str)
            else None
        )
        try:
            raw_usage = body["usage"]
            for name in (
                "prompt_tokens",
                "completion_tokens",
                "total_tokens",
                "prompt_cache_hit_tokens",
                "prompt_cache_miss_tokens",
            ):
                if name in raw_usage:
                    value = raw_usage[name]
                    if type(value) is not int or value < 0:
                        raise ValueError("invalid usage")
                    usage[name] = value
            details = raw_usage.get("prompt_tokens_details") or {}
            if isinstance(details, dict) and "cached_tokens" in details:
                cached = details["cached_tokens"]
                if type(cached) is not int or cached < 0:
                    raise ValueError("invalid cached usage")
                usage["cached_tokens"] = cached
            if not {"prompt_tokens", "completion_tokens"} <= usage.keys():
                raise ValueError("incomplete usage")
            choice = body["choices"][0]
            content, finish = choice["message"].get("content"), choice["finish_reason"]
            if not isinstance(content, str):
                content = ""
        except (KeyError, IndexError, TypeError, ValueError):
            return OperationObservation(
                status="unknown",
                external_id=external_id,
                usage=usage,
                result_json={"error_code": "kimi_observation_incomplete"},
            )
        valid = finish == "stop" and bool(content.strip())
        return OperationObservation(
            status="succeeded" if valid else "failed",
            external_id=external_id,
            usage=usage,
            actual_cost=None,
            cost_evidence="unknown",
            result_json={
                "content": content,
                "finish_reason": finish,
                "model": body.get("model", KIMI_MODEL),
                "response_type": "text_chat_completion",
            },
        )
