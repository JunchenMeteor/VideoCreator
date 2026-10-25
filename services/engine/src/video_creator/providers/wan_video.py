"""Wan2.7 BYOK submission and original-task collection; never resubmits a task."""
from __future__ import annotations

import hashlib
import ipaddress
import json
import re
from decimal import Decimal
from urllib.parse import urlsplit

import httpx

from video_creator.domain import contracts as c
from video_creator.domain.errors import EngineError
from video_creator.providers.production_common import install_output, permit_scope
from video_creator.workflows.attempt_control import attempt_control
from video_creator.workflows.production_json import canonical_object

MODEL = "wan2.7-t2v-2026-06-12"
SYNTHESIS_PATH = "/api/v1/services/aigc/video-generation/video-synthesis"
MAX_VIDEO_BYTES = 128 * 1024 * 1024


def endpoint(config):
    workspace, region = config.get("workspace_id"), config.get("region")
    if (not isinstance(workspace, str) or not re.fullmatch("[a-zA-Z0-9-]{2,63}", workspace)
            or region not in {"cn-beijing", "ap-southeast-1"} or config.get("model") != MODEL):
        raise EngineError("production_video_not_configured", "A verified matching Wan2.7 workspace, region and model are required.", 503)
    return f"https://{workspace}.{region}.maas.aliyuncs.com"


def download_hosts(config):
    hosts = config.get("download_hosts")
    if not isinstance(hosts, list) or not 0 < len(hosts) <= 16:
        raise EngineError("production_video_download_scope_missing", "Provider-confirmed exact output hosts must be installed before task submission.", 503)
    result = set()
    for host in hosts:
        if (not isinstance(host, str) or not re.fullmatch("[a-z0-9.-]{1,253}", host)
                or not host.endswith(".aliyuncs.com") or ".." in host or host.startswith(".")):
            raise EngineError("production_video_download_denied", "Video output hosts require exact provider storage domains.", 403)
        try:
            ipaddress.ip_address(host)
        except ValueError:
            result.add(host)
        else:
            raise EngineError("production_video_download_denied", "IP output hosts are not admitted.", 403)
    return frozenset(result)


