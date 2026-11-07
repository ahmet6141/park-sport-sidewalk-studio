"""RD01 inside real Blender (bpy module; skipped when not installed). Builds a road from a Bézier
curve and the modular kit through the operators, exports FBX and re-imports it to check what UE
and Painter will read: triangle count, UV channel order, colour layers and socket transforms."""
import json
import math
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
try:
    import bpy
    bpy.app.version  # finish bpy's delayed initialisation before mathutils is imported
except ImportError:
    bpy = None


@unittest.skipIf(bpy is None, 'Blender Python module (bpy) is not installed')
class RD01BlenderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        bpy.ops.wm.read_factory_settings(use_empty=True)
        import rd01_road_studio
        cls.addon = rd01_road_studio
        cls.addon.register()

    @classmethod
    def tearDownClass(cls):
        cls.addon.unregister()
        from rd01_road_studio.blender import ui
        assert not [c.__name__ for c in ui.CLASSES if c.is_registered]

    def curve(self, name='Main Street'):
        data = bpy.data.curves.new(name, 'CURVE'); data.dimensions = '3D'
        sp = data.splines.new('BEZIER'); sp.bezier_points.add(1)
        a, b = sp.bezier_points
        a.co, a.handle_left, a.handle_right = (0, 0, 0), (-10, 0, 0), (25, 0, 0)
        b.co, b.handle_left, b.handle_right = (40, 30, 0.5), (40, 10, 0.5), (40, 50, 0.5)
        ob = bpy.data.objects.new(name, data); bpy.context.scene.collection.objects.link(ob)
        ob.location = (5, 7, 0); ob.rotation_euler.z = math.radians(30)
        bpy.context.view_layer.objects.active = ob
        return ob

    def generated(self, owner):
        return [o for o in bpy.data.objects if o.type == 'MESH' and o.get('rd01_owner') == owner.get('rd01_uid')]

    def test_road_build_rebuild_validate_export(self):
        s = bpy.context.scene.rd01
        s.section_preset = 'URBAN_2L'; s.region = 'TR'
        curve = self.curve()
        self.assertEqual(bpy.ops.rd01.build_road(), {'FINISHED'}, s.status)
        objs = self.generated(curve)
        self.assertGreater(len(objs), 1)
        self.assertTrue(all(len(p.vertices) == 4 for o in objs for p in o.data.polygons))
        # Rebuilding replaces the previous output instead of stacking it.
        bpy.context.view_layer.objects.active = curve
        self.assertEqual(bpy.ops.rd01.build_road(), {'FINISHED'}, s.status)
        self.assertEqual(len(self.generated(curve)), len(objs))
        objs = self.generated(curve)
        for o in bpy.context.view_layer.objects:
            o.select_set(o in objs)
        self.assertEqual(bpy.ops.rd01.validate(), {'FINISHED'})
        self.assertIn('0 errors', s.status)
        with tempfile.TemporaryDirectory() as out:
            s.export_dir = out; s.export_profile = 'UE'
            self.assertEqual(bpy.ops.rd01.export(), {'FINISHED'}, s.status)
            manifest = json.loads((Path(out) / 'RD01_manifest.json').read_text())
            self.assertEqual(len(manifest['assets']), len(objs))
            rec = manifest['assets'][0]
            self.check_fbx(Path(out) / rec['file'], rec)

    def check_fbx(self, path, rec):
        before = set(bpy.data.objects)
        bpy.ops.import_scene.fbx(filepath=str(path))
        new = [o for o in bpy.data.objects if o not in before]
        try:
            mesh = next(o for o in new if o.type == 'MESH')
            self.assertEqual(len(mesh.data.polygons), rec['tris'])           # FIXED quad split, no n-gons
            self.assertEqual([u.name for u in mesh.data.uv_layers], rec['uv_layers'])
            self.assertEqual([a.name for a in mesh.data.color_attributes], ['RD01_Mask', 'RD01_ID'])
            sockets = {o.name.split('.')[0]: o for o in new if o.name.startswith('SOCKET_')}
            self.assertEqual(set(sockets), {'SOCKET_' + s['tag'] for s in rec['sockets']})
            for srec in rec['sockets']:
                loc = sockets['SOCKET_' + srec['tag']].matrix_world.translation - mesh.matrix_world.translation
                # Re-imported in metres with Blender axes: compare against the manifest's UE centimetres.
                self.assertAlmostEqual(loc.x * 100, srec['location_cm'][0], delta=0.5)
                self.assertAlmostEqual(-loc.y * 100, srec['location_cm'][1], delta=0.5)
        finally:
            for o in new:
                bpy.data.objects.remove(o, do_unlink=True)

    def test_kit_build_and_painter_export(self):
        s = bpy.context.scene.rd01
        s.section_preset = 'URBAN_2L'; s.region = 'EU'
        self.assertEqual(bpy.ops.rd01.build_kit(), {'FINISHED'}, s.status)
        root = bpy.data.objects['RD01_Kit_URBAN_2L_EU']
        pieces = self.generated(root)
        self.assertGreaterEqual(len(pieces), 10)
        for o in bpy.context.view_layer.objects:
            o.select_set(o in pieces[:3])
        with tempfile.TemporaryDirectory() as out:
            s.export_dir = out; s.export_profile = 'PAINTER'
            self.assertEqual(bpy.ops.rd01.export(), {'FINISHED'}, s.status)
            self.assertEqual(len(list((Path(out) / 'Meshes').glob('*.fbx'))), 3)


if __name__ == '__main__':
    unittest.main()
