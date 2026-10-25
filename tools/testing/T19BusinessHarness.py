"""Real business entry; Python -I -S startup only through approved PS starter.

Current root/Review runtime records do not exist: direct invocation is refused.
No product/package import appears at module scope and no caller supplies pins.
"""
import argparse
import hashlib
import json
import math
import os
import sys
import time
import traceback
import types
import xml.etree.ElementTree as ET
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
OWN = Path("G:/开发测试/Codex/VideoCreatorImplementation/TestDevelopment/BusinessHarness-T19").resolve()
AUTHORITY = REPO / "docs/task-board/T19RuntimeAuthorization.json"


class NotReady(RuntimeError):
    def __init__(self, message, *, phase="launch_admission", source_exception_type=None, frames=None):
        super().__init__(message)
        self.phase = phase
        self.source_exception_type = source_exception_type
        self.frames = frames or []


def call_setup(callback, legacy_not_ready_type):
    # Exact approved legacy guard class, not RuntimeError/Exception in general.
    # Genuine assertion/provider/implementation failures are not reclassified.
    try:
        return callback()
    except legacy_not_ready_type as error:
        frames = [{"file": f.filename, "line": f.lineno, "function": f.name}
                  for f in traceback.extract_tb(error.__traceback__)]
        raise NotReady(str(error), phase="setup_bootstrap",
                       source_exception_type=type(error).__name__, frames=frames) from error


def not_ready_record(error):
    return {"status": "not_ready_for_execution", "phase": error.phase,
            "code": str(error), "exception_type": type(error).__name__,
            "source_exception_type": error.source_exception_type, "frames": error.frames,
            "actual_cases": 0, "skip": 0, "exit": 78}


def _pairs(rows):
    result = {}
    for key, value in rows:
        if key in result:
            raise NotReady("duplicate governance JSON key")
        result[key] = value
    return result


def _float(value):
    parsed = float(value)
    if not math.isfinite(parsed):
        raise NotReady("nonfinite governance number")
    return parsed


def read_json(path):
    raw = path.read_bytes()
    if len(raw) > 67_108_864:
        raise NotReady("governance file too large")
    return json.loads(raw.decode("utf-8"), object_pairs_hook=_pairs, parse_float=_float,
        parse_constant=lambda _: (_ for _ in ()).throw(NotReady("nonfinite governance number")))


def file_sha(path):
    digest = hashlib.sha256()
    with path.open("rb") as source:
        while block := source.read(1_048_576):
            digest.update(block)
    return digest.hexdigest()


def check_file(item):
    path = Path(item["path"])
    if not path.is_absolute() or path.is_symlink() or file_sha(path) != item["sha256"]:
        raise NotReady("externally bound file changed")
    return path.resolve()


def load_trusted_launch(batch, output):
    if not AUTHORITY.is_file():
        raise NotReady("root authorization not published")
    root = read_json(AUTHORITY)
    if root["status"] != "ROOT_APPROVED_EXACT_RUNTIME" or batch not in root["batches"] or root["fees_cny"] != "0":
        raise NotReady("root approved runtime scope missing")
    review_path = check_file(root["independent_review"])
    if not review_path.is_relative_to(REPO / "docs/reviews"):
        raise NotReady("review outside independent owner boundary")
    review = read_json(review_path)
    if review["status"] != "APPROVED_EXACT_RUNTIME_BINDING" or batch not in review["batches"]:
        raise NotReady("independent runtime approval missing")
    for key in ("binding", "admission"):
        if review[key + "_sha256"] != root[key]["sha256"]:
            raise NotReady("independent expected runtime pins differ")
    binding = read_json(check_file(root["binding"]))
    admission = read_json(check_file(root["admission"]))
    if not Path(admission["own_data_dir"]).resolve().is_relative_to(OWN):
        raise NotReady("DataDir is outside this T19 isolated instance scope")
    output = output.resolve()
    if output != Path(root["output_dir"]).resolve() or not output.is_relative_to(OWN):
        raise NotReady("not exact own approved output")
    receipt = read_json(output / "PrePythonReceipt.json")
    if receipt["root_authorization_sha256"] != file_sha(AUTHORITY) or receipt["binding_sha256"] != root["binding"]["sha256"] or receipt["admission_sha256"] != root["admission"]["sha256"] or receipt["batch"] != batch:
        raise NotReady("pre-Python closed-input receipt missing or changed")
    if not sys.flags.no_site or not sys.flags.isolated:
        raise NotReady("requires actual -I -S before Python/site hooks")
    if Path(sys.executable).resolve() != Path(binding["service_python"]).resolve():
        raise NotReady("interpreter differs from trusted prelaunch identity")
    if any(n == "video_creator" or n.startswith("video_creator.") for n in sys.modules):
        raise NotReady("product imported before full launch admission")
    return root, binding, admission


