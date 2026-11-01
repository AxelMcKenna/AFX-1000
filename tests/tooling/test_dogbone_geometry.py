"""Own-net annular overlap must never permit a drilled hole under an SMD land."""

import unittest

from hardware.fabrication.dogbone_screen import DogboneScreen
from tests.tooling.test_fabrication_geometry import capture, rectangle


class DogboneDrillBoundary(unittest.TestCase):
    def screen(self,net="SIGNAL",layer="F.Cu"):
        data = capture()
        data["objects"].append(dict(net=net,kind="PAD",layers={layer:rectangle(9,9,11,11)}))
        return DogboneScreen(data)

    def test_own_annular_overlap_keeps_drill_and_margin_outside_land(self):
        screen = self.screen()
        self.assertFalse(screen.via_legal("SIGNAL",(10,10)))
        self.assertFalse(screen.via_legal("SIGNAL",(11.25,10)))
        self.assertTrue(screen.via_legal("SIGNAL",(11.26,10)))

    def test_other_net_pad_keeps_full_copper_clearance_on_any_layer(self):
        for layer in ("F.Cu","In1.Cu","B.Cu"):
            with self.subTest(layer=layer):
                screen = self.screen(net="OTHER",layer=layer)
                self.assertFalse(screen.via_legal("SIGNAL",(11.26,10)))
                self.assertFalse(screen.via_legal("SIGNAL",(11.53,10)))
                self.assertTrue(screen.via_legal("SIGNAL",(11.54,10)))


if __name__ == "__main__":
    unittest.main()
