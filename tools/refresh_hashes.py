"""Regenerate FILE_HASHES.json and PUBLISH_MANIFEST.json after a REVIEWED release change.
Python 3.10+, standard library only. Never run this to silence an unexpected hash failure.
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
ADDON = ROOT / "pk01_park_studio"
MANIFEST = ROOT / "PUBLISH_MANIFEST.json"
SKIP_DIRS = {".git", "__pycache__", "dist", ".venv", "venv", ".pytest_cache"}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def repository_files() -> list[str]:
    try:
        out = subprocess.run(["git", "ls-files", "--cached", "--others", "--exclude-standard"], cwd=ROOT,
                             check=True, capture_output=True, text=True).stdout.splitlines()
        files = [f for f in out if (ROOT / f).is_file()]
    except (OSError, subprocess.CalledProcessError):
        files = [p.relative_to(ROOT).as_posix() for p in ROOT.rglob("*")
                 if p.is_file() and not SKIP_DIRS.intersection(p.relative_to(ROOT).parts)]
    return sorted(f for f in files if f != MANIFEST.name and not f.endswith((".pyc", ".pyo")))


def refresh() -> tuple[int, int]:
    from tools.build_addon import source_files
    record = {p.relative_to(ADDON).as_posix(): sha256(p) for p in source_files() if p.name != "FILE_HASHES.json" or p.parent != ADDON}
    (ADDON / "FILE_HASHES.json").write_text(json.dumps(dict(sorted(record.items())), indent=2), encoding="utf-8")
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    manifest["files"] = {f: {"size": (ROOT / f).stat().st_size, "sha256": sha256(ROOT / f)} for f in repository_files()}
    MANIFEST.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return len(record), len(manifest["files"])


if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(ROOT))
    addon, repo = refresh()
    print(f"FILE_HASHES.json: {addon} add-on files; PUBLISH_MANIFEST.json: {repo} repository files.")
