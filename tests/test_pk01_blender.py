"""PK01 inside real Blender (the `bpy` module, e.g. `pip install bpy==4.5.*` on Python 3.11).
Skipped when bpy is not importable. Covers add-on (re)registration, park builds in both path
styles and the FBX + manifest export. Unreal import is still not exercised.
"""
import json
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
class PK01BlenderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        bpy.ops.wm.read_factory_settings(use_empty=True)
        import pk01_park_studio
        cls.addon = pk01_park_studio
        cls.addon.register()

    @classmethod
    def tearDownClass(cls):
        cls.addon.unregister()
        from pk01_park_studio import ui
        # Every class must be gone, or re-enabling the add-on fails and Blender hangs on exit.
        assert not [c.__name__ for c in ui.CLASSES if c.is_registered]

    def test_reregister(self):
        self.addon.unregister()
        self.assertFalse(hasattr(bpy.types.Scene, 'pk01'))
        self.addon.register()
        self.assertTrue(hasattr(bpy.context.scene, 'pk01'))

    def build(self, style):
        s = bpy.context.scene.pk01
        s.preset = 'GARDEN'; s.detail = 'DRAFT'; s.tree_count = 6; s.path_style = style; s.scene_name = 'Test_'+style
        self.assertEqual(bpy.ops.pk01.build(), {'FINISHED'}, s.status)
        roots = [o for o in bpy.data.objects if o.get('pk01_root') and o.name.endswith('Test_'+style)]
        self.assertEqual(len(roots), 1)
        return roots[0]

    def test_build_and_export_both_styles(self):
        for style in ('FLOW', 'CLASSIC'):
            with self.subTest(style=style):
                root = self.build(style)
                meshes = [o for o in root.children_recursive if o.type == 'MESH']
                self.assertGreater(len(meshes), 20)
                paths = [o for o in meshes if o.get('pk01_category') == 'Paths']
                self.assertTrue(paths)
                if style == 'FLOW':
                    self.assertTrue(any('FlowJunction' in o.get('pk01_asset_key', '') for o in paths))
                    self.assertTrue(any(any(p.use_smooth for p in o.data.polygons) for o in paths))
                for o in meshes[:40]:
                    self.assertIn('UV0_Tile', o.data.uv_layers)
                    self.assertIn('SW01_Tint', o.data.color_attributes)
                with tempfile.TemporaryDirectory() as out:
                    s = bpy.context.scene.pk01
                    s.active_root = root; s.export_directory = out; s.include_selected_sw01 = False
                    bpy.context.view_layer.objects.active = root
                    self.assertEqual(bpy.ops.pk01.export_unreal(), {'FINISHED'}, s.status)
                    folder = next(Path(out).iterdir())
                    manifest = json.loads((folder/'PK01_scene.json').read_text(encoding='utf-8'))
                    fbx = list((folder/'Meshes').glob('*.fbx'))
                    self.assertEqual(len(fbx), len(manifest['asset_map']))
                    self.assertTrue(all(f.stat().st_size > 100 for f in fbx))
                    self.assertTrue((folder/'PK01_Import.py').is_file())


if __name__ == '__main__':
    unittest.main()
