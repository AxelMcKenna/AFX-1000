"""Fault injection for the partial main-board placement and codec data hold."""

import copy
import json
import unittest

from hardware.electronics.common.netlists import netlist
from hardware.electronics.common.sexpr import a, children, first, read_sexpr
from hardware.fabrication import audit_audio_main_placement as audit


class AudioMainPlacement(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.parts,cls.pins=netlist(audit.OUT/"native-netlist.xml")
        cls.saved=read_sexpr((audit.OUT/"audio_core.kicad_pcb").read_text())
        cls.saved_plan=json.loads((audit.OUT/"plan.json").read_text())

    def setUp(self):
        self.tree=copy.deepcopy(self.saved)
        self.plan=copy.deepcopy(self.saved_plan)

    def move(self,ref,x,y,angle=0):
        fp=audit.footprints(self.tree)[ref]
        first(fp,"at")[1:]=[x,y,angle]
        side=str(first(fp,"layer")[1]).split(".")[0]
        self.plan["poses"][ref]=[x,y,angle,side]

    def verify(self):
        return audit.verify_geometry(self.tree,self.plan,self.parts,self.pins)

    def test_source_bound_partial_receipt_replays(self):
        self.assertEqual(audit.check(),json.loads((audit.OUT/"placement-handoff.json").read_text()))

    def test_generic_codec_land_cannot_silently_replace_data_hold(self):
        fp=copy.deepcopy(audit.footprints(self.tree)["U101"])
        next(p for p in children(fp,"property") if p[1]=="Reference")[2]="U201"
        self.tree.append(fp)
        with self.assertRaisesRegex(AssertionError,"Wrong placed footprint set"):
            self.verify()

    def test_tall_film_cannot_move_beneath_upper_monitor(self):
        self.move("C501",20,50)
        with self.assertRaisesRegex(AssertionError,"Upper monitor PCB receiving"):
            self.verify()

    def test_far_feedback_part_fails_even_when_its_body_has_space(self):
        self.move("R302",140,60)
        with self.assertRaisesRegex(AssertionError,"Local feedback/pump/clock endpoint"):
            self.verify()

    def test_underside_body_cannot_cover_a_through_hole_solder_tail(self):
        self.assertEqual(first(audit.footprints(self.tree)["R201"],"layer")[1],"B.Cu")
        self.move("R201",90,52)
        with self.assertRaisesRegex(AssertionError,"Opposite-face solder/body"):
            self.verify()

    def test_codec_reserve_must_cover_every_copper_layer(self):
        first(children(self.tree,"zone")[0],"layers")[:]=[a("layers"),"F.Cu"]
        with self.assertRaises(AssertionError):
            self.verify()

    def test_empty_local_cell_receipt_cannot_pass(self):
        self.plan["local_cells"]=[]
        with self.assertRaises(AssertionError):
            self.verify()


if __name__=="__main__":
    unittest.main()
