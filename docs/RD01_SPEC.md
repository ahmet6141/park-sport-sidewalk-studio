# RD01 Road Studio — Architecture & Implementation Specification (v1, revision 2)

Blender 4.5 LTS add-on for game-ready roads, sidewalks, junctions, roundabouts and rural/highway pieces.
Pipeline: Blender 4.5 authoring → FBX → Substance 3D Painter (unique-UV kit and macro sets) / Substance 3D Designer (tiling, lane and trim materials) → Unreal Engine 5.4–5.8.

Status markers used throughout:
**[V]** verified in this environment (bpy 4.5.14 module, Python 3.11, numpy 1.26). **[S]** sourced in the research JSON. **[I]** inferred / design decision. **[UE?]** Unreal-side behaviour that still needs an in-editor smoke test (Unreal is not available here). **[SP?]** Substance-side behaviour that still needs a Painter/Designer check.

Prototype and check scripts (scratchpad, not repository code). Rev 1: `/tmp/claude-0/-home-user-park-sport-sidewalk-studio/8c18d72f-ca47-53b4-a9cb-4452b6c02c19/scratchpad/rd01_verify/{v1,v2,junction_proto,ra_proto}.py`. Rev 2: `/tmp/claude-0/-home-user-park-sport-sidewalk-studio/8c18d72f-ca47-53b4-a9cb-4452b6c02c19/scratchpad/rev2/nums.py` (every number recomputed in this revision), `.../rev2/skew.py` + `.../rev2/skew2.py` (skewed / asymmetric X-junction cores), `.../rev2/ra2.py` (roundabout leg core with the splitter-widened leg), `.../rev2/bchk.py` + `.../rev2/bchk4.py` (socket export, excluded-collection export, Geometry Nodes instancer), `.../rev2/sor.py` + `.../rev2/sor2.py` (SOR / mean-value harmonic solve), `.../rev2/trim.py` (trim-sheet layouts), `.../rev2/idprop.py` (ID-pointer custom properties). The rev-1 spec is backed up at `.../rev2/rd01_spec_rev1_backup.md`. Reviewer checks: `.../scratchpad/review_chk/api1–api4.py`.

---

## R. Revision 2 — how the two reviews were resolved

Every item of the tech-art review (T1–T34) and the engineering review (E1–E35) is resolved in the section named in the index below. Where the reviews conflicted, the option that keeps quality topology **and** stays implementable was chosen:

