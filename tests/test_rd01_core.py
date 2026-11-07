"""RD01 pure-Python kernel: sections, rails, sweep topology, UVs, masks, validator (no bpy)."""
import math
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from rd01_road_studio.core import standards, section, sweep, rail, validate, uv
from rd01_road_studio.core.qmesh import QMesh, Part, Kind, UV_LAYERS, COLOR_ID, COLOR_MASK

CURVE = [((0, 0, 0), (40, 0, 0), (70, 20, 0), (90, 60, 1.0))]


def build(preset='URBAN_2L', region='EU', r=None, **kw):
    tpl = section.compile_section(standards.preset(preset, region))
    return tpl, sweep.build_road(r or rail.Rail.from_bezier(CURVE), tpl, sweep.RoadOptions(name='SM_RD01_Road_T', **kw))


class SectionTests(unittest.TestCase):
    def test_every_preset_compiles_in_every_region(self):
        for name in standards.PRESETS:
            for reg in standards.REGIONS:
                with self.subTest(preset=name, region=reg):
                    tpl = section.compile_section(standards.preset(name, reg))
                    ts = [c.t for c in tpl.columns]
                    self.assertTrue(all(b - a >= section.ARRIS_MIN_DT - 1e-9 for a, b in zip(ts, ts[1:])))
                    self.assertEqual(len(tpl.segments), len(tpl.columns) - 1)
                    self.assertAlmostEqual(tpl.columns[0].t, -tpl.columns[-1].t, places=9)   # symmetric presets

    def test_curb_geometry_matches_region_parameters(self):
        for reg in ('EU', 'TR', 'US'):
            tpl = section.compile_section(standards.preset('URBAN_2L', reg))
            toe = tpl.tag_index('L.toe'); back = tpl.tag_index('L.curb_back')
            self.assertTrue(tpl.columns[toe].hard)
            reveal = standards.REGIONS[reg]['reveal']
            top = max(c.z for c in tpl.columns[toe:back + 1])
            self.assertAlmostEqual(top - tpl.columns[toe].z, reveal, delta=0.006)
            self.assertFalse(any(c.hard for c in tpl.columns[toe + 1:back + 1]))   # arris is soft geometry

    def test_crossfall_drains_to_gutter_and_sidewalk_towards_road(self):
        tpl = section.compile_section(standards.preset('URBAN_2L', 'EU'))
        crown, lip, flow = tpl.tag_index('crown'), tpl.tag_index('L.lip'), tpl.tag_index('L.flow')
        self.assertGreater(tpl.columns[crown].z, tpl.columns[lip].z)
        self.assertGreater(tpl.columns[lip].z, tpl.columns[flow].z)
        self.assertGreater(tpl.columns[tpl.tag_index('L.back')].z, tpl.columns[tpl.tag_index('L.curb_back')].z)

    def test_unknown_inputs_refused(self):
        with self.assertRaises(ValueError):
            standards.preset('NOPE')
        with self.assertRaises(ValueError):
            standards.region('XX')


class RailTests(unittest.TestCase):
    def test_arc_curvature_and_stations(self):
        r = rail.Rail.arc(40.0, 90.0)
        self.assertAlmostEqual(r.length, 40 * math.pi / 2, delta=0.01)
        self.assertAlmostEqual(r.curvature(r.length / 2), 1 / 40, delta=1e-3)
        st = rail.sample_stations(r, 7.0, 1.0, 0.01)
        h = rail.station_spacing(40.0, 7.0, 0.01, 1.0)
        self.assertLessEqual(max(b - a for a, b in zip(st, st[1:])), h + 1e-9)
        self.assertEqual(st[0], 0.0); self.assertAlmostEqual(st[-1], r.length)

    def test_uniform_stations_are_equal(self):
        st = rail.sample_stations(rail.Rail.line(8.0), 7.0, 1.0, uniform=True)
        steps = {round(b - a, 9) for a, b in zip(st, st[1:])}
        self.assertEqual(len(steps), 1)

    def test_tight_curve_refused(self):
        tpl = section.compile_section(standards.preset('URBAN_2L'))
        with self.assertRaises(ValueError):
            sweep.build_road(rail.Rail.arc(5.0, 90), tpl)


