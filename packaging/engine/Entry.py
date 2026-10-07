"""Fixed frozen CLI bootstrap; no model credentials or budgets are provisioned."""

import hashlib
import json
import multiprocessing
import os
from pathlib import Path
import sys


def launch() -> int:
    resources = Path(__file__).resolve().parent / "Resources"
    if getattr(sys, "frozen", False):
        resources = Path(sys._MEIPASS) / "Resources"
    os.environ["VIDEO_CREATOR_MIGRATIONS_DIR"] = str(resources / "Migrations")
    os.environ["PYTHONUTF8"] = "1"
    os.environ["PYTHONIOENCODING"] = "utf-8"
    os.environ["OTEL_SDK_DISABLED"] = "true"
    os.environ["CREWAI_DISABLE_TELEMETRY"] = "true"
    os.environ["CREWAI_DISABLE_TRACKING"] = "true"
    if "serve" in sys.argv[1:]:
        manifest = json.loads((resources / "Media" / "manifest.json").read_text(encoding="utf-8"))
        for item in manifest["files"]:
            target = (resources / item["path"]).resolve()
            if not target.is_relative_to(resources.resolve()) or not target.is_file():
                raise RuntimeError("bundled_resource_missing")
            if target.stat().st_size != item["bytes"] or hashlib.sha256(target.read_bytes()).hexdigest() != item["sha256"]:
                raise RuntimeError("bundled_resource_changed")
        if "--ffmpeg" not in sys.argv and "--ffprobe" not in sys.argv:
            sys.argv.extend(["--ffmpeg", str(resources / "Media" / "bin" / "ffmpeg.exe"), "--ffprobe", str(resources / "Media" / "bin" / "ffprobe.exe")])
    from video_creator.cli.main import main
    return main()


if __name__ == "__main__":
    multiprocessing.freeze_support()
    raise SystemExit(launch())
