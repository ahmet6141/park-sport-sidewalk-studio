"""PK01 1.1 FLOW sidewalks, curve toolkit and swept/lathed props (pure Python, no bpy)."""
import collections
import hashlib
import itertools
import json
import math
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from pk01_park_studio import curves, flow, modeling, props
from pk01_park_studio.geometry import Mesh, MAT
from pk01_park_studio.planner import ParkConfig, build_park
from pk01_park_studio.vendor import sw01_core as sw

CFG = sw.Config(width=3.2, height=.18, pattern='SLABS', pattern_angle=0., paver_length=.8, paver_width=.4, curve_step=.4)


def closed_solid_defects(mesh):
    """Every recorded solid must be watertight (after welding split hard-edge columns),
    consistently wound and enclose a positive volume."""
    owner = {}
    for index, (start, count, _label) in enumerate(mesh.solids):
        for v in range(start, start+count): owner[v] = index
    faces = collections.defaultdict(list); defects = []
    for tri in mesh.triangles:
        ids = {owner.get(i) for i in tri}
        if len(ids) != 1 or None in ids: defects.append(('unowned', tri)); continue
        faces[ids.pop()].append(tri)
    key = lambda i: tuple(round(c, 7) for c in mesh.vertices[i])
    for index, tris in faces.items():
        edges = collections.Counter()
        volume = 0.
        for a, b, c in tris:
            for e in ((a, b), (b, c), (c, a)): edges[(key(e[0]), key(e[1]))] += 1
            A, B, C = (mesh.vertices[i] for i in (a, b, c))
            volume += (A[0]*(B[1]*C[2]-B[2]*C[1])-A[1]*(B[0]*C[2]-B[2]*C[0])+A[2]*(B[0]*C[1]-B[1]*C[0]))/6
        open_edges = sum(1 for (a, b), n in edges.items() if edges.get((b, a), 0) != n)
        if open_edges or volume <= 0: defects.append((mesh.solids[index][2], open_edges, volume))
    return defects


def buffers_valid(test, mesh):
    test.assertEqual(len(mesh.uv), len(mesh.triangles))
    test.assertEqual(len(mesh.material_ids), len(mesh.triangles))
    test.assertEqual(len(mesh.smooth), len(mesh.triangles))
    test.assertEqual(len(mesh.colors), len(mesh.vertices))
    test.assertTrue(all(math.isfinite(c) for p in mesh.vertices for c in p))
    test.assertTrue(all(0 <= i < len(mesh.vertices) for t in mesh.triangles for i in t))


class CurveTests(unittest.TestCase):
    def test_meander_is_flush_and_tangent_at_both_ends(self):
        pts = curves.meander((0., 0.), (40., 0.), 1.5, 2)
        self.assertEqual(pts[0], (0., 0.)); self.assertAlmostEqual(pts[-1][0], 40.); self.assertAlmostEqual(pts[-1][1], 0.)
        for a, b in ((pts[0], pts[1]), (pts[-2], pts[-1])):
            self.assertLess(abs(math.atan2(b[1]-a[1], b[0]-a[0])), math.radians(1.))
        self.assertGreater(max(abs(y) for x, y in pts), .5)

    def test_safe_amplitude_keeps_radius(self):
        amp = curves.safe_meander_amplitude(30., 3.2, 1, 4.)
        pts = curves.resample_adaptive(curves.meander((0, 0), (30, 0), amp, 1))
        self.assertGreaterEqual(curves.min_radius(pts), 3*3.2*.9)

    def test_fillet_replaces_corner_with_radius(self):
        pts = curves.fillet_polyline([(0, 0), (10, 0), (10, 10)], 3., .1)
        self.assertAlmostEqual(curves.min_radius(pts), 3., delta=.05)
        self.assertEqual(pts[0], (0., 0.)); self.assertEqual(pts[-1], (10., 10.))

    def test_adaptive_resampling_densifies_bends(self):
        arc = [(10*math.sin(a), 10*(1-math.cos(a))) for a in (i*math.pi/2/200 for i in range(201))]
        line = curves.resample_adaptive([(0, 0)]+[(x, 0) for x in range(1, 40)])
        bend = curves.resample_adaptive(arc)
        self.assertLess(len(line), 40/.4+3)
        self.assertLess(max(math.dist(a, b) for a, b in zip(bend, bend[1:])), .45+1e-9)
        self.assertEqual(bend[-1], arc[-1])

    def test_catmull_rom_interpolates_controls(self):
        ctrl = [(0, 0), (5, 3), (10, 0), (15, -2)]
        out = curves.catmull_rom(ctrl)
        for p in ctrl: self.assertLess(min(math.dist(p, q) for q in out), 1e-9)


