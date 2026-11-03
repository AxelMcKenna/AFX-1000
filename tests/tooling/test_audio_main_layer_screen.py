"""The added control layer needs the same analog guards and both reference planes."""
import unittest

from shapely.geometry import box

from hardware.fabrication.audio_main_layer_screen import LayeredSignalScreen


def polygon(geometry):
    return [dict(outer=list(geometry.exterior.coords),holes=[list(r.coords) for r in geometry.interiors])]


def capture(second_hole=False, sensitive=False):
    outer=box(0,0,10,10)
    second=outer.difference(box(4,4,6,6)) if second_hole else outer
    zones=[dict(net='AGND',layer=name,keepout=False,polygons=polygon(shape))
           for name,shape in [('In1.Cu',outer),('In4.Cu',second)]]
    if sensitive:
        zones.append(dict(net='',layer='In1.Cu',keepout=True,polygons=polygon(box(4,3,6,7)),prohibit_tracks=False,prohibit_vias=False))
    return dict(copper_layers=['F.Cu','In1.Cu','In2.Cu','In3.Cu','In4.Cu','B.Cu'],objects=[],outline=polygon(outer),zones=zones)


class LayerScreen(unittest.TestCase):
    def test_new_hole_requires_both_ground_references(self):
        screen=LayeredSignalScreen(capture(second_hole=True))
        self.assertFalse(screen.via_legal('GPIO',[5,5]))
        self.assertTrue(screen.via_legal('GPIO',[2,2]))

    def test_added_signal_layer_preserves_sensitive_node_guard(self):
        screen=LayeredSignalScreen(capture(sensitive=True))
        self.assertFalse(screen.legal('GPIO','In3.Cu',[[2,5],[8,5]]))
        self.assertTrue(screen.legal('GPIO','In3.Cu',[[2,2],[8,2]]))
        self.assertFalse(screen.via_legal('GPIO',[5,5]))

    def test_missing_second_reference_is_rejected(self):
        data=capture()
        data['zones']=[z for z in data['zones'] if z['layer']!='In4.Cu']
        with self.assertRaises(AssertionError):
            LayeredSignalScreen(data)


if __name__=='__main__':
    unittest.main()
