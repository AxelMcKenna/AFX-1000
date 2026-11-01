"""Reject stale CAD evidence, altered receiving geometry and hidden checks."""

import copy
import json
import tempfile
import unittest
from pathlib import Path

from hardware.electronics.common.sexpr import first, read_sexpr
from hardware.electronics.rail_disconnect.revision28.native_profile import summarize
from hardware.fabrication.audit_candidate import geometry_delta, native_evidence_errors, sha
from hardware.fabrication.audit_normalized import canonical


class NativeEvidence(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.project = self.root / "board.kicad_pro"
        self.project.write_text("{}")
        self.project.with_suffix(".kicad_pcb").write_text("(kicad_pcb)")
        self.project.with_suffix(".kicad_sch").write_text("(kicad_sch)")
        self.drc = dict(violations=[], unconnected_items=[], schematic_parity=[], ignored_checks=[])
        self.erc = dict(sheets=[], ignored_checks=[])
        for name, data in (("drc.json", self.drc), ("erc.json", self.erc)):
            (self.root/name).write_text(json.dumps(data))
        (self.root/"fp-lib-table").write_text("(fp_lib_table)")
        (self.root/"libraries").mkdir()
        (self.root/"libraries/part.kicad_mod").write_text("(footprint PART)")
        self.record = dict(checked_PCB_sha256=sha(self.project.with_suffix(".kicad_pcb")),
                           checked_project_sha256=sha(self.project),
                           checked_schematic_sha256=sha(self.project.with_suffix(".kicad_sch")),
                           raw_report_sha256={name: sha(self.root/name) for name in ("drc.json", "erc.json")},
                           captured_project_library_sha256={"libraries/part.kicad_mod": sha(self.root/"libraries/part.kicad_mod")},
                           captured_library_table_sha256={"fp-lib-table": sha(self.root/"fp-lib-table")},
                           status=summarize(self.drc, self.erc), uncapped_open_connections=0)

    def test_original_complete_evidence_matches(self):
        self.assertEqual(native_evidence_errors(self.project, self.record), [])

    def test_each_checked_cad_dependency_mutation_is_rejected(self):
        for name in ("board.kicad_pcb", "board.kicad_pro", "board.kicad_sch", "fp-lib-table", "libraries/part.kicad_mod", "drc.json", "erc.json"):
            with self.subTest(name=name):
                path = self.root/name
                original = path.read_text()
                path.write_text(original+" ")
                self.assertTrue(native_evidence_errors(self.project, self.record))
                path.write_text(original)

    def test_matching_zero_counts_do_not_excuse_disabled_native_check(self):
        self.drc["ignored_checks"] = ["track_not_centered_on_via"]
        path = self.root/"drc.json"
        path.write_text(json.dumps(self.drc))
        record = copy.deepcopy(self.record)
        record["raw_report_sha256"]["drc.json"] = sha(path)
        record["status"] = summarize(self.drc, self.erc)
        self.assertIn("Native check coverage is incomplete", native_evidence_errors(self.project, record))

    def test_claimed_uncapped_count_must_match_native_markers(self):
        record = dict(self.record, uncapped_open_connections=5)
        self.assertTrue(native_evidence_errors(self.project, record))


class SavedGeometry(unittest.TestCase):
    def board(self):
        return read_sexpr('(kicad_pcb (version 20260101) (footprint "PART" (at 1 2) (uuid "fp")) (segment (start 1 2) (end 3 4) (uuid "track")) (via (at 2 3) (uuid "via")) (zone (uuid "zone") (polygon (pts (xy 0 0) (xy 10 0) (xy 10 10))) (filled_polygon (pts (xy 1 1) (xy 9 1) (xy 9 9)))))')

    def test_component_move_is_detected(self):
        old = self.board()
        new = copy.deepcopy(old)
        first(first(new, "footprint"), "at")[1] = 2
        self.assertEqual(geometry_delta(old, new)["footprint"]["changed"], ["fp"])

    def test_refill_is_distinguished_from_authored_plane_change(self):
        old = self.board()
        new = copy.deepcopy(old)
        first(first(new, "zone"), "filled_polygon")[1][1][1] = 1.1
        self.assertEqual(geometry_delta(old, new)["zone"]["changed"], [])
        first(first(new, "zone"), "polygon")[1][1][1] = 1.1
        self.assertEqual(geometry_delta(old, new)["zone"]["changed"], ["zone"])

    def test_removed_via_and_board_setting_change_are_detected(self):
        old = self.board()
        new = [node for node in copy.deepcopy(old) if not (isinstance(node, list) and node and node[0] == "via")]
        first(new, "version")[1] = 20260102
        result = geometry_delta(old, new)
        self.assertEqual(result["via"]["removed"], ["via"])
        self.assertFalse(result["other_root_geometry_exact"])

    def test_format_comparison_ignores_uuid_but_retains_physical_mutations(self):
        old = self.board()
        new = copy.deepcopy(old)
        first(first(new, "footprint"), "uuid")[1] = "generated-identity"
        self.assertEqual(canonical(old), canonical(new))
        first(first(new, "footprint"), "at")[1] = 2
        self.assertNotEqual(canonical(old), canonical(new))

    def test_format_comparison_preserves_polygon_point_order(self):
        old = self.board()
        new = copy.deepcopy(old)
        points = first(first(first(new, "zone"), "polygon"), "pts")
        points[1], points[2] = points[2], points[1]
        self.assertNotEqual(canonical(old), canonical(new))


if __name__ == "__main__":
    unittest.main()
