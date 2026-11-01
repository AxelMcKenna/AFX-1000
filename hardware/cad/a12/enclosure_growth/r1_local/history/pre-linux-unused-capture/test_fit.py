import copy
import json
import tempfile
import unittest
from pathlib import Path

from hardware.electronics.common.sexpr import children, read_sexpr, sexpr

from .stage import BASE, OUT, R1, REPO, ROOT, sha
from .verify import ALL, row_errors


class LocalR1Fit(unittest.TestCase):
    def test_actual_source_context_and_all_native_roles(self):
        c = json.loads((ROOT / "capture.json").read_text())
        q = json.loads((OUT / "verification.json").read_text())
        self.assertEqual(len(q["cases"]), len(ALL))
        self.assertTrue(q["complete_required_case_set"])
        self.assertTrue(q["all_native_local_checks_clear"])
        self.assertFalse(q["changed_inputs"])
        self.assertFalse(q["executable_changed"])
        self.assertFalse(q["physical_qualified"])
        self.assertFalse(q["thermal_qualified"])
        self.assertFalse(q["new_whole_unit_source_or_assembly_qualified"])
        self.assertEqual(len(c["old_R1_only_exclusions"]), 1)
        self.assertEqual(c["old_R1_only_exclusions"][0]["old_row"][0], "e19_R1")
        self.assertTrue(c["all_other_native_boards_retained"])
        self.assertEqual(q["correlated_own_PCB_seat_cases"], [-0.2, 0, 0.2])
        self.assertEqual(c["actual_R1_receiving_row"][0], "new_selected_R1")
        for n, h in c["derived_context_sha256"].items():
            self.assertEqual(sha(ROOT / n), h)
        for mapping in [c["original_source_sha256"], q["source_sha256"], q["artifact_sha256"]]:
            for n, h in mapping.items():
                self.assertEqual(sha(REPO / n), h, n)
        for n, r in q["cases"].items():
            self.assertFalse(row_errors(n, r), n)
        a, b = [read_sexpr((p / "processor_carrier.kicad_pcb").read_text()) for p in [BASE, R1]]

        def fs(t):
            return {
                next(p[2] for p in children(f, "property") if p[1] == "Reference"): sexpr(f)
                for f in children(t, "footprint")
            }

        old, new = fs(a), fs(b)
        self.assertEqual(len(old), 88)
        self.assertTrue(all(new[n] == s for n, s in old.items() if n != "R1"))

    def test_actual_artifact_negative_mutations(self):
        q = json.loads((OUT / "verification.json").read_text())
        actual = q["cases"]["new_R1_positive_control"]
        with tempfile.TemporaryDirectory() as td:
            out = Path(td)
            name = "new_R1_positive_control"
            (out / (name + ".stl")).write_bytes((OUT / (name + ".stl")).read_bytes())
            (out / (name + ".log")).write_bytes((OUT / (name + ".log")).read_bytes())
            self.assertFalse(row_errors(name, actual, out))
            (out / (name + ".log")).write_text("WARNING: missing actual solid\n")
            self.assertTrue(row_errors(name, actual, out))
            (out / (name + ".log")).write_bytes((OUT / (name + ".log")).read_bytes())
            bad = copy.deepcopy(actual)
            bad["statistics"]["volume_mm3"] = 0
            self.assertTrue(row_errors(name, bad, out))
            (out / "power_collision.stl").write_bytes((OUT / (name + ".stl")).read_bytes())
            (out / "power_collision.log").write_text("Current top level object is empty.\n")
            self.assertTrue(row_errors("power_collision", dict(returncode=1, statistics=None), out))
            self.assertTrue(row_errors("undeclared", actual, out))


if __name__ == "__main__":
    unittest.main()
