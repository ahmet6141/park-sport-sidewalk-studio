"""Build a deterministic, Blender-installable ZIP of the RD01 Road Studio add-on (stdlib only)."""
from __future__ import annotations
import argparse
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

ROOT = Path(__file__).resolve().parents[1]
ADDON = ROOT / 'rd01_road_studio'


def files() -> list[Path]:
    return sorted(p for p in ADDON.rglob('*')
                  if p.is_file() and '__pycache__' not in p.parts and p.suffix not in {'.pyc', '.pyo'})


def build(output: Path | None = None) -> Path:
    output = (output or ROOT / 'dist' / 'RD01_Road_Studio.zip').resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(output, 'w', ZIP_DEFLATED, compresslevel=6) as zf:
        for path in files():
            info = ZipInfo(path.relative_to(ROOT).as_posix(), date_time=(2026, 1, 1, 0, 0, 0))
            info.compress_type = ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            zf.writestr(info, path.read_bytes())
    return output


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path)
    print('Built:', build(parser.parse_args().output))
