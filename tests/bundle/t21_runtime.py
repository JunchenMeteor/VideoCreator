"""Test-only actual service consumer context; never an authority or public DTO.

Production objects must be constructed by a separately approved frozen backend
bootstrap. This module has no product imports and accepts no approval flags.
"""
from __future__ import annotations

import hashlib
import json
import sys
import time
from pathlib import Path


class CaseBlocked(RuntimeError):
    def __init__(self, requirement, detail):
        super().__init__(detail)
        self.requirement = requirement


def file_sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class ActualRuntime:
    def __init__(self, *, bundle, contracts, engine_error, admitted_resources,
                 fixtures, journal, process_host=None, api=None, second_instance=None):
        # Only inspect modules already admitted and loaded by the independent
        # bootstrap. This guard performs no production import of its own.
        modules = {name: sys.modules.get(name) for name in (
            "video_creator.application.bundles", "video_creator.application.engine",
            "video_creator.domain.contracts", "video_creator.domain.errors")}
        if any(module is None for module in modules.values()):
            raise CaseBlocked("approved_actual_service_bootstrap", "actual backend modules are not already loaded")
        if type(bundle) is not modules["video_creator.application.bundles"].BundleService:
            raise CaseBlocked("actual_bundle_service", "a fake/substitute BundleService is not a business context")
        if type(bundle.engine) is not modules["video_creator.application.engine"].EngineService:
            raise CaseBlocked("actual_engine", "a fake/substitute Engine is not a business context")
        if contracts is not modules["video_creator.domain.contracts"] or engine_error is not modules["video_creator.domain.errors"].EngineError:
            raise CaseBlocked("unique_backend_contracts", "consumer must use the single admitted backend DTO/error modules")
        self.bundle, self.engine, self.c, self.EngineError = bundle, bundle.engine, contracts, engine_error
        self.resources = admitted_resources
        self.fixtures, self.journal = fixtures, journal
        self.process_host, self.api, self.second_instance = process_host, api, second_instance

    def fixture(self, case_id):
        if case_id not in self.fixtures:
            raise CaseBlocked("independently_bound_fixture", "fixture absent for " + case_id)
        return self.fixtures[case_id]

    def bound_bytes(self, record):
        path = Path(record["path"])
        expected = self.resources.get(str(path))
        if expected is None or expected != record["sha256"]:
            raise CaseBlocked("immutable_resource_pin", "resource is not in the externally approved complete closure")
        raw = path.read_bytes()
        assert hashlib.sha256(raw).hexdigest() == expected
        if "size" in record:
            assert type(record["size"]) is int and len(raw) == record["size"]
        return raw

    def bound_json(self, record):
        from t15_evidence import strict_json
        return strict_json(self.bound_bytes(record))

    def publication(self, case_id):
        fixture = self.fixture(case_id)
        if not fixture.get("bundle_revision_id"):
            raise CaseBlocked("real_published_bundle", "actual service-visible published revision absent")
        actor = self.bundle.principals.owner()
        manifest = self.bundle.get_manifest(actor, fixture["bundle_revision_id"], "derivative")
        handle = self.bundle.manifest_content(actor, fixture["bundle_revision_id"], "derivative")
        raw = handle.path.read_bytes()
        assert hashlib.sha256(raw).hexdigest() == handle.sha256 and len(raw) == handle.size
        actual = manifest.model_dump(mode="json")
        assert json.loads(raw) == actual
        return fixture, manifest, raw

    def artifact(self, manifest, role):
        items = [item for item in manifest.artifacts if role in item.roles]
        assert len(items) == 1, "one exact artifact required for " + role
        item = items[0]
        handle = self.bundle.content(self.bundle.principals.owner(), manifest.bundle_revision_id, item.artifact_id, "derivative")
        raw = handle.path.read_bytes()
        assert hashlib.sha256(raw).hexdigest() == item.sha256 == handle.sha256
        assert len(raw) == item.size == handle.size
        return item, handle.path, raw

    def document(self, manifest, role, model_name):
        item, path, raw = self.artifact(manifest, role)
        model = getattr(self.c, model_name).model_validate_json(raw)
        return item, model, raw

    def transcript(self, manifest):
        model = "ActualTranscriptDocumentV03" if manifest.schema_version == "0.3.0-candidate" else "ActualTranscriptDocument"
        return self.document(manifest, "actual_transcript", model)[1]

    def rows(self, manifest, role, model_name):
        _, _, raw = self.artifact(manifest, role)
        model = getattr(self.c, model_name)
        return [model.model_validate_json(line) for line in raw.splitlines()]

    def error(self, code, call, *args, **kwargs):
        try:
            call(*args, **kwargs)
        except self.EngineError as error:
            assert error.code == code
            return {"code": error.code, "status": error.status_code}
        raise AssertionError("required service rejection absent: " + code)

    def ordinary_lease(self, case_id):
        fixture = self.fixture(case_id)
        if not fixture.get("run_id"):
            raise CaseBlocked("real_uncompleted_run", "actual run absent for lease test")
        lease = self.engine.acquire_run("t21-" + case_id.lower(), run_id=fixture["run_id"])
        if lease is None:
            raise CaseBlocked("ordinary_current_lease", "run is not eligible for ordinary work")
        return fixture, lease

    def preparation(self, case_id):
        fixture, lease = self.ordinary_lease(case_id)
        if not fixture.get("preparation_id"):
            self.engine.release_run(lease)
            raise CaseBlocked("actual_preparation", "real durable preparation required")
        preparation = self.bundle.recover_preparation(lease, fixture["preparation_id"])
        return fixture, lease, preparation

    def host(self):
        if self.process_host is None:
            raise CaseBlocked("atomic_owned_job_supervisor", "Integration suspended/Job/pins host ABI not yet bound")
        return self.process_host

    def http(self):
        if self.api is None:
            raise CaseBlocked("real_supervised_loopback_API", "actual approved API child/session not bound")
        return self.api

    def second(self):
        if self.second_instance is None:
            raise CaseBlocked("second_independent_instance", "second approved installation bootstrap absent")
        assert self.second_instance.engine.instance_id != self.engine.instance_id
        return self.second_instance

    def wait(self, predicate, seconds=30):
        end = time.monotonic() + seconds
        while time.monotonic() < end:
            result = predicate()
            if result:
                return result
            time.sleep(0.05)
        raise AssertionError("actual wall-clock condition did not arrive within approved window")
