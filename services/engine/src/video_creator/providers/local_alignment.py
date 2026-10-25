"""One registered offline CTC request, original JSON allocation and owned child."""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import threading
import time
from pathlib import Path

from video_creator.domain import contracts as c
from video_creator.domain.errors import EngineError
from video_creator.domain.registered_alignment import (
    AffectedAlignmentRequest,
    InitialAlignmentRequest,
    alignment_request_bytes,
)
from video_creator.providers.local_asr import AsrProcessError, _ProcessTree, _Stream
from video_creator.providers.production_common import local_observation, output_scope
from video_creator.providers.production_resources import (
    ProductionResources,
    file_sha256,
)
from video_creator.workflows.attempt_control import attempt_control


def parse_request(data):
    if type(data) is not dict:
        raise EngineError("alignment_input_invalid", "Only the original canonical registered request is accepted.", 422)
    model = {"registered-initial-alignment-request-v1": InitialAlignmentRequest,
             "registered-affected-alignment-request-v1": AffectedAlignmentRequest}.get(data.get("format"))
    if model is None:
        raise EngineError("alignment_input_invalid", "Only the two sole registered request grammars are supported.", 422)
    return model.model_validate_json(json.dumps(data, ensure_ascii=False, allow_nan=False))


def create_alignment_builder(*, engine, worker, bundle, storage_root, resource_manifest_path,
                             resource_manifest_sha256, runtime_manifest_sha256, registration):
    """Trusted factory; no resource path or arbitrary entry point from caller text."""
    from video_creator.workflows.autonomous_production import BoundProductionDriver

    resources = ProductionResources(resource_manifest_path, resource_manifest_sha256, runtime_manifest_sha256)

    def builder(request_data, ordered_output_reservations, *, ordinary_lease, cancel, deadline_monotonic):
        request = parse_request(request_data)
        outputs = output_scope(ordered_output_reservations, ordinary_lease, storage_root)
        if (len(outputs) != 1 or request.binding.run_id != ordinary_lease.run_id
                or request.alignment_registration.registration != registration
                or request.alignment_registration.resource_manifest_sha256 != resources.manifest_sha256
                or request.alignment_registration.runtime_manifest_sha256 != resources.runtime_manifest_sha256
                or outputs[0].input_sha256 != hashlib.sha256(alignment_request_bytes(request)).hexdigest()):
            raise EngineError("alignment_binding_invalid", "One original request, ordinary lease, registration and allocation must agree.", 403)
        driver = AlignmentDriver(engine, worker, bundle, resources, storage_root, ordinary_lease, outputs[0], request,
                                 cancel, deadline_monotonic)
        return BoundProductionDriver(driver, request.model_dump(mode="json"))

    return builder


