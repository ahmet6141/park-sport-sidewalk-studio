# Changelog

## PK01 1.1.0 — FLOW sidewalks

- New default **FLOW** path style: path-following paving courses with symmetric edge cuts and no end slivers, jointed curb stones swept from a BULLNOSE / CHAMFER / SQUARE section, and junctions with curb returns and rounded dead ends. Border strips continue around the returns.
- Straight network links meander gently with zero offset and zero slope at both ends; the amplitude is clamped so the centre-line radius stays at least three path widths. Path end cuts are pinned to the design tangent so curves meet junction mouths without a wedge gap.
- Curb-return radius is reduced automatically where neighbouring junctions are close; identical junction layouts are instanced as one mesh.
- Lighting follows the real curved centre line; curved benches are nested in the grass of T/X junction curb returns.
- Higher-quality props built from new sweep/lathe primitives: straight bench with rounded timber slats and cast side frames, curved bench, turned light pole with swan-neck arm and disc luminaire, bollard and bin body.
- Socket connector (bridge) uses the FLOW builder when FLOW is selected.
- **CLASSIC** style keeps the unmodified SW01 1.0.1 core; its sidewalk geometry is byte-identical to 1.0.0 (regression-tested). `vendor/sw01_core.py` is unchanged.
- New pure-Python modules `curves.py`, `modeling.py`, `flow.py`; new tests in `tests/test_flow.py` (watertight solids, all 16 junction arm combinations, all paving patterns, mouth alignment, option validation).
- `tools/refresh_hashes.py` regenerates `FILE_HASHES.json` and `PUBLISH_MANIFEST.json` for a reviewed release.
- Still not validated inside Blender 4.5 or Unreal Engine 5.8.

## Repository packaging — 2026-09-25

- Organized the existing PK01 1.0.0 add-on with its SW01 1.0.1 dependency for source control.
- Preserved all original add-on files and license notices byte-for-byte.
- Added repository documentation, a deterministic ZIP builder, smoke tests and a first-publication helper.
- Did not change generator algorithms, fix application APIs, or validate Blender/Unreal runtime behavior.