| # | Topic | Options in the reviews | Decision (and why) |
|---|---|---|---|
| R1 | Junction skew | T25: test ±30°, cap at ±15° if it fails. E12: cap at 15° now. | **Cap v1 at ±15°.** Measured in `rev2/skew.py` and `rev2/skew2.py`: ±30° skew gives a min corner angle of 18.1° (R_lip 15.5). ±15° gives 30.3°–57.4°. Mixed ±15° gives ≥ 47.3° with bisector Q placement. Orthogonal arms with radii 3/9/6/15 give 40.7°. The patch gate becomes ≥ 40° for orthogonal arms and ≥ 30° when skew is non-zero (§3.6). |
| R2 | Curb type changes along one closed sweep | T26: morph types over 1 m. E13: one type per island. | **One curb type per island in v1** (E13). The common z-matched curb column structure (T26) is specified for straight transitions only (§2.6), and closed-sweep type morphs move to v1.1. The fold rule takes the stricter T26 margin: `outline radius − w_curb ≥ 0.10 m`. |
| R3 | Draft vs height-field gate | E7: 1:19 draft, or a gate at 0.045. | **Keep the 1:20 draft. The gate is n_z ≥ 0.045 and is applied to `face_kind == TOP` only** (new QMesh buffer). Barrier dimensions stay as published, and floating-point margin is kept. |
| R4 | Harmonic solver | T8: SOR or CG with cotangent / mean-value weights. E12: fixed-order Gauss–Seidel with a residual stop. | **SOR in fixed vertex order (ω = 2/(1 + sin(π/n)), ≈ 1.85 at n = 40), with mean-value XY weights.** Mean-value weights are positive and have linear precision (the plane patch test holds to solver tolerance, measured ≤ 4.8e-6 m), and SOR suits their non-symmetric system, which CG does not. The stop is residual-based (1e-8 m), and a residual above 0.5 mm is an ERROR. |
| R5 | Lateral morph | T2: per-column `t_offset` plus a COLLAPSE superset. E13: a t-morph, or a constant MEDIAN_FLUSH section plus a transition. | **Per-column `t_offset` with a superset template (T2), used for roundabout legs and kit transitions.** A band that disappears ends in a *collapse row*: its columns weld onto their anchor column at one loop, and the last row closes with documented triangles (`pole:collapse`) that are either coplanar with their neighbours or ≤ 1 cm wide. An odd column reduction cannot be quad-only without spreading poles (boundary-parity argument, §2.6). When those triangles lie in one plane, the exported triangulation is identical to any quad alternative. |
| R6 | Raised medians at junctions | T3: median arms need the morph. | **Raised medians compile to a MEDIAN_FLUSH band in the paved grid plus a separate island solid (D11).** The flush columns run through the junction core as ordinary carriageway columns, so median arms need no morph. Noses and refuge cut-throughs are island operations (§3.6, §3.11). |
| R7 | DOUBLE roundabouts | T33: drop, or add ring markings. E13: same problems. | **Dropped from v1** (moved to the v1.1 backlog, together with spiral ring markings). |
| R8 | Ramp-zone trim V | T16: nominal pre-morph v, or a CURB_DROP band. | **Both, by zone.** Flare faces (0 < λ < 1) keep their band with the nominal pre-morph v. Faces where λ = 1 on both loops switch to the CURB_DROP band, with a seam at ramp0 / ramp1, which is where real dropped-kerb units start. |
| R9 | SOLID bottoms | T34: SKIRT default, or a coarse bottom. | **SKIRT is the default for every paved-surface piece**, and the importer sets "Generate distance field as if two-sided". SOLID stays opt-in (bridges, cut-aways), using T-ladder caps and the full bottom grid. |
| R10 | Barrier trim overflow | T12: a second sheet if needed. E15: a taller sheet or 512 px/m. | **The layout is generated from the hard-range maxima.** Barrier and rail sheets use the VEH density class (512 px/m) by default. Barriers use two sheets (NJ/F and SINGLE_SLOPE/VERTICAL). Sheet height is the next power of two ≥ the need, and overflow is an ERROR (§4.7). |
| R11 | Painter road kit TD | T1: road tiles at 512 px/m; curb, ramp and tactile at 1024 px/m. | **As T1, except that the full-width ramp tile is 512 px/m.** A 4.0 m × 3.07 m tile at 1024 px/m cannot fit a 4096 set with the required padding (4096 px + 2 pads > 4096). The 1024 px/m ramp detail lives in `Tile_RampInsert` (curb back → ramp top), the drop-curb units and the tactile pads. |
| R12 | Junction / roundabout UV0 | T1(c): macro-unique 64–128 px/m, or UDIM. | **MACRO (one 4096 set) is the default.** TD = the largest multiple of 8 px/m ≤ 128 that fits. 64–128 is the target. 48–63 is allowed with WARN `MACRO_TD_LOW`: the kit D35 4-leg roundabout is estimated at 56 px/m (≈ 3,080 m²). Below 48 is an ERROR (use UDIM). **UDIM at VEH density is opt-in**: about 1,000 m² at 512 px/m would need 16 × 4K tiles. |
| R13 | Trim U across welds | T9: u from one reference column per band. E4: `uv_origin_cols`. | **A per-band reference column with a per-band origin map `uv_origin: Mapping[str, float]`** (key = the band's reference tag). Joints stay radial, and a weld still carries the exact u. |
| R14 | Mask channels | T21: geometry-derived terms only, noise in UE, plus an edge-blend channel. T20: a lane blend mask. | **R wet, G grime, B edge blend. A = edge wear on trim, unique and concrete slots, and lane-detail weight on RD01_Asphalt** (per-slot semantics, CORNER domain, so values never bleed across slots). The noise term is removed. |
| R15 | Marking lift and bar splitting | T6: max(3 mm, deviation + 2 mm), and split bars at every triangle edge including diagonals. E11: loops at every road loop, lift = 3 mm + warp, plus a clearance check. | **Lines sit on template columns (T6).** **Bars are split at every road column and loop line and copy the underlying quad's diagonal (E11)**, so they stay quads; splitting at diagonals would create triangles. Instead, the deviation between the two piecewise-linear surfaces is evaluated **exactly** at every vertex of their overlay (which includes the diagonal crossings), and `lift = max(3 mm, deviation + 2 mm)`. `MARKING_CLEARANCE ≥ 1 mm` is an ERROR. |
| R16 | Socket names | T30: `SOCKET_<Tag>` parented to the mesh. E24: `ue_socket_name` in the manifest. | **Both.** The FBX writes `SOCKET_<Tag>` parented to the render mesh. The manifest carries `tag` and `ue_socket_name` (= the tag), and the importer canonicalises names. |

Item index (where each review item is resolved):
- **Tech-art:** T1 §6.2 · T2 §2.6, §3.8 · T3 §3.6 · T4 §2.1, §3.6, §3.8, §3.9 · T5 §3.1 · T6 §3.9 · T7 §3.3 · T8 §3.5 · T9 §4.2 · T10 §2.2, §4.2 · T11 §4.2, §3.9 · T12 §4.7 · T13 §4.4 · T14 §4.2, §4.4, §9.1 · T15 §4.4 · T16 §3.7 · T17 §7.5 · T18 §7.4, §7.8 · T19 §7.9 · T20 §4.3 · T21 §5.2 · T22 §3.12 · T23 §3.1, §3.10 · T24 §3.10 · T25 §3.6, §9.2 · T26 §2.6, §3.11 · T27 §9.1 · T28 §3.10, §7.8 · T29 §7.3 · T30 §5.3, §7.2 · T31 §5.4, §6.1 · T32 §6.2, §7.10 · T33 §3.8 · T34 §3.2, §7.8.
- **Engineering:** E1 §10.2 · E2 §10.1 · E3 §10.1 · E4 §3.2, §3.3, §3.4, §10.2 · E5 §3.1, §3.8 · E6 §4.2 · E7 §1.4, §2.3 · E8 §2.3 · E9 §2.4 · E10 §3.1 · E11 §3.9 · E12 §3.5, §3.6 · E13 §2.6, §3.8 · E14 §3.7 · E15 §4.7 · E16 §9.1 · E17–E20 §8.1 · E21 §7.2 · E22 §5.5, §7.2 · E23 §7.2 · E24 §7.2 · E25 §7.8 · E26–E29 §8.3 · E30–E33 §9.2, §9.3 · E34 §3.8, §7.2 · E35 §1.1, §10.1.

**New finding, verified in this revision [V] (`rev2/bchk4.py`).** `export_scene.fbx(collection=…)` on a collection that is **excluded** from the view layer writes the objects, but their transforms are **never evaluated**. Socket empties came out with no `Lcl Translation` / `Lcl Rotation` (identity). The same export from an included collection after `view_layer.update()` writes `Lcl Translation [400,0,0]` and `Lcl Rotation [0,0,−180]`. The temporary export collection must therefore be linked, **included** and updated (§7.2). `verify_fbx` compares socket transforms against the manifest.

---

## 0. Decisions that resolve conflicts between the research reports

| # | Topic | Conflict | Decision |
|---|---|---|---|
| D1 | FBX axes/units | PK01 uses `axis_forward='-Y'` and `FBX_SCALE_ALL` (a metre file with a 180° node rotation). The UE report asks for identity axes and a cm-native file. | **`axis_forward='Y', axis_up='Z', apply_scale_options='FBX_SCALE_NONE', apply_unit_scale=True, global_scale=1.0, bake_space_transform=True`**. **[V]** The header is Up=+Z, Front=−Y, Coord=+X, `UnitScaleFactor=1.0`, vertices are in cm, the mesh Model has no `Lcl`, and a socket at 4 m parented to the mesh is written as `Lcl Translation (400,0,0)` (rev2). Never combine bake_space_transform with any other axis pair, because that corrupts socket orientation (research [V]). |
| D2 | Smoothing element | FACE (PK01 / Blender report) vs EDGE (UE report) | **`mesh_smooth_type='EDGE'`** **[V]** writes `LayerElementSmoothing ByEdge`. |
| D3 | Vertex colour encoding | FLOAT+LINEAR vs BYTE+SRGB | **BYTE_COLOR, CORNER domain, values written through `color_srgb`, exported with `colors_type='SRGB'`** **[V]**, so the bytes arrive unchanged. The active attribute plus `prioritize_active_color=True` decides which layer is written first **[V]**. |
| D4 | Tangents | `use_tspace` True vs False | **`use_tspace=True` always.** The exporter asserts `LayerElementTangent` after export **[V]**. |
| D5 | Triangulation | exporter `use_triangles` vs modifier | **Never `use_triangles=True`.** A temporary `TRIANGULATE` modifier is used (`quad_method='FIXED'`, `min_vertices=4`, `keep_custom_normals=True`). **[V]** FIXED splits a quad along **v0–v2**. The kernel chooses the diagonal by rotating the quad's vertex order, following the FIELD rule (§3.3). |
| D6 | Normals | WEIGHTED_NORMAL modifier vs kernel | **The kernel computes the final custom normals** (analytic for sweeps, face-strength fans for patches), with exactly one normal per (vertex, smooth fan) **[V auto-sharp]**. |
| D7 | UV channel contract | UV1 lightmap vs UV1 trim | **UV0 `UV0_Main`** is Painter / macro / copy of UV1. **UV1 `UV1_Tile`** is world / path / trim. **UV2 `UV2_Lane`** is lane-aligned asphalt detail (T20). **UV3 `UV3_Light`** is present in the BAKED profile only. Painter reads UV0 only. |
| D8 | Texel density | 1024 vs 512 | **Three TD classes:** **PED 1024 px/m** (curbs, gutters, markings, ramps, tactile), **VEH 512 px/m** (road tiles, barriers, rails), and **MACRO 48–128 px/m, target 64–128** (junction, roundabout and highway macro UV0). The scene preset "512 px/m (vehicle)" moves PED to 512. The class and the density are written per set and per sheet into the manifest. |
| D9 | Slot / material naming | `MI_RD01_*` vs `RD01_*` | Blender material = FBX slot = Painter Texture Set = **`RD01_<Set>`**. In UE: **`MI_RD01_<Set>`** (macro pieces: `MI_RD01_<Set>__<Piece>`, a child MI). Painter outputs `T_RD01_<Set>_BC/_N/_ORM`. |
| D10 | Socket direction | — | **Every port socket's +X points out of the piece.** FBX object `SOCKET_<Tag>`, parented to the render mesh (one render mesh per FBX). A straight piece has `Start` at (0,0,0) with yaw 180° and `End` at (L,0,0) with yaw 0°. |
| D11 | Islands and raised medians | conforming holes vs separate solids | **Splitter islands, refuge islands and raised medians are separate closed solids** that sit on a continuous paved grid and are sunk 5 cm into it. The paved grid carries a MEDIAN_FLUSH band under a raised median. The central roundabout island is concentric and welded into the radial sweep. |
| D12 | Curbs | welded vs separate | **Both.** Standard pieces weld curb, gutter and sidewalk into one top surface (TRIM UVs). *Curbless* variants cut the curb footprint exactly to the DIN unit's toe and back lines, and the Painter kit's UNIQUE curb units fill that gap (§6.2). |
| D13 | Markings | decal vs raised mesh | Default **RAISED**: opaque strips lifted ≥ 3 mm above the *triangulated* surface (§3.9), merged into the piece mesh **in the kernel**, slot `RD01_Marking`, with section collision disabled in UE. Profile **DECAL**: flat strips 10 mm above the surface, exported as separate non-Nanite assets. |
| D14 | UV packing | bpy ops vs own | **An own pure-Python MaxRects packer with no rotation by default** (rotation only for islands flagged isotropic). bpy UV operators are never used in the build path. |
| D15 | Closure | SOLID vs SKIRT | **SKIRT by default** for streets, junctions, roundabouts and spline roads. SOLID is opt-in. |
| D16 | Drive side | — | `drive_side` ∈ {RHT, LHT} is part of every region preset (UK = LHT, all others RHT). Every handed rule is written once for RHT and mirrored (§3.6, §3.8, §3.9). |
| D17 | Export location | timestamped folders vs fixed paths | **A stable `<base>/RD01_<scene>/current/`, replaced atomically, with every export also archived to `revisions/<stamp>/`** (§7.3). |
| D18 | Section changes along a road | — | **Lateral morph:** both end sections compile to one column superset, each column's t is interpolated with a stated taper law, and a vanishing band ends in a collapse row (§2.6). |

---

## 1. Package layout, responsibilities and core data model

### 1.1 Repository placement and the hash lock

```
park-sport-sidewalk-studio/
  pk01_park_studio/                 untouched (hash-locked by FILE_HASHES.json)
  rd01_road_studio/                 NEW add-on / extension package
  tests/test_rd01_*.py, tests/rd01_*.py, tests/data/rd01_*   NEW (unittest; pytest is not installed)
  tools/build_rd01.py, tools/rd01_preview.py                 NEW
  docs/RD01_*.md                    NEW
```

**Hash lock (E35).** `tests/test_repository.py::test_publication_manifest` checks the size and sha256 of all 112 files listed in `PUBLISH_MANIFEST.json`. These include `README.md`, `README_TR.md`, `CHANGELOG.md`, `CONTRIBUTING.md`, `.gitignore`, `.gitattributes`, `docs/PUBLISH_TR.md`, `docs/previews/*`, `tests/test_flow.py`, `tests/test_pk01_blender.py`, `tests/test_repository.py`, `tools/__init__.py`, `tools/build_addon.py` and `tools/refresh_hashes.py`. Rules:
- **No RD01 work package edits a listed file.** New files are not affected, because the test only iterates the manifest's entries.
- A release that must touch a listed file (for example a README link) runs `python3 tools/refresh_hashes.py` **in the same reviewed commit**. That script also rewrites `pk01_park_studio/FILE_HASHES.json`.
- `.gitignore` ignores `*.fbx`, `*.zip`, `*.blend` and `/dist/`. Tests therefore write their outputs to `tempfile` directories, and no RD01 data file uses those extensions.

### 1.2 Package tree

```
rd01_road_studio/
  __init__.py                 bl_info + register()/unregister(); NO bpy import at module import time
  blender_manifest.toml       extension manifest (id rd01_road_studio, blender_version_min "4.5.0",
                              [permissions] files = "Write FBX, JSON and SVG exports to the chosen folder",
                              paths_exclude_pattern = ["__pycache__/", "*.pyc"])
  LICENSE.txt  README.md
  core/                       PURE PYTHON, stdlib only (math, dataclasses, enum, json, hashlib, fractions). No bpy, no numpy.
    __init__.py
    types.py                  Vec2/Vec3/RGBA8/Edge aliases, Issue, Level                      (shared, WP0)
    specs.py                  every frozen spec / option dataclass shared across modules (§10.2)  (WP0)
    surface.py                Surface Protocol: z_at, normal_at, point                          (WP0)
    vec.py                    vector helpers, Newell normal, frames, quaternions, Blender→UE transform
    enums.py                  Part, Role, FaceKind, Closure, UVKind, UVMode, TDClass, Detail, DriveSide, slot registry, ID palette
    qmesh.py                  QMesh, builders, merge, hashing, components
    piece.py                  Piece / Port / Socket / SplineMeshInfo / Instance / Placement / BuiltObject
    template.py               ZRule / Column / Segment / Crossfall / MorphState / ProfileTemplate (data + evaluate)  (WP0)
    standards.py              Param registry, region presets (incl. drive_side), validation
    section.py                band model compile → ProfileTemplate; transitions (superset + lateral morph)
    profiles.py               curb / DIN unit / barrier / W-beam / island / side-slope / ditch / arris generators (2D)
    detail.py                 Detail level → generator parameters (arris segments, chord factor, spacing factor)
    rail.py                   Rail (plan arc length, line/arc/clothoid/Bezier), fillets, stations, superelevation, vertical checks
    sweep.py                  open-section sweep, closed-profile sweep, lathe, closures, ladder caps / curtains
    normals.py                analytic sweep normals, face-strength fans, FIELD diagonal orientation
    trisurface.py             TriSurface: exact queries on the chosen v0–v2 triangles (implements Surface)
    street.py                 build_street (straight / transition), build_precast_unit (curb & barrier units)
    validate.py               topology / UV / naming / port validators → Issue list + Metrics
    uv.py                     UV1 tiling rules, UV2 lane UVs, rebase, unique islands & unwrap, pack_texture_set
    pack.py                   MaxRects packer (single bin, UDIM multi-bin), padding, determinism
    trimsheet.py              trim-sheet layout generator, JSON I/O, guide SVG
    masks.py                  RD01_ID and RD01_Mask colours (geometry-derived terms only)
    manifest.py               manifest dict builder (pure), schema constants, UE-space conversion
    finalize.py               finalize_piece: merge markings → prune slots → diagonals → normals → UVs → masks → validate
    ramps.py                  perpendicular ramp stations / morph / compliance
    markings.py               dash fitting, line / bar / stop / yield strips on TriSurface, island clipping
    islands.py                splitter / refuge / median islands, rounded noses, cut-throughs
    collision.py              UCX hull generation
    patch.py                  Coons grids, SOR harmonic z with mean-value weights, O-grid disc, extrude-down
    junction.py               T / X junction builder
    road.py                   build_spline_road, chunking, ground-following side slopes, port lead-ins
    rural.py                  rural/highway section presets, guardrail (rail sweep + instances)
    roundabout.py             roundabout builder
    kit.py                    kit catalogue: PieceDef list + build_piece(), kit section solver, Painter set table
  blender/                    bpy layer (imported lazily from register())
    __init__.py               aggregates each module's CLASSES; register/unregister with a re-entrancy guard
    props.py  presets.py  ui.py  ops_build.py  ops_texturing.py  ops_export.py  ops_validate.py
    curve_input.py            Blender curve → CurveSpline data (no Rail dependency)
    ground.py                 ground object → height function (BVH ray cast)
    mesh_io.py                QMesh ↔ bpy Mesh, bpy-side content hash
    materials.py              RD01_* preview materials (exact-name reuse)
    scene.py                  ownership, staging, safe replace, orphan purge
    instancer.py              Geometry Nodes instancer object per owner (display only)
    export_fbx.py             FBX writer + verify_fbx
    export_substance.py       per-set Painter FBX (+ _high, + macro), painter.json, guides
    export_folder.py          stable current/ folder, atomic swap, revisions/
  unreal/
    RD01_Import.py            UE5 editor importer (Interchange first, legacy fallback)
    RD01_Materials.py         builds the M_RD01_* masters and material functions via MaterialEditingLibrary
  data/
    presets/sections/*.json   cross-section presets (EU/TR/DE/UK/US street, RQ11, RQ11 flat, RQ31, US rural…)
    presets/junctions/*.json  junction presets;  presets/roundabouts/*.json
    trim_sheets.json          GENERATED by trimsheet.generate_layouts(); a test asserts byte-equality
    id_palette.json           Part → RD01_ID colour (mirrors enums.py; a test asserts equality)
    kit_budgets.json          per-piece triangle budgets (§6.1)
    painter/RD01_UE.spexp     Painter export preset → T_RD01_<Set>_BC/_N/_ORM [SP?]
```

Rules:
- `core/*` imports cleanly under `python3 -I` without bpy. This is tested in a **subprocess** (§9.2).
- `blender/*` may import `core`, never the reverse.
- **Relative imports only** inside the package (`from ..core import qmesh`), never `import rd01_road_studio…`. As an extension the package loads as `bl_ext.user_default.rd01_road_studio`, so an absolute self-import would create a second module copy. A source-scan test enforces this (E19).
- Core is deterministic. It never uses `random`, `time`, `uuid` or the builtin `hash()` (salted per process), and an AST scan enforces this. Seeds come from `hashlib.blake2b(name.encode(), digest_size=8)`. Sets are sorted before hashing or iteration. Dicts are iterated in sorted key order wherever the order reaches output.
- Units: metres and radians internally (degrees only in the UI and presets); slopes are ratios (0.025 = 2.5 %).

### 1.3 Coordinate conventions

- Blender world: right-handed, Z up, metres. `unit_settings.scale_length` must be 1.0; otherwise the build operators refuse.
- Piece frame: **+X = running direction, +Y = left, +Z = up.** The top surface is ordered with t (lateral, + left) increasing. **s is always plan (horizontal) arc length.**
- Straight and spline-deformable pieces: origin on the centreline at s = 0, at the crown's finished surface height.
- Junctions and roundabouts: origin at the junction centre, at the priority road's crown height. Ports lie on the 0.5 m grid, and on the 4 m grid for kit pieces (§5.4).
- Kit curb units: origin at the start of the curb toe. The road face faces −Y.
- Blender → UE **[V math]**: location (x,y,z) m → (100x, −100y, 100z) cm; quaternion (w,x,y,z) → (w,−x,y,−z); yaw_UE = −yaw_Blender.
- Drive side: RHT means traffic keeps right. A handed rule is written for RHT, and LHT applies the mirror t → −t to the rule (not to the geometry).

### 1.4 Core mesh data model — `QMesh`

```python
# core/enums.py
class Part(IntEnum):            # → RD01_ID colour (sRGB bytes), Painter ID mask
    HIDDEN=0; LANE=1; SHOULDER=2; GUTTER=3; CURB_FACE=4; CURB_ARRIS=5; CURB_TOP=6; SIDEWALK=7
    RAMP=8; TACTILE=9; MARKING=10; ISLAND_TOP=11; APRON=12; VERGE=13; GRAVEL=14; DITCH=15
    BARRIER_FACE=16; BARRIER_TOP=17; RAIL=18; POST=19; CAP=20; MEDIAN_FLUSH=21
ID_COLOURS = {HIDDEN:(0,0,0), LANE:(255,0,0), SHOULDER:(255,128,0), GUTTER:(255,255,0), CURB_FACE:(0,255,0),
  CURB_ARRIS:(0,128,255), CURB_TOP:(0,255,255), SIDEWALK:(0,0,255), RAMP:(128,0,255), TACTILE:(255,0,255),
  MARKING:(255,255,255), ISLAND_TOP:(0,128,0), APRON:(128,64,0), VERGE:(128,255,0), GRAVEL:(192,160,96),
  DITCH:(128,0,0), BARRIER_FACE:(0,0,128), BARRIER_TOP:(0,128,128), RAIL:(192,192,192), POST:(64,64,64), CAP:(128,128,0),
  MEDIAN_FLUSH:(255,96,96)}
class Role(IntEnum): VISIBLE=0; ARRIS=1; CAP=2; HIDDEN=3; COLLAPSE=4; MARKING=5
class FaceKind(IntEnum): TOP=0; SKIRT=1; BOTTOM=2; CAP=3; SIDE=4; MARKING=5    # E7: set by builders
class Closure(str, Enum): OPEN='OPEN'; SKIRT='SKIRT'; SOLID='SOLID'
class UVKind(str, Enum): WORLD_XY='WORLD_XY'; PATH='PATH'; TRIM='TRIM'; PLANAR='PLANAR'
class UVMode(str, Enum): TILING='TILING'; UNIQUE='UNIQUE'; UDIM='UDIM'; MACRO='MACRO'
class TDClass(str, Enum): PED='PED'; VEH='VEH'; MACRO='MACRO'           # 1024 / 512 / 48–128 px/m (target 64–128)
class Unwrap(str, Enum): PLANAR='PLANAR'; UNROLL='UNROLL'; HEIGHTFIELD='HEIGHTFIELD'; POLAR='POLAR'
class DriveSide(str, Enum): RHT='RHT'; LHT='LHT'
class Detail(str, Enum): HIGH='HIGH'; LOD0='LOD0'; LOD1='LOD1'; LOD2='LOD2'
UV_LAYERS = ('UV0_Main', 'UV1_Tile', 'UV2_Lane')          # + 'UV3_Light' only in the BAKED profile
COLOR_ID, COLOR_MASK = 'RD01_ID', 'RD01_Mask'
POLE_TAGS = ('pole:ogrid', 'pole:collapse')               # documented poles (validator whitelist)
```

```python
# core/qmesh.py   (types from core/types.py)
@dataclass
class QMesh:
    name: str
    verts: list[Vec3] = field(default_factory=list)
    faces: list[tuple[int, ...]] = field(default_factory=list)   # 4 ids; 3 only at pole:collapse rows; CCW from outside
    slots: list[str] = field(default_factory=list)
    face_slot: list[int]; face_part: list[int]; face_role: list[int]; face_kind: list[int]
    face_strength: list[int]                                     # 1 strong (large flat), 0 weak (arris/chamfer)
    face_island: list[int]                                       # UV0 island group (-1 = none yet)
    face_rule: list[int]                                         # index into uv_rules (UV1 rule of the face)
    uv_rules: list[UVRule] = field(default_factory=list)
    param: list[tuple[Vec2, ...]]                                # per corner (u_m, v_m): run metres on the band's
                                                                 #   reference column, profile metres from the band anchor
    lane_param: list[tuple[Vec2, ...]] | None = None             # per corner (u_m, v01) for UV2_Lane, None = copy UV1
    uv: dict[str, list[tuple[Vec2, ...]]] = field(default_factory=dict)
    corner_normals: list[tuple[Vec3, ...]] | None = None
    id_color: list[tuple[RGBA8, ...]] | None = None
    mask: list[tuple[RGBA8, ...]] | None = None
    sharp: set[Edge] = field(default_factory=set)
    seams: set[Edge] = field(default_factory=set)
    vtags: dict[int, str] = field(default_factory=dict)          # 'port:Arm0', 'col:R.flow_line', 'pole:ogrid', ...
    meta: dict = field(default_factory=dict)

    def slot(self, name: str) -> int
    def add_vert(self, p: Vec3) -> int
    def add_face(self, vids, slot, part, role=Role.VISIBLE, kind=FaceKind.TOP, strength=1,
                 rule: int = -1, param=None, lane_param=None) -> int
    def add_grid(self, ids: list[list[int]], cell: Callable[[int, int], CellInfo]) -> list[int]
    def edge_faces(self) -> dict[Edge, list[int]]
    def components(self) -> list[list[int]]
    def append(self, other: 'QMesh', offset: Vec3 = (0., 0., 0.)) -> dict[int, int]   # remaps rules and slots
    def transformed(self, matrix4) -> 'QMesh'
    def prune_slots(self) -> None                                 # drop unused slots, keep registry order (E22)
    def tri_count(self) -> int                                    # Σ(len(f) − 2) — manifest 'tris' (E22)
    def bounds(self) -> tuple[Vec3, Vec3]
    def geometry_hash(self) -> str                                # kernel-side regression hash (blake2b, sorted sets)
    def uv_hash(self, layer: str = 'UV0_Main') -> str
    def check_buffers(self) -> None
```

Invariants (asserted by `check_buffers` and the validator):
1. Faces are quads. Triangles exist **only** in collapse rows (§2.6): one vertex carries `pole:collapse`, and the triangle is either coplanar with its neighbouring faces within 0.05° or its band is ≤ 1 cm wide at the last full loop. **N-gons are forbidden** (one n-gon makes the FBX exporter drop all tangents **[V]**).
2. Vertices are welded by construction. Builders share ids through explicit node lists and never weld by coordinates.
3. **Height field (E7, R3):** every face with `face_kind == TOP` on a road, junction or roundabout piece has n_z ≥ 0.045. Near-vertical profile segments get a 1:20 draft (n_z = 0.0499). SKIRT/BOTTOM/CAP/SIDE faces are exempt.
4. In each smooth fan, all corners at a vertex carry the same custom normal (D6).
5. Each quad's chosen triangulation diagonal is v0–v2 (D5).
6. Every layer in `UV_LAYERS` exists on every face. `id_color` and `mask` exist on every face.

`CellInfo = (slot, part, role, kind, strength, rule, param_fn)`.

---

## 2. Cross-section model

### 2.1 Parameter registry (`core/standards.py`)

```python
@dataclass(frozen=True)
class Param:
    default: float
    hard: tuple[float, float]          # outside → ERROR (refuse to build)
    soft: tuple[float, float] | None   # outside → WARN
    unit: str                          # 'm', 'ratio', 'deg', 'km/h', 'count'
    source: str
REGIONS = ('EU', 'TR', 'DE', 'UK', 'US')            # EU = neutral default
@dataclass(frozen=True)
class RegionPreset: region: str; drive_side: DriveSide; marking_patterns: Mapping[str, str]; params: Mapping[str, float]
def param(name: str, region: str = 'EU') -> Param
def region_preset(region: str) -> RegionPreset
def validate_params(values: Mapping[str, float], region: str) -> list[Issue]
```
`Issue` lives in `core/types.py` (E1).

Defaults and ranges. Hard limits are per region; soft ranges only warn. The rev 1 rows are unchanged except where noted. New rows are marked ★.

| name | EU | TR | DE | UK | US | hard | soft | source |
|---|---|---|---|---|---|---|---|---|
| ★ drive_side | RHT | RHT | RHT | **LHT** | RHT | — | — | [S] |
| lane_width | 3.25 | 3.25 | 3.25 | 3.25 | 3.35 | 2.75–3.75 | 3.00–3.50 (urban) | NACTO, RASt, AASHTO [S] |
| lane_width_rural | 3.50 | 3.50 [I] | 3.50 | 3.65 | 3.66 | 3.00–3.75 | 3.25–3.75 | RAL RQ11, RAA [S] |
| crossfall | 0.025 | 0.025 | 0.025 | 0.025 | 0.020 | 0.010–0.040 | — | [S] |
| gutter_width | 0.50 | 0.50 | 0.50 | 0.30 | 0.61 | 0.0–0.90 | — | [S] |
| gutter_slope | 0.06 | 0.06 | 0.06 | 0.06 | 0.06 | 0.02–0.083 | — | [S] |
| curb_reveal (barrier) | 0.12 | 0.15 | 0.12 | 0.125 | 0.15 | 0.10–0.225 (TR ≤ 0.15) | — | [S] |
| curb_reveal (mountable) | 0.10 | 0.10 | 0.10 | 0.10 | 0.10 | 0.075–0.15 | — | [S] |
| curb_reveal (flush/roll) | 0.03 | 0.03 | 0.03 | 0.006 | 0.0 | 0.0–0.03 | — | [S] |
| curb_top_width | 0.15 | 0.15 | 0.15 | 0.125 | 0.15 | 0.10–0.20 | — | [S] |
| curb_batter_setback | 0.03 | 0.03 | 0.03 | 0.025 | 0.025 | 0.02–0.06 (barrier) | — | [S] |
| arris_radius | 0.012 | 0.012 | 0.015 | 0.012 | 0.012 | 0.006–0.025 | — | [I]/DIN [S] |
| arris_segments | 2 | 2 | 2 | 2 | 2 | 1–4 (HIGH: 8) | — | [I] |
| sidewalk_width | 3.00 | 3.50 | 3.00 | 3.00 | 3.66 | TR ≥ 2.25, UK ≥ 1.5, US ≥ 1.22, ≤ 8.0 | 2.0–5.0 | [S] |
| ★ kit sidewalk width (solved, §5.4) | 3.07 | 3.57 | 3.07 | 3.30 | 3.865 | as above | — | [I] |
| sidewalk_cross_slope | 0.015 | 0.015 | 0.015 | 0.015 | 0.015 | 0.01–0.02 (UK 0.025) | — | [S] |
| ramp_slope_max | 1/12 | 0.08 | 1/12 | 1/12 | 1/12 | 0–max | — | [S] |
| ramp_width | 1.22 | 1.22 | 1.22 | 1.20 | 1.22 | 0.90 (TR) / 0.915–3.0 | — | [S] |
| flare_slope_max | 0.10 | 0.10 | 0.10 | 1/11 | 0.10 | ≤ 0.10 | — | [S] |
| ramp_landing | 1.22 | 1.22 | 1.22 | 0.90 | 1.22 | ≥ 0.90 | — | [S] |
| dws_depth | 0.60 | 0.60 | 0.60 | 0.80 | 0.61 | 0.60–1.20 | — | [S] |
| dws_setback | 0.0 | 0.30 | 0.0 | 0.0 | 0.0 | 0.0–0.30 | — | [S] |
| lip_max | 0.006 | 0.006 | 0.0 | 0.006 | 0.006 | 0–0.006 | — | [S] |
| curb_return_radius (toe) | 6.0 | 6.0 | 6.0 | 6.0 | 6.0 | 0.6–15.0 | 3–10 | [S] |
| ★ curb_return_radius_rural (paved edge) | 12.0 | 12.0 | 12.0 | 12.0 | 12.0 | 6.0–25.0 | — | [I] |
| crosswalk_bar / gap | 0.50/0.50 | 0.50/0.50 | 0.50/0.50 | 0.50/0.50 | 0.61/0.61 | bar 0.30–0.715 | — | [S] |
| crosswalk_length | 3.0 | 3.0 (4.0 if V>60) | 4.0 | 2.4 [I] | 3.05 | 1.83–6.0 | — | [S] |
| stop_line_width / offset | 0.50/1.0 | 0.50/1.0 | 0.50/1.0 | 0.30/1.0 [I] | 0.61/1.22 | 0.20–0.61 / 1.0–9.0 | — | [S] |
| marking_width (lane line) | 0.12 | 0.12 | 0.12 | 0.10 | 0.15 | 0.10–0.30 | — | [S] |
| shoulder_paved_width / slope | 2.50/0.04 | 2.50/0.04 [I] | 2.50/0.04 | 3.30/0.04 | 3.05/0.04 | 2.0–3.66 / 0.02–0.06 | Δ to lane ≤ 0.06 | [S] |
| bankett_width / slope | 1.50/0.06 | 1.50/0.06 | 1.50/0.06 | 1.00/0.06 | 1.20/0.06 | 1.0–2.5 / 0.04–0.12 | — | [S] |
| edge_strip | 0.50 | 0.50 | 0.50 | 1.00 | 0.0 | 0.0–1.0 | — | [S] |
| embankment_slope (V:H) | 1:1.5 | 1:1.5 | 1:1.5 | 1:2 | 1:4 | 1:1 – 1:6 | US > 1:3 → guardrail warn | [S] |
| embankment_height (no ground source) | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 0.0–10.0 | — | [I] |
| ★ cut_slope (V:H) | 1:1.5 | 1:1.5 | 1:1.5 | 1:2 | 1:3 | 1:1 – 1:6 | — | [I] |
| design_speed | 50 / 80 / 120 (urban/rural/highway) | | | | | 20–130 | — | [S] |
| e_max | 0.06 | 0.06 | 0.06 | 0.07 | 0.08 rural / 0.04 urban | 0.0–0.08 | — | [S] |
| rel_grade_max (Δs) | 0.005 | 0.005 | 0.005 | 0.005 | 0.005 | 0.001–0.009 | — | [S] |
| ★ taper_ratio (lateral shift, average 1:n) | urban 10 / rural 25 / highway 50 | same | same | same | same | 5–100 | — | [I] |
| ★ clothoid A (rural / highway) | R/2 / 2R/3 | same | same | same | same | R/3 – R | — | RAA [S per T23] |
| ★ roundabout entry / exit width (single lane) | 4.5 / 5.0 | same | same | same | same | entry ≥ 4.3 (ERROR) | entry 4.3–5.5 | FHWA [I] |
| ★ edge_blend_inset | 0.25 | 0.25 | 0.25 | 0.25 | 0.25 | 0.20–0.30 | — | T21 [I] |

Imperial values are stored exactly (inch = 0.0254, ft = 0.3048).

### 2.2 Band model (`core/section.py`)

```python
# core/enums.py (WP0): BandKind, CurbType, BarrierShape, CrownMode; PAVED/UNPAVED/COLLAPSIBLE sets
class BandKind(str, Enum):
    LANE='LANE'; EDGE_STRIP='EDGE_STRIP'; SHOULDER_PAVED='SHOULDER_PAVED'; BANKETT='BANKETT'
    GUTTER='GUTTER'; CURB='CURB'; SIDEWALK='SIDEWALK'; VERGE='VERGE'
    MEDIAN_RAISED='MEDIAN_RAISED'; MEDIAN_BARRIER='MEDIAN_BARRIER'; MEDIAN_FLUSH='MEDIAN_FLUSH'
    EMBANKMENT='EMBANKMENT'; DITCH='DITCH'
class CurbType(str, Enum): BARRIER='BARRIER'; MOUNTABLE='MOUNTABLE'; ROLL='ROLL'; FLUSH='FLUSH'
class BarrierShape(str, Enum): NJ='NJ'; F='F'; SINGLE_SLOPE='SINGLE_SLOPE'; VERTICAL='VERTICAL'
class CrownMode(str, Enum): CENTRE='CENTRE'; ONE_SIDED_LEFT='ONE_SIDED_LEFT'; ONE_SIDED_RIGHT='ONE_SIDED_RIGHT'; MEDIAN_EDGES='MEDIAN_EDGES'
PAVED = {LANE, EDGE_STRIP, SHOULDER_PAVED, MEDIAN_FLUSH, GUTTER}
UNPAVED = {BANKETT, VERGE, EMBANKMENT, DITCH}
COLLAPSIBLE = {LANE, EDGE_STRIP, SHOULDER_PAVED, MEDIAN_FLUSH}     # carriageway level, one plane per half (§2.6)
```
`Band`, `CrossSection` and `LineSpec` are frozen dataclasses in `core/specs.py` (E1):
```python
@dataclass(frozen=True)
class LineSpec: kind: str; offset: float; width: float; pattern: str   # kind 'CENTRE'|'LANE'|'EDGE'; offset from the band's inner edge
@dataclass(frozen=True)
class Band: kind: BandKind; width: float = 0.0; p: Mapping[str, float | str] = field(default_factory=dict)
            lines: tuple[LineSpec, ...] = ()      # longitudinal markings carried by this band
            band_id: str = ''                     # stable id (e.g. 'R.lane1'), set by the compiler if empty
@dataclass(frozen=True)
class CrossSection:
    name: str; region: str
    right: tuple[Band, ...]; left: tuple[Band, ...]; median: tuple[Band, ...] = ()
    crown: CrownMode = CrownMode.CENTRE
    closure: Closure = Closure.SKIRT              # D15
    slab_depth: float = 0.25; skirt_depth: float = 0.50; max_lateral: float = 1.75
    def symmetric(self) -> bool; def section_hash(self) -> str
    @staticmethod
    def from_json(d: dict) -> 'CrossSection'; def to_json(self) -> dict
```

How bands compile. **Ref** is the band's UV reference column: u is measured along the run on this column for every column of the band, so joints stay radial on curves (T9). **Anchor** is where v = 0.

| kind | columns emitted (outward) | z rule | part / slot | UV1 (ref · anchor) | UV2_Lane |
|---|---|---|---|---|---|
| LANE | equal splits (auto ceil(w/max_lateral), min 2), **plus the two edge columns of every line it carries** (`mk<k>a`, `mk<k>b`, T6) | CARRIAGEWAY | LANE / RD01_Asphalt | WORLD_XY 4.0 | per lane: u = run/8 m, v 0→1 from the driver's right edge |
| EDGE_STRIP | 1 per ≤ max_lateral + line edge columns | CARRIAGEWAY | SHOULDER / RD01_Asphalt | WORLD_XY | continues the outer lane's v (> 1) |
| SHOULDER_PAVED | ceil(w/1.5) + line edge columns | ROLLOVER | SHOULDER / RD01_Asphalt | WORLD_XY | as EDGE_STRIP |
| MEDIAN_FLUSH | splits ≤ max_lateral + line edge columns; the centre column is the crown | CARRIAGEWAY | MEDIAN_FLUSH / RD01_Asphalt | WORLD_XY | v = 0.5 (lane weight 0) |
| GUTTER | lip → flow line (+ a lane column 0.5 m from the flow line if w < 0.3) | ATTACHED_SLOPE | GUTTER / **RD01_TrimGutter** | TRIM 'GUTTER' (ref toe · anchor flow line) | copy UV1 |
| CURB | toe (hard) → face top → arris pts (soft) → top front → top back | ATTACHED | CURB_* / RD01_TrimCurb | TRIM 'CURB_<type>' (ref toe · anchor toe) | copy UV1 |
| SIDEWALK | curb back → [`dws0` if dws_setback > 0] → `dws1` → `ramp_top` → splits ≤ 1.5 → back of walk | ATTACHED_SLOPE (rises outward) | SIDEWALK / RD01_Concrete | **PATH** 2.0 m (ref curb back · anchor curb back) (T10) | copy UV1 |
| BANKETT | `blend` column (edge_blend_inset outside the paved edge) + ceil(w/1.5) | ATTACHED_SLOPE | GRAVEL / RD01_Gravel | WORLD_XY 4.0 | copy UV1 |
| VERGE | ≤ 1.0 m splits | ATTACHED_SLOPE | VERGE / RD01_Grass | WORLD_XY 4.0 | copy UV1 |
| MEDIAN_RAISED | **compiles to MEDIAN_FLUSH** in the paved grid, plus an island child (R6, §3.11) | — | — | — | — |
| MEDIAN_BARRIER | hardstrip edge → toe … top … toe → hardstrip | ATTACHED (vertical) | BARRIER_* / RD01_TrimBarrier[SV] | TRIM per face (ref toe) | copy UV1 |
| EMBANKMENT | hinge → crest arc (3 seg) → slope (k pts, ≤ 1.0 m) → toe arc (3 seg) → catch → apron; **k fixed per template** | ATTACHED, or ground-solved per station (§3.10) | VERGE / RD01_Grass | PATH 4.0 (ref hinge) | copy UV1 |
| DITCH | foreslope → bottom (rounded, 3 seg) → backslope → apron | ATTACHED | VERGE + DITCH / RD01_Grass + RD01_Soil | PATH 4.0 (ref ditch bottom) | copy UV1 |

- **Line edge columns (T6).** Longitudinal markings sit on planar template faces between their own edge columns. A centre line on a CENTRE crown is carried by the crown column plus the two innermost lane bands (`±w/2`). Lines never cross a template column, and markings never need a surface sample between columns.
- **Edge-blend column (T21).** For every paved band whose outward neighbour is UNPAVED with no curb in between, the compiler emits a `blend` column at `edge_blend_inset` (0.25 m) *inside* the paved edge (tag `X.blend_in`). The first UNPAVED band emits a column 0.25 m outside the edge (`X.blend_out`). The B mask channel (§5.2) ramps between them.
- **Drive side.** UV2_Lane v runs from the *driver's* right edge, so it mirrors under LHT. Line patterns come from the region preset.

### 2.3 Compiled profile (`core/template.py`, WP0; compiled by `section.compile_section`, WP1)

```python
@dataclass(frozen=True)
class ZRule:
    kind: str          # 'CARRIAGEWAY' | 'ATTACHED' | 'ATTACHED_SLOPE' | 'ROLLOVER' | 'GROUND'
    anchor: int = -1; dz: float = 0.0; slope: float = 0.0
@dataclass(frozen=True)
class Column:
    t: float           # lateral offset, + = left; strictly increasing; Δt ≥ 0.002 between kept columns
    z0: float; zr: ZRule; hard: bool
    tag: str           # 'crown', 'R.lip', 'R.flow_line', 'R.toe', 'R.face_top', 'R.arris1', 'R.top_front', 'R.curb_back',
                       # 'R.dws0', 'R.dws1', 'R.ramp_top', 'R.back', 'R.mk0a', 'R.blend_in', 'L.*', 'M.*', ...
    side: int          # -1 right, 0 centre/median, +1 left
    band: str          # band_id of the band that emitted it
@dataclass(frozen=True)
class Segment:
    part: Part; slot: str; role: Role; strength: int
    uv: UVRule         # UV1 rule; UVRule is in core/specs.py (E1)
    island_group: int  # UV0 island group (changes at every hard column and slot change)
    band: str          # band_id → reference column via ProfileTemplate.ref_col(band)
    lane: int          # lane index for UV2_Lane (-1 = not a lane face)
@dataclass(frozen=True)
class Crossfall: left: float; right: float       # outward fall per half (+ = falls outward); crown: (+c, +c)
@dataclass(frozen=True)
class MorphState:                                 # per-station modifiers; identity when empty
    side_lambda: Mapping[int, float] = {}         # ramps: side → λ ∈ [0,1]
    gutter_slope: Mapping[int, float] = {}        # ramps: side → gutter slope override
    t_offset: Mapping[int, float] = {}            # column → lateral offset added to template t (T2, E13)
    dz: Mapping[int, float] = {}                  # column → added dz (curb reveal morphs)
    z_abs: Mapping[int, float] = {}               # column → absolute z (ground catch points, §3.10)
    collapsed: frozenset[int] = frozenset()       # columns welded onto their collapse anchor at this station
class ProfileTemplate:                            # data + evaluation live in WP0 so WP2 can sweep fixture templates (E1)
    columns: tuple[Column, ...]; segments: tuple[Segment, ...]; tags: Mapping[str, int]
    section_hash: str; closure: Closure; slab_depth: float; skirt_depth: float; drive_side: DriveSide
    def evaluate(self, cf: Crossfall, morph: MorphState | None = None,
                 anchor_z: Callable[[int], float] | None = None) -> list[tuple[float, float]]
        # (t, z) per column; anchor_z overrides the z of the CARRIAGEWAY anchor columns (junction harmonic lip z, E4)
    def reach(self) -> float                       # max |t + t_offset| over the template's morph range
    def slice(self, tag_from: str, tag_to: str) -> 'ProfileTemplate'   # E4: edge half-profiles, T far side, ring edge
    def ref_col(self, band: str) -> int            # UV reference column of a band
    def band_cols(self, band: str) -> range
# core/section.py (WP1)
def compile_section(section: CrossSection, ramp: RampSpec | None = None,
                    split_counts: Mapping[str, int] | None = None) -> ProfileTemplate
```

Compilation algorithm:
1. Emit the median first (centred on t = 0), then each half outward. Right-half bands get negative t and left-half bands positive t.
2. Each band emitter receives `(t_start, anchor_column, side)` and returns columns and segments. `split_counts[band_id]` overrides the automatic split count, so all junction arms can share one count (E12).
3. **Arris points (E8).** `curb_section` produces arris points. A point is **dropped** when its Δt to the previous kept column is < 2 mm. **No arris is emitted** when the effective radius `r = min(arris_r, reveal/2, top_width/3)` is < 3 mm (for example FLUSH reveal 0); the corner then becomes a single soft column. `section_hash` is computed **after** dropping.
4. Concatenate (right reversed) + crown + left. Soft columns from different emitters that lie within 2 mm of each other (for example an edge-line edge and `blend_in`) are **merged**, and the merged column carries all their tags. Then assert that t is strictly increasing with Δt ≥ 2 mm. Profile segments steeper than 1:20 get a **1:20 draft** (n_z = 0.0499 ≥ the 0.045 gate, R3).
5. Hard flags: a column is hard if the angle between its adjacent segments is > 30° and it is not inside an arris run. Arris columns are soft (weak arris faces, strong neighbours). Crown and lip breaks (< 5°) are soft. A slot change on soft geometry is a seam without a sharp edge.
6. **Ramp columns** are always present in sidewalks: `R.dws0` (only if dws_setback > 0), `R.dws1 = curb back + dws_setback + dws_depth` and `R.ramp_top`. All three are included in `section_hash` (E14). `ramp_top` offset from the toe: `run = (reveal − lip − w_curb·sw_cs)/(m − sw_cs)` (EU: 1.717 m → 1.537 m behind the curb back; US reveal 0.15: 2.157 m → 1.982 m) **[V nums.py]**.
7. Validation runs every hard-range endpoint combination of the curb parameters (2⁶ combinations per region) in `test_rd01_section` (E8).

### 2.4 Crossfall, crown and superelevation (E9)

- CARRIAGEWAY z: `z(t) = −cf.left·(t − t_c)` for t ≥ t_c and `z(t) = −cf.right·(t_c − t)` for t < t_c (t_c = crown position, per carriageway for MEDIAN_EDGES).
- ATTACHED columns translate with their anchor (sidewalks, curbs and barriers never tilt).
- ROLLOVER (paved shoulder): low side `f_sh = max(f_default, f_lane)`; high side `f_sh = min(f_default, f_lane + 0.06)`.
- Superelevation (`rail.superelevation`), with c = normal crown slope:
  1. **Target.** `e(R) = e_max·(2·Rmin/R − (Rmin/R)²)`, clamped to [0, e_max], with `Rmin = V²/(127·(e_max + f(V)))` and f(V) taken from the metric table {30:.28, 40:.23, 50:.19, 60:.17, 70:.15, 80:.14, 90:.13, 100:.12, 110:.11, 120:.09, 130:.08} [S/I]. The signed target bank is `b_t(s) = e(R(s))` where e ≥ c, else −c (normal crown). On clothoids R(s) varies, so the bank develops along the spiral (§3.1).
  2. **Per-direction dilation.** `b_L(s) = max(−c, max_{s′: κ(s′)>0} (b_t(s′) − |s − s′|·Δs_max/a))`, and `b_R` likewise over κ < 0, where a is the distance from the rotation axis (CENTRE) to the carriageway edge.
  3. **Mapping (signed bank b ∈ [−c, e]).** For a left turn alone: `cf.right = −b_L`, `cf.left = max(c, b_L)`. A right turn mirrors this. Both contributions are **superposed as deviations from the normal crown**: `cf.left = max(c, b_L) − b_R − c`, `cf.right = max(c, b_R) − b_L − c`. This is continuous by construction on reverse curves.
     Test vectors (left turn, b_R = −c), given as (cf.left, cf.right): b = −c → (c, c); b = 0 → (c, 0); b = c → (c, −c); b = e → (e, −e).
  4. Warnings: R < Rmin(V); resultant slope `sqrt(g² + e²) > 0.09`; grade > 0.06 (rural/highway) or 0.08 (urban); grade < 0.007 inside reversal zones; **`SUPER_REVERSE_OVERLAP`** when b_L > −c and b_R > −c at the same s (short reverse tangent), reported with the resulting maximum relative gradient.
  5. **Before ports (T22):** over the last `L_lead` metres before a port (§3.12), b is forced to −c (normal crown) and the grade to a constant. The dilation treats a port as a target of −c.
- v1 rotation axis: CENTRE only.

### 2.5 Curb geometry (`profiles.curb_section`, `profiles.din_curb_profile`)

```python
def curb_section(kind: CurbType, reveal: float, top_width: float, setback: float, arris_r: float,
                 arris_seg: int, side: int, sw_cs: float) -> list[ProfilePt]      # ProfilePt in core/specs.py
def din_curb_profile(kind: str = 'HB15/30', detail: Detail = Detail.LOD0, region: str = 'EU') -> ClosedProfile
```
- BARRIER: toe (0,0) hard → face line to (setback, reveal) → fillet r = min(arris_r, reveal/2, top_width/3) between the face and top lines (the top slopes with sw_cs) → arris points (Δt < 2 mm dropped; none if r < 3 mm) → top front → top back (`top_width + setback` from the toe).
- MOUNTABLE: setback = reveal (45°), arris_r = max(arris_r, 0.025). ROLL / FLUSH: reveal ≤ 0.03, arris clamped to reveal/2, so FLUSH has no arris.
- `w_curb` = setback + top_width (0.18 m EU default).
- **Kit DIN unit** (closed profile): height 0.30, base 0.18, buried front 0.15, Radschräge 0.15 with 0.03 setback, arris r 0.015, back arris 0.005 [S DIN 483]. Units also get a **4 mm end chamfer** (T32): the end loop is the profile inset by 4 mm (offset polygon) at the end station, joined to the full profile 4 mm along the run by weak chamfer faces. This holds for LOD0 and HIGH (HIGH uses a 2-segment rounded chamfer); LOD1/LOD2 drop it.

### 2.6 Section transitions and lateral morph (`section.compile_transition`) — T2, E13, D18

```python
@dataclass(frozen=True)
class TransitionMap:                               # core/specs.py
    cols: tuple[tuple[str, str], ...]              # one half, inner → outer: (tag in A, tag in B); '' = absent at that end
    switch_at: float = 0.5                         # ξ where part/slot of re-purposed segments changes (forced loop + seam)
    mirror: bool = True                            # the other half uses the mirrored map
class TransitionTemplate:
    tpl: ProfileTemplate                           # column superset; tags from A, B-only columns tagged 'B:<tag>'
    collapse_anchor: Mapping[int, int]             # column → column it welds onto where it is absent
    def state(self, xi: float) -> MorphState       # t_offset, dz, collapsed for ξ ∈ [0, 1]
    def segment_at(self, j: int, xi: float) -> Segment
    def max_shift(self) -> float                   # max |t_B − t_A| over all columns
    def length_for(self, taper_ratio: float) -> float   # L = max_shift · taper_ratio, rounded up to the piece grid
def compile_transition(a: CrossSection, b: CrossSection, tmap: TransitionMap | None = None) -> TransitionTemplate
```

Rules:
1. **Pairing.** The pairing is automatic when both sections have the same band *kinds* in the same order per half, with lane counts allowed to differ. Columns are paired by band and index. Extra LANE / MEDIAN_FLUSH bands and extra columns pair with `''`. Any other combination needs an explicit `TransitionMap` (the kit ships one for every transition piece). Split counts are unified with `compile_section(split_counts=max)` so paired bands have equal column counts.
2. **Interpolation (taper law).** `t_j(ξ) = t_j^A + w(ξ)·(t_j^B − t_j^A)` with `w(ξ) = (1 − cos πξ)/2`. This is C1 with zero lateral slope at both ends, so lip, curb and back-of-walk lines leave and enter neighbouring pieces straight. The maximum lateral slope is `(π/2)·max_shift/L`. Curb reveal morphs use the same `w` through `MorphState.dz`. z rules are evaluated on the morphed t.
3. **Monotonicity (T2).** At every station, the non-collapsed columns are strictly increasing with Δt ≥ 2 mm (asserted per loop). A collapsing band's width is ≥ 2 mm at every loop before its collapse loop. If it is not, the sampler moves the last full loop back.
4. **Collapse row.** A band that is absent at one end is born from, or collapses onto, its `collapse_anchor` (the paired column on its inner side). At the end loop its columns **are the anchor vertex** (same vertex id, not a coordinate weld). The faces of the last row whose two far corners merged become triangles, and the merged vertex is tagged `pole:collapse`. These faces get Role.COLLAPSE (aspect-exempt). Allowed when either (a) the band is COLLAPSIBLE, in which case its faces lie in one crossfall plane (the crown column is never collapsed and a crown-straddling band such as MEDIAN_FLUSH splits into one triangle per half), or (b) the band's lateral extent at the last full loop is ≤ 1 cm (cosine law with loop spacing h ≤ L/10). Otherwise it is an ERROR (`COLLAPSE_NOT_PLANAR`).
   *Why triangles:* a quad-only patch has an even number of boundary edges. Removing one column across one row gives an odd count (2 + 1 + 1 + 1 = 5 for a 2→1 reduction), so a pure-quad reduction must spread poles across neighbouring columns and the port loop. The coplanar triangle is shading-identical to the exported triangulation of any quad alternative.
5. **Re-purposed segments.** A segment whose part/slot differs between A and B (GUTTER ↔ EDGE_STRIP, CURB_TOP ↔ GRAVEL, SIDEWALK ↔ BANKETT) switches at the forced loop `ξ = switch_at`, with a UV0 seam and a UV1 rule change there.
6. **Uses.** Kit transition pieces (below), roundabout legs (§3.8), and arm narrowing at junctions (an arm whose port section differs from its throat section).

Kit transition pieces:

| piece | A → B | map | length |
|---|---|---|---|
| `SM_RD01_Street_2Lto4L_3600` | Street_2L (half 7.0) → Street_4L (half 10.5) | automatic: lane 2 per half pairs with `''` and collapses onto the lane-1 edge column at A; the edge bands translate by 3.25 m and the sidewalk widens 3.07 → 3.32 | urban taper 1:10 × max shift 3.5 m = 35 m → 36 m |
| `SM_RD01_Street_UrbanToRural_1200` | Street_2L (EU) → Rural_RQ11_Flat (half 3.50 + 0.50 + 1.50 + 1.50 = 7.0) | explicit: `crown↔crown`, lane splits ↔ lane splits, `lip↔lane_edge`, `''↔blend_in`, `toe↔paved_edge`, `face_top/arris*/top_front ↔ ''` (collapse onto toe; reveal → 0 so extent → 0), `curb_back↔blend_out`, `dws1↔bankett_split`, `ramp_top↔bankett_outer`, splits ↔ verge splits, `back↔verge_outer`; switch_at 0.5 | 12 m |

The superset template of a transition piece hashes both end sections. Its ports carry the A and B `section_hash` respectively, so ports still match ordinary pieces exactly.

### 2.7 Barrier profiles (`profiles.barrier_section`)

`top = base − 2·((brk − reveal)/tan(lo) + (H − brk)/tan(up))`.

| shape | H | base | reveal | break | lo° | up° | top | face girth toe→top arris [V nums.py] |
|---|---|---|---|---|---|---|---|---|
| NJ | 0.813 | 0.610 | 0.076 | 0.330 | 55 | 84 | 0.152 | 0.872 |
| F | 0.813 | 0.610 | 0.076 | 0.254 | 55 | 84 | 0.243 | 0.855 |
| SINGLE_SLOPE | 1.067 | 0.610 | 0 | — | 79.2 | — | 0.203 | 1.086 |
| VERTICAL | 0.90 | 0.25 | — | — | 87.14 (1:20 draft) | — | 0.20 | 0.901 |

The reveal gets a 1:20 draft. Slope breaks get a 2-segment soft rounding with r = 0.025, and top arrises a 2-segment r = 0.02. The toe is hard. The trim band is anchored at the toe, and its u reference is the toe column.

---

## 3. Algorithms

### 3.1 Rails, alignment and station sampling (`core/rail.py`) — T5, T23, E5, E10

```python
@dataclass(frozen=True)
class RailSample:
    s: float; p: Vec3                 # s = PLAN (horizontal) arc length (E10)
    t_h: Vec2; left: Vec2             # analytic unit horizontal tangent / left normal
    kappa: float; dkappa: float       # signed horizontal curvature (+ = turning left) and dκ/ds
    grade: float                      # dz/ds
class Rail:
    length: float; closed: bool
    @classmethod
    def from_bezier(cls, segs, flatness: float = 0.002, knot_tol_deg: float = 0.5,
                    knot_policy: str = 'ERROR', min_radius: float = 0.0) -> tuple['Rail', list[Issue]]
    @classmethod
    def from_polyline(cls, pts, closed: bool = False) -> 'Rail'
    @classmethod
    def line(cls, length, start=(0, 0, 0), heading=0.0) -> 'Rail'
    @classmethod
    def arc(cls, centre, radius, a0, a1) -> 'Rail'
    @classmethod
    def clothoid(cls, start: Vec3, heading: float, k0: float, k1: float, length: float) -> 'Rail'   # T23
    @classmethod
    def compose(cls, parts) -> 'Rail'                 # G1 asserted at joins (≤ 0.5°)
    def at(self, s: float) -> RailSample
    def offset_point(self, s: float, t: float, z: float) -> Vec3
def fillet_polyline(pts, radius: float, clothoid_A: float | None = None) -> list[Rail]
def sample_stations(rail: Rail, spec: SamplingSpec, reach_left: float, reach_right: float,
                    cf_rate: Callable[[float], float] | None = None) -> list[float]
def chunk_ranges(stations, chunk_max: float = 64.0) -> list[tuple[int, int]]
def superelevation(rail: Rail, tpl: ProfileTemplate, spec: SuperSpec,
                   ports: Sequence[float] = ()) -> Callable[[float], Crossfall]
def vertical_checks(rail: Rail, design_speed: float) -> list[Issue]
```

**Bezier evaluation (E10).** A table `s → (segment, u)` is built by adaptive Gauss–Legendre integration of |B′_xy(u)|, refined until the plan length error is < 0.1 mm per segment. `at(s)` inverts the table with Newton steps on u. Tangent, curvature and grade come from the **analytic** derivatives B′, B″ (κ = (x′y″ − y′x″)/|B′_xy|³, grade = z′/|B′_xy|), never from the flattened polyline. The flattened polyline (≤ 2 mm) is used only for display and spatial queries.
- **Zero-length handles:** when |B′(u)| < 1e-9 at a segment end, the limit direction of B″ (then B‴) is used and INFO `DEGENERATE_HANDLE` is reported.
- **Knots:** a tangent break > `knot_tol_deg` (0.5°) is an ERROR `KNOT_KINK` with `knot_policy='ERROR'` (default). With `'FILLET'`, a circular fillet of `min_radius` is inserted (ERROR if it does not fit). VECTOR/FREE handles that create kinks are therefore never swept silently.

**Clothoids (T23).** `Rail.clothoid` evaluates Fresnel integrals (series for |x| < 4, else the asymptotic form; pure Python). `fillet_polyline(..., clothoid_A)` builds a symmetric spiral–arc–spiral with `L_s = A²/R` and spiral angle `τ = L_s/(2R)`. This requires 2τ ≤ Δ (the deflection). Otherwise A is reduced toward R/3, and if 2τ still exceeds Δ the result is ERROR `CLOTHOID_NO_FIT`. Rural presets use A = R/2 and highway presets 2R/3. Urban streets stay line+arc. The superelevation runoff lands on the spiral automatically, because b_t(s) follows κ(s) there (§2.4).

**Equidistribution sampling (T5, E5 — corrected).**
1. Dense pre-sample every 0.05 m and compute the required **centreline** spacing:
   `h(s) = min(max_spacing, zone_max(s), θ(R_out)/|κ|, warp_tol/(w_lat·|de/ds|))`,
   where `R_out = 1/|κ| + reach_convex` is the radius of the outermost column on the convex side, and `θ(R) = 2·acos(1 − chord_tol/R)`. Between stations the outer column turns through h·|κ|, so its sagitta stays ≤ chord_tol exactly when h·|κ| ≤ θ(R_out).
2. Smooth h with a 3-tap max-preserving filter (neighbour ratio ≤ 1.5).
3. `φ(s) = ∫ ds/h(s)`, `N = ceil(φ(L))`, stations at φ = k·φ(L)/N. Forced stations are inserted exactly, and neighbours closer than min_spacing are removed (forced stations win).
4. **Worked example [V nums.py]:** R = 6 m, reach 7 m, 1 cm tolerance → R_out = 13 m → θ(13) = **4.495°** → h = θ·R = **0.471 m** on the centreline (outer chord 1.02 m, sagitta 1.00 cm). The rev-1 formula `R_out·θ(R_out)` gave 1.02 m and a 4.7 cm sagitta. For reach 7 m: R = 8 → 0.584 m, R = 25 → 1.250 m, R = 50 → 1.873 m, all with a 1.00 cm outer sagitta.
5. **Shared station sets** (junction n_k, roundabout ring stations) are computed for the **largest-radius column** of everything swept on them (E5). Example: the rev-1 roundabout rule (N_θ chosen at R_o = 17.5 m) gives 96 stations and a 1.15 cm sagitta at R_o + 4 m. Choosing at R_o + 4.5 m gives 108 stations and 0.91 cm [V nums.py].

**Rail checks.** ERROR: concave-side fold `1/|κ| ≤ reach_concave + 0.5`; length < 1 m; NaN; closed splines (v1). For **closed outlines** (islands): every inward column offset d must satisfy `d ≤ r_local − 0.10` (R2). WARN: grade/speed checks (§2.4).

**Vertical alignment (T23).** `vertical_checks` samples g(s) every 0.5 m.
- A **grade break** is |Δg| > 0.005 within < 1.0 m. It produces WARN `GRADE_BREAK` (no vertical curve).
- A vertical curve is a run where g changes monotonically. It has K = L/(100·|Δg|), and WARN `K_CREST_LOW` / `K_SAG_LOW` fires when K < K_min(V).
- K_min table (AASHTO GDHS 2011 metric, **[I] recalled — recheck against the source in WP12**): crest {30:2, 40:4, 50:7, 60:11, 70:17, 80:26, 90:39, 100:52, 110:74, 120:95, 130:124}; sag {30:6, 40:9, 50:13, 60:18, 70:23, 80:30, 90:38, 100:45, 110:55, 120:63, 130:73}.

### 3.2 Sweep of an open section (`core/sweep.py`)

```python
# SweepSpec is in core/specs.py
@dataclass(frozen=True)
class SweepSpec:
    closure: Closure = Closure.SKIRT                 # D15
    cap_start: bool = True; cap_end: bool = True     # SOLID: T-ladder caps; SKIRT: end curtains (free ends only)
    uv_origin: Mapping[str, float] = field(default_factory=dict)   # band_id → u origin (m) on the band's ref column (R13)
    uv_dir: int = +1                                 # +1: u grows with s; −1: perimeter traversal runs against s (§4.2)
    uv_scale: Mapping[str, float] = field(default_factory=dict)    # band_id → U scale (port phase fit, ≤ 1 %)
    world_uv: bool = True
    diagonal_policy: str = 'FIELD'                   # 'FIELD' | 'MIRROR_T' (§3.3)
    ports: tuple[str, str] = ('', '')                # port names at start/end; '' = free end → curtain/cap
@dataclass
class SweepResult:
    mesh: QMesh; grid: list[list[int]]; stations: list[float]
    end_loops: tuple[list[int], list[int]]
    ref_u: dict[str, list[float]]                    # band_id → u (m) per loop on its reference column (for welds)
def sweep_section(rail, tpl, stations, crossfall, spec: SweepSpec,
                  morph: Callable[[float], MorphState] | None = None,
                  anchor_z: Callable[[float, int], float] | None = None,   # E4: (s, column) → lip z from a junction field
                  shared_start: list[int] | None = None, shared_end: list[int] | None = None,
                  mesh: QMesh | None = None, name: str = '') -> SweepResult
```

Construction:
1. Loop i at station s_i evaluates `tpl.evaluate(crossfall(s_i), morph(s_i), anchor_z=lambda j: anchor_z(s_i, j))` and gives `P_ij = rail.offset_point(s_i, t_j, z_j)`. Collapsed columns reuse their anchor's vertex id (§2.6). `shared_start`/`shared_end` reuse the given ids (welds to cores and edge bands).
2. Top quads: corners `a=(i,j), b=(i+1,j), c=(i+1,j+1), d=(i,j+1)`, CCW from above, `face_kind TOP`. Each corner gets
   - `param = (u_m, v_m)`, where `u_m = uv_origin[band] + uv_dir·uv_scale[band]·(3D arc length along the band's reference column up to loop i)` (the same value for every column of the band, which keeps joints radial, T9), and `v_m` = 3D profile distance from the band anchor (the *nominal pre-morph* distance in ramp zones, §3.7);
   - `lane_param` for lane faces (§4.3).
3. Closures:
   - **OPEN**: top only. Arm sweeps and edge bands *inside* junctions and roundabouts are always OPEN. The piece applies its closure once over the whole top surface (E4), so there are never double bottoms.
   - **SKIRT** (default): one quad column down from each outer edge column to `z_edge − skirt_depth` (`face_kind SKIRT`, role HIDDEN, PATH UV with u along the run and the per-side reverse flag of §4.2). **Free ends get an end curtain (T22):** T-ladder quads (top_j, top_{j+1}, top_{j+1} − d, top_j − d) with d = skirt_depth, sharing their outer bottom vertices with the skirts (`face_kind CAP`, PLANAR UV in the end plane, §4.2). Ends whose `spec.ports` entry is non-empty (a port) stay open.
   - **SOLID** (opt-in): skirts down to `z_base(s) = min_j z_ij − slab_depth`, a bottom grid with one vertex per top column (`face_kind BOTTOM`, faces −Z, PLANAR UV u = x, v = −y), and T-ladder end caps (`face_kind CAP`).
4. Sharp edges along every hard column, around skirts, caps and curtains.
5. Seams (UV0) at island-group changes, at re-purposed segment switches (§2.6), at cap/skirt/bottom/curtain boundaries, and at island length cuts (§4.4).
6. Chunking (spline roads): sweep the **whole** road once, compute normals and UVs globally, then split at `chunk_ranges`. Boundary loops are duplicated with identical positions, normals, UV1 and UV2.

### 3.3 Normals and diagonals (`core/normals.py`) — T7, E4

```python
def sweep_corner_normals(res: SweepResult, tpl, rail, crossfall, morph=None, anchor_z=None, h: float = 0.05) -> None
def fan_corner_normals(mesh: QMesh, fixed: Mapping[tuple[int, int], Vec3] | None = None) -> None
    # fixed key = (vertex, face): the corner of `face` at `vertex`; every corner in that corner's fan takes the normal.
def orient_diagonals(mesh: QMesh, policy: str = 'FIELD', field_xy: Callable[[float, float], float] | None = None,
                     field_st: Callable[[int], Callable[[Vec3], float]] | None = None, face_ids=None) -> None
```

**Analytic sweep normals** (exact and identical on shared loops):
- Profile normals per column: a soft column takes the length-weighted average of its strong adjacent segments (all segments if none is strong), and a hard column gets one normal per side.
- `D_prof = left·τ_t + Z·τ_z` and `D_s = (t_h·(1 − κ·t), grade) + Z·∂z/∂s`, with ∂z/∂s from a central difference of the *template evaluation* (including morph and anchor_z). n = normalize(D_s × D_prof).
- Skirts, curtains, bottoms and caps get flat face normals.

**Face-strength fan normals** (patches): fans are split by sharp edges and boundaries. A fan's normal is the area-weighted Newell normal of its STRONG faces if it contains any, otherwise of all its faces. **`fixed`** is keyed by (vertex, face), so a hard-column vertex can hold two fans. It is applied at **every loop shared between a sweep and a patch**: ports, arm throats, edge-band welds and ring throats. There the analytic sweep normals win, which removes shading breaks at welds (E4).

**Diagonals — FIELD rule (T7).** For each quad, compute the midpoints of both diagonals. Pick the diagonal whose midpoint z is closer to the smooth field at that XY:
- sweeps: the exact template evaluation at the midpoint's (s, t), including superelevation transitions and morphs;
- patches: `z_p(x, y) + h̄`, where z_p is the analytic priority crown function and h̄ the bilinear harmonic correction.
If the two differ by < 0.1 mm (planar quads), the tie-break is MIRROR_T (left half a–c, right half b–d), then the lower vertex id. The quad's vertex order is then rotated so that the chosen diagonal is v0–v2. A crown fold therefore always follows a diagonal that lies on the crown, and fold directions no longer alternate in wet-road reflections.

### 3.4 Closed-profile sweeps, lathe and precast units (`sweep.sweep_closed`, `sweep.lathe`, `street.build_precast_unit`)

```python
# ClosedProfile, ProfilePt in core/specs.py
def zmatch_profile(p: ClosedProfile) -> ClosedProfile
def sweep_closed(rail: Rail, prof: ClosedProfile, stations, slot: str, caps: bool = True, closed_rail: bool = False,
                 end_chamfer: float = 0.0, name: str = '') -> SweepResult
def lathe(profile_rz: Sequence[tuple[float, float]], segments: int, slot: str, caps: str = 'OGRID',
          name: str = '') -> SweepResult                      # E4: bollards (a lathe, not a torus)
```
- **Z-ladder caps**: the profile splits into two z-monotone chains, and `zmatch_profile` inserts the other chain's z levels into each chain before sweeping. Caps are PLANAR in the end plane in a right-handed frame facing outward: `e2 = +Z`, `e1 = e2 × n_cap` (T14).
- **End chamfer** (units, T32): with `end_chamfer = 0.004` the first and last loops use the inset profile (offset 4 mm inward) and sit 4 mm inside the piece ends, and the chamfer faces are weak.
- **Closed rails** (island outlines): the first and last loops are the same vertices, and there are no caps. **One curb type per closed sweep (R2).** The fold rule is `outline radius − w_curb ≥ 0.10 m`; for example the 0.30 m splitter tail works with a BARRIER curb (w 0.18 → 0.12 ✓) but not with a MOUNTABLE curb (0.30).
- **Lathe**: revolves an (r, z) profile about +Z with `segments` divisible by 4. Endpoints with r = 0 are replaced by `disc_ogrid` caps, and the 4 valence-3 poles are tagged `pole:ogrid`.

### 3.5 Patch toolkit (`core/patch.py`) — T8, E12

```python
def resample(poly, params) -> list[Vec3]
def coons(bottom, right, top, left) -> list[list[Vec3]]
def orient_patch(grid) -> list[list[Vec3]]
def laplace_smooth(grid, fixed, iters: int = 0)                       # off by default
def mean_value_weights(xy: Sequence[Vec2], nbrs: Sequence[Sequence[int]], i: int) -> dict[int, float]
def harmonic(xy: Sequence[Vec2], nbrs: Sequence[Sequence[int]], fixed: Mapping[int, float],
             omega: float | None = None, tol: float = 1e-8, max_sweeps: int = 20000) -> tuple[list[float], float]
    # returns (values, max residual)
def disc_ogrid(centre, radius, segments, inner: float = 0.45) -> tuple[list[Vec3], list[tuple[int, int, int, int]], list[int]]
    # third item = the 4 pole vertex ids (callers tag 'pole:ogrid')
def extrude_down(mesh, top_faces, base_z, slot) -> None              # SOLID opt-in only (R9)
```

**Harmonic z solve (R4).**
- **Weights:** mean-value XY weights on the edge-connected 1-ring, ordered by angle: `w_ij ∝ (tan(α_{j−1}/2) + tan(α_j/2))/|x_j − x_i|`, normalised. They are positive for fold-free patches (a gated property), have linear precision, and do not depend on grid grading, which removes the dense-region bias of uniform weights.
- **Solver:** SOR in ascending vertex order with `ω = clamp(2/(1 + sin(π/n)), 1.5, 1.95)`, where n is the largest grid dimension (≈ 1.85 at n = 40).
- **Stop:** max residual `|h_i − Σ w_ij h_j|` < 1e-8 m. If the residual is still > 0.5 mm after `max_sweeps`, the result is ERROR `HARMONIC_NOT_CONVERGED`; between tol and 0.5 mm it is WARN.
- **Measured [V rev2/sor2.py]:** 40×40 uniform and graded, and 60×60 graded grids converge in 125–253 sweeps (0.26–1.44 s pure Python). The plane **patch test** reproduces the plane with a max error ≤ 4.8e-6 m. A residual stop of 1e-5 m was measured to leave 4.6 mm of error at 60×60, which is why the tolerance is 1e-8.
- **Patch test in `test_rd01_patch`:** boundary z from a plane → interior error ≤ 1e-5 m.

### 3.6 T and X junctions (`core/junction.py`) — T3, T4, T25, E12

```python
# core/specs.py
@dataclass(frozen=True)
class CrosswalkSpec: length: float = 3.0; bar: float = 0.5; gap: float = 0.5; edge_min: float = 0.25; edge_max: float = 0.75
                     setback: float = 1.0      # throat → crosswalk start; auto-pushed by the ramp rule (§3.7)
                     style: str = 'ZEBRA'      # 'ZEBRA' | 'CONTINENTAL' | 'TRANSVERSE'
@dataclass(frozen=True)
class ArmSpec: section: CrossSection; heading_deg: float; length: float = 6.0
               crosswalk: CrosswalkSpec | None = CrosswalkSpec(); ramps: RampSpec | None = None
               stop_line: bool = True; lane_lines: str = 'SOLID_APPROACH'
               port_section: CrossSection | None = None   # arm narrows/widens to this at the port (§2.6)
               median_nose_gap: float = 1.0               # median nose tip ≥ this from the crosswalk edge (junction side)
@dataclass(frozen=True)
class CornerSpec: curb_radius: float = 6.0; sidewalk_mode: str = 'AUTO'   # 'AUTO' | 'SQUARE' | 'CONCENTRIC'
@dataclass(frozen=True)
class JunctionSpec:
    name: str
    arms: tuple[ArmSpec | None, ArmSpec | None, ArmSpec | None, ArmSpec | None]   # slots 0/90/180/270°
    corners: tuple[CornerSpec, CornerSpec, CornerSpec, CornerSpec]
    priority: int = 0; port_grid: float = 0.5; closure: Closure = Closure.SKIRT; detail: Detail = Detail.LOD0
    curbless: bool = False                     # D12 / §6.2(b)
    uv_mode: UVMode = UVMode.TILING            # TILING | MACRO | UDIM
    drive_side: DriveSide | None = None        # None → region preset
def build_junction(spec: JunctionSpec) -> Piece
```

**v1 limits (ERROR when violated):**
- X needs 4 arms. T needs 3 arms, with the missing slot opposite a present arm.
- **Skew ≤ 15°** from the slot (R1). Kit pieces use 0°.
- Opposite arms have equal carriageway column counts, MEDIAN_FLUSH columns included.
- Arm sections are symmetric.
- **Edge structure (T3):** any half-profile outward of the carriageway edge column is allowed — curb + sidewalk, paved shoulder, Bankett, verge, embankment or ditch. All arms of one junction share the same *band-kind sequence* in their edge profiles (widths may differ), so mixed urban/rural junctions are v1.1.
- Raised medians are MEDIAN_FLUSH plus an island (R6).

**Decomposition: central quad + arm patches + edge bands** (prototypes `junction_proto.py`, `rev2/skew2.py`).
1. **Lip lines.** The *lip* is the arm's carriageway edge column (urban: gutter lip; rural: paved edge). The fillet radius at the lip is `R_lip = curb_radius + gutter_width` (urban, curb radius at the toe), or `curb_return_radius_rural` (rural, 12 m default).
2. **Fillets.** Each corner (k, k+1) gets a circle of radius R_lip tangent to arm k's left lip line and arm k+1's right lip line, giving centre C, tangent points and the fillet arc. A missing slot (T) uses the priority road's far lip line **B**.
3. **Throats.** `σ_k = max(station of T_k^L, station of T_k^R)`, with a straight lip extension from the nearer tangent point. Port distance `D_k = snap_up(σ_k + length_k, port_grid)`.
4. **Counts.**
   - `m_k` = carriageway segments of arm k (unified across all arms with `split_counts`).
   - `n_k = max(2, ⌈φ_half/θ(R_lip)⌉, ⌈depth_k⌉)` with **`depth_k = (half-fillet arc length + straight extension)/1.0 m`** (E12). The edge columns lie at radii < R_lip, so θ is evaluated at R_lip, which is the largest radius on these stations (E5). Both half-fillets adjacent to arm k use n_k.
5. **Central quad corners Q — bisector placement.** Start at the fillet mid-angle. Then iterate 12 times: `Q_k ← C_k + R_k·b̂_k`, where b̂_k is the bisector of the central-quad angle at Q_k (toward Q_{k−1} and Q_{k+1}), clamped to the middle 60 % of the fillet's angular range and damped by 0.5. For orthogonal equal-radius arms this is the mid-angle (rev-1 construction). For a missing slot, Q is the perpendicular foot of the opposite Q on B.
6. **Boundary node lists** are created once with shared ids: throats (the arm's column positions at σ_k), inner sides (the same normalised parameters as the matching throat), half-fillets (uniform angle, extension by length) and B segments (uniform).
7. **XY grids.** One Coons patch per arm patch, plus the central quad, with orientation normalised.
   Quality [V `rev2/skew2.py`; 2L arms, lip half-width 3.75, 4 columns]:

   | case | min corner angle | notes |
   |---|---|---|
   | orthogonal, R_lip 1.1–15.5 | 46.7°–52.5° | aspect ≤ 8.9, 0 folds |
   | orthogonal, radii 3.5/9.5/6.5/15.5 | 40.7° | bisector Q (38.0° with mid-angle Q) |
   | mixed skew +15/−15 | 47.3°–48.8° | |
   | one arm +15° | 39.2°–42.8° | |
   | symmetric skew 15° (parallelogram core) | 30.3° (R 15.5) – 57.4° (R 1.1) | the obtuse core corner leaves ≤ 75° for the two arm patches |
   | 4L×2L skew 15°, R 6.5 | 37.3° | |
   | skew 30° | 18.1°–47.9° | **excluded from v1** |

   **Gates:** orthogonal arms ≥ 40° (WARN below); skewed arms ≥ 30° (WARN below); < 20° is an ERROR for junction patches (the global ≥ 10° rule still applies); aspect ≤ 12; 0 folds. `test_rd01_junction` asserts these over the matrix in §9.2.
8. **Z field.**
   - Priority base `z_p(x, y)` comes from the priority section's CARRIAGEWAY function. Boundary z comes from the arm templates, the fillet lip nodes interpolate linearly in arc length, and B uses the priority section.
   - Interior `z = z_p + h`, where h is harmonic with mean-value weights and SOR (§3.5).
   - **SQUARE corner z (E12):** `z(B_c)` = mean of the two throats' back-of-walk z. z is linear along each back-of-walk line (throat → B_c) and along M_s–B_c, and the two corner Coons quads blend their boundary z. The validator WARNs if the corner sidewalk cross slope exceeds 2 %.
9. **Edge bands (generalised, T3).**
   - The edge half-profile of arm k is `tpl_k.slice(lip_tag, outer_tag)`. A corner band uses the unified column structure, with widths interpolated linearly in arc length between the two arms. It is swept **concentrically** about C along extension + arc + extension, with loops at the core's fillet nodes, `anchor_z` from step 8, and Closure.OPEN.
   - A column at lateral distance d from the lip has radius `R_lip − d`. **ERROR `EDGE_RADIUS` if the outermost column's radius is < 0.5 m.** Example: rural R_lip 12, Bankett 1.5 + verge 1.5 → 9.0 m ✓; urban R 6 + gutter 0.5, CONCENTRIC sidewalk 3.07 → back of walk 6.5 − 0.5 − 0.18 − 3.07 = 2.75 m ✓.
   - Sidewalk corner modes: CONCENTRIC, or **SQUARE only when the block angle is 75°–105°** (E12). SQUARE produces two 3D Coons quads split at the curb-back arc midpoint M_s → building corner B_c. AUTO picks SQUARE when `w_sw ≥ 0.293·r_cb + 0.5` and the angle is in range.
   - T far side: a straight sweep of the far edge profile along B.
10. **Arm sweeps.**
    - Closure.OPEN, from σ_k to D_k. The start loop reuses the throat nodes and the edge-band end loops.
    - Forced stations: crosswalk edges, ramp/flare/gutter-warp stations, stop-line edges, island nose tips and cut-through edges, and the port.
    - Zone spacing: ≤ 0.30 m in ramp + flare zones, ≤ 1.0 m elsewhere.
    - When `port_section` differs from `section`, the arm is a transition sweep (§2.6), and its length is extended to the taper rule.
    - **Median arms (T3, R6):** the MEDIAN_FLUSH columns run through the core like any carriageway column. The raised body is an island child (`islands.build_median_island`). It ends in a rounded nose (odd segment count) whose tip is ≥ `median_nose_gap` (1.0 m) from the crosswalk edge on the junction side. Where the crosswalk crosses the median, the island is **cut through** (refuge):
      - the gap equals the crosswalk length;
      - the paved faces inside the gap get slot RD01_Concrete;
      - crosswalk bars are clipped by the island footprints;
      - DWS pads are placed at both gap edges (instances);
      - both cut ends are finished with rounded noses.
11. **Closure.** SKIRT (default): skirts on the outer boundary only. SOLID (opt-in): `extrude_down` once over the whole top.
12. **Normals.** `fan_corner_normals` with `fixed` (keyed by vertex and face) at ports, throats and edge-band welds. **Diagonals: FIELD** everywhere (§3.3).
13. **Drive side (T4).** In arm frame (+X toward the port), the *approach half* is t > 0 for RHT and t < 0 for LHT (a driver heading inward keeps to their own side). Stop lines and give-way lines cover the approach half, `SOLID_APPROACH` lane-line rules are mirrored, and corner radius assignment follows the slot order (unchanged).
14. UVs (§4; u runs continuously around each block perimeter), masks (§5.2), markings (§3.9), sockets (one per port, +X outward), collision COMPLEX.

New pieces: **`SM_RD01_Junction_T_RQ11`** (rural T, RQ11 flat arms, R_edge 12 m, Bankett + verge edge bands, give-way line on the stem) and **`SM_RD01_Junction_T_2LMedian`** (a Street_2L_Median through road with a median opening at the stem, cut-through refuges on both through-arm crosswalks, and noses ≥ 1 m from the crosswalks).

### 3.7 Accessible curb ramps (`core/ramps.py`) — T16, E14

```python
# RampSpec in core/specs.py (E1)
@dataclass(frozen=True)
class RampSpec:
    kind: str = 'PERPENDICULAR'          # PARALLEL|COMBINED|BLENDED reserved (ERROR)
    width: float = 1.22; slope_max: float = 1/12; flare_slope: float = 0.10; landing: float = 1.22
    dws_depth: float = 0.61; dws_setback: float = 0.0; lip: float = 0.0
    gutter_counter_slope: float = 0.05; gutter_transition: float = 0.61
    region: str = 'EU'
@dataclass(frozen=True)
class RampStations: flare0: float; ramp0: float; ramp1: float; flare1: float; g0: float; g1: float
def ramp_stations(spec: RampSpec, reveal: float, centre_s: float) -> RampStations
def fit_crosswalk_setback(spec: RampSpec, cw: CrosswalkSpec, reveal: float, sigma: float) -> tuple[float, list[Issue]]
def ramp_morph(spec, tpl, sides, stations: Mapping[int, RampStations]) -> Callable[[float], MorphState]
def ramp_compliance(mesh: QMesh, piece_meta: dict, spec: RampSpec) -> list[Issue]
```

- λ(s) = 1 on [ramp0, ramp1], ramps 0 → 1 over [flare0, ramp0] and 1 → 0 over [ramp1, flare1], and is 0 elsewhere. `flare_len = reveal/flare_slope`; `ramp0/ramp1 = centre ∓ width/2`.
- **Ramp plane:** `z = z_flow + lip + d·m` over the columns toe → `ramp_top`. Curb columns keep their t (setback ≥ 0.02 enforced, so the batter face becomes a ≥ 2 cm COLLAPSE strip). Flares blend with `(1−λ)·z_normal + λ·z_ramp`.
- **Gutter warp:** within [g0, g1] = [flare0 − 0.61, flare1 + 0.61] the gutter slope blends to 5 %.
- **Gutter warp vs throat (T16, E12):** the warp must not start inside the corner edge band, which cannot morph and shares the throat loop. `fit_crosswalk_setback` pushes the crosswalk setback by `σ + 0.05 − g0`, rounded up to 0.05 m, whenever `g0 < σ + 0.05` (INFO `CROSSWALK_PUSHED`). ERROR if the pushed crosswalk no longer fits the arm. **US defaults** (reveal 0.15, crosswalk 3.05, setback 1.0) give flare0 = σ + 0.415 and g0 = σ − 0.195, so the setback is pushed to 1.25 m. EU defaults give g0 = σ + 0.08 (no push) **[V nums.py]**. The US case is in `test_rd01_junction`.
- **DWS:** faces in [ramp0, ramp1] × [`R.dws0` (or the curb back), `R.dws1`] become TACTILE, slot `RD01_Tactile`, PATH 0.60 m. The u reference is the dws0 column with the u origin at ramp0, so the dome grid starts cleanly.
- **Trim V in ramp zones (R8, T16):**
  - flare faces (0 < λ < 1) keep their CURB_* band with **v = the nominal pre-morph profile distance** of each column, so the arris highlight stays on the arris columns;
  - faces with λ = 1 on both loops switch to the **CURB_DROP** band with absolute v (authored as a flush dropped kerb), with a UV seam at ramp0 / ramp1;
  - mask A (edge wear) is multiplied by (1 − λ).
- Grade breaks are column lines (constant t), so they are straight and perpendicular to the run [S R304.2.3].
- **Compliance report** (measured on the mesh): running slope, cross slope ≤ 1:48, flare slope, landing, width, lip ≤ lip_max, counter slope, combined grade, DWS depth/width, and footprint inside the crosswalk band.
  - Limits use exact `fractions.Fraction` (1/12 + 1/20 = 2/15 exactly), and measured values are compared with a tolerance of 1e-4 (E14).
  - FAIL → WARN.

### 3.8 Roundabouts (`core/roundabout.py`) — T2, T4, T33, E5, E13, E34

```python
# core/specs.py
@dataclass(frozen=True)
class SplitterSpec: length: float = 15.0; width_nose: float = 3.0; width_tail: float = 1.0
                    nose_radius: float = 0.5; tail_radius: float = 0.3; nose_gap: float = 1.0
                    offset: float = 0.5                 # flush-median margin on each side of the island (T2)
                    curb: CurbType = CurbType.BARRIER   # one curb type per island (R2)
                    cut_through: bool = True
@dataclass(frozen=True)
class LegSpec: heading_deg: float; section: CrossSection; entry_radius: float = 20.0; exit_radius: float = 25.0
               entry_width: float = 4.5; exit_width: float = 5.0; length: float | None = None   # None → auto
               splitter: SplitterSpec | None = SplitterSpec(); crosswalk: CrosswalkSpec | None = CrosswalkSpec()
               ramps: RampSpec | None = None
@dataclass(frozen=True)
class RoundaboutSpec:
    name: str; kind: str = 'SINGLE'            # 'MINI' | 'COMPACT' | 'SINGLE'   (DOUBLE removed from v1, R7)
    icd: float = 35.0; circ_width: float = 5.5
    apron_width: float = 3.0; apron_slope: float = 0.02; apron_reveal: float = 0.05
    island_curb: CurbType = CurbType.BARRIER; island_dome: float = 0.3
    mini_island: str = 'DOMED'                 # MINI only: 'DOMED' (traversable, ≤ 0.12) | 'PAINTED' (UK option)
    circ_crossfall: float = 0.02; edge: tuple[Band, ...] = (); legs: tuple[LegSpec, ...] = ()
    closure: Closure = Closure.SKIRT; detail: Detail = Detail.LOD0; drive_side: DriveSide | None = None
def build_roundabout(spec: RoundaboutSpec) -> Piece          # islands in piece.children (exported separately, §7.2)
```

| kind | ICD default (range) | circ width | apron | central island |
|---|---|---|---|---|
| MINI | 20 (13–25) | 5.0 | none | DOMED: traversable, dome ≤ 0.12, ROLL border, RD01_Concrete. PAINTED (UK option): flat white disc at carriageway level (RD01_Marking). Splitters are painted outlines (no solids). |
| COMPACT | 28 (25–30) | 5.0 | 2.0 | raised |
| SINGLE | 35 (30–45) | 5.5 (4.5–7.0) | 3.0 (1–4.5) | raised |

The MINI contradiction in rev 1 ("painted" vs "domed mountable") is resolved by `mini_island` (E13).

Construction:
1. **Radii.** R_o = ICD/2 (outer gutter lip), R_a = R_o − circ_width, R_ci = R_a − apron_width − w_apron_curb.
2. **Ring stations (E5, E13).** Ring stations are **not globally uniform**. Each leg core defines its own stations on R_a:
   - the central-quad bottom gets m_leg equal angular segments between the radial projections of Q_e and Q_x;
   - each ring arm gets n half-fillet segments between its ring throat and Q.
   Between leg cores, spacing is uniform and ≤ θ(R_max), with R_max = the largest-radius column swept on the ring (the outer back of walk). Grading is ≤ 1.5 between sectors and ≤ 2.0 at core boundaries (1.86 measured at ICD 35). The free sectors absorb the remainder so that the total station count is a multiple of 4 (needed by the O-grid island).
   All concentric columns share these stations, so **Q4 is exactly the radial projection of Q_e**, as in the prototype, and the prototype quality transfers. The leg-sector chord check at R_a requires `2θ_Q/m_leg ≤ θ(R_a)`, else ERROR `LEG_CORE_CHORD` (measured 4.60° vs 4.68° at ICD 35, m_leg 10 **[V rev2/ra2.py]**).
3. **Inner radial sweep** (closed rail): island curb → apron (rises inward at apron_slope, reveal at its edge) → mountable apron curb → R_a. The island top inside R_ci is a `disc_ogrid` (poles tagged `pole:ogrid`) with dome `island_dome·(1 − (r/R_ci)²)` (≤ 8 % slope, so HEIGHTFIELD unwrap applies, §4.4).
4. **Legs and lateral morph (T2, E13).**
   - Leg k is radial at heading φ_k (v1: legs pass through the centre, ≥ 60° apart).
   - The leg section at F has a **MEDIAN_FLUSH** band of width `w_m(s) = splitter_width(s) + 2·offset` (3.0 + 1.0 = 4.0 m at the nose), with the approach-half lane widened to `entry_width` and the departure-half lane to `exit_width`.
   - The leg arm from F to the port is a **transition sweep** (§2.6), with these `t_offset` laws:
     - median half-width: `m(s) = splitter_width(s)/2 + offset` along the island (linear nose → tail), then a cosine decay to 0 over `L_m = m_tail·taper_ratio` behind the tail, ending in a collapse row onto the crown column;
     - lane widths: cosine from entry/exit width to `lane_width` over `L_l = |Δw|·taper_ratio`.
   - Leg length (auto) = `max(spec.length, nose_gap + splitter.length + L_m, L_l, crosswalk end + 2.0)`, rounded up to 0.5 m (4 m for kit pieces).
   - **ERROR if `entry_width < 4.3 m`** (measured perpendicular to the entry lane at the yield line).
   - **Drive side (T4).** In leg frame (+X outward) the approach (entry) half is t > 0 for RHT and t < 0 for LHT. The entry fillet uses entry_radius on the entry side, and the exit fillet exit_radius on the other side. Circulation is CCW for RHT and CW for LHT. The splitter taper direction, the yield line half, ring lane-line rules and arrows all mirror.
5. **Leg core = a T junction whose through road is the ring** (§3.6 machinery):
   - the ring throats are radial at the ring station nearest outside T;
   - the leg throat is at F, where the leg section is widened, so leg half-width is 6.0–6.5 m with the splitter;
   - the central-quad corners are Q_e, Q_x and their radial projections onto R_a;
   - z uses the ring function `z(r) = −circ_crossfall·(r − (R_a+R_o)/2)` plus a harmonic correction.
   Quality with the widened leg **[V rev2/ra2.py]:**

   | case | min angle | aspect |
   |---|---|---|
   | ICD 28, hw 6.0 | 49.5° | 3.3 |
   | ICD 35, hw 6.5 | 46.6° | 4.1 |
   | ICD 45, hw 6.5 | 42.6° | 4.5 |
   | ICD 20 (MINI), hw 5.5 | 53.0° | 4.5 |

   Gate ≥ 40°.
6. **Ring sweeps** between legs: lanes R_a → R_o plus the outer edge profile, at the ring stations.
7. **Fillet edge bands:** the outer edge profile swept concentrically. ERROR if the outermost column's radius is < 0.5 m.
8. **Leg crosswalks:** `AUTO = max(7.5 m behind the yield line, F + 1.0 m)` [S FHWA]. With `cut_through`, the crosswalk must lie inside the splitter between `nose + nose_radius + 1.0` and `tail − 1.0`, otherwise the splitter length is extended (INFO) or ERROR (kit).
9. **Splitter islands (D11, T33):**
   - closed solids on the MEDIAN_FLUSH band, `offset` from each flush edge, with one curb type, the toe sunk 5 cm below the TriSurface (validator: ≥ 5 mm everywhere, E11), odd arc segment counts at both ends, and `outline r − w_curb ≥ 0.10`;
   - **cut-through:** two solids with a gap equal to the crosswalk length;
   - **both cut ends finished as rounded noses** (odd segments);
   - the paved faces in the gap become RD01_Concrete;
   - crosswalk bars are clipped by the island footprints;
   - DWS pads at the gap edges (instances).
10. **Markings:**
    - yield line along R_o across each entry (dashed 0.5/0.5 [I], width 0.5 TR / 0.3 others);
    - lane lines on legs;
    - **flush-median edge lines** (solid, converging into the centre line at the median collapse);
    - crosswalk bars (clipped);
    - MINI PAINTED: island disc + painted splitter outlines.
    Ring lane markings are not needed in v1 (single-lane circulation only).
11. Closure SKIRT, normals, UVs (ring: u continuous around the ring; MACRO UV0 by default for kit pieces), masks, sockets (one per leg port), collision COMPLEX.
12. **Children export (E34):** islands are separate assets `SM_RD01_<Piece>_Island<NN>`, each with UCX hulls. The manifest lists them under the parent's `children` with transforms relative to the parent origin, and the importer places them with the parent.

### 3.9 Markings (`core/markings.py`) — T6, T11, T33, E11, E15

```python
@dataclass(frozen=True)
class DashPattern: name: str; dash: float; gap: float           # gap 0 → solid
PATTERNS = {'SOLID': (0, 0), 'TR_URBAN': (3.0, 3.0), 'TR_RURAL': (4.5, 7.5), 'TR_OTOYOL': (6.0, 9.0), 'TR_JUNCTION': (1.5, 1.5),
            'DE_INNERORTS': (3.0, 6.0) [I], 'DE_AUTOBAHN': (6.0, 12.0), 'UK_1005': (1.0, 5.0), 'UK_1005_1': (2.0, 7.0),
            'UK_GIVEWAY_1003': (0.6, 0.3) [I], 'US_BROKEN': (3.048, 9.144), 'US_DOTTED': (0.61, 1.22),
            'AT_URBAN': (3.0, 3.0), 'AT_RURAL': (6.0, 9.0), 'AT_MOTORWAY': (6.0, 12.0)}
def dashes(length: float, pattern: DashPattern, phase: float = 0.0, end_with_dash: bool = True) -> list[tuple[float, float]]
def fit_dash_cycles(s0: float, s1: float, pattern: DashPattern, max_scale: float = 0.05) -> tuple[list[tuple[float, float]], float]
def zebra_layout(road_w, bar=0.5, gap=0.5, edge_min=0.25, edge_max=0.75) -> tuple[int, float]
def line_strip(surface: TriSurface, road: SweepResult, cols: tuple[int, int], ranges, mode='RAISED', band='LINE',
               sheet: TrimSheet | None = None, name: str = '') -> QMesh
def bar_strip(surface: TriSurface, footprint: Sequence[Vec2], road_lines: RoadLines, mode='RAISED', band='BAR',
              clip: Sequence[Sequence[Vec2]] = (), sheet: TrimSheet | None = None, name: str = '') -> QMesh
def marking_clearance(marking: QMesh, surface: TriSurface) -> tuple[float, list[Issue]]
```

- **Surface queries use the rendered triangles (T6, E11).** Every z comes from `TriSurface` (§10.2): the road's actual v0–v2 triangles after the FIELD diagonal choice. `SweepSurface` and the bilinear `SurfaceSampler` from rev 1 are removed.
- **Longitudinal lines.** The strip's side columns *are* the road template's line edge columns (`mk<k>a/b`, §2.2), and its loops are the road loops inside each dash plus the dash ends. Every strip quad therefore lies over one road quad and copies that quad's diagonal.
- **Transverse bars** (crosswalk bars, stop, yield and give-way lines) are split at **every road column line and loop line** they cross, plus ≤ 0.5 m splits, so they stay quads. Each bar quad copies the diagonal direction of the road quad below it.
- **Exact clearance (R15).** Both surfaces are piecewise linear, so the maximum of (road z − marking base z) over a marking face is reached at a vertex of their overlay arrangement: marking corners, crossings of the road diagonal with the marking edges, crossings of the marking diagonal with the road edges, and the crossing of the two diagonals. `deviation` is evaluated exactly at those points.
- **Lift rule (T6, R15):** per vertex `lift = max(3 mm, deviation_local + 2 mm)`, applied vertically (height field). ERROR `MARKING_LIFT` if a lift above 8 mm is needed (the remedy is to refine the road loops).
- RAISED skirts drop to 2 mm below the TriSurface.
- **Validator `MARKING_CLEARANCE`:** the top surface must be ≥ 1 mm above the TriSurface, sampled at marking vertices, face centroids, edge midpoints and arrangement vertices; an ERROR otherwise (E11).
- **Phase continuity (T11).**
  - Patterns are anchored at junction ports and stop lines (`end_with_dash`).
  - A road connected to ports at **both** ends uses `fit_dash_cycles`: an integer number of dash cycles between the two fixed ends, with the cycle length scaled ≤ 5 %. If 5 % is not enough, the scale is clamped, one end gets `end_with_dash`, and WARN `DASH_PHASE`.
  - Chunk boundaries never restart a pattern (global s).
- **Island clipping (T33):** bars are clipped by island footprints (splitters, medians), and the cut-through region gets no paint.
- **Drive side (T4):** stop, give-way and yield lines cover the approach half (§3.6). Centre-line patterns come from the region preset, and UK give-way lines use the double dashed `UK_GIVEWAY_1003` [I].
- U offset per strip = `k/8` of the U tile, with `k = blake2b(strip_name) % 8` (E15). An integer offset would do nothing on a U-tiling trim.
- Zebra example **[S KGM]:** `zebra_layout(7.0) == (7, 0.25)`.
- Slot `RD01_Marking`, part MARKING, `face_kind MARKING`, TRIM UV on the marking sheet (§4.7).
- RAISED markings are **appended to the piece mesh in the kernel** (`finalize_piece`, E22), and in UE the RD01_Marking section has collision disabled (§7.8).
- DECAL: top only at +10 mm, exported as a separate `SM_RD01_<Piece>_Decal` asset.

### 3.10 Rural / highway (`core/rural.py`, `core/road.py`) — T23, T24, T28

```python
def rq11(region='DE', ditch: bool = False, embankment_h: float | None = 1.0) -> CrossSection   # None → at-grade 'RQ11_Flat'
def us_rural_2lane(shoulder: float = 2.4) -> CrossSection
def rq31(barrier: BarrierShape = BarrierShape.NJ) -> CrossSection        # 31.0 m with NJ median
def rq36(...) -> CrossSection; def rq28(...) -> CrossSection; def us_interstate(...) -> CrossSection
def build_guardrail(surface: TriSurface, rail: Rail, spec: GuardrailSpec, stations) -> tuple[QMesh, list[Instance]]
def side_slope_morph(tpl: ProfileTemplate, rail: Rail, ground: Callable[[float, float], float | None],
                     side: int) -> Callable[[float], MorphState]           # road.py (T24)
```
`wbeam_profile` and `barrier_section` live in `profiles.py` (E1).

- **Alignment:** rural and highway presets use clothoid transitions (§3.1). The superelevation runoff lies on the spiral.
- **Ground source (T24).** `RoadBuild.ground` is a height function, filled in by the bpy layer (`blender/ground.py`, a BVH ray cast straight down onto the chosen ground object). Alternatively, `RoadBuild.ground_offsets` gives a signed hinge height above ground per control point, interpolated in s. Without either, the constant `embankment_height` applies.
  - **Catch-point solve, per station and side:** from the hinge (outer edge of Bankett or ditch back), run a line at 1:n_fill downward if the ground is below, or 1:n_cut upward if it is above. Bisect along t for its intersection with the ground (1 mm tolerance), with a minimum run of 0.5 m (if |h| < 0.5/n the slope flattens to reach the ground at 0.5 m).
  - **Topology stays a fixed grid:** the EMBANKMENT band always has the same columns (hinge, crest arc 3 seg, k slope points, toe arc 3 seg, catch, 2 apron points). k = ⌈max run over the road / 1.0 m⌉ is fixed per build. Only `t_offset` and `z_abs` vary per station (MorphState).
  - The arc rounding uses `T = clamp(1.5·|h|, 0.10, 3.0)`, so arc columns keep Δt ≥ 2 mm, and the arc curvature flips sign between fill and cut. Apron points follow the ground. A missing ground hit gives WARN and falls back to the constant height.
  - Junctions in v1 use the arms' constant height (ground following for junction edge bands is v1.1).
- **Guardrail.**
  - The W-beam rail is a thin closed profile swept along the offset path, with its top at TriSurface z + rail_height. Its UV is TRIM on `RD01_TrimRail` (VEH), with u scaled so that rail splices fall at u ≡ 0 (EU 4.0 m panel: scale 1.0; US 3.81 m: 0.952, within the 5 % limit).
  - Posts and blockouts are **instances** of UNIQUE kit parts (`RD01_KitRail`), placed every post_spacing.
  - **Scaling (T28):** the core returns `Instance` lists grouped per chunk. Blender shows them with **one Geometry Nodes instancer per road owner** (`blender/instancer.py`: a point mesh with a QUATERNION `rd01_rot` attribute → Instance on Points → Object Info of the asset; **[V rev2/bchk.py]** 3 instances evaluated headless with the expected yaw). The instancer is display-only and never exported. UE gets one ISM component per asset per chunk (§7.8).
- The median barrier in spline roads is cast-in-place (welded MEDIAN_BARRIER). Precast barriers are kit units (closed profile, Z-ladder caps, 4 mm end chamfer).

### 3.11 Islands and small props (`core/islands.py`, `core/street.py`) — T26, T33, E13

```python
def build_splitter(frame: tuple[Vec3, Vec2], spec: SplitterSpec, surface: Surface, cut: tuple[float, float] | None,
                   name: str) -> list[Piece]
def build_median_island(rail: Rail, s0: float, s1: float, width: float, curb: CurbType, noses: tuple[bool, bool],
                        cuts: Sequence[tuple[float, float]], surface: Surface, name: str) -> list[Piece]
def island_outline(...) -> list[Vec2]                     # rounded taper; odd segment counts at every rounded end
```
- **Outline.** A tapered rounded rectangle (splitters) or an offset band (medians). **Every rounded end, including the ends created by a cut-through, uses an odd segment count**, so the top-cap ladder ends on a tip *edge* rather than a vertex (T33).
- **One curb type per island (R2)**, swept around the closed outline with `sweep_closed(closed_rail=True)`. The fold rule `r_local − w_curb ≥ 0.10 m` is an ERROR when violated.
- The toe is sunk 5 cm below the TriSurface (D11). The validator checks ≥ 5 mm along the whole outline (E11: no light-leak gap).
- Top: ladder quads between the mirrored chains (ISLAND_TOP, `RD01_Grass` or `RD01_Concrete`). The bottom is extruded to 5 cm below the local surface (one SOLID per island).
- Collision: one UCX convex hull per solid (outlines are convex by construction; a concave outline is split at its inflection stations).
- Bollard: `lathe` with 16 segments and O-grid caps (`pole:ogrid`). The cap profile tilts ≤ 30°, so it unwraps POLAR (§4.4).
- Drain grate: a chamfered slab 0.50 × 0.30 × 0.10.
- Tactile pad: LOD0 is a 5 mm slab with a 2 mm chamfer. **HIGH adds domes** (base Ø 25 mm, top 60 % of the base, height 5 mm, pitch 50 mm [S PROWAG ranges]) for the Painter `_high` bake (T32). HIGH meshes are exempt from quad and UV gates (they are bake sources only).

### 3.12 Port continuity (`core/road.py`, `core/validate.py`) — T22, E33

- **Port record** (`piece.Port`): position, direction, section_hash, column positions, **per-column fan normals**, **UV phase** (u mod module for every band reference column), crossfall and grade.
- **`ports_match(a, b)`** requires all of the following (ERROR otherwise):
  - equal section_hash;
  - column positions within 1 mm (3D);
  - normals within 0.5°;
  - trim/path u equal modulo the band module (1 m) within 1 mm;
  - marking phase consistent.
- **Spline roads at ports.** Over `L_lead = max(2.0 m, arm length)` before a port, the road must have:
  - (a) zero curvature (straight lead-in);
  - (b) normal crown (dilation target −c at the port, §2.4);
  - (c) constant grade equal to 0 at the port. v1 junction ports are level; tilted ports are v1.1.
  Violations are ERROR `PORT_LEADIN`, `PORT_GRADE` or `PORT_CROWN`. `rd01.snap_curve_to_port` builds a compliant lead-in: it inserts a control point at `port − L_lead·dir` with ALIGNED handles along dir and sets the end point's handle along dir, so the last segment is straight and level.
- **U phase at ports (T11):** for a road with ports at both ends, each band's U scale is adjusted by ≤ 1 % so that `u ≡ 0 (mod 1 m)` at both ports (`SweepSpec.uv_scale`). With one port, the u origin is set so that `u ≡ 0` at that port. If 1 % is not enough, WARN `UV_PHASE`.
- **Unported ends** get end curtains (SKIRT) or T-ladder caps (SOLID), so no open profile is ever visible (§3.2).
- **Re-snap (T22):** a curve end linked to a port (`Object.rd01_road.links`) is re-snapped and rebuilt in the same operator and undo step whenever its junction or roundabout is rebuilt. A vanished port drops the link with WARN.

---

## 4. UV strategy

### 4.1 Channel contract (D7) — T20

| layer | index | TILING pieces | UNIQUE pieces | UDIM pieces | MACRO pieces |
|---|---|---|---|---|---|
| `UV0_Main` | 0 | copy of UV1 | packed 0–1 atlas of its set | packed UDIM tiles | packed 0–1 macro atlas (one 4096 set, 48–128 px/m, target 64–128) |
| `UV1_Tile` | 1 | world / path / trim (Designer) | tiling / trim (UE detail layers) | tiling / trim | tiling / trim |
| `UV2_Lane` | 2 | lane UV on LANE / EDGE_STRIP / SHOULDER faces, copy of UV1 elsewhere | same | same | same |
| `UV3_Light` | 3 | BAKED profile only | BAKED only | BAKED only | BAKED only |

Painter reads UV0 only [S]. FBX writes layers in creation order **[V]**, and `mesh_io` creates them in this order. UE derives tangents from UV0 (MikkTSpace). For TILING pieces UV0 = UV1, so the tangent frame follows the tiling UV. WORLD_XY branches therefore transform their normals explicitly (§7.9).

### 4.2 Tiling rules — UV1 (`core/uv.py`) — T9, T10, T11, T14, E6

```python
# UVRule is in core/specs.py
@dataclass(frozen=True)
class UVRule:
    kind: UVKind                       # WORLD_XY | PATH | TRIM | PLANAR
    tile_m: tuple[float, float] = (4.0, 4.0)
    sheet: str = ''; band: str = ''    # TRIM
    ref: str = ''                      # reference column tag: u is measured along this column for the whole band (T9)
    anchor: str = ''                   # tag where v = 0
    reverse: bool = False              # set by the compiler so that the signed UV area is positive (E6)
    nominal_v: bool = False            # ramp flares: v = nominal pre-morph distance (§3.7)
    plane: str = ''                    # PLANAR: 'BOTTOM' | 'END' | 'PRIORITY_ARM' (SQUARE corners)
def apply_tiling_uvs(mesh: QMesh, world_offset: Vec3 | None, sheets: Mapping[str, TrimSheet]) -> list[Issue]
def apply_lane_uvs(mesh: QMesh, tile_m: float = 8.0) -> None
def rebase(mesh: QMesh, layer: str = 'UV1_Tile') -> dict[str, tuple[int, int]]
def uv_stretch_report(mesh: QMesh) -> list[Issue]
```

- **WORLD_XY** (isotropic: asphalt 4 m, gravel and grass 4 m) uses world XY for generated spline roads, junctions and roundabouts, and piece-local XY for kit pieces. It applies to TOP faces only (WARN `WORLD_XY_STEEP` if n_z < 0.7, E16). Faces are CCW from above, so the orientation is positive.
- **PATH** (sidewalks, embankments, ditches, skirts, tactile): `u = param.u_m / tile_u`, `v = param.v_m / tile_v`. `param.u_m` is measured on the band's **reference column** and shared by every column of the band at that loop, so joints stay radial on curves (T9).
  - **Sidewalks (T10)** use slot RD01_Concrete, PATH 2.0 × 2.0 m, with ref and anchor at the **curb back**. The joint module lives in `trim_sheets.json`: `"RD01_Concrete": {"kind": "PATH", "tile_m": [2.0, 2.0], "joint_module_m": [1.0, 1.0]}`, so the Designer author draws joints at u, v ∈ {0, 0.5}, with v = 0 on the curb back.
  - CONCENTRIC corners continue the PATH around the arc (u on the curb-back column).
  - SQUARE corners are a PLANAR island aligned to the priority arm: e1 = that arm's axis, v measured from its curb-back line. The u origin of the non-priority arm's sidewalk PATH is chosen so that the seam lies on a joint line (u ≡ 0 mod 0.5).
- **TRIM** (curbs, gutters, barriers, rails, markings): `u = (param.u_m + u_offset)/u_tile_m`, and `v = band_v(sheet, band, param.v_m)`, where **rows are counted from the top of the image** (Designer / Photoshop convention) and `band_v = 1 − (y0_px + inset_px + d·density)/sheet_h_px` (T12). A band whose profile does not fit is an **ERROR** (`TRIM_OVERFLOW`). There is no silent scaling.
- **PLANAR**, always in a right-handed frame `e1 × e2 = n` (T14, E6):
  - SOLID bottoms (n = −Z): `u = x, v = −y`;
  - caps and SKIRT end curtains: `e2 = +Z`, `e1 = e2 × n` (facing outward);
  - SQUARE sidewalk corners: as above.
- **Skirts:** PATH with u along the run (top edge column) and v down the skirt, with the per-side `reverse` flag.
- **Reverse rule (E6).** For the side where the forward mapping would give a negative signed area, `u = −(param.u_m + u_offset)·k` and **v is unchanged**. Rev 1 negated u and v; that is a 180° rotation, which keeps the negative area and pushes TRIM v out of its band. Test: the signed UV area is > 0 on every face and every layer (UV0, UV1, UV2) for a SKIRT street, a SOLID street, a junction and a curb unit.
- **Continuity (T11).**
  - Spline roads keep global u across chunks.
  - **Block perimeters:** the bands that wrap a block (gutter, curb, sidewalk) carry u **continuously around the perimeter**, traversed CCW seen from above. Each segment (arm edge, corner band, arm edge) sets `uv_dir = ±1` according to whether its s agrees with that traversal, and its `uv_origin[band]` = the u at the end of the previous segment (welds carry exact u).
  - **Ports:** with both ends of a perimeter or road at ports, each band's U is scaled by ≤ 1 % (`SweepSpec.uv_scale`) so that u ≡ 0 (mod 1 m) at both ports. Kit straight pieces have lengths that are multiples of 1 m and u ≡ 0 at both ends by construction. If 1 % is not enough, WARN `UV_PHASE`.
- **Stretch (T9):** u is exact on the reference column. Other columns of the band stretch by `r_col/r_ref − 1` on arcs (on an R 6 curb return the curb back stretches 3 %). WARN `UV_STRETCH` above 5 % for TRIM bands and above 30 % for SIDEWALK PATH on CONCENTRIC corners, where radial joints are physically right. The report is part of the validation output.
- **Rebase:** per mesh and rule group, subtract integer floors (WORLD/PATH shift u and v; TRIM shifts u only). Chunks are ≤ 64 m, and the importer enables full-precision UVs for TILING meshes.

### 4.3 UV2_Lane — lane-aligned asphalt UV (T20)

- **LANE faces:** `u = (arc length along the lane's centre line)/8.0 m`, increasing in the **driving direction** of that lane (drive side and half). `v = 0` at the driver's right lane edge and `1` at the left edge, so `v = 0.5` is the lane centre. Opposing lanes therefore get a 180°-rotated UV, which keeps a positive signed area.
- **EDGE_STRIP / SHOULDER faces:** v continues linearly beyond the outer lane (v < 0 on the driver's right), so edge cracks and rut shoulders can be authored.
- **Ring lanes** on roundabouts: u along the ring in the circulation direction.
- **MEDIAN_FLUSH, junction and roundabout core patches:** `UV2 = (u_proj/8, 0.5)` (u projected on the priority axis or ring), and lane weight A = 0. These faces may have zero UV2 area (validator exemption: `UV2_DEGENERATE_OK` on faces with A = 0).
- **Arm patches** ramp the lane weight from 1 at the throat to 0 at the inner side (linear in the patch parameter).
- **Non-asphalt faces:** UV2 = UV1.
- Designer authors one lane-width material (tyre tracks at v ≈ 0.25 / 0.75, oil strip at 0.5, longitudinal cracks) that tiles every 8 m.

### 4.4 Unique UV0 for Painter (UNIQUE / UDIM / MACRO) — T13, T14, T15, R12

```python
@dataclass
class Island:
    mesh_name: str; faces: list[int]; method: Unwrap | None
    uv_m: dict[tuple[int, int], Vec2]; scale: float; w: float; h: float
    isotropic: bool                    # HIDDEN / BOTTOM islands: rotation allowed (T15)
    run_dir: Vec2 | None               # sweep islands: UV u axis must follow the run
def extract_islands(mesh: QMesh, max_len: float) -> list[Island]
def unwrap_island(mesh: QMesh, isl: Island) -> Unwrap            # always assigns a method or raises
def pack_texture_set(pieces: Sequence[Piece], set_name: str, td_class: TDClass, tex_px: int | None = None,
                     mode: UVMode = UVMode.UNIQUE) -> PackReport    # the ONLY packing entry point (E4)
```
1. **Islands = face groups** (island-group column range × loop range for sweeps; patches, caps, bottoms and skirts are separate). Every hard edge is a seam by construction. Runs longer than `max_len = min(2.0, (tex_px − 4·pad)/k_px)` are cut at loops.
2. **Unwrap method**, chosen in this order, so every island gets one (`UV_NO_METHOD` is an ERROR):
   - **PLANAR:** all normals within 2° of the Newell mean. Project in a right-handed frame with e1 = the projected run direction (or piece +X).
   - **UNROLL:** sweep islands (≥ 2 loops of one sweep): u = arc length on the island's reference column, v = cumulative profile distance, **u along the run**.
   - **HEIGHTFIELD** (T13): TOP faces that are not a sweep (harmonic junction tops, domed island tops), with all faces sloped ≤ 8 % (n_z ≥ 0.9968): `uv = (x, y)·k` in piece XY. The maximum directional TD error is `1 − 1/√(1+0.08²) = 0.32 %` (area-TD 0.16 %) **[V nums.py]**. A ±2.5 % crown (2.9° normal spread, which fails PLANAR) qualifies. Steeper patch islands are split along grid lines until each part qualifies or is PLANAR.
   - **POLAR** (T13): O-grid caps (bollard caps, island domes > 8 %) with a maximum normal tilt ≤ 35° use an azimuthal-equidistant map about the cap axis. Otherwise the cap is split at its O-grid ring into an inner HEIGHTFIELD/PLANAR disc and an UNROLL ring.
   - Bottoms: PLANAR `u = x, v = −y`. Caps and curtains: PLANAR in the end plane, right-handed, facing outward (T14).
3. **Scale** `k = td/tex_px` per metre × the role scale (HIDDEN 0.25, CAP 0.5, VISIBLE 1).
4. **Pack:** islands from **every piece of the set's catalogue membership** (not just the pieces the user ticked; §8.3) go into one atlas.
   - `pad = tex_px/128`.
   - **`allow_rotate=False`** by default. Only `isotropic` islands (HIDDEN, BOTTOM) may rotate (T15).
   - Gate `UV_RUN_DIR` (ERROR): every VISIBLE sweep island's UV u axis is within 1° of its run direction, so brushed concrete, saw cuts and rust streaks stay consistent.
   - `tex_px=None` tries 1024, 2048 and 4096 and never rescales silently. If 4096 fails: ERROR, suggesting MACRO, UDIM or VEH.
   - Capacity pre-check: `Σ area·k² ≤ 0.70·tex²`.
5. **MACRO (R12):** one 4096 set per piece. TD is the largest multiple of 8 px/m ≤ 128 that passes the capacity pre-check and the packer. Below 64: WARN `MACRO_TD_LOW`. Below 48: ERROR (use UDIM). The manifest records `td_class: "MACRO"` and `td_px_m`.
6. **UDIM** (opt-in, VEH density): `max_bins > 1`, `u += bin % 10`, `v += bin // 10`, tile = 1001 + bin. Patch tops are split along grid lines until each part fits a tile.
7. Write UV0, `seams`, `face_island` and `uv0_hash`.

```python
@dataclass(frozen=True)
class Rect: id: int; w: int; h: int; may_rotate: bool        # pixels, inflated by 2·pad
@dataclass(frozen=True)
class Placed: id: int; x: int; y: int; rotated: bool; bin: int
def maxrects_pack(rects: Sequence[Rect], bin_w: int, bin_h: int, max_bins: int = 1) -> list[Placed] | None
```
MaxRects uses Best-Short-Side-Fit with a deterministic order (height desc, width desc, id). Rotation is tried only for `may_rotate` rects. Determinism test: the same input gives identical placements.

### 4.5 Texel-density classes and tiling sizes (D8)

| class | px/m (default / vehicle preset) | used by |
|---|---|---|
| PED | 1024 / 512 | curb, gutter and marking trims; RD01_KitCurb, KitStrip (gutter+curb strip, ramp insert), KitTactile, KitIsland, KitProps |
| VEH | 512 / 512 | Painter road tiles (KitPave, KitWalk, KitCorner); barrier and rail trims; KitBarrier, KitRail |
| MACRO | solved 48–128 (target 64–128) | junction, roundabout and highway macro UV0 |

| tiling set | UV | tile | Designer physical size |
|---|---|---|---|
| RD01_Asphalt | WORLD_XY (UV1) + UV2_Lane | 4.0 m; lane UV 8.0 m × 1 lane | 400 cm; lane material 800 × lane width |
| RD01_Concrete | PATH | 2.0 × 2.0 m, joint module 1.0 m | 200 cm |
| RD01_Gravel / Grass / Soil | WORLD_XY / PATH (slopes) | 4.0 m | 400 cm |
| RD01_Tactile | PATH | 0.60 m | 60 cm |
| trims | TRIM | u tile = sheet_w/density (2.0 m PED, 4.0 m VEH) | §4.7 |

Gates (UNIQUE/UDIM/MACRO, visible faces): per-face density CV ≤ 0.05; median within ±10 % of the class density.

### 4.6 Optional UV3 lightmap (BAKED profile)

Reuses `extract_islands` + `maxrects_pack` (rotation allowed, since lightmaps are isotropic) on all faces. The scale is the largest that fits a 64/128/256 px lightmap with 2 px padding, and HIDDEN faces use 0.1. The importer sets `light_map_coordinate_index=3` and disables Generate Lightmap UVs.

### 4.7 Trim sheets (`core/trimsheet.py`, generated `data/trim_sheets.json`) — T12, E15, R10

```python
# core/specs.py
@dataclass(frozen=True)
class TrimBand: name: str; y0_px: int; y1_px: int; need_m: float; users: tuple[str, ...]
    def capacity_m(self, sheet: 'TrimSheet') -> float     # (y1 − y0 − 2·inset)/density
@dataclass(frozen=True)
class TrimSheet: name: str; td_class: TDClass; density_px_m: int; sheet_w_px: int; sheet_h_px: int
                 u_tile_m: float; inset_px: int; bands: tuple[TrimBand, ...]
# core/trimsheet.py
# needs come from profiles.trim_band_needs() (WP1): max girth over every hard-range endpoint combination of each band's users
def generate_layouts(needs: Mapping[str, Mapping[str, float]], density: Mapping[TDClass, int]) -> dict[str, TrimSheet]
def load_trim_sheets(path: str | None = None) -> dict[str, TrimSheet]
def band_v(sheet: TrimSheet, band: str, d_m: float) -> float      # 1 − (y0 + inset + d·density)/H
def guide_svg(sheet: TrimSheet) -> str                      # labelled bands, insets, u-tile joint ticks at u = 0 and 0.5
```
**Generation rules:**
- `need_m` is the maximum profile girth of the band's users over every hard-range endpoint combination, plus the skirts for markings (2 × (8 mm max lift + 2 mm sink)).
- `px = ceil(need·density + 2·inset)`, rounded up to a multiple of 8. Bands are stacked **from the top row**.
- `sheet_w = 2048`, `u_tile = sheet_w/density`, `sheet_h` = the next power of two ≥ Σ px. Above 4096 is ERROR `TRIM_OVERFLOW`.
- A user profile longer than its band's capacity is an ERROR in tests (E15).
- `data/trim_sheets.json` stores the layout together with the needs snapshot it was generated from. `test_rd01_trimsheet` (WP4) regenerates it from that snapshot, and `test_rd01_trim_fit` (WP8) checks `generate_layouts(profiles.trim_band_needs())` == the data file, with no overflow in any region.
- Every export writes `Trims/<Sheet>.json`, `Trims/<Sheet>_guide.svg` and `Trims/<Sheet>_guide.png` (the PNG rendered by the bpy layer) into the export folder.

Default layouts (PED 1024, VEH 512, inset 8 px; px rows from the top) — expected output of the generator, recomputed in `rev2/trim.py`. The needs are upper bounds from `nums.py`, and WP4 replaces them with exact girths from `profiles.py`:

| sheet | class | W × H | u tile | bands: rows [y0, y1) — need → capacity (m) |
|---|---|---|---|---|
| RD01_TrimCurb | PED | 2048 × 2048 | 2.0 m | CURB_BARRIER [0,464) 0.433 → 0.438 · CURB_MOUNTABLE [464,904) 0.412 → 0.414 · CURB_LOW (ROLL/FLUSH) [904,1200) 0.267 → 0.273 · **CURB_DROP** [1200,1496) 0.270 → 0.273 · spare |
| **RD01_TrimGutter** | PED | 2048 × 1024 | 2.0 m | GUTTER [0,944) 0.900 (hard max) → 0.906 |
| RD01_Marking | PED | 2048 × 2048 | 2.0 m | LINE [0,192) 0.170 → 0.172 · LINE_WIDE [192,536) 0.320 → 0.320 · BAR [536,1312) 0.735 → 0.742 · STOP [1312,1976) 0.630 → 0.633 |
| RD01_TrimBarrier (NJ, F) | VEH | 2048 × 2048 | 4.0 m | NJ_FACE [0,464) 0.872 → 0.875 · F_FACE [464,920) 0.855 → 0.859 · TOP [920,1104) 0.320 → 0.328 · **BARRIER_END** [1104,1552) 0.840 → 0.844 |
| **RD01_TrimBarrierSV** (SINGLE_SLOPE, VERTICAL) | VEH | 2048 × 2048 | 4.0 m | **SS_FACE** [0,576) 1.086 → 1.094 · **VERT_FACE** [576,1056) 0.901 → 0.906 · TOP [1056,1240) 0.320 → 0.328 · **BARRIER_END** [1240,1824) 1.100 → 1.109 |
| RD01_TrimRail | VEH | 2048 × 1024 | 4.0 m | WBEAM_FRONT [0,264) 0.480 → 0.484 · WBEAM_BACK [264,528) · WBEAM_EDGE [528,552) |

Further rules:
- The barrier sheets at PED 1024 (option) grow to 2048 × 4096.
- Island and median curbs reuse the CURB_* bands.
- The rev-1 POST and EDGING bands are gone: posts, blockouts and terminals are UNIQUE parts in `RD01_KitRail`, and the edging unit is UNIQUE in `RD01_KitCurb`.
- BARRIER_END maps the planar end caps of precast and CIP barrier ends (u ≤ base 0.61 m within the u tile).
- The rev-1 MARKING bands overflowed (US stop 0.61 > 0.609; LINE 0.15 + skirts > 0.156). They now fit.

---

## 5. Materials, texture sets, ID/mask colours, naming, markings

### 5.1 Slots / texture sets

| slot | kind | used by | UE parent | physical material (T18) |
|---|---|---|---|---|
| RD01_Asphalt | TILING, WORLD_XY 4 m + UV2_Lane | lanes, shoulders, flush medians | M_RD01_Tiling | PM_RD01_Asphalt |
| RD01_Concrete | TILING, PATH 2 m | sidewalks, cut-throughs, MINI island | M_RD01_Tiling (UseWorldXY off) | PM_RD01_Concrete |
| RD01_Gravel / RD01_Grass / RD01_Soil | TILING | Bankett / verges, slopes, island tops / ditch bottoms | M_RD01_Tiling | PM_RD01_Gravel / _Grass / _Soil |
| RD01_TrimCurb | TRIM | curbs, island and median curbs | M_RD01_Trim | PM_RD01_Concrete |
| **RD01_TrimGutter** | TRIM | gutters | M_RD01_Trim | PM_RD01_Concrete |
| RD01_TrimBarrier / **RD01_TrimBarrierSV** | TRIM (VEH) | NJ/F and SINGLE_SLOPE/VERTICAL barriers | M_RD01_Trim | PM_RD01_Concrete |
| RD01_TrimRail | TRIM (VEH) | W-beam rail | M_RD01_Trim | PM_RD01_Metal |
| RD01_Marking | TRIM (marking sheet) | RAISED markings | **M_RD01_Marking** (opaque, Nanite-safe); DECAL → M_RD01_MarkingDecal | PM_RD01_Paint |
| RD01_Tactile | TILING PATH 0.6 m | DWS | M_RD01_Tiling | PM_RD01_Concrete |
| RD01_KitCurb, KitStrip, KitTactile, KitIsland, KitProps (PED); KitPave, KitWalk, KitCorner, KitBarrier, KitRail (VEH) | UNIQUE | Painter kit (§6.2) | M_RD01_Unique | per set (Concrete / Asphalt / Metal) |
| RD01_Udim<Piece> | UDIM (opt-in) | large unique pieces | M_RD01_Unique (VT) | as its surfaces |
| RD01_Macro_<Piece> | MACRO (Painter export only) | junction / roundabout / highway macro | child MIs `MI_RD01_<Set>__<Piece>` with UseMacro on | unchanged |

- A UNIQUE or UDIM piece has **exactly one slot**; its parts are told apart by RD01_ID.
- A TILING piece has ≤ 8 slots. A typical street has 6: Asphalt, TrimGutter, TrimCurb, Concrete, Marking, Tactile. Unused slots are pruned in `finalize_piece` (registry order kept, E22).
- `UseWorldXY` is on for Asphalt, Gravel, Grass and Soil, and **off for Concrete** (PATH, T10).

### 5.2 Colour attributes — T21, T16, T20

- **RD01_ID** (BYTE_COLOR, CORNER): the flat Part colour (§1.4). The Painter export makes it active, so it becomes layer 0 **[V]**.
- **RD01_Mask** (BYTE_COLOR, CORNER), always exported (a missing layer reads as white in UE [S]). It holds **geometry-derived terms only** (T21):
  - **R — wetness:** `0.9·clamp(1 − d_flow/0.6)` on LANE / SHOULDER / GUTTER / MEDIAN_FLUSH, 1.0 on ditch bottoms, 0 elsewhere. d_flow is the horizontal distance to the flow-line polylines (gutter flow lines, low-side paved edges of uncurbed roads, ditch bottoms).
  - **G — grime:** `0.6·clamp(1 − d_out/1.0)` + 0.3 at sidewalk back edges + a 0.15 baseline on paved and curb faces. d_out is the distance to the nearest curb toe line, **island or median footprint outline**, or barrier toe. The rev-1 lane-centre term is removed: wheel tracks and the oil strip come from UV2_Lane.
  - **B — edge blend:** 1 at every uncurbed paved/unpaved edge column (corners on both sides), falling linearly to 0 at the `blend_in` and `blend_out` columns (§2.2), 0 elsewhere. It drives the asphalt → gravel/grass crumble blend in UE.
  - **A — per-slot meaning:**
    - on TRIM, UNIQUE, Concrete and Tactile slots, **edge wear**: 1.0 on ARRIS corners and top-front curb vertices, 0.5 on barrier slope breaks, **× (1 − λ)** in ramp zones (T16);
    - on RD01_Asphalt, **lane-detail weight**: 1 on swept lanes, 0 in junction and roundabout cores, ramping across arm patches (T20).
    Values are per corner, so the meanings never bleed across slot borders.
  - **No noise in vertex colours.** Cracks, damage and macro variation come from world-space noise in the UE masters (`MF_RD01_WorldNoise`, §7.9), so they do not alias with vertex density or LOD and do not repeat on every kit instance.
- `SM_RD01_Calib_Mask`: 5 quads with R = G = B = A ∈ {0, 64, 128, 191, 255}.

### 5.3 Naming — T30

- Meshes: `SM_RD01_<Family>_<Variant>[_<Size>]`, regex `^SM_RD01(_[A-Z0-9][A-Za-z0-9]*)+$`. Families: Street, Junction, Roundabout, Island, Curb, Tactile, Tile, Rural, Highway, Barrier, GR, Bollard, Drain, Calib, Road.
- Spline road chunks: **`SM_RD01_Road_<Curve>_S<ss>_C<cc>`** (spline index, chunk index; `<Curve>` sanitised to PascalCase alnum). When the sanitised name collides with another owner's chunks, `_<4 hex of owner id>` is appended (E28).
- Children: `SM_RD01_<Piece>_Island<NN>`. Decals: `SM_RD01_<Piece>_Decal`.
- Collision `UCX_<Mesh>_NN`.
- **Sockets:** FBX objects are named **`SOCKET_<Tag>`** and **parented to the render mesh**; one render mesh per FBX keeps tags unique. Tags: Start, End, Arm0..Arm3, Leg0..Leg5. The manifest stores `tag` and `ue_socket_name` (= tag), and the importer canonicalises (§7.8).
- LOD: `<Mesh>_LOD0..2` under an Empty `<Mesh>` with `fbx_type='LodGroup'`. Sockets are parented to `<Mesh>_LOD0` [UE?].
- Painter: `<Mesh>_low` / `<Mesh>_high[_n]`; macro `<Mesh>_macro_low`.
- Materials `RD01_<Set>`, instances `MI_RD01_<Set>` (macro children `MI_RD01_<Set>__<Piece>`), masters `M_RD01_Tiling|Trim|Unique|Marking|MarkingDecal`, textures `T_RD01_<Set>_BC|_N|_ORM`, physical materials `PM_RD01_<Surface>`.
- UE folders: `/Game/RD01/{Meshes,Materials,Textures,Decals,PhysMaterials,PCG,Calibration}`.

### 5.4 Grid / tile alignment for kit pieces — T31

- Port distances and piece lengths are multiples of 4.0 m wherever the piece carries WORLD_XY surfaces. Curb units are multiples of 0.25 m.
- **Half-widths are multiples of 0.5 m.** `kit.solve_kit_section` widens the sidewalk (never below the regional default) until the back of walk lands on the 0.5 m grid **[V nums.py]**:
  - Street_2L: EU/DE 6.93 → **7.0** (w_sw 3.07, total 14.0 m); TR 7.43 → 7.5 (3.57); UK 6.70 → 7.0 (3.30); US 7.795 → 8.0 (3.865);
  - Street_4L: EU 10.18 → 10.5 (3.32).
- The building corner `B_c = (half_A, half_B)` of orthogonal kit junctions is therefore on the 0.5 m grid.
- `test_rd01_kit` asserts half-width ∈ 0.5·ℤ, B_c ∈ 0.5·ℤ², lengths ∈ 4·ℤ, and `w_curb` == DIN footprint for curbless pieces.

### 5.5 Markings approach

D13 + §3.9.
- RAISED markings are **appended to the render mesh in the kernel** (`finalize_piece`), so Blender, the FBX and the manifest all see one mesh, sockets stay valid, and custom normals are never re-joined by bpy (E22).
- DECAL markings are separate `SM_RD01_<Piece>_Decal` assets (Nanite off, `MI_RD01_Marking_Decal`).
- Painter tiles (Tile_Crosswalk) and MACRO pieces may paint markings directly; those pieces export without RAISED markings when `paint_markings=True`.

---

## 6. Kit catalogue (v1), Painter kit and spline roads

### 6.1 Catalogue (`core/kit.py`)

```python
@dataclass(frozen=True)
class PieceDef:                                  # core/specs.py
    name: str; family: str; builder: str         # 'street'|'transition'|'junction'|'roundabout'|'unit'|'tile'|'island'|'prop'|'calib'
    params: Mapping[str, object]
    uv_mode: UVMode; texture_set: str | None; td_class: TDClass
    collision: str                               # 'COMPLEX' | 'UCX' | 'NONE'
    spline_deformable: bool = False
    painter: bool = False                        # Painter-flagged → UNIQUE gates in the catalogue test
def catalogue(region: str = 'EU', td_preset: int = 1024) -> list[PieceDef]
def build_piece(defn: PieceDef, detail: Detail = Detail.LOD0) -> Piece
def solve_kit_section(base: CrossSection, grid: float = 0.5) -> CrossSection
PAINTER_SETS: Mapping[str, tuple[TDClass, int, tuple[str, ...]]]      # set → (class, tex_px, member pieces)
```

| piece | dimensions (EU defaults) | mode / set | notes |
|---|---|---|---|
| SM_RD01_Street_2L_100/200/400/800 | 2×3.25 lanes, gutter 0.50, barrier curb 0.12 (0.18 wide), sidewalk 3.07 → **W 14.0** | TILING | spline-deformable, loops ≤ 1.0 m, SKIRT |
| SM_RD01_Street_2L_Curbless_400/800 | same, with the curb footprint (toe → curb back) left open and skirted | TILING | §6.2(b) |
| SM_RD01_Street_4L_400/800 | 4×3.25, sidewalk 3.32 → W 21.0 | TILING | |
| SM_RD01_Street_2L_Median_800 | MEDIAN_FLUSH 2.0 + median island child, half 8.0 | TILING + child | R6 |
| SM_RD01_Street_2L_Crossing_800 | mid-block zebra + 2 perpendicular ramps | TILING | |
| **SM_RD01_Street_2Lto4L_3600** | 2L → 4L, urban taper 1:10 | TILING | §2.6 |
| **SM_RD01_Street_UrbanToRural_1200** | Street_2L → RQ11_Flat | TILING | §2.6 |
| SM_RD01_Junction_X_2Lx2L_R600 | ports at 16 m | **MACRO** (TILING / UDIM options) | crosswalks + 8 ramps |
| SM_RD01_Junction_X_2Lx2L_Curbless_R600 | ports at 16 m | MACRO | §6.2(b) |
| SM_RD01_Junction_T_2Lx2L_R600 | ports at 16 m | MACRO | |
| SM_RD01_Junction_X_4Lx2L_R900 | | MACRO | |
| **SM_RD01_Junction_T_RQ11** | rural T, R_edge 12 m, ports at 24 m | MACRO | give-way line on the stem |
| **SM_RD01_Junction_T_2LMedian** | median through road, refuges | MACRO + island children | §3.6 |
| SM_RD01_Roundabout_D35_4Leg | SINGLE, splitters | MACRO + island children | |
| SM_RD01_Roundabout_D28_3Leg | COMPACT | MACRO + children | |
| SM_RD01_Roundabout_D20_Mini_4Leg | MINI DOMED, painted splitters | MACRO | |
| **SM_RD01_Roundabout_D20_Mini_4Leg_UK** | MINI PAINTED, LHT | MACRO | drive-side test |
| SM_RD01_Island_Splitter_L15W3 | nose 3.0 → tail 1.0, BARRIER curb | TILING | UCX |
| **SM_RD01_Island_Median_W200_800** | 2.0 m wide, 8 m, flat ends | TILING | UCX; child of Street_2L_Median |
| SM_RD01_Curb_HB_100/050/025 | DIN 15/30 unit + 4 mm end chamfer | UNIQUE RD01_KitCurb (PED) | UCX = profile prism |
| SM_RD01_Curb_HBArc_R100Ext/R200Ext/R400Ext/**R600Ext/R900Ext**/R100Int/R200Int/R400Int | arc length 0.785 m | UNIQUE RD01_KitCurb | R600/R900 match the kit junction returns |
| SM_RD01_Curb_HBDrop_100L / _100R | 1.0 m, reveal → flush | UNIQUE RD01_KitCurb | |
| SM_RD01_Curb_Flush_100, _Mountable_100, SM_RD01_Edging_100, SM_RD01_Gutter_Channel_100 | | UNIQUE RD01_KitCurb | |
| SM_RD01_Tile_* (§6.2a) | 4 m module | UNIQUE KitPave / KitWalk / KitCorner (VEH), KitStrip (PED) | Painter road kit |
| SM_RD01_Tactile_Pad_122x061, _080x080 (UK), _060x060 (TR) | 5 mm slab, 2 mm chamfer; HIGH domes | UNIQUE RD01_KitTactile (PED) | |
| SM_RD01_Island_Nose_R050_W200 | 1.0 m half-round nose | UNIQUE RD01_KitIsland | |
| SM_RD01_Bollard_080, SM_RD01_Drain_Grate_050x030 | lathe + O-grid caps | UNIQUE RD01_KitProps | |
| SM_RD01_Rural_RQ11_400/800 (embankment h 1.0), **_RQ11_Flat_400/800**, _RQ11_Ditch_800 | 2×3.50 + 2×0.50 + 2×1.50 Bankett (+ verge 1.50 for Flat) | TILING | landscape-spline ready |
| SM_RD01_Highway_RQ31_800 | 31.0 m with NJ median | TILING (MACRO option) | |
| SM_RD01_Barrier_NJ_400 / _F_400 / _SingleSlope_400 | precast units, end chamfer | TILING (UNIQUE option RD01_KitBarrier, VEH) | UCX ≤ 2 m slices |
| SM_RD01_GR_WBeam_400 | | TILING RD01_TrimRail (VEH) | spline-deformable |
| SM_RD01_GR_Post, _GR_Blockout, _GR_End_Fishtail | EU EDSP 0.75 / 2.0; US MGS 0.787 / 1.905 | UNIQUE RD01_KitRail (VEH) | instances |
| SM_RD01_Calib_Box_1x2x3, SM_RD01_Calib_Mask, **SM_RD01_Calib_Markings** | | — | importer checks (§7.8) |

DOUBLE roundabouts are removed (R7).

**Triangle budgets (E33).**
- `data/kit_budgets.json` holds per-piece `tri_budget` values, frozen at the first green catalogue build × 1.2. Changing a budget requires review.
- Absolute family caps: Street ≤ 300 tris/m, transition ≤ 400 tris/m, Junction ≤ 40 000, Roundabout ≤ 150 000, curb unit ≤ 1 000 (LOD0), Tile ≤ 2 000, Island ≤ 3 000, props ≤ 2 000, Calib ≤ 200.
- Tests assert `tri_count() ≤ min(budget, cap)`.

### 6.2 The Painter kit — T1, T32, R11, R12

The Painter kit has three parts. Every **Painter-flagged** piece passes the UNIQUE gates in the catalogue test: no overlaps, padding, TD CV ≤ 0.05, median ±10 % of its class, hard edges on seams, `UV_RUN_DIR`, and set fit.

**(a) UNIQUE road tiles on a 4 m module.** Each set is one 4096 set. Areas are EU estimates, and the test asserts the fit (capacity 0.70 × 4096² = 11.7 Mpx):

| piece | footprint | set | class | est. area → Mpx |
|---|---|---|---|---|
| SM_RD01_Tile_Lane_400 | 4.0 × lane width (3.25); crown edge z = 0, crossfall outward; rotate 180° for the other side | RD01_KitPave | VEH | 13.0 m² → 3.4 |
| SM_RD01_Tile_Crosswalk_400 | 4.0 × lane width; bars supplied as RD01_ID regions for Painter | RD01_KitPave | VEH | 13.0 → 3.4 |
| SM_RD01_Tile_Shoulder_400 | 4.0 × (edge strip 0.5 + Bankett 1.5) | RD01_KitPave | VEH | 8.0 → 2.1 |
| SM_RD01_Tile_Sidewalk_400 | 4.0 × w_sw (3.07) | RD01_KitWalk | VEH | 12.3 → 3.2 |
| SM_RD01_Tile_SidewalkBack_400 | 4.0 × (back of walk − ramp_top) (1.53) | RD01_KitWalk | VEH | 6.1 → 1.6 |
| SM_RD01_Tile_CornerSquare_R600 | SQUARE corner from the curb-back arc to B_c, out to station 12.0 on both arms (on the 4 m grid) | RD01_KitCorner | VEH | ≈ 25 → 6.6 |
| SM_RD01_Tile_GutterCurb_400 | 4.0 × (gutter + w_curb) welded strip | RD01_KitStrip | PED | 2.7 → 2.9 |
| SM_RD01_Tile_RampInsert_400 | 4.0 × (curb back → ramp_top) (1.54), DWS region included | RD01_KitStrip | PED | 6.2 → 6.4 |

A full-width ramp tile at PED (4.0 × 3.07 m at 1024 px/m) cannot fit a 4096 set: 4096 px plus 2 pads > 4096, and even split at 2 m the islands stack to 6288 px. The PED-class ramp detail therefore lives in the ramp insert, the drop curbs and the tactile pads (R11). Tiles are SKIRT, and adjacent tiles share edge column positions, so they assemble into straight streets, crossings and rural shoulders.

**(b) Curbless variants for UNIQUE curb units.** `Street_2L_Curbless_*` and `Junction_*_Curbless_*` remove the curb band. The gutter ends at the **toe** column and the sidewalk starts at the **curb-back** column, each with a skirt down `skirt_depth` that is hidden behind the unit. The gap is exactly the DIN HB 15/30 top footprint (Radschräge setback 0.03 + top 0.15 = 0.18 = w_curb, asserted). Curb returns are filled with `Curb_HBArc_R600Ext` (90° = 12 units) or R900Ext, and ramp zones with HBDrop units.

**(c) MACRO for large pieces (R12).**
- Junctions, roundabouts and highway pieces get a macro-unique UV0 in one 4096 set. TD is solved ≤ 128 px/m with a 64–128 target: Junction_X_2Lx2L ≈ 1,000 m² → 104 px/m, Roundabout_D28_3Leg ≈ 2,240 m² → 72, Roundabout_D35_4Leg ≈ 3,080 m² → 56 (WARN `MACRO_TD_LOW`); these are capacity estimates and the packer decides. The manifest records `td_class: MACRO` and `td_px_m`.
- Painter gets `Substance/Macro/<Piece>_macro_low.fbx` with a single slot `RD01_Macro_<Piece>` (RD01_ID by Part) and paints large-scale wear, patches and stains.
- In UE the piece keeps its tiling slots. The importer creates child MIs `MI_RD01_<Set>__<Piece>` with `UseMacro` on and the macro textures on UV0, blended over the UV1/UV2 detail (§7.9).
- UDIM at VEH density is opt-in per piece (about 16 × 4K tiles for a 1000 m² junction).

**Painter hand-off settings (T32):** bake size per set = the set's `tex_px` (KitCurb 4096, KitTactile 2048, ...); `use_low_as_high = not export_high`; the shipped Painter export preset `data/painter/RD01_UE.spexp` produces `T_RD01_<Set>_BC` (RGB), `_N` (DirectX), `_ORM` (R AO, G roughness, B metallic) [SP? preset schema]; 4 mm end chamfers on precast units (§2.5) let baked edge wear show unit joints; tactile pads export a domed `_high` (§3.11).

KitCurb capacity: ≈ 8.4 m² visible at PED 1024 (with the R600/R900 arcs) → 8.8 Mpx ≤ 11.7 (4096).

### 6.3 Spline road from a Blender curve (`core/road.py` + `blender/ops_build.py`)

Operator `rd01.road_build` on the active curve object:
1. `curve_input.read_curve(ob)` → `CurveSpline` records (world-space Bezier segments / poly points, closed flag, per-point ground offsets). The bpy layer never builds Rails.
2. **Core** `road.rails_from_splines(splines, settings)`:
   - Bezier → `Rail.from_bezier(knot_policy=settings.knot_policy, min_radius=settings.min_radius)` (E10);
   - Poly → `fillet_polyline(radius=min_radius, clothoid_A=…)` (clothoids for rural and highway presets, T23);
   - closed splines → ERROR (v1);
   - each open spline is one road (spline index `S<ss>`).
3. Section from the preset + overrides → `compile_section`. Rail checks, vertical checks, superelevation (rural/highway) with ports as crown targets.
4. `sample_stations` (forced chunk ends ≤ 64 m, ports, lead-ins, dash ends).
5. `sweep_section` (SKIRT, end curtains on free ends). Ground-following side slopes when `settings.ground` is set (`blender/ground.py` provides the height function, T24).
6. `finalize_piece` (markings merged, slots pruned, FIELD diagonals, normals, UV1/UV2, masks, validate) on the whole road. Then split into chunks, rebase UVs per chunk, and set chunk origins to their first centreline point (translation only).
7. Guardrail instances per chunk, shown through one GN instancer per road (§3.10).
8. `scene.commit_generated(owner=curve, ...)` (§8.3). Linked port ends are re-snapped when their junction rebuilds (§3.12).

`rd01.snap_curve_to_port` moves the end control point to the port, inserts the straight level lead-in (§3.12), and records the link.

---

## 7. Export

### 7.1 Export profiles

| profile | content | colour layer 0 | files (under `current/`, §7.3) |
|---|---|---|---|
| UE (default) | per piece or chunk: render mesh (RAISED markings already merged by the kernel) + UCX_ + SOCKET_ (+ LodGroup if non-Nanite); island children as their own FBX | RD01_Mask | `Meshes/<Mesh>.fbx` |
| SUBSTANCE | per UNIQUE/UDIM set: all its catalogue pieces `_low` (exploded along +Y, 1 m gaps), optional `_high`; per MACRO piece: `<Piece>_macro_low` | RD01_ID | `Substance/<Set>/<Set>_low.fbx`, `<Set>_high.fbx`, `<Set>.painter.json`; `Substance/Macro/<Piece>_macro_low.fbx` |
| BOTH | both | — | — |
| options | `nanite` (True), `marking_mode` RAISED/DECAL, `baked_lighting` (adds UV3), `lods` (non-Nanite), `export_high`, `paint_markings` (Painter tiles / MACRO) | | |

### 7.2 FBX writer (`blender/export_fbx.py`) — E21, E22, E23, E24, E34, T30

```python
FBX_KW = dict(
    use_selection=False, use_active_collection=False,           # collection=<temp> is passed per call (E21)
    object_types={'MESH', 'EMPTY'},
    axis_forward='Y', axis_up='Z', apply_unit_scale=True, global_scale=1.0,
    apply_scale_options='FBX_SCALE_NONE', bake_space_transform=True,          # [V]
    use_mesh_modifiers=True, mesh_smooth_type='EDGE', use_tspace=True,         # [V]
    use_triangles=False, colors_type='SRGB', prioritize_active_color=True,     # [V]
    use_custom_props=False, add_leaf_bones=False, bake_anim=False,
    path_mode='STRIP', embed_textures=False, batch_mode='OFF', use_metadata=True)
# FbxExpect is in core/specs.py (E4)
@dataclass(frozen=True)
class FbxExpect:
    render: str                                  # render mesh model, or the LodGroup null
    lod_models: tuple[str, ...] = ()             # '<Mesh>_LOD0', … when lods (E24)
    ucx: tuple[str, ...] = ()
    sockets: Mapping[str, tuple[Vec3, float]] = field(default_factory=dict)   # 'SOCKET_<Tag>' → (Lcl Translation cm, yaw°)
    uv_layers: tuple[str, ...] = UV_LAYERS
    first_color: str = 'RD01_Mask'
    materials: tuple[str, ...] = ()              # exact names, slot order (E23)
    normals_sample: tuple[tuple[int, Vec3], ...] = ()    # (loop index, expected normal) checks
def export_piece_ue(ob: bpy.types.Object, out_dir: Path, profile: ExportProfile) -> dict      # manifest record
def export_texture_set(objs, set_name: str, out_dir: Path, high: bool = False) -> Path
def export_macro_piece(ob, out_dir: Path) -> Path
def verify_fbx(path: Path, expect: FbxExpect) -> list[Issue]
```

Procedure per piece (UE):
1. Preconditions: Object mode, scene unit scale 1.0, no validator ERROR on the piece, name regex, and every slot material an **exact-name local** material. `ensure_materials` reuses exact names, **refuses linked (library) materials** with an ERROR, and never creates `.001` names (E23).
2. **Temp collection** `RD01_EXPORT_<8hex>`, linked to the scene collection, **included** (not excluded, not hidden). Call `view_layer.update()` after building the temps. An excluded collection exports unevaluated transforms: sockets lose their `Lcl Translation/Rotation` **[V rev2/bchk4.py]**.
3. **Name holds:** any existing object or mesh that owns a target name (`<Mesh>`, `UCX_<Mesh>_NN`, `SOCKET_<Tag>`, LOD names) is renamed `<name>__rd01hold` for the duration and restored in `finally`. Temps get exact names, never `.001`.
4. Temp objects:
   - render mesh = `ob.data.copy()` (the generated mesh is already the finalized kernel mesh with merged markings and pruned slots; no `new_from_object`, no bpy joins, E22), plus a `TRIANGULATE` modifier (`quad_method='FIXED'`, `ngon_method='BEAUTY'`, `min_vertices=4`, `keep_custom_normals=True`);
   - active colour = RD01_Mask;
   - UCX objects from the piece's hidden COLLISION children (created by `commit_generated`);
   - `SOCKET_<Tag>` empties **parented to the render mesh** (T30);
   - with `lods`: LodGroup Empty `<Mesh>`, children `<Mesh>_LOD0..2`, sockets parented to `_LOD0` [UE?].
5. `bpy.ops.export_scene.fbx(filepath=…, collection=<temp>, **FBX_KW)`. No `select_set` is needed (E21). Then in `finally`: delete temp objects **and their meshes**, restore held names, the active object and the mode.
6. `verify_fbx` (parse with `io_scene_fbx.parse_fbx`; **`import bpy` first**, because a bare `import io_scene_fbx.parse_fbx` hung here **[V]**):
   - GlobalSettings (Up 2/+1, Front 1/−1, Coord 0/+1, UnitScaleFactor 1.0);
   - no `Lcl Scaling`;
   - Model names exactly {render or LodGroup + LOD models} ∪ ucx ∪ sockets;
   - every polygon ≤ 3 vertices; `LayerElementTangent` present; smoothing ByEdge;
   - first colour layer RD01_Mask; UV layer names in contract order; Material names exactly `expect.materials` (E23);
   - **socket `Lcl Translation`/`Lcl Rotation` equal the manifest within 0.01 cm / 0.01°**;
   - sampled normals within 1e-3.
   Any failure aborts the staged export (§7.3).
7. **Children (E34):** island children are exported as their own FBX (`SM_RD01_<Piece>_Island<NN>`, with UCX). The manifest lists them under the parent's `children` with transforms relative to the parent origin.
8. `tris` in the manifest = the core `QMesh.tri_count()` stored in piece meta at finalize, never counted in bpy (E22).

### 7.3 Stable export folder (`blender/export_folder.py`) — T29

```python
class ExportFolder:
    def __init__(self, base: Path, scene_name: str)          # root = <base>/RD01_<scene>/
    def recover(self) -> list[Issue]                          # finish or roll back an interrupted swap
    def stage(self) -> Path                                   # root/.staging_<8hex>/
    def check_uv0(self, manifest: dict, locks: Mapping[str, str]) -> list[Issue]   # vs current/RD01_manifest.json + kit locks
    def commit(self) -> Path                                  # → root/current/ ; archive → root/revisions/<YYYYmmdd_HHMMSS>_<4hex>/
    def abort(self, reason: str) -> Path                      # EXPORT_FAILED.txt in staging; current/ untouched
```
- Exports always go to the **stable** `root/current/`: `Meshes/`, `Substance/<Set>/`, `Substance/Macro/`, `Trims/`, `RD01_manifest.json`, `README_SUBSTANCE.md`. Painter's mesh reload and UE reimport keep one fixed source path.
- Commit:
  1. verify everything in staging;
  2. `check_uv0` (a locked set whose uv0_hash changed is an ERROR, §8.3);
  3. copy staging → `revisions/<stamp>/`;
  4. rename `current/` → `.old_<hex>/`;
  5. rename staging → `current/`;
  6. delete `.old_<hex>/`.
- If step 4 or 5 fails (on Windows a file inside `current/` is still open), the result is ERROR "close the file in Painter/UE and export again", with staging kept. `recover()` restores `.old_*` when `current/` is missing.
- Revision folders are never overwritten. `rd01.export_prune_revisions` (keep N) is the only operation that deletes them.

### 7.4 Collision — T18

```python
def ucx_profile_prisms(prof: ClosedProfile, rail: Rail, max_len: float = 2.0) -> list[QMesh]
def ucx_boxes(bounds) -> list[QMesh]
def ucx_outline_prism(outline: Sequence[Vec2], z0: float, z1: float) -> QMesh
```
- Roads, junctions and roundabouts → COMPLEX (`CTF_USE_COMPLEX_AS_SIMPLE`), with three importer actions:
  - **the RD01_Marking section's collision is disabled** (`StaticMeshEditorSubsystem.enable_section_collision(mesh, False, 0, <marking section index>)` [UE?]), so raised markings are not physical ridges;
  - **Nanite fallback at 100 %** (`fallback_percent_triangles = 1.0`, `fallback_relative_error = 0.0` [UE? names per version]), so complex collision comes from the full mesh;
  - **physical materials per slot** through the MI (`PM_RD01_<Surface>`, §5.1).
- Barriers, islands, curb units, bollards and guardrail → UCX (quads, closed, convex). Spline-deformable pieces slice UCX into ≤ 2 m segments with a 5 mm gap [S].
- **Calibration** `SM_RD01_Calib_Markings` (a 4 × 4 m flat asphalt patch with one RAISED 0.15 m line): the importer spawns it in the editor world, line-traces across the line, and asserts that the hit z is constant within 1 mm and that the hit physical material is `PM_RD01_Asphalt`. It then destroys the actor without saving the level [UE?].

### 7.5 Sockets, ports, spline-mesh, landscape and PCG metadata — T17

- Sockets follow D10. Manifest entries are `{"tag", "ue_socket_name", "location_cm", "quat_xyzw", "yaw_deg"}`.
- Spline-deformable pieces: `{"forward_axis": "X", "boundary_min_cm": 0, "boundary_max_cm": L·100, "loops_max_spacing_m": 1.0, "max_strain": 0.10, "r_min_m": half_width/max_strain}`. Street_2L (half 7.0) gives **r_min 70 m** (rev 1 claimed 10 m, at which the inner back of walk compresses to 31 %). Below r_min, use generated spline roads instead of SplineMeshComponents.
- Landscape spline: `{"forward": "X", "up": "Z", "center_h": false, "scale_to_width": false, "width_cm": W·100}` for **every curbed or barrier section**. `true` is allowed only for symmetric uncurbed sections (RQ11_Flat), because otherwise curb and sidewalk widths would rescale and asymmetric sections would re-centre.
- **Nanite on spline meshes:** the importer logs `r.Nanite.AllowSplineMeshes` and sets the Nanite fallback to 100 % on spline-deformable pieces, because without the CVar the deformed fallback mesh is what renders [UE?].
- PCG: `{"symbol", "mesh", "length_cm"}` per spline piece, arm sockets for junctions, and instance groups.

### 7.6 LODs / Nanite — T34

- Nanite profile (default): LOD0 only, `build_nanite=True`, `nanite_triangle_threshold=0` (5.7+) [S], **fallback 100 % on COMPLEX and spline-deformable pieces**, and `explicit_tangents=True` for UNIQUE where available [S].
- **SKIRT pieces** (all paved-surface pieces by default) set `generate_distance_field_as_if_two_sided = True` (build settings) for Lumen [UE?].
- Non-Nanite: kernel LODs (LOD1: arris 1 segment, chord ×4, spacing ×2; LOD2: no arris, chord ×16, spacing ×4); silhouette columns kept; file LODs imported. WARN about the UE 5.5 spline-mesh LOD seam bug [S].
- Detail.HIGH: arris segments 8, tactile domes, rounded end chamfers. Used for `_high` Painter meshes, which are exempt from quad and UV gates.

### 7.7 Manifest (`core/manifest.py`, `RD01_manifest.json`)

```python
SCHEMA = 'rd01.kit/1.1'
def blender_to_ue(loc_m: Vec3, quat_wxyz) -> tuple[Vec3, tuple[float, float, float, float]]   # ((100x, −100y, 100z), (w, −x, y, −z))
def canonical_socket_name(tag: str) -> str          # = tag
def piece_record(piece: Piece, file: str, profile: ExportProfile) -> dict      # ExportProfile from core/specs.py (E1)
def build_manifest(pieces, placements, instances, settings: dict) -> dict
```
```json
{
 "schema": "rd01.kit/1.1", "generator": "RD01 Road Studio 0.1.0", "blender": "4.5.14",
 "units": "cm in FBX; metres in *_m fields", "axes": "Blender +X fwd/+Y left/+Z up; FBX Y-fwd/Z-up identity; UE (x,-y,z)",
 "region": "EU", "drive_side": "RHT", "td_classes": {"PED": 1024, "VEH": 512},
 "profile": {"kind": "UE", "nanite": true, "marking_mode": "RAISED"},
 "materials": {
   "RD01_Asphalt": {"kind": "TILING", "uv": "UV1_Tile", "lane_uv": "UV2_Lane", "tile_size_m": 4.0, "lane_tile_m": 8.0,
                    "world_xy": true, "parent": "M_RD01_Tiling", "phys_material": "PM_RD01_Asphalt",
                    "mask": {"R": "wet", "G": "grime", "B": "edge_blend", "A": "lane_weight"}},
   "RD01_Concrete": {"kind": "TILING", "uv": "UV1_Tile", "path": true, "tile_size_m": [2.0, 2.0], "joint_module_m": [1.0, 1.0],
                     "world_xy": false, "parent": "M_RD01_Tiling", "phys_material": "PM_RD01_Concrete"},
   "RD01_TrimCurb": {"kind": "TRIM", "sheet": "RD01_TrimCurb", "parent": "M_RD01_Trim", "phys_material": "PM_RD01_Concrete",
                     "mask": {"A": "edge_wear"}},
   "RD01_Marking": {"kind": "TRIM", "sheet": "RD01_Marking", "parent": "M_RD01_Marking", "phys_material": "PM_RD01_Paint",
                    "section_collision": false},
   "RD01_KitCurb": {"kind": "UNIQUE", "uv": "UV0_Main", "td_class": "PED", "td_px_m": 1024, "tex_px": 4096, "pad_px": 32,
                    "parent": "M_RD01_Unique", "phys_material": "PM_RD01_Concrete",
                    "textures": {"BC": "T_RD01_KitCurb_BC", "N": "T_RD01_KitCurb_N", "ORM": "T_RD01_KitCurb_ORM"}}},
 "trim_sheets": {"...": "generate_layouts() output, incl. sheet_w_px/sheet_h_px/u_tile_m/td_class and bands from the top"},
 "pieces": [{
   "name": "SM_RD01_Street_2L_400", "file": "Meshes/SM_RD01_Street_2L_400.fbx", "family": "Street",
   "uv_mode": "TILING", "td_class": null, "slots": ["RD01_Asphalt", "RD01_TrimGutter", "RD01_TrimCurb", "RD01_Concrete", "RD01_Marking"],
   "uv0_hash": "…", "bounds_cm": [[0, -700, -55], [400, 700, 5]], "tris": "<int: QMesh.tri_count()>", "ucx": 0, "collision": "COMPLEX",
   "sockets": [{"tag": "Start", "ue_socket_name": "Start", "location_cm": [0, 0, 0], "quat_xyzw": [0, 0, -1, 0], "yaw_deg": 180},
               {"tag": "End", "ue_socket_name": "End", "location_cm": [400, 0, 0], "quat_xyzw": [0, 0, 0, 1], "yaw_deg": 0}],
   "section_hash": "…", "port_phase": {"Start": {"R.toe": 0.0, "R.curb_back": 0.0}, "End": {"R.toe": 0.0, "R.curb_back": 0.0}},
   "spline": {"forward_axis": "X", "boundary_min_cm": 0, "boundary_max_cm": 400, "max_strain": 0.10, "r_min_m": 70.0},
   "landscape_spline": {"forward": "X", "up": "Z", "center_h": false, "scale_to_width": false, "width_cm": 1400},
   "pcg": {"symbol": "Street2L", "length_cm": 400},
   "nanite": {"enabled": true, "fallback_percent_triangles": 1.0, "explicit_tangents": false},
   "distance_field_two_sided": true, "full_precision_uvs": true,
   "normals": "IMPORT_NORMALS_AND_TANGENTS", "lods": 1, "children": [], "issues": []}],
 "placements": [{"asset": "SM_RD01_Road_Main_S00_C00", "group": "RD01_Road_Main", "location_cm": [0, 0, 0], "quat_xyzw": [0, 0, 0, 1]}],
 "instances": [{"asset": "SM_RD01_GR_Post", "group": "RD01_Road_Main", "chunk": "SM_RD01_Road_Main_S00_C00", "transforms_cm": [["…"]]}],
 "calibration": {"box": "SM_RD01_Calib_Box_1x2x3", "expect_bounds_cm": [[0, -200, 0], [100, 0, 300]],
                 "markings": "SM_RD01_Calib_Markings", "mask": "SM_RD01_Calib_Mask"},
 "painter_sets": {"RD01_KitCurb": {"normal_format": "DirectX", "tangent_per_fragment": true, "uv_tiles": false,
   "export_preset": "RD01_UE.spexp", "export_padding": "Dilation infinite", "bake_size": 4096,
   "dilation_px": 32, "id_dilation_px": 4, "id_source": "Vertex Color (RD01_ID)", "use_low_as_high": true,
   "relative_to_bbox": false, "max_frontal": 2.0, "max_rear": 2.0, "distance_units": "cm",
   "average_normals": true, "ao_self_occlusion": "By Mesh Name", "ignore_backface": "By Mesh Name", "match": "By Mesh Name"}},
 "issues": []
}
```
Unused slots are pruned (the example street has no Tactile slot), so UE's slot-count check matches (E22). `bake_size` is per set (= tex_px), and `use_low_as_high = not export_high` (T32).

### 7.8 UE editor importer (`unreal/RD01_Import.py`) **[UE?: not executed here]** — T18, T28, T30, T34, E25

Top level: `main(manifest_path, dest='/Game/RD01', place=False, use_pcg=False)`.
1. Log the engine version and the CVars `Interchange.FeatureFlags.Import.FBX` and `r.Nanite.AllowSplineMeshes`. Load the manifest and check the schema.
2. **Calibration:** box bounds (abort on mismatch), mask strip decoding, marking line trace (§7.4).
3. Per piece, an `AssetImportTask`:
   - **Interchange first** (pipeline stack override, as in rev 1: import_collision_according_to_mesh_name, one_convex_hull_per_ucx, build_nanite, recompute_normals False, use_full_precision_u_vs for TILING, IVCIO_REPLACE, import_lods). Every property is set through `_set()`, which logs instead of failing.
   - **Legacy fallback (E25):** with Interchange active, an `FbxImportUI` is ignored. The fallback therefore reads the CVar value, runs `SystemLibrary.execute_console_command(None, 'Interchange.FeatureFlags.Import.FBX 0')`, imports with `FbxImportUI` (rev-1 options), and restores the previous value in `finally`. Both values are logged.
4. **Post-import** via `StaticMeshEditorSubsystem`:
   - Nanite settings, plus **fallback 100 %** on COMPLEX and spline-deformable pieces;
   - collision trace COMPLEX, and **RD01_Marking section collision off**;
   - two-sided distance field on SKIRT pieces;
   - `light_map_coordinate_index=3` when UV3 exists;
   - **socket canonicalisation (T30):** for each manifest tag, collect sockets named `<tag>`, `SOCKET_<tag>` or `*_<tag>`; keep one, rename it to `ue_socket_name`, update its transform in place, and delete the rest. Assert exactly one socket per tag;
   - assert slot count and UCX count == manifest.
5. **Materials:**
   - create missing `PM_RD01_<Surface>` PhysicalMaterials (friction / restitution defaults per surface; surface types are left to the project and logged);
   - create or reuse `MI_RD01_<Set>` (parent = `M_RD01_*`, built by `RD01_Materials.py` if missing) with `TileSizeCM`, `UseWorldXY`, the textures if `T_RD01_<Set>_*` exist, and `PhysMaterial`;
   - MACRO pieces get child MIs `MI_RD01_<Set>__<Piece>` with `UseMacro` and the macro textures;
   - assign by slot name.
6. **Placement** (`place=True`):
   - one actor per manifest `group`, with StaticMeshComponents for placements and **one InstancedStaticMeshComponent per (asset, chunk)** for instances (T28; never one StaticMeshActor per post);
   - children are placed relative to their parent;
   - `use_pcg=True` instead writes a PCG graph `PCG_RD01_<group>` from the manifest;
   - the level is **never saved**; only assets are saved.
7. Write `RD01_import_report.json` next to the manifest.

### 7.9 UE master materials (`unreal/RD01_Materials.py`) — T19 **[UE?]**

`build_masters(dest='/Game/RD01/Materials', overwrite=False) -> dict[str, str]` builds the material functions and masters through `unreal.MaterialEditingLibrary` (`create_material_expression`, `connect_material_expressions`, `connect_material_property`, `recompile_material`):
- **MF_RD01_WorldUV — large-world-coordinate-safe world UV:** `uv = (CameraRelativeWorldPosition.xy + frac(CameraPositionWS.xy / TileSizeCM)·TileSizeCM) / TileSizeCM`, with **v negated** (UE Y = −Blender Y), so the projection equals the Blender-side UV1 world mapping. The frac acts on a per-frame LWC constant, and the per-pixel term is small and continuous: no precision loss far from the origin and no derivative seam at a per-pixel frac wrap.
- **MF_RD01_WorldNormal — world-XY normal transform:** a normal map sampled with world UVs is rebuilt as `N_ws = normalize(T_w·n.x + B_w·n.y + N_v·n.z)`, where T_w is world +X projected onto the vertex tangent plane and `B_w = N_v × T_w` (with the sign matching the v flip). It is then transformed **World → Tangent** before blending with tangent-space layers. Mesh tangents follow piece-local UV0, so without this, lighting would rotate with piece yaw. Smoke test: a kit street rotated 90° shows the same lighting direction on its asphalt.
- **MF_RD01_AntiTile:** a macro second sample (scale × 0.37, rotated 37°) blended by world noise, plus an optional **stochastic hex tiling** (Custom HLSL, 3-tap hex blend) behind the static switch `UseHexTiling`.
- **MF_RD01_WorldNoise:** world-space value noise for cracks, damage and macro variation. It replaces the removed vertex-colour noise (T21).
- **MF_RD01_DecodeMask:** reads RD01_Mask (stored as UNORM bytes, so 64 → 0.251, checked by the calibration strip) with per-master channel semantics (§5.2).
- **M_RD01_Tiling:** UV1 or world UV (`UseWorldXY`), WorldNormal, AntiTile, lane detail on **UV2** weighted by A (asphalt), edge blend by B, wetness R, grime G, optional `UseMacro` (UV0 macro BC/N/ORM: BC ×2 overlay, reoriented-normal blend, ORM multiply/overlay).
- **M_RD01_Trim:** UV1 trims, A = edge wear, R/G as above.
- **M_RD01_Unique:** UV0 BC/N/ORM, optional UV1 detail normal, A wear.
- **M_RD01_Marking:** **opaque** (not masked), no WPO/PDO (**Nanite-safe**), UV1 on the marking sheet, wetness from R. Used for RAISED markings.
- **M_RD01_MarkingDecal:** DBuffer deferred decal (DECAL profile).

UV index per kind: Tiling UV1 / world + UV2 + UV0 (macro); Trim UV1; Unique UV0 (+ UV1 detail); Marking UV1. `tests/test_rd01_unreal_stub.py` runs both scripts against a fake `unreal` module that records calls.

### 7.10 Substance hand-off — T32

- One Painter project per set FBX (PER_SET default; SINGLE optional). UDIM sets are always separate (the UV tile mode is fixed at project creation [S]). Each MACRO piece is its own project.
- `<Set>.painter.json` = `painter_sets[<Set>]` (bake size = tex_px, `use_low_as_high = not export_high`) + TD class and pad + piece list + uv0_hash.
- `data/painter/RD01_UE.spexp` is copied to `current/Substance/`, and README_SUBSTANCE.md explains installing it into Painter's `assets/export-presets` [SP?].
- Designer gets `Trims/*.json` + guide SVG/PNG, the tiling table (physical sizes), the lane-material spec (8 m × lane width, v = 0.5 lane centre, tyre tracks at 0.25 / 0.75), and the concrete joint module.

---

## 8. Blender UI, properties, presets, regeneration safety

### 8.1 Property groups (`blender/props.py`) — E10, E17, E18, E20

```python
ADDON_ID = __package__.rpartition('.')[0]    # root package: 'rd01_road_studio' or 'bl_ext.user_default.rd01_road_studio' (E17)
class RD01_SceneSettings(PropertyGroup):            # Scene.rd01
    region: EnumProperty(items=REGIONS)             # drive side follows the region preset (shown read-only)
    texel_density: EnumProperty(items=[('1024','PED 1024 px/m',''),('512','Vehicle 512 px/m','')])
    export_dir: StringProperty(subtype='DIR_PATH'); export_profile: EnumProperty(UE/SUBSTANCE/BOTH)
    nanite: BoolProperty(default=True); marking_mode: EnumProperty(RAISED/DECAL); baked_lighting: BoolProperty()
    lods: BoolProperty(); export_high: BoolProperty(); substance_layout: EnumProperty(PER_SET/SINGLE); paint_markings: BoolProperty()
    keep_revisions: IntProperty(default=20); status: StringProperty(); last_report: StringProperty()
class RD01_PortLink(PropertyGroup): end: EnumProperty(START/END); owner_id: StringProperty(); port: StringProperty()
class RD01_GroundOffset(PropertyGroup): point_index: IntProperty(); height: FloatProperty()
class RD01_RoadSettings(PropertyGroup):             # Object.rd01_road (curves)
    preset: EnumProperty(items=_cached_section_items); section_json: StringProperty()
    lanes_left/right: IntProperty(1..4); lane_width: FloatProperty; curb_type: EnumProperty; sidewalk_width: FloatProperty
    marking_pattern: EnumProperty(items=_cached_pattern_items); superelevation: BoolProperty; design_speed: FloatProperty
    closure: EnumProperty(OPEN/SKIRT/SOLID, default SKIRT); chunk_max: FloatProperty(64); max_spacing: FloatProperty(2.0)
    min_radius: FloatProperty(default=10.0)         # E10: used by fillet_polyline and knot FILLET policy
    knot_policy: EnumProperty(ERROR/FILLET); guardrail: EnumProperty(NONE/LEFT/RIGHT/BOTH)
    ground_object: PointerProperty(type=Object, poll=_is_mesh); ground_offsets: CollectionProperty(type=RD01_GroundOffset)
    links: CollectionProperty(type=RD01_PortLink)   # owner ids are ID custom properties (§8.3), not PropertyGroup fields
class RD01_JunctionSettings(PropertyGroup):         # Object.rd01_junction (root Empty)
    kind: EnumProperty(T/X); main_preset, side_preset: EnumProperty(items=_cached_section_items)
    corner_radius: FloatVectorProperty(size=4); arm_skew: FloatVectorProperty(size=4, min=-15, max=15)
    sidewalk_mode: EnumProperty(AUTO/SQUARE/CONCENTRIC); crosswalks: BoolProperty; ramps: BoolProperty
    arm_length: FloatProperty; priority: EnumProperty; curbless: BoolProperty; uv_mode: EnumProperty(TILING/MACRO/UDIM)
class RD01_RoundaboutSettings(PropertyGroup):       # Object.rd01_roundabout
    kind (MINI/COMPACT/SINGLE), mini_island (DOMED/PAINTED), icd, circ_width, apron_width, legs (3..5),
    leg_headings (FloatVectorProperty(size=5)), entry_radius, exit_radius, entry_width, exit_width,
    splitters: BoolProperty, leg_preset: EnumProperty(items=_cached_section_items), uv_mode
class RD01_KitSettings(PropertyGroup):              # Object.rd01_kit on the 'RD01_Kit_<region>' root Empty (UI only)
    region: StringProperty(); families: StringProperty()
class RD01_PieceSettings(PropertyGroup):            # Object.rd01_piece (UI display only)
    uv_mode: EnumProperty; texture_set: StringProperty(); td_class: StringProperty()
# Ownership, hashes and UV0 locks are ID custom properties managed by blender/scene.py (WP6), NOT PropertyGroups,
# so the bpy core I/O and export packages work before props.py (WP15) registers anything:
#   generated object: ob['rd01_generated']=1, ob['rd01_owner_id']=str, ob['rd01_owner_ref']=<owner Object> (ID pointer, E27),
#                     ob['rd01_role'] in PIECE/CHILD/COLLISION/INSTANCER/PORT, ob['rd01_piece_json']=str
#   mesh:             me['rd01_hash']=str (E26)
#   kit / junction / roundabout root: root['rd01_uv0_locks'] = {set_name: uv0_hash} (E29)
# [V rev2/idprop.py] an ID custom property holds an Object reference, survives on the referencing object,
# and reads as None after the owner is deleted (orphan detection).
class RD01_Preferences(AddonPreferences):
    bl_idname = ADDON_ID                            # never __package__ of the sub-package (E17)
    user_presets_dir: StringProperty(default='')    # '' → presets.user_dir() resolves lazily (E18)
```
- **Presets directory (E18).** `presets.user_dir()` first tries `bpy.utils.extension_path_user(ADDON_ID, path='presets', create=True)`. That raises `ValueError` for a legacy install or the test harness [V], so it then falls back to `bpy.utils.user_resource('SCRIPTS', path='presets/rd01_road_studio', create=True)` [V resolves]. It is never used as a property default.
- **Dynamic enums (E20).** Item callbacks return module-level cached lists (`_ENUM_CACHE[key]`), rebuilt only when presets change. The lists stay referenced, so Blender's UI never sees freed strings.
- **Imports (E19).** Only relative imports are used inside the package.

### 8.2 Operators and panels

Operators (`bl_options={'REGISTER','UNDO'}`; each catches exceptions, writes `Scene.rd01.status`, reports ERROR and leaves the scene unchanged):
`rd01.road_build`, `rd01.road_remove`, `rd01.junction_add`, `rd01.junction_rebuild`, `rd01.roundabout_add`, `rd01.roundabout_rebuild`, `rd01.kit_build`, `rd01.pack_texture_sets`, `rd01.uv0_unlock`, `rd01.preview_colors`, `rd01.snap_curve_to_port`, `rd01.validate`, `rd01.select_issues`, `rd01.export`, `rd01.export_prune_revisions`, **`rd01.purge_orphans`**, `rd01.preset_save`, `rd01.preset_load`.

Panels (VIEW_3D › Sidebar › "RD01"):

| panel | contents |
|---|---|
| RD01 Road Studio | region (+ drive side), TD, unit check |
| Spline Road | curve settings, ground object, Build / Rebuild / Remove, links |
| Junction | Add T / X, active root settings |
| Roundabout | Add, active root settings |
| Kit | family checkboxes, Build Kit (owner = kit root) |
| Texturing | texture sets, Pack, UV0 locks, colour preview |
| Export | dir, profile, options, Export, revisions, last report |
| Validate | run, issue list with "Select" buttons, Purge orphans |

UI code never calls view-dependent operators (headless safety [V research]).

### 8.3 Regeneration safety (`blender/scene.py`) — E26, E27, E28, E29

```python
def owner_id(ob) -> str                                 # minted in bpy (uuid4 hex; core never mints ids)
def ensure_unique_owner(ob) -> list[Issue]              # Shift+D detection (E27)
def commit_generated(context, owner, built: Sequence[BuiltObject], collection_name: str) -> list[bpy.types.Object]
def remove_generated(owner) -> int
def purge_orphans(context) -> int
def mesh_content_hash(me: bpy.types.Mesh) -> str        # E26
def kit_root(context, region: str) -> bpy.types.Object  # 'RD01_Kit_<region>' Empty
def get_locks(root) -> dict[str, str]; def set_lock(root, set_name: str, uv0_hash: str | None) -> None
```
- **Content hash (E26).** `mesh_content_hash` is blake2b over:
  - the float32 bytes of vertex coordinates, with −0.0 normalised to +0.0;
  - polygon loop starts, totals and loop vertex indices;
  - `material_index`;
  - the float32 bytes of UV0, UV1 and UV2;
  - the sorted edge keys flagged `sharp_edge` and `uv_seam`.
  It is computed **in bpy right after `qmesh_to_bpy`** and stored as `Mesh.rd01_hash`, so float64→float32 rounding and chunk translation can no longer make an unedited mesh look edited. Test: an unedited rebuild creates no `_edited` objects.
- **Owners (E27).** Generated objects store `rd01_owner_ref` (an ID-pointer custom property) as well as `rd01_owner_id`.
  - Before every build, `ensure_unique_owner` checks for other objects carrying the same owner_id. The object referenced by existing generated objects keeps the id. The duplicate (Shift+D) re-mints. If neither is referenced, the later name in sort order re-mints.
  - Owners whose world scale ≠ 1 (tolerance 1e-6, negative scale included) are refused with ERROR "apply scale".
  - Kit builds are owned by the `RD01_Kit_<region>` root Empty.
  - `purge_orphans` removes generated objects (and their meshes) whose owner is gone or whose owner_ref/owner_id disagree. Edited ones are kept as `_edited`.
- **Staging and names (E28).**
  1. Build everything into `RD01_STAGE_<8hex>` under temporary names `__rd01tmp_<hex>_<final>` (objects and meshes).
  2. **Before deleting anything:** if any final name is held by an object or mesh this owner does not own → ERROR, and nothing changes.
  3. Remove this owner's old generated objects **and their meshes** (meshes with no remaining users). Edited ones (hash mismatch) are kept, renamed `<name>_edited`, stripped of ownership, and reported as WARN.
  4. Rename temps to their final names and assert `ob.name == final` and `ob.data.name == final` (no `.001`).
  5. Move them into the owner's generated collection and drop the staging collection.
  An exception before step 3 removes only staging objects (PK01 pattern). User children of generated objects are re-parented with their world matrices preserved.
- **UV0 lock lifecycle (E29).**
  - Locks live **per texture set on the kit root** (`root['rd01_uv0_locks']`), not on piece objects that rebuilds delete. MACRO pieces store their lock on their junction or roundabout root.
  - Atlas membership is **the set's full catalogue membership** (`kit.PAINTER_SETS`), whatever families the user ticked: the core always packs the whole set and creates only the requested objects, so partial builds never change UV0.
  - The kit build computes each set's new uv0_hash in core **before staging**, and refuses (ERROR, with Unlock instructions) if a locked set would change. The export repeats the check against `current/` (§7.3).
- No import-time scene mutation. `register()` is re-entrant. `blender/__init__.py` (WP15) concatenates each module's `CLASSES` tuple, unregisters in reverse order, and deletes pointer properties before their classes [V research].

---

## 9. Validation and test plan

### 9.1 Validator (`core/validate.py`) — T14, T27, E7, E11, E16

```python
@dataclass
class Metrics: quads: int; tris: int; ngons: int; nonmanifold: int; open_edges_untagged: int; winding_errors: int
               negative_volumes: int; degenerate: int; tjunctions: int; duplicates: int; min_angle: float; max_aspect: float
               max_warp_m: float; poles_bad: int; flipped_uv: dict[str, int]; uv_overlaps: int; uv_out_of_bounds: int
               trim_v_out: int; unused_slots: int; min_gutter_px: float; min_border_px: float; td_median: float; td_cv: float
               sharp_off_seam: int; marking_clearance_min: float; euler_ok: bool
@dataclass(frozen=True)
class Gates: closure: Closure; uv_mode: UVMode; tex_px: int = 2048; pad_px: int = 16; td: float = 1024
             min_angle: float = 10.0; max_aspect: float = 20.0; max_warp: float = 0.005
             patch_min_angle_warn: float = 40.0; patch_min_angle_error: float = 20.0
def validate_mesh(mesh: QMesh, gates: Gates, surface: Surface | None = None) -> tuple[Metrics, list[Issue]]
def validate_piece(piece: Piece, gates: Gates) -> list[Issue]                 # + naming, slots, sockets, ports, children
def ports_match(a: Port, b: Port) -> list[Issue]                            # §3.12
```

| gate | level | algorithm / notes |
|---|---|---|
| ngons == 0 | ERROR | face sizes |
| tris == 0, except collapse-row triangles (`pole:collapse` vertex, coplanar within 0.05° or extent ≤ 1 cm) and HIGH meshes | ERROR | §2.6 |
| non-manifold edges == 0; winding consistent; **signed volume > 0 per SOLID component** (E16) | ERROR | edge→face map; divergence-theorem volume |
| SOLID: open edges == 0 and V − E + F = 2 per component | ERROR | |
| **open edges only on tagged boundaries** (`bnd:outer`, `bnd:skirt`, `bnd:marking`, `port:*`). Any other open edge (a crack) → `OPEN_EDGE` (T27) | ERROR | builders tag boundary vertices |
| degenerate faces (area < 1e-8 m², edge < 0.5 mm) == 0 | ERROR | |
| T-junctions: a vertex within **1 mm in 3D** of an edge interior it is not an endpoint of (T27) | ERROR | spatial hash, 0.25 m cells |
| unwelded duplicates (0.01 mm) == 0 per component | ERROR | |
| min corner angle ≥ 10° (VISIBLE TOP faces). Junction patches: ≥ 40° orthogonal, ≥ 30° skewed (WARN); < 20° ERROR. Roundabout cores ≥ 40° (WARN) | ERROR / WARN | R1 |
| edge aspect ≤ 20 (exempt ARRIS, CAP, HIDDEN, COLLAPSE, MARKING) | WARN | |
| quad warp ≤ 5 mm | WARN | |
| **height field: `face_kind == TOP` faces have n_z ≥ 0.045** (E7, R3) | ERROR | |
| poles (interior valence ≠ 4) only on sharp edges, seams or tagged curb columns, **or carrying a documented vtag (`pole:ogrid`, `pole:collapse`)** (T14, E16) | ERROR | |
| custom normals: unit length; dot with the face normal > 0.2; **a fan with weak faces and coplanar strong faces: ≤ 0.5° from the strong normal; an all-strong fan: ≤ 0.5° from its area-weighted mean**; uniform within each fan (E16) | ERROR | the soft 5° crown fan passes (it is all-strong, compared to its mean) |
| UV: no NaN; **signed area > 0 on every face of every layer** (UV2 zero area allowed on asphalt faces with lane weight 0) | ERROR | E6, T14 |
| every UV0 island has an unwrap method | ERROR | T13 |
| `UV_RUN_DIR`: every VISIBLE sweep island's UV0 u axis is within 1° of its run | ERROR | T15 |
| **TRIM v inside its band** (all corners) | ERROR | E16 |
| WORLD_XY faces with n_z < 0.7 | WARN | E16 |
| UV stretch: TRIM bands > 5 %, SIDEWALK PATH > 30 % | WARN | T9 |
| UNIQUE/UDIM/MACRO: UV0 within [0,1] or its tile; overlaps == 0 | ERROR | v0–v2 UV triangles, spatial hash, clipped area > (0.25 px)² |
| UNIQUE/UDIM/MACRO: gutter ≥ 2·pad − 0.5 px; border ≥ pad − 0.5 px | ERROR | |
| UNIQUE/UDIM/MACRO: TD CV ≤ 0.05; median within ±10 % of the class density | ERROR | |
| hard edges off UV0 seams == 0 | ERROR | |
| TILING: max \|u\|, \|v\| after rebase ≤ 64 | WARN | |
| names regex; slots ≤ 8; slots in the registry; **every slot used by ≥ 1 face**; UV layers and colour attributes present | ERROR | E16, E22 |
| ports: section hash, positions (1 mm), normals (0.5°), UV phase | ERROR | T22 |
| `MARKING_CLEARANCE` ≥ 1 mm above the TriSurface (vertices, centroids, edge midpoints, overlay vertices) | ERROR | E11 |
| island toe ≥ 5 mm below the TriSurface along the whole outline | ERROR | E11 |
| `COLLAPSE_NOT_PLANAR`, `HARMONIC_NOT_CONVERGED`, `EDGE_RADIUS`, `LEG_CORE_CHORD`, `TRIM_OVERFLOW`, `KNOT_KINK`, `PORT_*` | ERROR | builder checks reported through the same Issue list |

`tests/rd01_bad_fixtures.py` (WP3) holds one deliberately broken fixture per check:
- an ngon;
- a T-junction, plus a crack offset 0.5 mm in z;
- an untagged open edge in a SKIRT mesh;
- a flipped UV on each layer;
- overlapping islands;
- a pole on a seam, and an untagged O-grid pole;
- mixed fan normals;
- an open SOLID and an inverted SOLID;
- a sharp edge off a seam;
- TRIM v out of band;
- an unused slot;
- a rotated sweep island;
- a marking below its clearance.

### 9.2 Pure-Python tests (`python3 -m unittest discover -s tests`)

| file | owner | covers |
|---|---|---|
| test_rd01_core_import.py | WP0 | **subprocess** `python3 -I` imports `rd01_road_studio.core.*` and asserts `'bpy' not in sys.modules`. Running in-process would fail, because `discover` imports `test_pk01_blender` (bpy at module level) first (E30). AST scan of core: no `random` / `time` / `uuid` imports, no builtin `hash()` calls. Source scan of the package: no absolute `rd01_road_studio` self-imports (E19, E32). |
| test_rd01_types.py | WP0 | specs are frozen and hashable; QMesh buffer checks; `ProfileTemplate.evaluate/slice` on fixture templates; fixtures valid |
| test_rd01_section.py | WP1 | every preset compiles; defaults within hard ranges; t monotone; 1:20 draft and n_z ≥ 0.045; hard/soft rules; ramp_top (EU 1.717, US 2.157); **every hard-range endpoint combination of the curb parameters** (E8); arris drop and no-arris rules; column merge; section_hash stability; drive side per region; kit section solver on the 0.5 m grid |
| test_rd01_transition.py | WP1 | superset compile; per-loop monotonicity; collapse anchors; 2Lto4L and UrbanToRural maps; cosine law; port hashes of both ends |
| test_rd01_rail.py | WP2 | analytic tangents (no 2.96° steps at R 6); knot > 0.5° → ERROR / FILLET; zero-length handles; clothoid end curvature and tangent length; **h(R 6, reach 7) = 0.4707 ± 1e-3 and the measured column sagitta ≤ 1.0 cm on the generated mesh for R ∈ {6, 8, 25, 50}** (T5, E5); superelevation test vectors and **reverse-curve continuity** (E9); vertical K warnings |
| test_rd01_sweep.py | WP2 | quads only; SKIRT open edges only on tagged boundaries; end curtains; SOLID closed, Euler 2, volume > 0; analytic normals identical on duplicated loops; FIELD diagonals follow the crown and superelevation field |
| test_rd01_street.py | WP2 | build_street from fixture templates; transition sweeps with collapse rows; precast unit with end chamfer; lathe with O-grid caps |
| test_rd01_validate.py | WP3 | each bad fixture triggers exactly its Issue code |
| test_rd01_uv.py | WP4 | world/path/trim math; **signed area > 0 on every layer for a SKIRT street, a SOLID street, a patch and a curb unit** (E6); reverse rule keeps v in band; rebase; reference-column u and stretch WARN; perimeter continuity and ≤ 1 % port phase scaling; UV2 lane orientation per drive side |
| test_rd01_pack.py | WP4 | determinism; padding; no rotation unless isotropic; UDIM; overflow → None |
| test_rd01_trimsheet.py | WP4 | layout algorithm (rows from the top, multiples of 8, power-of-two height, overflow → ERROR); `generate_layouts(snapshot) == data/trim_sheets.json`; `band_v`; well-formed guide SVG |
| test_rd01_masks.py | WP4 | byte ranges; ID palette == JSON; per-slot channel meanings; d_out includes island outlines; edge-blend columns; no noise term |
| test_rd01_manifest.py | WP5 | blender_to_ue vectors; socket tag / ue name; schema keys; r_min = half/0.1; landscape flags false for curbed sections |
| test_rd01_finalize.py | WP8 | marking merge, slot pruning, tri_count, pipeline order |
| test_rd01_trim_fit.py | WP8 | `generate_layouts(profiles.trim_band_needs())` == data file; **no band overflow for any preset in any region** (E15); every TRIM user profile fits its band |
| test_rd01_unique.py | WP8 | KitCurb at PED fits 4096; TD median ±1 %; CV ≤ 0.05; sharp ⊆ seams; UV_RUN_DIR; HEIGHTFIELD/POLAR/PLANAR assignment |
| test_rd01_ramps.py | WP9 | compliance per region; lip; combined grade (exact Fractions); DWS area; CURB_DROP on λ = 1; nominal v on flares; A × (1 − λ); US crosswalk auto-push to 1.25 m |
| test_rd01_markings.py | WP9 | dash phase; `fit_dash_cycles` ≤ 5 %; zebra; **MARKING_CLEARANCE ≥ 1 mm on a superelevated road, a crowned road and a junction**; bars clipped by islands; k/8 offsets; drive side |
| test_rd01_islands.py | WP9 | odd segments at rounded and cut ends; fold rule; sunk toe; one curb type |
| test_rd01_collision.py | WP9 | hulls convex, closed, quads |
| test_rd01_patch.py | WP11 | Coons; **plane patch test ≤ 1e-5 m**; SOR convergence < 300 sweeps on 60×60; MVC weights positive |
| test_rd01_junction.py | WP11 | X and T for R ∈ {0.6, 3, 6, 9, 15}, 2L×2L and 4L×2L; **skew ±15° (arms 1/3), mixed ±15°, one arm +15°, asymmetric radii 3/9 and 3/9/6/15** (T25), with the §3.6 gates; skew 16° → ERROR; **US default ramps (auto-push)** (T16); **UK LHT T and X** (T4); Junction_T_RQ11 (rural edge bands; EDGE_RADIUS ERROR at R 6 with embankment); Junction_T_2LMedian (refuges, nose gap ≥ 1 m); port contract with normals and UV phase |
| test_rd01_road.py | WP12 | chunks and names; ground catch points with a constant column count; port lead-in rules; dash phase between two ports; reverse curves; kinked and zero-handle curves; closed, multi-spline and tight-radius curves (ERROR where applicable, E33); chunk ↔ junction port match ≤ 1 mm including normals |
| test_rd01_rural.py | WP12 | RQ11 / RQ11_Flat / RQ31 / US rural; guardrail instance grouping per chunk; rail splice u phase |
| test_rd01_roundabout.py | WP13 | SINGLE 35 4-leg, COMPACT 28 3-leg, MINI 20 DOMED, **MINI 20 PAINTED UK (LHT, CW)**; ring station rule (Q4 = radial projection, total ≡ 0 mod 4, grading); entry width < 4.3 → ERROR; monotone leg morph and collapse row; splitter cut-through with rounded cut ends; children placements |
| test_rd01_kit.py | WP14 | every non-roundabout catalogue piece builds and validates; half-widths ∈ 0.5ℤ; B_c on grid; tri budgets; Painter-flagged pieces pass UNIQUE gates; curbless footprint == DIN; **identical catalogue hashes under PYTHONHASHSEED=0 and =12345 (two subprocesses)** (E32) |
| test_rd01_catalogue.py | WP15 | the full catalogue, roundabouts included: validate, Painter gates (T1), budgets, hash determinism |

### 9.3 Real-Blender tests (skipped without bpy)

Harness as in `tests/test_pk01_blender.py`: `read_factory_settings(use_empty=True)` in setUp, then re-fetch `bpy.context.scene`.
- **`tests/test_rd01_blender_io.py` (WP6):** qmesh_to_bpy round trip; attribute set; sharp-edge stability after `normals_split_custom_set` [V behaviour]; get-or-create attributes (no `uv_seam.001`, E21); bpy-side hash stable across an unedited rebuild (E26); exact-name material reuse and linked refusal (E23); the GN instancer evaluates N instances; ground BVH height function.
- **`tests/test_rd01_blender_export.py` (WP10):**
  - UE export of the **WP0 fixture street and fixture curb unit** (E2), with `verify_fbx` including socket transforms;
  - export while the generated collection is **excluded** from the view layer (E33), which passes because the temp export collection is included;
  - re-import (`wm.fbx_import` and `import_scene.fbx`): socket X axis (1,0,0), bounds × 0.01 match;
  - Substance export of a fixture set; LOD `FbxExpect`;
  - ExportFolder stage, commit, recover and abort with a simulated lock.
- **`tests/test_rd01_blender.py` (WP15):**
  - register/unregister twice;
  - spline road from a Bezier S-curve; junction, roundabout and kit builds;
  - regeneration: user objects and edited meshes survive; **an unedited rebuild creates no `_edited`**; **a Shift+D duplicate owner re-mints and both rebuild independently**; a scaled owner is refused; purge_orphans; a name clash raises ERROR before anything is deleted;
  - UE export of Junction_X and a spline chunk (E2: added here, not in WP10);
  - UV0 locks per set on the kit root; re-snap of linked curves after a junction rebuild.
- **`tests/test_rd01_extension.py` (WP15), subprocess (E31):**
  - `BLENDER_USER_RESOURCES=<tmp>` is set in the child environment *before* bpy initialises;
  - build with `<bpy>/4.5/scripts/addons_core/bl_pkg/cli/blender_ext.py build` [V path];
  - install with `bpy.ops.extensions.package_install_files` and enable `bl_ext.user_default.rd01_road_studio`;
  - preferences resolve through `ADDON_ID` (E17), and the presets fallback works for a legacy install (E18);
  - the manifest has `[permissions] files` and `paths_exclude_pattern`, and its tags are on the 4.5 list.
- Preview renders (`tools/rd01_preview.py`, subprocess, **Cycles CPU only**, env `RD01_PREVIEW=1`) [V: Workbench/EEVEE abort here, no libEGL].

### 9.4 Repository integration

- `tools/build_rd01.py`: deterministic zip of `rd01_road_studio/` (sorted, fixed timestamps), plus an extension build and manifest validation when `blender_ext.py` is available.
- The hash lock of §1.1 applies: no listed file is edited without `tools/refresh_hashes.py` in the same reviewed commit.

---

## 10. Implementation plan

### 10.1 Work packages, ownership and waves — E1, E2, E3, E35

**Rules:**
- Every file has exactly one owner WP, and other WPs only import it.
- WP0 commits **no stubs into other WPs' files**. Shared types live in WP0-owned files, so later WPs compile against real definitions.
- A WP's tests use only modules from earlier waves, plus WP0 fixtures.
- No WP edits a hash-locked repository file (§1.1).

| WP | wave | owned files | depends on | exposes (concrete interface) | done when |
|---|---|---|---|---|---|
| **WP0 Foundation** | 0 | `rd01_road_studio/__init__.py`, `blender_manifest.toml`, `LICENSE.txt`, `core/__init__.py`, `core/types.py`, `core/specs.py`, `core/surface.py`, `core/vec.py`, `core/enums.py`, `core/qmesh.py`, `core/template.py`, `core/piece.py`, `data/id_palette.json`, `tests/rd01_fixtures.py`, `tests/test_rd01_core_import.py`, `tests/test_rd01_types.py` | — | `Issue`; all specs (§10.2); `Surface` Protocol; enums; `QMesh`; `ProfileTemplate.evaluate/slice/reach/ref_col/band_cols`; `Piece/Port/Socket/SplineMeshInfo/Instance/Placement/BuiltObject`; fixtures `fixture_street_template()`, `fixture_curb_profile()`, `fixture_street_piece()` and `fixture_curb_unit_piece()` (both fully finalised by hand: UVs, colours, normals, sockets), `fixture_patch_grid()` | types and core-import tests pass |
| **WP1 Sections & profiles** | 1 | `core/standards.py`, `core/section.py`, `core/profiles.py`, `core/detail.py`, `data/presets/sections/*.json`, `tests/test_rd01_section.py`, `tests/test_rd01_transition.py` | WP0 | `param`, `region_preset`, `validate_params`, `compile_section(section, ramp, split_counts)`, `compile_transition(a, b, tmap) → TransitionTemplate`, `curb_section`, `din_curb_profile`, `barrier_section`, `wbeam_profile`, `island_curb_profile`, `trim_band_needs()`, `detail_params(Detail) → DetailParams`, `load_section_preset(name)` | all presets compile; ranges, transitions and hard-range combinations pass |
| **WP2 Rail, sweep, normals, street** | 1 | `core/rail.py`, `core/sweep.py`, `core/normals.py`, `core/trisurface.py`, `core/street.py`, `tests/test_rd01_rail.py`, `tests/test_rd01_sweep.py`, `tests/test_rd01_street.py` | WP0 (tests use fixture templates) | `Rail.from_bezier/from_polyline/line/arc/clothoid/compose/at/offset_point`, `fillet_polyline`, `sample_stations`, `chunk_ranges`, `superelevation`, `vertical_checks`, `sweep_section`, `sweep_closed`, `lathe`, `zmatch_profile`, `sweep_corner_normals`, `fan_corner_normals`, `orient_diagonals`, `TriSurface(mesh, faces)` (implements `Surface`, plus `overlay_points(polygon)`), `build_street(tpl, length, ...)`, `build_precast_unit(profile, length, radius, end_chamfer, ...)` | sagitta, superelevation, sweep and street tests pass |
| **WP3 Validator** | 1 | `core/validate.py`, `tests/rd01_bad_fixtures.py`, `tests/test_rd01_validate.py` | WP0 | `validate_mesh(mesh, gates, surface)`, `validate_piece`, `ports_match`, `Metrics`, `Gates` | each bad fixture → exactly its code |
| **WP4 UV, pack, trims, masks** | 1 | `core/uv.py`, `core/pack.py`, `core/trimsheet.py`, `core/masks.py`, `data/trim_sheets.json`, `tests/test_rd01_uv.py`, `tests/test_rd01_pack.py`, `tests/test_rd01_trimsheet.py`, `tests/test_rd01_masks.py` | WP0 | `apply_tiling_uvs`, `apply_lane_uvs`, `rebase`, `uv_stretch_report`, `extract_islands`, `unwrap_island`, `pack_texture_set → PackReport`, `maxrects_pack`, `generate_layouts(needs, density)`, `load_trim_sheets`, `band_v`, `guide_svg`, `compute_masks(mesh, ctx: MaskContext)`, `apply_id_colors(mesh)` | UV/pack/trim/mask tests pass on fixtures |
| **WP5 Manifest** | 1 | `core/manifest.py`, `tests/test_rd01_manifest.py` | WP0 | `SCHEMA`, `blender_to_ue`, `canonical_socket_name`, `piece_record`, `build_manifest`, `spline_meta`, `landscape_meta` | schema and transform vectors pass |
| **WP6 bpy core I/O** | 1 | `blender/mesh_io.py`, `blender/materials.py`, `blender/scene.py`, `blender/curve_input.py`, `blender/ground.py`, `blender/instancer.py`, `tests/test_rd01_blender_io.py` | WP0 | `qmesh_to_bpy`, `bpy_to_qmesh`, `mesh_content_hash`, `ensure_materials`, `read_curve → list[CurveSpline]`, `ground_height_fn(ob)`, `make_instancer(owner, instances)`, `owner_id`, `ensure_unique_owner`, `commit_generated`, `remove_generated`, `purge_orphans`, `kit_root`, `get_locks/set_lock`; each module exports `CLASSES = ()` | QMesh round trip, hash stability, materials and instancer tests pass |
| **WP7 UE scripts** | 1 | `unreal/RD01_Import.py`, `unreal/RD01_Materials.py`, `docs/RD01_UNREAL.md`, `tests/test_rd01_unreal_stub.py`, `tests/data/rd01_manifest_sample.json` | WP0 (schema in this spec) | `RD01_Import.main(manifest_path, dest, place, use_pcg) → report`, `RD01_Materials.build_masters(dest, overwrite) → dict` | AST parse plus the fake-`unreal` stub test exercising every branch; flagged [UE?] |
| **WP8 Finalize** | 2 | `core/finalize.py`, `tests/test_rd01_finalize.py`, `tests/test_rd01_unique.py`, `tests/test_rd01_trim_fit.py` | WP1, WP2, WP3, WP4 | `finalize_piece(piece, ctx: FinalizeContext) → Piece`: merge RAISED markings → prune slots → FIELD diagonals → normals → UV1/UV2 → masks/ID → tri_count → validate | KitCurb atlas passes UNIQUE gates; `generate_layouts(trim_band_needs())` == data file with no overflow |
| **WP9 Ramps, markings, islands, collision** | 2 | `core/ramps.py`, `core/markings.py`, `core/islands.py`, `core/collision.py`, `tests/test_rd01_ramps.py`, `tests/test_rd01_markings.py`, `tests/test_rd01_islands.py`, `tests/test_rd01_collision.py` | WP1, WP2, WP3, WP4 | `ramp_stations`, `fit_crosswalk_setback`, `ramp_morph`, `ramp_compliance`, `PATTERNS`, `dashes`, `fit_dash_cycles`, `zebra_layout`, `line_strip`, `bar_strip`, `marking_clearance`, `build_splitter`, `build_median_island`, `island_outline`, `ucx_profile_prisms`, `ucx_boxes`, `ucx_outline_prism` | compliance, clearance and island tests pass |
| **WP10 bpy export** | 2 | `blender/export_fbx.py`, `blender/export_substance.py`, `blender/export_folder.py`, `data/painter/RD01_UE.spexp`, `tests/test_rd01_blender_export.py` | WP5, WP6 (+ WP0 fixtures) | `FBX_KW`, `export_piece_ue`, `export_texture_set`, `export_macro_piece`, `verify_fbx(path, FbxExpect)`, `ExportFolder` | fixture street + curb unit export verified (incl. socket transforms and the excluded-collection case); folder swap tests pass |
| **WP11 Junctions** | 3 | `core/patch.py`, `core/junction.py`, `data/presets/junctions/*.json`, `tests/test_rd01_patch.py`, `tests/test_rd01_junction.py` | WP1, WP2, WP3, WP4, WP8, WP9 | `coons`, `orient_patch`, `resample`, `laplace_smooth`, `mean_value_weights`, `harmonic`, `disc_ogrid`, `extrude_down`, `build_junction(spec) → Piece`, `t_core(through, arm, corners, ...) → CoreResult` (reused by WP13) | §9.2 junction matrix passes (skew, radii, US, UK, RQ11, median) |
| **WP12 Spline roads, rural, guardrail** | 3 | `core/road.py`, `core/rural.py`, `tests/test_rd01_road.py`, `tests/test_rd01_rural.py` | WP1, WP2, WP3, WP4, WP8, WP9 | `rails_from_splines(splines, settings)`, `build_spline_road(splines, section, settings: RoadBuild) → list[Piece]`, `side_slope_morph`, `check_port_leadin`, `rq11`, `rq11_flat`, `us_rural_2lane`, `rq31`, `rq36`, `rq28`, `us_interstate`, `build_guardrail` | road, ground, port and rural tests pass |
| **WP13 Roundabouts** | 4 | `core/roundabout.py`, `data/presets/roundabouts/*.json`, `tests/test_rd01_roundabout.py` | WP8, WP9, WP11 | `build_roundabout(spec) → Piece` (+ children), `ring_stations(spec, cores) → list[float]` | first: re-run the leg core with the widened leg and the core-defined stations at the gates (§3.8); then the 4 presets including UK LHT |
| **WP14 Kit catalogue** | 4 | `core/kit.py`, `data/kit_budgets.json`, `tests/test_rd01_kit.py` | WP1, WP2, WP8, WP9, WP11, WP12 | `catalogue(region, td_preset) → list[PieceDef]`, `build_piece(defn, detail) → Piece`, `solve_kit_section`, `PAINTER_SETS`, `build_texture_set(set_name, region) → (list[Piece], PackReport)` | all non-roundabout pieces validate; grid, budget, Painter and determinism tests pass |
| **WP15 bpy UI, operators, integration** | 5 | `blender/__init__.py`, `blender/props.py`, `blender/presets.py`, `blender/ops_build.py`, `blender/ops_texturing.py`, `blender/ops_export.py`, `blender/ops_validate.py`, `blender/ui.py`, `tests/test_rd01_blender.py`, `tests/test_rd01_catalogue.py`, `tests/test_rd01_extension.py` | all | `register()/unregister()` (aggregates every module's `CLASSES`), `ADDON_ID`, the operator ids of §8.2, `presets.user_dir()` | §9.3 Blender tests, the full catalogue and the extension install pass |
| **WP16 Tooling & docs** | continuous | `tools/build_rd01.py`, `tools/rd01_preview.py`, `rd01_road_studio/README.md`, `docs/RD01_TECHNICAL.md`, `docs/RD01_SUBSTANCE.md` | as available | `build_rd01.main() → zip path`, `rd01_preview.main(out_dir)` | deterministic zip; previews render (Cycles CPU); **no hash-locked file edited** (or `refresh_hashes.py` in the same reviewed commit) |

**Schedule:**
- W0: WP0.
- W1: WP1–WP7 in parallel.
- W2: WP8, WP9, WP10.
- W3: WP11, WP12.
- W4: WP13, WP14.
- W5: WP15.
- WP16 runs continuously.

Rev-1 → rev-2 renumbering:
- 0 → 0, 1 → 1, 2 → 2, 3 → 3, 4 → 4, 9 → 5, 10 → 6, 13 → 7, 11 → 10, 7 → 13, 12 → 15, 14 → 16;
- 5 is split into 11 (junctions) and 8 (finalize);
- 6 → 9;
- 8 is split into 12 (roads and rural) and 14 (kit).

### 10.2 Cross-package interfaces (WP0-owned definitions; E1, E4)

```python
# core/types.py
Vec2 = tuple[float, float]; Vec3 = tuple[float, float, float]; RGBA8 = tuple[int, int, int, int]
Edge = tuple[int, int]; Matrix4 = tuple[tuple[float, float, float, float], ...]
Level = Literal['ERROR', 'WARN', 'INFO']
@dataclass(frozen=True)
class Issue: level: Level; code: str; message: str; where: str = ''; value: float | None = None

# core/surface.py
class Surface(Protocol):
    def z_at(self, x: float, y: float) -> float | None          # None = outside the surface
    def normal_at(self, x: float, y: float) -> Vec3 | None
    def point(self, s: float, t: float) -> Vec3                 # sweep-parametrised surfaces; patches raise NotImplementedError

# core/specs.py — every shared frozen spec / option / result type (field lists are normative)
ProfilePt(dt: float, dz: float, hard: bool, part: Part, strength: int, role: Role = Role.VISIBLE)
ClosedProfile(pts: tuple[Vec2, ...], hard: tuple[bool, ...], seg_part: tuple[Part, ...], seg_role: tuple[Role, ...],
              seg_strength: tuple[int, ...], seg_island: tuple[int, ...], split: tuple[int, int], name: str = '')
LineSpec(kind: str, offset: float, width: float, pattern: str)
Band(kind: BandKind, width: float = 0.0, p: Mapping[str, float | str] = {}, lines: tuple[LineSpec, ...] = (), band_id: str = '')
CrossSection(name, region, right: tuple[Band, ...], left: tuple[Band, ...], median: tuple[Band, ...] = (),
             crown: CrownMode = CENTRE, closure: Closure = SKIRT, slab_depth=0.25, skirt_depth=0.50, max_lateral=1.75)
RampSpec(kind='PERPENDICULAR', width=1.22, slope_max=1/12, flare_slope=0.10, landing=1.22, dws_depth=0.61,
         dws_setback=0.0, lip=0.0, gutter_counter_slope=0.05, gutter_transition=0.61, region='EU')
CrosswalkSpec(length=3.0, bar=0.5, gap=0.5, edge_min=0.25, edge_max=0.75, setback=1.0, style='ZEBRA')
TransitionMap(cols: tuple[tuple[str, str], ...], switch_at=0.5, mirror=True)
SamplingSpec(max_spacing=2.0, min_spacing=0.05, chord_tol=0.01, warp_tol=0.005,
             forced: tuple[float, ...] = (), zones: tuple[tuple[float, float, float], ...] = ())
SuperSpec(e_max=0.06, design_speed_kmh=80.0, rel_grade_max=0.005, axis='CENTRE')
SweepSpec(closure=SKIRT, cap_start=True, cap_end=True, uv_origin: Mapping[str, float] = {}, uv_dir=+1,
          uv_scale: Mapping[str, float] = {}, world_uv=True, diagonal_policy='FIELD', ports: tuple[str, str] = ('', ''))
UVRule(kind: UVKind, tile_m=(4.0, 4.0), sheet='', band='', ref='', anchor='', reverse=False, nominal_v=False, plane='')
TrimBand(name, y0_px, y1_px, need_m, users: tuple[str, ...]);  TrimSheet(name, td_class, density_px_m, sheet_w_px,
         sheet_h_px, u_tile_m, inset_px, bands: tuple[TrimBand, ...])
ArmSpec(section, heading_deg, length=6.0, crosswalk=CrosswalkSpec(), ramps=None, stop_line=True,
        lane_lines='SOLID_APPROACH', port_section=None, median_nose_gap=1.0)
CornerSpec(curb_radius=6.0, sidewalk_mode='AUTO')
JunctionSpec(name, arms, corners, priority=0, port_grid=0.5, closure=SKIRT, detail=LOD0, curbless=False,
             uv_mode=TILING, drive_side=None)
SplitterSpec(length=15.0, width_nose=3.0, width_tail=1.0, nose_radius=0.5, tail_radius=0.3, nose_gap=1.0,
             offset=0.5, curb=BARRIER, cut_through=True)
LegSpec(heading_deg, section, entry_radius=20.0, exit_radius=25.0, entry_width=4.5, exit_width=5.0, length=None,
        splitter=SplitterSpec(), crosswalk=CrosswalkSpec(), ramps=None)
RoundaboutSpec(name, kind='SINGLE', icd=35.0, circ_width=5.5, apron_width=3.0, apron_slope=0.02, apron_reveal=0.05,
               island_curb=BARRIER, island_dome=0.3, mini_island='DOMED', circ_crossfall=0.02, edge=(), legs=(),
               closure=SKIRT, detail=LOD0, drive_side=None, uv_mode=MACRO)
GuardrailSpec(system='EU_EDSP', rail_height=0.75, post_spacing=2.0, blockout=0.15, offset=0.5, side='RIGHT', panel_length=4.0)
CurveSpline(index: int, kind: str, segs: tuple[tuple[Vec3, Vec3, Vec3, Vec3], ...], points: tuple[Vec3, ...],
            closed: bool, ground_offsets: tuple[tuple[int, float], ...] = ())
PortRef(end: str, port: 'Port')                                   # 'START' | 'END'
RoadBuild(name, region='EU', closure=SKIRT, chunk_max=64.0, sampling=SamplingSpec(), superelevation=None,
          marking_pattern='TR_URBAN', marking_mode='RAISED', guardrail=None, world_uv=True, min_radius=10.0,
          knot_policy='ERROR', clothoid_a_factor: float | None = None, ground_offsets=(), ports: tuple[PortRef, ...] = (),
          ground: Callable[[float, float], float | None] | None = field(default=None, compare=False, hash=False))
ExportProfile(kind='UE', nanite=True, marking_mode='RAISED', baked_lighting=False, lods=False,
              substance_layout='PER_SET', export_high=False, paint_markings=False)
FbxExpect(render, lod_models=(), ucx=(), sockets={}, uv_layers=UV_LAYERS, first_color='RD01_Mask', materials=(), normals_sample=())
PieceDef(name, family, builder, params, uv_mode, texture_set, td_class, collision, spline_deformable=False, painter=False)
DetailParams(arris_segments: int, chord_factor: float, spacing_factor: float, end_chamfer: float, domes: bool)
MaskContext(flow_lines: tuple[tuple[Vec2, ...], ...], outlines: tuple[tuple[Vec2, ...], ...], ramp_lambda: Mapping[int, float] = {})
FinalizeContext(region: str, drive_side: DriveSide, td: Mapping[TDClass, int], sheets: Mapping[str, TrimSheet],
                world_offset: Vec3 | None, marking_mode: str, gates: 'Gates | None' = None, masks: MaskContext | None = None)
PackReport(set_name, td_class, td_px_m, tex_px, pad_px, efficiency, uv0_hashes: Mapping[str, str], issues: tuple[Issue, ...])

# core/template.py (WP0): ZRule, Column, Segment, Crossfall, MorphState, ProfileTemplate — fields as in §2.3

# core/piece.py (WP0)
@dataclass(frozen=True)
class Port: name: str; position: Vec3; direction: Vec3; section_hash: str; columns: tuple[Vec3, ...]
            normals: tuple[tuple[Vec3, ...], ...]          # per column: one normal per fan (hard columns have two)
            uv_phase: Mapping[str, float]                   # band reference tag → u mod module
            crossfall: tuple[float, float]; grade: float
@dataclass(frozen=True)
class Socket: tag: str; position: Vec3; yaw_deg: float
@dataclass(frozen=True)
class SplineMeshInfo: forward_axis: str = 'X'; boundary_min_m: float = 0.0; boundary_max_m: float = 0.0
                      loops_max_spacing_m: float = 1.0; max_strain: float = 0.10; r_min_m: float = 0.0
@dataclass(frozen=True)
class Instance: asset: str; chunk: str; matrices: tuple[Matrix4, ...]
@dataclass(frozen=True)
class Placement: asset: str; group: str; matrix: Matrix4; parent: str | None = None
@dataclass
class Piece:
    name: str; family: str; mesh: QMesh
    markings: QMesh | None = None                            # RAISED: merged by finalize_piece; DECAL: exported separately
    collision: list[QMesh] = field(default_factory=list); collision_mode: str = 'COMPLEX'
    sockets: list[Socket] = field(default_factory=list); ports: list[Port] = field(default_factory=list)
    uv_mode: UVMode = UVMode.TILING; texture_set: str | None = None; td_class: TDClass | None = None; td_px_m: int | None = None
    spline: SplineMeshInfo | None = None; landscape_spline: dict | None = None; pcg: dict | None = None
    lods: list[QMesh] = field(default_factory=list); high: QMesh | None = None
    children: list[tuple['Piece', Matrix4]] = field(default_factory=list)   # islands with parent-relative transforms (E34)
    instances: list[Instance] = field(default_factory=list)
    issues: list[Issue] = field(default_factory=list)
    meta: dict = field(default_factory=dict)                 # tri_budget, tri_count, section_hash, ramp reports, …
@dataclass
class BuiltObject:                                           # core → bpy hand-off (E4)
    name: str; mesh: QMesh; role: str                        # 'PIECE' | 'CHILD' | 'COLLISION'
    matrix: Matrix4; parent: str | None = None
    sockets: list[Socket] = field(default_factory=list); piece_json: str = ''

# builders (pure, deterministic)
def build_street(tpl: ProfileTemplate | TransitionTemplate, length: float, *, closure=Closure.SKIRT, morph=None,
                 forced=(), ports=('Start', 'End'), name='') -> Piece                                       # street.py (WP2)
def build_precast_unit(profile: ClosedProfile, length: float, radius: float | None = None, external: bool = True,
                       end_chamfer: float = 0.004, name: str = '') -> Piece                                 # street.py (WP2)
def finalize_piece(piece: Piece, ctx: FinalizeContext) -> Piece                                             # finalize.py (WP8)
def build_junction(spec: JunctionSpec) -> Piece                                                             # junction.py (WP11)
def build_spline_road(splines: Sequence[CurveSpline], section: CrossSection, settings: RoadBuild) -> list[Piece]   # road.py (WP12)
def build_roundabout(spec: RoundaboutSpec) -> Piece                                                         # roundabout.py (WP13)
def build_piece(defn: PieceDef, detail: Detail = Detail.LOD0) -> Piece                                      # kit.py (WP14)
def pack_texture_set(pieces, set_name, td_class, tex_px=None, mode=UVMode.UNIQUE) -> PackReport              # uv.py (WP4)

# bpy layer
def qmesh_to_bpy(q: QMesh, materials: Mapping[str, Material], me: Mesh | None = None) -> Mesh                # WP6
def bpy_to_qmesh(ob: Object, evaluated: bool = True) -> QMesh                                               # WP6
def mesh_content_hash(me: Mesh) -> str                                                                      # WP6
def ensure_materials(slot_names: Iterable[str]) -> dict[str, Material]                                      # WP6
def read_curve(ob: Object) -> list[CurveSpline]; def ground_height_fn(ob: Object) -> Callable[[float, float], float | None]  # WP6
def commit_generated(context, owner: Object, built: Sequence[BuiltObject], collection_name: str) -> list[Object]   # WP6
def export_piece_ue(ob: Object, out_dir: Path, profile: ExportProfile) -> dict                             # WP10
def export_texture_set(objs, set_name: str, out_dir: Path, high: bool = False) -> Path                     # WP10
def verify_fbx(path: Path, expect: FbxExpect) -> list[Issue]                                               # WP10
```

`qmesh_to_bpy` contract (WP6, verified API path):
1. `foreach_set` on `co`, `vertex_index` and `loop_start` → `update(calc_edges=True)`, then assert `not me.validate()`.
2. `shade_smooth()`.
3. Materials in slot order and `material_index`.
4. UV layers in contract order (UV0, UV1, UV2 [+UV3]).
5. `sharp_edge` and `uv_seam` (get-or-create, never `.001`, E21).
6. Byte colours via `color_srgb`, with active = RD01_Mask.
7. `normals_split_custom_set` last, then assert the `sharp_edge` count is unchanged.
8. `me['rd01_hash'] = mesh_content_hash(me)` (E26).

### 10.3 Milestones

1. **M1 (W0–W2):** finalized street, curb units, ramps, markings and islands; fixture exports verified by FBX parsing.
2. **M2 (W3):** X/T junctions (skew ≤ 15°, rural, median), spline roads with ground, ports and guardrail instances.
3. **M3 (W4–W5):** roundabouts (including UK), the full catalogue with Painter gates, UI, extension install, and Blender integration tests.
4. **M4 (outside this environment):** UE smoke test on 5.4/5.5/5.7/5.8 (calibration box, sockets, mask strip, marking line trace, Nanite fallback, Interchange vs legacy, masters, macro MIs, ISM placement), and a Painter check of `RD01_UE.spexp` and the bake settings [SP?].

---

## 11. Risks, open items and things still unverified

- **[UE?]**: axis and unit result in-engine (guarded by the calibration box); mask decoding (calibration strip); Interchange property availability per version (logged by `_set`); socket naming under Interchange 5.5/5.6 (canonicalised by the importer); `enable_section_collision`, Nanite fallback property names, `generate_distance_field_as_if_two_sided`, `MaterialInstance.phys_material`; and the master-material graph (LWC world UV, world-normal transform, hex tiling) — the smoke test rotates a kit piece by 90° to check the lighting.
- **[SP?]**: the `.spexp` preset schema; the Painter mesh-reload behaviour with the stable `current/` path.
- **[I] values to recheck in their WP:** the AASHTO K table (WP12), the roundabout entry/exit width defaults (WP13), UK give-way pattern dimensions (WP9), and the W-beam girth (WP1 computes it from `wbeam_profile`).
- **Prototype coverage:** junction cores were measured for skew, radii and widths in `rev2/skew2.py`, and roundabout leg cores with the widened leg in `rev2/ra2.py`, but **only the 2D cores**. WP11 and WP13 must re-measure on the full builders (edge bands, transitions, collapse rows).
- **Documented exceptions to all-quad:** collapse-row triangles (coplanar, §2.6) and HIGH bake meshes. Every other mesh is 100 % quads.
- **Performance:** pure-Python SOR takes ~1.4 s per 60×60 patch [V], and a junction has 5 patches. Validator overlay checks are O(n log n) with spatial hashes. The catalogue build time is measured in WP14 and budgeted at < 5 min.
- Junction and roundabout z fields are visual blends, not drainage designs.
- **v1 limits:**
  - skew ≤ 15°;
  - symmetric arm sections; equal opposite carriageway column counts; one edge band-kind sequence per junction;
  - radial roundabout legs; no DOUBLE roundabouts;
  - PERPENDICULAR ramps only;
  - superelevation about the centre only;
  - no closed spline roads;
  - level junction ports;
  - one curb type per island;
  - no ground following on junction edge bands;
  - UK concrete step barrier withheld.
- Trim joint convention (unit joints at u = 0 and 0.5; the concrete joint module 1.0 m) must be honoured by Designer authors. It is documented in README_SUBSTANCE.md, the trim JSON and the guide SVG/PNG.

## Appendix A — verification log

| check | result |
|---|---|
| Triangulate `quad_method='FIXED'` diagonal | quad (0,1,2,3) → tris (0,1,2),(0,2,3): **v0–v2** |
| keep_custom_normals through FBX | max deviation 5.3e-5 |
| FBX identity axes + bake_space + FBX_SCALE_NONE | GlobalSettings Up 2/+1, Front 1/−1, Coord 0/+1, UnitScaleFactor 1.0; verts in cm; mesh Model has no Lcl |
| smoothing EDGE; tangents; colour bytes; UV order | ByEdge; tangents/binormals per UV layer; RD01_Mask first, bytes exact; UV order as created |
| auto-sharp | custom normals that differ across a smooth edge make Blender mark it sharp |
| LodGroup | the exporter writes the NodeAttribute type from Empty `fbx_type` |
| headless render | Workbench/EEVEE abort (no libEGL); Cycles CPU OK |
| rev 1 junction / roundabout prototypes | orthogonal X/T 46.7–52.5°; leg core 43.2–46.5° (rev-1 widths) |
| **rev 2: station spacing** (`nums.py`) | θ(13 m) = 4.495°, h = 0.471 m, outer sagitta 1.00 cm (literal rev-1 formula: 1.02 m / 4.7 cm); R 8/25/50 → 0.584 / 1.250 / 1.873 m |
| **rev 2: drafts, barrier girths, curb maxima** | 1:20 n_z 0.0499, 1:19 0.0526; NJ 0.872, F 0.855, SS 1.086, VERT 0.901; curb barrier max girth 0.433, mountable 0.412 |
| **rev 2: ramps** | EU run 1.717; US run 2.157; US flare0 = σ + 0.415, g0 = σ − 0.195 → setback 1.25; EU g0 = σ + 0.08 |
| **rev 2: kit widths** | half-widths EU/DE 7.0, TR 7.5, UK 7.0, US 8.0 (2L); EU 4L 10.5 |
| **rev 2: skewed/asymmetric junction cores** (`skew.py`, `skew2.py`) | see §3.6 table; skew 30° → 18.1° min → excluded |
| **rev 2: roundabout leg core, widened leg** (`ra2.py`) | ICD 28/35/45/20: 49.5° / 46.6° / 42.6° / 53.0°; central segment 4.60° vs chord limit 4.68° at R_a (ICD 35) |
| **rev 2: SOR + mean-value weights** (`sor.py`, `sor2.py`) | 125–253 sweeps to residual 1e-8 on 40×40 to 60×60 graded grids, 0.26–1.44 s; plane patch error ≤ 4.8e-6 m; residual stop 1e-5 leaves 4.6 mm error at 60×60 |
| **rev 2: trim layouts** (`trim.py`) | §4.7 table; all bands fit; barrier sheets at PED would be 2048 × 4096 |
| **rev 2: excluded-collection export** (`bchk4.py`) | excluded → socket Lcl missing (identity); included + update → Lcl Translation [400,0,0], Rotation [0,0,−180]; parented sockets OK |
| **rev 2: GN instancer** (`bchk.py`) | QUATERNION point attribute → Instance on Points: 3 instances with yaw 0 / 90° / 180° evaluated headless |
| **rev 2: ID custom properties** (`idprop.py`) | an Object reference stored as an ID property survives and reads None after the owner is deleted |
| **rev 2: presets fallback** | `bpy.utils.user_resource('SCRIPTS', path='presets/rd01_road_studio')` resolves; `blender_ext.py` at `<bpy>/4.5/scripts/addons_core/bl_pkg/cli/` |
| **rev 2: parse_fbx import** | importing `io_scene_fbx.parse_fbx` without importing bpy first hung > 90 s here; verify_fbx imports bpy first |

## Appendix B — v1.1 backlog

- PARALLEL / BLENDED / COMBINED ramps.
- Curb-type morphs along closed sweeps (T26 design: a common z-matched curb column superset, 1 m morph).
- DOUBLE roundabouts with spiral ring markings, entry lane lines and offset legs.
- Junction skew beyond 15° (needs a curved-core decomposition).
- Mixed urban/rural junction edges.
- Tilted (graded) junction ports.
- Ground following for junction edge bands.
- Hatched flush medians and chevrons; arrows / symbol atlas.
- Pavement-layer cutaway (surface 0.04 / binder 0.08 / base 0.22 / sub-base 0.30–0.40; sidewalk 0.08 + 0.04 + 0.20; kerb haunch 0.15–0.20 [S]).
- Driveway mountable transitions; inner/outer superelevation axes; instanced tactile domes.
- PK01 bridge (PK01 consuming `rd01_road_studio.core` sections); UE PCG graph asset generation beyond the manifest graph.