class Journal:
    def __init__(self, output):
        self.path = output / "Events.jsonl"
        self.sequence = 0

    def record(self, event, fields):
        self.sequence += 1
        row = {"sequence": self.sequence, "event": event, "at_ns": time.time_ns(), "fields": fields}
        with self.path.open("a", encoding="utf-8", newline="\n") as stream:
            stream.write(json.dumps(row, ensure_ascii=False, allow_nan=False) + "\n")
            stream.flush()
            os.fsync(stream.fileno())
        return types.SimpleNamespace(name=self.sequence)


def actual_context(root, binding, admission, output, journal):
    # The -S interpreter deliberately did not process .pth/editable hooks. Add
    # only the exact reviewed site directory as a path, not site.addsitedir().
    site = Path(binding["service_site_packages"]).resolve(strict=True)
    if not site.is_relative_to(REPO / ".venv"):
        raise NotReady("service dependency path outside actual frozen root environment")
    tests = REPO / "tests/bundle"
    sys.path.insert(0, str(tests))
    from t16_guard import admit_runtime, NotReadyForExecution
    def construct():
        _, checked = admit_runtime(root["admission"]["path"], root["admission"]["sha256"],
                                   root["binding"]["path"], root["binding"]["sha256"])
        if str(Path(__file__).resolve()) not in checked["required_sources"]:
            raise NotReady("actual harness omitted from the frozen body closure", phase="setup_bootstrap")
        sys.path.insert(0, str(site))
        from t18_business_adapter import B11ServiceAdapter
        return B11ServiceAdapter(root["admission"]["path"], root["admission"]["sha256"],
                                 root["binding"]["path"], root["binding"]["sha256"], journal)
    adapter = call_setup(construct, NotReadyForExecution)
    from video_creator.domain import contracts
    from video_creator.domain.errors import EngineError
    from video_creator.domain.bundle import AccessContext, PrincipalRegistration
    from video_creator.application.worker import WorkerService
    return types.SimpleNamespace(bundle=adapter.service, engine=adapter.service.engine,
        contracts=contracts, EngineError=EngineError, AccessContext=AccessContext,
        PrincipalRegistration=PrincipalRegistration, WorkerService=WorkerService,
        resource_manifest_sha256=admission["t18_trusted_resource_profile"]["asr_manifest_sha256"])


