"""Proposed versioned CLI child; never invoked during standard authoring."""
import argparse
import hashlib
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "tests/gate0"))
from PhasedTrace import install
from SuccessLatch import install_after_success_latch


def main():
    parser = argparse.ArgumentParser()
    for name in ["data-dir", "resource-manifest", "target-run", "trace-dir", "latch-dir", "approved-source-freeze"]:
        parser.add_argument("--" + name, required=True)
    parser.add_argument("--stage", choices=["K", "RN"], required=True)
    args = parser.parse_args()
    freeze = json.loads(Path(args.approved_source_freeze).read_text("utf8"))
    if not freeze.get("root_launch_authorized") or not freeze.get("independent_criteria_approved"):
        raise ValueError("Await actual standard approval and final root launch")
    if freeze.get("criteria_revision") != 2 or freeze.get("criteria_review_id") != "RV14":
        raise ValueError("Await independent approval of candidate revision2")
    if freeze.get("criteria_version") != "gate0-local-recovery-phased-evidence-v1":
        raise ValueError("Incorrect approved criteria version")
    for relative, expected in freeze["production_sources"].items():
        path = (REPO / relative).resolve(strict=True)
        if not path.is_relative_to(REPO) or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise ValueError("Final production source identity mismatch")
    install(args.trace_dir, args.target_run, args.latch_dir if args.stage == "RN" else None)
    if args.stage == "K":
        install_after_success_latch("finish_output", args.latch_dir, args.target_run, "local-shot-1")
    from video_creator.cli.main import main as product_main
    sys.argv = ["video_creator", "worker", "--data-dir", args.data_dir,
                "--workflow", "gate0-local-render-v1", "--resource-manifest", args.resource_manifest,
                "--run-id", args.target_run, "--max-seconds", "70"]
    return product_main()


if __name__ == "__main__":
    raise SystemExit(main())
