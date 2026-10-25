"""Supply/housing integration regressions, including the real header/pot near miss."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from hardware.cad.a11 import integration as cad
from hardware.cad.a11.verify import verify_sources
from hardware.electronics.common.sexpr import children, first, read_sexpr, sexpr


class A11SupplyIntegration(unittest.TestCase):
    def obstacles(self):
        data = cad.assignments(cad.ROOT / "reference-components.scad")
        return (
            [b for b in data["boards"] if b[0] != "power_carrier"]
            + [e for e in data["envelopes"] if e[0] != "power_components"]
            + data["port_envelopes"]
        )

    def test_real_board_replaces_the_generic_reserve_and_retains_all_parts(self):
        actual = cad.packet()
        self.assertEqual(actual["board"][4:7], [90, 44, 1.6])
        self.assertEqual(len(actual["components"]), 157)
        self.assertGreaterEqual(
            cad.electronics_clearance(actual, self.obstacles())["minimum_axis_gap_mm"], 0.25
        )
        generated = cad.assignments(cad.ROOT / "generated/components.scad")
        self.assertNotIn("power_components", {e[0] for e in generated["envelopes"]})
        self.assertEqual(next(b for b in generated["boards"] if b[0] == "power_carrier"), actual["board"])

    def test_old_datum_is_rejected_for_header_to_resonance_pot_clearance(self):
        actual = cad.packet(datum=(207, 105, 6.5))
        # The old position has no volume collision but only 0.09 mm Z clearance.
        self.assertFalse(any(cad.overlap(a, b) for a in actual["reserves"] for b in self.obstacles()))
        with self.assertRaisesRegex(AssertionError, "Insufficient supply-to-electronics clearance"):
            cad.electronics_clearance(actual, self.obstacles())

    def changed_board(self, change):
        tree = read_sexpr(cad.PCB.read_text())
        change(tree)
        tmp = tempfile.NamedTemporaryFile(suffix=".kicad_pcb", delete=False)
        path = Path(tmp.name)
        tmp.close()
        path.write_text(sexpr(tree))
        self.addCleanup(path.unlink)
        return path

    def test_missing_component_cannot_make_the_clearance_check_pass(self):
        def remove(tree):
            tree[:] = [
                n
                for n in tree
                if not (
                    isinstance(n, list)
                    and n
                    and n[0] == "footprint"
                    and any(p[1:3] == ["Reference", "C31"] for p in children(n, "property"))
                )
            ]

        with self.assertRaises(AssertionError):
            cad.packet(self.changed_board(remove))

    def test_changed_outline_needs_a_new_interface_review(self):
        def grow(tree):
            for line in children(tree, "gr_line"):
                if first(line, "layer")[1] == "Edge.Cuts":
                    for end in ("start", "end"):
                        if float(first(line, end)[1]) == 190:
                            first(line, end)[1] = 192

        with self.assertRaisesRegex(AssertionError, "Supply outline changed"):
            cad.packet(self.changed_board(grow))

    def test_taller_bottom_capacitors_fail_the_floor_check(self):
        with patch.dict(cad.HEIGHT_LIMITS, {"Capacitor_SMD:C_1210_3225Metric": 3.8}):
            with self.assertRaisesRegex(AssertionError, "reaches the chassis floor"):
                cad.write_packet()

    def test_stale_supply_copper_invalidates_saved_mechanical_evidence(self):
        record = {
            "source_sha256": {str(p.relative_to(cad.ROOT)): cad.digest(p) for p in cad.ROOT.rglob("*.scad")},
            "power_integration": {"sources_sha256": {str(cad.PCB.relative_to(cad.REPO)): "0" * 64}},
        }
        with self.assertRaisesRegex(AssertionError, "Stale supply integration"):
            verify_sources(record)

    def test_changed_mount_drill_is_rejected(self):
        def shrink(tree):
            fp = next(
                fp
                for fp in children(tree, "footprint")
                if any(p[1:3] == ["Reference", "H1"] for p in children(fp, "property"))
            )
            first(children(fp, "pad")[0], "drill")[1] = 2.0

        with self.assertRaises(AssertionError):
            cad.packet(self.changed_board(shrink))


class DisconnectIntegration(unittest.TestCase):
    def test_all_disconnect_parts_and_vent_reserves_are_present(self):
        from hardware.cad.a11.disconnect import packet

        d = packet()
        self.assertEqual(len(d["components"]), 164)
        self.assertEqual(len(d["mounts"]), 4)
        self.assertEqual(len(d["cylinders"]), 6)
        self.assertEqual(len(d["vent_air"]), 6)
        self.assertGreaterEqual(d["minimum_allocated_floor_gap_mm"], 0.25)
        self.assertFalse(d["pcb_routed"])
        self.assertFalse(d["physical_protection_verified"])

    def test_changed_disconnect_copper_invalidates_saved_fit(self):
        from hardware.cad.a11.disconnect import E25

        record = {
            "source_sha256": {str(p.relative_to(cad.ROOT)): cad.digest(p) for p in cad.ROOT.rglob("*.scad")},
            "power_integration": {
                "sources_sha256": {str((E25 / "rail_disconnect.kicad_pcb").relative_to(cad.REPO)): "0" * 64}
            },
        }
        with self.assertRaisesRegex(AssertionError, "Stale supply integration"):
            verify_sources(record)


if __name__ == "__main__":
    unittest.main()