def run_cases(cases, context, journal, output):
    # Actual methods/driver exceptions are retained; no unittest.skip or fakepass.
    from t16_guard import NotReadyForExecution
    suite = ET.Element("testsuite", name="T19-business", tests=str(len(cases)), failures="0", errors="0", skipped="0")
    results = []
    failures = 0
    unavailable = 0
    for name, callback in cases:
        begin = time.monotonic()
        journal.record("actual_case_enter", {"case": name})
        node = ET.SubElement(suite, "testcase", name=name)
        try:
            evidence = callback(context)
            journal.record("actual_case_returned", {"case": name, "evidence": evidence})
            result = {"case": name, "status": "passed", "evidence": evidence}
        except BaseException as error:
            not_ready = isinstance(error, (NotReadyForExecution, NotReady))
            if not_ready:
                unavailable += 1
            else:
                failures += 1
            # Avoid reflecting model/source/credential bodies. Full code and
            # assertion location is retained via traceback frame coordinates.
            frames = [{"file": f.filename, "line": f.lineno, "function": f.name} for f in traceback.extract_tb(error.__traceback__)]
            ET.SubElement(node, "error" if not_ready else "failure", type=type(error).__name__).text = json.dumps(frames)
            result = {"case": name, "status": "not_ready_for_execution" if not_ready else "failed", "exception_type": type(error).__name__, "frames": frames}
            journal.record("actual_case_raised", result)
        node.set("time", str(time.monotonic() - begin))
        results.append(result)
    suite.set("failures", str(failures))
    suite.set("errors", str(unavailable))
    ET.ElementTree(suite).write(output / "Results.xml", encoding="utf-8", xml_declaration=True)
    return results, failures, unavailable


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--batch", choices=("service-negative", "transport-negative", "qualified-bundle", "bundle-consume", "bundle-correction", "bundle-runtime-gap"), required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        root, binding, admission = load_trusted_launch(args.batch, args.output)
        fixture = None
        if args.batch in {"qualified-bundle", "bundle-consume", "bundle-correction", "bundle-runtime-gap"}:
            if not admission.get("actual_fixture"):
                raise NotReady("real independently qualified fixture/bootstrap not bound; positive cannot execute")
            fixture = read_json(check_file(admission["actual_fixture"]))
            if args.batch == "bundle-correction":
                oracle_record = fixture.get("correction_oracle")
                if not oracle_record:
                    raise NotReady("independent per-ancestor correction oracle absent", phase="fixture_admission")
                resource_map = binding["required_resources"]
                if resource_map.get(oracle_record["path"]) != oracle_record["sha256"]:
                    raise NotReady("correction oracle not independently bound as resource", phase="fixture_admission")
                oracle = read_json(check_file(oracle_record))
                for ancestor in oracle.get("ancestors", []):
                    record = {"path": ancestor["file_path"], "sha256": ancestor["file_sha256"]}
                    if resource_map.get(record["path"]) != record["sha256"]:
                        raise NotReady("original ancestor bytes not independently bound as resource", phase="fixture_admission")
                    check_file(record)
                fixture["correction_oracle_document"] = oracle
        output = args.output.resolve()
        journal = Journal(output)
        context = actual_context(root, binding, admission, output, journal)
        from t19_business_cases import SERVICE_CASES
        if args.batch == "service-negative":
            cases = SERVICE_CASES
        elif args.batch == "transport-negative":
            from t19_transport_cases import run_actual_http_negative
            cases = [("real-http-auth-and-404", run_actual_http_negative)]
        else:
            from t19_bundle_cases import produce_from_actual_fixture, consume_actual_bundle, reject_actual_runtime_gap, consume_actual_correction
            if args.batch == "qualified-bundle":
                call = reject_actual_runtime_gap if fixture.get("scenario") == "actual-runtime-gap" else produce_from_actual_fixture
            elif args.batch == "bundle-correction":
                call = consume_actual_correction
            elif args.batch == "bundle-runtime-gap":
                call = reject_actual_runtime_gap
            else:
                call = consume_actual_bundle
            cases = [(args.batch, lambda ctx: call(ctx, fixture))]
        results, failures, unavailable = run_cases(cases, context, journal, output)
        context.bundle.stop_exports()
        terminal = {"actual_cases": len(results), "failures": failures, "not_ready": unavailable, "skip": 0, "results": results,
                    "scope": "actual bound local services; does not prove autonomous model quality/precision/threeOS", "exit": 1 if failures else 78 if unavailable else 0}
        (output / "BusinessReceipt.json").write_text(json.dumps(terminal, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8", newline="\n")
        print(json.dumps({"cases": len(results), "failures": failures, "skip": 0, "exit": terminal["exit"]}))
        return terminal["exit"]
    except NotReady as error:
        print(json.dumps(not_ready_record(error)))
        return 78


if __name__ == "__main__":
    raise SystemExit(main())