class ModelingTests(unittest.TestCase):
    def test_curb_profiles_are_ccw_on_both_sides(self):
        for style in modeling.CURB_STYLES:
            for outer, inner in ((-1.6, -1.42), (1.6, 1.42)):
                pts, flags = modeling.curb_profile(outer, inner, -.07, .18, style)
                self.assertEqual(len(pts), len(flags))
                self.assertGreater(sw.area(pts), 0)
                self.assertAlmostEqual(min(abs(p[0]-outer) for p in pts), 0.)

    def test_swept_and_lathed_props_are_closed(self):
        for build in (props.bench, props.bench_curved, props.light_pole, props.bollard, props.bin_prop):
            mesh = build()
            with self.subTest(mesh=mesh.name):
                buffers_valid(self, mesh)
                self.assertEqual(closed_solid_defects(mesh), [])
                self.assertTrue(any(mesh.smooth), 'rounded parts must shade smooth')


class FlowModuleTests(unittest.TestCase):
    def test_curved_module_closed_and_compatible(self):
        path = flow.make_path(curves.resample_adaptive(curves.meander((0, 0), (36, 0), 1.4, 2)), (1, 0), (1, 0))
        for style in modeling.CURB_STYLES:
            with self.subTest(style=style):
                mesh, meta = flow.build_flow_module('SM_Test_Flow', path, CFG, style)
                buffers_valid(self, mesh)
                self.assertEqual(closed_solid_defects(mesh), [])
                self.assertEqual(set(mesh.material_ids) - set(range(len(sw.MATERIALS))), set())
                for key in ('config', 'path', 'in', 'out', 'collision'): self.assertIn(key, meta)
                self.assertAlmostEqual(meta['in']['yaw_degrees'], 0., places=6)
                self.assertAlmostEqual(meta['out']['yaw_degrees'], 0., places=6)
                self.assertGreater(meta['pavers'], 200)
                json.dumps(meta)

    def test_every_pattern_and_tactile(self):
        path = sw.Path(curves.resample_adaptive(curves.fillet_polyline([(0, 0), (8, 0), (14, 6)], 5.)))
        from dataclasses import replace
        for pattern in ('SLABS', 'RUNNING', 'STACK', 'HERRINGBONE', 'BASKET'):
            cfg = replace(CFG, pattern=pattern, pattern_angle=45. if pattern == 'HERRINGBONE' else 0., tactile=pattern == 'RUNNING')
            with self.subTest(pattern=pattern):
                mesh, meta = flow.build_flow_module('SM_Test_'+pattern, path, cfg)
                self.assertEqual(closed_solid_defects(mesh), [])
                self.assertGreater(meta['pavers'], 20)

    def test_symmetric_edge_cuts(self):
        courses = flow._lateral_courses(-1.3, 1.3, .4)
        widths = [b-a for a, b in courses]
        self.assertAlmostEqual(sum(widths), 2.6)
        self.assertAlmostEqual(widths[0], widths[-1])
        self.assertGreaterEqual(min(widths), .2-1e-9)

    def test_junction_every_arm_combination(self):
        for n in range(5):
            for arms in itertools.combinations('ENWS', n):
                arms = ''.join(arms)
                with self.subTest(arms=arms or 'none'):
                    mesh, meta = flow.build_junction('SM_Test_J_'+arms, arms, CFG, 4.4, 2.5)
                    buffers_valid(self, mesh)
                    self.assertEqual(closed_solid_defects(mesh), [])
                    for hull in meta['collision']: self.assertGreater(sw.area(hull['polygon']), 0)
                    # Open mouths coincide with the arm path cross-section.
                    for d in arms:
                        dx, dy = flow.DIRECTIONS[d]
                        for side in (-1, 1):
                            corner = (dx*4.4-dy*side*1.6, dy*4.4+dx*side*1.6)
                            self.assertLess(min(math.dist(corner, p) for p in meta['outline']), 1e-6)


