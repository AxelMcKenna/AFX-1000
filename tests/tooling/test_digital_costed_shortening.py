import copy,json,unittest
from pathlib import Path
from hardware.electronics.common.sexpr import children,first,read_sexpr
from hardware.fabrication.audit_candidate import geometry_delta
from hardware.fabrication.audit_digital_costed_shortening import verify_delta


class CostedShorteningBoundaryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        root=Path(__file__).resolve().parents[2]/'hardware/fabrication/staging'
        cls.before=read_sexpr((root/'digital-serial1-closed-native-03/digital_core.kicad_pcb').read_text())
        cls.after=read_sexpr((root/'digital-costed-shortening-native-01/digital_core.kicad_pcb').read_text())
        cls.recipe=json.loads((root/'digital-combined-costed-routes-01/construction.json').read_text())

    def reject(self,board,recipe=None):
        r=copy.deepcopy(recipe or self.recipe);r['geometry_delta']=geometry_delta(self.before,board)
        with self.assertRaises(AssertionError):verify_delta(self.before,board,r)

    def test_actual_native_delta_matches_declared_routes(self):
        verify_delta(self.before,self.after,self.recipe)

    def test_unrelated_component_move_rejected_even_with_matching_manifest(self):
        b=copy.deepcopy(self.after);first(children(b,'footprint')[0],'at')[1]='99'
        self.reject(b)

    def test_existing_foreign_copper_change_rejected(self):
        b=copy.deepcopy(self.after)
        n=next(n for n in children(b,'segment') if first(n,'net')[1]=='5V_DIG');first(n,'width')[1]='0.7'
        self.reject(b)

    def test_new_via_drill_change_rejected(self):
        b=copy.deepcopy(self.after);uid=self.recipe['geometry_delta']['via']['added'][0]
        n=next(n for n in children(b,'via') if first(n,'uuid')[1]==uid);first(n,'drill')[1]='0.2'
        self.reject(b)

    def test_added_track_wrong_net_rejected(self):
        b=copy.deepcopy(self.after);uid=self.recipe['geometry_delta']['segment']['added'][0]
        n=next(n for n in children(b,'segment') if first(n,'uuid')[1]==uid);first(n,'net')[1]='AGND'
        self.reject(b)

    def test_undeclared_extra_R3015_move_rejected(self):
        b=copy.deepcopy(self.after)
        f=next(f for f in children(b,'footprint') if any(p[1:3]==['Reference','R3015'] for p in children(f,'property')))
        first(f,'at')[1]='75.5'
        self.reject(b)

    def test_forged_retirement_inventory_rejected(self):
        r=copy.deepcopy(self.recipe);r['removed_uuids']=r['removed_uuids'][:-1]
        self.reject(self.after,r)


if __name__=='__main__':unittest.main()
