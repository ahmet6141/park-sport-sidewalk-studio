"""Repository smoke tests, not Blender/Unreal runtime or full historical tests."""
import ast
import hashlib
import json
import math
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from pk01_park_studio import contracts
from pk01_park_studio.geometry import Mesh, MAT
from tools.build_addon import verify_supplied_hashes, source_files, version


class RepositoryTests(unittest.TestCase):
    def test_source_syntax(self):
        for path in ROOT.rglob("*.py"):
            with self.subTest(path=str(path.relative_to(ROOT))):
                ast.parse(path.read_text(encoding="utf-8"), filename=str(path))

    def test_original_file_hashes(self):
        self.assertGreater(verify_supplied_hashes(), 50)

    def test_every_source_file_below_git_limit(self):
        for path in source_files():
            with self.subTest(path=str(path)):
                self.assertLess(path.stat().st_size, 100 * 1024 * 1024)

    def test_version(self):
        self.assertEqual(version(), "1_0_0")

    def test_texture_png_headers(self):
        for path in (ROOT / "pk01_park_studio/assets/textures").rglob("*.png"):
            with self.subTest(path=path.name):
                with path.open("rb") as stream:
                    self.assertEqual(stream.read(8), b"\x89PNG\r\n\x1a\n")

    def test_identity_transform_to_centimetres(self):
        matrix = [[1,0,0,1],[0,1,0,2],[0,0,1,3],[0,0,0,1]]
        location, quat, scale = contracts.convert_matrix(matrix, [[1,0,0],[0,1,0],[0,0,1]])
        self.assertEqual(location, [100, 200, 300])
        self.assertEqual(scale, [1,1,1])
        self.assertEqual(quat, (0,0,0,1))

    def test_invalid_transform_rejected(self):
        matrix = [[0,0,0,0],[0,1,0,0],[0,0,1,0],[0,0,0,1]]
        with self.assertRaises(ValueError):
            contracts.convert_matrix(matrix, [[1,0,0],[0,1,0],[0,0,1]])

    def test_closed_box_buffers(self):
        mesh = Mesh("smoke_box")
        mesh.box((0,0,.5), (2,3,1), MAT["Curb"], bevel=.01)
        self.assertGreater(len(mesh.triangles), 0)
        self.assertEqual(len(mesh.material_ids), len(mesh.triangles))
        self.assertEqual(len(mesh.uv), len(mesh.triangles))
        self.assertTrue(all(math.isfinite(c) for p in mesh.vertices for c in p))
        self.assertTrue(all(0 <= i < len(mesh.vertices) for t in mesh.triangles for i in t))

    def test_publication_manifest(self):
        manifest = json.loads((ROOT / "PUBLISH_MANIFEST.json").read_text(encoding="utf-8"))
        for relative, data in manifest["files"].items():
            with self.subTest(path=relative):
                path = ROOT / relative
                self.assertEqual(path.stat().st_size, data["size"])
                self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), data["sha256"])


if __name__ == "__main__":
    unittest.main()
