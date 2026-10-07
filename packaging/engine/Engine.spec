# PyInstaller internal Windows candidate, built from a fixed committed source stage.
import os
from pathlib import Path
from PyInstaller.utils.hooks import collect_all, copy_metadata

stage = Path(os.environ["VIDEO_CREATOR_BUILD_STAGE"]).resolve()
source = stage / "services" / "engine" / "src"
resources = stage / "Resources"
datas = [(str(resources), "Resources")]
# Keep the fixed ASR module sources available to a separately provisioned isolated runtime.
datas += [(str(p), str(p.parent.relative_to(source))) for p in source.rglob("*.py")]
binaries = []
hiddenimports = [str(p.relative_to(source).with_suffix("")).replace(os.sep, ".") for p in source.rglob("*.py") if p.name != "__init__.py"]
for package in ("crewai", "crewai_core"):
    package_datas, package_binaries, package_hidden = collect_all(package, on_error="warn once")
    datas += package_datas
    binaries += package_binaries
    hiddenimports += package_hidden
for distribution in ("crewai", "mcp", "keyring", "video-creator-engine"):
    datas += copy_metadata(distribution, recursive=True)
hiddenimports += ["uvicorn.logging", "uvicorn.loops.auto", "uvicorn.protocols.http.auto", "uvicorn.protocols.websockets.auto", "uvicorn.lifespan.on", "keyring.backends.Windows"]
a = Analysis([str(stage / "packaging" / "engine" / "Entry.py")], pathex=[str(source)], binaries=binaries, datas=datas, hiddenimports=hiddenimports, hookspath=[], runtime_hooks=[], excludes=[], noarchive=False)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name="VideoCreatorEngine", debug=False, bootloader_ignore_signals=False, strip=False, upx=False, console=True, disable_windowed_traceback=False)
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name="VideoCreatorEngine")