class PlannerTests(unittest.TestCase):
    def test_classic_paths_are_unchanged_from_1_0_0(self):
        plan = build_park(ParkConfig(preset='GARDEN', detail='DRAFT', tree_count=0, path_style='CLASSIC'))
        digest = hashlib.sha256()
        keys = sorted(k for k in plan.assets if k.startswith('SM_PK01_SW01_'))
        for k in keys: digest.update(plan.assets[k].geometry_hash().encode())
        self.assertEqual(len(keys), 15)
        self.assertEqual(digest.hexdigest(), 'b1ceb7bdb95832852d1f1c8deee7f22e78d382c59d2142f6bdabbfe17b4d7db3')

    def test_flow_presets_join_every_spur_to_a_mouth(self):
        for preset in ('GARDEN', 'COMMUNITY'):
            with self.subTest(preset=preset):
                plan = build_park(ParkConfig(preset=preset, detail='DRAFT', tree_count=0))
                json.dumps(plan.settings)
                self.assertNotIn('_junctions', plan.settings)
                junctions = [p for p in plan.placements if 'FlowJunction' in p.asset]
                self.assertGreater(len(junctions), 3)
                mouths = []
                for p in junctions:
                    meta = plan.assets[p.asset].meta['sw01']; zone = plan.zones[p.zone]
                    for d in meta['arms']:
                        dx, dy = flow.DIRECTIONS[d]
                        mouths.append((zone.location[0]+dx*meta['reach_m'], zone.location[1]+dy*meta['reach_m']))
                ends = [e for path in plan.paths if not path['junction'] for e in (path['points'][0], path['points'][-1])]
                for m in mouths:
                    self.assertLess(min(math.dist(m, e) for e in ends), .05)
                # Path end cuts that meet a mouth are exactly orthogonal (no hairline wedge).
                for p in plan.placements:
                    meta = plan.assets[p.asset].meta.get('sw01', {})
                    if meta.get('builder') != 'PK01_FLOW': continue
                    zone = plan.zones[p.zone]
                    for tag in ('in', 'out'):
                        loc = meta[tag]['location']; world = (zone.location[0]+loc[0], zone.location[1]+loc[1])
                        if min(math.dist(world, m) for m in mouths) < .05:
                            self.assertAlmostEqual(math.remainder(meta[tag]['yaw_degrees'], 90.), 0., places=6)
                self.assertTrue(any('BenchCurved' in p.asset for p in plan.placements))

    def test_ui_exposes_every_config_field(self):
        import ast
        from dataclasses import fields
        tree = ast.parse((ROOT/'pk01_park_studio/ui.py').read_text(encoding='utf-8'))
        settings = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'PK01_Settings')
        names = {n.target.id for n in settings.body if isinstance(n, ast.AnnAssign)}
        self.assertEqual({f.name for f in fields(ParkConfig)}-names, set())

    def test_flow_options_validated(self):
        for bad in (dict(path_style='ZIGZAG'), dict(curb_profile='ROUND'), dict(junction_radius=9.), dict(meander=-1.)):
            with self.subTest(**bad):
                with self.assertRaises(ValueError): ParkConfig(**bad).validate()


if __name__ == '__main__':
    unittest.main()