class SweepTests(unittest.TestCase):
    def test_all_presets_validate_clean(self):
        for name in standards.PRESETS:
            for r in (rail.Rail.from_bezier(CURVE), rail.Rail.line(40), rail.Rail.arc(60, -90)):
                with self.subTest(preset=name, rail=r.length):
                    _, pieces = build(name, r=r)
                    for p in pieces:
                        self.assertEqual(validate.validate_mesh(p.mesh), [])

    def test_quads_only_and_buffers_complete(self):
        _, pieces = build()
        m = pieces[0].mesh
        self.assertEqual({len(f) for f in m.faces}, {4})
        for layer in UV_LAYERS:
            self.assertEqual(len(m.uv[layer]), len(m.faces))
        self.assertEqual(len(m.colors[COLOR_ID]), len(m.faces))
        self.assertEqual(len(m.colors[COLOR_MASK]), len(m.faces))
        self.assertTrue(m.sharp and m.sharp <= m.seams)

    def test_chunks_share_boundary_loops(self):
        r = rail.Rail.from_bezier(CURVE)
        tpl, pieces = build(r=r, markings=False)
        self.assertGreater(len(pieces), 1)
        for a, b in zip(pieces, pieces[1:]):
            end = {tuple(round(c + o, 6) for c, o in zip(a.mesh.verts[v], a.origin))
                   for v, tag in a.mesh.vtags.items() if 'port:End' in tag}
            start = {tuple(round(c + o, 6) for c, o in zip(b.mesh.verts[v], b.origin))
                     for v, tag in b.mesh.vtags.items() if 'port:Start' in tag}
            self.assertEqual(end, start)
            self.assertEqual(len(end), len(tpl.columns))

    def test_free_ends_have_curtains_and_ports_stay_open(self):
        _, closed = build(r=rail.Rail.line(8), chunk_length=0)
        _, open_ = build(r=rail.Rail.line(8), chunk_length=0, port_start=True, port_end=True)
        caps = lambda m: sum(1 for k in m.face_kind if k == Kind.CAP)
        self.assertGreater(caps(closed[0].mesh), 0)
        self.assertEqual(caps(open_[0].mesh), 0)
        self.assertEqual(validate.validate_mesh(open_[0].mesh), [])

    def test_sockets_point_out_of_the_piece(self):
        _, pieces = build(r=rail.Rail.line(12), chunk_length=0)
        start, end = pieces[0].sockets
        self.assertAlmostEqual(start.yaw_deg, 180.0)
        self.assertAlmostEqual(end.yaw_deg, 0.0)
        self.assertAlmostEqual(end.position[0], 12.0)

    def test_markings_float_above_surface(self):
        tpl, pieces = build(r=rail.Rail.line(18), chunk_length=0)
        m = pieces[0].mesh
        mk = [f for f, p in enumerate(m.face_part) if p == Part.MARKING and m.face_kind[f] == Kind.MARKING
              and m.face_normal(f)[2] > 0.9]
        self.assertTrue(mk)
        for f in mk:
            for v in m.faces[f]:
                x, y, z = m.verts[v]
                self.assertAlmostEqual(z - tpl.z_at(y), sweep.MARK_LIFT, delta=2e-4)

    def test_dash_fit_divides_length(self):
        dashes = sweep._dash_intervals('DASH_3_6', 36.0, True)
        self.assertEqual(len(dashes), 4)
        self.assertAlmostEqual(dashes[1][0] - dashes[0][0], 9.0)

    def test_uv2_lane_runs_from_driver_right_edge(self):
        for reg, drive in (('EU', 'RHT'), ('UK', 'LHT')):
            tpl, pieces = build(region=reg, r=rail.Rail.line(16), chunk_length=0, markings=False)
            m = pieces[0].mesh
            for f, part in enumerate(m.face_part):
                if part == Part.LANE:
                    vs = [v for _, v in m.uv['UV2_Lane'][f]]
                    self.assertTrue(all(-1e-9 <= v <= 1 + 1e-9 for v in vs))

    def test_wetness_mask_peaks_at_gutter(self):
        tpl, pieces = build(r=rail.Rail.line(8), chunk_length=0, markings=False)
        m = pieces[0].mesh
        wet = {}
        for f, part in enumerate(m.face_part):
            for v, col in zip(m.faces[f], m.colors[COLOR_MASK][f]):
                wet[round(m.verts[v][1], 3)] = max(wet.get(round(m.verts[v][1], 3), 0), col[0])
        flow = round(tpl.columns[tpl.tag_index('L.flow')].t, 3)
        self.assertGreater(wet[flow], 200)
        self.assertEqual(wet[0.0], 0)

    def test_deterministic(self):
        a = build()[1][0].mesh; b = build()[1][0].mesh
        self.assertEqual(a.geometry_hash(), b.geometry_hash())
        self.assertEqual(a.uv_hash('UV1_Tile'), b.uv_hash('UV1_Tile'))