class AlignmentDriver:
    def __init__(self, engine, worker, bundle, resources, storage_root, lease, output, request, cancel, deadline):
        self.engine, self.worker, self.bundle, self.resources = engine, worker, bundle, resources
        self.storage_root, self.lease, self.output, self.request = Path(storage_root), lease, output, request
        self.control = attempt_control(cancel, deadline)

    def __call__(self, permit, secret):
        with self.control.activate():
            request, declared = self.request, self.request.alignment_registration
            route = permit.route
            route_sha = hashlib.sha256(json.dumps(route.model_dump(mode="json"), ensure_ascii=False,
                sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()
            if ((permit.run_id, permit.fencing_token) != (self.lease.run_id, self.lease.fencing_token)
                    or route.route_id != declared.registration.route_id or route_sha != declared.route_sha256
                    or route.capability != "alignment" or not route.verified or route.source != "owned_local"
                    or route.credential_ref is not None or secret is not None or route.max_operation_cost.units()):
                raise EngineError("alignment_permit_denied", "Only the original verified free local route and current ordinary fence may execute.", 403)
            self.engine.get_request(self.lease)
            section = self.resources.section("alignment", "qualified_local_forced_alignment")
            if section != declared.resources.model_dump(mode="json"):
                raise EngineError("alignment_resource_changed", "Only the original complete installed resource section is used.", 503)
            worker_path = self.resources.resource(section["worker_resource"])
            runtime_path = self.resources.resource(section["runtime_resource"])
            current = Path(__file__).parents[1] / "media/alignment_worker.py"
            if (file_sha256(current) != declared.worker_sha256 or file_sha256(worker_path) != declared.worker_sha256
                    or file_sha256(runtime_path) != declared.runtime_sha256):
                raise EngineError("alignment_resource_changed", "Actual fixed worker/runtime bytes changed.", 503)
            # The installer index fixes the full engine tree, not only the entry
            # point. Exactly one indexed package marker determines its root.
            markers = [r["relative_path"] for r in self.resources.records.values()
                       if r["relative_path"].endswith("/video_creator/__init__.py")]
            if len(markers) != 1:
                raise EngineError("alignment_engine_resources_missing", "One complete indexed installed engine closure is required.", 503)
            prefix = markers[0].rsplit("/", 1)[0] + "/"
            files = {r["relative_path"]: r["sha256"] for r in self.resources.records.values()
                     if r["relative_path"].startswith(prefix)}
            required = ("domain/contracts.py", "domain/registered_alignment.py", "media/alignment_text.py", "media/ctc_alignment.py")
            for name in required:
                indexed = self.resources.resource(prefix + name)
                actual = Path(__file__).parents[1] / name
                if file_sha256(actual) != file_sha256(indexed):
                    raise EngineError("alignment_engine_resources_changed", "The installed worker closure differs from the current registered implementation.", 503)
            audio = self.bundle.content_path(self.lease, request.audio.asset_id)
            if (audio.stat().st_size, file_sha256(audio)) != (request.audio.size, request.audio.sha256):
                raise EngineError("alignment_audio_changed", "Original admitted complete audio bytes changed.", 422)
            protocol = {"protocol": "registered-ctc-worker-v1", "resource_root": str(self.resources.root),
                        "engine_files": files, "engine_marker": markers[0], "storage_root": str(self.storage_root),
                        "partial_output": str(self.output.partial_path), "audio_path": str(audio),
                        "request": request.model_dump(mode="json"),
                        "request_sha256": hashlib.sha256(alignment_request_bytes(request)).hexdigest()}
            observed = self._run([str(runtime_path), "-I", "-B", "-X", "utf8", str(worker_path)], protocol)
            identity = c.AlignmentExecutionIdentity.model_validate(observed.get("execution_identity"))
            if (observed.get("status") != "succeeded" or observed.get("protocol") != protocol["protocol"]
                    or observed.get("request_sha256") != protocol["request_sha256"]
                    or identity != declared.registration.method_qualification_ref.execution_identity
                    or observed.get("output_sha256") != file_sha256(self.output.partial_path)
                    or observed.get("output_bytes") != self.output.partial_path.stat().st_size):
                raise EngineError("alignment_child_output_invalid", "Actual child request, identity and complete output must agree.", 422)
            self.engine.get_request(self.lease)
            try:
                os.link(self.output.partial_path, self.output.completed_path, follow_symlinks=False)
                self.output.partial_path.unlink()
            except OSError:
                raise EngineError("alignment_output_completion_uncertain", "Keep the original allocated handles for reconciliation.", 409, "reconcile") from None
            manifest = self.worker.finish_output(self.lease, self.output)
            locator = {"preparation_id": request.preparation_id} if type(request) is InitialAlignmentRequest else {"repair_command_sha256": request.repair_command_sha256}
            return local_observation((manifest,), {**locator, "request_sha256": protocol["request_sha256"],
                                                   "execution_identity": identity.model_dump(mode="json")})

    def _run(self, argv, protocol):
        raw = json.dumps(protocol, ensure_ascii=False, allow_nan=False).encode()
        if len(raw) > 16 * 1024 * 1024:
            raise EngineError("alignment_input_exceeded", "Original protocol exceeds its finite byte bound.", 413)
        deadline = time.monotonic() + self.control.remaining(1800)
        process = tree = writer = streams = None
        write_failed = threading.Event()
        failure, closed = None, False
        try:
            process = subprocess.Popen(argv, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                env={**{name: os.environ[name] for name in ("SYSTEMROOT", "TEMP", "TMP") if name in os.environ},
                     "HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1"},
                shell=False, start_new_session=os.name != "nt")
            tree = _ProcessTree(process)
            stdout, stderr = _Stream(process.stdout, 65536), _Stream(process.stderr, 65536)
            streams = (stdout, stderr)

            def send():
                try:
                    process.stdin.write(raw)
                    process.stdin.close()
                except (OSError, ValueError):
                    write_failed.set()

            writer = threading.Thread(target=send, daemon=True)
            writer.start()
            while process.poll() is None:
                self.control.check()
                if time.monotonic() >= deadline:
                    raise EngineError("alignment_timeout", "The original CTC child exceeded its bounded deadline.", 409)
                if (write_failed.is_set() or any(s.exceeded.is_set() or s.failed.is_set() for s in streams)
                        or self.output.partial_path.exists() and self.output.partial_path.stat().st_size > 8 * 1024 * 1024):
                    raise EngineError("alignment_child_output_invalid", "Original child protocol exceeded its byte bound.", 422)
                time.sleep(0.02)
        except EngineError as error:
            failure = error
        except (OSError, ValueError, AsrProcessError):
            failure = EngineError("alignment_child_failed", "Original local CTC process was unavailable.", 503)
        finally:
            try:
                closed = tree.close() if tree is not None else False
            except (OSError, AsrProcessError):
                closed = False
            if process is not None:
                try:
                    if process.poll() is None:
                        process.kill()
                    process.wait(timeout=5)
                except (OSError, subprocess.TimeoutExpired):
                    closed = False
            if writer is not None:
                writer.join(timeout=5)
            if streams is not None:
                for stream in streams:
                    stream.thread.join(timeout=5)
        if (process is None or process.poll() is None or type(process.returncode) is not int or not closed
                or writer is None or writer.is_alive() or streams is None or any(s.thread.is_alive() for s in streams)):
            raise EngineError("alignment_cleanup_uncertain", "Owned child, descendants and protocol resources lack a complete terminal observation.", 503, "reconcile")
        if failure is not None:
            raise failure
        if process.returncode != 0 or any(s.exceeded.is_set() or s.failed.is_set() for s in streams):
            raise EngineError("alignment_child_failed", "Actual CTC child did not return a successful bounded protocol.", 503)
        from video_creator.application.bundles import strict_json

        result = strict_json(bytes(stdout.content))
        if type(result) is not dict:
            raise EngineError("alignment_child_output_invalid", "Actual child protocol must be one complete object.", 422)
        return result
