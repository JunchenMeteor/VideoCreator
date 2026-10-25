"""Record genuine renderer, decoder and authority calls without replacing results."""
import functools
import os
import time
from pathlib import Path
from t14_evidence import Journal, atomic_json
from ProbeTrace import wrap_probe


def install(directory, target_run_id, reconciliation_latch=None):
    # Product imports occur only in the subsequently approved child entry.
    from video_creator.application.worker import WorkerService
    from video_creator.application.engine import EngineService
    from video_creator.application.assets import AssetService
    from video_creator.media.local_render import LocalTemplateRenderer
    from video_creator.media.ffmpeg import FFmpegRuntime

    journal = Journal(Path(directory) / "Events", "actual_os_observation")
    restores = []

    def wrap(cls, name, kind, details):
        original = getattr(cls, name)

        @functools.wraps(original)
        def observed(self, *args, **kwargs):
            facts = {"pid": os.getpid(), "target_run_id": target_run_id,
                     "method": name, "kind": kind, **details(args, kwargs)}
            journal.record(kind + "_begin", facts)
            try:
                result = original(self, *args, **kwargs)
            except BaseException as error:
                journal.record(kind + "_raised", {**facts, "exception_type": type(error).__name__})
                raise
            journal.record(kind + "_returned", facts)
            return result

        setattr(cls, name, observed)
        restores.append((cls, name, original))

    wrap(LocalTemplateRenderer, "render_shot", "render", lambda a, k: {
        "step_key": "local-shot-" + str(k["index"]), "renderer": "render_shot"})
    wrap(LocalTemplateRenderer, "compose", "render", lambda a, k: {
        "step_key": "local-compose", "renderer": "compose"})
    original_probe = FFmpegRuntime.probe
    FFmpegRuntime.probe = wrap_probe(original_probe, journal, target_run_id)
    restores.append((FFmpegRuntime, "probe", original_probe))
    wrap(WorkerService, "allocate_output", "allocate_call", lambda a, k: {
        "run_id": a[0].run_id, "step_key": a[1] if len(a) > 1 else k["step_key"]})
    wrap(WorkerService, "commit_generated_step", "step_commit_call", lambda a, k: {
        "run_id": a[0].run_id, "step_key": a[1] if len(a) > 1 else k["step_key"]})
    wrap(AssetService, "register_candidate", "asset_commit_call", lambda a, k: {})
    wrap(EngineService, "complete_step", "plain_step_commit_call", lambda a, k: {"run_id": a[0].run_id})

    if reconciliation_latch is not None:
        original_finish = WorkerService.finish_reconciliation
        used = False

        @functools.wraps(original_finish)
        def end_reconciliation(self, invocation, *args, **kwargs):
            nonlocal used
            fact = {"pid": os.getpid(), "run_id": invocation.lease.run_id,
                    "lease": invocation.lease.model_dump(mode="json")}
            journal.record("finish_reconciliation_begin", fact)
            result = original_finish(self, invocation, *args, **kwargs)
            journal.record("finish_reconciliation_returned", {**fact, "underlying_original_returned": True})
            if invocation.lease.run_id == target_run_id and not used:
                used = True
                folder = Path(reconciliation_latch)
                folder.mkdir(parents=True, exist_ok=True)
                atomic_json(folder / "LatchReady.json", {
                    "event": "t14_reconciliation_end_return_latch", **fact,
                    "original_method_succeeded": True, "evidence_kind": "actual_product_call"})
                deadline = time.monotonic() + 30
                while not (folder / "ReleaseLatch").exists():
                    if time.monotonic() >= deadline:
                        raise TimeoutError("R observer latch expired; no normal continuation pass")
                    time.sleep(.02)
            return result

        WorkerService.finish_reconciliation = end_reconciliation
        restores.append((WorkerService, "finish_reconciliation", original_finish))
    return journal, restores