class WanVideoDriver:
    def __init__(self, *, engine, worker, decoder, resources, route_id, lease, output,
                 shot, ratio, cancel, deadline_monotonic):
        self.engine, self.worker, self.decoder, self.resources = engine, worker, decoder, resources
        self.route_id, self.lease, self.output, self.shot = route_id, lease, output, shot
        self.control = attempt_control(cancel, deadline_monotonic)
        config = resources.section("picture", "wan2.7")
        self.base, self.allowed_hosts = endpoint(config), download_hosts(config)
        if config.get("resolution") not in {"720P", "1080P"} or ratio not in {"9:16", "16:9"}:
            raise EngineError("production_video_resolution_invalid", "Actual approved output requires a supported finite frame profile.", 422)
        if not 0 < shot.duration_us <= 15_000_000 or shot.duration_us % 40000:
            raise EngineError("production_video_duration_invalid", "This provider supports only bounded two-to-fifteen second generated clips.", 422)
        duration = max(2, (shot.duration_us + 999999) // 1000000)
        prompt = "Generate one continuous shot. No dialogue or spoken words; ambient soundtrack only.\n" + shot.visual + "\nCamera: " + shot.camera
        if len(prompt) > 1500:
            raise EngineError("production_video_prompt_invalid", "Approved visual prompt exceeds the provider protocol bound.", 422)
        self.payload = {"model": MODEL, "input": {"prompt": prompt}, "parameters": {
            "resolution": config["resolution"], "ratio": ratio, "duration": duration,
            "prompt_extend": False, "watermark": True}}
        self.request_sha256 = hashlib.sha256(canonical_object(self.payload).encode()).hexdigest()
        self.config_sha256 = hashlib.sha256(canonical_object(config).encode()).hexdigest()

    def _scope(self, permit, secret):
        permit_scope(self.engine, permit, self.lease, self.route_id, "video", self.base + SYNTHESIS_PATH,
                     local=False, secret=secret)

    def _json(self, method, url, secret, *, payload=None):
        # No SDK retry, redirect, environment proxy or response body logging.
        self.control.check()
        headers = {"Authorization": "Bearer " + secret.reveal()}
        if payload is not None:
            headers.update({"Content-Type": "application/json", "X-DashScope-Async": "enable"})
        with (httpx.Client(transport=httpx.HTTPTransport(retries=0), follow_redirects=False,
                          trust_env=False, timeout=httpx.Timeout(self.control.remaining(30), connect=self.control.remaining(10))) as client,
              client.stream(method, url, json=payload, headers=headers) as response):
            if response.status_code != 200:
                raise ValueError("upstream status")
            parts, size = [], 0
            for block in response.iter_bytes():
                self.control.check()
                size += len(block)
                if size > 1024 * 1024:
                    raise ValueError("upstream response bound")
                parts.append(block)
        value = json.loads(b"".join(parts))
        if not isinstance(value, dict):
            raise TypeError("upstream object")
        return value

    def __call__(self, permit, secret):
        with self.control.activate():
            self._scope(permit, secret)
            try:
                body = self._json("POST", self.base + SYNTHESIS_PATH, secret, payload=self.payload)
                task_id = body["output"]["task_id"]
                if not isinstance(task_id, str) or not re.fullmatch("[a-zA-Z0-9-]{1,128}", task_id):
                    raise ValueError("task identity")
            except (httpx.HTTPError, OSError, ValueError, TypeError, KeyError, EngineError):
                return c.OperationObservation(status="unknown", result_json={"error_code": "wan_submission_uncertain",
                        "request_payload_sha256": self.request_sha256})
            # Return immediately so the original Executor durably observes the
            # acceptance before any later poll. Never repeat POST during lookup.
            return c.OperationObservation(status="pending", external_id=task_id,
                result_json={"task_id": task_id, "request_payload_sha256": self.request_sha256,
                             "provider_config_sha256": self.config_sha256,
                             "resource_manifest_sha256": self.resources.manifest_sha256,
                             "runtime_manifest_sha256": self.resources.runtime_manifest_sha256,
                             "provider_request_id": body.get("request_id"), "needs_original_task_query": True})

    def collect_original(self, permit, secret, original: c.OperationObservation):
        """Bound adapter collection, NOT a registered reconciliation dispatcher.

        Backend must call this only under its original-operation restricted
        authorization/current output fence. That port is still pending; it must
        not create a new normal Run/Operation merely to invoke this method.
        """
        with self.control.activate():
            self._scope(permit, secret)
            if (not isinstance(original, c.OperationObservation) or original.status not in {"pending", "unknown"}
                    or not isinstance(original.result_json, dict)
                    or original.result_json.get("task_id") != original.external_id
                    or original.result_json.get("request_payload_sha256") != self.request_sha256
                    or original.result_json.get("provider_config_sha256") != self.config_sha256
                    or original.result_json.get("resource_manifest_sha256") != self.resources.manifest_sha256
                    or original.result_json.get("runtime_manifest_sha256") != self.resources.runtime_manifest_sha256
                    or not isinstance(original.external_id, str) or not re.fullmatch("[a-zA-Z0-9-]{1,128}", original.external_id)):
                raise EngineError("production_video_task_identity_invalid", "Only the exact recorded original task and resources may be queried.", 409)
            try:
                body = self._json("GET", self.base + "/api/v1/tasks/" + original.external_id, secret)
                result = body["output"]
                if result["task_id"] != original.external_id:
                    raise ValueError("task changed")
                status = result["task_status"]
                if status in {"PENDING", "RUNNING"}:
                    return original
                if status != "SUCCEEDED":
                    return c.OperationObservation(status="unknown", external_id=original.external_id,
                        result_json={**original.result_json, "provider_task_status": status,
                                     "error_code": "wan_original_task_not_successful"})
                raw_usage = body["usage"]
                duration_us = Decimal(str(raw_usage["duration"])) * 1_000_000
                if (not duration_us.is_finite() or not 0 < duration_us <= 15_000_000
                        or duration_us != duration_us.to_integral_value()
                        or duration_us != self.payload["parameters"]["duration"] * 1_000_000):
                    raise ValueError("usage duration")
                usage = {"video_duration_us": int(duration_us), "video_count": raw_usage["video_count"], "resolution_tier": raw_usage["SR"]}
                if any(type(value) is not int or value < 0 for value in usage.values()):
                    raise ValueError("usage integers")
                if usage["video_count"] != 1 or usage["resolution_tier"] != int(self.payload["parameters"]["resolution"].removesuffix("P")):
                    raise ValueError("usage profile")
                if self.output.completed_path.is_file() and not self.output.partial_path.exists():
                    # The original controlled completed handle can be observed
                    # without downloading/regenerating it. Backend still owns
                    # current/adoption authority before this method is callable.
                    probe = self.decoder(self.output.completed_path, "video/mp4")
                    file = self.worker.finish_output(self.lease, self.output)
                else:
                    self._download(result["video_url"], secret=None)
                    file, probe = install_output(self.engine, self.worker, self.lease, self.output, self.decoder, "video/mp4")
                if not probe.decoded or probe.media_type != "video/mp4" or not probe.has_video or probe.duration_us is None or probe.duration_us < self.shot.duration_us:
                    raise ValueError("actual clip duration")
            except (httpx.HTTPError, OSError, ValueError, TypeError, KeyError, ArithmeticError, EngineError):
                return c.OperationObservation(status="unknown", external_id=original.external_id,
                    result_json={**original.result_json, "error_code": "wan_collection_uncertain"})
            # Raw usage is not a bill. Only an approved backend pricing/receipt
            # rule can settle the reservation and make this operation Ready.
            return c.OperationObservation(status="succeeded", external_id=original.external_id, usage=usage,
                result_json={**original.result_json, "generated_files": [file.model_dump(mode="json")],
                             "actual_probe": probe.model_dump(mode="json"), "provider_task_status": "SUCCEEDED"})

    def _download(self, url, secret):
        parsed = urlsplit(url)
        if (secret is not None or parsed.scheme != "https" or parsed.hostname not in self.allowed_hosts
                or parsed.username or parsed.password or parsed.fragment or parsed.port not in {None, 443}):
            raise EngineError("production_video_download_denied", "Result URL is outside the installed exact storage scope.", 403)
        with (httpx.Client(transport=httpx.HTTPTransport(retries=0), trust_env=False, follow_redirects=False,
                          timeout=httpx.Timeout(self.control.remaining(60), connect=self.control.remaining(10))) as client,
              client.stream("GET", url) as response):
            if response.status_code != 200:
                raise ValueError("download status")
            size = 0
            with self.output.partial_path.open("xb") as target:
                for block in response.iter_bytes():
                    self.control.check()
                    size += len(block)
                    if size > MAX_VIDEO_BYTES:
                        raise ValueError("video bound")
                    target.write(block)
