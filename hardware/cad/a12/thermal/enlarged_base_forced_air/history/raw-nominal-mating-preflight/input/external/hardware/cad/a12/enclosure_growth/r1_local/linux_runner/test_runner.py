import json
import math
import tempfile
import unittest
from pathlib import Path

from hardware.cad.a12.thermal.enlarged_base.verify import mesh

from .openscad import IMAGE, REPO, command
from .prove import OUT, ROOT, sha


class PinnedRunner(unittest.TestCase):
    def test_actual_proof_and_raw_artifacts(self):
        q = json.loads((OUT / "verification.json").read_text())
        self.assertEqual(q["image"], IMAGE)
        self.assertTrue(q["actual_runtime_controls_passed"])
        self.assertFalse(q["physical_qualified"])
        self.assertEqual(set(q["cases"]), {"solid", "witness", "empty"})
        for n, h in {**q["source_sha256"], **q["artifact_sha256"]}.items():
            self.assertEqual(sha(ROOT / n), h, n)
        for n, expected in [("solid", 1.5), ("witness", 0.008)]:
            row = q["cases"][n]
            self.assertEqual(row["returncode"], 0)
            self.assertIn("NoError", row["stdout"] + row["stderr"])
            m = mesh(OUT / (n + ".stl"))
            self.assertEqual(m, row["statistics"])
            self.assertTrue(m["closed_oriented_boundary"])
            self.assertFalse(m["degenerate_triangles_excluded"])
            self.assertTrue(math.isclose(m["volume_mm3"], expected, abs_tol=1e-7))
        row = q["cases"]["empty"]
        self.assertEqual(row["returncode"], 1)
        self.assertIn("Current top level object is empty.", row["stdout"] + row["stderr"])
        self.assertFalse((OUT / "empty.stl").exists())

    def test_mount_policy_and_rejected_output_mutations(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as td:
            d = Path(td)
            source = d / "actual.scad"
            source.write_text("cube(1);")
            out = d / "fresh.stl"
            cmd = command(["-o", str(out), str(source)])
            self.assertIn("none", cmd)
            self.assertIn("--read-only", cmd)
            self.assertIn("ALL", cmd)
            self.assertIn("no-new-privileges=true", cmd)
            self.assertIn(f"type=bind,source={REPO},target={REPO},readonly", cmd)
            self.assertIn(f"type=bind,source={d},target={d}", cmd)
            self.assertIn(f"type=bind,source={source},target={source},readonly", cmd)
            out.write_text("do not overwrite actual evidence")
            with self.assertRaises(ValueError):
                command(["-o", str(out), str(source)])
            with self.assertRaises(ValueError):
                command(["-o", "/private/tmp/unapproved.stl", str(source)])


if __name__ == "__main__":
    unittest.main()
