"""Build a deterministic Blender-installable ZIP. Python 3.10+, standard library only."""
from __future__ import annotations
import argparse
import ast
import hashlib
import json
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

ROOT = Path(__file__).resolve().parents[1]
ADDON = ROOT / "pk01_park_studio"


def source_files(addon: Path = ADDON) -> list[Path]:
    result = []
    for path in sorted(addon.rglob("*")):
        if path.is_symlink():
            raise ValueError(f"Symlink not allowed in add-on package: {path}")
        if path.is_file() and "__pycache__" not in path.parts and path.suffix not in {".pyc", ".pyo"}:
            result.append(path)
    return result


def verify_supplied_hashes(addon: Path = ADDON) -> int:
    record = json.loads((addon / "FILE_HASHES.json").read_text(encoding="utf-8"))
    actual = {str(p.relative_to(addon)).replace("\\", "/") for p in source_files(addon)}
    expected = set(record) | {"FILE_HASHES.json"}
    if actual != expected:
        raise ValueError(f"File set differs: missing={expected - actual}, extra={actual - expected}")
    for relative, expected_hash in record.items():
        path = addon / relative
        if hashlib.sha256(path.read_bytes()).hexdigest() != expected_hash:
            raise ValueError(f"Original add-on bytes changed: {relative}")
    return len(record)


def version() -> str:
    tree = ast.parse((ADDON / "__init__.py").read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "bl_info" for t in node.targets):
            info = ast.literal_eval(node.value)
            return "_".join(str(x) for x in info["version"])
    raise ValueError("bl_info version not found")


def build(output: Path | None = None) -> Path:
    verify_supplied_hashes()
    output = output or ROOT / "dist" / f"PK01_ParkSport_Studio_{version()}.zip"
    output = output.resolve()
    if output == ADDON or ADDON in output.parents:
        raise ValueError("Output must be outside the source add-on directory")
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(output.suffix + ".tmp")
    try:
        with ZipFile(temporary, "w", compression=ZIP_DEFLATED, compresslevel=6) as archive:
            for path in source_files():
                relative = path.relative_to(ADDON.parent).as_posix()
                info = ZipInfo(relative, date_time=(2026, 9, 25, 0, 0, 0))
                info.compress_type = ZIP_DEFLATED
                info.external_attr = 0o100644 << 16
                archive.writestr(info, path.read_bytes(), compress_type=ZIP_DEFLATED, compresslevel=6)
        temporary.replace(output)
    finally:
        if temporary.exists():
            temporary.unlink()
    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="Optional destination ZIP file")
    args = parser.parse_args()
    target = build(args.output)
    print(f"Built: {target} ({target.stat().st_size / 1_000_000:.1f} MB)")
    print("Install this ZIP in Blender; engine runtime compatibility is not validated by this command.")
