"""Reject unsafe boundary changes even when a trial has fewer total opens."""
import copy
import json
import unittest
from pathlib import Path
from hardware.electronics.common.sexpr import children, first, read_sexpr
from hardware.fabrication.audit_nf_eight_trial import verify_geometry, verify_connections, drill_screen


class EightLayerBoundary(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        root = Path(__file__).resolve().parents[2]/'hardware/fabrication/staging'
        cls.boards = [read_sexpr((root/n/'negative_startup_physical.kicad_pcb').read_text())
                      for n in ['nf-ct-local-native-01','nf-eight-cell-native-02']]
        cls.captures = [json.loads((root/n/'capture.json').read_text())
                        for n in ['nf-ct-local-inputs-166','nf-eight-cell-inputs-164']]
        cls.removed = json.loads((root/'nf-ct-cell-prepare-01/construction.json').read_text())['removed_segments']

    def test_actual_trial_preserves_boundaries_connections_and_drill_clearance(self):
        verify_geometry(*self.boards, self.removed)
        verify_connections(*self.captures)
        drill_screen(*self.boards, self.captures[1])

    def test_missing_new_layer_keepout_rejected(self):
        changed = copy.deepcopy(self.boards[1])
        zone = next(z for z in children(changed,'zone') if children(z,'keepout') and children(z,'layer') and first(z,'layer')[1]=='In5.Cu')
        changed.remove(zone)
        with self.assertRaises(AssertionError): verify_geometry(self.boards[0],changed,self.removed)

    def test_old_power_plane_mapped_to_wrong_layer_rejected(self):
        changed = copy.deepcopy(self.boards[1])
        zone = next(z for z in children(changed,'zone') if not children(z,'keepout') and first(z,'layer')[1]=='In6.Cu')
        first(zone,'layer')[1] = 'In5.Cu'
        with self.assertRaises(AssertionError): verify_geometry(self.boards[0],changed,self.removed)

    def test_existing_force_copper_change_rejected(self):
        changed = copy.deepcopy(self.boards[1])
        track = next(n for n in children(changed,'segment') if first(n,'net')[-1]=='/DIG5_FORCE')
        first(track,'width')[1] = .16
        with self.assertRaises(AssertionError): verify_geometry(self.boards[0],changed,self.removed)

    def test_moved_bypass_pad_disconnection_rejected(self):
        changed = copy.deepcopy(self.captures[1])
        pad = next(o for o in changed['objects'] if o.get('ref')=='C36' and o.get('pin')=='1')
        pad['group'] = 'broken'
        with self.assertRaises(AssertionError): verify_connections(self.captures[0],changed)

    def test_local_CT_return_relabelled_AGND_rejected(self):
        changed = copy.deepcopy(self.captures[1])
        pad = next(o for o in changed['objects'] if o.get('ref')=='C35' and o.get('pin')=='2')
        pad['net'] = '/AGND'
        with self.assertRaises(AssertionError): verify_connections(self.captures[0],changed)


if __name__=='__main__': unittest.main()