class ValidatorTests(unittest.TestCase):
    def quad(self):
        m = QMesh('SM_RD01_Bad')
        ids = [m.add_vert(p) for p in ((0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 1, 0))]
        uvs = ((0, 0), (1, 0), (1, 1), (0, 1))
        m.add_face(ids, 'RD01_Asphalt', Part.LANE, uvs={k: uvs for k in UV_LAYERS})
        m.colors[COLOR_ID] = [((0, 0, 0, 255),) * 4]; m.colors[COLOR_MASK] = [((0, 0, 0, 0),) * 4]
        return m, ids

    def codes(self, m, mode='TILING'):
        return {i.code for i in validate.validate_mesh(m, mode)}

    def test_clean_quad(self):
        self.assertEqual(self.codes(self.quad()[0]), set())

    def test_detects_each_defect(self):
        m, ids = self.quad(); m.mark_edge(ids[0], ids[1], sharp=True, seam=False)
        self.assertEqual(self.codes(m), {'SHARP_NOT_SEAM'})
        m, ids = self.quad(); m.uv['UV1_Tile'][0] = tuple(reversed(m.uv['UV1_Tile'][0]))
        self.assertEqual(self.codes(m), {'UV_FLIP'})
        m, ids = self.quad(); m.faces[0] = tuple(reversed(m.faces[0]))
        self.assertIn('HEIGHTFIELD', self.codes(m))
        m, ids = self.quad(); m.uv['UV0_Main'][0] = ((0, 0), (2, 0), (2, 1), (0, 1))
        self.assertEqual(self.codes(m, 'UNIQUE'), {'UV_RANGE'})
        m, ids = self.quad(); m.verts[2] = (1, 1, 0.9)
        self.assertEqual(self.codes(m), set())
        m, ids = self.quad(); mid = m.add_vert((0.5, 0.0, 0.0))
        extra = [m.add_vert(p) for p in ((0, -1, 0), (1, -1, 0))]
        m.add_face((extra[0], extra[1], ids[1], mid), 'RD01_Asphalt', Part.LANE,
                   uvs={k: ((0, 0), (1, 0), (1, 1), (0.5, 1)) for k in UV_LAYERS})
        m.colors[COLOR_ID].append(((0, 0, 0, 255),) * 4); m.colors[COLOR_MASK].append(((0, 0, 0, 0),) * 4)
        self.assertIn('TJUNCTION', self.codes(m))


if __name__ == '__main__':
    unittest.main()
